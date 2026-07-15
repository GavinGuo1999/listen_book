# Runbook

## 约定

- 后端或前端代码变更后，优先跑短命令验证。
- 不默认由 Codex 启动长驻服务；Windows 后台进程在当前工具环境里不稳定。
- 需要实机验证时，由用户运行：

```bat
scripts\stop-dev.bat
scripts\start-dev.bat
```

## 首次准备

创建 `.env`：

```powershell
cd D:\Projects\listen_book
Copy-Item .env.example .env
```

安装后端依赖：

```powershell
cd D:\Projects\listen_book
.venv\Scripts\python.exe -m pip install --no-cache-dir -e backend[dev]
```

安装前端依赖：

```powershell
cd D:\Projects\listen_book\frontend
npm install --no-audit --no-fund
```

执行数据库迁移：

```powershell
cd D:\Projects\listen_book\backend
..\.venv\Scripts\alembic.exe upgrade head
```

## 启动和停止

推荐 Windows 工作流：

```bat
scripts\start-dev.bat
```

这会分别打开后端和前端窗口。

手动启动后端：

```powershell
cd D:\Projects\listen_book\backend
..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

手动启动前端：

```powershell
cd D:\Projects\listen_book\frontend
npm run dev -- --host 127.0.0.1
```

停止：

```bat
scripts\stop-dev.bat
```

## 健康检查

后端：

```powershell
curl.exe http://127.0.0.1:8000/api/health
```

前端：

```text
http://127.0.0.1:5173/
```

## 自动化验证

前端构建：

```powershell
cd D:\Projects\listen_book\frontend
npm run build
```

后端测试：

```powershell
cd D:\Projects\listen_book
.venv\Scripts\python.exe -m pytest backend\tests -q
```

后端 lint：

```powershell
cd D:\Projects\listen_book
.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py
```

服务启动后的 API smoke：

```powershell
cd D:\Projects\listen_book
.venv\Scripts\python.exe scripts\smoke_api.py
```

该脚本会：

1. 检查 `/api/health`
2. 上传临时 TXT
3. 等待解析为 `ready`
4. 读取章节和第一句
5. 保存并读取阅读进度
6. 删除临时测试书籍

后端 pytest 额外覆盖 TXT、GB18030 TXT、EPUB 解析、注册/登录、用户进度隔离、公共书库审批可见性、审批审计记录、阅读进度、删除清理、音频接口、TTS 语气规则和失败路径。

## E2E 浏览器测试

Playwright E2E 测试覆盖注册/登录/退出、上传、解析等待、阅读进度恢复、删除、普通用户上传待审、管理员审核中心批准、审批历史展示和批准后公共可见等关键路径。当前脚本刻意不触发真实 TTS，避免 E2E 依赖外部网络。

运行前提：本机 PostgreSQL 可访问，且应用数据库用户有权限创建或访问测试库 `listen_book_e2e`。

E2E 运行时会：

- 使用独立数据库 `listen_book_e2e`
- 使用独立存储目录 `storage/e2e`
- 测试前执行迁移并清空测试库
- bootstrap 测试管理员 `admin`
- 在测试后端进程中启动隔离 worker，消费真实持久化任务
- 临时启动测试后端到 `http://127.0.0.1:8001`
- 临时启动测试前端到 `http://127.0.0.1:5174`
- 让测试前端 dev server 代理 `/api` 到测试后端

因此 E2E 不需要真实开发后端 `127.0.0.1:8000` 或真实开发前端 `127.0.0.1:5173`，也不会清空或写入真实开发库。

如果应用数据库用户没有建库权限，首次运行前用 PostgreSQL 管理员创建测试库：

```sql
CREATE DATABASE listen_book_e2e OWNER listen_book_app;
```

```powershell
cd D:\Projects\listen_book\frontend

# headless 运行（CI / 快速验证）
npm run test:e2e

# 没有 PostgreSQL 建库权限时，使用 storage/e2e 下的隔离 SQLite 数据库
npm run test:e2e:sqlite

# 可见浏览器（调试用）
npx playwright test --headed

# 只跑某个文件
npx playwright test e2e/books.spec.ts
```

测试文件：`frontend/e2e/books.spec.ts`
Playwright 配置：`frontend/playwright.config.ts`

SQLite 模式用于本地浏览器主流程验收，通过 SQLAlchemy 当前模型初始化测试库；PostgreSQL 模式额外验证 Alembic 迁移和生产数据库方言。发布前至少跑通一种模式，有 PostgreSQL 测试库时优先跑默认模式。

注意：Playwright 会使用 8001/5174 端口启动测试服务。如果端口被占用，先停止占用进程再运行 E2E。

## 公共书库与审批

- 未登录用户只能访问登录/注册页，不能访问书库、上传、音频、进度或审批 API。
- 管理员账号由 `.env` 显式配置：

```text
LISTEN_BOOK_BOOTSTRAP_ADMIN_USERNAME=admin
LISTEN_BOOK_BOOTSTRAP_ADMIN_PASSWORD=change-me-admin-password
```

- 服务启动时会确保该账号存在、启用且拥有管理员权限；普通注册用户不会自动成为管理员。
- 管理员后台入口是 `/admin`，普通用户访问会回到普通书库页。
- 管理员上传 TXT/EPUB 后自动发布到公共书库。
- 普通用户上传 TXT/EPUB 后默认进入 `pending_review`，只有上传者本人和管理员可见。
- 管理员可在前端独立“审核中心”里集中处理上传。
- 审核中心支持：
  - 待审批、解析失败、已拒绝、全部筛选
  - 分页
  - 上传者和上传时间展示
  - 当前审批备注
  - 审批历史：审批人、审批时间、原状态、新状态、历史备注
- 拒绝或批准时可填写审批备注；当前备注会保存到书籍的 `review_note`，每次审批也会写入 `book_review_events` 审计表。
- 也可直接调用：

```http
GET /api/admin/books/reviews
PATCH /api/admin/books/{book_id}/review
```

请求体示例：

```json
{
  "review_status": "rejected",
  "review_note": "文件内容不完整，请重新上传。"
}
```

当前支持上传格式为 TXT/EPUB；PDF 暂不接入。

旧接口暂保留兼容并已在 OpenAPI 中标记为 deprecated，新代码优先使用 `/api/admin/...`：

```http
GET /api/books/admin/reviews
PATCH /api/books/{book_id}/review
```

管理员审计列表接口仅管理员可用，返回上传者信息和 `review_history`。

## 朗读语气

- 当前真实 TTS provider 使用 `edge-tts`，模型版本为 `13`。
- 语气规则会根据句子特征调整语速和音高：
  - 普通疑问句保持中性，不再额外升调。
  - 对白略提高音高、略加快，和旁白做基础区分。
  - 长句、逗号密集句降低语速，减少赶读感。
  - 省略号/破折号进一步放慢。
  - “低声/轻声/喃喃”等轻声标记放低音高，“大声/喊道/怒道”等强情绪标记提高音高。
- 这仍是轻量规则；尚未实现按角色分配不同音色。
- 固定评测样例位于 `samples/tts_golden/`，评分口径见 `docs/tts-evaluation.md`。调整 TTS 或切句规则后，优先用这组样例听测，避免凭感觉反复改规则。

## 后台 worker

`scripts\start-dev.bat` 会先执行数据库迁移，再分别启动 worker、FastAPI 和 Vite。worker 持续处理书籍解析、句子音频生成和章节音频预生成任务。

需要单独启动 worker 时：

```powershell
cd D:\Projects\listen_book\backend
..\.venv\Scripts\python.exe -m app.workers.jobs
```

任务领取规则：

- 解析任务优先于章节预生成和单句音频任务。
- PostgreSQL 使用 `FOR UPDATE SKIP LOCKED`，多个 worker 不会领取同一任务。
- 失败任务最多自动尝试 3 次，按指数退避等待。
- 运行超过 5 分钟仍未完成的任务会被视为 worker 中断并重新入队。
- 最终失败任务可在 `/admin` 的任务中心查看并手动重试。

管理员任务 API：

```http
GET /api/admin/jobs?status=failed
POST /api/admin/jobs/{job_id}/retry
```

## 常见注意事项

- 真实 TTS provider 使用 `edge-tts`，音频生成需要网络访问。
- Markdown 文档统一按 UTF-8 读取和写入。
- 如果 PowerShell 输出中文乱码，使用：

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
Get-Content -Path docs\PROJECT_MEMORY.md -Encoding UTF8
```

- 运行产物不要提交：
  - `.env`
  - `.venv/`
  - `frontend/node_modules/`
  - `frontend/dist/`
  - `storage/uploads/*`
  - `storage/audio/*`
  - `logs/`
