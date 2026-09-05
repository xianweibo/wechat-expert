# 端到端回归测试: B站抓取 -> AI 总结 -> 阿里云推送
# 一站式，全白名单 PowerShell 命令

$ErrorActionPreference = 'Continue'
$SOCKS = '127.0.0.1:18080'
$ALIYUN = '8.134.248.11'
$ALIYUN_SSH_PORT = 22
$ALIYUN_USER = 'gongzhonghao'
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519"
$WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'

# SESSDATA 和 bili_jct (从 .env 拿, 失败则用占位)
$envFile = 'Z:\代码\养龙虾\公众号专家\gzh-worker\.env'
$SESSDATA = ''
$BILI_JCT = ''
$TARGET_UID = '290663424'
$MINIMAX_KEY = ''

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_
        if ($line -match '^BILIBILI_SESSDATA=(.+)$') { $SESSDATA = $Matches[1].Trim() }
        elseif ($line -match '^BILIBILI_BILI_JCT=(.+)$') { $BILI_JCT = $Matches[1].Trim() }
        elseif ($line -match '^MINIMAX_API_KEY=(.+)$') { $MINIMAX_KEY = $Matches[1].Trim() }
        elseif ($line -match '^TARGET_UP_UID=(.+)$') { $TARGET_UID = $Matches[1].Trim() }
    }
}

Write-Host "=== 1. 环境检查 ===" -ForegroundColor Cyan
Write-Host "SESSDATA 长度: $($SESSDATA.Length)"
Write-Host "bili_jct 长度: $($BILI_JCT.Length)"
Write-Host "MINIMAX_KEY 长度: $($MINIMAX_KEY.Length)"
Write-Host "TARGET_UP_UID: $TARGET_UID"

if ($SESSDATA.Length -lt 10 -or $MINIMAX_KEY.Length -lt 10) {
    Write-Host "[ERROR] .env 文件未读到 SESSDATA 或 MINIMAX_KEY" -ForegroundColor Red
    exit 1
}
