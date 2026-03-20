import json
import re
import ast
import operator
from typing import Dict, List, Optional, Any


def parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
    """解析LLM响应

    Args:
        response: LLM响应

    Returns:
        解析后的字典
    """
    # 移除Markdown代码块标记
    response = response.strip()
    if response.startswith('```'):
        # 匹配 ```json 或 ```python 等标记
        response = re.sub(r'^```[a-zA-Z]*\n', '', response)
        response = re.sub(r'\n```$', '', response)
        response = response.strip()
    
    # 移除可能的单引号或双引号包围
    # 处理可能的转义引号
    import re
    # 移除字符串两端的引号（包括可能的转义）
    response = re.sub(r'^[\"\']+(.*?)[\"\']+$', r'\1', response)
    
    # 优先尝试直接 JSON 解析（更可靠）
    try:
        result = json.loads(response)
        # 验证必需字段
        if all(key in result for key in ["thought", "action", "action_input"]):
            # action_input 可以是对象或字符串
            action_input = result["action_input"]
            content = action_input if result["action"] == "finish" else ""
            return {
                "thought": result["thought"],
                "action": result["action"],
                "description": result.get("description", ""),
                "action_input": action_input,
                "content": content
            }
    except (json.JSONDecodeError, KeyError, AttributeError, IndexError) as e:
        # 直接解析失败，尝试寻找 JSON 对象
        try:
            # 查找 JSON 对象（支持嵌套和换行）
            start_idx = response.find('{')
            if start_idx != -1:
                # 从第一个 { 开始，寻找匹配的 }
                brace_count = 0
                in_string = False
                escape_next = False
                for i in range(start_idx, len(response)):
                    char = response[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"':
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = response[start_idx:i+1]
                                result = json.loads(json_str)
                                
                                # 验证必需字段
                                if all(key in result for key in ["thought", "action", "action_input"]):
                                    # action_input 可以是对象或字符串
                                    action_input = result["action_input"]
                                    content = action_input if result["action"] == "finish" else ""
                                    return {
                                        "thought": result["thought"],
                                        "action": result["action"],
                                        "description": result.get("description", ""),
                                        "action_input": action_input,
                                        "content": content
                                    }
                                break
        except (json.JSONDecodeError, KeyError, AttributeError, IndexError) as e:
            pass
    
    # 回退到文本格式解析（支持中英文冒号）
    thought_match = re.search(r'思考[：:]\s*(.*?)\n行动[：:]', response, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else ""

    action_match = re.search(r'行动[：:]\s*(\w+)(?:\s*-\s*|\()(.*?)(?:\)|$)', response, re.DOTALL)
    if action_match:
        action = action_match.group(1).strip()
        action_input = action_match.group(2).strip()
        action_input = action_input.strip(' \t\n\r')
    else:
        action = ""
        action_input = ""

    if not thought or not action:
        return None

    return {
        "thought": thought,
        "action": action,
        "action_input": action_input,
        "content": action_input if action == "finish" else ""
    }


def parse_action_parameters(action_input: str) -> Dict[str, Any]:
    """解析行动参数

    Args:
        action_input: 行动输入字符串

    Returns:
        参数字典
    """
    parameters = {}

    if not action_input:
        return parameters

    # 使用更健壮的正则表达式，支持多行内容
    # 匹配 key="value" 格式，其中 value 可以包含换行符和转义字符
    pattern = r'(\w+)="((?:[\s\S]|\\")*?)"'
    matches = re.findall(pattern, action_input)

    for match in matches:
        key = match[0]
        value = match[1]
        parameters[key] = value

    return parameters


def process_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """处理参数，转换转义字符

    Args:
        parameters: 原始参数字典

    Returns:
        处理后的参数字典
    """
    processed = {}
    for key, value in parameters.items():
        if isinstance(value, str):
            value = value.replace('\\n', '\n')
            value = value.replace('\\t', '\t')
            value = value.replace('\\r', '\r')
            value = value.replace('\\"', '"')
            value = value.replace('\\\\', '\\')
        processed[key] = value
    return processed


def calculate_expression(expression: str) -> str:
    """计算表达式

    Args:
        expression: 数学表达式

    Returns:
        计算结果
    """
    try:
        allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
        }

        def _eval(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            elif isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                if type(node.op) in allowed_operators:
                    return allowed_operators[type(node.op)](left, right)
                else:
                    raise ValueError(f"不支持的操作: {type(node.op).__name__}")
            else:
                raise ValueError(f"不支持的表达式: {type(node).__name__}")

        tree = ast.parse(expression, mode='eval')
        result = _eval(tree.body)
        return f"计算结果: {result}"

    except Exception as e:
        return f"计算错误: {str(e)}"


def parse_plan(plan: str, max_steps: int = 8) -> List[str]:
    """解析任务规划

    Args:
        plan: 任务规划文本
        max_steps: 最大步骤数

    Returns:
        规划步骤列表
    """
    # 添加调试日志
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"解析计划，原始内容: {repr(plan[:500])}")
    
    # 首先尝试解析JSON格式
    try:
        import json
        plan = plan.strip()
        
        # 移除Markdown代码块标记
        if plan.startswith('```'):
            # 匹配 ```json 或 ```python 等标记
            plan = re.sub(r'^```[a-zA-Z]*\n', '', plan)
            plan = re.sub(r'\n```$', '', plan)
            plan = plan.strip()
        
        if plan.startswith('[') or plan.startswith('{'):
            plan_data = json.loads(plan)
            if isinstance(plan_data, list):
                steps = []
                for item in plan_data:
                    if isinstance(item, dict):
                        if 'description' in item:
                            steps.append(item['description'])
                        elif 'step' in item:
                            steps.append(item.get('description', f"步骤 {item['step']}"))
                if steps:
                    logger.debug(f"JSON解析成功，提取到{len(steps)}个步骤")
                    return steps[:max_steps]
    except json.JSONDecodeError as e:
        logger.debug(f"JSON解析失败: {e}")
        pass
    
    # 如果JSON解析失败，尝试文本格式解析
    steps = []
    lines = plan.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配多种格式的步骤行：
        # 1. 纯数字格式: "1. 步骤内容"
        # 2. Markdown格式: "1. **步骤1：步骤内容**"
        # 3. 带括号格式: "1) 步骤内容"
        # 4. 其他变体格式
        if re.match(r'^\d+[.)\s]', line):
            # 提取数字后面的内容
            step_match = re.search(r'^\d+[.)\s]+(.*)', line)
            if step_match:
                step_content = step_match.group(1).strip()
                # 去除Markdown粗体格式 **内容**
                step_content = re.sub(r'\*\*(.*?)\*\*', r'\1', step_content)
                # 去除可能的步骤编号前缀，如 "步骤1：" 或 "步骤1: "
                step_content = re.sub(r'^步骤\d+[:：]\s*', '', step_content).strip()
                # 去除可能的标题格式，如 "### 标题"
                step_content = re.sub(r'^#+\s*', '', step_content).strip()
                
                if step_content:
                    steps.append(step_content)

    if not steps:
        # 尝试备用解析方案：提取所有以数字开头的行
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r'^\d+[.)\s]', line):
                step_match = re.search(r'^\d+[.)\s]+(.*)', line)
                if step_match:
                    step_content = step_match.group(1).strip()
                    # 去除Markdown格式
                    step_content = re.sub(r'\*\*(.*?)\*\*', r'\1', step_content)
                    step_content = re.sub(r'^#+\s*', '', step_content).strip()
                    
                    if step_content:
                        steps.append(step_content)
    
    logger.debug(f"文本解析结果，提取到{len(steps)}个步骤: {steps}")

    if not steps:
        logger.error(f"任务规划为空，原始内容: {repr(plan)}")
        raise ValueError("任务规划为空")

    return steps[:max_steps]


def parse_json_with_escape_cleaning(response: str, logger=None) -> Optional[Dict[str, Any]]:
    """解析 JSON 响应，支持清理无效的转义序列
    
    Args:
        response: 包含 JSON 的响应文本
        logger: 可选的日志记录器
        
    Returns:
        解析后的字典，如果解析失败则返回 None
    """
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    
    import json
    import re
    
    # 尝试提取 JSON，使用多种方法提高容错性
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as json_error:
            # 尝试清理无效的转义序列
            logger.warning(f"JSON 解析失败，尝试清理转义字符：{json_error}")
            try:
                # 清理路径中的无效转义序列（如 \\w, \\工 等）
                # 只保留有效的 JSON 转义序列
                cleaned_json = re.sub(r'\\([^\\nrtbf"\'\\])', r'\\\\\1', json_str)
                # 再次尝试解析
                return json.loads(cleaned_json)
            except Exception as cleanup_error:
                logger.error(f"JSON 清理后仍然失败：{cleanup_error}")
                # 如果清理后仍然失败，尝试更激进的清理
                try:
                    # 移除所有无效的转义序列
                    aggressive_cleaned = re.sub(r'\\[^\\nrtbf"\'\\]', r'\\\\', json_str)
                    return json.loads(aggressive_cleaned)
                except Exception as aggressive_error:
                    logger.error(f"激进清理后仍然失败：{aggressive_error}")
                    raise json_error
    
    return None
