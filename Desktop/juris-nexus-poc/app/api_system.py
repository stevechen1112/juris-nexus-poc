"""
系統 API 模組 - 處理系統狀態監控和配置相關的 API 端點
"""

import logging
import os
import json
import asyncio
import socket
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.model_clients import ClaudeClient, TaiwanLLMClient
from app.config import (
    USE_MOCK_MODE, 
    MOCK_CLAUDE, 
    MOCK_TAIWAN_LLM,
    CLAUDE_API_KEY,
    HUGGINGFACE_API_KEY,
    TAIWAN_LLM_API_URL
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# 緩存客戶端實例
_claude_client = None
_taiwan_llm_client = None

# 系統統計數據
system_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "average_response_time": 0,
    "active_users": 5,
    "last_updated": datetime.now().isoformat()
}

# 系統日誌
system_logs = []

def get_claude_client() -> ClaudeClient:
    """取得或創建Claude客戶端實例
    
    Returns:
        ClaudeClient: Claude客戶端實例
    """
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient(use_mock=MOCK_CLAUDE)
    return _claude_client

def get_taiwan_llm_client() -> TaiwanLLMClient:
    """取得或創建Taiwan LLM客戶端實例
    
    Returns:
        TaiwanLLMClient: Taiwan LLM客戶端實例
    """
    global _taiwan_llm_client
    if _taiwan_llm_client is None:
        _taiwan_llm_client = TaiwanLLMClient(use_mock=MOCK_TAIWAN_LLM)
    return _taiwan_llm_client

# 請求和響應模型
class MockModeConfigRequest(BaseModel):
    """模擬模式配置請求模型"""
    use_mock_mode: bool
    mock_claude: bool
    mock_taiwan_llm: bool

# API 端點
@router.get("/statistics")
async def get_statistics() -> Dict[str, Any]:
    """獲取系統統計信息
    
    Returns:
        Dict: 系統統計數據
    """
    try:
        # 計算成功率
        total = system_stats["successful_requests"] + system_stats["failed_requests"]
        success_rate = 0
        if total > 0:
            success_rate = round((system_stats["successful_requests"] / total) * 100, 2)
        
        return {
            "status": "success",
            "total_requests": system_stats["total_requests"],
            "successful_requests": system_stats["successful_requests"],
            "failed_requests": system_stats["failed_requests"],
            "average_response_time": system_stats["average_response_time"],
            "success_rate": success_rate,
            "active_users": system_stats["active_users"],
            "last_updated": system_stats["last_updated"]
        }
    except Exception as e:
        logger.error(f"獲取系統統計信息時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取系統統計信息時出錯: {str(e)}")

@router.get("/logs")
async def get_logs(limit: int = 20) -> Dict[str, Any]:
    """獲取系統日誌
    
    Args:
        limit: 返回的日誌條數限制
        
    Returns:
        Dict: 系統日誌
    """
    try:
        # 如果沒有日誌，嘗試從日誌文件中讀取
        if not system_logs:
            try:
                # 嘗試讀取日誌文件
                log_file = "app.log"
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        lines = f.readlines()[-100:]  # 只讀取最後100行
                        for line in lines:
                            parts = line.strip().split(" - ", 3)
                            if len(parts) >= 4:
                                timestamp, source, level, message = parts
                                system_logs.append({
                                    "timestamp": timestamp,
                                    "source": source,
                                    "level": level,
                                    "message": message
                                })
            except Exception as e:
                logger.warning(f"讀取日誌文件時出錯: {str(e)}")
                # 如果無法讀取日誌文件，添加一些模擬日誌
                system_logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": "app.api_system",
                    "level": "INFO",
                    "message": "系統啟動"
                })
        
        # 返回最新的日誌
        logs = sorted(system_logs, key=lambda x: x["timestamp"], reverse=True)[:limit]
        
        return {
            "status": "success",
            "logs": logs
        }
    except Exception as e:
        logger.error(f"獲取系統日誌時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取系統日誌時出錯: {str(e)}")

@router.post("/config/mock-mode")
async def update_mock_mode(request: MockModeConfigRequest) -> Dict[str, Any]:
    """更新模擬模式配置
    
    Args:
        request: 模擬模式配置請求
        
    Returns:
        Dict: 更新結果
    """
    try:
        # 更新環境變數
        env_file_path = ".env"
        env_vars = {}
        
        # 讀取現有環境變數
        if os.path.exists(env_file_path):
            with open(env_file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key] = value
        
        # 更新模擬模式配置
        env_vars["USE_MOCK_MODE"] = str(request.use_mock_mode).lower()
        env_vars["MOCK_CLAUDE"] = str(request.mock_claude).lower()
        env_vars["MOCK_TAIWAN_LLM"] = str(request.mock_taiwan_llm).lower()
        
        # 寫回環境變數文件
        with open(env_file_path, "w") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        # 更新全局變數
        global USE_MOCK_MODE, MOCK_CLAUDE, MOCK_TAIWAN_LLM
        USE_MOCK_MODE = request.use_mock_mode
        MOCK_CLAUDE = request.mock_claude
        MOCK_TAIWAN_LLM = request.mock_taiwan_llm
        
        # 重新初始化客戶端
        global _claude_client, _taiwan_llm_client
        _claude_client = None
        _taiwan_llm_client = None
        
        logger.info(f"更新模擬模式配置: USE_MOCK_MODE={USE_MOCK_MODE}, MOCK_CLAUDE={MOCK_CLAUDE}, MOCK_TAIWAN_LLM={MOCK_TAIWAN_LLM}")
        
        return {
            "status": "success",
            "message": "模擬模式配置已更新",
            "config": {
                "use_mock_mode": USE_MOCK_MODE,
                "mock_claude": MOCK_CLAUDE,
                "mock_taiwan_llm": MOCK_TAIWAN_LLM
            }
        }
    except Exception as e:
        logger.error(f"更新模擬模式配置時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新模擬模式配置時出錯: {str(e)}")

@router.get("/test/claude")
async def test_claude_api(
    claude_client: ClaudeClient = Depends(get_claude_client)
) -> Dict[str, Any]:
    """測試Claude API連接
    
    Args:
        claude_client: Claude客戶端依賴
        
    Returns:
        Dict: 測試結果
    """
    try:
        # 檢查是否使用模擬模式
        if claude_client.use_mock:
            return {
                "status": "mock",
                "message": "使用模擬模式",
                "model": "claude-3-5-sonnet-20241022 (模擬)"
            }
        
        # 簡單的測試提示
        prompt = "請用一句話介紹你自己。"
        
        # 測量響應時間
        start_time = datetime.now()
        response = await claude_client.generate(prompt)
        end_time = datetime.now()
        
        # 計算響應時間（毫秒）
        response_time = (end_time - start_time).total_seconds() * 1000
        
        # 更新統計數據
        system_stats["total_requests"] += 1
        system_stats["successful_requests"] += 1
        
        # 更新平均響應時間
        current_avg = system_stats["average_response_time"]
        total_requests = system_stats["successful_requests"]
        system_stats["average_response_time"] = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        system_stats["last_updated"] = datetime.now().isoformat()
        
        return {
            "status": "success",
            "message": "Claude API連接正常",
            "model": claude_client.model,
            "response_time": response_time,
            "response_preview": response[:100] + "..." if len(response) > 100 else response
        }
    except Exception as e:
        # 更新統計數據
        system_stats["total_requests"] += 1
        system_stats["failed_requests"] += 1
        system_stats["last_updated"] = datetime.now().isoformat()
        
        logger.error(f"測試Claude API時出錯: {str(e)}")
        return {
            "status": "error",
            "message": f"連接失敗: {str(e)}"
        }

@router.get("/test/taiwan-llm")
async def test_taiwan_llm_api(
    taiwan_llm_client: TaiwanLLMClient = Depends(get_taiwan_llm_client)
) -> Dict[str, Any]:
    """測試Taiwan LLM API連接
    
    Args:
        taiwan_llm_client: Taiwan LLM客戶端依賴
        
    Returns:
        Dict: 測試結果
    """
    try:
        # 檢查是否使用模擬模式
        if taiwan_llm_client.use_mock:
            return {
                "status": "mock",
                "message": "使用模擬模式",
                "model": "Llama-3-Taiwan-8B-Instruct (模擬)"
            }
        
        # 檢查網絡連接
        hostname = "api.huggingface.co"
        try:
            # 嘗試解析主機名
            socket.gethostbyname(hostname)
        except socket.gaierror:
            return {
                "status": "error",
                "message": f"無法解析主機名: {hostname}",
                "details": "DNS解析失敗，請檢查網絡連接"
            }
        
        # 簡單的測試提示
        prompt = "請用一句話介紹你自己。"
        
        # 測量響應時間
        start_time = datetime.now()
        response = await taiwan_llm_client.generate(prompt)
        end_time = datetime.now()
        
        # 計算響應時間（毫秒）
        response_time = (end_time - start_time).total_seconds() * 1000
        
        # 更新統計數據
        system_stats["total_requests"] += 1
        system_stats["successful_requests"] += 1
        
        # 更新平均響應時間
        current_avg = system_stats["average_response_time"]
        total_requests = system_stats["successful_requests"]
        system_stats["average_response_time"] = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        system_stats["last_updated"] = datetime.now().isoformat()
        
        return {
            "status": "success",
            "message": "Taiwan LLM API連接正常",
            "model": taiwan_llm_client.model,
            "response_time": response_time,
            "response_preview": response[:100] + "..." if len(response) > 100 else response
        }
    except Exception as e:
        # 更新統計數據
        system_stats["total_requests"] += 1
        system_stats["failed_requests"] += 1
        system_stats["last_updated"] = datetime.now().isoformat()
        
        logger.error(f"測試Taiwan LLM API時出錯: {str(e)}")
        return {
            "status": "error",
            "message": f"連接失敗: {str(e)}"
        }
