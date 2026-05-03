"""
M1模块配置文件

包含大模型相关配置和其他参数
"""

import os

class Config:
    # 大模型配置
    LLM_ENABLED = True
    LLM_API_KEY = "1aa5046636ef4adcb98c37c39f1e973a.2BBvQ2bAaDMJDOZ8"
    LLM_MODEL = "GLM-5.1"
    LLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    # 大模型参数
    LLM_TEMPERATURE = 0.7
    LLM_MAX_TOKENS = 2000
    
    # 降级策略
    FALLBACK_TO_LOCAL = True
    
    # 航路点数量限制
    MAX_WAYPOINTS = 10
    MIN_WAYPOINTS = 3
    
    # 日志配置
    LOG_LEVEL = "INFO"
    
    @classmethod
    def load_from_env(cls):
        """从环境变量加载配置"""
        if os.environ.get("LLM_ENABLED"):
            cls.LLM_ENABLED = os.environ["LLM_ENABLED"].lower() == "true"
        if os.environ.get("LLM_API_KEY"):
            cls.LLM_API_KEY = os.environ["LLM_API_KEY"]
        if os.environ.get("LLM_MODEL"):
            cls.LLM_MODEL = os.environ["LLM_MODEL"]
        if os.environ.get("LLM_API_URL"):
            cls.LLM_API_URL = os.environ["LLM_API_URL"]
        if os.environ.get("LLM_TEMPERATURE"):
            cls.LLM_TEMPERATURE = float(os.environ["LLM_TEMPERATURE"])
        if os.environ.get("LLM_MAX_TOKENS"):
            cls.LLM_MAX_TOKENS = int(os.environ["LLM_MAX_TOKENS"])