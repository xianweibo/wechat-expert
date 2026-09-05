# 公众号草稿推送脚本（走阿里云 8.134.248.11，白名单 IP）
# 用法: powershell -ExecutionPolicy Bypass -File .\regression_test_push.ps1

$ErrorActionPreference = 'Stop'

# 1. 配置
$SOCKS_PORT = 18080
$ALIYUN_HOST = '8.134.248.11'
$ALIYUN_PORT = 22
$ALIYUN_USER = 'gongzhonghao'
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519"
$REMOTE_SCRIPT = '/tmp/push_to_mp_on_aliyun.py'
$LOCAL_SCRIPT = Join-Path $PSScriptRoot 'push_to_mp_on_aliyun.py'

# 2. 检测 SOCKS 代理
Write-Host "==> 1. 检测 SOCKS 代理 127.0.0.1:$SOCKS_PORT ..." -ForegroundColor Cyan
$socks = Test-NetConnection -ComputerName 127.0.0.1 -Port $SOCKS_PORT -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $socks) {
    Write-Host "    [ERROR] SOCKS 代理未运行。请先启动你的代理软件（如 Clash/V2Ray/Netch）" -ForegroundColor Red
    Write-Host "    然后再跑这个脚本。" -ForegroundColor Red
    exit 1
}
Write-Host "    [OK] SOCKS 代理在线" -ForegroundColor Green

# 3. 验证 SSH key
if (-not (Test-Path $SSH_KEY)) {
    Write-Host "    [ERROR] SSH key 不存在: $SSH_KEY" -ForegroundColor Red
    exit 1
}
Write-Host "    [OK] SSH key 存在" -ForegroundColor Green

# 4. SCP 上传脚本到阿里云
Write-Host "==> 2. SCP 上传脚本到阿里云 $ALIYUN_USER@$ALIYUN_HOST ..." -ForegroundColor Cyan
$scpCmd = "scp -P $ALIYUN_PORT -i `"$SSH_KEY`" -o `"ProxyCommand=nc -X connect -x 127.0.0.1:$SOCKS_PORT %h %p`" `"$LOCAL_SCRIPT`" `${ALIYUN_USER}@${ALIYUN_HOST}:$REMOTE_SCRIPT"
Write-Host "    CMD: $scpCmd"
Invoke-Expression $scpCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "    [ERROR] SCP 失败" -ForegroundColor Red
    exit 1
}
Write-Host "    [OK] 脚本已上传到 $REMOTE_SCRIPT" -ForegroundColor Green

# 5. SSH 到阿里云执行推送
Write-Host "==> 3. SSH 到阿里云执行推送 ..." -ForegroundColor Cyan
$sshCmd = "ssh -p $ALIYUN_PORT -i `"$SSH_KEY`" -o `"ProxyCommand=nc -X connect -x 127.0.0.1:$SOCKS_PORT %h %p`" ${ALIYUN_USER}@${ALIYUN_HOST} `"python3 $REMOTE_SCRIPT`""
Write-Host "    CMD: $sshCmd"
Invoke-Expression $sshCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "    [ERROR] 推送失败（exit $LASTEXITCODE）" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host ""
Write-Host "==> [DONE] 推送流程结束" -ForegroundColor Green
