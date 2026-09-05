import os
import http.client
import json

body = json.dumps({
    'model': 'MiniMax-M3',
    'max_tokens': 200,
    'messages': [{'role': 'user', 'content': '用一句话证明你能联网'}],
}, ensure_ascii=False).encode('utf-8')
conn = http.client.HTTPSConnection('api.minimaxi.com', timeout=30)
conn.request('POST', '/anthropic/v1/messages', body=body, headers={
    'x-api-key': os.environ.get('MINIMAX_API_KEY', ''),
    'anthropic-version': '2023-06-01',
    'Content-Type': 'application/json; charset=utf-8',
})
resp = conn.getresponse()
data = json.loads(resp.read().decode('utf-8'))
print('status:', resp.status)
print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])
