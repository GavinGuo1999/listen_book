# Listen Book

家庭读书/听书 Web 应用，当前稳定版本为 `v0.3.1`：面向本地自用和家庭局域网使用，优先保证上传、解析、朗读、缓存、进度恢复、登录和管理员审核这条主流程稳定。

## 当前能做什么

- TXT/EPUB 上传、解析、断句
- 书库和阅读页
- Edge TTS 按句生成 MP3
- 音频缓存和章节预生成
- 已有书籍删除
- 阅读进度保存
- 精确播放位置保存/恢复
- 浏览器 E2E 和后端 API 自动化测试
- 注册、登录、当前用户和退出登录
- 独立登录/注册页，未登录不能访问书库和审批
- 登录态使用后端 HttpOnly Cookie
- 登录后阅读进度按用户隔离
- 公共书库 + 上传审批最小闭环
  - 管理员账号由 `.env` 显式 bootstrap
  - 管理员上传自动发布
  - 普通用户上传默认待审批
  - 管理员可在 `/admin` 后台批准/拒绝
  - 拒绝时可填写审批备注
  - 管理员审核中心可查看上传者、上传时间、解析失败筛选、分页和审批历史
  - 普通用户只看到已发布书籍和自己上传的待审/拒绝书籍
- 小说朗读语气基础优化：按对白、长句、感叹、省略号和轻声/喊话等特征调整 Edge TTS 语速/音高

## 当前不做什么

- PDF 解析暂不接入；当前上传格式明确收敛为 TXT/EPUB。
- 不先追求复杂 AI 讲书或多角色配音；朗读优化先用固定 golden 样例评测自然度。
- 管理员后台目前是最小闭环；批量审批、复杂筛选、用户管理和权限分层仍属于下一阶段。
- 后台任务仍是 MVP 形态；后续再升级为轻量 worker 扫描 pending job。

## 稳定版本验收

`v0.3.1` 的验收目标：

1. 本地服务可稳定启动。
2. 管理员可上传一本 TXT/EPUB 并自动发布。
3. 普通用户上传后进入待审批，管理员可批准/拒绝并留下审计记录。
4. 阅读页可按句播放、缓存音频、预生成章节音频。
5. 阅读句子和音频位置可恢复。
6. 自动化测试覆盖后端 API、TTS 规则和浏览器主流程。

前端已按职责拆分为 `pages/`、`components/` 和 `hooks/`；`App.tsx` 只负责路由和跨模块编排，后续功能不再继续集中堆叠到单文件。

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
cd D:\Projects\listen_book\backend
..\.venv\Scripts\alembic.exe upgrade head
```

配置 bootstrap 管理员（示例，实际密码写在本机 `.env`，不要提交）：

```text
LISTEN_BOOK_BOOTSTRAP_ADMIN_USERNAME=admin
LISTEN_BOOK_BOOTSTRAP_ADMIN_PASSWORD=change-me-admin-password
```

启动后系统会确保该用户存在、启用且拥有管理员权限。普通注册用户不会自动成为管理员。

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

浏览器 E2E：

```powershell
cd D:\Projects\listen_book\frontend
npm run test:e2e
```

该命令会使用独立 PostgreSQL 测试库 `listen_book_e2e` 和 `storage/e2e`，并临时启动测试后端到 `127.0.0.1:8001`、测试前端到 `127.0.0.1:5174`；不会清空或写入真实开发库。首次运行前如果应用数据库用户没有建库权限，需要用 PostgreSQL 管理员执行：

```sql
CREATE DATABASE listen_book_e2e OWNER listen_book_app;
```

没有 PostgreSQL 建库权限时，可使用完全位于 `storage/e2e` 下的 SQLite 隔离测试库完成浏览器主流程验收：

```powershell
cd D:\Projects\listen_book\frontend
npm run test:e2e:sqlite
```

更多运行和排错步骤见 [docs/runbook.md](docs/runbook.md)。

## 项目资料

- 变更记录：[CHANGELOG.md](CHANGELOG.md)
- 运行手册：[docs/runbook.md](docs/runbook.md)
- TTS 评测说明：[docs/tts-evaluation.md](docs/tts-evaluation.md)
- 项目交接记忆：[docs/PROJECT_MEMORY.md](docs/PROJECT_MEMORY.md)
