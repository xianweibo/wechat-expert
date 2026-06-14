import fs from 'fs';
import path from 'path';
import https from 'https';
import crypto from 'crypto';

const MINIMAX_HOST = process.env.MINIMAX_HOST || 'api.minimaxi.com';
const MINIMAX_IMAGE_KEY = process.env.MINIMAX_IMAGE_API_KEY || process.env.MINIMAX_API_KEY || '';
const DEFAULT_MODEL = process.env.MINIMAX_IMAGE_MODEL || 'image-01';
const DEFAULT_ASPECT = process.env.COVER_ASPECT_RATIO || '16:9';
const COVERS_DIR = process.env.COVERS_DIR || path.join(process.cwd(), 'covers');
const DEFAULT_STYLE = process.env.COVER_STYLE || 'auto';
const RETRY_MAX = Math.max(0, parseInt(process.env.COVER_RETRY_MAX || '2', 10));
const RETRY_BASE_MS = Math.max(100, parseInt(process.env.COVER_RETRY_BASE_MS || '1500', 10));
const TEXT_OVERLAY = (process.env.COVER_TEXT_OVERLAY ?? 'true').toLowerCase() !== 'false';

export type CoverStyle = 'auto' | 'tech' | 'finance' | 'lifestyle' | 'education' | 'news';

export interface CoverGenOptions {
  title: string;
  description?: string;
  style?: CoverStyle | string;
  model?: string;
  aspectRatio?: string;
  outPath?: string;
  noText?: boolean;
}

export interface CoverGenResult {
  ok: true;
  filePath: string;
  size: number;
  mime: string;
  model: string;
  style: string;
  attempts: number;
  durationMs: number;
}

export interface CoverGenError {
  ok: false;
  error: string;
  statusCode?: number;
  attempts: number;
}

const STYLE_PRESETS: Record<string, string> = {
  auto: 'modern professional editorial, suitable for Chinese WeChat public account business content, clean composition, soft natural lighting, subtle palette',
  tech: 'futuristic tech aesthetic, deep blue and cyan gradients, abstract geometric shapes and circuit-like patterns, soft glow, no human faces, suitable for AI / programming / software topics',
  finance: 'business finance aesthetic, dark navy with gold accents, abstract candlestick and chart silhouettes, upward arrows, professional and authoritative, no human faces, suitable for stocks / economy / markets topics',
  lifestyle: 'lifestyle aesthetic, warm pastel tones, soft natural daylight, cozy lifestyle objects (coffee, plants, books, window light), relaxed and inviting, no human faces, suitable for personal growth / wellness topics',
  education: 'educational aesthetic, light cream background with subtle paper texture, soft bookshelf or chalkboard motifs, warm and intellectual, no human faces, suitable for learning / knowledge / tutorial topics',
  news: 'news editorial aesthetic, bold red accent on neutral grayscale, sharp geometric shapes reminiscent of broadcast graphics, urgent and serious tone, no human faces, suitable for current events / breaking news topics',
};

const VALID_STYLES: CoverStyle[] = ['auto', 'tech', 'finance', 'lifestyle', 'education', 'news'];

function resolveStyle(style?: string): string {
  const s = (style || DEFAULT_STYLE || 'auto').toLowerCase();
  if (!VALID_STYLES.includes(s as CoverStyle)) {
    console.warn(`[cover-gen] unknown style '${s}', falling back to 'auto'`);
    return STYLE_PRESETS.auto;
  }
  return STYLE_PRESETS[s];
}

function buildPrompt(opts: CoverGenOptions): string {
  const styleDesc = resolveStyle(opts.style);
  const descPart = opts.description ? `\n\nArticle summary: ${opts.description}` : '';
  const overlay = !opts.noText && TEXT_OVERLAY;
  const textDirective = overlay
    ? `\n\nRender the article title prominently as bold elegant Chinese typography. Title text to render:\n"""${opts.title}"""\nUse a clear readable font, high contrast against the background, with subtle shadow or highlight for legibility. The title should occupy the central area of the image, scaled to be readable when displayed as a small thumbnail.`
    : `\n\nDo NOT render any text, logos, watermarks, or recognizable human faces.`;

  return `Generate a cover image for a Chinese WeChat public account article.
Title: ${opts.title}${descPart}

Visual style: ${styleDesc}.${textDirective}

Technical requirements:
- Aspect ratio: ${opts.aspectRatio || DEFAULT_ASPECT} (WeChat list-card friendly)
- No other text besides the title
- No watermarks, signatures, or copyright marks
- No recognizable human faces in the foreground`;
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

function extractBase64DataUrl(respBody: string): { mime: string; base64: string; downloadUrl?: string } | null {
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
    return { mime: '', base64: '', downloadUrl: urlCandidate };
  }
  return null;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function isTransient(status: number): boolean {
  return status === 429 || (status >= 500 && status < 600);
}

export async function generateCover(opts: CoverGenOptions): Promise<CoverGenResult | CoverGenError> {
  if (!MINIMAX_IMAGE_KEY) {
    return { ok: false, error: 'MINIMAX_IMAGE_API_KEY (or MINIMAX_API_KEY) is not set', attempts: 0 };
  }
  const prompt = buildPrompt(opts);
  const model = opts.model || DEFAULT_MODEL;
  const aspectRatio = opts.aspectRatio || DEFAULT_ASPECT;
  const styleName = (opts.style || DEFAULT_STYLE || 'auto').toLowerCase();

  const body = {
    model,
    prompt,
    aspect_ratio: aspectRatio,
    n: 1,
    response_format: 'b64_json',
  };

  if (!fs.existsSync(COVERS_DIR)) {
    fs.mkdirSync(COVERS_DIR, { recursive: true });
  }

  const titleHash = crypto.createHash('sha1').update(`${styleName}|${opts.title}|${opts.description || ''}`).digest('hex').slice(0, 10);
  const safeTitle = (opts.title || 'cover').replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_').slice(0, 30);
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filePath = opts.outPath || path.join(COVERS_DIR, `${safeTitle}_${titleHash}_${ts}.jpg`);

  let lastErr = '';
  let lastStatus: number | undefined;
  const startedAt = Date.now();

  for (let attempt = 1; attempt <= RETRY_MAX + 1; attempt++) {
    let resp;
    try {
      resp = await postJson(MINIMAX_HOST, '/v1/image_generation', {
        'Authorization': `Bearer ${MINIMAX_IMAGE_KEY}`,
        'x-api-key': MINIMAX_IMAGE_KEY,
        'Content-Type': 'application/json; charset=utf-8',
      }, body);
    } catch (e: any) {
      lastErr = `minimax request failed: ${e?.message || e}`;
      console.warn(`[cover-gen] attempt ${attempt} failed: ${lastErr}`);
      if (attempt > RETRY_MAX) break;
      await sleep(RETRY_BASE_MS * Math.pow(2, attempt - 1));
      continue;
    }

    lastStatus = resp.status;
    if (resp.status < 200 || resp.status >= 300) {
      lastErr = `minimax HTTP ${resp.status}: ${resp.data.slice(0, 500)}`;
      console.warn(`[cover-gen] attempt ${attempt} ${lastErr}`);
      if (!isTransient(resp.status) || attempt > RETRY_MAX) break;
      await sleep(RETRY_BASE_MS * Math.pow(2, attempt - 1));
      continue;
    }

    const extracted = extractBase64DataUrl(resp.data);
    if (!extracted) {
      lastErr = `unexpected response shape: ${resp.data.slice(0, 500)}`;
      console.warn(`[cover-gen] attempt ${attempt} ${lastErr}`);
      if (attempt > RETRY_MAX) break;
      await sleep(RETRY_BASE_MS * Math.pow(2, attempt - 1));
      continue;
    }

    let buf: Buffer;
    try {
      if (extracted.downloadUrl) {
        buf = await downloadToBuffer(extracted.downloadUrl);
      } else {
        buf = Buffer.from(extracted.base64, 'base64');
      }
    } catch (e: any) {
      lastErr = `download/decode failed: ${e?.message || e}`;
      console.warn(`[cover-gen] attempt ${attempt} ${lastErr}`);
      if (attempt > RETRY_MAX) break;
      await sleep(RETRY_BASE_MS * Math.pow(2, attempt - 1));
      continue;
    }

    if (buf.length < 1024) {
      lastErr = `image too small (${buf.length} bytes), likely invalid`;
      console.warn(`[cover-gen] attempt ${attempt} ${lastErr}`);
      if (attempt > RETRY_MAX) break;
      await sleep(RETRY_BASE_MS * Math.pow(2, attempt - 1));
      continue;
    }

    const mime = extracted.mime || 'image/jpeg';
    fs.writeFileSync(filePath, buf);
    return {
      ok: true,
      filePath,
      size: buf.length,
      mime,
      model,
      style: styleName,
      attempts: attempt,
      durationMs: Date.now() - startedAt,
    };
  }

  return {
    ok: false,
    error: lastErr || 'cover generation failed after retries',
    statusCode: lastStatus,
    attempts: RETRY_MAX + 1,
  };
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

export const __testing = { STYLE_PRESETS, VALID_STYLES, resolveStyle, buildPrompt, isTransient };