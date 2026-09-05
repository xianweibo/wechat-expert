# Generate a Chinese summary for BiliBili video. Title and content are Chinese; keep prompt ASCII to avoid PowerShell UTF-8 BOM issues.
$ErrorActionPreference = 'Stop'
$CURL = 'C:\Windows\System32\curl.exe'
$ALIYUN = '8.134.248.11'
$ALIYUN_PORT = 22
$ALIYUN_USER = 'gongzhonghao'
$SSH_KEY = 'C:\Users\Administrator\.ssh\id_ed25519'
$WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'
$KNOWN_BVID = 'BV1gZ7Z6hEaP'

$SESSDATA = '9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC'
$BILI_JCT = 'de6ed23d674a50a73865adae67069017'
$MINIMAX_KEY = 'sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo'

function Log([string]$msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" }
function LogOk([string]$msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [OK] $msg" -ForegroundColor Green }
function LogErr([string]$msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [ERR] $msg" -ForegroundColor Red }

Log('========== E2E regression test start ==========')

# === 1. Video detail ===
Log("[1/4] Fetch video detail $KNOWN_BVID")
$detailUrl = "https://api.bilibili.com/x/web-interface/view?bvid=$KNOWN_BVID"
$detailCookie = "SESSDATA=$SESSDATA; bili_jct=$BILI_JCT"
$detailJson = & $CURL -sS -G --max-time 20 `
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" `
    -H "Cookie: $detailCookie" `
    "$detailUrl"
if ($LASTEXITCODE -ne 0) { LogErr("curl exit $LASTEXITCODE"); exit 1 }
$detail = $detailJson | ConvertFrom-Json
if ($detail.code -ne 0) { LogErr("Video detail code=$($detail.code): $($detail.message)"); exit 1 }
$d = $detail.data
$rights = $d.rights
$isCharged = ($rights.is_charging_arc -eq 1 -or $rights.ugc_pay -eq 1 -or $d.is_upower_exclusive -eq $true -or $d.is_upower_play -eq $true)
if (-not $isCharged) { LogErr("Not a charged video"); exit 1 }
LogOk("Charged video: $($d.title)")
$cid = $d.pages[0].cid
$targetBvid = $d.bvid
$targetTitle = $d.title
$targetAuthor = $d.owner.name
$targetMid = $d.owner.mid
$targetCreated = $d.pubdate
Log("    bvid=$targetBvid cid=$cid author=$targetAuthor mid=$targetMid")

# === 2. Subtitle fallback ===
Log("[2/4] Subtitle fallback")
$subText = ''
$playerUrl = "https://api.bilibili.com/x/player/v2?bvid=$targetBvid&cid=$cid"
Start-Sleep -Seconds 2
$playerJson = & $CURL -sS -G --max-time 20 `
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" `
    -H "Cookie: $detailCookie" `
    "$playerUrl"
$player = $playerJson | ConvertFrom-Json
$subs = $player.data.subtitle.subtitles
if ($subs.Count -gt 0) {
    $subUrl = 'https:' + $subs[0].subtitle_url
    Log("    Subtitle URL: $subUrl")
    Start-Sleep -Seconds 1
    $subJson = & $CURL -sS --max-time 20 "$subUrl"
    $sub = $subJson | ConvertFrom-Json
    $subText = ($sub.body | ForEach-Object { $_.content }) -join "`n"
    Log("    Subtitle length: $($subText.Length)")
}
if ($subText.Length -lt 50) {
    Log('    No subtitle, fallback to description')
    $subText = $d.desc
    if ($d.dynamic) { $subText += "`n" + $d.dynamic }
    Log("    Fallback content length: $($subText.Length)")
}

# === 3. MiniMax API ===
Log('[3/4] Call MiniMax')
# Save title+content to temp file as UTF-8, then use that for the prompt
$contentFile = Join-Path $env:TEMP ("gzh_content_" + [guid]::NewGuid().ToString('N') + ".txt")
$truncated = $subText.Substring(0, [Math]::Min(6000, $subText.Length))
# Use ASCII labels + Chinese content (will be UTF-8 when sent)
$promptText = "Please generate a Chinese summary (600-800 characters) for this BiliBili video. The title and content are in Chinese, please summarize them in Chinese. Focus on main topic, key arguments, conclusions. Use professional Chinese tone." + "`n`n" + "Title: " + $targetTitle + "`n`n" + "Content:" + "`n" + $truncated

$mmBody = @{
    model      = 'MiniMax-M2.7'
    max_tokens = 2048
    messages   = @(@{ role = 'user'; content = $promptText })
} | ConvertTo-Json -Depth 5 -Compress
$mmHeaders = @{
    'x-api-key'         = $MINIMAX_KEY
    'anthropic-version' = '2023-06-01'
    'Content-Type'      = 'application/json'
}
$mm = Invoke-RestMethod -Uri 'https://api.minimaxi.com/anthropic/v1/messages' -Method Post -Body $mmBody -Headers $mmHeaders -TimeoutSec 120
if ($mm.error) { LogErr("MiniMax error: $($mm.error.message)"); exit 1 }
$summary = ''
foreach ($item in $mm.content) {
    if ($item.type -eq 'text') { $summary = $item.text; break }
}
if (-not $summary) { LogErr('MiniMax returned no text'); exit 1 }
Log("    Summary length: $($summary.Length)")
Log("    Preview: $($summary.Substring(0, [Math]::Min(120, $summary.Length)))...")

# === 4. Push via SSH to Aliyun gzh-expert-app ===
Log('[4/4] Push to Aliyun gzh-expert-app via SSH')
$publishedAt = (Get-Date -Date '1970-01-01 00:00:00Z').AddSeconds($targetCreated).ToUniversalTime().ToString('yyyy-MM-dd')
$payload = @{
    title   = $targetTitle
    summary = $summary
    source  = @{
        bvid         = $targetBvid
        url          = "https://www.bilibili.com/video/$targetBvid"
        up_uid       = [int]$targetMid
        up_name      = $targetAuthor
        published_at = $publishedAt
    }
} | ConvertTo-Json -Depth 5 -Compress

$tmpLocal = Join-Path $env:TEMP ("gzh_payload_" + [guid]::NewGuid().ToString('N') + ".json")
[System.IO.File]::WriteAllText($tmpLocal, $payload, [System.Text.Encoding]::UTF8)
Log("    Payload: $tmpLocal")
$tmpRemote = '/tmp/gzh_payload.json'

$scpCmd = "scp -P $ALIYUN_PORT -i `"$SSH_KEY`" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o BatchMode=yes `"$tmpLocal`" ${ALIYUN_USER}@${ALIYUN}:$tmpRemote"
Log("    scp...")
Invoke-Expression $scpCmd
if ($LASTEXITCODE -ne 0) { LogErr('scp failed'); exit 1 }

$remoteCmd = "curl -sS -X POST -H 'Content-Type: application/json' -H 'X-Worker-Secret: $WORKER_SECRET' --data-binary @${tmpRemote} http://127.0.0.1:39800/api/bilibili/summary"
$sshCmd = "ssh -p $ALIYUN_PORT -i `"$SSH_KEY`" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o BatchMode=yes ${ALIYUN_USER}@${ALIYUN} `"$remoteCmd`""
Log("    ssh + curl POST...")
$pushResult = Invoke-Expression $sshCmd
Log("    Push result: $pushResult")
Remove-Item $tmpLocal -Force -ErrorAction SilentlyContinue
Remove-Item $contentFile -Force -ErrorAction SilentlyContinue

Log('========== Done ==========')
