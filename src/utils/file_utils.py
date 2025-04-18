import os
import logging

def ensure_app_directories():
    """
    确保应用所需的基本目录已创建
    """
    directories = [
        "logs",
        "templates"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.debug(f"Created directory: {directory}")
