# Listen Book

家庭读书/听书 Web 应用。

当前已完成本地听书 MVP 和登录/多用户进度隔离最小闭环：

- TXT/EPUB 上传、解析、断句
- 书库和阅读页
- Edge TTS 按句生成 MP3
- 音频缓存和章节预生成
- 已有书籍删除
- 阅读进度保存
- 精确播放位置保存/恢复
- 浏览器 E2E 和后端 API 自动化测试
- 注册、登录、当前用户和退出登录
- 未登录时保留本地 `local` 用户模式
- 登录后阅读进度按用户隔离

当前仍未实现：PDF 解析、完整权限/书库归属隔离。

## 技术栈

- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React + TypeScript + Vite
- Database: PostgreSQL
- Storage: local filesystem under `storage/`

## 快速开始

创建本地环境文件：

```powershell
Copy-Item .env.example .env
```

安装后端依赖：

```powershell
.venv\Scripts\python.exe -m pip install --no-cache-dir -e backend[dev]
```

安装前端依赖：

```powershell
cd frontend
npm install --no-audit --no-fund
```

执行数据库迁移：

```powershell
cd D:\listen_book\backend
..\.venv\Scripts\alembic.exe upgrade head
```

启动开发服务：

```bat
scripts\start-dev.bat
```

打开：

```text
http://127.0.0.1:5173/
```

停止开发服务：

```bat
scripts\stop-dev.bat
```

## PostgreSQL

默认连接串见 `.env.example`：

```text
postgresql+psycopg://listen_book_app:change-me@localhost:5432/listen_book
```

示例初始化 SQL：

```sql
CREATE USER listen_book_app WITH PASSWORD 'change-me';
CREATE DATABASE listen_book OWNER listen_book_app;
GRANT ALL PRIVILEGES ON DATABASE listen_book TO listen_book_app;
```

## 验证命令

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

更多运行和排错步骤见 [docs/runbook.md](docs/runbook.md)。
