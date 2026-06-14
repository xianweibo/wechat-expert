import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';
import { generateCover, type CoverStyle } from './cover_gen';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

const COVER_IMAGE_URL = process.env.COVER_IMAGE_URL || 'https://aka.doubaocdn.com/s/Xw8r1wUL5J';
const COVER_GEN_ENABLED = (process.env.COVER_GEN_ENABLED || 'false').toLowerCase() === 'true';
const COVERS_DIR = process.env.COVERS_DIR || path.join(process.cwd(), 'covers');
const DEFAULT_COVER_STYLE = (process.env.COVER_STYLE || 'auto').toLowerCase();
const DEFAULT_COVER_ASPECT = process.env.COVER_ASPECT_RATIO || '16:9';

app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/info', (_req, res) => {
  res.json({
    name: 'gongzhonghao-zhuanjia',
    version: '0.2.0',
    mode: process.env.NODE_ENV,
    cover_gen_enabled: COVER_GEN_ENABLED,
    cover_style: DEFAULT_COVER_STYLE,
    cover_aspect: DEFAULT_COVER_ASPECT,
  });
});

app.post('/api/bilibili/summary', async (req, res) => {
  const workerSecret = req.headers['x-worker-secret'] as string;
  const expectedSecret = process.env.BILIBILI_WORKER_SECRET;

  if (!expectedSecret || workerSecret !== expectedSecret) {
    res.status(401).json({ success: false, message: 'Unauthorized' });
    return;
  }

  try {
    const { title, summary, source, cover } = req.body as {
      title: string;
      summary: string;
      source: any;
      cover?: { style?: string; aspectRatio?: string; noText?: boolean };
    };

    console.log('[bilibili/summary] recv:');
    console.log('  title:  ', title);
    console.log('  source: ', source?.bvid);

    const accessToken = await getAccessToken();
    let thumbMediaId: string;

    if (COVER_GEN_ENABLED) {
      const style = (cover?.style || DEFAULT_COVER_STYLE) as CoverStyle;
      const aspectRatio = cover?.aspectRatio || DEFAULT_COVER_ASPECT;
      console.log(`[cover-gen] enabled, generating cover: style=${style} aspect=${aspectRatio}`);
      const result = await generateCover({
        title,
        description: (summary || '').slice(0, 400),
        style,
        aspectRatio,
        noText: cover?.noText,
      });
      if (!result.ok) {
        throw new Error(`cover generation failed (${result.attempts} attempts): ${result.error}`);
      }
      console.log(
        `[cover-gen] saved to ${result.filePath} (${result.size} bytes, model=${result.model}, style=${result.style}, ` +
        `${result.attempts} attempt(s), ${result.durationMs}ms)`
      );
      thumbMediaId = await uploadLocalImage(result.filePath, accessToken);
    } else {
      console.log('[cover-gen] disabled, using fixed COVER_IMAGE_URL');
      thumbMediaId = await uploadCoverImage(accessToken);
    }

    const mediaId = await createDraft({
      title,
      summary,
      source,
      thumbMediaId,
    }, accessToken);

    res.json({ success: true, media_id: mediaId });
  } catch (e: any) {
    console.error('[bilibili/summary] failed:', e.message);
    res.status(500).json({ success: false, message: e.message });
  }
});

app.get('/api/cover/styles', (_req, res) => {
  res.json({
    styles: ['auto', 'tech', 'finance', 'lifestyle', 'education', 'news'],
    default: DEFAULT_COVER_STYLE,
    aspects: ['1:1', '16:9', '2.35:1', '4:3', '3:4'],
    default_aspect: DEFAULT_COVER_ASPECT,
    text_overlay: (process.env.COVER_TEXT_OVERLAY ?? 'true').toLowerCase() !== 'false',
  });
});

async function getAccessToken(): Promise<string> {
  const appId = process.env.WECHAT_APP_ID || 'wx567a639466e247cd';
  const appSecret = process.env.WECHAT_APP_SECRET;

  if (!appSecret) {
    throw new Error('WECHAT_APP_SECRET not configured');
  }

  const url = `https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${appId}&secret=${appSecret}`;
  const resp = await fetch(url);
  const data = await resp.json();

  if (data.errcode) {
    throw new Error(`get access_token failed: ${data.errmsg}`);
  }

  return data.access_token;
}

async function uploadCoverImage(accessToken: string): Promise<string> {
  console.log('uploading fixed cover image...');
  const imageResp = await fetch(COVER_IMAGE_URL);
  if (!imageResp.ok) {
    throw new Error(`download cover image failed: ${imageResp.status}`);
  }
  const imageBuffer = Buffer.from(await imageResp.arrayBuffer());

  const contentType = imageResp.headers.get('content-type') || 'image/jpeg';
  const ext = contentType.includes('png') ? 'png' : 'jpg';

  return await uploadBufferToWechat(imageBuffer, contentType, ext, accessToken);
}

async function uploadLocalImage(filePath: string, accessToken: string): Promise<string> {
  if (!fs.existsSync(filePath)) {
    throw new Error(`local cover not found: ${filePath}`);
  }
  const buf = fs.readFileSync(filePath);
  const ext = filePath.toLowerCase().endsWith('.png') ? 'png' : 'jpg';
  const contentType = ext === 'png' ? 'image/png' : 'image/jpeg';
  console.log('uploading local cover:', filePath, `(${buf.length} bytes)`);
  return await uploadBufferToWechat(buf, contentType, ext, accessToken);
}

async function uploadBufferToWechat(
  imageBuffer: Buffer,
  contentType: string,
  ext: string,
  accessToken: string,
): Promise<string> {
  const boundary = '----FormBoundary' + Date.now();
  const parts: Buffer[] = [];
  parts.push(Buffer.from(
    `--${boundary}\r\nContent-Disposition: form-data; name="media"; filename="cover.${ext}"\r\nContent-Type: ${contentType}\r\n\r\n`
  ));
  parts.push(imageBuffer);
  parts.push(Buffer.from(`\r\n--${boundary}--\r\n`));

  const uploadUrl = `https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${accessToken}&type=image`;
  const uploadResp = await fetch(uploadUrl, {
    method: 'POST',
    headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}` },
    body: Buffer.concat(parts),
  });

  const uploadData = await uploadResp.json();
  if (uploadData.errcode) {
    throw new Error(`upload cover to wechat failed: ${uploadData.errmsg}`);
  }
  console.log('cover uploaded, media_id:', uploadData.media_id);
  return uploadData.media_id;
}

interface DraftParams {
  title: string;
  summary: string;
  source: {
    bvid: string;
    url: string;
    up_uid: number;
    up_name: string;
    published_at: string;
  };
  thumbMediaId: string;
}

async function createDraft(params: DraftParams, accessToken: string): Promise<string> {
  const content = generateArticleContent(params);

  const draftData = {
    articles: [{
      title: params.title,
      author: '',
      digest: params.summary.substring(0, 120),
      content,
      thumb_media_id: params.thumbMediaId,
      need_open_comment: 1,
      only_fans_can_comment: 0,
    }],
  };

  const url = `https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${accessToken}`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draftData),
  });

  const data = await resp.json();

  if (data.errcode) {
    throw new Error(`create draft failed: ${data.errmsg}`);
  }

  return data.media_id;
}

function generateArticleContent(params: DraftParams): string {
  return `<h2>ðŸ“ å†…å®¹ç²¾åŽ</h2>
${params.summary.replace(/\n/g, '<br/>')}
<hr/>
<p style="color:#999;font-size:12px;">æœ¬å†…å®¹ç”± AI æ ¹æ®è§†é¢‘å­—å¹•è‡ªåŠ¨ç”Ÿæˆï¼Œä»…ä¾›å­¦ä¹ å‚è€ƒï¼Œä¸æž„æˆæŠ•èµ„å»ºè®®ã€‚</p>`;
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`gongzhonghao-zhuanjia API listening on http://0.0.0.0:${PORT}`);
});