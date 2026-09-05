import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';
import * as fs from 'fs';
import mpProxy from './mp_proxy';

// override: 容器 env_file 的值在容器创建时冻结，扫码登录后写入的新 cookie
// 依赖 dotenv 在进程重启时覆盖旧值，否则 docker restart 后仍是过期登录态
dotenv.config({ override: true });

const app = express();
const PORT = process.env.PORT || 3000;

// ---- 环境变量 ----
const MINIMAX_API_KEY = (process.env.MINIMAX_API_KEY || '').trim();
const MINIMAX_HOST = process.env.MINIMAX_HOST || 'api.minimaxi.com';
const MINIMAX_LLM_MODEL = process.env.MINIMAX_LLM_MODEL || 'MiniMax-M3';
const MINIMAX_IMAGE_MODEL = process.env.MINIMAX_IMAGE_MODEL || 'image-01-live';
// 魔搭（ModelScope）API-Inference —— 主出图通道，FLUX 模型
const MOTASCOPE_API_KEY = (process.env.MoTa_API_KEY || '').trim();
const MOTASCOPE_MODEL = process.env.MOTASCOPE_MODEL || 'Tongyi-MAI/Z-Image-Turbo';
const MOTASCOPE_HOST = process.env.MOTASCOPE_HOST || 'api-inference.modelscope.cn';
const GZH_WORKER_SECRET = process.env.GZH_WORKER_SECRET || '';
const DEFAULT_AUTHOR = process.env.DEFAULT_AUTHOR || '小喇叭大只讲';
const STYLE_PATH = (process.env.STYLE_PATH || '').trim();

// ---- 风格档案（启动时加载一次）----
let STYLE_SUMMARY = '';

function loadStyleSummary(): void {
  if (!STYLE_PATH) {
    console.warn('[init] STYLE_PATH 未配置 — 降级到内置 prompt');
    return;
  }
  try {
    if (!fs.existsSync(STYLE_PATH)) {
      console.warn(`[init] 风格档案不存在: ${STYLE_PATH}`);
      return;
    }
    const txt = fs.readFileSync(STYLE_PATH, 'utf8').trim();
    if (txt) {
      STYLE_SUMMARY = txt;
      console.log(`[init] 风格档案已加载: ${STYLE_PATH} (${txt.length} chars)`);
    } else {
      console.warn(`[init] 风格档案为空: ${STYLE_PATH}`);
    }
  } catch (e: any) {
    console.warn(`[init] 读风格档案失败 ${STYLE_PATH}: ${e.message}`);
  }
}

loadStyleSummary();

app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// ---- B 站 SESSDATA 健康检查（手动触发版） ----
app.get('/api/health/session', async (_req, res) => {
  const sessdata = (process.env.BILIBILI_SESSDATA || '').trim();
  const biliJct = (process.env.BILIBILI_BILI_JCT || '').trim();
  if (!sessdata || !biliJct) {
    return res.json({ ok: false, error: 'SESSDATA 或 bili_jct 未配置' });
  }
  try {
    const resp = await fetch('https://api.bilibili.com/x/web-interface/nav', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Cookie': `SESSDATA=${sessdata}; bili_jct=${biliJct}`,
      },
    });
    const data: any = await resp.json();
    res.json({
      ok: data.code === 0 && data.data?.isLogin,
      code: data.code,
      mid: data.data?.mid,
      uname: data.data?.uname,
      level: data.data?.level_info?.current_level,
      vipStatus: data.data?.vipStatus,
      message: data.message,
    });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

app.get('/api/info', (_req, res) => {
  res.json({
    name: '公众号专家',
    version: '0.1.0',
    mode: process.env.NODE_ENV,
  });
});

// ---- mp_proxy 调用辅助 ----
async function callMpProxy(endpoint: string, payload: any): Promise<any> {
  const url = `http://localhost:${PORT}/api/admin/${endpoint}`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Worker-Secret': GZH_WORKER_SECRET,
    },
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

async function fetchBilibiliMeta(bvid: string): Promise<{ title: string; desc: string; cid: number; pubdate: number }> {
  const resp = await callMpProxy('bilibili-check-bvids', { bvids: [bvid] });
  if (!resp || !resp.ok) {
    throw new Error(`bilibili-check-bvids failed: ${JSON.stringify(resp)}`);
  }
  const items = resp.results || resp.items || resp.data || [];
  if (!items.length) {
    throw new Error(`BVID ${bvid} 无数据（视频不存在/已删除/会员限定）`);
  }
  const item = items[0];
  if (item.error) {
    throw new Error(`BVID ${bvid} B 站侧错误: ${item.error}`);
  }
  return {
    title: item.title || '',
    desc: item.desc || '',
    cid: item.cid,
    pubdate: item.pubdate || 0,
  };
}

async function fetchBilibiliSubtitle(bvid: string, cid: number): Promise<string> {
  if (!cid) {
    console.warn(`[subtitle] cid 为空，跳过 bvid=${bvid}`);
    return '';
  }
  try {
    const resp = await callMpProxy('bilibili-subtitle', { bvid, cid: Number(cid) });
    if (!resp || !resp.ok) {
      console.warn(`[subtitle] mp_proxy 返回失败: ${resp && resp.error}`);
      return '';
    }
    const text = resp.subtitle_text || '';
    const needLogin = resp.need_login_subtitle;
    const isUpower = resp.is_upower_exclusive;
    if (text) {
      console.log(`[subtitle] 拿到字幕 ${text.length} chars (bvid=${bvid})`);
    } else if (isUpower) {
      console.warn(`[subtitle] 字幕为空，视频是充电专属（账号未充电或 SESSDATA 无效）bvid=${bvid}`);
    } else if (needLogin) {
      console.warn(`[subtitle] 字幕为空，需要登录（SESSDATA 过期/无效）bvid=${bvid}`);
    } else {
      console.log(`[subtitle] 字幕为空（视频无字幕）bvid=${bvid}`);
    }
    return text;
  } catch (e: any) {
    console.warn(`[subtitle] 拿字幕异常 bvid=${bvid}: ${e.message}`);
    return '';
  }
}

async function uploadCover(coverUrl: string): Promise<string> {
  const fileName = `gzh-cover-${Date.now()}.jpg`;
  const resp = await callMpProxy('mp-material-image-add', { image_url: coverUrl, file_name: fileName });
  if (!resp || !resp.ok) {
    throw new Error(`mp-material-image-add failed: ${JSON.stringify(resp)}`);
  }
  const mediaId = resp.media_id || resp.thumb_media_id;
  if (!mediaId) {
    throw new Error(`mp-material-image-add 无 media_id: ${JSON.stringify(resp)}`);
  }
  console.log('[cover] 封面已上传, media_id:', mediaId);
  return mediaId;
}

async function createDraft(title: string, html: string, thumbMediaId: string, author: string): Promise<string> {
  const resp = await callMpProxy('mp-draft-add', {
    title,
    content: html,
    thumb_media_id: thumbMediaId,
    author,
    digest: '',
  });
  if (!resp || !resp.ok) {
    throw new Error(`mp-draft-add failed: ${JSON.stringify(resp)}`);
  }
  const mediaId = resp.media_id;
  if (!mediaId) {
    throw new Error(`mp-draft-add 无 media_id: ${JSON.stringify(resp)}`);
  }
  console.log('[draft] 草稿已建, media_id:', mediaId);
  return mediaId;
}

// ---- LLM + 封面辅助 ----
async function minimaxChat(prompt: string, maxTokens: number = 8192, timeout: number = 300): Promise<string> {
  if (!MINIMAX_API_KEY) {
    throw new Error('MINIMAX_API_KEY 未配置');
  }
  const url = `https://${MINIMAX_HOST}/v1/text/chatcompletion_v2`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout * 1000);
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${MINIMAX_API_KEY}`,
        'Content-Type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify({
        model: MINIMAX_LLM_MODEL,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: maxTokens,
      }),
      signal: controller.signal,
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`minimax chat HTTP ${resp.status}: ${txt.substring(0, 200)}`);
    }
    const data = await resp.json() as any;
    const baseResp = data.base_resp || {};
    if (baseResp.status_code && baseResp.status_code !== 0) {
      throw new Error(`minimax chat error: ${JSON.stringify(data).substring(0, 300)}`);
    }
    const choices = data.choices || [];
    if (!choices.length) {
      throw new Error(`minimax chat empty choices: ${JSON.stringify(data)}`);
    }
    const text = ((choices[0].message || {}).content || '').trim();
    if (!text) {
      throw new Error(`minimax chat empty content: ${JSON.stringify(data)}`);
    }
    return text;
  } finally {
    clearTimeout(timer);
  }
}

// ---- 内容安全消毒（微信审核高危词硬替换） ----
const SANITIZE_RULES: Array<[RegExp, string]> = [
  [ /(\d{3,5})\s*(最多最多)?的?压力位/g, '$1一带的历史阻力区域' ],
  [ /(\d{3,5})\s*的?支撑位/g, '$1一带的历史支撑区域' ],
  [ /切记[，。]?\s*(空|多|加仓|减仓|清仓|平仓|建仓|满仓)/g, '（历史数据记录，非操作建议）' ],
  [ /(空|多|加仓|减仓|清仓|平仓|建仓|满仓)[，,]?\s*或\s*(\d)\s*层/g, '（仓位仅为历史回测记录）' ],
  [ /或\s*(\d)\s*层/g, '（仓位为历史回测记录）' ],
  [ /(满仓|清仓|all\s?in)/gi, '重仓操作（历史记录）' ],
  [ /去美元化/g, '国际货币格局多元化' ],
  [ /本币结算/g, '非美元货币结算' ],
  [ /替代支付系统/g, '跨境支付新渠道' ],
  [ /关税战/g, '关税调整' ],
  [ /脱钩/g, '供应链调整' ],
  [ /中美对抗/g, '国际经贸博弈' ],
  [ /崩给你看/g, '面临较大调整压力' ],
  [ /雪崩/g, '快速走弱' ],
  [ /崩盘/g, '深度调整' ],
  [ /死给你看/g, '面临出清压力' ],
  [ /完了/g, '承压明显' ],
  [ /刺破泡沫/g, '挤压估值泡沫' ],
  [ /叫你好看/g, '带来调整压力' ],
];

function sanitizeText(text: string): string {
  if (!text) return text;
  let count = 0;
  for (const [pattern, repl] of SANITIZE_RULES) {
    text = text.replace(pattern, (m, ...args) => {
      count++;
      // $1/$2 反向引用在函数形式下需手动展开
      return repl.replace(/\$(\d)/g, (_, d) => (args[Number(d) - 1] !== undefined ? String(args[Number(d) - 1]) : ''));
    });
  }
  if (count) console.log(`[sanitize] replaced ${count} sensitive hits`);
  return text;
}

async function generateSummary(title: string, desc: string, subtitle: string): Promise<string> {
  let styleSection = '';
  if (STYLE_SUMMARY) {
    styleSection = '【你的真实写作口吻档案 — 严格按这个来】\n' + STYLE_SUMMARY + '\n\n';
  }

  let dataSourceSection: string;
  let inputSection: string;
  let lengthSection: string;

  if (subtitle) {
    dataSourceSection =
      '# 数据来源（最重要的事）\n' +
      '- **总结必须完全基于下面提供的视频字幕内容**\n' +
      '- 字幕包含 UP 主的论点、论据、论证和结论，你要把这些提取出来\n' +
      '- **不要**使用任何外部参考链接或论据来源\n' +
      '- **不要**编造字幕里没有的内容\n\n';
    inputSection =
      '# 输入\n' +
      `视频标题：${title}\n` +
      `视频简介：${desc || '（无）'}\n` +
      `字幕内容：\n${subtitle}\n\n`;
    lengthSection =
      '# 长度\n' +
      '- 6-8 个要点\n' +
      '- 每个要点 **150-250 字**，要有论点+论据+论证\n' +
      '- 总长 **1500-2000 字**\n\n';
  } else {
    dataSourceSection =
      '# 最重要的事\n' +
      '- **每篇总结必须紧扣这个视频的具体内容**，不要套用固定模板\n' +
      '- 不同的视频讲不同的话题，总结必须反映这篇视频的独特信息点\n' +
      '- 小标题要跟视频内容相关，不要用通用标题\n\n';
    inputSection =
      '# 输入\n' +
      `视频标题：${title}\n` +
      `视频简介：${desc}\n\n`;
    lengthSection =
      '# 长度\n' +
      '- 5-7 个要点\n' +
      '- 每个要点 **100-200 字**\n' +
      '- 总长 **1000-1500 字**\n\n';
  }

  const prompt =
    styleSection +
    '你正在用上面档案里你自己的真实口吻，给一篇 B 站财经视频做公众号学习总结。\n' +
    '读者是关注公众号的散户朋友，对财经有兴趣但不想看专业内容。\n\n' +
    dataSourceSection +
    '# 内容安全（微信审核红线，违反=封文）\n' +
    '- **禁止**出现具体点位操作指令：如\'到4050就空\'、\'XX点位加仓/清仓\'、\'几成仓位\'这类表述\n' +
    '- **禁止**直接建议买卖方向或仓位：不写\'空\'/\'多\'/\'抄底\'/\'逃顶\'等操作指令\n' +
    '- **禁止**地缘敏感词：去美元化、本币结算、关税战、脱钩、中俄/中美对抗\n' +
    '- **禁止**恐慌性绝对化词汇：崩盘、雪崩、完蛋、经济崩溃、危机爆发\n' +
    '- 涉及风险用中性表述：\'面临调整压力\'、\'存在回落风险\'、\'历史数据显示\'\n\n' +
    '# 风格（自然就好，不要每篇都硬塞同样的套路）\n' +
    '- 第一人称「我」/「我们」/「咱们」\n' +
    '- 口语化，像聊天，但每段 2-3 句合在一起\n' +
    '- 可以偶尔用军事比喻、排比、反问，但**不要每篇都全用上**，看内容是否合适\n' +
    '- 敏感词用拼音或缩写（战z、信x、东方c产）\n' +
    '- **不要**「综上所述」「值得注意的是」「首先...其次...最后」「在当今...背景下」这类 AI 套话\n\n' +
    '# 排版\n' +
    '- 用 `### 标题` 标小标题（每个要点 1 个 `###`，标题要跟内容相关）\n' +
    '- 要点之间**空一行**\n' +
    '- 每段 2-3 句话写在一起\n' +
    '- **每个要点的首句必须用 `**加粗**`**，作为该要点的核心论点/结论，方便读者扫读\n' +
    '- 其余重点句也可用 `**加粗**` 突出\n' +
    '- 末尾 `### 总结` 段落（150-200 字）\n\n' +
    lengthSection +
    inputSection +
    '# 输出\n' +
    "**只**输出最终文本，不要任何开场白（不要'以下是'、'根据视频'等）\n" +
    '**不要**写思考过程\n';

  return await minimaxChat(prompt, 8192, 300);
}

async function rewriteTitle(title: string, desc: string): Promise<string> {
  const prompt =
    '你是公众号标题改写助手。\n' +
    "把以下 B 站视频标题改写为更适合公众号文章的标题，**只输出改写后的标题本身**（不要任何解释、不要思考过程、不要'改写后：'前缀）。\n\n" +
    `原标题: ${title}\n` +
    `简介: ${(desc || '').substring(0, 200)}\n\n` +
    '改写要求：\n' +
    '- 60 字以内\n' +
    '- 突出核心信息\n' +
    "- 去掉期数标签、'《第xxx期》'等冗余\n" +
    '- 不要标题党\n';
  try {
    const text = await minimaxChat(prompt, 2048, 30);
    let cleaned = text.trim();
    // 去掉首尾引号/装饰
    cleaned = cleaned.replace(/^["'「」『』《》]+/, '').replace(/["'「」『』《》]+$/, '').trim();
    // 取第一行
    cleaned = cleaned.split('\n')[0].trim();
    if (!cleaned || cleaned.length > 80 || cleaned === title) {
      console.warn(`[rewrite-title] 输出不可用 (${cleaned})，用原标题`);
      return title;
    }
    console.log(`[rewrite-title] '${title}' -> '${cleaned}'`);
    return cleaned;
  } catch (e: any) {
    console.warn(`[rewrite-title] failed: ${e.message}, use original`);
    return title;
  }
}

async function generateCoverPrompt(title: string, desc: string): Promise<string> {
  const prompt =
    `你是财经媒体封面 prompt 设计师，为魔搭 FLUX 文生图模型写英文 prompt。\n\n` +
    `视频标题：${title}\n` +
    `视频简介：${(desc || '').substring(0, 300)}\n\n` +
    `要求：\n` +
    `- **先拆解标题中的所有核心概念**（通常 2-4 个），在 prompt 开头用 'Concepts: concept1 (visual1), concept2 (visual2), ...' 列出\n` +
    `- 为每个核心概念设计对应的视觉元素，组合成一个连贯的画面（不是孤立罗列）\n` +
    `- prompt 100-200 词英文，必须覆盖标题所有概念，不能只画最显眼的一个\n` +
    `- 画面构图：多个视觉元素分层组合（前景/中景/背景），元素之间有视觉关联\n` +
    `- 风格：财经媒体编辑插图（Bloomberg/Reuters/WSJ 风格），深色背景，高对比数据可视化\n` +
    `- 配色：深蓝/炭黑背景 + A股配色（crimson red for rising/up, emerald green for falling/down）\n` +
    `- 概念视觉化示例（参考，不要照抄）：\n` +
    `  '加息' → upward-spiraling yield curve with glowing red trajectory;\n` +
    `      '按兵不动' → frozen pause icon + flatlined interest rate gauge;\n` +
    `      '两难困境' → split-screen dual-path composition balanced on pivot scale;\n` +
    `      '市场观望' → sideways sentiment indicator with hesitation arrows;\n` +
    `      '暴跌' → cascading plunging red candlesticks;\n` +
    `      '央行' → central bank building silhouette with data overlay;\n` +
    `      '通胀' → upward pressure gauge with red warning indicators\n` +
    `- 16:9 构图，画面右侧或顶部预留标题区域（但不画文字、不画水印）\n` +
    `- 避免：anime 卡通、金色 candlestick + 上升箭头模板、城市天际线、自然风景、生活化物件、人脸、旗帜、政治符号、武器\n` +
    `- FLUX 友好：描述具体、画面感强、光影细节丰富\n\n` +
    `输出格式：只输出 prompt 本身（含 Concepts: 行），不要任何解释、不要 "Here is..." 开场。`;
  try {
    const text = await minimaxChat(prompt, 2048, 60);
    let cleaned = text.trim().replace(/^["'「」『』《》]+/, '').replace(/["'「」『』《》]+$/, '').trim();
    cleaned = cleaned.split('\n\n')[0].trim();
    // FLUX 是英文 prompt，长度 > 50 词即可
    if (cleaned && /[a-zA-Z]/.test(cleaned) && cleaned.length > 50) {
      console.log('[cover-prompt] generated:', cleaned);
      return cleaned;
    }
    console.warn('[cover-prompt] LLM 输出不可用,用降级 prompt');
  } catch (e: any) {
    console.warn(`[cover-prompt] failed: ${e.message}, 用降级 prompt`);
  }
  // 降级 prompt（多概念视觉化示例，财经媒体编辑插图风格）
  return (
    'Concepts: market pause (frozen gauge), dual dilemma (split composition), wait-and-see sentiment (sideways indicator). ' +
    'Editorial financial media cover illustration. Deep navy background with high-contrast data visualization. ' +
    'Foreground: a frozen pause icon overlaying a flatlined federal funds interest rate gauge with crimson red frozen needle. ' +
    'Midground: split-screen dilemma composition showing two divergent paths (upward red arrows vs downward green arrows) ' +
    'balanced on a pivot scale. Background: sideways market sentiment indicator with hesitation arrows pointing horizontally, ' +
    'subtle grid lines and tick marks. Bottom-right negative space reserved for title. ' +
    'Cinematic lighting, photorealistic data terminal aesthetic, 16:9 aspect ratio, no text, no watermark, ' +
    'no human faces, no flags, no anime style.'
  );
}

async function generateCoverImage(prompt: string): Promise<string> {
  const url = 'https://api.minimaxi.com/v1/image_generation';
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${MINIMAX_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: MINIMAX_IMAGE_MODEL,
        prompt,
        aspect_ratio: '16:9',
        response_format: 'url',
        n: 1,
      }),
      signal: controller.signal,
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`image-01-live HTTP ${resp.status}: ${txt.substring(0, 200)}`);
    }
    const obj = await resp.json() as any;
    const baseResp = obj.base_resp || {};
    if ((baseResp.status_code || 0) !== 0) {
      throw new Error(`image-01-live error: ${JSON.stringify(baseResp)}`);
    }
    const urls = (obj.data || {}).image_urls || [];
    if (!urls.length) {
      throw new Error(`image-01-live no urls: ${JSON.stringify(obj)}`);
    }
    console.log('[cover-image] 生成成功:', urls[0].substring(0, 80) + '...');
    return urls[0];
  } finally {
    clearTimeout(timer);
  }
}

// 魔搭（ModelScope）FLUX 文生图 —— 异步任务模式
// 1. POST /v1/images/generations 拿 task_id（X-ModelScope-Async-Mode: true）
// 2. GET /v1/tasks/{task_id} 轮询（X-ModelScope-Task-Type: image_generation）
// 3. task_status === "SUCCEED" → 返回 output_images[0]
async function generateCoverImageModelScope(prompt: string): Promise<string> {
  if (!MOTASCOPE_API_KEY) {
    throw new Error('MOTASCOPE_API_KEY 未配置（环境变量 MoTa_API_KEY）');
  }
  const baseUrl = `https://${MOTASCOPE_HOST}`;
  const createUrl = `${baseUrl}/v1/images/generations`;

  // 1. 提交文生图任务
  const createController = new AbortController();
  const createTimer = setTimeout(() => createController.abort(), 30000);
  let taskId: string;
  try {
    const createResp = await fetch(createUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${MOTASCOPE_API_KEY}`,
        'Content-Type': 'application/json',
        'X-ModelScope-Async-Mode': 'true',
      },
      body: JSON.stringify({
        model: MOTASCOPE_MODEL,
        prompt,
        size: '1024x576',
        negative_prompt:
          'anime, cartoon, golden candlestick with up arrow template, city skyline, natural landscape, ' +
          'daily life objects, office desk, coffee, teacup, plant, notebook, human faces, flags, ' +
          'political symbols, weapons, text, watermark',
        seed: Math.floor(Math.random() * 1000000),
        steps: 30,
      }),
      signal: createController.signal,
    });
    if (!createResp.ok) {
      const txt = await createResp.text();
      throw new Error(`modelscope create HTTP ${createResp.status}: ${txt.substring(0, 200)}`);
    }
    const createObj = await createResp.json() as any;
    taskId = createObj.task_id;
    if (!taskId) {
      throw new Error(`modelscope create no task_id: ${JSON.stringify(createObj).substring(0, 300)}`);
    }
    console.log(`[modelscope] task_id=${taskId}`);
  } finally {
    clearTimeout(createTimer);
  }

  // 2. 轮询任务状态，每 5 秒一次，最多 48 次（240 秒超时）
  const pollUrl = `${baseUrl}/v1/tasks/${taskId}`;
  const maxAttempts = 48;
  const intervalMs = 5000;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    // 至少等 5 秒再发起下一次轮询（首次也等，给模型出图时间）
    await new Promise((resolve) => setTimeout(resolve, intervalMs));

    const pollController = new AbortController();
    const pollTimer = setTimeout(() => pollController.abort(), 30000);
    try {
      const pollResp = await fetch(pollUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${MOTASCOPE_API_KEY}`,
          'X-ModelScope-Task-Type': 'image_generation',
        },
        signal: pollController.signal,
      });
      if (!pollResp.ok) {
        const txt = await pollResp.text();
        console.warn(`[modelscope] poll HTTP ${pollResp.status}: ${txt.substring(0, 150)}`);
        continue;
      }
      const pollObj = await pollResp.json() as any;
      const status = pollObj.task_status;
      console.log(`[modelscope] poll #${attempt + 1}/${maxAttempts} status=${status || 'UNKNOWN'}`);

      if (status === 'SUCCEED') {
        const images: string[] = pollObj.output_images || [];
        if (!images.length) {
          throw new Error(`modelscope SUCCEED 但无 output_images: ${JSON.stringify(pollObj).substring(0, 300)}`);
        }
        console.log('[modelscope] 出图成功:', images[0].substring(0, 80) + '...');
        return images[0];
      }
      if (status === 'FAILED') {
        throw new Error(`modelscope task FAILED: ${JSON.stringify(pollObj).substring(0, 300)}`);
      }
      // PENDING / UNKNOWN → 继续轮询
    } catch (e: any) {
      // 轮询单次失败不立即终止，除非是 FAILED 状态抛的
      if (e.message && e.message.includes('modelscope task FAILED')) {
        throw e;
      }
      console.warn(`[modelscope] poll #${attempt + 1} 异常: ${e.message}`);
    } finally {
      clearTimeout(pollTimer);
    }
  }
  throw new Error(`modelscope 轮询超时（${maxAttempts * intervalMs / 1000}s），task_id=${taskId}`);
}

// 封面总入口：先魔搭 FLUX，失败回退 MiniMax image-01-live
async function generateCover(title: string, desc: string): Promise<string> {
  const prompt = await generateCoverPrompt(title, desc);
  console.log(`[cover] prompt: ${prompt.substring(0, 80)}...`);

  // 1. 优先魔搭
  if (MOTASCOPE_API_KEY) {
    try {
      const url = await generateCoverImageModelScope(prompt);
      console.log('[cover] 走魔搭 FLUX 出图成功');
      return url;
    } catch (e: any) {
      console.warn(`[cover] 魔搭失败，回退 MiniMax: ${e.message}`);
    }
  } else {
    console.warn('[cover] MOTASCOPE_API_KEY 未配置，直接走 MiniMax');
  }

  // 2. 回退 MiniMax
  if (MINIMAX_API_KEY) {
    const url = await generateCoverImage(prompt);
    console.log('[cover] 走 MiniMax image-01-live 出图成功');
    return url;
  }

  // 3. 两个 key 都没有
  throw new Error('封面生成失败：MOTASCOPE_API_KEY 和 MINIMAX_API_KEY 均未配置');
}

// ---- HTML 构造 ----
function extractFyi(desc: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const re = /https?:\/\/[^\s<>\u4e00-\u9fff]+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(desc || '')) !== null) {
    const url = m[0].replace(/[，。,.;；:：!！?？)）」』]+$/, '');
    if (!seen.has(url)) {
      seen.add(url);
      out.push(url);
    }
  }
  return out;
}

function summaryToHtml(summary: string): string {
  const lines = summary.split('\n');
  const outParts: string[] = [];
  let paraBuf: string[] = [];

  const flushPara = () => {
    if (paraBuf.length === 0) return;
    let text = paraBuf.join(' ').trim();
    paraBuf = [];
    if (!text) return;
    const hasBold = text.includes('**');
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // 若 LLM 没加粗，自动给首句加粗（首句 = 到第一个句末标点为止）
    if (!hasBold) {
      const m = text.match(/^(.*?[。！？\?])/);
      if (m && m[1]) {
        const first = m[1];
        const rest = text.substring(first.length);
        text = `<strong>${first}</strong>${rest}`;
      }
    }
    outParts.push(`<p>${text}</p>`);
    outParts.push('<p></p>');
  };

  for (const line of lines) {
    const s = line.trim();
    if (s.startsWith('### ')) {
      flushPara();
      outParts.push(`<h3>${s.substring(4).trim()}</h3>`);
      continue;
    }
    if (s.startsWith('## ')) {
      flushPara();
      outParts.push(`<h2>${s.substring(3).trim()}</h2>`);
      continue;
    }
    if (s.startsWith('# ')) {
      flushPara();
      outParts.push(`<h2>${s.substring(2).trim()}</h2>`);
      continue;
    }
    if (s === '') {
      flushPara();
      continue;
    }
    paraBuf.push(s);
  }
  flushPara();
  // 去掉末尾多余空行
  while (outParts.length > 0 && outParts[outParts.length - 1] === '<p></p>') {
    outParts.pop();
  }
  return outParts.join('');
}

function buildHtml(summary: string, fyiLinks: string[], title: string): string {
  let fyiHtml = '';
  if (fyiLinks.length > 0) {
    const fyiParts: string[] = [
      '<p></p>',
      '<p><strong>FYI</strong></p>',
      '<p></p>',
    ];
    fyiLinks.forEach((url, i) => {
      fyiParts.push(`<p>[${i + 1}] <a href="${url}">${url}</a></p>`);
    });
    fyiHtml = fyiParts.join('');
  }

  const bodyHtml = summaryToHtml(summary);

  // 顶部声明块：3 行加粗声明 + 3 空 + --- + 1 空（不含"没想到啊..."）
  const top =
    '<p><strong>内容不作为投资建议，注意风险。</strong><br/>' +
    '<strong>都是历史数据，仅作为学习。</strong><br/>' +
    '<strong>独立学者：</strong></p>' +
    '<p></p><p></p><p></p>' +
    '<p>---</p>' +
    '<p></p>';

  // 底部声明块
  const bottom =
    '<p></p>' +
    '<p>---</p>' +
    '<p></p>' +
    '<p>Make you greate again！</p>' +
    '<p></p>' +
    '<p>=======</p>' +
    '<p>=</p>' +
    '<p>以下不是建议<br/>' +
    '只是根据历史数据,量化模式回测<br/>' +
    '都是历史数据和我本人的记录，不作为建议荐股！！！<br/>' +
    '每天都更新，仅供学习</p>' +
    '<p>=</p>' +
    '<p>=======</p>' +
    '<p>PS：<br/>' +
    '最后的最后<br/>' +
    '不指导、不建议、不入群，都是前一天历史数据分析，根据量化模型回测出来，不构成投资建议。<br/>' +
    '股市有风险，投资需谨慎<br/>' +
    '股票池：<br/>' +
    '以下的都是公司企业，不是股票推荐</p>';

  return top + bodyHtml + fyiHtml + bottom;
}

// ---- POST /api/bilibili/summary ----
// 幂等缓存：bvid → media_id。推送方超时重试会导致重复建草稿，这里按 bvid 去重
const processedBvids = new Map<string, string>();

function rememberDraft(key: string, mediaId: string): void {
  processedBvids.set(key, mediaId);
  if (processedBvids.size > 100) {
    const oldest = processedBvids.keys().next().value;
    if (oldest) processedBvids.delete(oldest);
  }
}

app.post('/api/bilibili/summary', async (req, res) => {
  const workerSecret = req.headers['x-worker-secret'];
  if (!GZH_WORKER_SECRET || workerSecret !== GZH_WORKER_SECRET) {
    res.status(401).json({ success: false, message: 'Unauthorized' });
    return;
  }

  const body = req.body || {};
  const bvid: string = (body.bvid || '').trim();
  const dedupKey: string = bvid || (body.source?.bvid || '').trim();

  if (dedupKey && processedBvids.has(dedupKey)) {
    const mediaId = processedBvids.get(dedupKey)!;
    console.log(`[summary] 幂等命中 bvid=${dedupKey}，返回已有草稿 ${mediaId}`);
    res.json({ success: true, media_id: mediaId, deduplicated: true });
    return;
  }

  // ---- 新流程：body 含 bvid ----
  if (bvid) {
    try {
      console.log(`[summary] 新流程开始 bvid=${bvid}`);

      console.log('[summary] 1. 拉取 B 站元数据...');
      const meta = await fetchBilibiliMeta(bvid);
      const { title, desc, cid } = meta;
      console.log(`[summary] 标题: ${title}, cid: ${cid}`);

      console.log('[summary] 2. 拉取字幕...');
      const subtitle = await fetchBilibiliSubtitle(bvid, cid);
      if (subtitle) {
        console.log(`[summary] 字幕长度: ${subtitle.length}`);
      } else {
        console.log('[summary] 字幕为空，降级用 title+desc');
      }

      console.log('[summary] 3. 生成总结...');
      const summary = sanitizeText(await generateSummary(title, desc, subtitle));
      console.log(`[summary] 总结长度: ${summary.length}`);

      console.log('[summary] 4. 改写标题...');
      const draftTitle = sanitizeText(await rewriteTitle(title, desc));
      console.log(`[summary] 改写后标题: ${draftTitle}`);

      console.log('[summary] 5. 生成封面 prompt + 魔搭出图...');
      const coverUrl = await generateCover(title, desc);
      console.log(`[summary] 封面 URL: ${coverUrl.substring(0, 80)}...`);

      console.log('[summary] 6. 上传封面到公众号素材库...');
      const thumbMediaId = await uploadCover(coverUrl);

      console.log('[summary] 7. 提取 FYI 链接...');
      const fyiLinks = extractFyi(desc);
      console.log(`[summary] FYI 链接: ${fyiLinks.length} 个`);

      console.log('[summary] 8. 构造 HTML...');
      const html = buildHtml(summary, fyiLinks, draftTitle);
      console.log(`[summary] HTML 长度: ${html.length}`);

      console.log('[summary] 9. 建草稿...');
      const mediaId = await createDraft(draftTitle, html, thumbMediaId, DEFAULT_AUTHOR);

      console.log(`[summary] 完成 media_id=${mediaId}`);
      if (dedupKey) rememberDraft(dedupKey, mediaId);
      res.json({ success: true, media_id: mediaId });
    } catch (e: any) {
      console.error('[summary] 失败:', e.message);
      res.status(500).json({ success: false, message: e.message });
    }
    return;
  }

  // ---- 降级模式：body 无 bvid 但有 title/summary ----
  const title: string = body.title || '';
  const summary: string = body.summary || '';
  if (!title || !summary) {
    res.status(400).json({
      success: false,
      message: '需要提供 bvid（新流程）或 title+summary（降级模式）',
    });
    return;
  }

  try {
    console.log(`[summary] 降级模式 title=${title}`);

    // 优先魔搭，魔搭 key 缺失时回退 MiniMax；两者都没配置才报错
    if (!MOTASCOPE_API_KEY && !MINIMAX_API_KEY) {
      res.status(400).json({
        success: false,
        message: '降级模式未配置封面通道（MOTASCOPE_API_KEY 和 MINIMAX_API_KEY 均缺失）',
      });
      return;
    }

    console.log('[summary] 降级: 生成封面（魔搭优先，MiniMax 兜底）...');
    const coverUrl = await generateCover(title, body.desc || '');
    const thumbMediaId = await uploadCover(coverUrl);

    const fyiLinks = extractFyi(body.desc || '');
    const html = buildHtml(summary, fyiLinks, title);
    const mediaId = await createDraft(title, html, thumbMediaId, DEFAULT_AUTHOR);

    console.log(`[summary] 降级完成 media_id=${mediaId}`);
    if (dedupKey) rememberDraft(dedupKey, mediaId);
    res.json({ success: true, media_id: mediaId });
  } catch (e: any) {
    console.error('[summary] 降级失败:', e.message);
    res.status(500).json({ success: false, message: e.message });
  }
});

app.use('/api/admin', mpProxy);

// ---- B 站 SESSDATA 保鲜定时任务 ----
// 每 6 小时调一次 /x/web-interface/nav，让 B 站服务端认为该 SESSDATA 仍在活跃使用，避免被吊销
const SESSION_KEEPALIVE_INTERVAL_MS = 6 * 60 * 60 * 1000; // 6 小时

/**
 * 保鲜任务检测到 SESSDATA 失效时推送告警。
 * 支持 Server酱（推荐，国内个人用）和飞书 webhook（团队用）。
 * 通过环境变量配置，未配置则只写日志。
 * 同时去重：同一个容器启动周期内不重复推送相同告警。
 */
let lastAlertType: string = '';
let lastAlertTime: number = 0;
const ALERT_DEDUP_MS = 6 * 60 * 60 * 1000; // 6 小时内同类型不重复推

async function notifySessionAlert(payload: {
  type: 'unlogin' | 'network_error';
  mid?: number;
  code?: number;
  message?: string;
  error?: string;
}): Promise<void> {
  // 去重
  const now = Date.now();
  if (payload.type === lastAlertType && (now - lastAlertTime) < ALERT_DEDUP_MS) {
    console.log(`[alert] 重复告警去重: type=${payload.type} 距上次 ${Math.round((now - lastAlertTime) / 60000)} 分钟`);
    return;
  }

  const time = new Date().toISOString().replace('T', ' ').substring(0, 19);
  let body = `⚠️ B 站 SESSDATA 失效\n\n时间: ${time} (UTC)\n容器: gzh-expert-app (8.134.248.11)\n`;
  if (payload.type === 'unlogin') {
    body += `原因: 账号未登录 (B站code=${payload.code}, msg=${payload.message})\n`;
  } else {
    body += `原因: 网络错误 (${payload.error})\n`;
  }
  body += `\n请访问 NAS 管理面板扫码重登:\nhttp://<NAS_IP>:41091/\n\n或手动复制 cookie 更新阿里云 .env 后重启容器`;

  const serverChanKey = (process.env.SERVERCHAN_SENDKEY || '').trim();
  const feishuWebhook = (process.env.FEISHU_WEBHOOK_URL || '').trim();

  let sent = false;

  // 优先 Server酱
  if (serverChanKey) {
    try {
      const r = await fetch(`https://sctapi.ftqq.com/${serverChanKey}.send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'B站登录态失效', desp: body }),
      });
      const j: any = await r.json();
      if (j.code === 0) {
        console.log('[alert] ✅ Server酱 推送成功');
        sent = true;
      } else {
        console.warn(`[alert] ⚠️ Server酱 推送失败: ${j.message}`);
      }
    } catch (e: any) {
      console.warn(`[alert] Server酱 调用异常: ${e.message}`);
    }
  }

  // 兜底飞书
  if (!sent && feishuWebhook) {
    try {
      const r = await fetch(feishuWebhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msg_type: 'text', content: { text: body } }),
      });
      const j: any = await r.json();
      if (j.StatusCode === 0 || j.code === 0) {
        console.log('[alert] ✅ 飞书 webhook 推送成功');
        sent = true;
      } else {
        console.warn(`[alert] ⚠️ 飞书 webhook 推送失败: ${JSON.stringify(j)}`);
      }
    } catch (e: any) {
      console.warn(`[alert] 飞书 webhook 调用异常: ${e.message}`);
    }
  }

  if (!sent) {
    console.warn(`[alert] 没有配置任何推送通道 (SERVERCHAN_SENDKEY 或 FEISHU_WEBHOOK_URL)，只写日志`);
  }

  lastAlertType = payload.type;
  lastAlertTime = now;
}

async function keepaliveBilibiliSession(): Promise<void> {
  const sessdata = (process.env.BILIBILI_SESSDATA || '').trim();
  const biliJct = (process.env.BILIBILI_BILI_JCT || '').trim();
  if (!sessdata || !biliJct) {
    console.warn('[keepalive] SESSDATA 或 bili_jct 未配置，跳过保鲜');
    return;
  }
  try {
    const resp = await fetch('https://api.bilibili.com/x/web-interface/nav', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Cookie': `SESSDATA=${sessdata}; bili_jct=${biliJct}`,
      },
    });
    const data: any = await resp.json();
    if (data.code === 0 && data.data && data.data.isLogin) {
      const mid = data.data.mid;
      const uname = data.data.uname;
      const level = data.data.level_info?.current_level;
      console.log(`[keepalive] ✅ SESSDATA 有效 mid=${mid} uname=${uname} level=${level} next_run=6h`);
      // 已恢复正常：清除告警去重标记，下次失效可立即重新告警
      if (lastAlertType) {
        console.log('[keepalive] 已恢复，清除告警去重标记');
        lastAlertType = '';
        lastAlertTime = 0;
      }
    } else {
      console.warn(`[keepalive] ⚠️ SESSDATA 失效或未登录 code=${data.code} message=${data.message}`);
      // 推送告警
      await notifySessionAlert({
        type: 'unlogin',
        mid: data.data?.mid,
        code: data.code,
        message: data.message,
      });
    }
  } catch (e: any) {
    console.error(`[keepalive] 调用失败: ${e.message}`);
    await notifySessionAlert({
      type: 'network_error',
      error: e.message,
    });
  }
}

// 启动 30 秒后第一次（便于健康检查立刻看到结果，且方便 e2e 测试）
setTimeout(() => keepaliveBilibiliSession(), 30_000);
// 然后每 6 小时跑一次
setInterval(keepaliveBilibiliSession, SESSION_KEEPALIVE_INTERVAL_MS);
console.log('[init] B 站 SESSDATA 保鲜定时任务已启动（每 6 小时）');

app.listen(PORT, '0.0.0.0', () => {
  console.log(`公众号专家 API 运行在 http://0.0.0.0:${PORT}`);
});