import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.document_processor import preprocess_document, split_into_clauses
from app.dual_ai_engine import DualAIEngine
from app.learning_recorder import LearningRecorder
from app.utils import save_upload_file_temporarily, format_json_response, format_error_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# 緩存AI引擎實例
_ai_engine = None
_learning_recorder = None

def get_ai_engine() -> DualAIEngine:
    """取得或創建AI引擎實例
    
    Returns:
        DualAIEngine: AI引擎實例
    """
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = DualAIEngine()
    return _ai_engine

def get_learning_recorder() -> LearningRecorder:
    """取得或創建學習記錄器實例
    
    Returns:
        LearningRecorder: 學習記錄器實例
    """
    global _learning_recorder
    if _learning_recorder is None:
        _learning_recorder = LearningRecorder()
    return _learning_recorder

def _record_analysis_result(
    input_data: Dict[str, Any], 
    analysis_result: Dict[str, Any]
) -> str:
    """背景任務：記錄分析結果
    
    Args:
        input_data: 輸入數據
        analysis_result: 分析結果
    
    Returns:
        str: 記錄ID
    """
    recorder = get_learning_recorder()
    
    # 從結果中提取所需數據
    initial_output = analysis_result.get("initial_analysis", analysis_result.get("analysis", {}))
    evaluation = analysis_result.get("evaluation", {})
    final_output = analysis_result.get("analysis", {})
    
    # 記錄交互
    return recorder.record_interaction(
        input_data=input_data,
        initial_output=initial_output,
        evaluation=evaluation,
        final_output=final_output
    )

# API路由
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康檢查端點
    
    Returns:
        Dict: 健康狀態
    """
    return {
        "status": "success",
        "message": "服務正常運行",
        "version": "0.2.0"
    }

# 文本分析請求模型
class TextAnalysisRequest(BaseModel):
    """文本分析請求模型"""
    text: str
    format: str = "default"  # 條款格式化方式
    options: Optional[Dict[str, Any]] = None  # 分析選項

# 分析結果響應模型
class AnalysisResponse(BaseModel):
    """分析結果響應模型"""
    status: str
    document_info: Optional[Dict[str, Any]] = None
    analysis: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

# 文本分析端點
@router.post("/analyze/text", response_model=AnalysisResponse)
async def analyze_text(
    request: TextAnalysisRequest,
    engine: DualAIEngine = Depends(get_ai_engine)
) -> Dict[str, Any]:
    """分析文本中的合同條款
    
    Args:
        request: 包含待分析文本的請求對象
        engine: AI引擎依賴

    Returns:
        Dict: 包含分析結果的響應
    """
    logger.info("接收到文本分析請求")
    
    try:
        # 拆分條款
        clauses = split_into_clauses(request.text)
        
        # 設置分析選項
        options = request.options or {}
        
        # 分析條款
        result = await engine.analyze_contract(clauses, **options)
        
        # 構建回應
        response = {
            "status": result.get("status", "success"),
            "analysis": result.get("analysis", {}),
            "metadata": result.get("metadata", {})
        }
        
        # 可選地包含評估結果
        if "evaluation" in result:
            response["evaluation"] = result["evaluation"]
        
        return response
        
    except Exception as e:
        logger.error(f"分析文本時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析文本時出錯: {str(e)}")

# 文件分析端點
@router.post("/analyze/file", response_model=AnalysisResponse)
async def analyze_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    engine: DualAIEngine = Depends(get_ai_engine)
) -> Dict[str, Any]:
    """分析上傳的合同文件
    
    Args:
        background_tasks: 背景任務管理器
        file: 上傳的合同文件
        engine: AI引擎依賴

    Returns:
        Dict: 包含分析結果的響應
    """
    logger.info(f"接收到文件分析請求: {file.filename}")
    
    # 檢查文件類型
    file_extension = os.path.splitext(file.filename)[1].lower()
    supported_extensions = ['.pdf', '.docx', '.doc']
    if file_extension not in supported_extensions:
        error_msg = f"不支持的文件類型: {file_extension}。支持的類型: {', '.join(supported_extensions)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # 處理文件上傳
        temp_file_path = await save_upload_file_temporarily(file)
        
        # 處理文檔
        document_data = await process_document(temp_file_path)
        
        # 分析合同
        result = await engine.analyze_contract(document_data['clauses'])
        
        # 清理臨時文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        # 構建回應
        response = {
            "status": result.get("status", "success"),
            "document_info": document_data['document_info'],
            "analysis": result.get("analysis", {}),
            "metadata": result.get("metadata", {})
        }
        
        # 可選地包含評估結果
        if "evaluation" in result:
            response["evaluation"] = result["evaluation"]
        
        return response
        
    except Exception as e:
        logger.error(f"分析文件時出錯: {str(e)}")
        # 如果出錯也要清理臨時文件
        try:
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception:
            pass
        
        raise HTTPException(status_code=500, detail=f"分析文件時出錯: {str(e)}")

# 統計信息端點
@router.get("/stats")
async def get_statistics(
    recorder: LearningRecorder = Depends(get_learning_recorder)
) -> Dict[str, Any]:
    """獲取系統統計信息
    
    Args:
        recorder: 學習記錄器依賴

    Returns:
        Dict: 統計信息
    """
    logger.info("獲取系統統計信息")
    
    try:
        stats = await recorder.get_statistics()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"獲取統計信息時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取統計信息時出錯: {str(e)}")

# 原有的分析合同端點（保留向後兼容性）
@router.post("/analyze-contract")
async def analyze_contract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    engine: DualAIEngine = Depends(get_ai_engine)
) -> Dict[str, Any]:
    """接收合同文件並返回風險分析(舊端點)
    
    Args:
        background_tasks: 背景任務管理器
        file: 上傳的合同文件
        engine: AI引擎依賴

    Returns:
        Dict: 包含分析結果的響應
    """
    logger.info(f"接收到合同分析請求(舊端點): {file.filename}")
    
    # 重定向到新端點
    result = await analyze_file(background_tasks, file, engine)
    
    # 為舊格式做轉換
    return {
        "status": result.get("status", "success"),
        "document_info": result.get("document_info", {}),
        "analysis_result": {
            "analysis": result.get("analysis", {}),
            "evaluation": result.get("evaluation", {}),
            "metadata": result.get("metadata", {})
        }
    }

# 工具函數
async def process_document(file_path: str) -> Dict[str, Any]:
    """處理文檔並提取條款（異步版本）
    
    Args:
        file_path: 文件路徑

    Returns:
        Dict: 文檔數據
    """
    # 在非阻塞模式下調用同步函數
    return await asyncio.to_thread(preprocess_document, file_path)
