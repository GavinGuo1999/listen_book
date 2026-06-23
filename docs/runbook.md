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
cd D:\listen_book
Copy-Item .env.example .env
```

安装后端依赖：

```powershell
cd D:\listen_book
.venv\Scripts\python.exe -m pip install --no-cache-dir -e backend[dev]
```

安装前端依赖：

```powershell
cd D:\listen_book\frontend
npm install --no-audit --no-fund
```

执行数据库迁移：

```powershell
cd D:\listen_book\backend
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
cd D:\listen_book\backend
..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

手动启动前端：

```powershell
cd D:\listen_book\frontend
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
cd D:\listen_book\frontend
npm run build
```

后端测试：

```powershell
cd D:\listen_book
.venv\Scripts\python.exe -m pytest backend\tests -q
```

后端 lint：

```powershell
cd D:\listen_book
.venv\Scripts\ruff.exe check --no-cache backend\app backend\tests scripts\smoke_api.py
```

服务启动后的 API smoke：

```powershell
cd D:\listen_book
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

运行前提：后端服务已在 `http://127.0.0.1:8000` 运行。

```powershell
cd D:\listen_book\frontend

# headless 运行（CI / 快速验证）
npm run test:e2e

# 可见浏览器（调试用）
npx playwright test --headed

# 只跑某个文件
npx playwright test e2e/books.spec.ts
```

测试文件：`frontend/e2e/books.spec.ts`
Playwright 配置：`frontend/playwright.config.ts`

注意：E2E 测试会复用已运行的前端 dev server；如果前端未运行，Playwright 会临时启动一个测试用 dev server。后端服务仍需提前手动启动。

## 公共书库与审批

- 默认本地用户 `local` 是管理员，用于本地单机/开发体验。
- 第一个正式注册用户会自动成为管理员。
- 管理员上传 TXT/EPUB 后自动发布到公共书库。
- 普通用户上传 TXT/EPUB 后默认进入 `pending_review`，只有上传者本人和管理员可见。
- 管理员可在前端独立“审核中心”里集中处理上传，也可在书库行点击“批准/拒绝”。
- 审核中心支持：
  - 待审批、解析失败、已拒绝、全部筛选
  - 分页
  - 上传者和上传时间展示
  - 当前审批备注
  - 审批历史：审批人、审批时间、原状态、新状态、历史备注
- 拒绝或批准时可填写审批备注；当前备注会保存到书籍的 `review_note`，每次审批也会写入 `book_review_events` 审计表。
- 也可直接调用：

```http
PATCH /api/books/{book_id}/review
```

请求体示例：

```json
{
  "review_status": "rejected",
  "review_note": "文件内容不完整，请重新上传。"
}
```

当前支持上传格式为 TXT/EPUB；PDF 暂不接入。

管理员审计列表接口：

```http
GET /api/books/admin/reviews
```

该接口仅管理员可用，返回上传者信息和 `review_history`。

## 朗读语气

- 当前真实 TTS provider 使用 `edge-tts`，模型版本为 `13`。
- 语气规则会根据句子特征调整语速和音高：
  - 普通疑问句保持中性，不再额外升调。
  - 对白略提高音高、略加快，和旁白做基础区分。
  - 长句、逗号密集句降低语速，减少赶读感。
  - 省略号/破折号进一步放慢。
  - “低声/轻声/喃喃”等轻声标记放低音高，“大声/喊道/怒道”等强情绪标记提高音高。
- 这仍是轻量规则；尚未实现按角色分配不同音色。

## 手动 worker 兜底

上传接口会通过 FastAPI `BackgroundTasks` 自动触发一次解析。如果存在 pending parse job 需要手动重试：

```powershell
cd D:\listen_book
.venv\Scripts\python.exe -m app.workers.parse_books
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
