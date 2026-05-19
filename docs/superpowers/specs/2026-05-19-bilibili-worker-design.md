# B站充电视频总结 Worker - 设计规格

> 最后更新：2026-05-19
> 状态：已批准

---

## 1. 项目概述

| 项目 | 值 |
|------|---|
| 名称 | gzh-worker |
| 定位 | 每日 B 站充电视频总结 + 公众号草稿创建 |
| 部署位置 | NAS (192.168.9.3) |
| 运行方式 | Docker 容器 + cron 定时任务 |
| 技术栈 | Node.js 20 + TypeScript + axios |
| 总结 AI | MiniMax M2.7 |

---

## 2. 角色说明

| 角色 | UID | 说明 |
|------|-----|------|
| 我 | `144796213` | 运行 Worker 的账号 |
| 目标 UP 主 | `290663424` | 需要爬取其充电视频的 UP 主 |

---

## 3. 架构

```
NAS (192.168.9.3) - gzh-worker 容器
    │
    └─ 每天 12:00 (cron)
         │
         ▼
    ┌─────────────────────────┐
    │  1. 获取目标 UP 主最新视频列表
    │     (uid: 290663424)
    │     Cookie: SESSDATA + bili_jct
    └─────────────────────────┘
         │
         ▼
    ┌─────────────────────────┐
    │  2. 筛选充电视频
    │     判断是否有付费/充电内容
    │     记录上次抓取的 bvid，避免重复
    └─────────────────────────┘
         │
         ▼
    ┌─────────────────────────┐
    │  3. 获取字幕 + 简介
    │     - 自动字幕 (B 站 AI 生成)
    │     - 视频简介/描述
    │     - 不爬评论
    └─────────────────────────┘
         │
         ▼
    ┌─────────────────────────┐
    │  4. 调用 MiniMax M2.7 总结
    │     拼接字幕 + 简介
    │     生成精华总结
    └─────────────────────────┘
         │
         ▼
    ┌─────────────────────────┐
    │  5. POST 到阿里云 API
    │     http://8.134.248.11:3000
    │     /api/bilibili/summary
    │     发送: title + summary + source
    └─────────────────────────┘
         │
         ▼
    ┌─────────────────────────┐
    │  阿里云服务器
    │  6. 调用微信公众号草稿 API
    │     创建草稿 (需先上传封面)
    └─────────────────────────┘
```

---

## 4. 目录结构

```
gzh-worker/
├── src/
│   ├── index.ts           # 入口，cron 主逻辑
│   ├── bilibili.ts        # B 站爬取 (视频列表/字幕/简介)
│   ├── minimax.ts         # MiniMax M2.7 总结
│   └── poster.ts          # 发送到阿里云 API
├── .env                   # 配置文件 (不提交 Git)
├── package.json
├── tsconfig.json
├── Dockerfile             # 镜像构建
└── docker-compose.yml     # 容器编排 + cron
```

---

## 5. 环境变量

```env
# B 站登录态
BILIBILI_SESSDATA=51CjC...
BILIBILI_BILI_JCT=84b14a38d9df625098c9fe7fe338b421
BILIBILI_UID=144796213

# 目标 UP 主
TARGET_UP_UID=290663424

# MiniMax
MINIMAX_API_KEY=sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c99

# 阿里云服务器
ALIYUN_API_URL=http://8.134.248.11:3000/api/bilibili/summary

# 存储 (防止重复抓取)
LAST_BVID_FILE=/app/data/last_bvid.txt
```

---

## 6. 核心逻辑

### 6.1 定时任务 (cron)

- 时间：每天 12:00 (北京时间)
- 使用 node-cron 实现
- 容器启动时自动调度

### 6.2 去重机制

- 将上次抓取的 bvid 记录到 `LAST_BVID_FILE`
- 抓取前先对比，有新视频才继续
- 抓取成功后更新 bvid

### 6.3 B 站 API 调用

```typescript
// 获取视频列表
GET https://api.bilibili.com/x/space/wbi/arc/search
  ?mid=290663424
  &pn=1
  &ps=10
  &order=pubdate

// 获取字幕
GET https://api.bilibili.com/x/player/v2
  ?bvid={bvid}

// 获取视频详情
GET https://api.bilibili.com/x/web-interface/view
  ?bvid={bvid}
```

### 6.4 字幕获取

- 优先获取 UP 主上传的字幕文件
- 其次获取 B 站自动生成的字幕
- 字幕格式为 ASS/SRT，需解析为纯文本

### 6.5 MiniMax M2.7 总结

```typescript
// MiniMax API endpoint
POST https://api.minimax.chat/v1/text/chatcompletion_v2

// prompt 设计
"你是一个财经学习内容整理助手。请根据以下视频字幕和简介，生成一段精华总结：

视频标题：{title}
视频简介：{description}
字幕内容：{subtitle_text}

要求：
- 提取核心要点，3-5 条
- 用通俗易懂的语言
- 不复述原话，用自己语言重构
- 保持中立，不预测涨跌
- 篇幅控制在 300 字以内
"
```

### 6.6 发送到阿里云

```typescript
POST {ALIYUN_API_URL}
Content-Type: application/json

{
  "title": "视频标题",
  "summary": "AI 生成的总结",
  "source": {
    "bvid": "BVxxxx",
    "url": "https://bilibili.com/video/BVxxxx",
    "up_uid": 290663424,
    "up_name": "UP主名",
    "published_at": "2026-05-19"
  }
}
```

---

## 7. 错误处理

| 场景 | 处理方式 |
|------|---------|
| B 站 Cookie 失效 | 记录错误日志，发送告警（后续扩展） |
| 无新视频 | 直接退出，不调用 AI |
| MiniMax API 失败 | 重试 2 次，失败则记录并退出 |
| 阿里云 API 失败 | 重试 2 次，失败则记录并退出 |
| 字幕获取失败 | 使用简介代替，继续流程 |

---

## 8. Worktree 多 Session 开发策略

### Session 类型

| Session | 用途 | 分支名 |
|---------|------|--------|
| infra/bilibili-api | B 站爬取逻辑 (bilibili.ts) | `feat/bilibili-api` |
| infra/minimax-summary | MiniMax 总结逻辑 (minimax.ts) | `feat/minimax-summary` |
| infra/poster | 发送逻辑 (poster.ts) | `feat/poster` |
| infra/cron-setup | cron + 入口 (index.ts) | `feat/cron-setup` |
| infra/docker | Docker 部署 (Dockerfile + compose) | `feat/docker` |

### 开发顺序

1. `feat/bilibili-api` → 最先，验证 B 站 API 能通
2. `feat/minimax-summary` → 验证 AI 能调
3. `feat/poster` → 验证能发到阿里云
4. `feat/cron-setup` → 整合所有模块
5. `feat/docker` → 容器化部署

---

## 9. 已批准的决策

- [x] 使用 Node.js + TypeScript (与现有项目统一)
- [x] 使用 MiniMax M2.7 进行总结
- [x] NAS 部署，Docker 容器运行
- [x] 每天 12:00 定时执行
- [x] 只抓字幕 + 简介，不爬评论
- [x] 摘要发送后由阿里云服务器创建公众号草稿
- [x] 使用 Cookie 认证 (SESSDATA + bili_jct)
- [x] 去重机制：记录上次 bvid

---

## 10. 待定

- [ ] 公众号草稿模板（用户说后续再聊）
- [ ] 封面图策略（草稿需要 thumb_media_id）
- [ ] 告警机制（Cookie 失效等）