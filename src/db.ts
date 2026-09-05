import { Pool } from 'pg';

// 草稿历史 + bvid 幂等记录的持久层。
// PostgreSQL（docker-compose 里的 postgres 服务，named volume 持久化）。
// DB 不可用时自动降级为纯内存模式：主流程不受影响，只打一次警告。

let pool: Pool | null = null;
let dbOk = false;
let warned = false;

function warnOnce(e: unknown): void {
  if (!warned) {
    warned = true;
    console.warn(`[db] 数据库不可用，降级为纯内存幂等缓存: ${(e as Error).message}`);
  }
}

export async function initDraftStore(memory: Map<string, string>): Promise<void> {
  const url = (process.env.DATABASE_URL || '').trim();
  if (!url) {
    console.warn('[db] DATABASE_URL 未配置，草稿历史仅存内存（重启即失）');
    return;
  }
  pool = new Pool({ connectionString: url, max: 3 });
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS draft_history (
        id SERIAL PRIMARY KEY,
        bvid TEXT UNIQUE,
        title TEXT,
        media_id TEXT NOT NULL,
        mode TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      )
    `);
    // 预加载最近 100 条 bvid 幂等记录到内存（L1），DB 是持久层（L2）
    const r = await pool.query(
      `SELECT bvid, media_id FROM draft_history
       WHERE bvid IS NOT NULL AND bvid <> ''
       ORDER BY id DESC LIMIT 100`
    );
    for (const row of r.rows) {
      memory.set(row.bvid as string, row.media_id as string);
    }
    dbOk = true;
    console.log(`[db] draft_history 就绪，预加载 ${r.rows.length} 条 bvid 幂等记录`);
  } catch (e) {
    warnOnce(e);
  }
}

export async function persistDraftRecord(rec: {
  bvid: string;
  title: string;
  mediaId: string;
  mode: string;
}): Promise<void> {
  if (!pool || !dbOk) return;
  try {
    await pool.query(
      `INSERT INTO draft_history (bvid, title, media_id, mode)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (bvid) DO UPDATE SET title = EXCLUDED.title, media_id = EXCLUDED.media_id`,
      [rec.bvid || null, rec.title || '', rec.mediaId, rec.mode]
    );
  } catch (e) {
    // 写失败只降级：内存缓存仍在，本进程不再尝试写库
    dbOk = false;
    warnOnce(e);
  }
}
