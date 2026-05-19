import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/info', (_req, res) => {
  res.json({
    name: '公众号专家',
    version: '0.1.0',
    mode: process.env.NODE_ENV,
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
    const { title, summary, source } = req.body;

    console.log('收到 B站 Worker 总结:');
    console.log('标题:', title);
    console.log('来源:', source);

    const accessToken = await getAccessToken();
    const mediaId = await createDraft({
      title,
      summary,
      source,
    }, accessToken);

    res.json({ success: true, media_id: mediaId });
  } catch (e: any) {
    console.error('创建草稿失败:', e.message);
    res.status(500).json({ success: false, message: e.message });
  }
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
    throw new Error(`获取 access_token 失败: ${data.errmsg}`);
  }

  return data.access_token;
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
}

async function createDraft(params: DraftParams, accessToken: string): Promise<string> {
  const content = generateArticleContent(params);

  const draftData = {
    articles: [{
      title: params.title,
      author: params.source.up_name,
      digest: params.summary.substring(0, 120),
      content,
      thumb_media_id: '',
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
    throw new Error(`创建草稿失败: ${data.errmsg}`);
  }

  return data.media_id;
}

function generateArticleContent(params: DraftParams): string {
  return `<p>📺 来源：<a href="${params.source.url}">${params.source.up_name} - ${params.title}</a></p>
<p>📅 发布时间：${params.source.published_at}</p>
<hr/>
<h2>📝 内容精华</h2>
${params.summary.replace(/\n/g, '<br/>')}
<hr/>
<p>🔗 <a href="${params.source.url}">👉 点击查看原视频</a></p>
<hr/>
<p style="color:#999;font-size:12px;">本内容由 AI 根据视频字幕自动生成，仅供学习参考，不构成投资建议。</p>`;
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`公众号专家 API 运行在 http://0.0.0.0:${PORT}`);
});