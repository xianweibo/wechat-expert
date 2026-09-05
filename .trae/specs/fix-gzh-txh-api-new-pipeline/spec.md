# 修复 NAS gzh-txh-api 走新流程 Spec

## Why

yuanbao 调用链路：`yuanbao → 127.0.0.1:41090（STCP visitor）→ NAS:41090 → gzh-txh-api/server.py`。

NAS 上的 [gzh-txh-api/server.py](file:///z:/代码/养龙虾/公众号专家/gzh-txh-api/server.py) 走的是**完全旧流程**：
- `minimax_summary(title, desc)` 无字幕（prompt 写死"无字幕；请基于简介合理推断"）
- `build_html` 含"没想到啊，我才没休息几天又可以玩了。"
- 顶部声明无加粗、段落无留白、无首句加粗、无 `### → <h3>` 转换
- 封面用硬编码生活化 prompt（咖啡/植物/灯笼），违反 project_rules
- LLM 用 MiniMax-M2.7（anthropic 兼容），不是火山方舟

前一个 spec `align-bilibili-summary-with-new-pipeline` 改的是阿里云 `src/index.ts` 的 `/api/bilibili/summary`，**不在这条链路上**，未解决用户问题。

## What Changes

- **修改** `gzh-txh-api/server.py`：
  - `bilibili_view` 返回增加 `cid` 字段
  - 新增 `bilibili_subtitle(bvid, cid)` 函数，调 mp_proxy `/api/admin/bilibili-subtitle`
  - `minimax_summary` 改为 `minimax_summary(title, desc, subtitle)`：字幕非空时以字幕为数据源；改用火山方舟 ARK API（OpenAI 兼容），复刻 `gzh_v2_server.py` 的 prompt（首句加粗 + 6-8 要点 + 1500-2000 字）
  - 新增 `rewrite_title(title, desc)` 标题改写
  - `minimax_cover` 改为 LLM 生成封面 prompt + 调 MiniMax image-01-live（金融终端质感，严禁生活化元素）
  - 新增 `_summary_to_html(summary)` 函数：`### → <h3>`、段落留白、`**xx** → <strong>`、无加粗时首句自动加粗
  - `build_html` 改为 `build_html(summary, fyi_links, title)`：顶部声明加粗 + 删"没想到啊" + FYI 标题 + 底部声明
  - `process_draft` 插入拿字幕步骤
- **新增** 环境变量（NAS docker-compose.yml 或 .env）：
  - `ARK_BASE_URL`、`ARK_API_KEY`、`ARK_MODEL`
  - `STYLE_PATH`（可选，风格档案路径）
- **部署**：SCP server.py 到 NAS `/vol2/1000/docker_related/gzh-txh-api/`，重启 docker 容器

## Impact
- Affected code: `gzh-txh-api/server.py`（主要改动）
- NAS 部署：SCP + docker restart
- yuanbao 无需改动（调用方式不变）

## ADDED Requirements
### Requirement: 字幕作为数据源
WHEN body 含 bvid THEN 服务端调 bilibili-subtitle 拿字幕，LLM 以字幕为唯一数据源生成总结

### Requirement: 新 HTML 结构
按 project_rules.md 第 4 节：顶部声明加粗 + 删"没想到啊" + 段落留白 + 首句加粗 + FYI + 底部声明
