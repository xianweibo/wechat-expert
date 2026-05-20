import cron from 'node-cron';
import fs from 'fs';
import path from 'path';
import { getConfig } from './config';
import { getLatestVideos, getVideoDetail, getSubtitle } from './bilibili';
import { generateSummary } from './minimax';
import { postSummary } from './poster';
import { SummaryPayload } from './types';

async function loadLastBvid(filePath: string): Promise<string | null> {
  try {
    if (fs.existsSync(filePath)) {
      return fs.readFileSync(filePath, 'utf-8').trim();
    }
  } catch (e) {
    console.warn('[Storage] 读取 last_bvid 失败:', e);
  }
  return null;
}

async function saveLastBvid(filePath: string, bvid: string): Promise<void> {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(filePath, bvid, 'utf-8');
  console.log(`[Storage] 已保存 bvid: ${bvid}`);
}

async function runDailyTask(): Promise<void> {
  console.log('========== 开始每日任务 ==========');
  console.log(`时间: ${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}`);

  const config = getConfig();

  console.log(`[1/5] 获取 UP 主 ${config.targetUpUid} 的最新视频...`);
  const videos = await getLatestVideos(config.targetUpUid, config.bilibili.sessdata, config.bilibili.bili_jct);

  if (videos.length === 0) {
    console.log('[BiliBili] 没有找到视频，退出');
    return;
  }

  console.log(`[BiliBili] 找到 ${videos.length} 个视频`);
  console.log(`[BiliBili] 最新视频: ${videos[0].title} (${videos[0].bvid})`);

  const lastBvid = await loadLastBvid(config.lastBvidFile);

  let targetVideo = null;
  for (const video of videos) {
    if (video.bvid === lastBvid) break;
    targetVideo = video;
    break;
  }

  if (!targetVideo) {
    console.log('[BiliBili] 没有新视频需要处理，退出');
    return;
  }

  console.log(`\n[2/5] 处理视频: ${targetVideo.title}`);

  console.log('[3/5] 获取视频详情和字幕...');
  const detail = await getVideoDetail(targetVideo.bvid, config.bilibili.sessdata, config.bilibili.bili_jct);

  const firstCid = detail.pages?.[0]?.cid || 0;
  let subtitleText = '';

  if (firstCid > 0) {
    subtitleText = await getSubtitle(targetVideo.bvid, firstCid, config.bilibili.sessdata, config.bilibili.bili_jct);
  }

  console.log(`[BiliBili] 字幕长度: ${subtitleText.length} 字符`);

  console.log('[4/5] 调用 MiniMax 生成总结...');
  const result = await generateSummary(detail.title, detail.description + '\n' + detail.dynamic, subtitleText, config.minimaxApiKey, targetVideo.bvid);

  console.log('--- 总结预览 ---');
  console.log(result.summary.substring(0, 200) + '...');
  console.log('--- 预览结束 ---\n');

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
  await postSummary(payload, config.aliyunApiUrl, config.workerSecret);

  await saveLastBvid(config.lastBvidFile, targetVideo.bvid);

  console.log('\n========== 任务完成 ==========');
}

async function manualRun(): Promise<void> {
  try {
    await runDailyTask();
  } catch (e: any) {
    console.error('❌ 任务执行失败:', e.message);
    process.exit(1);
  }
}

function startCron(): void {
  console.log('[Cron] 启动定时任务 (每天 12:00 北京时间)...');
  cron.schedule('0 4 * * *', async () => {
    try {
      await runDailyTask();
    } catch (e: any) {
      console.error('❌ 定时任务执行失败:', e.message);
    }
  });
  console.log('[Cron] 定时任务已调度');
}

const mode = process.argv[2] || 'cron';

if (mode === 'now') {
  manualRun();
} else {
  startCron();
  console.log('[Worker] 运行中，按 Ctrl+C 退出');
}

export { runDailyTask };