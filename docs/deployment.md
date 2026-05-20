# 公众号专家 - 部署方案

> 最后更新：2026-05-19

---

## 一、服务器信息

| 项目 | 值 |
|------|---|
| IP | 8.134.248.11 |
| 系统 | CentOS 8 |
| 项目用户 | `gongzhonghao` |
| 项目目录 | `/home/gongzhonghao/apps/gzh-expert-git/` |
| SSH Key | ed25519 (`gzh_expert_ed25519`) |
| API 地址 | http://gzh.relexplace.com |

---

## 二、目录结构

```
/home/gongzhonghao/apps/gzh-expert-git/
├── docker-compose.yml      # 容器编排（App + PostgreSQL）
├── Dockerfile              # 应用镜像（tsx 运行 TS）
├── .env                    # 环境变量（不提交 Git）
├── .env.example            # 环境变量模板（提交 Git）
├── .gitignore
├── src/                    # 源代码
├── data/
│   └── uploads/            # 上传文件
├── logs/                   # 日志
├── docs/                   # 文档
└── scripts/                # 脚本（公众号 API 测试等）
```

---

## 三、Docker 容器架构（已验证）

**重要**：服务器 80/443 端口被**宝塔面板**占用，公众号专家 Docker 容器不使用 80/443，监听 **39800**，通过宝塔 Nginx 反向代理。

```
┌──────────────────────────────────────────────────────┐
│          宝塔 Nginx (80) - 共用端口                │
│   gzh.relexplace.com → 反向代理 127.0.0.1:39800    │
└──────────────────────────────────────────────────────┘
                        ↓ (39800)
┌─────────────┐     ┌─────────────┐
│  App       │────▶│  PostgreSQL │
│  :3000     │     │   :5432     │
│ (Node.js)   │     │ (Docker内)   │
└─────────────┘     └─────────────┘
```

### 容器说明

| 容器名 | 镜像 | 端口 | 说明 |
|--------|------|------|------|
| gzh-expert-app | node:20-alpine | 39800:3000 | 后端 API 服务（tsx 运行 TS） |
| gzh-expert-db | postgres:16-alpine | 5432 (Docker内) | 数据库 |

**已删除**：gzh-expert-nginx 容器（由宝塔 Nginx 替代）

---

## 四、部署命令

### 首次部署

```bash
# 1. 进入项目目录
cd ~/apps/gzh-expert-git

# 2. 克隆代码（如果是新服务器）
git clone https://github.com/xianweibo/wechat-expert.git .
# 或已有目录则 git pull

# 3. 复制环境变量模板并填写
cp .env.example .env
nano .env  # 填入真实值

# 4. 构建并启动所有容器
docker compose up -d --build

# 5. 查看容器状态
docker compose ps

# 6. 查看日志
docker compose logs -f app
```

### 日常操作

```bash
# 进入项目目录
cd ~/apps/gzh-expert-git

# 启动
docker compose up -d

# 停止
docker compose down

# 重启应用
docker compose restart app

# 查看日志
docker compose logs -f app

# 进入容器调试
docker compose exec app sh

# 数据库备份
docker compose exec postgres pg_dump -U gzh_expert gzh_expert > backup_$(date +%Y%m%d).sql

# 更新代码后重新构建
git pull
docker compose up -d --build
```

---

## 五、宝塔反向代理配置

宝塔 Nginx 已配置 `gzh.relexplace.com` 反向代理到 `127.0.0.1:8080`。

配置文件位置：

```
/www/server/panel/vhost/nginx/gzh.relexplace.com.conf
```

查看配置：

```bash
sudo nginx -T | grep gzh.relexplace
```

如需修改或新增域名，在宝塔面板操作或手动编辑配置文件后执行：

```bash
sudo nginx -t && sudo nginx -s reload
```

---

## 六、安全配置清单

### 已完成
- [x] 创建专用项目用户（非 root）
- [x] SSH Key 登录（ed25519）
- [x] 免密 sudo 配置
- [x] Docker 用户组权限
- [x] `.env` 文件加入 `.gitignore`
- [x] API 服务运行在 8080 端口
- [x] 宝塔反向代理配置 `gzh.relexplace.com`

### 待完成
- [ ] 防火墙规则（仅开放 80/443/22）
- [ ] 禁用密码登录（确认 SSH Key 可用后）
- [ ] SSL 证书配置（宝塔一键申请 Let's Encrypt）
- [ ] 数据库定期自动备份
- [ ] 公众号 AppSecret 存入项目 `.env`（当前在 `/tmp/.mp_app_secret`）

---

## 七、微信公众号接入（已验证）

### 当前状态
- 类型：订阅号
- AppID：`wx567a639466e247cd`
- AppSecret：已重置，存放于服务器 `/tmp/.mp_app_secret`
- 白名单 IP：`8.134.248.11`
- 草稿 API：**✅ 已验证可用**
  - 流程：获取 Token → 上传封面图获取 media_id → 调用 draft/add 创建草稿
  - 当前模式：`WECHAT_MP_DRAFT_MODE=manual`（手动复制）
  - 可切换为 `api` 模式实现自动创建草稿

### 公众号 API 测试脚本

```bash
# 1. 存储 AppSecret
echo '你的AppSecret' > /tmp/.mp_app_secret
chmod 600 /tmp/.mp_app_secret

# 2. 测试脚本
/tmp/test-mp.sh
```

---

## 八、微信小程序接入

### 当前状态
- 已注册（审核中）
- 类目：待确认（**非游戏类目**）
- 流量主：需上线后有流量才能开通
- 广告位：开通流量主后创建激励视频广告位

### 开发阶段先用模拟模式
```env
AD_MODE=mock
```

拿到 adUnitId 后切换：
```env
AD_MODE=wechat
MINIPROGRAM_AD_UNIT_ID=你的广告位ID
```

---

## 九、故障排查

```bash
# 容器没启动？
docker compose ps

# API 报 500？
docker compose logs -f app

# 端口被占用？
sudo lsof -i :39800
sudo lsof -i :5432

# 数据库连不上？
docker compose exec postgres psql -U gzh_expert -d gzh_expert

# 反向代理不工作？
sudo nginx -t
sudo nginx -s reload
sudo nginx -T | grep gzh.relexplace

# 磁盘空间？
df -h
docker system df
docker system prune -f  # 清理无用镜像（谨慎）

# API 直连测试
curl http://127.0.0.1:39800/api/health
curl http://gzh.relexplace.com/api/health
```