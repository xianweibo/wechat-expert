#requires -Version 5.1
<#
.SYNOPSIS
  生成公众号专家项目的本地 SSH config（Windows 用）

.DESCRIPTION
  重装后只需运行一次，生成 ~/.ssh/config 和可选的密钥对。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\setup-local-ssh.ps1
  powershell -ExecutionPolicy Bypass -File .\scripts\setup-local-ssh.ps1 -GenerateKey
#>

[CmdletBinding()]
param(
    [switch]$GenerateKey,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$SshDir     = Join-Path $env:USERPROFILE '.ssh'
$ConfigPath = Join-Path $SshDir 'config'
$AliyunKey  = Join-Path $SshDir 'gzh_expert_ed25519'
$NasKey     = Join-Path $SshDir 'gzh_nas_ed25519'

# ---------- 准备 .ssh 目录 ----------
if (-not (Test-Path $SshDir)) {
    New-Item -ItemType Directory -Path $SshDir -Force | Out-Null
    Write-Host "[+] 已创建 $SshDir" -ForegroundColor Green
}

# ---------- 修复权限（Windows 上防止 ssh 警告） ----------
try {
    icacls $SshDir /inheritance:r 2>&1 | Out-Null
    icacls $SshDir /grant:r "${env:USERNAME}:(R,W)" 2>&1 | Out-Null
} catch {}

# ---------- 写 config ----------
$configBody = @"
# 公众号专家 - 服务器快捷别名
# 由 scripts/setup-local-ssh.ps1 生成

Host aliyun
    HostName 8.134.248.11
    Port 22
    User gongzhonghao
    IdentityFile ~/.ssh/gzh_expert_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 30

Host nas
    HostName 8.134.248.11
    Port 39022
    User paulproject
    IdentityFile ~/.ssh/gzh_nas_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 30
"@

if ((Test-Path $ConfigPath) -and -not $Force) {
    Write-Host "[!] $ConfigPath 已存在，跳过（用 -Force 覆盖）" -ForegroundColor Yellow
} else {
    $configBody | Out-File -Encoding ascii -NoNewline $ConfigPath
    Write-Host "[+] 已生成 SSH config: $ConfigPath" -ForegroundColor Green
}

# ---------- 生成密钥（可选）----------
if ($GenerateKey) {
    if ((Test-Path $AliyunKey) -and -not $Force) {
        Write-Host "[!] $AliyunKey 已存在，跳过" -ForegroundColor Yellow
    } else {
        ssh-keygen -t ed25519 -f $AliyunKey -N '""' -C "gzh-expert-$(Get-Date -Format yyyyMMdd)"
        Write-Host "[+] 已生成阿里云密钥: $AliyunKey" -ForegroundColor Green
        Write-Host "    请把 ${AliyunKey}.pub 内容追加到阿里云 ~/.ssh/authorized_keys" -ForegroundColor Yellow
    }

    if ((Test-Path $NasKey) -and -not $Force) {
        Write-Host "[!] $NasKey 已存在，跳过" -ForegroundColor Yellow
    } else {
        ssh-keygen -t ed25519 -f $NasKey -N '""' -C "gzh-nas-$(Get-Date -Format yyyyMMdd)"
        Write-Host "[+] 已生成 NAS 密钥: $NasKey" -ForegroundColor Green
        Write-Host "    请把 ${NasKey}.pub 内容追加到 NAS ~/.ssh/authorized_keys（需 sudo）" -ForegroundColor Yellow
    }
}

# ---------- 验证 ----------
Write-Host ""
Write-Host "==> 当前 .ssh 目录内容：" -ForegroundColor Cyan
Get-ChildItem $SshDir -Force | Select-Object Name, Length | Format-Table -AutoSize

Write-Host ""
Write-Host "==> 后续操作：" -ForegroundColor Cyan
if (-not (Test-Path $AliyunKey)) {
    Write-Host "  1. 生成密钥: powershell -ExecutionPolicy Bypass -File .\scripts\setup-local-ssh.ps1 -GenerateKey" -ForegroundColor White
}
Write-Host "  2. 测试连接: ssh aliyun 'echo OK'" -ForegroundColor White
Write-Host "  3. 恢复 .env: powershell -ExecutionPolicy Bypass -File .\scripts\restore-env.ps1" -ForegroundColor White