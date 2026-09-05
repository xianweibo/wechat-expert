@echo off
setlocal
set SSH=C:\Windows\System32\OpenSSH\ssh.exe
set OPTS=-o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=%USERPROFILE%\.ssh\known_hosts
%SSH% %OPTS% %*
endlocal