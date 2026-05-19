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
  lastBvidFile: string;
}