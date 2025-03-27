import os
from dotenv import load_dotenv
import logging

# 加載環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# API配置
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
TAIWAN_LLM_API_KEY = os.getenv("TAIWAN_LLM_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
TAIWAN_LLM_API_URL = os.getenv("TAIWAN_LLM_API_URL", "https://api.huggingface.co/models/yentinglin/Llama-3-Taiwan-8B-Instruct")

# 模擬模式配置
USE_MOCK_MODE = os.getenv("USE_MOCK_MODE", "true").lower() == "true"  # 默認啟用模擬模式
MOCK_CLAUDE = os.getenv("MOCK_CLAUDE", "false").lower() == "true"  # 默認不模擬 Claude API
MOCK_TAIWAN_LLM = os.getenv("MOCK_TAIWAN_LLM", "true").lower() == "true"  # 默認模擬 Taiwan LLM API

# 應用配置
TEMP_UPLOAD_DIR = os.getenv("TEMP_UPLOAD_DIR", "./app/data/temp")
LEARNING_DATA_DIR = os.getenv("LEARNING_DATA_DIR", "./app/data/learning")

# 確保目錄存在
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
os.makedirs(LEARNING_DATA_DIR, exist_ok=True)

# AI模型配置
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"  # 更新為最新的模型版本
TAIWAN_LLM_MODEL = "yentinglin/Llama-3-Taiwan-8B-Instruct"  # 更新為8B版本

# 提示配置
MAX_TOKENS_CLAUDE = 4096
MAX_TOKENS_TAIWAN_LLM = 4096

# 應用配置
APP_NAME = "JURIS NEXUS"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "基於雙層AI架構的法律助手系統概念驗證"
