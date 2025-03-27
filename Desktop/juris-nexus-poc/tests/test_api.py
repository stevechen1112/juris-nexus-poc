import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import io

from app.main import app
from app.api import get_ai_engine, get_learning_recorder
from app.dual_ai_engine import DualAIEngine
from app.learning_recorder import LearningRecorder

# 創建測試客戶端
client = TestClient(app)

# 模擬分析結果
MOCK_ANALYSIS_RESULT = {
    "status": "success",
    "analysis": {
        "analysis": [
            {
                "clause_id": "第一條",
                "clause_text": "本合同由甲方和乙方簽訂。",
                "risks": [
                    {
                        "risk_description": "未明確定義甲方和乙方",
                        "severity": "中",
                        "legal_basis": "契約明確性原則",
                        "recommendation": "明確定義甲方和乙方的完整資訊"
                    }
                ]
            }
        ],
        "summary": {
            "high_risks_count": 0,
            "medium_risks_count": 1,
            "low_risks_count": 0,
            "overall_risk_assessment": "中度風險"
        }
    },
    "evaluation": {
        "quality_score": 8,
        "feedback": "分析質量良好，但可進一步提高法律專業性",
        "improvement_suggestions": "可以加強法律依據的引用",
        "needs_improvement": False
    },
    "metadata": {
        "used_evaluation": True,
        "used_improvement": False,
        "clauses_count": 1,
        "quality_score": 8,
        "duration_seconds": 2.5
    }
}

# 模擬文檔處理結果
MOCK_DOCUMENT_DATA = {
    "document_info": {
        "filename": "test.docx",
        "file_type": "docx",
        "text_length": 500
    },
    "full_text": "第一條：本合同由甲方和乙方簽訂。",
    "clauses": [
        {"id": "第一條", "text": "本合同由甲方和乙方簽訂。"}
    ]
}

# 測試健康檢查端點
def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "version" in data

# 模擬AI引擎依賴
@pytest.fixture
def mock_ai_engine():
    mock_engine = AsyncMock(spec=DualAIEngine)
    mock_engine.analyze_contract.return_value = MOCK_ANALYSIS_RESULT
    
    original_get_ai_engine = get_ai_engine
    app.dependency_overrides[get_ai_engine] = lambda: mock_engine
    
    yield mock_engine
    
    # 清理
    app.dependency_overrides[get_ai_engine] = original_get_ai_engine

# 模擬學習記錄器依賴
@pytest.fixture
def mock_learning_recorder():
    mock_recorder = AsyncMock(spec=LearningRecorder)
    mock_recorder.get_statistics.return_value = {
        "total_records": 10,
        "success_count": 8,
        "failure_count": 2,
        "success_rate": 80.0,
        "average_recent_score": 8.5
    }
    
    original_get_learning_recorder = get_learning_recorder
    app.dependency_overrides[get_learning_recorder] = lambda: mock_recorder
    
    yield mock_recorder
    
    # 清理
    app.dependency_overrides[get_learning_recorder] = original_get_learning_recorder

# 測試文本分析端點
@pytest.mark.asyncio
async def test_analyze_text(mock_ai_engine):
    # 測試請求數據
    request_data = {
        "text": "第一條：本合同由甲方和乙方簽訂。",
        "format": "default"
    }
    
    # 發送請求
    response = client.post("/api/analyze/text", json=request_data)
    
    # 驗證響應
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "analysis" in data
    
    # 驗證AI引擎調用
    mock_ai_engine.analyze_contract.assert_called_once()
    # 檢查傳遞給analyze_contract的參數
    args, kwargs = mock_ai_engine.analyze_contract.call_args
    assert len(args[0]) > 0  # 確保條款列表非空
    assert kwargs == {}  # 沒有額外參數

# 測試指定參數的文本分析
@pytest.mark.asyncio
async def test_analyze_text_with_options(mock_ai_engine):
    # 測試請求數據，包含選項
    request_data = {
        "text": "第一條：本合同由甲方和乙方簽訂。",
        "format": "default",
        "options": {
            "use_evaluation": False,
            "use_batch_processing": True,
            "batch_size": 5,
            "ignore_cache": True
        }
    }
    
    # 發送請求
    response = client.post("/api/analyze/text", json=request_data)
    
    # 驗證響應
    assert response.status_code == 200
    
    # 驗證選項被正確傳遞
    args, kwargs = mock_ai_engine.analyze_contract.call_args
    assert kwargs["use_evaluation"] is False
    assert kwargs["use_batch_processing"] is True
    assert kwargs["batch_size"] == 5
    assert kwargs["ignore_cache"] is True

# 測試文件上傳和分析端點
@pytest.mark.asyncio
async def test_analyze_file(mock_ai_engine):
    # 模擬文件上傳
    with patch("app.api.process_document", return_value=MOCK_DOCUMENT_DATA) as mock_process:
        # 設置異步魔術方法
        mock_process.__await__ = lambda: iter([MOCK_DOCUMENT_DATA])
        
        # 創建模擬文件
        file_content = b"This is a test file content"
        files = {"file": ("test.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        # 發送請求
        response = client.post("/api/analyze/file", files=files)
        
        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "analysis" in data
        assert "document_info" in data
        
        # 驗證AI引擎調用
        mock_ai_engine.analyze_contract.assert_called_once()

# 測試統計信息端點
@pytest.mark.asyncio
async def test_get_statistics(mock_learning_recorder):
    # 發送請求
    response = client.get("/api/stats")
    
    # 驗證響應
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "stats" in data
    assert data["stats"]["success_rate"] == 80.0
    
    # 驗證學習記錄器調用
    mock_learning_recorder.get_statistics.assert_called_once()
