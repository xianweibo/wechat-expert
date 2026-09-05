# Sandbox SSH 使用说明

## 密钥信息
SSH 公钥已添加到阿里云服务器和 NAS 的 authorized_keys 中：
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEf+e2/N1XtXXJKvmjZ52QHgCivmkZfsSBgjDtQ7tplU gzh-expert-2026
```

## 使用方法
1. 确保本地私钥已保存到 `C:\Users\Administrator\.ssh\id_ed25519`（Windows）或 `~/.ssh/id_ed25519`（Linux/macOS），权限设置为 600：
   ```bash
   chmod 600 ~/.ssh/id_ed25519
   ```
2. 将 `scripts/sandbox_ssh_config` 的内容追加到 `~/.ssh/config` 文件中，使用别名连接：
   ```bash
   # 连接阿里云服务器
   ssh aliyun-gzh
   # 连接 NAS（直连内网）
   ssh nas-gzh
   ```

## 安全规则
- **必须使用 SSH Key 登录**，禁止使用密码
- 私钥文件权限必须为 600
- 禁止将私钥提交到 Git

## 注意事项
1. NAS 直连内网地址 `192.168.9.3`，需在同一局域网内
2. 如果 FRP 隧道连接异常，可以重启对应容器恢复：
   - 阿里云端操作：`sudo docker restart frps-gzhworker`
   - NAS 端操作：`sudo docker restart frpc-gzhworker`
