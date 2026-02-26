import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "system": {
        "name": "灵犀",
        "version": "0.1.0",
        "description": "智能任务处理系统"
    },
    "llm": {
        "provider": "openai",
        "api_key": "",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2048,
        "timeout": 30
    },
    "database": {
        "lingxi_db": "data/lingxi.db",
        "skills_db": "data/skills.db"
    },
    "logging": {
        "level": "INFO",
        "file": "logs/lingxi.log",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "session": {
        "timeout": 3600,
        "max_history": 100
    },
    "skills": {
        "registry_path": "data/skills.db",
        "builtin_skills": ["search", "calculator", "weather"]
    },
    "web": {
        "enabled": False,
        "host": "localhost",
        "port": 5000,
        "debug": False
    },
    "engine": {
        "default": "react",
        "max_steps": 10,
        "timeout": 60
    }
}

# 全局配置实例
_config = None

def load_config(config_path: str = None, initial_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """加载配置
    
    Args:
        config_path: 配置文件路径
        initial_config: 初始配置字典（可选）
        
    Returns:
        配置字典
    """
    global _config
    if _config:
        return _config
    
    # 确定配置文件路径
    if not config_path:
        # 尝试从默认位置加载
        default_paths = [
            "config.yaml",
            "lingxi/config.yaml",
            "../config.yaml"
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    # 加载配置文件
    if initial_config:
        # 使用默认配置作为基础，然后合并初始配置
        config = DEFAULT_CONFIG.copy()
        config = _merge_configs(config, initial_config)
    else:
        # 使用默认配置作为基础
        config = DEFAULT_CONFIG.copy()
    
    if config_path and os.path.exists(config_path):
        logger.info(f"加载配置文件: {config_path}")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # 合并配置
                    config = _merge_configs(config, user_config)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    else:
        logger.warning("未找到配置文件，使用默认配置")
    
    # 加载环境变量覆盖
    config = _load_from_env(config)
    
    # 验证配置
    config = _validate_config(config)
    
    # 保存全局配置
    _config = config
    
    return config

def _merge_configs(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """合并配置
    
    Args:
        default: 默认配置
        user: 用户配置
        
    Returns:
        合并后的配置
    """
    merged = default.copy()
    
    for key, value in user.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_configs(merged[key], value)
        else:
            merged[key] = value
    
    return merged

def _load_from_env(config: Dict[str, Any]) -> Dict[str, Any]:
    """从环境变量加载配置
    
    Args:
        config: 当前配置
        
    Returns:
        加载环境变量后的配置
    """
    # LLM配置
    if os.environ.get("LLM_PROVIDER"):
        config["llm"]["provider"] = os.environ.get("LLM_PROVIDER")
    
    # 支持多种API密钥环境变量名，优先级从高到低
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        config["llm"]["api_key"] = api_key
    
    if os.environ.get("LLM_MODEL"):
        config["llm"]["model"] = os.environ.get("LLM_MODEL")
    
    # Web配置
    if os.environ.get("WEB_ENABLED"):
        config["web"]["enabled"] = os.environ.get("WEB_ENABLED").lower() == "true"
    
    if os.environ.get("WEB_HOST"):
        config["web"]["host"] = os.environ.get("WEB_HOST")
    
    if os.environ.get("WEB_PORT"):
        try:
            config["web"]["port"] = int(os.environ.get("WEB_PORT"))
        except ValueError:
            pass
    
    # 日志配置
    if os.environ.get("LOG_LEVEL"):
        config["logging"]["level"] = os.environ.get("LOG_LEVEL")
    
    return config

def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证配置
    
    Args:
        config: 当前配置
        
    Returns:
        验证后的配置
    """
    # 确保必要的目录存在
    _ensure_directories(config)
    
    # 验证LLM配置
    if not config["llm"]["api_key"] and config["llm"]["provider"] != "mock":
        logger.warning("未设置LLM API密钥，将使用模拟响应")
    
    # 验证引擎配置
    if config["engine"]["default"] not in ["react", "plan_react"]:
        logger.warning(f"未知引擎: {config['engine']['default']}，使用默认引擎: react")
        config["engine"]["default"] = "react"
    
    return config

def _ensure_directories(config: Dict[str, Any]):
    """确保必要的目录存在
    
    Args:
        config: 配置
    """
    # 创建data目录
    data_dir = os.path.dirname(config["database"]["lingxi_db"])
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    # 创建logs目录
    log_dir = os.path.dirname(config["logging"]["file"])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

def get_config() -> Dict[str, Any]:
    """获取配置
    
    Returns:
        配置字典
    """
    global _config
    if not _config:
        _config = load_config()
    return _config

def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值
    
    Args:
        key: 配置键，支持点号分隔，如 "llm.model"
        default: 默认值
        
    Returns:
        配置值
    """
    config = get_config()
    
    # 解析键
    keys = key.split(".")
    value = config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value

def reload_config() -> Dict[str, Any]:
    """重新加载配置
    
    Returns:
        重新加载后的配置
    """
    global _config
    _config = None
    return load_config()

def set_config(config: Dict[str, Any]):
    """设置配置
    
    Args:
        config: 配置字典
    """
    global _config
    _config = config

if __name__ == "__main__":
    # 测试配置加载
    config = load_config()
    print("配置加载成功:")
    print(f"系统名称: {config['system']['name']}")
    print(f"LLM提供商: {config['llm']['provider']}")
    print(f"默认引擎: {config['engine']['default']}")
    print(f"Web启用: {config['web']['enabled']}")