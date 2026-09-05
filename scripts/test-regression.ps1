param(
    [string]$Sessdata = "",
    [string]$BiliJct = "",
    [string]$MinimaxKey = "",
    [string]$AliyunUrl = "http://8.134.248.11:3000/api/bilibili/summary",
    [string]$WorkerSecret = "",
    [int]$UpUid = 290663424
)

$ErrorActionPreference = "Stop"

if (-not $Sessdata -or -not $BiliJct -or -not $MinimaxKey) {
    Write-Host "Usage: .\test-regression.ps1 -Sessdata <SESSDATA> -BiliJct <bili_jct> -MinimaxKey <key> [-WorkerSecret <secret>]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or set env vars: BILIBILI_SESSDATA, BILIBILI_BILI_JCT, MINIMAX_API_KEY, BILIBILI_WORKER_SECRET"
    exit 1
}

$Headers = @{
    "Cookie" = "SESSDATA=$Sessdata; bili_jct=$BiliJct"
    "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    "Referer" = "https://www.bilibili.com"
}

Write-Host "========== 回归测试开始 ==========" -ForegroundColor Green
Write-Host "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# --- Step 1: Dynamic API ---
Write-Host "`n[1/5] 动态API获取UP主 ${UpUid} 的视频..." -ForegroundColor Cyan

$allVideos = @()
$offset = ""

for ($page = 0; $page -lt 3; $page++) {
    $url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid=${UpUid}"
    if ($offset) { $url += "&offset=$offset" }

    Write-Host "  请求页 $($page + 1): $url"
    try {
        $resp = Invoke-RestMethod -Uri $url -Headers $Headers -TimeoutSec 15
        if ($resp.code -ne 0) {
            Write-Host "  动态API错误: code=$($resp.code), msg=$($resp.message)" -ForegroundColor Red
            break
        }

        $items = $resp.data.items
        if (-not $items -or $items.Count -eq 0) {
            Write-Host "  动态列表为空"
            break
        }

        foreach ($item in $items) {
            $major = $item.modules.module_dynamic.major
            if (-not $major -or -not $major.archive) { continue }
            $archive = $major.archive
            if (-not $archive.bvid) { continue }

            $allVideos += @{
                bvid = $archive.bvid
                title = $archive.title
                is_charging_arc = $archive.is_charging_arc
                ctime = $archive.ctime
                duration_text = $archive.duration_text
            }
        }

        $hasMore = $resp.data.has_more
        $offset = $resp.data.offset
        if (-not $hasMore -or -not $offset) {
            Write-Host "  动态列表已到底"
            break
        }
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "  请求失败: $($_.Exception.Message)" -ForegroundColor Red
        break
    }
}

Write-Host "  动态API获取到 $($allVideos.Count) 个视频"

if ($allVideos.Count -eq 0) {
    Write-Host "  没有找到视频，退出" -ForegroundColor Red
    exit 1
}

foreach ($v in $allVideos[0..9]) {
    $chargeMark = if ($v.is_charging_arc) { "[充电]" } else { "" }
    Write-Host "    $($v.bvid) | $($v.title) $chargeMark"
}

# --- Step 2: Find charged video ---
Write-Host "`n[2/5] 查找充电视频..." -ForegroundColor Cyan

$targetVideo = $null
$targetDetail = $null

foreach ($video in $allVideos) {
    Write-Host "  检查 $($video.bvid): $($video.title) (is_charging_arc=$($video.is_charging_arc))"

    if ($video.is_charging_arc) {
        $targetVideo = $video
        Write-Host "  -> 动态API标记为充电视频" -ForegroundColor Green
        break
    }

    try {
        $detailResp = Invoke-RestMethod -Uri "https://api.bilibili.com/x/web-interface/view?bvid=$($video.bvid)" -Headers $Headers -TimeoutSec 10
        if ($detailResp.code -eq 0) {
            $rights = $detailResp.data.rights
            $isCharged = ($rights.is_charging_arc -eq 1) -or ($rights.ugc_pay -eq 1)
            if ($isCharged) {
                $targetVideo = $video
                $targetDetail = $detailResp.data
                Write-Host "  -> 详情API确认充电视频 (is_charging_arc=$($rights.is_charging_arc), ugc_pay=$($rights.ugc_pay))" -ForegroundColor Green
                break
            }
        }
    } catch {
        Write-Host "  -> 详情API失败: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    Start-Sleep -Milliseconds 300
}

if (-not $targetVideo) {
    Write-Host "  没有找到充电视频，使用第一个视频作为测试" -ForegroundColor Yellow
    $targetVideo = $allVideos[0]
}

if (-not $targetDetail) {
    try {
        $detailResp = Invoke-RestMethod -Uri "https://api.bilibili.com/x/web-interface/view?bvid=$($targetVideo.bvid)" -Headers $Headers -TimeoutSec 10
        if ($detailResp.code -eq 0) {
            $targetDetail = $detailResp.data
        }
    } catch {
        Write-Host "  获取视频详情失败: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$pubdate = if ($targetVideo.ctime) {
    [DateTimeOffset]::FromUnixTimeSeconds($targetVideo.ctime).ToString("yyyy-MM-dd")
} else {
    Get-Date -Format "yyyy-MM-dd"
}

Write-Host "`n  目标视频: $($targetVideo.bvid) - $($targetVideo.title) ($pubdate)" -ForegroundColor Green

# --- Step 3: Get subtitle ---
Write-Host "`n[3/5] 获取字幕..." -ForegroundColor Cyan

$subtitleText = ""
if ($targetDetail -and $targetDetail.pages -and $targetDetail.pages.Count -gt 0) {
    $cid = $targetDetail.pages[0].cid
    try {
        $playerResp = Invoke-RestMethod -Uri "https://api.bilibili.com/x/player/v2?bvid=$($targetVideo.bvid)&cid=$cid" -Headers $Headers -TimeoutSec 10
        if ($playerResp.code -eq 0 -and $playerResp.data.subtitle.subtitles.Count -gt 0) {
            $subUrl = $playerResp.data.subtitle.subtitles[0].subtitle_url
            if ($subUrl -and -not $subUrl.StartsWith("http")) {
                $subUrl = "https:$subUrl"
            }
            Write-Host "  下载字幕: $subUrl"
            $subResp = Invoke-RestMethod -Uri $subUrl -Headers $Headers -TimeoutSec 10
            $lines = @()
            foreach ($item in $subResp.body) {
                $text = if ($item.content) { $item.content.Trim() } elseif ($item.i) { $item.i.Trim() } else { "" }
                if ($text) { $lines += $text }
            }
            $subtitleText = $lines -join "`n"
        } else {
            Write-Host "  没有字幕" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  字幕获取失败: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  无视频详情，跳过字幕" -ForegroundColor Yellow
}

Write-Host "  字幕长度: $($subtitleText.Length) 字符"

# --- Step 4: MiniMax summary ---
Write-Host "`n[4/5] MiniMax 生成总结..." -ForegroundColor Cyan

$desc = if ($targetDetail) { "$($targetDetail.description)`n$($targetDetail.dynamic)" } else { "" }
$subtitleSection = if ($subtitleText) { $subtitleText } else { "（无字幕）" }

$prompt = @"
你是一个财经学习内容整理助手。请根据以下视频字幕和简介，生成一段精华总结。

视频标题：$($targetVideo.title)
视频简介：$desc
字幕内容：
$subtitleSection

要求：
- 提取核心要点，分5-8个要点详细展开
- 用通俗易懂的语言
- 不复述原话，用自己语言重构
- 保持中立，不预测涨跌
- 篇幅控制在1000字左右，内容要充实有深度
- 每个要点要有充分的论述和分析，不要只是简单罗列
"@

$summaryBody = @{
    model = "MiniMax-Text-01"
    messages = @(@{ role = "user"; content = $prompt })
    max_tokens = 2048
    temperature = 0.7
} | ConvertTo-Json -Depth 5 -Compress

$minimaxHeaders = @{
    "Authorization" = "Bearer $MinimaxKey"
    "Content-Type" = "application/json"
}

$summary = ""
try {
    Write-Host "  调用 MiniMax API..."
    $mmResp = Invoke-RestMethod -Uri "https://api.minimax.chat/v1/text/chatcompletion_v2" -Method Post -Headers $minimaxHeaders -Body $summaryBody -TimeoutSec 60
    if ($mmResp.error) {
        Write-Host "  MiniMax错误: $($mmResp.error.message)" -ForegroundColor Red
    } else {
        $summary = $mmResp.choices[0].message.content
    }
} catch {
    Write-Host "  MiniMax调用失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  尝试Anthropic兼容接口..." -ForegroundColor Yellow

    $anthropicBody = @{
        model = "MiniMax-M2.7"
        max_tokens = 2048
        messages = @(@{ role = "user"; content = $prompt })
    } | ConvertTo-Json -Depth 5 -Compress

    $anthropicHeaders = @{
        "x-api-key" = $MinimaxKey
        "anthropic-version" = "2023-06-01"
        "Content-Type" = "application/json"
    }

    try {
        $aResp = Invoke-RestMethod -Uri "https://api.minimaxi.com/anthropic/v1/messages" -Method Post -Headers $anthropicHeaders -Body $anthropicBody -TimeoutSec 120
        foreach ($item in $aResp.content) {
            if ($item.type -eq "text") {
                $summary = $item.text
                break
            }
        }
    } catch {
        Write-Host "  Anthropic接口也失败: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if (-not $summary) {
    Write-Host "  总结生成失败，退出" -ForegroundColor Red
    exit 1
}

Write-Host "`n--- 总结预览 ---" -ForegroundColor Yellow
Write-Host $summary.Substring(0, [Math]::Min(300, $summary.Length))
if ($summary.Length -gt 300) { Write-Host "..." }
Write-Host "--- 预览结束 ---`n" -ForegroundColor Yellow

# --- Step 5: Push to Aliyun ---
Write-Host "[5/5] 推送到阿里云 → 公众号草稿..." -ForegroundColor Cyan

if (-not $WorkerSecret) {
    Write-Host "  未提供 WorkerSecret，跳过推送" -ForegroundColor Yellow
    Write-Host "  如需推送，请设置 -WorkerSecret 参数" -ForegroundColor Yellow
} else {
    $payload = @{
        title = $targetVideo.title
        summary = $summary
        source = @{
            bvid = $targetVideo.bvid
            url = "https://www.bilibili.com/video/$($targetVideo.bvid)"
            up_uid = $UpUid
            up_name = ""
            published_at = $pubdate
        }
    } | ConvertTo-Json -Depth 5

    $pushHeaders = @{
        "Content-Type" = "application/json"
        "X-Worker-Secret" = $WorkerSecret
    }

    try {
        $pushResp = Invoke-RestMethod -Uri $AliyunUrl -Method Post -Headers $pushHeaders -Body $payload -TimeoutSec 30
        if ($pushResp.success) {
            Write-Host "  推送成功！草稿 media_id: $($pushResp.media_id)" -ForegroundColor Green
        } else {
            Write-Host "  推送失败: $($pushResp.message)" -ForegroundColor Red
        }
    } catch {
        Write-Host "  推送请求失败: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  阿里云服务器可能不可达（沙箱网络限制）" -ForegroundColor Yellow
    }
}

Write-Host "`n========== 回归测试完成 ==========" -ForegroundColor Green
Write-Host "视频: $($targetVideo.bvid) - $($targetVideo.title)"
Write-Host "总结长度: $($summary.Length) 字符"
