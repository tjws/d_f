# 本地容器运行说明

本目录把项目拆成两类服务：

```text
浏览器
  -> frontend (Nginx, :5174)
      -> /api/* -> backend (FastAPI, :8001)
          -> PostgreSQL (:5433，业务事实、审计和 AI 运行结果)
          -> Redis (:6380，任务投递和限额，不保存业务事实)
          -> worker (Dramatiq + LangGraph，生成待人工确认的草稿)
```

## 文件职责

- `backend.Dockerfile`：构建 FastAPI 与 Worker 共用的 Python 镜像。
- `frontend.Dockerfile`：构建 Vue 静态文件，并交给 Nginx 提供服务。
- `nginx.conf`：将同源 `/api/` 请求代理给后端，容器版页面不依赖 CORS。
- `local.env.example`：本机配置模板；复制为 `local.env` 后修改。`local.env` 被 Git 忽略。
- `compose.yml`：定义所有容器、端口、数据卷和健康检查。

## 日常启动

从仓库根目录运行：

```powershell
# 首次使用 Qdrant 时创建外部 named volume；已有环境无需重复执行
docker volume create k12_qdrant_storage

# 首次或 Alembic 迁移有变化时：初始化/升级 PostgreSQL 表结构
docker compose --env-file infra/local.env --profile tools run --rm migrate

# 启动完整容器版
docker compose --env-file infra/local.env --profile app up -d --build

# 查看状态和日志
docker compose --env-file infra/local.env ps
docker compose --env-file infra/local.env logs -f backend worker
```

访问容器版前端：`http://localhost:5174`；后端接口文档：`http://localhost:8001/docs`。

不会占用本机正在使用的 `8000` 和 `5173`，也不会操作其他项目的容器。

## SQLite 首次迁移

迁移脚本默认只预检；必须加入 `--execute` 才写入 PostgreSQL。执行前先备份 SQLite，目标数据库非空时会拒绝运行；`role_permissions` 是 Alembic 固定初始化的系统表，数量一致时会跳过。

```powershell
cd E:\codex_folder\project\t_f\backend
$env:POSTGRES_DATABASE_URL = 'postgresql+psycopg://<user>:<password>@localhost:5433/k12_sales_app'
python -m scripts.migrate_sqlite_to_postgres
python -m scripts.migrate_sqlite_to_postgres --execute
```

## 百炼调用边界

运行环境默认 `AI_PROVIDER=bailian`。在本机容器运行前，需要在未提交的 `infra/local.env` 中提供 `DASHSCOPE_API_KEY`；不要把 Key 写入代码、镜像或 Git。若暂时只做本地单元测试，测试夹具会强制使用 Mock，不会调用外部模型。

销售 Agent 的“自动判断”会额外发起一次百炼规划调用：它只发送客户阶段、消息/时间线数量和是否存在已确认画像等最小摘要，以及用户主动输入的指令；不会发送姓名、电话或聊天正文。随后才由既有工作流生成建议草稿。若要节省一次调用，在侧边栏直接选择“回复建议”“标签建议”或“日程建议”；无论哪种方式，生成结果都必须由人工确认，系统没有自动发送能力。

侧边栏的“综合五工具分析”会按顺序调用 `knowledge.search`、`customer_profile.read_confirmed`、`orders.list`、`tags.analyze` 和 `course_openings.read` 五个只读工具。每一步只返回脱敏摘要并写入 `ai_workflow_runs.result_json`，缺失画像、知识库未命中和实时座位数都会标记为待人工核实；该流程不会自动写订单、改标签、建日程或发送消息。

如需学习 Agent 的检查点控制，可在 `POST /customers/{customer_id}/agent/run` 的请求体中使用 `{"task":"comprehensive","execution_mode":"checkpointed"}`。接口会先保存计划并返回 `paused`，然后通过 `POST /customers/{customer_id}/agent/runs/{run_id}/control` 发送 `{"action":"correct","correction":{"skip_tools":["orders.list"]}}` 保存人工修正，再发送 `{"action":"resume","step_limit":1}` 逐步继续，或把 `step_limit` 设为 5 完成剩余步骤。`pause`、`correct`、`resume` 都只控制本次只读分析，不会发送消息；最终仍需人工确认回复草稿。

Compose 将 `AI_WORKFLOW_EXECUTION_MODE` 固定为 `queue`。综合 Agent 的规划请求返回 `queued` 后由 `ai_workflow` Worker 执行；前端通过 `GET /customers/{customer_id}/agent/runs/{run_id}` 轮询完整步骤。Worker 每完成一个工具就回写 PostgreSQL，收到 `pause` 后会在下一个工具边界停下；Redis 只负责投递，不保存业务结果。

- 只有用户在页面点击“生成”才会创建任务。
- 每个用户每天最多 `AI_DAILY_BAILIAN_REQUEST_LIMIT=20` 次。
- 单次模型超时 20 秒，Dramatiq `max_retries=0`，失败不会隐式重试。
- Worker 只落库画像、回复、标签或日程草稿；人工确认前绝不自动发送或创建正式日程。

容器默认关闭 `APP_DEV_AUTH_BYPASS`，未登录请求应返回 `401`。

### 本地演示账号与安全 smoke

演示账号整理脚本默认只预览，不会写入数据库：

```powershell
cd E:\codex_folder\project\t_f\backend
python -m scripts.ensure_demo_accounts
```

如果本机演示库中的密码已经被改动，确认这是本地开发库后，再显式重置三个演示账号：

```powershell
python -m scripts.ensure_demo_accounts --apply --reset-passwords
```

脚本只处理 `demo_admin`、`demo_manager`、`demo_sales`，不会自动覆盖已有角色，也不应在生产环境执行。
重置后可运行安全 smoke；也可以通过 `SECURITY_SALES_USERNAME` 和
`SECURITY_SALES_PASSWORD` 指定一个已有的 sales 账号，脚本本身不会创建或修改账号：

```powershell
$env:SECURITY_BASE_URL = 'http://localhost:8001'
python -m scripts.security_smoke
```

### 容器上线前只读 smoke 检查

该脚本不会创建或修改业务数据，只检查 readiness、演示账号登录、客户列表和本地 RAG；脚本会显式使用 `use_vector=false`，避免验收时隐式调用百炼 Embedding：

```powershell
docker compose --env-file infra/local.env exec -e SMOKE_BASE_URL=http://localhost:8000 backend python -m scripts.production_smoke
```

可通过 `SMOKE_BASE_URL`、`SMOKE_USERNAME`、`SMOKE_PASSWORD` 环境变量指定检查地址和测试账号。不要把真实密码写入脚本或 Git。

## 本地演示数据与知识库

知识库资料保存在 `backend/data/knowledge/*.md`，由本地关键词检索器按需读取，不调用百炼。可用以下命令先预览、再明确写入当前数据库：

```powershell
docker compose --env-file infra/local.env exec backend python -m scripts.seed_demo_data
docker compose --env-file infra/local.env exec backend python -m scripts.seed_demo_data --apply
```

演示账号均使用密码 `Demo123456!`，只适合本机测试。脚本是幂等的，不会清空或覆盖已有客户；不要在生产环境执行。

`seed_demo_data --apply` 会补齐三名客户及学生、文本/语音 Mock 聊天、时间线、画像、标签、日程、订单、工单、AI 建议/反馈、话术和多分片知识库资料。它不会调用百炼、上传音频或接入真实企业微信；语音使用 `mock-voice:` 媒体 key，便于在页面中手动点击 Mock 转写。
如果需要把已经转写过的固定演示语音恢复成“待人工转写”，可以显式执行：

```powershell
docker compose --env-file infra/local.env exec backend python -m scripts.seed_demo_data --apply --reset-voice
```

## Readiness、备份与恢复演练

`GET http://localhost:8001/health` 只表示进程已启动；`GET http://localhost:8001/health/ready` 会实际检查 PostgreSQL 和 Redis。启用 `RAG_VECTOR_ENABLED=1` 时还会检查 Qdrant，任一必需依赖不可用时返回 `503`。

备份只使用 PostgreSQL 官方 `pg_dump`，默认写到 Git 忽略的 `backend/backups/`，不会把密码、JWT 或百炼 Key 写入文件：

```powershell
cd E:\codex_folder\project\t_f
$env:DATABASE_URL = 'postgresql+psycopg://<user>:<password>@localhost:5433/<db>'
python backend/scripts/backup_postgres.py
```

也可以直接在 Compose 的 PostgreSQL 容器内导出（宿主机重定向到 Git 忽略目录）：

```powershell
$stamp = Get-Date -Format yyyyMMddTHHmmssZ
docker compose --env-file infra/local.env exec -T postgres pg_dump -U k12_app -d k12_sales_app --format=custom > "backend/backups/k12_sales_$stamp.dump"
```

恢复只建议对临时演练库执行，并且必须显式确认覆盖目标库：

```powershell
$env:RESTORE_DATABASE_URL = 'postgresql+psycopg://<user>:<password>@localhost:5433/k12_restore_drill'
python backend/scripts/restore_postgres.py backend/backups/<backup>.dump --confirm-dangerous-restore
```

恢复会使用 `pg_restore --clean --if-exists` 覆盖目标库；脚本不会自动创建目标库，也不会触碰当前开发库。演练后用 `alembic current`、`/health/ready` 和关键业务查询核对，再由人工决定是否保留演练库。

恢复前可以先做不连接目标数据库的归档校验：

```powershell
python backend/scripts/verify_backup.py backend/backups/<backup>.dump
```

该命令只执行 `pg_restore --list`，不会创建数据库、删除数据或调用恢复流程。

生产化定时备份：backend 容器把 `backend/backups/` 挂载到宿主机，便于 Task Scheduler 或其他调度器每天执行：

```powershell
cd E:\codex_folder\project\t_f
powershell -ExecutionPolicy Bypass -File infra/run-backup.ps1
```

脚本会先创建 custom-format 备份，再执行只读 `pg_restore --list` 校验；它不会自动清理旧备份。只有明确设置
`BACKUP_PRUNE_ENABLED=1` 并传入 `-Prune` 才会按 30 天清理，建议先人工核对备份和恢复演练结果。管理后台“运行状态”只读取最新文件的时间、大小和过期状态，不会触发备份或删除。

### 数据保留、语音转写和 Mock 业务同步

- 管理后台“数据导出与保留”显示各数据集的默认保留天数。`POST /admin/data-retention/preview` 只统计到期记录；`POST /admin/data-retention/purge` 仅允许清理聊天消息和 AI 反馈，要求 `DATA_RETENTION_AUTO_DELETE=1`、管理员身份和 `confirm=true`。客户表与 `audit_logs` 永不由此工具删除。
- 聊天工作台可以创建 `voice` 类型的 Mock 消息，媒体 key 使用 `mock-voice:家长想了解课程` 这样的格式；点击“Mock 转写”调用 `POST /customers/{customer_id}/chat-messages/{message_id}/transcribe`，文本加密保存并写入时间线。当前不上传音频、不调用外部 ASR。
- 管理后台“订单与工单”提供 Mock 外部同步演练。`POST /admin/operations/mock-sync` 在一个事务内导入订单和工单，按外部编号幂等，重复同步会跳过；真实订单系统仍需后续提供接口和凭据后再实现适配器。
### 知识库向量索引

Compose 默认将已发布知识文档投递到 `knowledge_index` 队列，由 worker 异步写入 Qdrant；本地直接运行 FastAPI 时默认 `manual`，不会因保存文档而连接 Qdrant。需要手动重建时，在管理后台点击“重建向量索引”，或设置 `KNOWLEDGE_INDEX_EXECUTION_MODE=sync` 做同步演练。索引失败会保留在文档的状态字段中，不会回滚文档发布。

### RAG 评测闭环

当知识检索触发 fallback，或综合 Agent 收到人工纠错反馈时，系统会在同一事务中创建一条
`rag_evaluation_cases` 待复核用例。它只保存截断后的查询摘要、来源、检索模式和文档 slug，
不会保存完整聊天正文或模型密钥。管理员/经理登录后访问：
`http://localhost:5174/admin/rag-evaluation`。

在页面中可以补充期望命中的知识文档 slug、复核备注，并标记“已复核”或“已忽略”。
“运行 RAG 评测”只执行关键词/向量召回统计，不调用回复生成模型；修复知识文档后可再次运行，
用 Hit@K 和 MRR 对比改动前后的召回质量。销售角色即使手动访问页面，后端也会返回 403。

### 本地 Mock 企业微信消息回放

已有的 `/wecom/mock/callback` 会执行验签、`integration_events` 幂等登记、
聊天消息入库和时间线事件创建。可以用回放脚本生成一组假的家长消息，
不需要真实企业微信账号：

```powershell
cd E:\codex_folder\project\t_f\backend
# 默认只预览，不写数据库
python -m scripts.replay_wecom_events --customer-id 1

# 明确写入；userid 必须对应数据库中的 Mock 用户
$env:WECOM_CALLBACK_TOKEN = '<与后端 WECOM_CALLBACK_TOKEN 相同的本地值>'
python -m scripts.replay_wecom_events --customer-id 1 --userid demo-user-001 --apply

# 使用同一批 event_id 再发送一次，预期每条返回 duplicate
python -m scripts.replay_wecom_events --customer-id 1 --event-prefix replay-check --repeat 2 --apply
```

脚本不会调用百炼，也不会自动生成或发送 AI 回复；它只模拟“家长发来消息”。
执行后刷新 `/sidebar`，即可在选中客户的聊天和最近时间线中看到结果。

### 端到端与安全验收

这两个脚本只验证当前运行环境；不会替代针对代码改动的单元测试。

```powershell
cd E:\codex_folder\project\t_f\backend

# 只读检查登录、客户、聊天和时间线
python -m scripts.local_e2e_smoke

# 明确写入一条本地演示消息，并核对聊天/时间线各增加一条
python -m scripts.local_e2e_smoke --customer-id 1 --apply

# 完整演示验收：健康状态、客户/学生/聊天/时间线/侧边栏、订单工单、
# AI 建议、知识库、管理权限和前端代理；默认只读，不调用任何模型
python -m scripts.demo_e2e_smoke

# 明确写入一条 Mock 语音转写，并验证重复转写不会产生第二条时间线
python -m scripts.demo_e2e_smoke --apply

# 检查匿名 401、sales 访问管理接口 403
python -m scripts.security_smoke
```

发布候选版可以额外运行一套完整的只读检查，串联健康状态、客户工作台、Mock
侧边栏、管理看板、sales 权限和 Nginx `/api/` 代理。它不会创建客户、触发 AI
工作流或发送消息：

```powershell
cd E:\codex_folder\project\t_f\backend
python -m scripts.release_candidate_smoke
```

默认访问容器版 `http://localhost:8001` 和 `http://localhost:5174`，账号可通过
`RC_ADMIN_USERNAME`、`RC_ADMIN_PASSWORD`、`RC_SALES_USERNAME`、
`RC_SALES_PASSWORD` 覆盖。若只检查后端，可加 `--skip-frontend`。

如果从 Compose 的 backend 容器内部执行，地址要改为容器端口：

```powershell
docker compose --env-file infra/local.env exec -e DEMO_BASE_URL=http://localhost:8000 backend python -m scripts.demo_e2e_smoke --skip-frontend
```

账号可通过 `E2E_USERNAME`、`E2E_PASSWORD`、`SECURITY_SALES_USERNAME`、
`SECURITY_SALES_PASSWORD` 环境变量覆盖；不要把真实密码写入脚本或 Git。
容器交付前必须保持 `APP_DEV_AUTH_BYPASS=0`。

### Agent 任务幂等与人工重试

Agent 和 LangGraph 工作流支持显式 `idempotency_key`。同一操作者、同一客户再次提交同一个键时，API 只返回原运行记录，不会再次排队或重复生成建议：

```powershell
$body = '{"task":"comprehensive","idempotency_key":"demo-agent-20260916-01"}'
Invoke-RestMethod http://localhost:8001/customers/1/agent/run -Method Post -Headers @{ Authorization = "Bearer <token>"; "Content-Type" = "application/json" } -Body $body
```

Worker 不会自动无限重试。失败运行需要人工明确确认，并且单次运行最多执行 `AI_WORKFLOW_MAX_ATTEMPTS` 次（默认 3 次）：

```powershell
$body = '{"confirm":true}'
Invoke-RestMethod http://localhost:8001/customers/1/ai-workflow/<run_id>/retry -Method Post -Headers @{ Authorization = "Bearer <token>"; "Content-Type" = "application/json" } -Body $body
```

综合 Agent 使用 `/customers/{customer_id}/agent/runs/{run_id}/retry`。重试会保留已成功的只读步骤，只重新执行失败步骤；所有建议仍需人工确认、编辑和发送。

### Worker 心跳与失联任务恢复

Worker 执行中的 `running` 任务会定期更新 `heartbeat_at`。管理员或经理可在
`/admin/ai-workflow-runs` 页面点击“检查异常任务”，或调用以下接口，把超过阈值且没有
心跳的任务标记为 `failed`：

```powershell
$body = '{"confirm":true,"stale_after_seconds":120,"limit":50}'
Invoke-RestMethod http://localhost:8001/admin/ai-workflow-runs/recover-stale -Method Post `
  -Headers @{ Authorization = "Bearer <admin-or-manager-token>"; "Content-Type" = "application/json" } `
  -Body $body
```

接口必须带 `confirm=true`，阈值范围为 30 秒至 24 小时；它只改变任务状态并保留
`error_code=worker_lost`，不会自动重新排队或再次调用百炼。处理完成后，人工在客户页确认
上下文，再使用已有的 retry 接口决定是否重试。这样可以避免 Worker 迟到结果覆盖恢复决定，
也避免进程异常时产生重复的模型调用。

### AI 灰度发布与试点日报

管理员可以在 `http://localhost:5174/admin/ai-rollout` 控制综合 Agent 的发布范围：

- `all`：默认全量放行；
- `pilot`：只允许 active 灰度名单中的用户运行综合 Agent；
- 灰度名单最多 30 名用户，并可标记为新人、老顾问或未分类；
- 每日指标快照写入 `ai_rollout_daily_reports`，可重复生成同一天的日报，不会创建重复记录。

切换到 `pilot` 前，先把用于验收的管理员或销售账号加入名单；后端在 Agent 入口再次校验，
因此即使手动调用 API 或绕过前端入口，也不会绕过灰度门禁。灰度门禁只限制 AI 运行，
不改变人工编辑、确认和发送消息的流程。发布时建议先生成日报观察采用率、失败数和 RAG fallback，
确认稳定后再切回 `all`。

### AI 工作流 SSE 状态推送

客户工作台运行 AI 工作流后，会优先连接：
`GET /customers/{customer_id}/ai-workflow/{run_id}/events`。
接口返回 `text/event-stream`，只推送任务状态、运行编号和下一步动作，不推送完整聊天正文或模型原始输出。
前端使用 `fetch` 读取 SSE，以便继续携带 Bearer 鉴权头；如果代理或网络不支持流式连接，会自动回退为状态查询，
不会把 JWT 放进 URL。终态事件仍要求人工查看建议、编辑、确认后再发送。

### 业务经营看板

管理员和经理可以在 `http://localhost:5174/admin/business-dashboard` 查看经营汇总，
后端接口为 `GET /admin/business-dashboard`。默认统计最近 7 天，也可以传入 UTC 的
`start` 和 `end` 查询参数，时间范围最多 31 天；销售角色即使直接调用接口也会收到 403。

看板直接读取现有客户、课程订单和服务工单，不新增表或迁移。订单金额只统计 `paid` 和
`completed`，工单的开放数统计 `open` 与 `in_progress`。当前数据模型没有单独的“续费订单”
类型，因此页面显示的“复购/续费近似率”定义为：重复付费客户数 / 至少有一笔 paid 或
completed 订单的客户数。这是学习阶段的可解释代理指标，不应当当作正式续费率；未来接入
真实订单分类后再替换口径。

### 管理后台统一首页

打开 `http://localhost:5174/admin` 会进入管理总览。页面复用现有的 AI 看板、业务经营看板、
系统状态和待处理建议接口，用卡片和简表展示当前管理重点；它不复制业务数据，也不新增数据库表。
管理员或经理可以从卡片跳转到对应详情页，销售角色不会看到管理导航，后端接口仍负责最终权限校验。

### 标签目录管理

管理后台的 `http://localhost:5174/admin/tags` 用于维护统一标签目录并查看使用统计。
`GET /admin/tags` 允许 admin/manager 查看；新建、编辑和启停用标签只允许 admin。
统计区分标签关联客户数、AI 建议数、人工确认数和拒绝数。标签停用只影响后续目录使用，
不会删除历史客户标签记录，也不会改变已有的人工确认结果。

### 管理后台订单与工单

管理后台的 `http://localhost:5174/admin/operations` 提供订单和服务工单的只读汇总，
后端接口为 `GET /admin/operations`。它复用客户页已经存在的 `course_orders` 和
`service_tickets` 表，不新增迁移；可按订单状态、工单状态筛选，且会沿用客户数据权限范围。
管理员可以查看全部可见客户，经理只查看自己组织范围内的客户，销售角色会被后端拒绝访问。

页面中的客户名称可以跳转到客户工作台；订单或工单的修改仍然在客户详情页完成，避免管理
汇总页绕过既有业务校验。工单摘要在后端解密后才返回给有权限的管理用户，运行日志和页面
不会打印密钥、JWT 或完整聊天正文。

### 管理后台权限矩阵

`http://localhost:5174/admin/permissions` 展示 `role_permissions` 中现有的角色、模块、动作
和数据范围。管理员可以修改已有配置的 `data_scope`，经理只能查看，销售角色不能访问；后端
接口分别是 `GET /admin/permissions` 和 `PATCH /admin/permissions/{permission_id}`。

本功能只调整已有权限记录，不新增表或迁移。`admin` 角色始终保持 `all` 数据范围，`customers`
模块不接受 `team` 范围，避免把当前客户数据过滤逻辑改成未定义状态。每次实际修改会和
`permission.data_scope_changed` 审计记录放在同一事务中，失败时不会只留下半条变更记录。

### 管理后台数据导出与保留策略

管理员可在 `http://localhost:5174/admin/data-export` 导出客户基础信息、聊天消息索引、审计日志
和 AI 采用反馈。后端接口为 `GET /admin/data-export/{dataset}`，支持 `format=csv|json`、
UTC `start/end` 和最多 10000 条记录。经理和销售不能访问导出接口。

导出默认脱敏：客户姓名、手机号、IP 地址会遮罩；聊天只保留截断后的脱敏预览，不导出
`content_encrypted`；AI 编辑正文只导出“是否存在”标记。每次导出都会写入
`admin.data_exported` 审计日志。当前策略不自动删除数据，也不擅自规定具体保留天数；
客户确认保留周期后，再配置定时清理和删除前复核流程。

### 客户流失风险定时评分

`worker` 同时注册 `churn_scoring` 队列；`churn-scheduler` 只负责定期把最新导入文件投递到
Redis，不直接计算模型。两个目录通过 Compose 挂载：

- `backend/data/churn_artifacts`：模型产物，Backend 可登记，Worker 只读。
- `backend/data/churn_imports`：待评分 CSV，Backend、Worker 和 Scheduler 都只读。

安全默认值是 `CHURN_SCORING_SCHEDULE_ENABLED=0`。准备好 CSV、在管理页面登记并审批模型后，
才可在 `infra/local.env` 中显式改为 `1` 并重启 `churn-scheduler`。重复投递同一模型、同一数据
指纹和同一来源不会重复生成统计批次。页面上的漂移告警只比较风险等级分布，不能解释为模型
准确率或真实流失概率。

历史清理脚本默认只预览。只有人工检查预计数量后添加 `--apply` 才会级联删除旧批次及其预测、
干预记录；客户、学生、日程和时间线不随评分批次删除。
