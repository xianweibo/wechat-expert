# Regression Test - Full Pipeline using curl.exe
$ErrorActionPreference = 'Continue'

$SESSDATA = $env:BILIBILI_SESSDATA
$MINIMAX_KEY = $env:MINIMAX_API_KEY
$ALIYUN_URL = 'http://8.134.248.11:3000/api/bilibili/summary'
$WORKER_SECRET = $env:BILIBILI_WORKER_SECRET

Write-Output "=================================================="
Write-Output "Regression Test - Full Pipeline"
Write-Output "=================================================="

# Step 1: Get latest charged video
Write-Output "[1/5] Getting latest charged video..."
$cookieHeader = "SESSDATA=$SESSDATA"
$videoListJson = curl.exe -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -H "Referer: https://www.bilibili.com/" -H "Cookie: $cookieHeader" "https://api.bilibili.com/x/space/arc/search?mid=290663424&pn=1&ps=10&order=pubdate"

$resp = $videoListJson | ConvertFrom-Json
if ($resp.code -ne 0) {
    Write-Output "  ERROR: Bilibili API returned code=$($resp.code), msg=$($resp.message)"
    exit 1
}

$vlist = $resp.data.list.vlist
$targetVideo = $null
foreach ($v in $vlist) {
    if ($v.is_charging_arc -eq $true -or $v.elec_arc_type -gt 0) {
        $targetVideo = $v
        break
    }
}
if (-not $targetVideo) {
    $targetVideo = $vlist[0]
    Write-Output "  No charged video found, using latest"
}

$bvid = $targetVideo.bvid
$title = $targetVideo.title
Write-Output "  Target: $title ($bvid)"

# Step 2: Get video detail
Write-Output "[2/5] Getting video detail..."
$detailJson = curl.exe -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -H "Referer: https://www.bilibili.com/" -H "Cookie: $cookieHeader" "https://api.bilibili.com/x/web-interface/view?bvid=$bvid"
$detailResp = $detailJson | ConvertFrom-Json
$detail = $detailResp.data
$cid = $detail.cid
$description = $detail.desc
$ownerMid = $detail.owner.mid
$ownerName = $detail.owner.name
$pubdate = $detail.pubdate
Write-Output "  CID: $cid, Duration: $($detail.duration)s"

# Step 3: Get subtitle
Write-Output "[3/5] Getting subtitle..."
$subtitleText = ''
$subJson = curl.exe -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -H "Referer: https://www.bilibili.com/" -H "Cookie: $cookieHeader" "https://api.bilibili.com/x/player/v2?bvid=$bvid&cid=$cid"
$subResp = $subJson | ConvertFrom-Json
$subtitles = $subResp.data.subtitle.subtitles
if ($subtitles.Count -gt 0) {
    $subUrl = $subtitles[0].subtitle_url
    if ($subUrl.StartsWith('//')) { $subUrl = "https:$subUrl" }
    Write-Output "  Downloading subtitle..."
    $subContentJson = curl.exe -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -H "Referer: https://www.bilibili.com/" $subUrl
    $subContent = $subContentJson | ConvertFrom-Json
    $lines = @()
    foreach ($item in $subContent.body) {
        $text = $item.content.Trim()
        if ($text) { $lines += $text }
    }
    $subtitleText = $lines -join ' '
    Write-Output "  Subtitle length: $($subtitleText.Length) chars"
} else {
    Write-Output "  No subtitle available"
}

# Step 4: Generate summary with MiniMax
Write-Output "[4/5] Generating summary with MiniMax..."

$subtitlePart = if ($subtitleText) { $subtitleText } else { "(no subtitle)" }
$promptText = "You are a financial content summarizer. Summarize the following video in Chinese.`n`nVideo Title: $title`nVideo Description: $description`nSubtitle Content:`n$subtitlePart`n`nRequirements:`n- Extract 5-8 key points with detailed analysis`n- Use plain language`n- Rewrite in your own words`n- Stay neutral, no predictions`n- About 1000 Chinese characters`n- Each point should have thorough discussion"

$minimaxBodyObj = @{
    model = 'MiniMax-M2.7'
    max_tokens = 2048
    messages = @(@{ role = 'user'; content = $promptText })
}
$minimaxBodyJson = $minimaxBodyObj | ConvertTo-Json -Depth 5 -Compress

# Save to temp file to avoid encoding issues with curl.exe
$tempBodyFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tempBodyFile, $minimaxBodyJson, [System.Text.Encoding]::UTF8)

$mmJson = curl.exe -s -X POST "https://api.minimaxi.com/anthropic/v1/messages" -H "x-api-key: $MINIMAX_KEY" -H "anthropic-version: 2023-06-01" -H "Content-Type: application/json" -d "@$tempBodyFile"
Remove-Item $tempBodyFile -Force

$mmResp = $mmJson | ConvertFrom-Json
$summary = ''
foreach ($item in $mmResp.content) {
    if ($item.type -eq 'text') {
        $summary = $item.text
        break
    }
}
if (-not $summary -and $mmResp.choices) {
    $summary = $mmResp.choices[0].message.content
}
Write-Output "  Summary generated: $($summary.Length) chars"
$previewLen = [Math]::Min(200, $summary.Length)
Write-Output "  Preview: $($summary.Substring(0, $previewLen))..."

# Step 5: Push to WeChat draft
Write-Output "[5/5] Pushing to WeChat draft..."

$pubDateStr = [DateTimeOffset]::FromUnixTimeSeconds($pubdate).DateTime.ToString('yyyy-MM-dd')

$payloadObj = @{
    title = $title
    summary = $summary
    source = @{
        bvid = $bvid
        url = "https://www.bilibili.com/video/$bvid"
        up_uid = $ownerMid
        up_name = $ownerName
        published_at = $pubDateStr
    }
}
$payloadJson = $payloadObj | ConvertTo-Json -Depth 5 -Compress

$tempPayloadFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tempPayloadFile, $payloadJson, [System.Text.Encoding]::UTF8)

$pushJson = curl.exe -s -X POST $ALIYUN_URL -H "Content-Type: application/json" -H "X-Worker-Secret: $WORKER_SECRET" -d "@$tempPayloadFile"
Remove-Item $tempPayloadFile -Force

$pushResp = $pushJson | ConvertFrom-Json
Write-Output "  Response success: $($pushResp.success)"
if ($pushResp.success) {
    Write-Output ""
    Write-Output "=================================================="
    Write-Output "REGRESSION TEST PASSED!"
    Write-Output "=================================================="
} else {
    Write-Output "  FAILED: $($pushResp.message)"
    Write-Output ""
    Write-Output "=================================================="
    Write-Output "REGRESSION TEST FAILED at step 5"
    Write-Output "=================================================="
    exit 1
}
