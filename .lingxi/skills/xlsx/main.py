#!/usr/bin/env python3
"""XLSX skill implementation - provides actual Excel operations"""

import logging
import os
import subprocess
from typing import Dict, Any


def execute(parameters: Dict[str, Any]) -> str:
    """Execute XLSX skill

    Args:
        parameters: Parameters dictionary
            - operation: Operation type (read, analyze, merge, create, edit)
            - file_path: File path (for read, analyze, edit operations)
            - file_path1: First file path (for merge operation)
            - file_path2: Second file path (for merge operation)
            - output_file: Output file path (for merge, create operations)
            - content: Content to write (for create operation)
            - description: Description of the operation

    Returns:
        Operation result
    """
    logger = logging.getLogger(__name__)

    operation = parameters.get("operation", "read")
    logger.debug(f"执行XLSX技能，参数: {parameters}")

    try:
        if operation == "read":
            return _read_excel(parameters)
        elif operation == "analyze":
            return _analyze_excel(parameters)
        elif operation == "merge":
            return _merge_excel(parameters)
        elif operation == "create":
            return _create_excel(parameters)
        elif operation == "edit":
            return _edit_excel(parameters)
        elif operation == "sort":
            return _sort_excel(parameters)
        else:
            return f"错误: 不支持的操作类型 '{operation}'。支持的操作: read, analyze, merge, create, edit, sort"

    except Exception as e:
        logger.error(f"执行XLSX技能失败: {e}")
        return f"错误: XLSX技能执行失败 - {str(e)}"


def _read_excel(parameters: Dict[str, Any]) -> str:
    """Read Excel file"""
    file_path = parameters.get("file_path")
    if not file_path:
        return "错误: 缺少file_path参数"

    if not os.path.exists(file_path):
        return f"错误: 文件不存在 - {file_path}"

    try:
        import pandas as pd
        df = pd.read_excel(file_path)
        
        result = f"成功读取Excel文件: {file_path}\n\n"
        result += f"行数: {len(df)}\n"
        result += f"列数: {len(df.columns)}\n"
        result += f"列名: {list(df.columns)}\n\n"
        result += f"前5行数据:\n{df.head().to_string()}"
        
        return result
    except ImportError:
        return "错误: 需要安装pandas库。请运行: pip install pandas openpyxl"
    except Exception as e:
        return f"错误: 读取Excel文件失败 - {str(e)}"


def _analyze_excel(parameters: Dict[str, Any]) -> str:
    """Analyze Excel file"""
    file_path = parameters.get("file_path")
    if not file_path:
        return "错误: 缺少file_path参数"

    if not os.path.exists(file_path):
        return f"错误: 文件不存在 - {file_path}"

    try:
        import pandas as pd
        df = pd.read_excel(file_path)
        
        result = f"成功分析Excel文件: {file_path}\n\n"
        result += f"数据形状: {df.shape}\n"
        result += f"数据类型:\n{df.dtypes.to_string()}\n\n"
        result += f"统计信息:\n{df.describe().to_string()}"
        
        return result
    except Exception as e:
        return f"错误: 分析Excel文件失败 - {str(e)}"


def _merge_excel(parameters: Dict[str, Any]) -> str:
    """Merge Excel files"""
    file_path1 = parameters.get("file_path1")
    file_path2 = parameters.get("file_path2")
    output_file = parameters.get("output_file", "merged.xlsx")

    if not file_path1 or not file_path2:
        return "错误: 缺少file_path1或file_path2参数"

    if not os.path.exists(file_path1):
        return f"错误: 文件不存在 - {file_path1}"
    if not os.path.exists(file_path2):
        return f"错误: 文件不存在 - {file_path2}"

    try:
        import pandas as pd
        df1 = pd.read_excel(file_path1)
        df2 = pd.read_excel(file_path2)
        
        # 找到共同列
        common_columns = list(set(df1.columns) & set(df2.columns))
        
        if not common_columns:
            # 如果没有共同列，使用所有列
            merged_df = pd.concat([df1, df2], ignore_index=True)
        else:
            # 使用第一个共同列进行合并
            merge_key = common_columns[0]
            merged_df = pd.merge(df1, df2, on=merge_key, how='outer')
        
        merged_df.to_excel(output_file, index=False)
        
        result = f"成功合并Excel文件!\n\n"
        result += f"文件1: {file_path1} ({len(df1)}行 x {len(df1.columns)}列)\n"
        result += f"文件2: {file_path2} ({len(df2)}行 x {len(df2.columns)}列)\n"
        result += f"输出文件: {output_file}\n"
        result += f"合并结果: {len(merged_df)}行 x {len(merged_df.columns)}列"
        
        return result
    except Exception as e:
        return f"错误: 合并Excel文件失败 - {str(e)}"


def _create_excel(parameters: Dict[str, Any]) -> str:
    """Create new Excel file
    
    支持两种参数格式:
    1. content: CSV格式字符串
    2. data: Python列表/字典 (DataFrame可直接接收的数据)
    
    输出文件路径:
    - file_path 或 output_file (优先使用 file_path)
    """
    # 确定输出文件路径
    output_file = parameters.get("file_path") or parameters.get("output_file", "output.xlsx")
    
    # 获取数据
    content = parameters.get("content")
    data = parameters.get("data")
    
    # 参数校验
    if not content and not data:
        return (
            "错误: 创建Excel文件缺少数据参数。\n"
            "请提供以下任一参数:\n"
            "  - content: CSV格式字符串 (例如: '姓名,年龄\\n张三,25\\n李四,30')\n"
            "  - data: Python列表/字典 (例如: [{'姓名': '张三', '年龄': 25}, ...])"
        )
    
    # 如果同时传了 content 和 data，优先使用 data
    if data is not None and content:
        logging.getLogger(__name__).warning("同时提供了 content 和 data 参数，优先使用 data")
    
    try:
        import pandas as pd
        from io import StringIO
        
        # 根据数据类型创建 DataFrame
        if data is not None:
            # 使用 data 参数 (列表/字典)
            if not isinstance(data, (list, dict)):
                return (
                    f"错误: data 参数类型不正确。期望 list 或 dict，实际得到 {type(data).__name__}\n"
                    f"示例: [{'姓名': '张三', '年龄': 25}, {'姓名': '李四', '年龄': 30}]"
                )
            df = pd.DataFrame(data)
        else:
            # 使用 content 参数 (CSV字符串)
            if not isinstance(content, str):
                return (
                    f"错误: content 参数类型不正确。期望 str (CSV格式)，实际得到 {type(content).__name__}\n"
                    f"示例: '姓名,年龄\\n张三,25\\n李四,30'"
                )
            if not content.strip():
                return "错误: content 参数为空字符串，无法创建Excel文件"
            df = pd.read_csv(StringIO(content))
        
        # 检查 DataFrame 是否为空
        if df.empty:
            return "错误: 数据为空，无法创建Excel文件"
        
        df.to_excel(output_file, index=False)
        
        result = f"成功创建Excel文件: {output_file}\n"
        result += f"行数: {len(df)}\n"
        result += f"列数: {len(df.columns)}\n"
        result += f"列名: {list(df.columns)}"
        
        return result
    except Exception as e:
        return f"错误: 创建Excel文件失败 - {str(e)}"


def _edit_excel(parameters: Dict[str, Any]) -> str:
    """Edit Excel file"""
    file_path = parameters.get("file_path")
    if not file_path:
        return "错误: 缺少file_path参数"

    if not os.path.exists(file_path):
        return f"错误: 文件不存在 - {file_path}"

    try:
        import pandas as pd
        df = pd.read_excel(file_path)

        # 这里可以添加编辑逻辑
        result = f"成功读取Excel文件: {file_path}\n"
        result += f"行数: {len(df)}\n"
        result += f"列数: {len(df.columns)}"

        return result
    except Exception as e:
        return f"错误: 编辑Excel文件失败 - {str(e)}"


def _sort_excel(parameters: Dict[str, Any]) -> str:
    """Sort Excel file by specified column"""
    file_path = parameters.get("file_path")
    column = parameters.get("column")
    ascending = parameters.get("ascending", True)

    if not file_path:
        return "错误: 缺少file_path参数"
    if not column:
        return "错误: 缺少column参数"

    if not os.path.exists(file_path):
        return f"错误: 文件不存在 - {file_path}"

    try:
        import pandas as pd
        df = pd.read_excel(file_path)

        if column not in df.columns:
            return f"错误: 列 '{column}' 不存在。可用列: {list(df.columns)}"

        # 排序
        df_sorted = df.sort_values(by=column, ascending=ascending)

        # 生成输出文件名
        base_name = os.path.splitext(file_path)[0]
        extension = os.path.splitext(file_path)[1]
        output_file = f"{base_name}_按{column}排序{extension}"

        df_sorted.to_excel(output_file, index=False)

        result = f"成功排序Excel文件!\n\n"
        result += f"原文件: {file_path}\n"
        result += f"排序列: {column}\n"
        result += f"排序方式: {'升序' if ascending else '降序'}\n"
        result += f"输出文件: {output_file}\n"
        result += f"行数: {len(df_sorted)}\n"
        result += f"列数: {len(df_sorted.columns)}"

        return result
    except Exception as e:
        return f"错误: 排序Excel文件失败 - {str(e)}"
