import fs from 'fs';
import path from 'path';
import https from 'https';

const MINIMAX_HOST = process.env.MINIMAX_HOST || 'api.minimaxi.com';
const MINIMAX_IMAGE_KEY = process.env.MINIMAX_IMAGE_API_KEY || process.env.MINIMAX_API_KEY || '';
const DEFAULT_MODEL = process.env.MINIMAX_IMAGE_MODEL || 'image-01';
const DEFAULT_ASPECT = process.env.COVER_ASPECT_RATIO || '16:9';
const COVERS_DIR = process.env.COVERS_DIR || path.join(process.cwd(), 'covers');

export interface CoverGenOptions {
  title: string;
  description?: string;
  style?: string;
  model?: string;
  aspectRatio?: string;
  outPath?: string;
}

export interface CoverGenResult {
  ok: true;
  filePath: string;
  size: number;
  mime: string;
  model: string;
}

export interface CoverGenError {
  ok: false;
  error: string;
  statusCode?: number;
}

function buildPrompt(opts: CoverGenOptions): string {
  const style = opts.style || 'modern professional editorial, suitable for Chinese WeChat public account business content, clean composition, soft natural lighting, subtle palette';
  const descPart = opts.description ? `\n\nArticle summary: ${opts.description}` : '';
  return `Generate a cover image for a Chinese WeChat public account article.\nTitle: ${opts.title}${descPart}\n\nStyle: ${style}.\nNo text, no logos, no watermarks, no people faces in the foreground.`;
}

function postJson(host: string, urlPath: string, headers: Record<string, string>, body: any, timeoutMs = 90000): Promise<{ status: number; data: string }> {
  return new Promise((resolve, reject) => {
    const payload = Buffer.from(JSON.stringify(body), 'utf-8');
    const req = https.request({
      host,
      port: 443,
      path: urlPath,
      method: 'POST',
      headers: { ...headers, 'Content-Length': payload.length.toString() },
      timeout: timeoutMs,
    }, (res) => {
      const chunks: Buffer[] = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode || 0, data: Buffer.concat(chunks).toString('utf-8') }));
    });
    req.on('timeout', () => { req.destroy(new Error('request timeout')); });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

function extractBase64DataUrl(respBody: string): { mime: string; base64: string } | null {
  let obj: any;
  try { obj = JSON.parse(respBody); } catch { return null; }

  const candidates: any[] = [
    obj?.data?.image_base64,
    obj?.image_base64,
    obj?.data?.[0]?.image_base64,
    obj?.data?.[0]?.b64_json,
    obj?.b64_json,
  ];
  for (const c of candidates) {
    if (typeof c === 'string' && c.length > 100) {
      return { mime: 'image/jpeg', base64: c };
    }
  }
  const urlCandidate = obj?.data?.image_url || obj?.data?.[0]?.url || obj?.url;
  if (typeof urlCandidate === 'string' && urlCandidate.startsWith('http')) {
    return { mime: '', base64: '', downloadUrl: urlCandidate } as any;
  }
  return null;
}

export async function generateCover(opts: CoverGenOptions): Promise<CoverGenResult | CoverGenError> {
  if (!MINIMAX_IMAGE_KEY) {
    return { ok: false, error: 'MINIMAX_IMAGE_API_KEY (or MINIMAX_API_KEY) is not set' };
  }
  const prompt = buildPrompt(opts);
  const model = opts.model || DEFAULT_MODEL;
  const aspectRatio = opts.aspectRatio || DEFAULT_ASPECT;

  const body = {
    model,
    prompt,
    aspect_ratio: aspectRatio,
    n: 1,
    response_format: 'b64_json',
  };

  let resp;
  try {
    resp = await postJson(MINIMAX_HOST, '/v1/image_generation', {
      'Authorization': `Bearer ${MINIMAX_IMAGE_KEY}`,
      'x-api-key': MINIMAX_IMAGE_KEY,
      'Content-Type': 'application/json; charset=utf-8',
    }, body);
  } catch (e: any) {
    return { ok: false, error: `minimax request failed: ${e?.message || e}` };
  }

  if (resp.status < 200 || resp.status >= 300) {
    return { ok: false, statusCode: resp.status, error: `minimax HTTP ${resp.status}: ${resp.data.slice(0, 500)}` };
  }

  const extracted = extractBase64DataUrl(resp.data);
  if (!extracted) {
    return { ok: false, error: `unexpected response shape: ${resp.data.slice(0, 500)}` };
  }

  if (!fs.existsSync(COVERS_DIR)) {
    fs.mkdirSync(COVERS_DIR, { recursive: true });
  }

  const ext = (extracted as any).downloadUrl ? 'png' : (extracted.mime.includes('png') ? 'png' : 'jpg');
  const safeTitle = (opts.title || 'cover').replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_').slice(0, 60);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const filePath = opts.outPath || path.join(COVERS_DIR, `${safeTitle}_${ts}.${ext}`);

  let buf: Buffer;
  if ((extracted as any).downloadUrl) {
    buf = await downloadToBuffer((extracted as any).downloadUrl);
  } else {
    buf = Buffer.from(extracted.base64, 'base64');
  }

  fs.writeFileSync(filePath, buf);
  return { ok: true, filePath, size: buf.length, mime: extracted.mime || 'image/jpeg', model };
}

function downloadToBuffer(url: string): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return downloadToBuffer(res.headers.location).then(resolve, reject);
      }
      const chunks: Buffer[] = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    }).on('error', reject);
  });
}
