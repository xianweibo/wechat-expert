import requests, json, datetime

SESSDATA = '9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC'
BILI_JCT = 'de6ed23d674a50a73865adae67069017'
UP_UID = 290663424
MINIMAX_API_KEY = 'sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo'
WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'

cookies = {'SESSDATA': SESSDATA, 'bili_jct': BILI_JCT}
req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.bilibili.com/'}

print('=== Regression Test ===')

print('\n[1] Dynamic API...')
url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid=%d' % UP_UID
resp = requests.get(url, cookies=cookies, headers=req_headers, timeout=15)
print('  HTTP: %d, CT: %s' % (resp.status_code, resp.headers.get('content-type')))
if resp.text:
    data = resp.json()
    print('  code=%d, items=%d' % (data.get('code'), len(data.get('data',{}).get('items',[]))))
else:
    print('  EMPTY response!')

print('\n[2] Regular API...')
url2 = 'https://api.bilibili.com/x/space/arc/search?mid=%d&ps=5&pn=1&order=pubdate' % UP_UID
resp2 = requests.get(url2, cookies=cookies, headers=req_headers, timeout=15)
print('  HTTP: %d' % resp2.status_code)
if resp2.text:
    data2 = resp2.json()
    print('  code=%d, msg=%s' % (data2.get('code'), data2.get('message')))
    vlist = data2.get('data',{}).get('list',{}).get('vlist',[])
    print('  Videos: %d' % len(vlist))
    for v in vlist[:5]:
        bv = v.get('bvid','')
        title = v.get('title','')[:30]
        created = v.get('created',0)
        date = datetime.datetime.fromtimestamp(created).strftime('%Y-%m-%d') if created else 'N/A'
        print('    %s | %s | %s' % (bv, title, date))
else:
    print('  EMPTY!')

print('\n[3] Find charged video...')
target = None
for v in vlist:
    bv = v.get('bvid')
    try:
        detail_resp = requests.get('https://api.bilibili.com/x/web-interface/view?bvid=%s' % bv, cookies=cookies, headers=req_headers, timeout=10)
        if detail_resp.status_code == 200:
            detail = detail_resp.json()
            rights = detail.get('data',{}).get('rights',{})
            is_charged = rights.get('is_charging_arc',0) == 1 or rights.get('ugc_pay',0) == 1
            print('  %s: is_charging_arc=%s ugc_pay=%s' % (bv, rights.get('is_charging_arc'), rights.get('ugc_pay')))
            if is_charged:
                target = v
                target_bv = bv
                target_title = v.get('title')
                target_rights = rights
                print('  ==> CHARGED VIDEO FOUND: %s' % bv)
                break
    except Exception as e:
        print('  %s error: %s' % (bv, e))

if not target:
    print('  No charged video found in top 5, checking more...')
    target = vlist[0] if vlist else None

if target:
    bv = target.get('bvid')
    print('\n[4] Get subtitle for %s...' % bv)
    first_cid = None
    try:
        view_resp = requests.get('https://api.bilibili.com/x/web-interface/view?bvid=%s' % bv, cookies=cookies, headers=req_headers, timeout=10)
        if view_resp.status_code == 200:
            view_data = view_resp.json().get('data',{})
            if view_data.get('pages'):
                first_cid = view_data['pages'][0].get('cid')
                title = view_data.get('title','')
                pubdate_ts = view_data.get('pubdate', 0)
                pubdate = datetime.datetime.fromtimestamp(pubdate_ts).strftime('%Y-%m-%d') if pubdate_ts else 'N/A'
                print('  Title: %s' % title[:40])
                print('  Pubdate: %s' % pubdate)
                print('  CID: %s' % first_cid)
    except Exception as e:
        print('  View error: %s' % e)

    if first_cid:
        print('\n[5] MiniMax summary...')
        subtitle_text = ''
        try:
            player_resp = requests.get('https://api.bilibili.com/x/player/v2?bvid=%s&cid=%s' % (bv, first_cid), cookies=cookies, headers=req_headers, timeout=10)
            if player_resp.status_code == 200:
                subs = player_resp.json().get('data',{}).get('subtitle',{}).get('subtitles',[])
                if subs:
                    sub_url = subs[0].get('subtitle_url','')
                    if sub_url and not sub_url.startswith('http'):
                        sub_url = 'https:' + sub_url
                    print('  Sub URL: %s' % sub_url[:80])
                    sub_resp = requests.get(sub_url, headers=req_headers, timeout=10)
                    if sub_resp.status_code == 200:
                        body = sub_resp.json().get('body',[])
                        lines = []
                        for item in body:
                            text = item.get('i','') or item.get('content','')
                            if text:
                                lines.append(text.strip())
                        subtitle_text = '\n'.join(lines)
                        print('  Subtitle chars: %d' % len(subtitle_text))
                    else:
                        print('  Sub download failed: %d' % sub_resp.status_code)
                else:
                    print('  No subtitles')
        except Exception as e:
            print('  Subtitle error: %s' % e)

        if subtitle_text:
            prompt = 'You are a financial content organizer. Based on the following video subtitle, generate an engaging summary suitable for a WeChat public account. Requirements: extract 5-8 core points, use accessible language, stay neutral (no price predictions), around 1000 characters, each point should have thorough analysis.\n\nSubtitle:\n' + subtitle_text[:3000]
            try:
                mm_resp = requests.post('https://api.minimax.chat/v1/text/chatcompletion_v2',
                    json={'model': 'MiniMax-Text-01', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 2048, 'temperature': 0.7},
                    headers={'Authorization': 'Bearer %s' % MINIMAX_API_KEY, 'Content-Type': 'application/json'},
                    timeout=120)
                if mm_resp.status_code == 200:
                    result = mm_resp.json()
                    summary = result.get('choices',[{}])[0].get('message',{}).get('content','')
                    print('  Summary generated: %d chars' % len(summary))
                    print('  Preview: %s...' % summary[:200])

                    print('\n[6] Push to Aliyun...')
                    push_resp = requests.post('http://8.134.248.11:39800/api/bilibili/summary',
                        json={'title': bv, 'summary': summary, 'source': {'bvid': bv, 'url': 'https://www.bilibili.com/video/%s' % bv, 'up_uid': UP_UID, 'up_name': '', 'published_at': pubdate}},
                        headers={'Content-Type': 'application/json', 'X-Worker-Secret': WORKER_SECRET},
                        timeout=30)
                    print('  Push HTTP: %d' % push_resp.status_code)
                    if push_resp.status_code == 200:
                        push_data = push_resp.json()
                        print('  Push result: %s' % push_data)
                    else:
                        print('  Push failed: %s' % push_resp.text[:200])
                else:
                    print('  MiniMax failed: %d %s' % (mm_resp.status_code, mm_resp.text[:200]))
            except Exception as e:
                print('  MiniMax error: %s' % e)
        else:
            print('  No subtitle text, skip MiniMax')

print('\n=== Done ===')