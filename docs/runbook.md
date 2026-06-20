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

后端 pytest 额外覆盖 TXT、GB18030 TXT、EPUB 解析、阅读进度、删除清理、音频接口和失败路径。

## E2E 浏览器测试

Playwright E2E 测试覆盖上传、解析等待、阅读进度恢复和删除等关键路径。当前脚本刻意不触发真实 TTS，避免 E2E 依赖外部网络。

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
