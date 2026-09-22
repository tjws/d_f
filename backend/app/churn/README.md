# 客户流失风险模块

本阶段实现一个独立、可重复执行的离线机器学习实验，不接客户业务表、API 或前端。
模型只用于辅助人工确定跟进优先级，不会自动联系客户。

## 调用链

```text
k12_churn.csv
  -> scripts/train_churn_baseline.py       命令行入口与参数
  -> churn/dataset.py                      字段校验、清洗、数据质量报告
  -> churn/training.py                     切分训练集/验证集/测试集
  -> churn/pipeline.py                     预处理 + Logistic Regression
  -> churn/evaluation.py                   验证集选阈值、测试集算指标
  -> churn/artifacts.py                    保存模型包与 JSON 报告
  -> backend/data/churn_artifacts/         本地产物，不进入 Git
```

## 为什么这样分层

- `contracts.py` 是统一数据契约，防止各处对字段含义理解不同。
- `dataset.py` 只关心输入是否可靠，不关心使用什么算法。
- `pipeline.py` 把缺失值、标准化、独热编码与模型锁在一起，保证训练和预测一致。
- `training.py` 负责实验流程，不直接处理文件路径或输出格式。
- `evaluation.py` 把技术指标翻译为召回率、Top 20% 命中率和提升度等业务指标。
- `artifacts.py` 负责产物版本和落盘，以后可替换成模型仓库而不改训练逻辑。

## 当前边界

- CSV 是静态快照，没有 `observed_at` 和未来 30 天结果窗口，所以不能证明“提前 30 天”预警。
- 当前使用分层随机切分，适合教学基线；有历史时间字段后应改成按时间切分。
- `student_id` 只用于识别样本，禁止进入模型；`is_churned` 是答案，也禁止进入特征。
- `total_spend` 的空值保留为缺失，由训练流水线使用训练集的中位数填补。
- `class_weight="balanced"` 用于降低漏掉流失客户的风险，但最终阈值仍需业务确认。
- `.joblib` 本质上是 Python 序列化文件，只能加载本系统自己生成且来源可信的模型文件。

## 手动运行

在 `backend` 目录执行：

```powershell
E:\Anaconda\envs\py313\python.exe -m scripts.train_churn_baseline `
  --csv "C:\Users\Administrator\Desktop\测试数据\kk\k12_churn.csv"
```

默认输出：

- `backend/data/churn_artifacts/churn_logistic_baseline.joblib`
- `backend/data/churn_artifacts/churn_logistic_baseline_report.json`

## 第二阶段：批量评分与追溯

第二阶段读取第一阶段生成的可信模型，把无标签的待评分 CSV 转换成风险排名并写入独立表：

```text
待评分 CSV + churn_logistic_baseline.joblib
  -> scripts/score_churn_batch.py
  -> churn/dataset.py                    复用与训练相同的数据清洗
  -> churn/inference.py                  校验模型契约、预测概率、排名和分级
  -> services/churn_risk_service.py      事务编排与批次状态
  -> dao/churn_risk_dao.py               数据库读写
  -> churn_scoring_batches               一次评分的模型、数据和数量摘要
  -> churn_risk_predictions              每个学生的概率、等级和批次内排名
```

高风险阈值来自第一阶段的验证集。中风险阈值默认是高风险阈值的 60%，它属于可调整的业务分级规则，
不是模型自行学习出的客观事实。批量评分不会修改客户或学生主表，也不会触发消息发送。

先在仓库根目录升级数据库：

```powershell
E:\Anaconda\envs\py313\python.exe -m alembic upgrade head
```

再在 `backend` 目录执行：

```powershell
E:\Anaconda\envs\py313\python.exe -m scripts.score_churn_batch `
  --csv "C:\Users\Administrator\Desktop\测试数据\kk\k12_churn.csv"
```

## 第三阶段：只读风险管理页面

评分数据通过受权限保护的管理接口提供给 Vue 页面：

```text
frontend/views/admin/ChurnRiskView.vue
  -> frontend/api/churnRisks.ts
  -> GET /admin/churn-risks/batches
  -> GET /admin/churn-risks/batches/{batch_id}
  -> schemas/churn_risk.py
  -> services/churn_risk_admin_service.py
  -> dao/churn_risk_dao.py
  -> churn_scoring_batches / churn_risk_predictions
```

- `admin` 和 `manager` 可以查看，`sales` 由后端返回 403。
- 页面上的 `risk_score` 只表示风险排序分值，不宣传为真实流失概率。
- 页面只读，不会修改客户、创建日程或自动发送消息。
- 前端地址：`/admin/churn-risks`。

## 第四阶段：学生映射与人工干预闭环

外部编号不能直接假定为本系统 `students.id`。系统使用来源命名空间建立映射：

```text
source_system + external_student_id
  -> external_student_mappings
  -> students
  -> customers
  -> customer.owner_id / organization_id 权限范围
  -> churn_risk_predictions.mapping_id 历史快照
```

- 管理员可以看到未映射记录；经理和销售只看到已映射且位于自己数据范围内的客户。
- 管理员或经理创建映射时，会回填同一来源、同一编号的历史未映射风险记录。
- 一条预测只允许创建一个 `churn_risk_interventions` 生命周期，重复提交返回冲突。
- 创建干预会在同一事务中创建 `schedules`、`timeline_events` 和 `audit_logs`。
- 完成干预必须由人工填写 `retained/recovered/churned/unknown`，不会自动改变客户阶段或发送消息。
- 前端统一入口：`/churn-risks`；管理员后台仍可从 `/admin/churn-risks` 进入。

## 第五阶段：真正的时间型训练契约

静态 CSV 仍使用原来的随机分层基线。只有数据增加以下字段后，才能验证未来窗口预警：

- `observed_at`：特征快照时点，UTC ISO 8601。
- `label_window_end`：未来标签窗口结束时间；默认必须等于观察时点后 30 天。
- `is_churned`：该未来窗口内是否流失。

时间型训练使用按时间顺序的 `purged_time_split`。凡是标签窗口跨越下一数据分区边界的样本都会被清除，避免训练阶段偷看到未来结果：

```powershell
E:\Anaconda\envs\py313\python.exe -m scripts.train_churn_baseline `
  --csv "C:\data\k12_churn_temporal.csv" `
  --temporal `
  --horizon-days 30
```

## 第六阶段：模型治理、队列和运行监控

```text
模型文件 + 评测报告
  -> 管理员登记 candidate
  -> 管理员人工审批 approved（旧版本 retired）
  -> API 或 scheduler 投递 Dramatiq
  -> Worker 加载已审批模型
  -> 幂等检查（模型指纹 + 数据指纹 + 来源）
  -> 批量评分
  -> 风险等级分布漂移提示
```

目录约定：

- `backend/data/churn_artifacts/`：可信模型和评测报告，不进入 Git。
- `backend/data/churn_imports/`：待评分 CSV，不进入 Git；容器以只读方式挂载。

环境变量：

- `CHURN_SCORING_SCHEDULE_ENABLED=0`：默认关闭定时评分。
- `CHURN_SCORING_INTERVAL_SECONDS=86400`：显式开启后的投递间隔，最少 300 秒。
- `CHURN_DISTRIBUTION_DRIFT_THRESHOLD=0.15`：风险等级占比绝对变化告警阈值。

分布漂移只是运行提示，不等同于特征漂移、模型准确率下降或真实客户流失概率。
定时器只负责投递，Worker 才执行评分；同一模型和同一份文件重复投递会复用已有批次。

历史清理默认只预览，只有明确追加 `--apply` 才删除：

```powershell
E:\Anaconda\envs\py313\python.exe -m scripts.cleanup_churn_history --older-than-days 730
E:\Anaconda\envs\py313\python.exe -m scripts.cleanup_churn_history --older-than-days 730 --apply
```
