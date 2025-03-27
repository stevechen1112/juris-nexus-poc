import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.dual_ai_engine import DualAIEngine

# 模擬條款數據
MOCK_CLAUSES = [
    {"id": "第一條", "text": "本合同由甲方和乙方簽訂。"},
    {"id": "第二條", "text": "合同期限為一年。"}
]

# 模擬初步分析結果
MOCK_INITIAL_ANALYSIS = {
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
}

# 模擬評估結果
MOCK_EVALUATION = {
    "quality_score": 8,
    "feedback": "分析質量良好，但可進一步提高法律專業性",
    "missing_risks": [],
    "improvement_suggestions": "可以更詳細地說明法律依據",
    "needs_improvement": False
}

# 模擬改進後的分析結果
MOCK_IMPROVED_ANALYSIS = {
    "analysis": [
        {
            "clause_id": "第一條",
            "clause_text": "本合同由甲方和乙方簽訂。",
            "risks": [
                {
                    "risk_description": "未明確定義甲方和乙方",
                    "severity": "中",
                    "legal_basis": "依據民法第153條，契約成立時應有當事人之意思表示一致，當事人身分不明確可能導致契約效力存疑",
                    "recommendation": "明確定義甲方和乙方的完整資訊，包括名稱、統一編號及代表人"
                }
            ]
        }
    ],
    "summary": {
        "high_risks_count": 0,
        "medium_risks_count": 1,
        "low_risks_count": 0,
        "overall_risk_assessment": "中度風險，但可通過修正降低風險"
    }
}

# 測試DualAIEngine的分析功能
@pytest.mark.asyncio
async def test_analyze_contract():
    # 創建模擬客戶端
    mock_taiwan_llm = AsyncMock()
    mock_taiwan_llm.analyze_contract.return_value = MOCK_INITIAL_ANALYSIS
    mock_taiwan_llm.cache_enabled = True
    
    mock_claude = AsyncMock()
    mock_claude.evaluate_analysis.return_value = MOCK_EVALUATION
    mock_claude.cache_enabled = True
    
    mock_recorder = AsyncMock()
    
    # 創建引擎實例
    engine = DualAIEngine(
        taiwan_llm_client=mock_taiwan_llm,
        claude_client=mock_claude,
        learning_recorder=mock_recorder
    )
    
    # 執行分析
    result = await engine.analyze_contract(MOCK_CLAUSES)
    
    # 驗證結果
    assert result["status"] == "success"
    assert result["analysis"] == MOCK_INITIAL_ANALYSIS
    assert result["evaluation"] == MOCK_EVALUATION
    assert result["metadata"]["used_evaluation"] is True
    assert result["metadata"]["used_improvement"] is False
    assert "quality_score" in result["metadata"]
    
    # 驗證函數調用
    mock_taiwan_llm.analyze_contract.assert_called_once_with(MOCK_CLAUSES)
    mock_claude.evaluate_analysis.assert_called_once_with(MOCK_INITIAL_ANALYSIS, MOCK_CLAUSES)
    mock_recorder.record_interaction.assert_called_once()

# 測試需要改進的情況
@pytest.mark.asyncio
async def test_analyze_contract_with_improvement():
    # 創建需要改進的評估結果
    evaluation_needs_improvement = MOCK_EVALUATION.copy()
    evaluation_needs_improvement["needs_improvement"] = True
    evaluation_needs_improvement["missing_risks"] = [
        {
            "clause_id": "第一條",
            "risk_description": "缺少明確的通知地址",
            "severity": "低"
        }
    ]
    
    # 創建模擬客戶端
    mock_taiwan_llm = AsyncMock()
    mock_taiwan_llm.analyze_contract.return_value = MOCK_INITIAL_ANALYSIS
    mock_taiwan_llm.cache_enabled = True
    
    mock_claude = AsyncMock()
    mock_claude.evaluate_analysis.return_value = evaluation_needs_improvement
    mock_claude.improve_analysis.return_value = MOCK_IMPROVED_ANALYSIS
    mock_claude.cache_enabled = True
    
    mock_recorder = AsyncMock()
    
    # 創建引擎實例
    engine = DualAIEngine(
        taiwan_llm_client=mock_taiwan_llm,
        claude_client=mock_claude,
        learning_recorder=mock_recorder
    )
    
    # 執行分析
    result = await engine.analyze_contract(MOCK_CLAUSES)
    
    # 驗證結果
    assert result["status"] == "success"
    assert result["evaluation"] == evaluation_needs_improvement
    assert result["analysis"] == MOCK_IMPROVED_ANALYSIS
    assert result["initial_analysis"] == MOCK_INITIAL_ANALYSIS
    assert result["metadata"]["used_evaluation"] is True
    assert result["metadata"]["used_improvement"] is True
    
    # 驗證函數調用
    mock_taiwan_llm.analyze_contract.assert_called_once_with(MOCK_CLAUSES)
    mock_claude.evaluate_analysis.assert_called_once_with(MOCK_INITIAL_ANALYSIS, MOCK_CLAUSES)
    mock_claude.improve_analysis.assert_called_once_with(
        original_analysis=MOCK_INITIAL_ANALYSIS,
        evaluation=evaluation_needs_improvement,
        clauses=MOCK_CLAUSES
    )
    mock_recorder.record_interaction.assert_called_once()
    mock_recorder.record_improvement.assert_called_once()

# 測試處理Taiwan LLM錯誤的情況
@pytest.mark.asyncio
async def test_analyze_contract_with_taiwan_llm_error():
    # 創建模擬客戶端
    mock_taiwan_llm = AsyncMock()
    mock_taiwan_llm.analyze_contract.return_value = {"error": "模型調用失敗"}
    mock_taiwan_llm.cache_enabled = True
    
    mock_claude = AsyncMock()
    mock_claude.cache_enabled = True
    
    mock_recorder = AsyncMock()
    
    # 創建引擎實例
    engine = DualAIEngine(
        taiwan_llm_client=mock_taiwan_llm,
        claude_client=mock_claude,
        learning_recorder=mock_recorder
    )
    
    # 執行分析
    result = await engine.analyze_contract(MOCK_CLAUSES)
    
    # 驗證結果
    assert result["status"] == "error"
    assert "error" in result
    assert "analysis" in result
    assert result["analysis"]["error"] == "模型調用失敗"
    
    # 驗證函數調用
    mock_taiwan_llm.analyze_contract.assert_called_once_with(MOCK_CLAUSES)
    mock_claude.evaluate_analysis.assert_not_called()  # Claude不應該被調用
    mock_recorder.record_interaction.assert_not_called()  # 不應記錄失敗的交互

# 測試批量處理
@pytest.mark.asyncio
async def test_analyze_contract_with_batch_processing():
    # 創建較大的條款列表
    large_clauses = [{"id": f"條款{i}", "text": f"這是條款內容{i}"} for i in range(10)]
    
    # 創建模擬客戶端
    mock_taiwan_llm = AsyncMock()
    mock_taiwan_llm.analyze_contract.return_value = MOCK_INITIAL_ANALYSIS
    mock_taiwan_llm.analyze_contract_batch.return_value = MOCK_INITIAL_ANALYSIS
    mock_taiwan_llm.cache_enabled = True
    
    mock_claude = AsyncMock()
    mock_claude.evaluate_analysis.return_value = MOCK_EVALUATION
    mock_claude.cache_enabled = True
    
    mock_recorder = AsyncMock()
    
    # 創建引擎實例
    engine = DualAIEngine(
        taiwan_llm_client=mock_taiwan_llm,
        claude_client=mock_claude,
        learning_recorder=mock_recorder,
        use_batch_processing=True,
        batch_size=3
    )
    
    # 執行分析
    result = await engine.analyze_contract(large_clauses)
    
    # 驗證結果
    assert result["status"] == "success"
    
    # 驗證批量處理被調用
    mock_taiwan_llm.analyze_contract_batch.assert_called_once_with(large_clauses, batch_size=3)
    mock_taiwan_llm.analyze_contract.assert_not_called()  # 直接分析不應被調用

# 測試不使用評估的情況
@pytest.mark.asyncio
async def test_analyze_contract_without_evaluation():
    # 創建模擬客戶端
    mock_taiwan_llm = AsyncMock()
    mock_taiwan_llm.analyze_contract.return_value = MOCK_INITIAL_ANALYSIS
    mock_taiwan_llm.cache_enabled = True
    
    mock_claude = AsyncMock()
    mock_claude.cache_enabled = True
    
    mock_recorder = AsyncMock()
    
    # 創建引擎實例，禁用評估
    engine = DualAIEngine(
        taiwan_llm_client=mock_taiwan_llm,
        claude_client=mock_claude,
        learning_recorder=mock_recorder,
        use_evaluation=False
    )
    
    # 執行分析
    result = await engine.analyze_contract(MOCK_CLAUSES)
    
    # 驗證結果
    assert result["status"] == "success"
    assert result["analysis"] == MOCK_INITIAL_ANALYSIS
    assert "evaluation" not in result
    assert result["metadata"]["used_evaluation"] is False
    assert result["metadata"]["used_improvement"] is False
    
    # 驗證僅調用了Taiwan LLM
    mock_taiwan_llm.analyze_contract.assert_called_once_with(MOCK_CLAUSES)
    mock_claude.evaluate_analysis.assert_not_called()
    mock_recorder.record_interaction.assert_not_called()  # 沒有評估，不記錄交互
