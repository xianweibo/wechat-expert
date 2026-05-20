import axios from 'axios';
import { SummaryPayload } from './types';

export async function postSummary(
  payload: SummaryPayload,
  apiUrl: string,
  workerSecret: string
): Promise<void> {
  console.log('[Poster] 发送到阿里云服务器:', apiUrl);

  const response = await axios.post(apiUrl, payload, {
    headers: { 
      'Content-Type': 'application/json',
      'X-Worker-Secret': workerSecret
    },
    timeout: 30000,
  });

  if (response.data.success) {
    console.log('[Poster] ✅ 发送成功');
  } else {
    throw new Error(`发送失败: ${response.data.message}`);
  }
}