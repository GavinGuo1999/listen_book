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
- 登录/多用户进度隔离最小闭环：注册、登录、当前用户、退出登录、token 鉴权
- 未登录时保留默认本地用户 `local` 模式；登录后阅读进度按用户隔离
- 服务启动后的 API smoke 脚本：`scripts/smoke_api.py`
- Windows 启停脚本：`scripts\start-dev.bat`、`scripts\stop-dev.bat`

当前主要未完成：

- PDF 解析
- 完整书库归属/权限隔离
- 登录链路浏览器 E2E
- 更自然的小说朗读：更细的停顿、情绪、角色/旁白风格

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
