import http.client
import json

body = json.dumps({
    'model': 'MiniMax-M3',
    'max_tokens': 200,
    'messages': [{'role': 'user', 'content': '用一句话证明你能联网'}],
}, ensure_ascii=False).encode('utf-8')
conn = http.client.HTTPSConnection('api.minimaxi.com', timeout=30)
conn.request('POST', '/anthropic/v1/messages', body=body, headers={
    'x-api-key': 'sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo',
    'anthropic-version': '2023-06-01',
    'Content-Type': 'application/json; charset=utf-8',
})
resp = conn.getresponse()
data = json.loads(resp.read().decode('utf-8'))
print('status:', resp.status)
print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])
