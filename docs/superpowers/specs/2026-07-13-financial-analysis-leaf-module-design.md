# 财务分析叶子模块第一阶段设计

## 1. 设计结论

第一阶段继续在 `china-credit-financial-analysis-skill-work` 中完善现有 Skill，不建设完整 Agent、插件运行框架或多 Skill 编排器。

本阶段只增加三个工程能力：

1. 一个稳定的 `financial_analysis_bundle.json` 输出契约；
2. 一个确定性的 bundle 校验器；
3. 一个串联现有备份、DOCX 写回、数字审计和结构校验能力的安全入口。

现有 Skill 仍可独立更新授信评审报告财务章节；未来 `risk-analyst`、`report-writer` 或 `bank-rm-vertical` 通过 bundle 读取其分析结果，不依赖 DOCX 内部结构和临时过程文件。

## 2. 设计依据

### 2.1 现有 Skill 的有效经验

现有 Skill 已形成适合叶子能力的四层结构：

- `SKILL.md` 定义触发条件、硬规则和标准流程；
- `references/` 保存来源优先级、财务口径、写作和 DOCX 规则；
- `scripts/` 承担抽取、单位转换、确定性计算、备份、写回和校验；
- `templates/` 保存银行报告和行业写作模板。

第一阶段应复用这些能力，补齐接口和端到端写回闭环，而不是重新建设运行平台。

### 2.2 `anthropics/financial-services` 的分层经验

参考仓库将职责分为：

- Skill：业务方法、规则、引用资料和局部确定性脚本；
- Vertical plugin：Skill 源头、薄命令入口和可选连接器；
- Agent plugin：端到端工作流提示和所需 Skill 副本；
- 仓库治理：检查 manifest、引用关系和 Skill 副本漂移。

结构化 Schema 只放在真实的跨组件输出边界上，运行编排和仓库治理不下沉到每一个叶子 Skill。第一阶段据此只为财务分析的公开输出建立 Schema。

## 3. 范围

### 3.1 本阶段包含

- 统一财务分析结构化输出；
- 保留金额、期间、单位、口径、来源和状态；
- 确定性计算同比及财务比率；
- 生成有证据支持的风险关注点和待核验事项；
- 根据明确的写回计划更新 DOCX 财务章节；
- 写回前创建时间戳备份；
- 保留原资产负债表格式；
- 执行数字反向审计和 DOCX 结构校验；
- 将业务产物输出到用户指定的仓库外目录。

### 3.2 本阶段不包含

- 完整授信报告生成；
- 多 Agent 或跨 Skill 编排；
- CRM、征信、工商、司法或外部 MCP 接入；
- 客户资料维护；
- 授信额度建议或最终审批结论；
- `commands/`、`hooks/` 或插件 manifest；
- 运行状态机、事件日志和通用任务调度框架；
- 全量文件哈希清单和四级运行过程包；
- Agent Skill 同步或副本漂移治理。

现有公告抓取、官方 PDF 抽取、Excel 导入和文本导入脚本可继续保留，但不作为第一阶段主链验收的必选能力，也不继续横向扩展。

## 4. 目标结构

只在现有目录中增加必要文件：

```text
china-credit-financial-analysis-skill-work/
├─ SKILL.md
├─ schemas/
│  └─ financial_analysis_bundle.schema.json
├─ references/
│  ├─ financial-analysis-bundle.md
│  └─ 现有业务规则
├─ scripts/
│  ├─ validate_financial_analysis_bundle.py
│  ├─ update_financial_docx.py
│  └─ 现有确定性脚本
└─ templates/
   └─ 现有银行及行业模板
```

不为目录完整性创建空 Skill、空 Hook 或未使用的连接器。

## 5. 模块边界

### 5.1 财务分析 Skill

负责：

- 选择可信数据来源；
- 锁定口径、期间和单位；
- 调用确定性脚本完成数据归一化和计算；
- 根据已验证数据撰写财务分析；
- 组装 `financial_analysis_bundle.json`；
- 在写回前调用 bundle 校验器；
- 用户要求更新 DOCX 时调用安全写回入口。

不得直接心算同比或比率，不得把缺少来源、单位不明或存在冲突的数据写入正文。

### 5.2 Bundle Schema

负责定义公开输出字段、字段类型、必要状态和允许值。Schema 使用显式版本号，并拒绝未声明的顶层字段。

Schema 不负责业务计算，也不记录运行调度状态。

### 5.3 Bundle 校验器

`validate_financial_analysis_bundle.py` 负责：

- 执行 JSON Schema 校验；
- 检查正文可用数据仅来自 `verified` 或 `calculated` 状态；
- 检查金额和比率包含来源或计算输入；
- 检查单位、口径和期间完整；
- 检查 `docx_write_plan` 的必要字段；
- 检查风险点不包含最终审批结论。

校验失败时退出非零，不触发 DOCX 写回。

### 5.4 DOCX 安全写回入口

`update_financial_docx.py` 是现有脚本的薄编排层，不重新实现底层 DOCX 逻辑。它按固定顺序调用或复用：

1. bundle 校验；
2. 时间戳备份；
3. 财务章节定位；
4. 正文和表格写回；
5. 资产负债表格式保留；
6. 数字反向审计；
7. DOCX 结构校验；
8. 修改说明导出。

任一步失败即停止。不得覆盖唯一原件，不得在章节定位失败后自动改为危险的替换或追加方式。

## 6. 数据流

```mermaid
flowchart LR
    A["DOCX 与财务数据"] --> B["标准化 metric pack"]
    B --> C["确定性财务指标计算"]
    C --> D["模板化分析与风险归纳"]
    D --> E["financial_analysis_bundle.json"]
    E --> F["bundle 校验"]
    F -->|"仅分析"| G["供未来 Skill 或人工读取"]
    F -->|"更新 DOCX"| H["DOCX 安全写回入口"]
    H --> I["备份、写回、审计、校验"]
    I --> J["更新稿与审计产物"]
```

DOCX 是可选交付形式，bundle 才是叶子模块的稳定公开接口。

## 7. `financial_analysis_bundle` 契约

第一版顶层结构为：

```json
{
  "schema_version": "1.0",
  "company_name": "某公司",
  "reporting_basis": "合并口径",
  "currency": "CNY",
  "unit": "万元",
  "periods": ["2024", "2025"],
  "sources": {},
  "financial_tables": {},
  "ratios": {},
  "risk_points": [],
  "pending_verification": [],
  "docx_write_plan": {}
}
```

字段职责：

- `sources`：来源标识、名称、类型和本地文件引用；
- `financial_tables`：资产负债、利润、现金流及财务指标的标准化数据；
- `ratios`：公式、输入指标、结果、展示值和计算状态；
- `risk_points`：证据支持的风险关注事项及其来源引用；
- `pending_verification`：缺失、冲突、来源不足或单位不明事项；
- `docx_write_plan`：待写入正文、表格二维数据、写回模式、章节锚点、目标单位、格式保留和输出文件名。

统一数据状态沿用现有口径：

```text
verified
calculated
source_missing
unit_missing
conflict
missing
llm_generated_blocked
```

只有 `verified` 和 `calculated` 数据可以进入正式正文。

Bundle 不包含 `run_id`、运行状态机、事件日志、仓库治理信息和全量文件哈希。

## 8. DOCX 写回约束

写回计划至少提供：

- `mode`：`insert` 或 `replace`；
- `section_start` 和 `section_end`；
- `analysis_anchor`：财务分析正文的精确起始锚点；
- `analysis_markdown`：已通过数字审计的待写入正文；
- `table_rows`：按目标 DOCX 表格形状组织的二维文本数组；
- `target_unit`；
- `require_backup: true`；
- `preserve_asset_liability_table: true`；
- `change_shading`；
- `output_filename`。

替换模式还必须满足：

- 原财务章节起止位置可确定；
- 备份已成功创建；
- 原资产负债表可定位并复用；
- 输出路径不是原文件路径；
- bundle 校验已通过。

章节定位不可靠时停止写回，保留分析 bundle 和待核验事项供人工处理。

## 9. 业务产物与仓库分离

所有业务运行要求用户显式指定仓库外输出目录。Skill 仓库不保存真实客户资料、原始授信报告、备份文件、更新稿或运行过程目录。

一次完整写回应保留：

```text
normalized_metric_pack.json
calculated_metrics.json
financial_analysis_bundle.json
更新后的 DOCX
备份 DOCX
number_audit.json
validation_result.json
change_log.md
待核验清单.md
```

这些产物足以追溯数据来源、确定性计算、写回范围、校验结果和人工待办，不再增加通用事件日志或运行清单。

## 10. 失败处理

第一阶段只区分结果，不建设通用状态机：

- 数据、单位、来源或章节定位不满足准入条件：停止写回并输出待核验事项；
- bundle Schema 或业务规则校验失败：退出非零；
- 备份失败：退出非零，禁止写回；
- DOCX 写回或结构校验失败：保留备份和校验结果，不宣称完成；
- 视觉渲染工具不可用：明确记录只完成结构校验，不宣称视觉验收完成。

## 11. 测试与验收

### 11.1 自动化测试

第一阶段只增加与新边界直接相关的测试：

- 一个合法 bundle 可以通过 Schema 和业务校验；
- 单位缺失、来源冲突、非法状态和审批结论被拒绝；
- 一个合成 DOCX 可以完成备份、章节更新、格式保留、数字审计和结构校验；
- 原始 DOCX 未被修改；
- 写回失败时不会产生被标记为完成的更新稿。

测试使用虚构公司和临时目录，不把测试运行产物留在仓库。

### 11.2 真实模板回归

在仓库外使用一份现有银行授信报告副本执行回归，检查：

- 财务章节位置正确；
- 资产负债表结构未退化；
- 字体、字号、底纹、表格顺序和单位符合模板；
- 写入数字均可追溯至 bundle；
- 原始文件和业务数据未进入 Git。

如环境支持渲染，检查更新页面的视觉布局；不支持时明确记录限制。

### 11.3 第一阶段完成条件

只有以下条件全部满足，第一阶段才完成：

1. bundle 契约稳定且校验器通过正反例测试；
2. DOCX 安全写回入口完成端到端合成测试；
3. 至少一次仓库外真实模板回归通过；
4. 备份、修改说明、待核验清单和校验结果完整；
5. 原始 DOCX 未被覆盖；
6. 仓库中没有业务运行产物；
7. Skill 结构校验和现有回归测试通过；
8. 未输出最终授信审批结论。

## 12. 第二阶段迁移原则

第一阶段验收后再创建最小 `bank-rm-vertical`：

```text
bank-rm-vertical/
├─ .claude-plugin/plugin.json
├─ commands/
│  └─ credit-report.md
└─ skills/
   └─ credit-analysis/
```

第二阶段遵循以下原则：

- 导入已经验证的财务分析叶子模块，不重写 bundle；
- command 保持薄，只负责加载 Skill 和接收输入；
- 不创建没有实现内容的 `client-profile`、`docx-author`、hooks 或 MCP；
- 出现第二个真实 Skill 后再扩展 vertical；
- 出现真实跨 Skill 编排需求后再建设 Agent；
- 出现 Agent 内置 Skill 副本后再引入同步和漂移检查。

## 13. 设计约束摘要

第一阶段的复杂度上限是：

```text
一个公开 bundle
+ 一个 bundle 校验器
+ 一个 DOCX 安全写回入口
+ 复用现有确定性脚本
```

任何新增组件都必须直接服务于 bundle 可复用性或 DOCX 写回完整性，否则推迟到第二阶段或更后阶段。
