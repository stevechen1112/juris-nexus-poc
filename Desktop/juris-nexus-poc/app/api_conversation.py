"""
對話 API 模組 - 處理法律諮詢對話相關的 API 端點
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.model_clients import ClaudeClient, TaiwanLLMClient
from app.legal_tasks.consultation_service import LegalConsultationService
from app.config import USE_MOCK_MODE, MOCK_CLAUDE, MOCK_TAIWAN_LLM

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversation")

# 緩存服務實例
_consultation_service = None
_claude_client = None
_taiwan_llm_client = None

# 模擬數據存儲
conversations = {}
messages = {}

def get_consultation_service() -> LegalConsultationService:
    """取得或創建法律諮詢服務實例
    
    Returns:
        LegalConsultationService: 法律諮詢服務實例
    """
    global _consultation_service, _claude_client, _taiwan_llm_client
    if _consultation_service is None:
        if _claude_client is None:
            _claude_client = ClaudeClient(use_mock=MOCK_CLAUDE)
        if _taiwan_llm_client is None:
            _taiwan_llm_client = TaiwanLLMClient(use_mock=MOCK_TAIWAN_LLM)
        _consultation_service = LegalConsultationService(
            claude_client=_claude_client,
            taiwan_llm_client=_taiwan_llm_client
        )
    return _consultation_service

# 請求和響應模型
class ConversationCreateRequest(BaseModel):
    """創建對話請求模型"""
    title: str
    topic: Optional[str] = "general"

class MessageCreateRequest(BaseModel):
    """創建消息請求模型"""
    content: str
    role: str = "user"

class ConversationResponse(BaseModel):
    """對話響應模型"""
    id: str
    title: str
    created_at: str
    topic: Optional[str] = None
    message_count: int = 0

class MessageResponse(BaseModel):
    """消息響應模型"""
    id: str
    conversation_id: str
    content: str
    role: str
    created_at: str

# API 端點
@router.post("/")
async def create_conversation(
    request: ConversationCreateRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """創建新對話
    
    Args:
        request: 包含對話標題和主題的請求
        
    Returns:
        Dict: 包含新對話ID和標題的響應
    """
    try:
        conversation_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        # 創建對話記錄
        conversations[conversation_id] = {
            "id": conversation_id,
            "title": request.title,
            "topic": request.topic,
            "created_at": created_at,
            "message_count": 0
        }
        
        # 創建消息存儲
        messages[conversation_id] = []
        
        # 添加系統初始消息
        system_message_id = str(uuid.uuid4())
        system_message = {
            "id": system_message_id,
            "conversation_id": conversation_id,
            "content": "您好，我是 JURIS NEXUS 法律諮詢助手。請問有什麼法律問題需要協助？",
            "role": "system",
            "created_at": created_at
        }
        messages[conversation_id].append(system_message)
        
        # 更新消息計數
        conversations[conversation_id]["message_count"] = 1
        
        logger.info(f"創建新對話: {conversation_id}, 標題: {request.title}")
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "title": request.title
        }
    except Exception as e:
        logger.error(f"創建對話時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"創建對話時出錯: {str(e)}")

@router.get("/")
async def list_conversations() -> Dict[str, Any]:
    """獲取所有對話列表
    
    Returns:
        Dict: 包含對話列表的響應
    """
    try:
        conversation_list = list(conversations.values())
        conversation_list.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "status": "success",
            "conversations": conversation_list
        }
    except Exception as e:
        logger.error(f"獲取對話列表時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取對話列表時出錯: {str(e)}")

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """獲取特定對話詳情
    
    Args:
        conversation_id: 對話ID
        
    Returns:
        Dict: 包含對話詳情的響應
    """
    try:
        if conversation_id not in conversations:
            raise HTTPException(status_code=404, detail=f"找不到對話: {conversation_id}")
        
        return {
            "status": "success",
            "conversation": conversations[conversation_id]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取對話時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取對話時出錯: {str(e)}")

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str) -> Dict[str, Any]:
    """刪除特定對話
    
    Args:
        conversation_id: 對話ID
        
    Returns:
        Dict: 刪除結果
    """
    try:
        if conversation_id not in conversations:
            raise HTTPException(status_code=404, detail=f"找不到對話: {conversation_id}")
        
        # 刪除對話和相關消息
        del conversations[conversation_id]
        if conversation_id in messages:
            del messages[conversation_id]
        
        logger.info(f"刪除對話: {conversation_id}")
        
        return {
            "status": "success",
            "message": f"對話 {conversation_id} 已刪除"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除對話時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除對話時出錯: {str(e)}")

@router.post("/{conversation_id}/messages")
async def create_message(
    conversation_id: str,
    request: MessageCreateRequest,
    consultation_service: LegalConsultationService = Depends(get_consultation_service)
) -> Dict[str, Any]:
    """添加消息到對話
    
    Args:
        conversation_id: 對話ID
        request: 包含消息內容和角色的請求
        consultation_service: 法律諮詢服務依賴
        
    Returns:
        Dict: 包含消息ID和AI回應的響應
    """
    try:
        if conversation_id not in conversations:
            raise HTTPException(status_code=404, detail=f"找不到對話: {conversation_id}")
        
        # 創建用戶消息
        message_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        user_message = {
            "id": message_id,
            "conversation_id": conversation_id,
            "content": request.content,
            "role": request.role,
            "created_at": created_at
        }
        
        # 添加到消息列表
        if conversation_id not in messages:
            messages[conversation_id] = []
        
        messages[conversation_id].append(user_message)
        
        # 獲取對話歷史
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages[conversation_id]
        ]
        
        # 獲取對話主題
        topic = conversations[conversation_id].get("topic", "general")
        
        # 使用法律諮詢服務生成回應
        logger.info(f"處理對話 {conversation_id} 的消息: {message_id}")
        
        # 呼叫法律諮詢服務
        response_content = await consultation_service.provide_consultation(
            request.content,
            conversation_history=conversation_history,
            topic=topic
        )
        
        # 創建系統回應消息
        system_message_id = str(uuid.uuid4())
        system_message = {
            "id": system_message_id,
            "conversation_id": conversation_id,
            "content": response_content,
            "role": "system",
            "created_at": datetime.now().isoformat()
        }
        
        # 添加到消息列表
        messages[conversation_id].append(system_message)
        
        # 更新消息計數
        conversations[conversation_id]["message_count"] = len(messages[conversation_id])
        
        return {
            "status": "success",
            "message_id": message_id,
            "response": response_content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"創建消息時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"創建消息時出錯: {str(e)}")

@router.get("/{conversation_id}/messages")
async def list_messages(conversation_id: str) -> Dict[str, Any]:
    """獲取對話的所有消息
    
    Args:
        conversation_id: 對話ID
        
    Returns:
        Dict: 包含消息列表的響應
    """
    try:
        if conversation_id not in conversations:
            raise HTTPException(status_code=404, detail=f"找不到對話: {conversation_id}")
        
        conversation_messages = messages.get(conversation_id, [])
        
        return {
            "status": "success",
            "messages": conversation_messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取消息列表時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取消息列表時出錯: {str(e)}")
