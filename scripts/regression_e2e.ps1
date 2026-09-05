# End-to-end regression: BiliBili fetch + MiniMax summary + Aliyun push
# Push is initiated by Aliyun (8.134.248.11) which is in WeChat MP IP whitelist

$ErrorActionPreference = 'Stop'
$ALIYUN = '8.134.248.11'
$ALIYUN_PORT = 22
$ALIYUN_USER = 'gongzhonghao'
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519"
$WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'
$TARGET_UP_UID = 290663424

# From NAS gzh-worker container env
$SESSDATA = '9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC'
$BILI_JCT = 'de6ed23d674a50a73865adae67069017'
$MINIMAX_KEY = 'sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo'

function Log([string]$msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" }
function LogOk([string]$msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [OK] $msg" -ForegroundColor Green }
function LogErr([string]$msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [ERR] $msg" -ForegroundColor Red }

Log('========== E2E regression test start ==========')

# === 1. BiliBili space API (use curl.exe to avoid 412) ===
Log("[1/5] Fetch latest videos of UP $TARGET_UP_UID")
$listUrl = "https://api.bilibili.com/x/space/arc/search?mid=$TARGET_UP_UID&ps=10&pn=1"
$listCookie = "SESSDATA=$SESSDATA; bili_jct=$BILI_JCT"
try {
    $listJson = & curl.exe -sS -G --max-time 20 `
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" `
        -H "Cookie: $listCookie" `
        -H "Referer: https://space.bilibili.com/$TARGET_UP_UID/" `
        "$listUrl"
    if ($LASTEXITCODE -ne 0) { throw "curl exit $LASTEXITCODE" }
    $listResp = $listJson | ConvertFrom-Json
} catch {
    LogErr("BiliBili space API failed: $($_.Exception.Message)")
    exit 1
}
if ($listResp.code -ne 0) {
    LogErr("BiliBili space API code=$($listResp.code): $($listResp.message)")
    Log('Sleep 10s and retry...')
    Start-Sleep -Seconds 10
    $listJson = & $CURL -sS -G --max-time 20 `
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" `
        -H "Cookie: $listCookie" `
        -H "Referer: https://space.bilibili.com/$TARGET_UP_UID/" `
        "$listUrl"
    $listResp = $listJson | ConvertFrom-Json
    if ($listResp.code -ne 0) {
        LogErr("BiliBili space API retry failed code=$($listResp.code): $($listResp.message)")
        exit 1
    }
}
$vlist = $listResp.data.list.vlist
Log("    Got $($vlist.Count) videos")
if ($vlist.Count -eq 0) { LogErr('No videos'); exit 1 }
$target = $vlist[0]
Log("    Selected: $($target.title) ($($target.bvid))")

# === 2. Video detail (use curl.exe) ===
Log("[2/5] Fetch video detail $($target.bvid)")
$detailUrl = "https://api.bilibili.com/x/web-interface/view?bvid=$($target.bvid)"
$detailCookie = "SESSDATA=$SESSDATA; bili_jct=$BILI_JCT"
try {
    $detailJson = & curl.exe -sS -G --max-time 20 `
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" `
        -H "Cookie: $detailCookie" `
        "$detailUrl"
    if ($LASTEXITCODE -ne 0) { throw "curl exit $LASTEXITCODE" }
    $detail = $detailJson | ConvertFrom-Json
} catch {
    LogErr("Video detail failed: $($_.Exception.Message)")
    exit 1
}
if ($detail.code -ne 0) {
    LogErr("Video detail code=$($detail.code): $($detail.message)")
    exit 1
}
$d = $detail.data
$rights = $d.rights
$isCharged = ($rights.is_charging_arc -eq 1 -or $rights.ugc_pay -eq 1)
if (-not $isCharged) {
    LogErr("Latest video is NOT charged (is_charging_arc=$($rights.is_charging_arc) ugc_pay=$($rights.ugc_pay))")
    exit 1
}
LogOk('Confirmed charged video')
$cid = $d.pages[0].cid
Log("    cid=$cid")
Log("    desc length: $($d.desc.Length)")

# === 3. Subtitle (use curl.exe) ===
Log("[3/5] Fetch subtitle (cid=$cid)")
$playerUrl = "https://api.bilibili.com/x/player/v2?bvid=$($target.bvid)&cid=$cid"
$subText = ''
$hasSubtitle = $false
try {
    Start-Sleep -Seconds 3
    $playerJson = & $CURL -sS -G --max-time 20 `
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" `
        -H "Cookie: $detailCookie" `
        "$playerUrl"
    if ($LASTEXITCODE -ne 0) { throw "curl exit $LASTEXITCODE" }
    $player = $playerJson | ConvertFrom-Json
    $subs = $player.data.subtitle.subtitles
    if ($subs.Count -gt 0) {
        $subUrl = 'https:' + $subs[0].subtitle_url
        Log("    Subtitle URL: $subUrl")
        $subJson = & $CURL -sS --max-time 20 "$subUrl"
        $sub = $subJson | ConvertFrom-Json
        $subText = ($sub.body | ForEach-Object { $_.content }) -join "`n"
        $hasSubtitle = $true
        Log("    Subtitle length: $($subText.Length)")
    } else {
        Log('    No subtitle, will fallback to description')
    }
} catch {
    LogErr("Subtitle fetch error: $($_.Exception.Message), fallback to description")
}
if (-not $hasSubtitle -or $subText.Length -lt 50) {
    # Fallback: use description + dynamic
    $subText = $d.desc
    if ($d.dynamic) { $subText += "`n" + $d.dynamic }
    Log("    Fallback content length: $($subText.Length)")
}

# === 4. MiniMax API ===
Log('[4/5] Call MiniMax to generate summary')
$truncatedSub = $subText.Substring(0, [Math]::Min(6000, $subText.Length))
$prompt = "Generate a Chinese summary (600-800 chars) for this BiliBili video:`n`n[Title] $($target.title)`n`n[Subtitle]`n$truncatedSub"
$mmBody = @{
    model      = 'MiniMax-M2.7'
    max_tokens = 2048
    messages   = @(@{ role = 'user'; content = $prompt })
} | ConvertTo-Json -Depth 5 -Compress
$mmHeaders = @{
    'x-api-key'         = $MINIMAX_KEY
    'anthropic-version' = '2023-06-01'
    'Content-Type'      = 'application/json'
}
try {
    $mm = Invoke-RestMethod -Uri 'https://api.minimaxi.com/anthropic/v1/messages' -Method Post -Body $mmBody -Headers $mmHeaders -TimeoutSec 120
} catch {
    LogErr("MiniMax failed: $($_.Exception.Message)")
    exit 1
}
if ($mm.error) {
    LogErr("MiniMax error: $($mm.error.message)")
    exit 1
}
$summary = ''
foreach ($item in $mm.content) {
    if ($item.type -eq 'text') { $summary = $item.text; break }
}
if (-not $summary) { LogErr('MiniMax returned no text'); exit 1 }
Log("    Summary length: $($summary.Length)")
$preview = $summary.Substring(0, [Math]::Min(120, $summary.Length))
Log("    Preview: $preview...")

# === 5. Push to Aliyun gzh-expert-app ===
Log('[5/5] Push to Aliyun gzh-expert-app via SSH')
$publishedAt = (Get-Date -Date '1970-01-01 00:00:00Z').AddSeconds($target.created).ToUniversalTime().ToString('yyyy-MM-dd')
$payload = @{
    title   = $target.title
    summary = $summary
    source  = @{
        bvid         = $target.bvid
        url          = "https://www.bilibili.com/video/$($target.bvid)"
        up_uid       = [int]$target.mid
        up_name      = $target.author
        published_at = $publishedAt
    }
} | ConvertTo-Json -Depth 5 -Compress

$tmpLocal = Join-Path $env:TEMP ("gzh_payload_" + [guid]::NewGuid().ToString('N') + ".json")
$payload | Out-File -FilePath $tmpLocal -Encoding UTF8 -NoNewline
Log("    Payload written to $tmpLocal")
$tmpRemote = '/tmp/gzh_payload.json'

Log("    scp to ${ALIYUN}:$tmpRemote")
$scpCmd = "scp -P $ALIYUN_PORT -i `"$SSH_KEY`" -o StrictHostKeyChecking=accept-new `"$tmpLocal`" ${ALIYUN_USER}@${ALIYUN}:$tmpRemote"
Invoke-Expression $scpCmd
if ($LASTEXITCODE -ne 0) { LogErr('scp failed'); exit 1 }

Log("    ssh to Aliyun and curl POST")
$remoteCmd = "curl -sS -X POST -H 'Content-Type: application/json' -H 'X-Worker-Secret: $WORKER_SECRET' --data-binary @${tmpRemote} http://127.0.0.1:39800/api/bilibili/summary"
$sshCmd = "ssh -p $ALIYUN_PORT -i `"$SSH_KEY`" -o StrictHostKeyChecking=accept-new ${ALIYUN_USER}@${ALIYUN} `"$remoteCmd`""
Log("    CMD: $sshCmd")
$pushResult = Invoke-Expression $sshCmd
Log("    Push result: $pushResult")
Remove-Item $tmpLocal -Force -ErrorAction SilentlyContinue

Log('========== Done ==========')
