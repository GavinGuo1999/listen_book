# Project Memory

## 固定约定

当用户说“收工”“下班”“今天到这里”“结束今天工作”等类似指令时，Codex 需要先更新项目交接记录，再结束本轮回复。

每次 Codex 修改会影响运行效果的后端或前端代码后，不在 Codex 工具里直接启动长驻服务。Windows 后台启动在当前环境里不稳定，容易出现工具长时间转圈。

默认流程改为：

1. Codex 跑短命令验证，例如 lint、build、接口测试
2. Codex 提醒用户用 `scripts\stop-dev.bat` 和 `scripts\start-dev.bat` 重启
3. 用户确认服务启动后，Codex 再做接口或页面可用性检查

服务启动后需要验证：

- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:5173/`

除非用户明确要求 Codex 尝试重启服务。

交接记录至少包括：

1. 今天完成了什么
2. 修改了哪些关键文件
3. 验证过什么命令或功能
4. 当前还没完成什么
5. 下一次继续时的优先任务
6. 必要的启动、测试、排错命令

优先更新：

- `docs/PROJECT_MEMORY.md`：高密度项目状态和恢复入口
- `docs/progress-YYYY-MM-DD.md`：当天详细进度

下次新会话开始时，优先读取本文件、当天/最近的 progress 文档和 README，再继续开发。

编码注意：

- Markdown 文档统一按 UTF-8 读取和写入。
- 如果 PowerShell 输出中文乱码，优先使用：

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
Get-Content -Path docs\PROJECT_MEMORY.md -Encoding UTF8
```

- `docs/PROJECT_MEMORY.md` 当前文件内容本身是正常中文；之前看到乱码是终端输出编码问题。

## 当前项目摘要

项目是一个家庭读书/听书 Web 应用，目标是支持公共书库、多用户独立进度、上传电子书、解析章节/段落/句子，并按句朗读和缓存音频。

当前技术栈：

- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- Frontend: React + TypeScript + Vite
- Storage: local filesystem under `storage/`

当前已完成的第一阶段能力：

- FastAPI 后端基础结构
- PostgreSQL 数据模型和 Alembic 迁移
- TXT/EPUB 上传和后台自动解析
- 非 UTF-8 TXT 解析回退：`utf-8-sig`、`utf-8`、`gb18030`、`big5`
- Book -> Chapter -> Paragraph -> Sentence 数据结构
- React 前端书库/阅读页基础 UI
- 前端轮询书籍解析状态，`uploaded/parsing` 变 `ready` 后自动加载正文
- 句子展示、点击高亮、上一句/下一句
- 第一版真实 TTS 链路：Edge TTS 生成 MP3，按句缓存到 `storage/audio`
- 前端点击句子/播放按钮后真实播放音频
- 当前句播放结束后自动切到下一句
- 基于句尾标点的轻量朗读语气增强：疑问句目前不再特殊升调，感叹句略增强，省略号放慢
- 音频预生成：批量预热接口、状态查询接口、句子状态点、章节“预生成本章”
- 已有书籍删除：删除书籍、正文结构、阅读状态、相关任务、上传源文件和已生成音频
- 前端删除交互：书库删除入口、页面内确认弹窗、删除当前书后清空阅读/播放/缓存状态
- 阅读进度保存最小版：默认本地用户、按书保存/读取当前句子、重新打开书时恢复高亮句
- 精确播放位置保存/恢复：播放中低频保存 `audio_position_ms`，暂停立即保存，恢复播放时设置 `<audio>.currentTime`
- 后端自动化测试第一批：上传解析、GB18030 解析、阅读进度、书籍删除清理
- 后端音频接口测试：生成、缓存、失败重试、prefetch/status、文件端点安全检查
- 正式浏览器 E2E smoke：上传 TXT、等待解析、阅读进度恢复、删除临时书
- 登录/多用户进度隔离：注册、登录、当前用户、退出登录、Cookie Session 鉴权
- 独立 `/login` 登录/注册页；未登录不能访问书库、上传、阅读、音频、进度或审批接口
- 登录后阅读进度按用户隔离
- 公共书库 + 上传审批最小闭环：
  - 书籍有独立 `review_status`：`pending_review`、`approved`、`rejected`
  - 管理员上传自动发布，普通用户上传默认待审批
  - 管理员账号由 `.env` 显式 bootstrap，不再使用“第一个注册用户自动成为管理员”
  - 管理员可通过 `/admin` 后台或 `PATCH /api/books/{book_id}/review` 批准/拒绝
  - 拒绝时可填写 `review_note` 审批备注
  - 管理员审核中心可查看待审批/解析失败/已拒绝/全部筛选、分页、上传者、上传时间和审批历史
  - 审批历史写入 `book_review_events`：审批人、审批时间、原状态、新状态、历史备注
  - 普通用户只能看到已发布书籍和自己上传的待审/拒绝书籍
  - 章节、进度、音频接口都会检查书籍可见性，避免绕过审批读取正文
- 小说朗读语气基础优化：
  - Edge TTS `model_version=13`
  - 对白略提高音高/加快，和旁白做基础区分
  - 长句、逗号密集句、省略号/破折号会放慢
  - “低声/轻声/喃喃”等轻声标记降低音高，“大声/喊道/怒道”等强情绪标记提高音高
- 登录/注册浏览器 E2E 脚本已补：注册、退出、重新登录
- 浏览器 E2E 已覆盖审批路径：普通用户上传待审、其他用户不可见、本地管理员待审批列表批准、批准后其他用户可见
- 浏览器 E2E 已隔离到独立 PostgreSQL 测试库 `listen_book_e2e` 和 `storage/e2e`，不再写入真实开发库
- 服务启动后的 API smoke 脚本：`scripts/smoke_api.py`
- Windows 启停脚本：`scripts\start-dev.bat`、`scripts\stop-dev.bat`
- 开发库重置脚本：`scripts/reset_dev_data.py`，会清理业务数据和 storage，并按 `.env` 重建 bootstrap 管理员

当前主要未完成：

- 更完整的管理员后台体验：批量审批、复杂筛选、后台权限分层等
- PDF 解析暂不做；当前上传格式明确收敛为 TXT/EPUB
- 更自然的小说朗读：真正的多角色音色分配、按章节/角色学习风格

## 最近交接记录：2026-07-03

今天整理：

- 确认最新提交 `240251b test: isolate playwright e2e environment` 已将 Playwright E2E 切到独立测试环境：
  - PostgreSQL 测试库：`listen_book_e2e`
  - 测试 storage：`storage/e2e`
  - 测试后端：`127.0.0.1:8001`
  - 测试前端：`127.0.0.1:5174`
- 修正 README 和 runbook 里的本机项目路径，从 `D:\listen_book` 更新为 `D:\Projects\listen_book`。
- 当前 `.env` 仍包含真实本地 bootstrap 管理员密码，不要提交 `.env`。

下一步优先任务：

1. 管理员后台继续增强：批量审批、复杂筛选、后台权限分层。
2. 做用户管理页：查看用户、启停用户、设置/取消管理员。
3. 管理员 API 路径后续可逐步迁到 `/api/admin/...`。

## 最近交接记录：2026-07-04

本轮按静态审查建议完成：

- 将项目文档定位为 `v0.3-local-mvp`，补充当前能做什么、当前不做什么和稳定版本验收口径。
- 新增 `CHANGELOG.md`，记录 v0.3 本地 MVP 能力和下一阶段候选任务。
- 管理员接口开始迁到独立命名空间：
  - 新增 `GET /api/admin/books/reviews`
  - 新增 `PATCH /api/admin/books/{book_id}/review`
  - 旧 `GET /api/books/admin/reviews` 和 `PATCH /api/books/{book_id}/review` 仍保留兼容
  - 前端 API 调用已切到 `/api/admin/...`
- 切句器从单一正则升级为小型扫描器：
  - 保持中文句号、问号、叹号和引号处理
  - 新增英文句号切分
  - 避免在 `Mr.`、`p.m.`、`a.m.`、`e.g.`、`i.e.` 等常见缩写中误切
- 新增切句黄金测试集 `backend/tests/test_text_splitter.py`。
- 新增 TTS golden 文本样例：
  - `samples/tts_golden/chinese_dialogue.txt`
  - `samples/tts_golden/chinese_narration.txt`
  - `samples/tts_golden/english_narration.txt`
  - `samples/tts_golden/mixed_symbols.txt`
- 新增 `docs/tts-evaluation.md`，记录自然度、断句、对白感、速度和奇怪停顿的 1-5 分评测表。
- `.gitignore` 新增 `.playwright-mcp/`，避免浏览器工具临时文件污染工作区。

本轮验证：

- 重新运行 `.venv\Scripts\python.exe -m pip install --no-cache-dir -e backend[dev]`，修正本机 editable install 仍指向旧路径 `D:\listen_book\backend` 的问题。
- `.venv\Scripts\python.exe -m pytest backend\tests -q` 通过，当前为 `29 passed`。
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py` 通过。
- `cd frontend && npm run build` 通过。
- `cd frontend && npm run test:e2e` 未跑起：本机缺少 PostgreSQL 测试库 `listen_book_e2e`，需先用管理员执行 `CREATE DATABASE "listen_book_e2e" OWNER listen_book_app;`。
- `git diff --check` 通过，仅有 Windows 换行提示。

下一步优先任务：

1. 拆前端 `App.tsx`，优先抽 `useAuth`、`useBooks`、`useAdminReview` 和页面组件。
2. 做用户管理页：查看用户、启停用户、设置/取消管理员。
3. 设计轻量 worker：扫描 pending job，统一处理解析、音频生成和章节预生成。

## 最近交接记录：2026-06-25

今天完成：

- 重做认证入口和登录态边界：
  - `/login` 独立登录/注册页
  - 未登录请求业务 API 返回 401，不再回退到 `local`
  - 登录态改为后端 HttpOnly Cookie：`listen_book_session`
  - 前端不再使用 `localStorage` 保存 token
- 注册页去掉“显示名”，后端默认 `display_name = username`。
- 管理员初始化改为显式 bootstrap：
  - `.env` 配置 `LISTEN_BOOK_BOOTSTRAP_ADMIN_USERNAME`
  - `.env` 配置 `LISTEN_BOOK_BOOTSTRAP_ADMIN_PASSWORD`
  - 服务启动时确保该用户存在、启用、是管理员，并同步配置密码
  - 普通注册用户永远不是管理员
  - 删除“第一个注册用户自动成为管理员”的规则
- 管理员后台入口改为 `/admin`，普通业务页不再混入审批中心。
- 清理开发库污染数据：
  - 新增 `scripts/reset_dev_data.py`
  - 已清理测试用户、旧 `local` 用户、书籍、章节、句子、音频、任务、审批记录和 storage 文件
  - 清理后按 `.env` 重建 `admin` 管理员
- 改善认证错误提示：
  - 缺用户名/密码、用户名不存在、密码错误、用户名重复、用户停用等都返回明确中文提示
  - 前端解析 JSON `detail`，不再直接显示 `{"detail":"..."}`
  - 前端登录/注册表单增加基础校验
- 更新 README、runbook 和当天 progress 文档。

今天验证：

- `.venv\Scripts\python.exe -m pytest backend\tests` 通过，当前为 `24 passed`
- `.venv\Scripts\python.exe -m ruff check backend scripts` 通过
- `cd frontend && npm run build` 通过
- `cd frontend && npx playwright test --list` 通过，当前发现 `5` 个 E2E 用例

当前注意事项：

- 当前 `.env` 含真实 bootstrap 管理员密码，不要提交 `.env`。
- 这一天最后未完整跑 Playwright E2E，因为当时 E2E 仍会写真实开发库；该问题已在后续提交 `240251b` 中修复。
- 如果要让正在运行的服务加载新认证逻辑和 `.env`，需要重启服务：

```bat
scripts\stop-dev.bat
scripts\start-dev.bat
```

下次优先任务：

1. 管理员后台继续拆分 API 路径，例如迁到 `/api/admin/...`。
2. 做用户管理页：查看用户、启停用户、设置/取消管理员。

## 最近交接记录：2026-06-23

今天完成：

- 完成独立管理员待审批列表：
  - 本地 `local` 管理员和正式管理员可在侧边栏看到“待审批书籍”
  - 待审批列表显示数量、书名、解析状态
  - 管理员可集中批准发布或拒绝
  - 拒绝时可填写可选审批备注，写入 `review_note`
- 收紧前端上传入口：
  - 上传控件只接受 `.txt,.epub`
  - 页面明确提示“PDF 暂不接入”
- 补浏览器 E2E 审批路径：
  - API 注册非管理员用户
  - 普通用户通过 UI 登录并上传 TXT
  - 上传者看到“待审批”
  - 另一个普通用户看不到待审书
  - 本地管理员在独立待审批列表批准
  - 批准后其他普通用户可见
- 优化小说朗读基础语气：
  - Edge TTS 版本提升到 `13`，避免复用旧缓存
  - 对白、长句、逗号密集句、省略号/破折号、轻声标记、强情绪标记都会影响语速/音高
  - 疑问句仍保持中性，不恢复特殊升调
- 补 TTS 语气规则单元测试。
- 更新 README、runbook 和本项目记忆。

今天验证：

- `.venv\Scripts\python.exe -m pytest backend\tests -q` 通过，当前为 `21 passed`
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py` 通过
- `cd frontend && npm run build` 通过
- `cd frontend && npm run test:e2e` 通过，当前为 `4 passed`

当前注意事项：

- 本轮 E2E 通过一次性 PowerShell 命令临时启动后端；如果后端是本轮启动的，测试结束后已停止。
- Playwright 仍只自动启动前端；常规手动运行 E2E 前仍需保证后端 `127.0.0.1:8000` 已启动。
- 本地 `master` 仍比 `origin/master` 多提交，当前工作区改动准备收口提交，尚未推送。

下次优先任务：

1. 如需实机确认，运行 `scripts\stop-dev.bat` 和 `scripts\start-dev.bat` 后打开页面复核管理员待审批列表。
2. 可继续做批量审批、复杂筛选或后台权限分层。
3. 或继续推进真正的多角色小说朗读。

## 最近交接记录补充：2026-06-23 审批后台增强

本轮继续完成：

- 新增审批审计记录：
  - 新表 `book_review_events`
  - 新迁移 `backend/alembic/versions/20260623_0003_book_review_events.py`
  - 每次管理员审批都会记录审批人、审批时间、原状态、新状态、备注
- 新增管理员审计接口：
  - `GET /api/books/admin/reviews`
  - 仅管理员可用
  - 返回上传者信息和 `review_history`
- 增强前端管理员审核中心：
  - 待审批、解析失败、已拒绝、全部筛选
  - 客户端分页
  - 展示上传者、上传时间、审核状态
  - 展示当前备注和审批历史
- 测试增强：
  - 后端测试覆盖审计接口、非管理员 403、审批事件字段
  - E2E 覆盖审核中心中上传者展示、审批后历史展示

本轮验证：

- 已执行本机数据库迁移：`20260622_0002 -> 20260623_0003`
- `.venv\Scripts\python.exe -m pytest backend\tests -q` 通过，当前为 `21 passed`
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py` 通过
- `cd frontend && npm run build` 通过
- `cd frontend && npm run test:e2e` 通过，当前为 `4 passed`

## 最近交接记录：2026-06-22

今天完成：

- 确定书库模型方向：公共书库为主，普通用户上传需要管理员审批；EPUB 解析当前够用，PDF 暂不继续。
- 新增书籍审核数据模型和迁移：
  - `backend/alembic/versions/20260622_0002_book_review_workflow.py`
  - `Book.uploader_id`
  - `Book.review_status`
  - `Book.review_note`
- 新增公共书库可见性规则：
  - 管理员可见全部书籍
  - 普通用户可见已批准公共书籍 + 自己上传的待审/拒绝书籍
  - 章节、进度、音频生成/预取/状态/文件接口都会校验书籍可见性
- 新增管理员审批能力：
  - `PATCH /api/books/{book_id}/review`
  - 前端书库行对管理员显示“批准/拒绝”
  - 非管理员审批返回 403
- 上传规则调整：
  - 管理员上传自动 `approved`
  - 普通用户上传默认 `pending_review`
  - 支持格式收敛为 TXT/EPUB；PDF 上传会被拒绝
- 管理员初始化规则：
  - 第一个正式注册用户自动成为管理员
  - 默认本地用户 `local` 仍为管理员
- 补登录/注册浏览器 E2E 脚本：
  - 注册
  - 退出登录
  - 重新登录
- 实机验证时修复：
  - `scripts/smoke_api.py` 使用 `httpx.Client(..., trust_env=False)`，避免本机 API smoke 被环境代理拦到 502
  - 注册成功和退出登录后默认切回“登录”页签，避免重新登录时误发注册请求导致 409
- 更新前端类型、API、书库状态徽标和审批按钮。
- 补后端自动化测试：
  - 普通用户上传待审批
  - 其他普通用户不可见未审批书籍
  - 非管理员不能审批
  - 管理员批准后公共可见

今天验证：

- `.venv\Scripts\python.exe -m pytest backend\tests -q` 通过，当前为 `16 passed`
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py` 通过
- `cd frontend && npm run build` 通过
- `.venv\Scripts\python.exe scripts\smoke_api.py` 通过
- `cd frontend && npm run test:e2e` 通过，当前为 `3 passed`
- `git diff --check` 通过（仅有 Windows 换行提示）

当前注意事项：

- Alembic 迁移 `20260622_0002` 已在本机执行过。
- 本轮 Codex 已后台启动过后端 `127.0.0.1:8000` 和前端 `127.0.0.1:5173` 完成实机验证；验证结束后已用 `scripts\stop-dev.bat` 停止服务。
- 本地 `master` 原本比 `origin/master` 多 4 个提交；本轮还有未提交改动，尚未推送。

下次优先任务：

1. 手测审批流：普通用户上传、管理员批准/拒绝、其他用户可见性。
2. 选择是否做独立管理员待审批列表。
3. 否则转向小说朗读体验优化。

## 最近交接记录：2026-06-20

今天完成：

- 新增浏览器 E2E：
  - `frontend/playwright.config.ts`
  - `frontend/e2e/books.spec.ts`
  - 覆盖首页加载、上传 TXT、等待解析、阅读进度恢复、删除临时测试书
  - 测试刻意不触发真实 TTS，避免依赖外部网络
- 扩展音频接口和失败路径测试：
  - `backend/tests/test_audio_api.py`
  - 覆盖音频生成、缓存复用、TTS 失败标记、失败重试、prefetch/status、文件端点安全检查
- 完成 EPUB 解析最小版：
  - `backend/app/services/epub.py`
  - `backend/app/workers/parse_books.py`
  - 使用 Python 标准库读取 EPUB zip、container、OPF manifest/spine、XHTML/HTML 正文
  - 按章节/段落/句子入库
  - 无效 EPUB 会将书籍标记为 `failed`
- 完成登录/多用户进度隔离最小闭环：
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - 前端侧栏新增账号卡、登录/注册、退出登录
  - API 自动携带 token
  - 无 token 时仍使用默认本地用户 `local`
  - 登录用户的阅读进度互相隔离
- 更新 README 和 runbook：
  - 记录 TXT/EPUB 支持
  - 记录 E2E、auth、音频测试覆盖范围

今天提交：

- `7f6dee0 test: add browser e2e and audio api coverage`
- `7454f13 feat: parse epub uploads`
- `ce3047c feat: add auth and user progress isolation`

今天验证：

- 用户实机运行 E2E：`2 passed`
- `.venv\Scripts\python.exe -m pytest backend\tests -q` 通过，当前为 `15 passed`
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py` 通过
- `npm run build` 通过
- `git diff --check` 通过

当前注意事项：

- 今天没有推送远端；本地 `master` 比 `origin/master` 多 3 个功能提交，另有本交接文档提交待处理/待推送。
- 后端和前端代码变更后，明天实机测试前建议先重启服务：

```bat
scripts\stop-dev.bat
scripts\start-dev.bat
```

- 登录功能是最小闭环：已实现注册、登录、token、当前用户、退出登录和进度隔离；尚未实现完整书库归属/权限隔离。
- 当前浏览器 E2E 仍覆盖未登录本地模式；登录链路 E2E 还没补。
- PDF 解析仍未实现。

明天建议测试顺序：

1. 先启动服务并检查：
   - `http://127.0.0.1:8000/api/health`
   - `http://127.0.0.1:5173/`
2. 跑自动化：
   - `.venv\Scripts\python.exe -m pytest backend\tests -q`
   - `cd frontend && npm run test:e2e`
3. 浏览器手测：
   - 未登录本地模式能否正常上传/阅读/保存进度
   - 注册一个新用户并登录
   - 登录用户上传 TXT/EPUB 是否能解析
   - 登录用户 A 和未登录本地模式/用户 B 的阅读进度是否互不覆盖
   - 退出登录后是否回到本地模式

下次优先任务：

1. 补登录/注册浏览器 E2E。
2. 做书库归属/权限隔离设计：公共书库还是用户私有书库需要先定。
3. 继续 PDF 解析，或先完善 EPUB 解析质量。
4. 改善小说朗读体验。

## 最近交接记录：2026-06-19

今天完成：

- 优化已有书籍删除交互：
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - 将浏览器原生 `window.confirm` 改为页面内确认弹窗
  - 弹窗展示书名、删除影响范围、取消/确认按钮和删除中 loading
- 处理项目文档乱码问题：
  - 确认 `docs/PROJECT_MEMORY.md` 文件本身按 UTF-8 读取正常
  - 之前乱码是 PowerShell 输出编码问题
  - 已补充 UTF-8 读取说明
  - 已修正 `docs/progress-2026-06-18.md` 中关于乱码的旧备注
- 完成阅读进度保存最小版：
  - `GET /api/books/{book_id}/progress`
  - `PUT /api/books/{book_id}/progress`
  - 使用默认本地用户 `local`
  - 保存时校验 `sentence_id` 必须属于当前书籍
  - 前端加载章节后尝试恢复上次句子
  - 点击句子、上一句/下一句切换当前句时保存进度
- 完成精确播放位置保存/恢复：
  - 前端播放中每 5 秒保存一次 `audio_position_ms`
  - 暂停时立即保存当前播放位置
  - 切换上一句/下一句时保存新句子的播放位置为 `0`
  - 恢复书籍进度时保留后端返回的 `audio_position_ms`
  - 再次播放恢复出来的句子时设置 `<audio>.currentTime`
- 完成 v0.2 测试与稳定性第一批：
  - 新增 pytest 覆盖 TXT 上传解析、GB18030 解析、阅读进度、书籍删除清理
  - 新增 `scripts/smoke_api.py` 用于服务启动后的 API smoke 验收
  - 修复 dev 依赖 `httpx2` -> `httpx`
  - `Job.payload` 改为跨数据库兼容 JSON，PostgreSQL 下仍使用 JSONB
  - 解析 worker 显式转换 job payload 中的 `book_id` 为 UUID
  - 应用启动时自动创建 storage 子目录
  - 时间戳默认值改为 timezone-aware UTC
  - 重写 README 和 runbook，补充自动化验证与浏览器手工验收清单
- 新增当天交接记录：
  - `docs/progress-2026-06-19.md`

今天验证：

- `npm run build` 通过。
- 后端导入检查通过。
- `ruff check backend/app` 通过。
- Python AST 语法检查通过。
- 用户已验证已有书籍删除功能可用。
- `npm run build` 在精确播放位置保存/恢复改动后再次通过。
- 用户已实机验证精确播放位置保存/恢复可用。
- `.venv\Scripts\python.exe -m pytest backend\tests -q` 通过。
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py` 通过。
- `npm run build` 在 v0.2 稳定性改动后通过。
- 用户收工前反馈测试无明显问题；当前无阻塞问题。
- 尚未接入正式浏览器 E2E，浏览器播放路径暂按 `docs/runbook.md` 手工验收。

下次优先任务：

1. 增加正式浏览器 E2E 测试脚本。
2. 扩展音频接口测试和失败路径测试。
3. 开始 EPUB 解析。
4. 登录/多用户系统。

## 最近交接记录：2026-06-18

今天完成：

- 关闭问号特殊升调：
  - `backend/app/services/tts.py`
  - Edge TTS `model_version=12`
  - 疑问句现在和普通句一样使用 `+0% / +0Hz`
- 完善音频预生成体验：
  - `POST /api/audio/sentences/prefetch`
  - `POST /api/audio/sentences/status`
  - 前端显示句子音频状态点
  - 章节标题区有“预生成本章”按钮和进度
- 修复非 UTF-8 TXT 解析失败：
  - `backend/app/workers/parse_books.py`
  - TXT 读取按 `utf-8-sig`、`utf-8`、`gb18030`、`big5` 回退
- 修复中文断句正则：
  - `backend/app/services/text_splitter.py`
  - 使用稳定 Unicode 转义匹配中文标点和常见右引号/括号
- 已重新解析《增广贤文》：
  - book id: `f19c5b5a-2f0f-467e-a09a-4bfb5fae11b1`
  - status: `ready`
  - chapters: `1`
  - sentences: `350`
- 播放栏移到阅读正文上方：
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
- 新增测试样例和上传辅助脚本：
  - `samples/tts-test-sample.txt`
  - `scripts/upload_sample.py`
- 新增已有书籍删除：
  - `DELETE /api/books/{book_id}`
  - 删除数据库关联记录、上传源文件、已生成音频和相关任务
  - 前端书库列表新增删除入口
  - 删除前使用页面内确认弹窗
  - 删除当前选中书时清空阅读、播放、音频缓存和预热状态
- 新增阅读进度保存最小版：
  - `GET /api/books/{book_id}/progress`
  - `PUT /api/books/{book_id}/progress`
  - 使用默认本地用户 `local`
  - 前端选中书并加载章节后恢复上次句子
  - 点击句子、上一句/下一句切换当前句时保存进度

今天验证：

- `npm run build` 通过。
- 后端导入检查通过。
- ruff 检查通过。
- Python AST 语法检查通过。
- 用户已实机验证书籍删除功能可用。
- 《增广贤文》数据库状态确认 `ready`。
- 本地解析函数确认可读取 GB18030 TXT。

当前注意事项：

- 后端代码变更后，需要用户手动重启服务才能在浏览器中生效。
- 不要默认由 Codex 启动/重启长期服务；Windows 后台启动在当前工具环境里不稳定。
- `compileall` 在当前 Windows 环境可能因为 `__pycache__` 写权限报错；需要语法验证时可用 AST 解析替代。

下次优先任务：

1. 验证阅读进度保存：点到某句、刷新/重选书籍后应恢复高亮。
2. 做精确音频播放位置保存/恢复：保存 `audio_position_ms`，恢复时设置 `<audio>.currentTime`。
3. 补后端删除和进度接口的自动化测试。
4. 增加正式 E2E 测试脚本。
5. 开始 EPUB 解析。

## 最近交接记录：2026-06-17

今天完成：

- 新增 `docs/PROJECT_MEMORY.md`，约定收工时更新项目记忆。
- 明确 Codex 不再默认启动长驻服务，避免 Windows/Powershell 后台进程导致工具转圈。
- 新增 `scripts\start-dev.bat` 和 `scripts\stop-dev.bat`，用于用户本机启动/停止前后端。
- 后端上传书籍后会通过 FastAPI `BackgroundTasks` 自动触发一次解析任务。
- 前端会轮询处理中书籍状态，解析完成后自动加载正文。
- 修复未选句时点击“下一句”跳到第二句的问题。
- 新增音频接口：
  - `POST /api/audio/sentences/{sentence_id}`
  - `GET /api/audio/assets/{asset_id}/file`
- 安装并接入 `edge-tts`，默认中文音色 `zh-CN-XiaoxiaoNeural`。
- 音频按句生成 MP3 并缓存到 `storage/audio`。
- 前端使用隐藏 `<audio>` 播放句子音频。
- 播放结束后自动切换到下一句。
- Edge TTS provider 加入轻量 prosody 推断：
  - 普通句号：`+0%`, `+0Hz`
  - 疑问句：`+2%`, `+12Hz`
  - 感叹句：`+4%`, `+8Hz`
  - 省略号：`-6%`, `-4Hz`

今天验证：

- `npm run build` 通过。
- `.venv\Scripts\ruff.exe check --no-cache backend\app` 通过。
- FastAPI TestClient 上传 TXT 后自动解析到 `ready` 通过。
- `POST /api/audio/sentences/{sentence_id}` 能生成 `audio/mpeg` MP3。
- 问句音频生成测试通过，文件大小约 9792 bytes。

下次优先任务：

1. 做阅读/播放进度保存接口和前端自动保存。
2. 做一个简洁的用户体系占位：先支持本地默认用户，后续再加登录 UI。
3. 改善朗读体验：自动预生成后几句，减少切句等待。
4. 增加正式 E2E 测试脚本，而不是只靠手工点击。
5. 开始 EPUB 解析。

下次恢复上下文时先读：

- `docs/PROJECT_MEMORY.md`
- `docs/progress-2026-06-17.md`
- `docs/runbook.md`

## 常用命令

启动后端：

```powershell
cd D:\listen_book\backend
..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

启动前端：

```powershell
cd D:\listen_book\frontend
npm run dev -- --host 127.0.0.1
```

执行数据库迁移：

```powershell
cd D:\listen_book\backend
..\.venv\Scripts\alembic.exe upgrade head
```

手动运行 TXT 解析 worker：

```powershell
cd D:\listen_book
.venv\Scripts\python.exe -m app.workers.parse_books
```

前端构建：

```powershell
cd D:\listen_book\frontend
npm run build
```

后端 lint：

```powershell
cd D:\listen_book
.venv\Scripts\ruff.exe check --no-cache backend\app
```

## 最近交接记录：2026-07-15（v0.3.1）

本轮完成：

- 前端 `App.tsx` 从约 1400 行缩减到约 200 行，仅保留路由和跨模块编排。
- 新增 `frontend/src/pages/`：登录页、阅读页、管理员审核页。
- 新增 `frontend/src/components/`：应用侧栏、播放器、删除确认弹窗。
- 新增 `frontend/src/hooks/`：认证、书库、音频播放、阅读进度、管理员审核。
- 保留原有 API、页面路径、CSS 类名和 `data-testid`，拆分不改变用户流程。
- 旧管理员接口在 OpenAPI 中标记为 deprecated；前端继续使用 `/api/admin/...`。
- E2E 增加显式 SQLite 隔离模式，数据库文件限制在 `storage/e2e`，默认 PostgreSQL 模式保持不变。
- 修复 Playwright 1.61 Cookie 参数兼容问题。
- 前端、后端包和 FastAPI 元数据版本统一为 `0.3.1`。

本轮验证：

- `.venv\Scripts\python.exe -m pytest backend\tests -q`：`29 passed`。
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py`：通过。
- `cd frontend && npm run build`：通过。
- `cd frontend && npm run test:e2e:sqlite`：`5 passed`，覆盖登录、上传解析、进度恢复、删除和审批闭环。
- 默认 PostgreSQL E2E 仍需要一次性创建 `listen_book_e2e`；当前本机应用账号没有建库权限。

下一阶段优先任务：

1. 设计常驻轻量 worker，统一领取解析、音频生成和章节预生成任务。
2. 为任务补充开始/完成时间、重试策略、并发领取保护和后台失败重试入口。
3. 建立真实 EPUB 黄金样本库，覆盖标题、目录、脚注和版权页过滤。

## 最近交接记录：2026-07-15（v0.4.0）

本轮完成：

- 新增 Alembic 迁移 `20260715_0004`，扩展 Job 的优先级、去重、最大尝试次数、下次重试、开始和完成时间。
- 新增通用常驻 worker `app.workers.jobs`，统一处理书籍解析、句子音频和章节音频预生成。
- PostgreSQL 领取任务使用 `FOR UPDATE SKIP LOCKED`；失败任务指数退避，运行超时任务自动回收。
- 上传、音频生成和章节预生成改为持久化入队，不再依赖 FastAPI `BackgroundTasks`。
- 前端播放器会等待异步音频任务完成；章节按钮使用 `PREFETCH_CHAPTER_AUDIO`。
- 管理员后台新增任务列表、状态筛选、失败原因、尝试次数和手动重试。
- 新增 `GET /api/admin/jobs` 和 `POST /api/admin/jobs/{job_id}/retry`。
- `scripts/start-dev.bat` 会自动迁移并启动 worker、后端、前端；`stop-dev.ps1` 只停止属于当前项目的进程。
- E2E 测试后端会启动隔离 worker；SQLite E2E 初始化会重建隔离测试表结构。
- 本机开发 PostgreSQL 已迁移到 `20260715_0004 (head)`。

本轮验证：

- `.venv\Scripts\python.exe -m pytest backend\tests -q`：`35 passed`。
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py scripts\e2e_env.py scripts\e2e_setup.py scripts\run_e2e_backend.py scripts\run_e2e_sqlite.py`：通过。
- `cd frontend && npm run build`：通过。
- `cd frontend && npm run test:e2e:sqlite`：`5 passed`。
- Alembic PostgreSQL `upgrade head` 与 `current`：`20260715_0004 (head)`。

下一阶段优先任务：

1. 建立真实 EPUB 黄金样本库，覆盖标题、目录、脚注和版权页过滤。
2. 增加任务保留/清理策略，避免长期运行后 done job 无限增长。
3. 再评估用户管理、批量审核和更细权限。

## 最近交接记录：2026-07-15（v0.4.1）

本轮完成：

- EPUB 解析器增加 manifest properties、spine linear、guide 和正文 EPUB 语义识别。
- 章节标题优先从首个标题元素提取，并从朗读正文移除重复标题。
- 过滤目录、封面、版权页、脚注、尾注、脚注引用和非线性 spine 内容。
- 支持 URL 编码和带片段的 manifest href，限制单个正文文档为 10 MiB，并阻止路径越出包根目录。
- 新增 `samples/epub_golden/semantic-book/` 可复现黄金夹具及独立回归测试。
- worker 定期清理超过保留期的成功任务，默认保留 30 天；失败任务继续保留。
- 新增 `LISTEN_BOOK_JOB_RETENTION_DAYS` 和 `LISTEN_BOOK_JOB_CLEANUP_INTERVAL_SECONDS` 配置。
- 前后端及 FastAPI 版本统一升级为 `0.4.1`。

本轮验证：

- `.venv\Scripts\python.exe -m pytest backend\tests -q`：`37 passed`。
- `.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py scripts\e2e_env.py scripts\e2e_setup.py scripts\run_e2e_backend.py scripts\run_e2e_sqlite.py`：通过。
- `cd frontend && npm run build`：通过。
- `cd frontend && npm run test:e2e:sqlite`：`5 passed`。
- 本版本没有数据库结构变更，不新增 Alembic 迁移。

下一阶段优先任务：

1. 增加首次启动诊断，检查数据库、存储目录、默认密钥和管理员密码。
2. 增加管理员用户管理和批量审核能力，并保持审计记录完整。
3. 在现有 TTS golden 样例上建立可重复的主观评分记录，再继续调整朗读规则。
