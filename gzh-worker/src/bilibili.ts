import axios, { AxiosHeaders } from 'axios';
import { BilibiliVideo, VideoDetail } from './types';

const BILIBILI_API = 'https://api.bilibili.com';

function buildHeaders(sessdata: string, bili_jct: string): Record<string, string> {
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
  const headers = buildHeaders(sessdata, bili_jct);

  const urls = [
    `${BILIBILI_API}/x/space/wbi/arc/search?mid=${uid}&pn=1&ps=10&order=pubdate&jsonp=jsonp`,
    `${BILIBILI_API}/x/space/arc/search?mid=${uid}&pn=1&ps=10&order=pubdate&jsonp=jsonp`,
  ];

  for (const url of urls) {
    try {
      console.log(`[BiliBili] 请求: ${url}`);
      const response = await axios.get(url, { headers, timeout: 10000 });
      const data = response.data;

      if (data.code === 0 && data.data?.list?.vlist) {
        console.log(`[BiliBili] 成功获取 ${data.data.list.vlist.length} 个视频`);
        return data.data.list.vlist;
      }

      console.log(`[BiliBili] API 返回: code=${data.code}, msg=${data.message}`);
    } catch (e: any) {
      console.warn(`[BiliBili] 请求失败: ${e.message}`);
    }
  }

  throw new Error('无法获取B站视频列表');
}

export async function getVideoDetail(
  bvid: string,
  sessdata: string,
  bili_jct: string
): Promise<VideoDetail> {
  const headers = buildHeaders(sessdata, bili_jct);
  const url = `${BILIBILI_API}/x/web-interface/view?bvid=${bvid}`;

  console.log(`[BiliBili] 获取视频详情: ${bvid}`);
  const response = await axios.get(url, { headers, timeout: 10000 });

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
  const headers = buildHeaders(sessdata, bili_jct);
  const url = `${BILIBILI_API}/x/player/v2?bvid=${bvid}&cid=${cid}`;

  console.log(`[BiliBili] 获取字幕: ${bvid}, cid=${cid}`);
  const response = await axios.get(url, { headers, timeout: 10000 });

  if (response.data.code !== 0) {
    console.warn(`[BiliBili] 获取字幕失败: ${response.data.message}`);
    return '';
  }

  const subtitles = response.data.data?.subtitle?.subtitles || [];

  if (subtitles.length === 0) {
    console.log('[BiliBili] 没有字幕');
    return '';
  }

  const subtitleInfo = subtitles[0];
  const subtitleUrl = subtitleInfo.subtitle_url;

  if (!subtitleUrl) {
    console.log('[BiliBili] 字幕URL为空');
    return '';
  }

  console.log(`[BiliBili] 下载字幕: ${subtitleUrl}`);

  try {
    const subHeaders = {
      ...headers,
      'Referer': `https://www.bilibili.com/video/${bvid}`,
    };
    const subResponse = await axios.get(subtitleUrl, { headers: subHeaders, timeout: 10000 });
    return parseSubtitle(subResponse.data);
  } catch (e: any) {
    console.warn(`[BiliBili] 字幕下载失败: ${e.message}`);
    return '';
  }
}

function parseSubtitle(content: any): string {
  if (typeof content !== 'object' || !content.body) {
    return '';
  }

  const lines: string[] = [];

  for (const item of content.body) {
    if (item.i || item.content) {
      const text = (item.i || item.content || '').trim();
      if (text) {
        lines.push(text);
      }
    }
  }

  return lines.join('\n');
}

export function isChargedVideo(video: BilibiliVideo): boolean {
  return true;
}