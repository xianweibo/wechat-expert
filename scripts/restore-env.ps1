#requires -Version 5.1
<#
.SYNOPSIS
  公众号专家 - 重装后从服务器恢复 .env / SSH Key / docker 配置

.DESCRIPTION
  电脑重装后 SSH key 和 .env 通常一起丢失。
  本脚本按顺序尝试：
    1. 检测 SSH 私钥是否还在 .ssh 目录
    2. 若无，提示用户恢复
    3. 从阿里云 scp 拉取 .env（如果能登录）
    4. 从 NAS    scp 拉取 gzh-worker/.env
    5. 写入本地，保留现有 GITHUB_TOKEN（如果丢失前残留）

.NOTES
  Author : 公众号专家 Maintainer
  Updated: 2026-06-11
  Usage  : powershell -ExecutionPolicy Bypass -File .\scripts\restore-env.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipAliyun,
    [switch]$SkipNas,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# ---------- 颜色 ----------
function Write-Step($msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)    { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "    [X]  $msg" -ForegroundColor Red }

# ---------- 路径 ----------
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvLocal    = Join-Path $ProjectRoot '.env'
$EnvExample  = Join-Path $ProjectRoot '.env.example'
$WorkerDir   = Join-Path $ProjectRoot 'gzh-worker'
$EnvWorker   = Join-Path $WorkerDir   '.env'
$WorkerExam  = Join-Path $WorkerDir   '.env.example'

$SshDir      = Join-Path $env:USERPROFILE '.ssh'

# ---------- 服务器地址 ----------
$AliyunHost  = '8.134.248.11'
$AliyunPort  = 22
$AliyunUser  = 'gongzhonghao'
$AliyunEnv   = '/home/gongzhonghao/apps/gzh-expert-git/.env'

$NasHost     = '8.134.248.11'
$NasPort     = 39022
$NasUser     = 'paulproject'
$NasEnv      = '/vol2/1000/docker_related/gzh-worker/.env'

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  公众号专家 - 环境恢复脚本" -ForegroundColor Magenta
Write-Host "  Project Root: $ProjectRoot" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

# ---------- 1. SSH 私钥检查 ----------
Write-Step "1/5 检查 SSH 私钥"

$AliyunKey = Join-Path $SshDir 'gzh_expert_ed25519'
$NasKey    = Join-Path $SshDir 'gzh_nas_ed25519'
$DefaultKey = Join-Path $SshDir 'id_ed25519'

$hasAliyunKey = Test-Path $AliyunKey
$hasNasKey    = Test-Path $NasKey
$hasDefault   = Test-Path $DefaultKey

if ($hasAliyunKey) { Write-OK "找到阿里云私钥: $AliyunKey" }
else { Write-Warn "缺少阿里云私钥: $AliyunKey" }

if ($hasNasKey) { Write-OK "找到 NAS 私钥: $NasKey" }
else { Write-Warn "缺少 NAS 私钥: $NasKey" }

if ($hasDefault) { Write-OK "找到默认私钥: $DefaultKey" }

if (-not ($hasAliyunKey -or $hasNasKey -or $hasDefault)) {
    Write-Err "没有任何 SSH 私钥。"
    Write-Host ""
    Write-Host "恢复方式（任选其一）：" -ForegroundColor Yellow
    Write-Host "  A. 从备份还原整个 .ssh 目录到 $SshDir" -ForegroundColor Yellow
    Write-Host "  B. 用密码登录服务器后重新上传公钥：" -ForegroundColor Yellow
    Write-Host "       ssh-keygen -t ed25519 -f $AliyunKey -N ''" -ForegroundColor Yellow
    Write-Host "       ssh-copy-id -i ${AliyunKey}.pub $AliyunUser@$AliyunHost" -ForegroundColor Yellow
    Write-Host ""
    if (-not $DryRun) {
        $choice = Read-Host "是否现在生成新密钥对？(y/N)"
        if ($choice -eq 'y') {
            if (-not (Test-Path $SshDir)) { New-Item -ItemType Directory -Path $SshDir -Force | Out-Null }
            ssh-keygen -t ed25519 -f $AliyunKey -N '""' -C "gzh-expert-restored-$(Get-Date -Format yyyyMMdd)"
            Write-OK "已生成新密钥。请把 ${AliyunKey}.pub 内容加到服务器的 ~/.ssh/authorized_keys 后再运行本脚本。"
            exit 0
        }
    }
    exit 1
}

# ---------- 2. SSH 连接测试 ----------
Write-Step "2/5 测试 SSH 连接"

$aliyunKeyToUse = if ($hasAliyunKey) { $AliyunKey } else { $DefaultKey }
$nasKeyToUse    = if ($hasNasKey)    { $NasKey }    else { $DefaultKey }

function Test-Ssh($host, $port, $user, $key) {
    $args = @('-i', $key, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
              '-p', $port, "$user@$host", 'echo OK')
    try {
        $out = & ssh @args 2>&1
        if ($LASTEXITCODE -eq 0 -and ($out -join '`n') -match 'OK') {
            return $true
        }
        return $false
    } catch { return $false }
}

if (-not $SkipAliyun) {
    if (Test-Ssh $AliyunHost $AliyunPort $AliyunUser $aliyunKeyToUse) {
        Write-OK "阿里云 SSH 可达"
        $aliyunReachable = $true
    } else {
        Write-Warn "阿里云 SSH 不可达（key 或网络问题）"
        $aliyunReachable = $false
    }
}

if (-not $SkipNas) {
    if (Test-Ssh $NasHost $NasPort $NasUser $nasKeyToUse) {
        Write-OK "NAS SSH 可达"
        $nasReachable = $true
    } else {
        Write-Warn "NAS SSH 不可达"
        $nasReachable = $false
    }
}

# ---------- 3. 拉取 .env ----------
Write-Step "3/5 从服务器拉取 .env"

function Pull-Env($localPath, $host, $port, $user, $remotePath, $key) {
    if ($DryRun) {
        Write-Host "    [DRY] scp -P $port -i $key $user@${host}:$remotePath $localPath"
        return $true
    }
    try {
        $backup = "${localPath}.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
        if (Test-Path $localPath) {
            Copy-Item $localPath $backup -Force
            Write-Host "    已备份原文件到: $backup"
        }
        scp -P $port -i $key "$user@${host}:$remotePath" $localPath
        if ($LASTEXITCODE -eq 0) {
            Write-OK "写入: $localPath"
            return $true
        }
        Write-Err "scp 失败，退出码 $LASTEXITCODE"
        return $false
    } catch {
        Write-Err "scp 异常: $_"
        return $false
    }
}

if ($aliyunReachable -and -not $SkipAliyun) {
    Pull-Env $EnvLocal $AliyunHost $AliyunPort $AliyunUser $AliyunEnv $aliyunKeyToUse
} else {
    Write-Warn "跳过阿里云 .env 拉取"
}

if ($nasReachable -and -not $SkipNas) {
    Pull-Env $EnvWorker $NasHost $NasPort $NasUser $NasEnv $nasKeyToUse
} else {
    Write-Warn "跳过 NAS .env 拉取"
}

# ---------- 4. .env 完整性检查 ----------
Write-Step "4/5 校验 .env 完整性"

$requiredKeys = @(
    'WECHAT_APP_ID','WECHAT_APP_SECRET',
    'POSTGRES_USER','POSTGRES_PASSWORD','DATABASE_URL',
    'BILIBILI_WORKER_SECRET',
    'JWT_SECRET'
)

if (Test-Path $EnvLocal) {
    $content = Get-Content $EnvLocal -Raw
    $missing = @()
    foreach ($k in $requiredKeys) {
        if ($content -notmatch "(?m)^${k}=.+" -or $content -match "(?m)^${k}=(__FILL|CHANGE_ME|$k)") {
            $missing += $k
        }
    }
    if ($missing.Count -eq 0) {
        Write-OK "主 .env 所有必填项已就位"
    } else {
        Write-Warn "主 .env 缺失或仍为占位符：$($missing -join ', ')"
    }
} else {
    Write-Warn "主 .env 不存在，将从 .env.example 复制"
    if (-not $DryRun) {
        if (Test-Path $EnvExample) {
            Copy-Item $EnvExample $EnvLocal
            Write-OK "已复制模板到 .env，请手动填值"
        }
    }
}

if (Test-Path $EnvWorker) {
    $wc = Get-Content $EnvWorker -Raw
    $wmissing = @()
    foreach ($k in 'BILIBILI_SESSDATA','BILIBILI_BILI_JCT','MINIMAX_API_KEY','BILIBILI_WORKER_SECRET') {
        if ($wc -notmatch "(?m)^${k}=.+" -or $wc -match "(?m)^${k}=(__FILL|$k)") {
            $wmissing += $k
        }
    }
    if ($wmissing.Count -eq 0) { Write-OK "gzh-worker .env 完整" }
    else { Write-Warn "gzh-worker .env 缺失：$($wmissing -join ', ')" }
}

# ---------- 5. 后续提示 ----------
Write-Step "5/5 下一步"
Write-Host @"

恢复完成后的检查清单：

  [ ] 安装 Git for Windows:        https://git-scm.com/download/win
  [ ] 安装 Node.js 20 LTS:         https://nodejs.org/
  [ ] 安装 Docker Desktop:         https://www.docker.com/products/docker-desktop/
  [ ] cd 到项目目录运行:           npm install
  [ ] 启动容器:                    docker compose up -d --build
  [ ] 健康检查:                    curl http://localhost:39800/api/health

如果 GITHUB_TOKEN 丢失，到 https://github.com/settings/tokens 重新生成。
如果 WECHAT_APP_SECRET 丢失，到 https://mp.weixin.qq.com 重置。
如果 BILIBILI_SESSDATA 失效，重新登录 B 站从浏览器 Cookie 复制。

"@ -ForegroundColor White

Write-Host "搞定。" -ForegroundColor Green