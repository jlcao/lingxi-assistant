---
name: xlsx
description: "Comprehensive spreadsheet operations including read, analyze, merge, create, edit, and sort. Supports Excel files (.xlsx, .xlsm) and CSV files (.csv, .tsv)."
version: "2.1.0"
trigger_conditions: "用户请求读取Excel文件、分析数据、合并表格、创建新表格、编辑表格或排序表格时触发"
execution_guidelines: "1. 根据operation参数执行相应操作\n2. 返回操作结果或错误信息\n3. 支持多种Excel操作：读取、分析、合并、创建、编辑、排序"
author: "Lingxi Team"
license: MIT
---

# XLSX Skill Documentation

## Overview

This skill provides comprehensive Excel file operations including reading, analyzing, merging, creating, and editing Excel files.

## Operations

### 1. Read (读取Excel文件)

Read an Excel file and return its structure and content.

**Parameters:**

- `operation` (required): "read"
- `file_path` (required): Path to the Excel file

**Returns:**

- Success: File path, row count, column count, column names, and first 5 rows
- Error: Error message

**Example:**

```python
xlsx(operation="read", file_path="人员信息.xlsx")
```

### 2. Analyze (分析Excel文件)

Analyze an Excel file and return detailed statistics.

**Parameters:**

- `operation` (required): "analyze"
- `file_path` (required): Path to the Excel file

**Returns:**

- Success: Data shape, data types, and statistical information
- Error: Error message

**Example:**

```python
xlsx(operation="analyze", file_path="人员信息.xlsx")
```

### 3. Merge (合并Excel文件)

Merge two Excel files based on common columns.

**Parameters:**

- `operation` (required): "merge"
- `file_path1` (required): Path to the first Excel file
- `file_path2` (required): Path to the second Excel file
- `output_file` (optional): Path for the merged output file (default: "merged.xlsx")

**Returns:**

- Success: Merge result, file information, and output file details
- Error: Error message

**Example:**

```python
xlsx(
    operation="merge",
    file_path1="人员信息.xlsx",
    file_path2="员工信息表.xlsx",
    output_file="合并后的人员信息.xlsx"
)
```

### 4. Create (创建Excel文件)

Create a new Excel file from content.

**Parameters:**

- `operation` (required): "create"
- `output_file` (optional): Path for the output file (default: "output.xlsx")
- `content` (required): Content to write (CSV format)

**Returns:**

- Success: Creation result and file information
- Error: Error message

**Example:**

```python
xlsx(
    operation="create",
    output_file="output.xlsx",
    content="name,age\nAlice,25\nBob,30"
)
```

### 5. Edit (编辑Excel文件)

Edit an existing Excel file.

**Parameters:**

- `operation` (required): "edit"
- `file_path` (required): Path to the Excel file

**Returns:**

- Success: Edit result and file information
- Error: Error message

**Example:**

```python
xlsx(operation="edit", file_path="人员信息.xlsx")
```

### 6. Sort (排序Excel文件)

Sort an Excel file by a specified column.

**Parameters:**

- `operation` (required): "sort"
- `file_path` (required): Path to the Excel file
- `column` (required): Column name to sort by
- `ascending` (optional): Sort order, true for ascending, false for descending (default: true)

**Returns:**

- Success: Sort result, original file, sort column, sort order, and output file details
- Error: Error message

**Example:**

```python
xlsx(
    operation="sort",
    file_path="人员信息.xlsx",
    column="年龄",
    ascending=False
)
```

## Dependencies

- pandas
- openpyxl

Install dependencies:

```bash
pip install pandas openpyxl
```

## Error Handling

The skill will return clear error messages for common issues:

- Missing required parameters
- File not found
- Invalid operation type
- Execution errors

## Best Practices

1. **File Paths**: Always use absolute or relative file paths correctly
2. **Merge Keys**: The merge operation automatically detects common columns
3. **Data Types**: The skill handles various data types automatically
4. **Error Handling**: Always check the return value for error messages
