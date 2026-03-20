import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 获取用户目录下的全局 .lingxi 目录
USER_HOME = Path.home()
GLOBAL_LINGXI_DIR = USER_HOME / ".lingxi"

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
        "lingxi_db": str(GLOBAL_LINGXI_DIR / "data" / "lingxi.db"),
        "skills_db": str(GLOBAL_LINGXI_DIR / "data" / "skills.db")
    },
    "logging": {
        "level": "INFO",
        "file": str(GLOBAL_LINGXI_DIR / "logs" / "lingxi.log"),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "session": {
        "timeout": 3600,
        "max_history": 100
    },
    "skills": {
        "registry_path": str(GLOBAL_LINGXI_DIR / "data" / "skills.db"),
        "builtin_skills": ["search", "calculator", "weather"],
        "builtin_skills_dir": "lingxi/skills/builtin",
        "user_skills_dir": str(GLOBAL_LINGXI_DIR / "skills")
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
    
    配置加载优先级（从高到低）：
    1. 环境变量
    2. 工作目录配置 (.lingxi/conf/config.yaml)
    3. 用户目录配置 (~/.lingxi/conf/config.yaml)
    4. 项目配置文件 (config.yaml)
    5. 默认配置 (DEFAULT_CONFIG)
    
    Args:
        config_path: 配置文件路径
        initial_config: 初始配置字典（可选）
        
    Returns:
        配置字典
    """
    global _config
    if _config:
        return _config
    
    # 使用默认配置作为基础
    config = DEFAULT_CONFIG.copy()
    
    # 1. 加载项目配置文件
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
    
    if config_path and os.path.exists(config_path):
        logger.info(f"加载项目配置文件：{config_path}")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                project_config = yaml.safe_load(f)
                if project_config:
                    config = _merge_configs(config, project_config)
        except Exception as e:
            logger.error(f"加载项目配置文件失败：{e}")
    else:
        logger.warning("未找到项目配置文件")
    
    # 2. 加载用户目录配置 (~/.lingxi/conf/config.yaml)
    user_config_path = GLOBAL_LINGXI_DIR / "conf" / "config.yaml"
    if user_config_path.exists():
        logger.info(f"加载用户目录配置：{user_config_path}")
        try:
            with open(user_config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    config = _merge_configs(config, user_config)
        except Exception as e:
            logger.error(f"加载用户目录配置失败：{e}")
    
    # 3. 加载工作目录配置 (.lingxi/conf/config.yaml)
    workspace_config_path = Path.cwd() / ".lingxi" / "conf" / "config.yaml"
    if workspace_config_path.exists():
        logger.info(f"加载工作目录配置：{workspace_config_path}")
        try:
            with open(workspace_config_path, "r", encoding="utf-8") as f:
                workspace_config = yaml.safe_load(f)
                if workspace_config:
                    config = _merge_configs(config, workspace_config)
        except Exception as e:
            logger.error(f"加载工作目录配置失败：{e}")
    
    # 4. 合并初始配置（如果提供）
    if initial_config:
        config = _merge_configs(config, initial_config)
    
    # 5. 加载环境变量覆盖
    config = _load_from_env(config)
    
    # 6. 验证配置
    config = _validate_config(config)
    
    # 7. 保存全局配置
    _config = config
    
    logger.debug(f"配置加载完成，LLM 提供商：{config.get('llm', {}).get('provider', 'unknown')}")
    
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
    # LLM 配置
    if os.environ.get("LLM_PROVIDER"):
        config["llm"]["provider"] = os.environ.get("LLM_PROVIDER")
    
    # 支持多种 API 密钥环境变量名，优先级从高到低
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        config["llm"]["api_key"] = api_key
    
    if os.environ.get("LLM_MODEL"):
        config["llm"]["model"] = os.environ.get("LLM_MODEL")
    
    # Web 配置
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
    
    # 验证 LLM 配置
    if not config["llm"]["api_key"] and config["llm"]["provider"] != "mock":
        logger.warning("未设置 LLM API 密钥，将使用模拟响应")
    
    # 验证引擎配置
    if config["engine"]["default"] not in ["react", "plan_react"]:
        logger.warning(f"未知引擎：{config['engine']['default']}，使用默认引擎：react")
        config["engine"]["default"] = "react"
    
    return config

def _ensure_directories(config: Dict[str, Any]):
    """确保必要的目录存在
    
    Args:
        config: 配置
    """
    from pathlib import Path
    import sys
    
    # 确保全局 .lingxi 目录及其子目录存在
    (GLOBAL_LINGXI_DIR / "conf").mkdir(parents=True, exist_ok=True)
    (GLOBAL_LINGXI_DIR / "data").mkdir(parents=True, exist_ok=True)
    (GLOBAL_LINGXI_DIR / "logs").mkdir(parents=True, exist_ok=True)
    (GLOBAL_LINGXI_DIR / "skills").mkdir(parents=True, exist_ok=True)
    
    # 确保数据库目录存在
    db_path = config.get("session", {}).get("db_path", "data/assistant.db")
    if not Path(db_path).is_absolute():
        db_path = str(GLOBAL_LINGXI_DIR / db_path)
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # 确保长期记忆数据库目录存在
    ltm_db_path = config.get("context_management", {}).get("long_term_memory", {}).get("db_path", "data/long_term_memory.db")
    if not Path(ltm_db_path).is_absolute():
        ltm_db_path = str(GLOBAL_LINGXI_DIR / ltm_db_path)
    ltm_db_dir = Path(ltm_db_path).parent
    ltm_db_dir.mkdir(parents=True, exist_ok=True)
    
    # 确保技能目录存在（用户目录）
    user_skills_dir = GLOBAL_LINGXI_DIR / "skills"
    user_skills_dir.mkdir(parents=True, exist_ok=True)
    
    # 设置内置技能目录路径（打包后指向资源目录）
    if getattr(sys, 'frozen', False):
        # 打包后的应用，技能目录在 resources/app.asar.unpacked/lingxi/skills/builtin
        try:
            bundled_skills_dir = Path(sys.executable).parent / "resources" / "app.asar.unpacked" / "lingxi" / "skills" / "builtin"
            if not bundled_skills_dir.exists():
                # 尝试另一个可能的路径
                bundled_skills_dir = Path(sys.executable).parent / "resources" / "app.asar" / "lingxi" / "skills" / "builtin"
            if bundled_skills_dir.exists():
                config.setdefault("skills", {})["builtin_skills_dir"] = str(bundled_skills_dir)
                logger.info(f"检测到打包环境，内置技能目录：{bundled_skills_dir}")
            else:
                logger.warning(f"打包环境中未找到内置技能目录：{bundled_skills_dir}")
        except Exception as e:
            logger.error(f"获取打包资源目录失败：{e}")
    else:
        # 开发环境，使用相对路径
        config.setdefault("skills", {})["builtin_skills_dir"] = "lingxi/skills/builtin"
    
    # 设置用户技能目录（始终使用用户目录）
    config.setdefault("skills", {})["user_skills_dir"] = str(user_skills_dir)

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
    print(f"系统名称：{config['system']['name']}")
    print(f"LLM 提供商：{config['llm']['provider']}")
    print(f"默认引擎：{config['engine']['default']}")
    print(f"Web 启用：{config['web']['enabled']}")
