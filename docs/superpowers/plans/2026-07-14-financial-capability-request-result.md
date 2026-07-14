# Financial Capability Request/Result Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 `capability_request.json` 驱动现有财务 bundle 到 DOCX 主链，并始终产出可机读的 `capability_result.json` 与审计凭证。

**Architecture:** 新入口只做 request 校验、路径解析、bundle 固化、调用现有 `update_financial_docx.update_financial_docx`、哈希清单和结果封装。业务校验、备份、DOCX 定位、格式保留、数字审计与结构校验继续由现有模块负责。

**Tech Stack:** Python 3 标准库、python-docx、JSON Schema 文档、现有自定义 bundle 校验器和 DOCX 更新器。

## Global Constraints

- 不引入 Agent、插件、MCP、hooks 或 LLM API。
- 不从原始财务数据自动生成分析文字或完整 bundle。
- 不修改 `financial_analysis_bundle` 1.0 字段。
- 所有运行产物必须位于 Skill 仓库外。
- 原始 DOCX 不得被覆盖。
- 只复用现有 DOCX 更新器，不复制底层写回逻辑。

---

### Task 1: Request/Result 契约与校验

**Files:**
- Create: `schemas/capability_request.schema.json`
- Create: `schemas/capability_result.schema.json`
- Create: `scripts/validate_capability_contract.py`
- Create: `scripts/selftest_financial_capability.py`

**Interfaces:**
- Produces: `validate_request(payload) -> list[str]`
- Produces: `validate_result(payload) -> list[str]`

- [ ] 编写 request/result 有效与无效样例测试，并确认因模块缺失而失败。
- [ ] 实现严格字段、枚举、路径字符串、哈希和 artifact descriptor 校验。
- [ ] 运行 `python -X utf8 -B scripts/selftest_financial_capability.py --case contract` 并确认通过。
- [ ] 提交契约与校验器。

### Task 2: 统一执行入口

**Files:**
- Create: `scripts/run_financial_analysis_capability.py`
- Modify: `scripts/selftest_financial_capability.py`

**Interfaces:**
- Consumes: `run_financial_analysis_capability.py <capability_request.json>`
- Produces: `capability_result.json`，退出码 `0/2/3`

- [ ] 编写成功、bundle 阻断、输入哈希不一致和非空运行目录测试，并确认失败。
- [ ] 实现相对路径解析、仓库外目录门禁、request/bundle 固化和输入哈希。
- [ ] 调用现有 `update_financial_docx()`，汇总其业务产物，不复制写回逻辑。
- [ ] 生成 result、产物哈希、源文件完整性和指标。
- [ ] 运行全部 capability self-test 并提交。

### Task 3: Skill 与文档集成

**Files:**
- Modify: `SKILL.md`
- Create: `references/financial-capability-contract.md`
- Modify: `references/financial-analysis-bundle.md`

- [ ] 增加统一入口触发条件、命令示例和失败状态说明。
- [ ] 明确 bundle 仍是业务输出，result 是运行凭证，两者不能互相替代。
- [ ] 运行 Skill 校验、现有自测和 `git diff --check`。
- [ ] 提交文档集成。

### Task 4: 真实模板回归

**Files:**
- No repository files expected.

- [ ] 在仓库外创建 request、bundle 和运行目录。
- [ ] 使用真实模板执行统一入口。
- [ ] 校验 source hash、bundle、DOCX、result、审计凭证和 staging 清理。
- [ ] 渲染更新稿关键页，确认无重叠、截断和表格破坏。
- [ ] 完成审查、合并和推送。

