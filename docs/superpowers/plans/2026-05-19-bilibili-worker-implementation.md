# B站充电视频总结 Worker - 实现计划

> 最后更新：2026-05-19
> 状态：已批准

---

## 文件结构

创建以下文件：

| 文件 | 职责 |
|------|------|
| `gzh-worker/package.json` | Node.js 依赖 |
| `gzh-worker/tsconfig.json` | TypeScript 配置 |
| `gzh-worker/src/index.ts` | 入口，cron 调度 + 主逻辑 |
| `gzh-worker/src/bilibili.ts` | B 站爬取 (视频列表/字幕/简介) |
| `gzh-worker/src/minimax.ts` | MiniMax M2.7 总结 |
| `gzh-worker/src/poster.ts` | 发送到阿里云 API |
| `gzh-worker/src/types.ts` | 共享类型定义 |
| `gzh-worker/src/config.ts` | 环境变量读取 |
| `gzh-worker/Dockerfile` | 镜像构建 |
| `gzh-worker/docker-compose.yml` | 容器编排 + cron |
| `gzh-worker/.env.example` | 环境变量模板 |
| `gzh-worker/.gitignore` | 忽略规则 |

---

## 小步骤任务

### Phase 1: 项目脚手架

#### Task 1.1: 创建项目目录和 package.json

**文件**：`gzh-worker/package.json`

```json
{
  "name": "gzh-worker",
  "version": "0.1.0",
  "description": "B站充电视频总结 Worker - 每日12点抓取+总结+推送到公众号草稿",
  "main": "dist/index.js",
  "scripts": {
    "dev": "tsx src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "echo \"No tests yet\" && exit 0"
  },
  "dependencies": {
    "axios": "^1.7.9",
    "dotenv": "^16.4.7",
    "node-cron": "^3.0.3",
    "node-fetch": "^2.7.0"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/node-cron": "^3.0.11",
    "tsx": "^4.19.0",
    "typescript": "^5.6.0"
  }
}
```

**验证**：`cat gzh-worker/package.json`

---

#### Task 1.2: 创建 tsconfig.json

**文件**：`gzh-worker/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**验证**：`cat gzh-worker/tsconfig.json`

---

#### Task 1.3: 创建 .gitignore

**文件**：`gzh-worker/.gitignore`

```
node_modules/
dist/
.env
.env.local
.env.production
*.log
data/
```

**验证**：`cat gzh-worker/.gitignore`

---

#### Task 1.4: 创建 .env.example

**文件**：`gzh-worker/.env.example`

```
# B站登录态
BILIBILI_SESSDATA=你的SESSDATA
BILIBILI_BILI_JCT=你的bili_jct
BILIBILI_UID=144796213

# 目标UP主
TARGET_UP_UID=290663424

# MiniMax
MINIMAX_API_KEY=你的MiniMax API Key

# 阿里云服务器
ALIYUN_API_URL=http://8.134.248.11:3000/api/bilibili/summary

# 本地存储
LAST_BVID_FILE=/app/data/last_bvid.txt
```

**验证**：`cat gzh-worker/.env.example`

---

### Phase 2: 核心代码

#### Task 2.1: 创建类型定义

**文件**：`gzh-worker/src/types.ts`

```typescript
export interface BilibiliVideo {
  bvid: string;
  title: string;
  description: string;
  pubdate: number;
  duration: number;
  owner: {
    mid: number;
    name: string;
    face: string;
  };
  stat: {
    view: number;
    like: number;
    coin: number;
    favorite: number;
    share: number;
    reply: number;
  };
}

export interface Subtitle {
  lan: string;
  lan_doc: string;
  subtitle_url: string;
}

export interface VideoDetail {
  title: string;
  description: string;
  dynamic: string;
  owner: {
    mid: number;
    name: string;
    face: string;
  };
  subtitle: {
    subtitles: Subtitle[];
  };
 pages: {
    cid: number;
    part: string;
  }[];
}

export interface SummaryPayload {
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

export interface Config {
  bilibili: {
    sessdata: string;
    bili_jct: string;
    uid: number;
  };
  targetUpUid: number;
  minimaxApiKey: string;
  aliyunApiUrl: string;
  lastBvidFile: string;
}
```

**验证**：`cat gzh-worker/src/types.ts`

---

#### Task 2.2: 创建配置读取

**文件**：`gzh-worker/src/config.ts`

```typescript
import dotenv from 'dotenv';
import { Config } from './types';
import path from 'path';

dotenv.config({ path: path.join(__dirname, '..', '.env') });

export function getConfig(): Config {
  const sessdata = process.env.BILIBILI_SESSDATA;
  const bili_jct = process.env.BILIBILI_BILI_JCT;
  const uid = parseInt(process.env.BILIBILI_UID || '144796213');
  const targetUpUid = parseInt(process.env.TARGET_UP_UID || '290663424');
  const minimaxApiKey = process.env.MINIMAX_API_KEY;
  const aliyunApiUrl = process.env.ALIYUN_API_URL || 'http://8.134.248.11:3000/api/bilibili/summary';
  const lastBvidFile = process.env.LAST_BVID_FILE || '/app/data/last_bvid.txt';

  if (!sessdata || !bili_jct || !minimaxApiKey) {
    throw new Error('Missing required environment variables: BILIBILI_SESSDATA, BILIBILI_BILI_JCT, MINIMAX_API_KEY');
  }

  return {
    bilibili: { sessdata, bili_jct, uid },
    targetUpUid,
    minimaxApiKey,
    aliyunApiUrl,
    lastBvidFile,
  };
}
```

**验证**：`cat gzh-worker/src/config.ts`

---

#### Task 2.3: 创建 B 站爬取模块

**文件**：`gzh-worker/src/bilibili.ts`

```typescript
import axios from 'axios';
import { BilibiliVideo, VideoDetail, Subtitle } from './types';

const BILIBILI_API = 'https://api.bilibili.com';

export async function getCookieHeaders(sessdata: string, bili_jct: string): Promise<Record<string, string>> {
  return {
    'Cookie': `SESSDATA=${sessdata}; bili_jct=${bili_jct}`,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com',
  };
}

export async function getLatestVideos(
  uid: number,
  sessdata: string,
  bili_jct: string
): Promise<BilibiliVideo[]> {
  const headers = await getCookieHeaders(sessdata, bili_jct);

  // wbi 签名需要特殊处理，这里先用简单方式尝试
  const url = `${BILIBILI_API}/x/space/wbi/arc/search?mid=${uid}&pn=1&ps=10&order=pubdate`;

  const response = await axios.get(url, { headers });
  const data = response.data;

  if (data.code !== 0) {
    console.error('B站 API 错误:', data.message);
    // 尝试备用接口
    const fallbackUrl = `${BILIBILI_API}/x/space/arc/search?mid=${uid}&pn=1&ps=10&order=pubdate`;
    const fallbackResp = await axios.get(fallbackUrl, { headers });
    if (fallbackResp.data.code === 0) {
      return fallbackResp.data.data.list.vlist || [];
    }
    throw new Error(`B站 API 请求失败: ${data.message}`);
  }

  return data.data.list.vlist || [];
}

export async function getVideoDetail(
  bvid: string,
  sessdata: string,
  bili_jct: string
): Promise<VideoDetail> {
  const headers = await getCookieHeaders(sessdata, bili_jct);
  const url = `${BILIBILI_API}/x/web-interface/view?bvid=${bvid}`;
  const response = await axios.get(url, { headers });

  if (response.data.code !== 0) {
    throw new Error(`获取视频详情失败: ${response.data.message}`);
  }

  return response.data.data;
}

export async function getSubtitle(
  bvid: string,
  cid: number,
  sessdata: string,
  bili_jct: string
): Promise<string> {
  const headers = await getCookieHeaders(sessdata, bili_jct);
  const url = `${BILIBILI_API}/x/player/v2?bvid=${bvid}&cid=${cid}`;
  const response = await axios.get(url, { headers });

  if (response.data.code !== 0) {
    console.warn(`获取字幕失败: ${response.data.message}`);
    return '';
  }

  const subtitles = response.data.data.subtitle?.subtitles || [];
  if (subtitles.length === 0) {
    console.warn('没有字幕');
    return '';
  }

  // 获取第一个字幕文件
  const subtitleInfo = subtitles[0];
  const subtitleUrl = subtitleInfo.subtitle_url;

  if (!subtitleUrl) {
    return '';
  }

  // 下载字幕文件
  const subtitleResp = await axios.get(subtitleUrl, { headers: { ...headers, Referer: 'https://www.bilibili.com' } });

  // 解析 ASS/SRT 为纯文本
  return parseSubtitle(subtitleResp.data);
}

function parseSubtitle(content: string): string {
  // 简单解析 ASS/SSA 格式
  const lines = content.split('\n');
  const textLines: string[] = [];

  for (const line of lines) {
    // 跳过元数据行
    if (line.startsWith('[') || line.startsWith('Events:') || line.startsWith('Format:')) {
      continue;
    }
    // 解析 Dialogue 行
    const dialogueMatch = line.match(/^Dialogue:\s+\d+,\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+,,(.+)$/);
    if (dialogueMatch) {
      const text = dialogueMatch[1];
      // 移除样式标签
      const cleanText = text.replace(/\{[^}]+\}/g, '').replace(/<[^>]+>/g, '').trim();
      if (cleanText) {
        textLines.push(cleanText);
      }
    }
  }

  return textLines.join('\n');
}

export function isChargedVideo(video: BilibiliVideo): boolean {
  // 充电专属视频的判断逻辑：
  // 1. 查看视频标题是否包含"充电"相关标识
  // 2. 或者视频需要登录才能查看（pv=1 表示需要登录）
  // 这里先简单通过标题判断，后续可能需要调整
  return true; // 先全部抓取，后续加判断
}
```

**验证**：`cat gzh-worker/src/bilibili.ts`

---

#### Task 2.4: 创建 MiniMax 总结模块

**文件**：`gzh-worker/src/minimax.ts`

```typescript
import axios from 'axios';

export interface SummaryResult {
  summary: string;
  keyPoints: string[];
}

export async function generateSummary(
  title: string,
  description: string,
  subtitleText: string,
  apiKey: string
): Promise<SummaryResult> {
  const prompt = `你是一个财经学习内容整理助手。请根据以下视频字幕和简介，生成一段精华总结。

视频标题：${title}
视频简介：${description}
字幕内容：
${subtitleText || '（无字幕）'}

要求：
- 提取核心要点，3-5 条
- 用通俗易懂的语言
- 不复述原话，用自己语言重构
- 保持中立，不预测涨跌
- 篇幅控制在 300 字以内
- 最后附上原视频链接：https://www.bilibili.com/video/${'${bvid}'}`;

  const response = await axios.post(
    'https://api.minimax.chat/v1/text/chatcompletion_v2',
    {
      model: 'MiniMax-Text-01',
      messages: [
        {
          role: 'user',
          content: prompt,
        },
      ],
      max_tokens: 1000,
      temperature: 0.7,
    },
    {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (response.data.error) {
    throw new Error(`MiniMax API 错误: ${response.data.error.message}`);
  }

  const summary = response.data.choices?.[0]?.message?.content || '';

  // 简单提取关键点（以换行分隔）
  const keyPoints = summary
    .split('\n')
    .filter((line: string) => line.trim() && (line.includes('•') || line.match(/^\d+\./)))
    .map((line: string) => line.trim());

  return { summary, keyPoints };
}
```

**验证**：`cat gzh-worker/src/minimax.ts`

---

#### Task 2.5: 创建发送到阿里云模块

**文件**：`gzh-worker/src/poster.ts`

```typescript
import axios from 'axios';
import { SummaryPayload } from './types';

export async function postSummary(
  payload: SummaryPayload,
  apiUrl: string
): Promise<void> {
  console.log('发送到阿里云服务器...');

  const response = await axios.post(apiUrl, payload, {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000,
  });

  if (response.data.success) {
    console.log('✅ 发送成功，公众号草稿已创建');
  } else {
    console.error('❌ 发送失败:', response.data.message);
    throw new Error(`发送失败: ${response.data.message}`);
  }
}
```

**验证**：`cat gzh-worker/src/poster.ts`

---

#### Task 2.6: 创建主入口

**文件**：`gzh-worker/src/index.ts`

```typescript
import cron from 'node-cron';
import fs from 'fs';
import path from 'path';
import { getConfig } from './config';
import { getLatestVideos, getVideoDetail, getSubtitle, isChargedVideo } from './bilibili';
import { generateSummary } from './minimax';
import { postSummary } from './poster';
import { SummaryPayload } from './types';

async function loadLastBvid(filePath: string): Promise<string | null> {
  try {
    if (fs.existsSync(filePath)) {
      return fs.readFileSync(filePath, 'utf-8').trim();
    }
  } catch (e) {
    console.warn('读取 last_bvid 失败:', e);
  }
  return null;
}

async function saveLastBvid(filePath: string, bvid: string): Promise<void> {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(filePath, bvid, 'utf-8');
}

async function runDailyTask(): Promise<void> {
  console.log('========== 开始每日任务 ==========');
  console.log(`时间: ${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}`);

  const config = getConfig();

  // 1. 获取最新视频列表
  console.log(`\n[1/5] 获取 UP 主 ${config.targetUpUid} 的最新视频...`);
  const videos = await getLatestVideos(config.targetUpUid, config.bilibili.sessdata, config.bilibili.bili_jct);

  if (videos.length === 0) {
    console.log('没有找到视频，退出');
    return;
  }

  console.log(`找到 ${videos.length} 个视频`);
  console.log(`最新视频: ${videos[0].title} (${videos[0].bvid})`);

  // 2. 检查是否有新视频
  const lastBvid = await loadLastBvid(config.lastBvidFile);

  // 找最新且未处理过的视频
  let targetVideo = null;
  for (const video of videos) {
    if (video.bvid === lastBvid) break;
    if (isChargedVideo(video)) {
      targetVideo = video;
      break;
    }
  }

  if (!targetVideo) {
    console.log('没有新视频需要处理，退出');
    return;
  }

  console.log(`\n[2/5] 处理视频: ${targetVideo.title}`);

  // 3. 获取视频详情和字幕
  console.log('[3/5] 获取视频详情和字幕...');
  const detail = await getVideoDetail(targetVideo.bvid, config.bilibili.sessdata, config.bilibili.bili_jct);

  const firstCid = detail.pages?.[0]?.cid || 0;
  let subtitleText = '';

  if (firstCid > 0) {
    subtitleText = await getSubtitle(targetVideo.bvid, firstCid, config.bilibili.sessdata, config.bilibili.bili_jct);
  }

  console.log(`字幕长度: ${subtitleText.length} 字符`);

  // 4. 生成总结
  console.log('[4/5] 调用 MiniMax 生成总结...');
  const result = await generateSummary(
    detail.title,
    detail.description + '\n' + detail.dynamic,
    subtitleText,
    config.minimaxApiKey
  );

  console.log('总结生成完成');
  console.log('--- 总结预览 ---');
  console.log(result.summary.substring(0, 200) + '...');
  console.log('--- 预览结束 ---\n');

  // 5. 发送到阿里云
  const publishedAt = new Date(targetVideo.pubdate * 1000).toISOString().replace('T', ' ').substring(0, 10);
  const payload: SummaryPayload = {
    title: detail.title,
    summary: result.summary,
    source: {
      bvid: targetVideo.bvid,
      url: `https://www.bilibili.com/video/${targetVideo.bvid}`,
      up_uid: targetVideo.owner.mid,
      up_name: targetVideo.owner.name,
      published_at: publishedAt,
    },
  };

  console.log('[5/5] 发送到阿里云服务器...');
  await postSummary(payload, config.aliyunApiUrl);

  // 保存已处理的 bvid
  await saveLastBvid(config.lastBvidFile, targetVideo.bvid);

  console.log('\n========== 任务完成 ==========');
}

// 手动触发（用于测试）
async function manualRun(): Promise<void> {
  try {
    await runDailyTask();
  } catch (e) {
    console.error('任务执行失败:', e);
    process.exit(1);
  }
}

// cron 调度
function startCron(): void {
  console.log('启动定时任务 (每天 12:00 北京时间)...');

  // cron 表达式: 分 时 日 月 周
  // 12:00 北京时间 = 04:00 UTC
  cron.schedule('0 4 * * *', async () => {
    try {
      await runDailyTask();
    } catch (e) {
      console.error('定时任务执行失败:', e);
    }
  });

  console.log('定时任务已调度');
}

// 主入口
const mode = process.argv[2] || 'cron';

if (mode === 'now') {
  manualRun();
} else {
  startCron();
  // 保持进程运行
  console.log('Worker 运行中，按 Ctrl+C 退出');
}
```

**验证**：`cat gzh-worker/src/index.ts`

---

### Phase 3: Docker 部署

#### Task 3.1: 创建 Dockerfile

**文件**：`gzh-worker/Dockerfile`

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json ./

RUN npm install --omit=dev && npm cache clean --force

COPY . .

RUN mkdir -p /app/data

CMD ["node", "dist/index.js"]
```

**验证**：`cat gzh-worker/Dockerfile`

---

#### Task 3.2: 创建 docker-compose.yml

**文件**：`gzh-worker/docker-compose.yml`

```yaml
services:
  gzh-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: gzh-worker
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    networks:
      - gzh-worker-net

networks:
  gzh-worker-net:
    driver: bridge
```

**验证**：`cat gzh-worker/docker-compose.yml`

---

### Phase 4: 阿里云 API 扩展

#### Task 4.1: 扩展阿里云 API 端点

**文件**：`src/api/bilibili.ts`（在现有项目中新增）

```typescript
import express from 'express';
import { createDraft, getAccessToken } from './wechat';
import { SummaryPayload } from './types';

const router = express.Router();

router.post('/summary', async (req, res) => {
  try {
    const payload: SummaryPayload = req.body;

    console.log('收到 B站 Worker 总结:', payload.title);

    // 获取 access_token
    const accessToken = await getAccessToken();

    // 获取封面图（暂时用默认封面）
    // TODO: 后续添加封面图上传逻辑

    // 创建草稿
    const result = await createDraft({
      title: payload.title,
      author: payload.source.up_name,
      digest: payload.summary.substring(0, 120),
      content: generateArticleContent(payload),
      thumbMediaId: '', // TODO: 后续添加
      needOpenComment: 1,
      onlyFansCanComment: 0,
    }, accessToken);

    res.json({ success: true, media_id: result.media_id });
  } catch (e: any) {
    console.error('创建草稿失败:', e.message);
    res.status(500).json({ success: false, message: e.message });
  }
});

function generateArticleContent(payload: SummaryPayload): string {
  return `<p>来源：<a href="${payload.source.url}">${payload.source.up_name} - ${payload.title}</a></p>
<p>发布时间：${payload.source.published_at}</p>
<hr/>
<h2>内容总结</h2>
${payload.summary.replace(/\n/g, '<br/>')}
<hr/>
<p>本内容由 AI 根据视频字幕和简介自动生成，仅供学习参考。</p>`;
}

export default router;
```

**验证**：`cat src/api/bilibili.ts`

---

## 执行选项

| 选项 | 说明 |
|------|------|
| **子代理驱动（推荐）** | 启动多个并发 worktree，每个负责一个模块 |
| **内联执行** | 我按顺序逐一执行所有任务 |

---

## 验证步骤

每个模块完成后执行：

```bash
# 本地测试
cd gzh-worker
npm install
npm run dev

# Docker 构建测试
docker compose build
docker compose up -d
docker compose logs -f
```

---

## 注意事项

1. **B 站 Cookie 有效期**：SESSDATA 可能会过期，需要定期重新获取
2. **字幕获取**：部分视频可能没有字幕，会使用简介代替
3. **去重机制**：通过 `last_bvid.txt` 避免重复处理
4. **阿里云 API**：需要确保 `8.134.248.11:3000` 可访问