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
- 提取核心要点，分5-8个要点详细展开
- 用通俗易懂的语言
- 不复述原话，用自己语言重构
- 保持中立，不预测涨跌
- 篇幅控制在1000字左右，内容要充实有深度
- 每个要点要有充分的论述和分析，不要只是简单罗列`;

  console.log('[MiniMax] 发送总结请求...');

  return withRetry(async () => {
    const response = await axios.post(
      'https://api.minimaxi.com/anthropic/v1/messages',
      {
        model: 'MiniMax-M2.7',
        max_tokens: 2048,
        messages: [{ role: 'user', content: prompt }],
      },
      {
        headers: {
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'Content-Type': 'application/json',
        },
        timeout: 120000,
      }
    );

    if (response.data.error) {
      throw new Error(`MiniMax API 错误: ${response.data.error.message}`);
    }

    // Anthropic 兼容接口返回 content 数组
    let summary = '';
    const content = response.data.content;
    if (Array.isArray(content)) {
      for (const item of content) {
        if (item.type === 'text') {
          summary = item.text || '';
          break;
        }
      }
    }
    // fallback: OpenAI 格式
    if (!summary) {
      summary = response.data.choices?.[0]?.message?.content || '';
    }
    return { summary, keyPoints: [] };
  }, 'MiniMax');
}