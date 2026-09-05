# 公众号专家 - 重装后恢复指南

> 适用场景：电脑重装系统后，需要把本地工作环境恢复成与服务器一致。
> 最后更新：2026-06-11

---

## 一、总览（按顺序执行）

| 步骤 | 任务 | 是否必须 | 预估 |
|---|---|---|---|
| 0 | 确认 `.git` 目录完好 | ✅ 是 | 1 分钟 |
| 1 | 安装基础工具 (Git / Node / Docker) | ✅ 是 | 15 分钟 |
| 2 | 恢复 SSH 密钥 | ⚠️ 视备份 | 10 分钟 |
| 3 | 恢复 `.env` 文件 | ✅ 是 | 5 分钟 |
| 4 | `npm install` 装依赖 | ✅ 是 | 5 分钟 |
| 5 | 启动 Docker 并验证 | ✅ 是 | 5 分钟 |
| 6 | 验证 worktree 分支 | 建议 | 5 分钟 |

---

## 二、逐步说明

### 步骤 0：确认项目文件完好

```powershell
cd Z:\代码\养龙虾\公众号专家
Test-Path .git           # 应返回 True
Test-Path src\index.ts   # 应返回 True
Test-Path README.md      # 应返回 True
```

如果 `.git` 不存在，**立刻停止**——这是灾难性的，需要从远端 `git clone` 重建工作树：

```powershell
cd ..
# 备份当前目录
Rename-Item 公众号专家 公众号专家-broken
git clone https://github.com/xianweibo/wechat-expert.git 公众号专家
# 注意：所有未推送的 worktree 分支会丢失，需提前 git fetch origin
```

---

### 步骤 1：安装基础工具

| 工具 | 下载 | 备注 |
|---|---|---|
| Git for Windows | https://git-scm.com/download/win | 安装时勾选 "Add Git to PATH" |
| Node.js 20 LTS | https://nodejs.org/ | 不要装最新版 |
| Docker Desktop | https://www.docker.com/products/docker-desktop/ | 安装后需重启，WSL2 后端 |

装完验证：

```powershell
git --version
node --version
npm --version
docker --version
```

---

### 步骤 2：恢复 SSH 密钥

SSH 私钥丢了基本不可逆，但有三种恢复方式：

**方式 A：从备份还原（最简单）**
```powershell
# 如果有 .ssh 目录的备份（U 盘 / 网盘 / OneDrive）
Copy-Item -Recurse <备份路径>\.ssh $env:USERPROFILE\.ssh
icacls $env:USERPROFILE\.ssh /inheritance:r
icacls $env:USERPROFILE\.ssh /grant:r "$env:USERNAME:(R)"
```

**方式 B：服务器端有密码登录**
```powershell
ssh-copy-id -i $env:USERPROFILE\.ssh\gzh_expert_ed25519.pub gongzhonghao@8.134.248.11
```

**方式 C：服务器端只有原公钥（最麻烦）**
- 联系阿里云控制台 → 重置实例密码 → Workbench 登录 → 追加新公钥 → 重置密码策略

**写入 SSH config**（让 `ssh aliyun` / `ssh nas` 别名生效）：

```powershell
$cfg = @"
Host aliyun
    HostName 8.134.248.11
    Port 22
    User gongzhonghao
    IdentityFile ~/.ssh/gzh_expert_ed25519
    StrictHostKeyChecking accept-new

Host nas
    HostName 8.134.248.11
    Port 39022
    User paulproject
    IdentityFile ~/.ssh/gzh_nas_ed25519
    StrictHostKeyChecking accept-new
"@
$cfg | Out-File -Encoding ascii $env:USERPROFILE\.ssh\config
```

测试：

```powershell
ssh aliyun "echo OK; docker ps"
ssh nas "sudo su - -c 'docker ps'"
```

---

### 步骤 3：恢复 .env

直接跑脚本：

```powershell
cd Z:\代码\养龙虾\公众号专家
powershell -ExecutionPolicy Bypass -File .\scripts\restore-env.ps1
```

脚本会：
1. 检测 SSH 私钥是否存在
2. 测试 SSH 连通性
3. `scp` 从阿里云拉 `/home/gongzhonghao/apps/gzh-expert-git/.env` 到本地 `.env`
4. `scp` 从 NAS 拉 `/vol2/1000/docker_related/gzh-worker/.env` 到本地 `gzh-worker/.env`
5. 校验关键字段是否就位

**手动方式**（如果脚本不工作）：

```powershell
scp -i $env:USERPROFILE\.ssh\gzh_expert_ed25519 `
    gongzhonghao@8.134.248.11:/home/gongzhonghao/apps/gzh-expert-git/.env `
    .env

scp -P 39022 -i $env:USERPROFILE\.ssh\gzh_nas_ed25519 `
    paulproject@8.134.248.11:/vol2/1000/docker_related/gzh-worker/.env `
    gzh-worker\.env
```

⚠️ **如果 `scp` 失败**（服务端权限问题），通过 SSH 进服务器手动 `cat` 出来复制粘贴：

```bash
# 阿里云上
cat /home/gongzhonghao/apps/gzh-expert-git/.env
# 然后复制输出到本地 .env
```

---

### 步骤 4：装依赖

```powershell
cd Z:\代码\养龙虾\公众号专家
npm install
cd gzh-worker
npm install
cd ..
```

如果 `npm install` 报网络错误：
```powershell
npm config set registry https://registry.npmmirror.com
```

---

### 步骤 5：启动 Docker

```powershell
# 主应用（带 PostgreSQL）
docker compose up -d --build

# 看日志
docker compose logs -f app

# 健康检查
curl http://localhost:39800/api/health
```

`gzh-worker` **不要在本地跑**（它是 NAS 上的），除非你想调试：

```powershell
cd gzh-worker
docker compose up -d --build
```

---

### 步骤 6：验证 worktree 分支

```powershell
cd Z:\代码\养龙虾\公众号专家
git worktree list
```

预期看到：

```
Z:\代码\养龙虾\公众号专家          xxxxxxx [main]
Z:\代码\养龙虾\wt-bilibili-api     xxxxxxx [feat/bilibili-api]
Z:\代码\养龙虾\wt-minimax-summary  xxxxxxx [feat/minimax-summary]
Z:\代码\养龙虾\wt-poster           xxxxxxx [feat/poster]
Z:\代码\养龙虾\wt-cron-setup       xxxxxxx [feat/cron-setup]
Z:\代码\养龙虾\wt-docker           xxxxxxx [feat/docker]
```

如果 worktree 丢失但分支还在远端：
```powershell
git fetch origin
git worktree add ../wt-bilibili-api origin/feat/bilibili-api
```

---

## 三、关键凭据补救清单

| 凭据 | 在哪 | 丢失后怎么办 |
|---|---|---|
| `WECHAT_APP_SECRET` | 阿里云 `/tmp/.mp_app_secret` | 公众号后台 → 开发 → 基本配置 → 重置 |
| `BILIBILI_SESSDATA` / `BILI_JCT` | NAS `/tmp/auth.txt` | 浏览器登录 B 站 → DevTools → Application → Cookies |
| `MINIMAX_API_KEY` | NAS `/tmp/auth.txt` | https://api.minimaxi.com 控制台重新生成 |
| `BILIBILI_WORKER_SECRET` | 阿里云 `.env` | 重新生成 32 字符随机串，两端同步改 |
| `POSTGRES_PASSWORD` | 阿里云 `.env` | 重置后旧数据需重新导入 |
| `JWT_SECRET` | 阿里云 `.env` | 重新生成即可，旧 token 失效 |
| `GITHUB_TOKEN` | 本地 `.env` | https://github.com/settings/tokens 重新生成 |

---

## 四、防患于未然（下次重装不慌）

把以下内容备份到 **非本机**（OneDrive / 阿里云 OSS / U 盘）：

1. `C:\Users\<user>\.ssh\` 整个目录
2. `C:\Users\<user>\.docker\` （Docker Desktop 数据）
3. 项目根目录的 `.env` 和 `gzh-worker/.env`
4. PostgreSQL 数据卷导出：
   ```powershell
   docker exec gzh-expert-db pg_dump -U gzh_expert gzh_expert > backup.sql
   ```
5. 浏览器书签里保存 SKILL.md 中"服务器"表格