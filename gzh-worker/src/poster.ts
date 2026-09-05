import axios from 'axios';
import { SummaryPayload, withRetry } from './types';

export async function postSummary(
  payload: SummaryPayload,
  apiUrl: string,
  workerSecret: string
): Promise<void> {
  console.log('[Poster] 发送到阿里云服务器:', apiUrl);

  await withRetry(async () => {
    const response = await axios.post(apiUrl, payload, {
      headers: {
        'Content-Type': 'application/json',
        'X-Worker-Secret': workerSecret,
      },
      // 阿里云端要现做封面（魔搭出图最长约 4 分钟）+ 建草稿，30s 必超时导致重试重复建草稿
      timeout: 420000,
    });

    if (!response.data.success) {
      throw new Error(`发送失败: ${response.data.message}`);
    }

    console.log('[Poster] ✅ 发送成功');
  }, 'Poster');
}