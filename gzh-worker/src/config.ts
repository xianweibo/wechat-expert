import dotenv from 'dotenv';
import path from 'path';
import { Config } from './types';

dotenv.config({ path: path.join(__dirname, '..', '.env') });

export function getConfig(): Config {
  const sessdata = process.env.BILIBILI_SESSDATA;
  const bili_jct = process.env.BILIBILI_BILI_JCT;
  const uid = parseInt(process.env.BILIBILI_UID || '144796213');
  const targetUpUid = parseInt(process.env.TARGET_UP_UID || '290663424');
  const minimaxApiKey = process.env.MINIMAX_API_KEY;
  const aliyunApiUrl = process.env.ALIYUN_API_URL || 'http://8.134.248.11:3000/api/bilibili/summary';
  const workerSecret = process.env.BILIBILI_WORKER_SECRET || '';
  const lastBvidFile = process.env.LAST_BVID_FILE || '/app/data/last_bvid.txt';

  if (!sessdata || !bili_jct || !minimaxApiKey) {
    throw new Error('Missing required environment variables: BILIBILI_SESSDATA, BILIBILI_BILI_JCT, MINIMAX_API_KEY');
  }

  return {
    bilibili: { sessdata, bili_jct, uid },
    targetUpUid,
    minimaxApiKey,
    aliyunApiUrl,
    workerSecret,
    lastBvidFile,
  };
}