# Changelog

## v0.4.0 - 2026-07-15

- 新增持久化任务队列，统一支持 `PARSE_BOOK`、`GENERATE_AUDIO`、`PREFETCH_CHAPTER_AUDIO`。
- Job 增加优先级、去重键、最大尝试次数、下次重试、开始时间和完成时间。
- PostgreSQL worker 使用 `FOR UPDATE SKIP LOCKED` 领取任务，支持多 worker 并发保护。
- 任务失败按指数退避重试；运行超时任务自动回收到队列，耗尽次数后进入最终失败。
- 上传、句子音频和章节预生成接口全部改为持久化入队，不再依赖 FastAPI `BackgroundTasks`。
- 前端播放器等待异步音频就绪，章节预生成使用独立章节任务。
- 管理员后台新增任务状态列表、失败原因、尝试次数和手动重试。
- `start-dev.bat` 自动迁移并启动 worker；E2E 后端同步启动隔离 worker。
- 新增队列、重试、超时回收、管理员任务 API 和章节预生成测试。

## v0.3.1 - 2026-07-15

- 将前端 `App.tsx` 从约 1400 行缩减为路由和模块编排入口。
- 拆出登录、阅读器、管理员审核页面，以及侧栏、播放器、删除确认组件。
- 拆出认证、书库、阅读播放、阅读进度和管理员审核 hooks。
- 保持现有 API、页面路径、CSS 类名和 E2E 测试标识兼容。
- 旧管理员接口在 OpenAPI 中标记为 deprecated，新代码继续使用 `/api/admin/...`。
- 增加隔离 SQLite E2E 覆盖入口；默认 PostgreSQL E2E 路径保持不变。
- 修复 Playwright 新版本 Cookie 参数兼容问题。
- 统一前端、后端包和 FastAPI 元数据版本为 `0.3.1`。
- 验收通过：后端 29 个测试、ruff、前端生产构建、5 个浏览器 E2E 流程。

## v0.3-local-mvp

- 完成本地听书 MVP：TXT/EPUB 上传解析、章节/段落/句子结构、逐句播放、音频缓存、章节预生成。
- 完成登录注册和 HttpOnly Cookie 登录态，阅读进度按用户隔离。
- 完成公共书库和上传审核最小闭环，管理员可批准/拒绝并查看审批历史。
- 完成 Playwright E2E 独立测试环境，避免写入真实开发库。
- 新增 `/api/admin/books/reviews` 和 `/api/admin/books/{book_id}/review` 管理员接口；旧 `/api/books/admin/reviews` 和 `/api/books/{book_id}/review` 暂保留兼容。
- 新增切句黄金测试集和 TTS golden 样例，后续朗读优化先按固定样例评测。

## 下一阶段候选

- 管理员后台增强：批量审批、复杂筛选、用户管理、权限分层。
- EPUB 解析稳健性：章节标题识别、空段落清理、脚注/目录/版权页过滤。
- 更自然的小说朗读：在 golden 样例上稳定提升，再考虑多角色音色分配。
