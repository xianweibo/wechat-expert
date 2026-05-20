import axios from 'axios';
import { withRetry } from './types';

export interface SummaryResult {
  summary: string;
  keyPoints: string[];
}

export async function generateSummary(
  title: string,
  description: string,
  subtitleText: string,
  apiKey: string,
  bvid: string
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
- 最后附上原视频链接：https://www.bilibili.com/video/${bvid}`;

  console.log('[MiniMax] 发送总结请求...');

  return withRetry(async () => {
    const response = await axios.post(
      'https://api.minimax.chat/v1/text/chatcompletion_v2',
      {
        model: 'MiniMax-Text-01',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 1000,
        temperature: 0.7,
      },
      {
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        timeout: 60000,
      }
    );

    if (response.data.error) {
      throw new Error(`MiniMax API 错误: ${response.data.error.message}`);
    }

    const summary = response.data.choices?.[0]?.message?.content || '';
    return { summary, keyPoints: [] };
  }, 'MiniMax');
}