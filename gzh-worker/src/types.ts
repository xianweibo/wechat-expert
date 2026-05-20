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
  stat?: {
    view: number;
    like: number;
    coin: number;
    favorite: number;
    share: number;
    reply: number;
  };
  rights?: {
    is_cooperation?: number;
    is_charging_arc?: number;
    no_background?: number;
  };
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

export interface Subtitle {
  id: number;
  lan: string;
  lan_doc: string;
  subtitle_url: string;
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
  workerSecret: string;
  lastBvidFile: string;
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  label: string,
  maxRetries: number = 2
): Promise<T> {
  let lastError: Error | null = null;
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      return await fn();
    } catch (e: any) {
      lastError = e;
      if (attempt <= maxRetries) {
        const delay = attempt * 2000;
        console.warn(`[${label}] 第 ${attempt} 次失败，${delay}ms 后重试: ${e.message}`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  throw lastError!;
}