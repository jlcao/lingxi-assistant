#!/usr/bin/env python3
"""记忆管理工具 - 继承 ToolBase"""

import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from lingxi.core.tools import ToolValidationError, ToolExecutionError
from lingxi.core.tools.Tool import ToolBase
from lingxi.core.tools.FileTool import FileTool
from lingxi.utils.config import get_config


MEMORY_TEMPLATE = """📖 个人记忆库

## 1. 用户记忆（user）- 长期个性化信息
说明：永久留存，用于定制化服务，格式：- [YYYY-MM-DD] 记忆内容 | 标签（可选）
### 1.1 生活偏好与习惯
### 1.2 基础个人信息（非敏感）
### 1.3 长期目标与需求
### 1.4 交互偏好与关键结论

## 2. 工作记忆（work）- 临时上下文信息
说明：短期留存，任务结束可清理，格式：- [YYYY-MM-DD] 临时内容 | 类型

## 3. 待办事项（todo）- 任务清单
说明：进度可追踪，格式：- [YYYY-MM-DD] 任务内容 | 截止时间 | 进度（未完成/进行中/已完成）
"""


MEMORY_CATEGORIES = {
    "user": {
        "name": "用户记忆",
        "pattern": r"- \[(\d{4}-\d{2}-\d{2})\] (.+?)(?: \| (.+))?$",
        "section_start": "## 1. 用户记忆",
        "section_end": "## 2. 工作记忆"
    },
    "work": {
        "name": "工作记忆",
        "pattern": r"- \[(\d{4}-\d{2}-\d{2})\] (.+?)(?: \| (.+))?$",
        "section_start": "## 2. 工作记忆",
        "section_end": "## 3. 待办事项"
    },
    "todo": {
        "name": "待办事项",
        "pattern": r"- \[(\d{4}-\d{2}-\d{2})\] (.+?) \| (.+?) \| (.+)$",
        "section_start": "## 3. 待办事项",
        "section_end": None
    }
}


SENSITIVE_PATTERNS = [
    (r'\b\d{6,16}\b', '数字ID/账号'),
    (r'\b\d{3,4}[-\s]?\d{3,4}[-\s]?\d{3,4}\b', '电话号码'),
    (r'\b\d{16,19}\b', '银行卡号'),
    (r'\b\d{15}|\d{18}\b', '身份证号'),
    (r'password[:\s=].+', '密码'),
    (r'passwd[:\s=].+', '密码'),
    (r'验证码[:\s=].+', '验证码'),
    (r'\b\d{4,6}\b', '验证码/邮编'),
]


class MemoryTool(ToolBase):
    """记忆管理工具类，支持记忆的保存、查找、更新、删除、统计"""

    def __init__(self):
        super().__init__("memory", "记忆管理工具，支持记忆保存、查找、更新、删除、统计")
        self.file_tool = FileTool()
        # 每次初始化时执行清理
        self._cleanup()

    def get_parameters_description(self) -> str:
        """获取工具参数描述"""
        return """- memory 工具调用示例
```json
{
  "operation_type": "add|search|update|delete|statistics|init|cleanup",
  "category": "user|work|todo",
  "content": "记忆内容",
  "tags": "标签1,标签2",
  "keyword": "搜索关键词",
  "limit": 10,
  "date": "2024-01-01",
  "line_number": 1
}
```"""

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """统一入口方法，根据operation_type分发到对应方法"""
        operation_type = parameters.get("operation_type", "").lower()

        operation_map = {
            "init": self._init,
            "add": self._add,
            "search": self._search,
            "update": self._update,
            "delete": self._delete,
            "statistics": self._statistics,
            "cleanup": self._manual_cleanup
        }

        if operation_type not in operation_map:
            raise ToolValidationError(
                f"不支持的操作类型: {operation_type}，支持的类型：init/add/search/update/delete/statistics/cleanup"
            )

        return operation_map[operation_type](parameters)

    def validate_parameters(self, parameters: Dict[str, Any]) -> Optional[str]:
        """验证参数"""
        operation_type = parameters.get("operation_type", "").lower()

        if operation_type == "init":
            return None

        if operation_type in ["add", "update", "delete"]:
            if not parameters.get("content") and operation_type != "delete":
                raise ToolValidationError("缺少必要参数: content")

        if operation_type == "search":
            if not parameters.get("keyword") and not parameters.get("category"):
                raise ToolValidationError("搜索需要提供 keyword 或 category 参数")

        if operation_type in ["update", "delete"]:
            if not parameters.get("line_number"):
                raise ToolValidationError("更新/删除需要提供 line_number 参数")

        return None

    def _get_memory_path(self) -> str:
        """获取记忆文件路径"""
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, ".lingxi", "memory", "MEMORY.md")

    def _ensure_directory_exists(self, file_path: str) -> None:
        """确保目录存在"""
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def _init(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """初始化记忆文件"""
        memory_path = self._get_memory_path()

        if os.path.exists(memory_path):
            return {
                "status": "S",
                "content": [],
                "error": "",
                "result_description": f"记忆文件已存在: {memory_path}"
            }

        try:
            self._ensure_directory_exists(memory_path)
            with open(memory_path, 'w', encoding='utf-8') as f:
                f.write(MEMORY_TEMPLATE)

            return {
                "status": "S",
                "content": [],
                "error": "",
                "result_description": f"记忆文件已创建: {memory_path}"
            }
        except Exception as e:
            raise ToolExecutionError(f"初始化记忆文件失败: {str(e)}")

    def _read_memory_file(self) -> str:
        """读取记忆文件内容"""
        memory_path = self._get_memory_path()

        if not os.path.exists(memory_path):
            self._init({})

        try:
            with open(memory_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ToolExecutionError(f"读取记忆文件失败: {str(e)}")

    def _write_memory_file(self, content: str) -> None:
        """写入记忆文件内容"""
        memory_path = self._get_memory_path()
        self._ensure_directory_exists(memory_path)

        try:
            with open(memory_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise ToolExecutionError(f"写入记忆文件失败: {str(e)}")

    def _detect_sensitive_content(self, content: str) -> Optional[str]:
        """检测敏感内容"""
        for pattern, description in SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return description
        return None

    def _parse_memory_entries(self, content: str, category: str) -> List[Dict[str, Any]]:
        """解析记忆条目"""
        entries = []
        category_info = MEMORY_CATEGORIES.get(category)
        if not category_info:
            return entries

        pattern = category_info["pattern"]
        section_start = category_info["section_start"]
        section_end = category_info["section_end"]

        in_section = False
        for line in content.split('\n'):
            if section_start in line:
                in_section = True
                continue
            if section_end and section_end in line:
                in_section = False
                continue
            if in_section and line.strip().startswith('- ['):
                match = re.match(pattern, line.strip())
                if match:
                    entry = {
                        "line_content": line.strip(),
                        "date": match.group(1)
                    }
                    if category == "todo":
                        entry["content"] = match.group(2)
                        entry["deadline"] = match.group(3)
                        entry["progress"] = match.group(4)
                    else:
                        entry["content"] = match.group(2)
                        if match.group(3):
                            entry["tags"] = match.group(3)
                    entries.append(entry)

        return entries

    def _find_entry_by_line_number(self, content: str, line_number: int) -> Optional[Dict[str, Any]]:
        """根据行号查找记忆条目"""
        lines = content.split('\n')
        if 0 < line_number <= len(lines):
            line = lines[line_number - 1]
            if line.strip().startswith('- ['):
                return {"line_number": line_number, "line_content": line.strip()}
        return None

    def _get_category_section(self, content: str, category: str) -> tuple:
        """获取分类的起始和结束行号"""
        category_info = MEMORY_CATEGORIES.get(category)
        if not category_info:
            return None, None

        lines = content.split('\n')
        start_line = None
        end_line = None

        for i, line in enumerate(lines):
            if category_info["section_start"] in line:
                start_line = i
            if start_line is not None and category_info["section_end"] in line:
                end_line = i
                break

        return start_line, end_line

    def _count_entries_in_section(self, content: str, category: str) -> int:
        """统计某个分类的记忆条目数量"""
        entries = self._parse_memory_entries(content, category)
        return len(entries)

    def _statistics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """统计记忆"""
        content = self._read_memory_file()

        user_count = self._count_entries_in_section(content, "user")
        work_count = self._count_entries_in_section(content, "work")
        todo_count = self._count_entries_in_section(content, "todo")
        total_count = user_count + work_count + todo_count

        result = {
            "status": "S",
            "content": [],
            "error": "",
            "result_description": f"记忆统计完成",
            "statistics": {
                "total": total_count,
                "user": user_count,
                "work": work_count,
                "todo": todo_count
            }
        }

        return result

    def _add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """新增记忆"""
        content = params.get("content", "")
        category = params.get("category", "user")
        tags = params.get("tags", "")
        deadline = params.get("deadline", "")
        progress = params.get("progress", "未完成")

        if category not in MEMORY_CATEGORIES:
            raise ToolValidationError(f"无效的分类: {category}，支持的分类：user/work/todo")

        sensitive = self._detect_sensitive_content(content)
        if sensitive:
            raise ToolValidationError(f"禁止存储敏感内容: {sensitive}")

        current_date = datetime.now().strftime("%Y-%m-%d")

        if category == "todo":
            if not deadline:
                raise ToolValidationError("待办事项需要提供截止时间(deadline)")
            new_entry = f"- [{current_date}] {content} | {deadline} | {progress}"
        else:
            if tags:
                new_entry = f"- [{current_date}] {content} | {tags}"
            else:
                new_entry = f"- [{current_date}] {content}"

        content_mem = self._read_memory_file()
        lines = content_mem.split('\n')

        start_line, end_line = self._get_category_section(content_mem, category)
        if start_line is None:
            raise ToolExecutionError(f"无法找到分类 {category} 的位置")

        insert_pos = end_line if end_line else len(lines)
        lines.insert(insert_pos, new_entry)

        self._write_memory_file('\n'.join(lines))

        return {
            "status": "S",
            "content": [],
            "error": "",
            "result_description": f"已添加{category}记忆: {new_entry}"
        }

    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索记忆"""
        keyword = params.get("keyword", "")
        category = params.get("category", "")
        limit = params.get("limit", 0)
        tags_filter = params.get("tags", "")

        content = self._read_memory_file()

        if category:
            categories_to_search = [category]
        else:
            categories_to_search = ["user", "work", "todo"]

        all_results = []

        for cat in categories_to_search:
            entries = self._parse_memory_entries(content, cat)
            for entry in entries:
                entry["category"] = cat
                entry["category_name"] = MEMORY_CATEGORIES[cat]["name"]

                if keyword and keyword.lower() not in entry["content"].lower():
                    continue

                if tags_filter and tags_filter.lower() not in entry.get("tags", "").lower():
                    continue

                all_results.append(entry)

        all_results.sort(key=lambda x: x["date"], reverse=True)

        if limit > 0:
            all_results = all_results[:limit]

        if not all_results:
            return {
                "status": "S",
                "content": [],
                "error": "",
                "result_description": "未找到相关记忆"
            }

        return {
            "status": "S",
            "content": all_results,
            "error": "",
            "result_description": f"找到 {len(all_results)} 条记忆"
        }

    def _update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """更新记忆"""
        line_number = params.get("line_number")
        new_content = params.get("content", "")

        if not line_number:
            raise ToolValidationError("更新需要提供 line_number 参数")

        memory_path = self._get_memory_path()
        content = self._read_memory_file()
        lines = content.split('\n')

        if line_number < 1 or line_number > len(lines):
            raise ToolValidationError(f"行号无效，有效范围: 1-{len(lines)}")

        old_line = lines[line_number - 1]
        if not old_line.strip().startswith('- ['):
            raise ToolValidationError(f"第 {line_number} 行不是记忆条目")

        sensitive = self._detect_sensitive_content(new_content)
        if sensitive:
            raise ToolValidationError(f"禁止存储敏感内容: {sensitive}")

        old_match = re.match(r"- \[(\d{4}-\d{2}-\d{2})\] (.+?)(?: \| (.+))?$", old_line.strip())
        if old_match:
            date = old_match.group(1)
            if '|' in old_line:
                parts = old_line.strip().split('|')
                if len(parts) == 3:
                    new_line = f"- [{date}] {new_content} | {parts[1].strip()} | {parts[2].strip()}"
                else:
                    new_line = f"- [{date}] {new_content} | {parts[1].strip()}"
            else:
                new_line = f"- [{date}] {new_content}"

            lines[line_number - 1] = new_line
            self._write_memory_file('\n'.join(lines))

            return {
                "status": "S",
                "content": [],
                "error": "",
                "result_description": f"已更新记忆: {new_line}"
            }
        else:
            raise ToolExecutionError(f"无法解析原记忆条目格式")

    def _delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除记忆"""
        line_number = params.get("line_number")

        if not line_number:
            raise ToolValidationError("删除需要提供 line_number 参数")

        content = self._read_memory_file()
        lines = content.split('\n')

        if line_number < 1 or line_number > len(lines):
            raise ToolValidationError(f"行号无效，有效范围: 1-{len(lines)}")

        line_to_delete = lines[line_number - 1]
        if not line_to_delete.strip().startswith('- ['):
            raise ToolValidationError(f"第 {line_number} 行不是记忆条目")

        del lines[line_number - 1]
        self._write_memory_file('\n'.join(lines))

        return {
            "status": "S",
            "content": [],
            "error": "",
            "result_description": f"已删除记忆: {line_to_delete.strip()}"
        }

    def _cleanup(self) -> None:
        """自动清理过期记忆"""
        config = get_config()
        cleanup_days = config.get("memory", {}).get("auto_cleanup_days", 30)
        enabled_categories = config.get("memory", {}).get("enabled_categories", ["work", "todo"])

        if not enabled_categories:
            return

        try:
            content = self._read_memory_file()
            lines = content.split('\n')
            lines_to_keep = []
            current_category = None
            in_category = False
            deleted_count = 0

            # 计算过期日期
            cutoff_date = datetime.now() - timedelta(days=cleanup_days)

            for line in lines:
                # 检测分类开始
                if line.strip().startswith("## 1. 用户记忆"):
                    current_category = "user"
                    in_category = True
                elif line.strip().startswith("## 2. 工作记忆"):
                    current_category = "work"
                    in_category = True
                elif line.strip().startswith("## 3. 待办事项"):
                    current_category = "todo"
                    in_category = True
                elif line.strip().startswith("##"):
                    # 其他分类开始
                    in_category = False

                # 检查是否是记忆条目且需要清理
                if in_category and line.strip().startswith('- [') and current_category in enabled_categories:
                    match = re.match(r"- \[(\d{4}-\d{2}-\d{2})\] (.+)", line.strip())
                    if match:
                        entry_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                        if entry_date >= cutoff_date:
                            lines_to_keep.append(line)
                        else:
                            deleted_count += 1
                else:
                    lines_to_keep.append(line)

            # 如果有变化，写入文件
            new_content = '\n'.join(lines_to_keep)
            if new_content != content:
                self._write_memory_file(new_content)
        except Exception as e:
            # 清理失败不影响其他功能
            self.logger.error(f"自动清理记忆失败: {str(e)}")

    def _manual_cleanup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """手动执行清理"""
        config = get_config()
        cleanup_days = config.get("memory", {}).get("auto_cleanup_days", 30)
        enabled_categories = config.get("memory", {}).get("enabled_categories", ["work", "todo"])

        if not enabled_categories:
            return {
                "status": "S",
                "content": [],
                "error": "",
                "result_description": "没有启用自动清理的分类"
            }

        try:
            content = self._read_memory_file()
            lines = content.split('\n')
            lines_to_keep = []
            current_category = None
            in_category = False
            deleted_count = 0

            # 计算过期日期
            cutoff_date = datetime.now() - timedelta(days=cleanup_days)

            for line in lines:
                # 检测分类开始
                if line.strip().startswith("## 1. 用户记忆"):
                    current_category = "user"
                    in_category = True
                elif line.strip().startswith("## 2. 工作记忆"):
                    current_category = "work"
                    in_category = True
                elif line.strip().startswith("## 3. 待办事项"):
                    current_category = "todo"
                    in_category = True
                elif line.strip().startswith("##"):
                    # 其他分类开始
                    in_category = False

                # 检查是否是记忆条目且需要清理
                if in_category and line.strip().startswith('- [') and current_category in enabled_categories:
                    match = re.match(r"- \[(\d{4}-\d{2}-\d{2})\] (.+)", line.strip())
                    if match:
                        entry_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                        if entry_date >= cutoff_date:
                            lines_to_keep.append(line)
                        else:
                            deleted_count += 1
                else:
                    lines_to_keep.append(line)

            # 如果有变化，写入文件
            new_content = '\n'.join(lines_to_keep)
            if new_content != content:
                self._write_memory_file(new_content)

            return {
                "status": "S",
                "content": [],
                "error": "",
                "result_description": f"已清理 {deleted_count} 条过期记忆（超过 {cleanup_days} 天）",
                "cleanup_details": {
                    "deleted_count": deleted_count,
                    "cleanup_days": cleanup_days,
                    "enabled_categories": enabled_categories
                }
            }
        except Exception as e:
            raise ToolExecutionError(f"清理记忆失败: {str(e)}")