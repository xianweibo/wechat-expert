import json, sys
d = json.load(open('/tmp/bv.json'))
data = d['data']
print('title:', data['title'])
print('owner:', data['owner']['name'])
print('pubdate:', data['pubdate'])
subs = data.get('subtitle', {}).get('subtitles', [])
print('subtitle_count:', len(subs))
for s in subs:
    print('sub:', s.get('lan_doc'), s.get('subtitle_url', '')[:100])
