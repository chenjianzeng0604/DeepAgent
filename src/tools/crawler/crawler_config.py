"""
爬虫配置管理器 - 集合名称识别模块
"""
import logging

logger = logging.getLogger(__name__)

# 场景集合映射
SCENARIO_COLLECTIONS = {
    # 技术类别
    "tech": "deepresearch_tech",
    # 医学类别
    "med": "deepresearch_med",
    # 金融类别
    "fin": "deepresearch_fin",
    # 教育类别
    "edu": "deepresearch_edu",
    # 招投标类别
    "bid": "deepresearch_bid"
}

class CrawlerConfigManager:
    """简化后的爬虫配置管理器，仅保留集合名称识别功能"""
    
    def __init__(self):
        pass
    
    def get_collection_name(self, scenario=None):
        """获取指定场景对应的Milvus集合名称
        
        Args:
            scenario: 场景名称，为None时使用默认场景
            
        Returns:
            str: Milvus集合名称
        """
        if not scenario:
            logger.warning("场景名称为空")
            return None
        scenario_lower = scenario.lower()
        if scenario_lower in SCENARIO_COLLECTIONS:
            return SCENARIO_COLLECTIONS[scenario_lower]
        return None

crawler_config_manager = CrawlerConfigManager()
