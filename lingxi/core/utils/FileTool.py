#!/usr/bin/env python3
"""文件操作工具 - 继承 ToolBase"""

import os
import re
from typing import Dict, List, Any, Optional
from lingxi.core.utils import ToolValidationError
from lingxi.core.utils.Tool import ToolBase


class FileTool(ToolBase):
    """文件操作工具类，支持read/write/delete/create四种操作，支持整文件/行级两种粒度，带文件大小安全限制"""
    
    def __init__(self):
        super().__init__("file", "用于对本地文本文件进行安全、可控的读取/删除/创建/改操作，支持整文件/行级两种粒度，带文件大小安全限制")
        self.default_max_size = "10MB"
        self.default_encoding = "utf-8"

    def get_parameters_description(self) -> str:
        """
        获取工具参数描述
        
        Returns:
            参数描述字符串  
        """

        str = """```json
{{"file_path": "文件路径，字符串，必填","encoding": "编码，默认 utf-8","operation_type": "read/write/delete/create/list，必填","operate_scope": "full/line，默认 full","line_params": {{"start_line": "开始行号，数字，行操作时生效","end_line": "结束行号，数字，行操作时生效","filter_rule": "读取时过滤关键词，字符串"}},"content": "操作内容，字符串，必填，create/write/insert 时必填"}}
```"""
        return "- execute 工具调用示例\n" + str
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一入口方法，根据operation_type分发到对应方法
        
        Args:
            parameters: 完整的操作参数
        
        Returns:
            操作结果字典
        """ 
        operation_type = parameters.get("operation_type", "").lower()
        
        operation_map = {
            "read": self._read,
            "write": self._write,
            "delete": self._delete,
            "create": self._create,
            "list": self._list
        }
        
        if operation_type not in operation_map:
            raise ToolValidationError(f"不支持的操作类型: {operation_type}，支持的类型：read/write/delete/create/list")
        
        return operation_map[operation_type](parameters)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Optional[str]:
        """
        验证参数
        
        Args:
            parameters: 工具参数
            
        Returns:
            错误信息（如果有），否则返回 None
        """
        operation_type = parameters.get("operation_type", "")
        
        # 检查必要参数
        if operation_type in ["read", "write", "delete"]:
            if not parameters.get("file_path"):
                raise ToolValidationError("缺少必要参数: file_path")
        elif operation_type == "create":
            if not parameters.get("file_path"):
                raise ToolValidationError("缺少必要参数: file_path")
        elif operation_type == "list":
            if not parameters.get("path"):
                raise ToolValidationError("缺少必要参数: path")
        
        # 检查文件大小限制（仅适用于文件操作）
        security_params = parameters.get("security_params", {})
        max_size_str = security_params.get("max_size", self.default_max_size)
        
        if parameters.get("file_path") and os.path.exists(parameters["file_path"]):
            file_size = os.path.getsize(parameters["file_path"])
            max_size_bytes = self._parse_max_size(max_size_str)
            
            if file_size > max_size_bytes:
                raise ToolValidationError(f"文件大小超过限制 {max_size_str}，实际大小：{file_size/1024/1024:.2f}MB")
        
        return True
    
    def _parse_max_size(self, max_size_str: str) -> int:
        """解析文件大小限制字符串为字节数"""
        try:
            max_size_num = float(re.findall(r'\d+', max_size_str)[0])
            unit = re.findall(r'[a-zA-Z]+', max_size_str)[0].upper()
            
            unit_map = {
                "KB": 1024,
                "MB": 1024 * 1024,
                "GB": 1024 * 1024 * 1024
            }
            return max_size_num * unit_map.get(unit, unit_map["MB"])
        except ValueError:
            raise ToolValidationError(f"无效的文件大小限制格式: {max_size_str}")  # 默认10MB
    
    def _read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件操作"""
        file_path = params.get("file_path", "")
        result = {"status": "F", "content": [], "error": "", "result_description": f"读取文件: {file_path}"}
        encoding = params.get("encoding", self.default_encoding)
        operate_scope = params.get("operate_scope", "full").lower()
        line_params = params.get("line_params", {})
        security_params = params.get("security_params", {})
        max_size_str = security_params.get("max_size", self.default_max_size)
        
        # 前置校验
        self._validatevalidate_file_exists(file_path)
        self._validate_file_size(file_path, max_size_str)
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                all_lines = [line.rstrip('\n') for line in f.readlines()]
            
            if operate_scope == "full":
                for idx, line in enumerate(all_lines, 1):
                    result["content"].append({"line": str(idx), "str": line})
                result["status"] = "S"
            elif operate_scope == "line":
                start_line = line_params.get("start_line", 1)
                end_line = line_params.get("end_line", len(all_lines))
                filter_rule = line_params.get("filter_rule", "")
                
                result["error"] = self._validate_line_range(start_line, end_line, len(all_lines))
                if result["error"]:
                    return result
                content = ""
                line_num = 0
                for idx in range(start_line - 1, end_line):
                    line_num = idx + 1
                    line_content = all_lines[idx]
                    
                    if filter_rule and filter_rule not in line_content:
                        continue
                    content += f"{line_num}:\t{line_content}\n"
                
                return f"已读取文件:{file_path} {line_num}行\n内容:\n{content}"
        except Exception as e:
            raise ToolExecutionError(f"读取异常: {str(e)}")
        
    
    def _write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件操作"""
        file_path = params.get("file_path", "")
        result = {"status": "F", "content": [], "error": "", "result_description": f"写入文件: {file_path}"}
        
        
        encoding = params.get("encoding", self.default_encoding)
        operate_scope = params.get("operate_scope", "full").lower()
        line_params = params.get("line_params", {})
        content_params = params.get("content_params", {})
        security_params = params.get("security_params", {})
        max_size_str = security_params.get("max_size", self.default_max_size)
        
        # 前置校验
        self._validate_file_exists(file_path)
        self._validate_file_size(file_path, max_size_str)
        
        try:
            if operate_scope == "full":
                # 支持简单的 content 参数或 content_params.new_content
                new_content = params.get("content") or content_params.get("new_content", "")
                append_content = content_params.get("append_content", "")
                content = new_content
                
                if append_content:
                    content += "\n" + append_content if content else append_content
                
                dir_path = os.path.dirname(file_path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)
                
                lines = content.split('\n')
                for idx, line in enumerate(lines, 1):
                    result["content"].append({"line": str(idx), "str": line})
                
                return f"已写入文件:{file_path} {len(lines)}行"
            elif operate_scope == "line":
                start_line = line_params.get("start_line", 1)
                end_line = line_params.get("end_line", start_line)
                # 支持直接使用 content 参数或 content_params.insert_content
                insert_content = params.get("content") or content_params.get("insert_content", "")
                
                with open(file_path, 'r', encoding=encoding) as f:
                    all_lines = [line.rstrip('\n') + '\n' for line in f.readlines()]
                
                total_lines = len(all_lines)
                if start_line < 1 or end_line > total_lines + 1 or start_line > end_line:
                    raise ToolValidationError(f"行号范围无效，文件总行数：{total_lines}，请求范围：{start_line}-{end_line}")
                
                # 分割内容并过滤掉末尾的空行（避免 split 产生多余空行）
                content_lines = insert_content.split('\n')
                if content_lines and content_lines[-1] == '':
                    content_lines = content_lines[:-1]
                
                insert_lines = [line + '\n' for line in content_lines]
                del all_lines[start_line-1:end_line]
                for idx, line in enumerate(insert_lines):
                    all_lines.insert(start_line-1 + idx, line)
                
                with open(file_path, 'w', encoding=encoding) as f:
                    f.writelines(all_lines)
                
                content = ""
                line_num = 0
                for idx in range(start_line-1, start_line-1 + len(insert_lines)):
                    if idx < len(all_lines):
                        line_content = all_lines[idx].rstrip('\n')
                        content += f"{line_num}:\t{line_content}\n"
                
                return f"已写入文件:{file_path} {line_num}行 {start_line}-{end_line}\n内容:\n{content}"
        except Exception as e:
            raise ToolExecutionError(f"写入异常: {str(e)}")
    
    
    def _delete(self, params: Dict[str, Any]) -> str:
        """删除文件/行操作"""
        file_path = params.get("file_path", "")
        result = {"status": "F", "content": [], "error": "", "result_description": f"删除文件: {file_path}"}
        
        
        encoding = params.get("encoding", self.default_encoding)
        operate_scope = params.get("operate_scope", "full").lower()
        line_params = params.get("line_params", {})
        security_params = params.get("security_params", {})
        max_size_str = security_params.get("max_size", self.default_max_size)
        
        # 前置校验
        result["error"] = self._validate_file_exists(file_path)
        if result["error"]:
            return result
        
        try:
            if operate_scope == "full":
                os.remove(file_path)
                result["content"] = [{"line": "0", "str": "文件已删除"}]
                result["status"] = "S"
                result["result_description"] = f"文件已删除: {file_path}"
            elif operate_scope == "line":
                start_line = line_params.get("start_line", 1)
                end_line = line_params.get("end_line", start_line)
                
                with open(file_path, 'r', encoding=encoding) as f:
                    all_lines = [line.rstrip('\n') + '\n' for line in f.readlines()]
                
                self._validate_line_range(start_line, end_line, len(all_lines))
                
                deleted_content = []
                for idx in range(start_line - 1, end_line):
                    deleted_content.append({
                        "line": str(idx+1),
                        "str": all_lines[idx].rstrip('\n')
                    })
                
                del all_lines[start_line-1:end_line]
                
                with open(file_path, 'w', encoding=encoding) as f:
                    f.writelines(all_lines)
                
                return f"已删除{file_path}文件的行 {start_line}-{end_line}"
        except Exception as e:
            raise ToolExecutionError(f"删除异常: {str(e)}")
        
    
    def _create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建文件操作"""
        file_path = params.get("file_path", "")
        result = {"status": "F", "content": [], "error": "", "result_description": f"创建文件: {file_path}"}
        
        
        encoding = params.get("encoding", self.default_encoding)
        content_params = params.get("content_params", {})
        security_params = params.get("security_params", {})
        max_size_str = security_params.get("max_size", self.default_max_size)
        
        # 前置校验
        if os.path.exists(file_path):
            result["error"] = f"文件已存在，创建失败: {file_path}"
            return result
        
        try:
            # 支持简单的 content 参数或 content_params.new_content
            new_content = params.get("content") or content_params.get("new_content", "")
            append_content = content_params.get("append_content", "")
            content = new_content
            
            if append_content:
                content += "\n" + append_content if content else append_content
            
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            lines = content.split('\n')
            for idx, line in enumerate(lines, 1):
                result["content"].append({"line": str(idx), "str": line})
            
            return f"文件已创建: {file_path}"
        except Exception as e:
            raise ToolExecutionError(f"创建异常: {str(e)}")
    
    def _list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录内容操作"""
        directory_path = params.get("path", "")
        result = {"status": "F", "content": [], "error": "", "result_description": f"列出目录: {directory_path}"}
        
        # 前置校验
        if not directory_path:
            result["error"] = "缺少必要参数: path"
            return result
        
        if not os.path.exists(directory_path):
            result["error"] = f"目录不存在: {directory_path}"
            return result
        
        if not os.path.isdir(directory_path):
            result["error"] = f"路径不是目录: {directory_path}"
            return result
        
        try:
            # 列出目录内容
            items = []
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                item_type = "directory" if os.path.isdir(item_path) else "file"
                items.append({
                    "name": item,
                    "type": item_type,
                    "path": item_path
                })
            
            # 按类型和名称排序
            items.sort(key=lambda x: (x["type"], x["name"]))
            
            # 转换为符合格式的内容
            for idx, item in enumerate(items, 1):
                result["content"].append({
                    "line": str(idx),
                    "str": f"[{item['type']}] {item['name']}"
                })
            
            result["status"] = "S"
        except Exception as e:
            result["error"] = f"列出目录异常: {str(e)}"
        
        return result
    
    def _validate_file_exists(self, file_path: str) -> str:
        """检查文件是否存在，返回错误信息（空表示无错误）"""
        if not os.path.exists(file_path):
            raise ToolValidationError(f"文件不存在: {file_path}")
        if os.path.isdir(file_path):
            raise ToolValidationError(f"路径是目录而非文件: {file_path}")
        return ""
    
    def _validate_file_size(self, file_path: str, max_size_str: str) -> str:
        """检查文件大小是否超限，返回错误信息（空表示无错误）"""
        max_size_bytes = self._parse_max_size(max_size_str)
        file_size = os.path.getsize(file_path)
        
        if file_size > max_size_bytes:
            raise ToolValidationError(f"文件大小超过限制 {max_size_str}，实际大小：{file_size/1024/1024:.2f}MB")
        return ""
    
    def _validate_line_range(self, start_line: int, end_line: int, total_lines: int) -> str:
        """验证行号范围是否合法，返回错误信息（空表示无错误）"""
        if start_line < 1:
            raise ToolValidationError(f"开始行号不能小于1，当前值：{start_line}")
        if end_line > total_lines:
            raise ToolValidationError(f"结束行号超过文件总行数，总行数：{total_lines}，当前值：{end_line}")
        if start_line > end_line:
            raise ToolValidationError(f"开始行号不能大于结束行号，范围：{start_line}-{end_line}")
        return ""
