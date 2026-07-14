# 财务分析能力调用契约 1.0

本契约为 Codex、Pi 或其他编排器提供同一个文件级调用入口。它不包含 Agent 状态、LLM 调用或原始财报抽取逻辑。

## 三层边界

| 文件 | 角色 | 主要内容 |
| --- | --- | --- |
| `capability_request.json` | 调用信封 | 请求 ID、固定 operation、输入路径、可选源文件哈希、运行产物目录。 |
| `financial_analysis_bundle.json` | 业务载荷 | 财务表、比率、风险关注点、待核验项和 DOCX 写回计划。 |
| `capability_result.json` | 执行回执 | 稳定状态、输入与产物描述符、原件完整性、审计指标和标准错误。 |

统一入口只接受已经组装完成的 bundle：

```powershell
python -B scripts/run_financial_analysis_capability.py C:\business\run\capability_request.json
```

## capability_request

```json
{
  "schema_version": "1.0",
  "capability": "china-credit-financial-analysis",
  "request_id": "run-20260714-001",
  "operation": "update_docx",
  "inputs": {
    "source_docx": "input/report.docx",
    "financial_analysis_bundle": "input/financial_analysis_bundle.json",
    "source_docx_sha256": "可选的64位SHA-256"
  },
  "artifact_directory": "output/run-20260714-001"
}
```

- 第一版只允许 `operation: update_docx`。
- 相对路径以 request 文件所在目录为基准，而不是当前 shell 目录。
- `request_id` 只允许字母、数字、点、下划线和连字符，长度 1 至 128。
- `source_docx_sha256` 可省略；提供时必须与运行前原件一致，否则在备份和写回前阻断。
- `artifact_directory` 必须位于 Skill 仓库外，且运行开始时不存在或为空。非空目录不会被清理或覆盖。
- 完整字段约束以 `schemas/capability_request.schema.json` 为准。

运行目录中的 `capability_request.json` 是路径已归一化为绝对路径的审计副本，便于确认本次实际输入，不用于覆盖调用方原 request。

## capability_result

稳定状态只有三种：

| 状态 | 含义 | 退出码 |
| --- | --- | --- |
| `success` | bundle、数字审计、DOCX 校验及原件完整性均通过。 | `0` |
| `blocked` | 输入、哈希、bundle、数字或 DOCX 业务门禁未通过。 | `2` |
| `failed` | 文件解析、文件系统或未预期执行错误。 | `3` |

Result 的 `inputs` 和 `artifacts` 使用统一描述符：

```json
{
  "path": "C:\\business\\output\\updated.docx",
  "sha256": "64位SHA-256",
  "size_bytes": 12345
}
```

`source_integrity` 记录原 DOCX 执行前后哈希及 `unchanged`。`metrics` 固定记录 `number_findings` 与 `docx_failed_checks`。`errors` 中每项均有稳定 `code`、可读 `message` 和 `details`。完整字段约束以 `schemas/capability_result.schema.json` 为准。

成功结果必须满足：

- 九类固定 artifact 描述符全部非空且指向实际文件；
- `source_integrity.unchanged` 为 `true`；
- 两项审计指标均为 `0`；
- `errors` 为空。

`capability_result.json` 不记录自身哈希，避免递归定义。调用方应以运行目录访问控制或外部清单封存该回执。

## 固定产物

成功运行目录包含：

```text
capability_request.json
financial_analysis_bundle.json
bundle_validation.json
capability_result.json
<source>.backup-<timestamp>.docx
<configured-output>.docx
number_audit.json
validation_result.json
change_log.md
待核验清单.md
```

阻断或失败时，结果中未生成的 artifact 为 `null`，已经安全生成的请求、bundle、校验、备份或其他审计文件仍保留。不能仅凭“目录中存在 DOCX”判断成功，必须读取 `capability_result.json`。

## 编排器接入规则

1. 编排器只负责准备 request、观察进程退出和读取 result，不解析 DOCX 内部结构。
2. 编排器不得绕过 bundle 校验、源哈希门禁或原 updater 直接修改 DOCX。
3. `blocked` 是可审计业务结果，不应自动改写为 `failed`，也不应无条件重试。
4. 需要人工补数或核验时，读取 `errors`、`bundle_validation.json` 和 `待核验清单.md` 后生成新 request；不得复用非空运行目录。
5. 业务产物始终放在仓库外；仓库只保存代码、Schema、参考契约和测试。
