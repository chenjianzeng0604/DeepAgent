import os
import logging
from datetime import datetime


def setup_logging(app_name="app", log_level=logging.INFO):
    """
    设置统一的日志配置
    
    Args:
        app_name: 应用名称，用于日志文件命名
        log_level: 日志级别
        
    Returns:
        logger: 配置好的日志器
    """
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join("logs", f"{app_name}.log"), encoding="utf-8")
        ]
    )
    return logging.getLogger(app_name)
