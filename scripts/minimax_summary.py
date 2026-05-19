import requests
import json
import sys

API_KEY = "sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo"
API_URL = "https://api.minimaxi.com/anthropic/v1/messages"

with open("/tmp/subtitle-clean.txt", "r", encoding="utf-8") as f:
    subtitle = f.read()

prompt = f"""请根据以下B站视频字幕，生成一段适合公众号发布的精华总结。

要求：
1. 提取核心要点，3-5条
2. 用通俗易懂的语言，不复述原话，用自己的语言重构
3. 保持中立，不预测涨跌
4. 篇幅控制在300字以内
5. 适合财经/新闻类公众号读者

字幕内容：
{subtitle}

请直接输出总结内容，不要有前缀说明。"""

headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}

data = {
    "model": "MiniMax-M2.7",
    "max_tokens": 800,
    "messages": [{"role": "user", "content": prompt}]
}

print("正在调用 MiniMax API...")
resp = requests.post(API_URL, headers=headers, json=data, timeout=120)

if resp.status_code == 200:
    result = resp.json()
    # Extract text from content array
    summary = ""
    for item in result.get("content", []):
        if item.get("type") == "text":
            summary = item.get("text", "")
            break

    print("\n=== 总结 ===")
    print(summary)

    with open("/tmp/summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)
    print("\n总结已保存到 /tmp/summary.txt")
else:
    print(f"调用失败: {resp.status_code}")
    print(f"Response: {resp.text}")
    sys.exit(1)
