# Changelog

## v0.3-local-mvp

- 完成本地听书 MVP：TXT/EPUB 上传解析、章节/段落/句子结构、逐句播放、音频缓存、章节预生成。
- 完成登录注册和 HttpOnly Cookie 登录态，阅读进度按用户隔离。
- 完成公共书库和上传审核最小闭环，管理员可批准/拒绝并查看审批历史。
- 完成 Playwright E2E 独立测试环境，避免写入真实开发库。
- 新增 `/api/admin/books/reviews` 和 `/api/admin/books/{book_id}/review` 管理员接口；旧 `/api/books/admin/reviews` 和 `/api/books/{book_id}/review` 暂保留兼容。
- 新增切句黄金测试集和 TTS golden 样例，后续朗读优化先按固定样例评测。

## 下一阶段候选

- 管理员后台增强：批量审批、复杂筛选、用户管理、权限分层。
- 轻量 worker：扫描 pending job，统一处理解析、音频生成和章节预生成。
- EPUB 解析稳健性：章节标题识别、空段落清理、脚注/目录/版权页过滤。
- 更自然的小说朗读：在 golden 样例上稳定提升，再考虑多角色音色分配。
