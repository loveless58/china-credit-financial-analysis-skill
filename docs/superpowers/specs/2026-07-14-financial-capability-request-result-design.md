# 财务分析能力 Request/Result 闭环设计

## 1. 设计结论

在现有 `financial_analysis_bundle -> DOCX` 安全主链外增加一个编排器无关的确定性外壳：

```text
capability_request.json
        ↓
run_financial_analysis_capability.py
        ↓
financial_analysis_bundle.json
        +
更新后的 DOCX
        +
capability_result.json
        +
完整审计凭证
```

统一入口只接受已经组装完成的 `financial_analysis_bundle`。原始财报抽取、来源选择、分析文字撰写仍由 Skill 工作流完成，不下沉到确定性入口，也不建设通用任务引擎。

## 2. 目标

- 为 Codex、Pi 或普通命令行提供同一个文件级调用契约；
- 复用现有 bundle 校验和 DOCX 安全写回逻辑；
- 将请求、bundle、输出文档、备份、数字审计、结构校验、变更日志和待核验清单固化到一个仓库外运行目录；
- 通过 `capability_result.json` 提供稳定状态、绝对路径、哈希、大小、指标和错误信息；
- 保证原始 DOCX 不被覆盖，失败时也尽可能保留审计凭证。

## 3. 非目标

- 不从任意原始财务数据自动生成完整 bundle；
- 不引入 LLM API、Agent 编排、MCP、hooks 或运行时插件；
- 不建设跨能力状态机、事件总线或重试框架；
- 不改变 `financial_analysis_bundle` 1.0 业务契约；
- 不复制 `update_financial_docx.py` 的备份、定位、写回和校验实现。

## 4. Request 契约

第一版 `capability_request` 只支持 `update_docx`：

```json
{
  "schema_version": "1.0",
  "capability": "china-credit-financial-analysis",
  "request_id": "run-20260714-001",
  "operation": "update_docx",
  "inputs": {
    "source_docx": "C:/business/input/report.docx",
    "financial_analysis_bundle": "C:/business/input/financial_analysis_bundle.json",
    "source_docx_sha256": "可选的64位SHA-256"
  },
  "artifact_directory": "C:/business/output/run-20260714-001"
}
```

相对路径以 request 文件所在目录为基准解析。运行目录必须位于 Skill 仓库外，并且在运行开始时不存在或为空。

## 5. Result 契约

`capability_result.json` 的稳定状态为：

- `success`：bundle、数字审计和 DOCX 校验全部通过；
- `blocked`：输入、哈希、bundle、数字或业务门禁未通过；
- `failed`：发生文件系统、解析或未预期执行错误。

Result 记录：

- request/capability/operation/version；
- 开始和结束时间；
- 输入文件绝对路径与 SHA-256；
- 原 DOCX 执行前后哈希及 `unchanged`；
- 所有已生成产物的绝对路径、SHA-256 和字节数；
- 数字审计发现数和 DOCX 失败检查数；
- 标准错误码、消息和明细。

Result 不记录自身哈希，避免递归定义。

## 6. 固定产物

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

失败运行至少保留已经可以安全生成的 request、bundle、bundle 校验、DOCX 校验、待核验清单和 capability result。

## 7. 退出码

- `0`：`success`
- `2`：`blocked`
- `3`：`failed`，或 request 无法解析到可信运行目录

## 8. 安全边界

- request、bundle、源 DOCX 和运行目录不得指向会覆盖同一个文件实体的路径；
- 可选输入哈希不一致时，在任何备份或写回前阻断；
- 运行目录非空时阻断，避免混合两次运行的凭证；
- 原 DOCX 前后哈希必须一致，否则结果不得为成功；
- 不输出最终授信审批结论或授信额度建议。

## 9. 验收

1. 有效 request 生成 bundle、更新 DOCX、result 和全部审计凭证；
2. result 符合严格 schema，所有成功产物路径存在且哈希匹配；
3. bundle 无效时返回 `blocked`，不生成备份和更新稿；
4. 输入哈希不匹配时在写回前阻断；
5. 运行目录位于仓库内或非空时阻断；
6. 原 DOCX 哈希保持不变；
7. 现有 bundle、数字审计、表格保真和 DOCX 回归全部继续通过；
8. 真实模板回归输出位于仓库外。

