// ASR 兜底: B站字幕不可用时, 下载视频音频 -> NAS whisper.cpp 服务转写
// 缓存层: 进程内 LRU + PostgreSQL 持久化(避免重复转写)
import { Pool } from 'pg';
import { execSync } from 'child_process';
import { createHash } from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

let dbPool: Pool | null = null;
let dbReady = false;
let dbWarned = false;

function warnDb(e: unknown): void {
  if (!dbWarned) {
    dbWarned = true;
    console.warn(`[asr] DB 不可用, 仅用内存缓存: ${(e as Error).message}`);
  }
}

export async function initAsrCache(): Promise<void> {
  const url = (process.env.DATABASE_URL || '').trim();
  if (!url) return;
  dbPool = new Pool({ connectionString: url, max: 2 });
  try {
    await dbPool.query(`
      CREATE TABLE IF NOT EXISTS asr_cache (
        bvid TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        chars INT NOT NULL,
        transcribe_seconds REAL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      )
    `);
    dbReady = true;
    console.log('[asr] asr_cache 表就绪');
  } catch (e) {
    dbPool = null;
    warnDb(e);
  }
}

const memCache = new Map<string, { text: string; chars: number; ts: number }>();
const MEM_MAX = 50;
const MEM_TTL_MS = 24 * 60 * 60 * 1000;

function memGet(bvid: string) {
  const v = memCache.get(bvid);
  if (!v) return null;
  if (Date.now() - v.ts > MEM_TTL_MS) {
    memCache.delete(bvid);
    return null;
  }
  return v;
}

function memSet(bvid: string, text: string) {
  if (memCache.size >= MEM_MAX) {
    const oldest = memCache.keys().next().value;
    if (oldest) memCache.delete(oldest);
  }
  memCache.set(bvid, { text, chars: text.length, ts: Date.now() });
}

async function dbGet(bvid: string): Promise<string | null> {
  if (!dbPool || !dbReady) return null;
  try {
    const r = await dbPool.query('SELECT text FROM asr_cache WHERE bvid=$1', [bvid]);
    if (r.rows.length) {
      memSet(bvid, r.rows[0].text);
      return r.rows[0].text as string;
    }
  } catch (e) {
    dbReady = false;
    warnDb(e);
  }
  return null;
}

async function dbSet(bvid: string, text: string, transcribeSeconds: number): Promise<void> {
  if (!dbPool || !dbReady) return;
  try {
    await dbPool.query(
      `INSERT INTO asr_cache (bvid, text, chars, transcribe_seconds) VALUES ($1,$2,$3,$4)
       ON CONFLICT (bvid) DO UPDATE SET text=EXCLUDED.text, chars=EXCLUDED.chars, transcribe_seconds=EXCLUDED.transcribe_seconds, created_at=now()`,
      [bvid, text, text.length, transcribeSeconds]
    );
  } catch (e) {
    dbReady = false;
    warnDb(e);
  }
}

// 工具: B站 playurl 拿音频 m4s URL(走 mp_proxy 已有的 B站 cookie, 通过 SESSDATA 鉴权)
async function fetchAudioUrl(bvid: string, cid: number): Promise<string | null> {
  const sessdata = (process.env.BILIBILI_SESSDATA || '').trim();
  if (!sessdata) return null;
  const cookie = `SESSDATA=${sessdata}; bili_jct=${(process.env.BILIBILI_BILI_JCT || '').trim()}`;
  const url = `https://api.bilibili.com/x/player/playurl?bvid=${bvid}&cid=${cid}&qn=16&fnval=1&fnver=0&fourk=0`;
  const resp = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'Referer': `https://www.bilibili.com/video/${bvid}`,
      'Cookie': cookie,
    },
  });
  const j: any = await resp.json();
  if (j.code !== 0) return null;
  // FLV 单流(常见) 或 DASH audio
  const durl = j.data?.durl;
  if (durl && durl[0]?.url) return durl[0].url as string;
  const audio = j.data?.dash?.audio;
  if (audio && audio[0]?.baseUrl) return audio[0].baseUrl as string;
  return null;
}

// 下载音频到本地临时文件
async function downloadAudio(audioUrl: string, bvid: string): Promise<string> {
  const tmp = path.join(os.tmpdir(), `gzh-asr-${bvid}-${createHash('md5').update(audioUrl).digest('hex').slice(0,8)}.m4a`);
  const resp = await fetch(audioUrl, {
    headers: {
      'User-Agent': 'Mozilla/5.0',
      'Referer': `https://www.bilibili.com/video/${bvid}`,
    },
  });
  if (!resp.ok) throw new Error(`audio download HTTP ${resp.status}`);
  const buf = Buffer.from(await resp.arrayBuffer());
  fs.writeFileSync(tmp, buf);
  return tmp;
}

export interface AsrResult { text: string; transcribe_seconds: number; fromCache: boolean }

export async function transcribeViaAsr(bvid: string, cid: number, asrServiceUrl: string): Promise<AsrResult | null> {
  // 1. 缓存查
  const m = memGet(bvid);
  if (m) return { text: m.text, transcribe_seconds: 0, fromCache: true };
  const cached = await dbGet(bvid);
  if (cached) return { text: cached, transcribe_seconds: 0, fromCache: true };

  // 2. 拿音频 URL -> 下载 -> 上传到 NAS ASR 服务
  const audioUrl = await fetchAudioUrl(bvid, cid);
  if (!audioUrl) {
    console.warn(`[asr] ${bvid} 拿不到 audio url`);
    return null;
  }
  const localPath = await downloadAudio(audioUrl, bvid);
  console.log(`[asr] ${bvid} 音频下载完成 ${(fs.statSync(localPath).size/1024/1024).toFixed(1)}MB, 开始转写`);

  // 3. 推送到 NAS ASR 服务(wait, 27分钟视频约8-12分钟)
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 1500 * 1000); // 25 分钟上限
  let result: AsrResult | null = null;
  try {
    const audioBuf = fs.readFileSync(localPath);
    const r = await fetch(`${asrServiceUrl}/asr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio_b64: audioBuf.toString('base64'),
        bvid,
      }),
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    if (!r.ok) {
      console.warn(`[asr] ${bvid} NAS 服务返回 HTTP ${r.status}`);
      return null;
    }
    const j: any = await r.json();
    if (!j.ok || !j.text || j.text.length < 200) {
      console.warn(`[asr] ${bvid} NAS 服务结果不可用: ok=${j.ok} len=${(j.text||'').length}`);
      return null;
    }
    memSet(bvid, j.text);
    await dbSet(bvid, j.text, j.transcribe_seconds || 0);
    result = { text: j.text, transcribe_seconds: j.transcribe_seconds || 0, fromCache: false };
    console.log(`[asr] ${bvid} 转写完成 chars=${j.text.length} took=${j.transcribe_seconds}s`);
    return result;
  } catch (e: any) {
    clearTimeout(timer);
    console.warn(`[asr] ${bvid} 调用 NAS 服务异常: ${e.message}`);
    return null;
  } finally {
    try { fs.unlinkSync(localPath); } catch {}
  }
}
