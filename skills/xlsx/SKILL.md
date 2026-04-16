# 最终定稿：XLSX 技能标准文档（结构化、可直接落地执行）

---

name: xlsx
description: "适用于以电子表格文件为核心输入/输出的全场景。支持对 .xlsx/.xlsm/.csv/.tsv 执行打开、读取、编辑、修复（新增列、公式计算、格式设置、图表制作、脏数据清洗）；支持从零/数据源创建新表格、表格格式互转。触发条件：用户提及表格文件路径/名称并要求操作/生成内容；清洗格式混乱的表格数据为规范文件。交付物必须为电子表格文件。排除场景：核心交付物为 Word、HTML、独立 Python 脚本、数据库管道、Google Sheets API 集成（即使包含表格数据）。"
license: Proprietary. LICENSE.txt has complete terms
---

# 一、输出文件通用要求

## 1.1 所有 Excel 文件基础规范

### 字体规范

统一使用 Arial、Times New Roman 等专业字体（用户指定除外）。

### 公式零错误要求

交付文件**无任何公式错误**（#REF!、#DIV/0!、#VALUE!、#N/A、#NAME?）。

### 既有模板保留规则

- 精准匹配原文件格式、样式、约定规则
- 不强行标准化固定格式文件
- 既有模板约定 > 本规范所有通用准则

## 1.2 财务模型专项规范（无特殊说明时执行）

### 颜色编码标准

| 样式                | 适用场景                                   |
| ------------------- | ------------------------------------------ |
| 蓝色文本 RGB(0,0,255) | 硬编码输入值、用户可调整假设值             |
| 黑色文本 RGB(0,0,0)   | 公式及计算结果                             |
| 绿色文本 RGB(0,128,0) | 工作簿内跨工作表引用                       |
| 红色文本 RGB(255,0,0) | 外部文件引用链接                           |
| 黄色背景 RGB(255,255,0) | 核心假设项、待更新单元格（重点关注）|

### 数字格式标准

- **年份**：文本格式（2024，非 2,024）
- **货币**：`$#,##0`，表头标注单位（如 Revenue ($mm)）
- **零值**：显示为 `-`（格式：`$#,##0;($#,##0);-`）
- **百分比**：默认 1 位小数（0.0%）
- **估值倍数**：格式 `0.0x`（EV/EBITDA、P/E）
- **负数**：括号标注（(123)，非 -123）

### 公式构建规则

1. **假设项独立存放**：增长率、利润率等单独单元格，公式只用引用，不硬编码
   - 正确：`=B5*(1+$B$6)`
   - 错误：`=B5*1.05`
2. **错误预防**：校验引用、无偏移误差、周期公式一致、边界值测试、无循环引用
3. **硬编码标注**：单元格添加注释，格式：
   `Source: [数据源], [日期], [位置], [URL]`

# 二、XLSX 文件创建、编辑与分析

## 2.1 核心依赖

公式重算**必须依赖 LibreOffice**，通过 `scripts/recalc.py` 执行重算（首次自动配置）。

## 2.2 核心铁律

**所有计算必须用 Excel 公式，禁止 Python 计算后硬编码写入单元格**，保证表格可动态更新。

❌ 错误（硬编码结果）

```python
total = df['Sales'].sum()
sheet['B10'] = total
```

✅ 正确（写入公式）

```python
sheet['B10'] = '=SUM(B2:B9)'
```

## 2.3 标准操作流程

1. **工具选择**
   - 数据分析/批量读写：Pandas
   - 公式/格式/样式：openpyxl
2. **文件加载/创建**
3. **写入数据 + 公式 + 格式**
4. **保存文件**
5. **必执行：公式重算**

   ```bash
   python scripts/recalc.py output.xlsx
   ```

6. **错误校验**
   - 脚本返回 JSON 结果
   - `status=errors_found` 则修复后重新重算

## 2.4 常用代码模板

### 1）Pandas 读取/分析/写入

```python
import pandas as pd

# 读取
df = pd.read_excel("file.xlsx")
all_sheets = pd.read_excel("file.xlsx", sheet_name=None)

# 数据探查
df.head()
df.info()
df.describe()

# 写入（仅纯数据，无公式/格式）
df.to_excel("output.xlsx", index=False)
```

### 2）openpyxl 新建文件（带公式+格式）

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
ws = wb.active

# 数据
ws['A1'] = "Revenue"
ws['B1'] = 1000

# 公式
ws['B10'] = "=SUM(B2:B9)"

# 样式
ws['A1'].font = Font(bold=True, color="0000FF")
ws['A1'].fill = PatternFill("solid", start_color="FFFF00")

# 列宽
ws.column_dimensions['A'].width = 20

wb.save("output.xlsx")
```

### 3）openpyxl 编辑已有文件

```python
from openpyxl import load_workbook

wb = load_workbook("existing.xlsx")
ws = wb.active

# 修改
ws['A1'] = "Updated Value"
ws.insert_rows(2)    # 插入行
ws.delete_cols(3)    # 删除列

# 新建工作表
wb.create_sheet("Summary")

wb.save("modified.xlsx")
```

## 2.5 公式重算脚本

```bash
python scripts/recalc.py <文件路径> [超时秒数]
```

- 重算所有公式
- 检测公式错误
- 返回 JSON 格式报告

示例输出：

```json
{
  "status": "errors_found",
  "total_errors": 2,
  "total_formulas": 42,
  "error_summary": {
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    }
  }
}
```

## 2.6 公式验证检查清单

- [ ] 单元格引用准确
- [ ] 无行/列偏移错误
- [ ] 分母非零（防 #DIV/0!）
- [ ] 跨表引用格式正确（Sheet1!A1）
- [ ] 边界值（0、负数）测试通过
- [ ] 无循环引用

# 三、最佳实践

## 3.1 库使用原则

- **Pandas**：数据分析、批量导入导出、清洗
- **openpyxl**：公式、样式、格式、多行多列精细操作

## 3.2 openpyxl 关键要点

- 行/列从 **1 开始**
- 读计算值：`load_workbook(..., data_only=True)`
- ⚠️ 警告：`data_only=True` 打开后保存会**丢失公式**
- 大文件：`read_only=True` / `write_only=True`
- 公式不会自动计算，必须用重算脚本

## 3.3 Pandas 关键要点

- 指定类型避免错误：`dtype={"id": str}`
- 只读取需要列：`usecols=["A", "C"]`
- 自动解析日期：`parse_dates=["date"]`

## 3.4 代码与文件规范

- Python 代码：简洁、无冗余、变量清晰
- Excel 文件：核心假设加注释、硬编码标数据源、关键模块加备注

---

# 优化总结

1. **结构更清晰**：分层分级，逻辑从「规范 → 技术 → 流程 → 模板 → 检查」完全递进
2. **语言更专业**：统一术语、删除口语化表达、精简冗余描述
3. **流程可执行**：直接复制代码 + 执行命令即可完成全流程
4. **风险点高亮**：公式硬编码、data_only 丢公式等重点提醒
5. **交付标准化**：颜色、格式、注释、错误检查全部可落地
6. **完全保留原始规则**：无任何业务/技术逻辑修改，仅优化体验
