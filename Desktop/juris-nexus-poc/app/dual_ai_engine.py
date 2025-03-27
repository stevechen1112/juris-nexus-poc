import logging
import json
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from app.model_clients import TaiwanLLMClient, ClaudeClient
from app.learning_recorder import LearningRecorder

logger = logging.getLogger(__name__)

class DualAIEngine:
    """雙層AI分析引擎 - 協調Taiwan LLM與Claude處理合同分析"""
    
    def __init__(
        self,
        taiwan_llm_client: Optional[TaiwanLLMClient] = None,
        claude_client: Optional[ClaudeClient] = None,
        learning_recorder: Optional[LearningRecorder] = None,
        use_evaluation: bool = True,
        use_improvement: bool = True,
        use_batch_processing: bool = True,
        batch_size: int = 3
    ):
        """初始化雙層AI引擎
        
        Args:
            taiwan_llm_client: 台灣LLM客戶端，如未提供會創建默認實例
            claude_client: Claude客戶端，如未提供會創建默認實例
            learning_recorder: 學習記錄器，用於記錄互動和改進
            use_evaluation: 是否使用Claude評估結果
            use_improvement: 是否使用Claude改進分析
            use_batch_processing: 是否使用批量處理
            batch_size: 批量處理時每批的條款數量
        """
        self.taiwan_llm = taiwan_llm_client or TaiwanLLMClient()
        self.claude = claude_client or ClaudeClient()
        self.learning_recorder = learning_recorder or LearningRecorder()
        self.use_evaluation = use_evaluation
        self.use_improvement = use_improvement
        self.use_batch_processing = use_batch_processing
        self.batch_size = batch_size
        
        logger.info("已初始化雙層AI引擎")
        if not use_evaluation:
            logger.info("評估功能已禁用")
        if not use_improvement:
            logger.info("改進功能已禁用")
    
    async def analyze_contract(
        self, 
        clauses: List[Dict[str, str]], 
        **kwargs
    ) -> Dict[str, Any]:
        """協調雙層AI分析合同條款

        Args:
            clauses: 合同條款列表，每個條款為包含id和text的字典
            **kwargs: 其他選項，可包括：
                - use_evaluation: 布爾值，覆蓋默認評估設置
                - use_improvement: 布爾值，覆蓋默認改進設置
                - use_batch_processing: 布爾值，覆蓋默認批量處理設置
                - batch_size: 整數，每批處理的條款數量
                - ignore_cache: 布爾值，是否忽略緩存

        Returns:
            Dict: 包含分析結果、評估及元數據的字典
        """
        # 獲取運行時選項
        use_evaluation = kwargs.get('use_evaluation', self.use_evaluation)
        use_improvement = kwargs.get('use_improvement', self.use_improvement)
        use_batch_processing = kwargs.get('use_batch_processing', self.use_batch_processing)
        batch_size = kwargs.get('batch_size', self.batch_size)
        ignore_cache = kwargs.get('ignore_cache', False)
        
        # 如果指定忽略緩存，臨時關閉各客戶端的緩存
        if ignore_cache:
            original_cache_state_taiwan = self.taiwan_llm.cache_enabled
            original_cache_state_claude = self.claude.cache_enabled
            self.taiwan_llm.cache_enabled = False
            self.claude.cache_enabled = False
        
        # 記錄處理開始
        start_time = time.time()
        logger.info(f"開始分析合同，共{len(clauses)}個條款")
        
        # 生成唯一分析ID用於追蹤
        analysis_id = f"analysis_{int(start_time)}"
        
        try:
            # 第一步：使用Taiwan LLM進行初步分析
            logger.info(f"[{analysis_id}] 使用Taiwan LLM進行初步分析")
            
            # 根據條款數量決定是否使用批量處理
            if use_batch_processing and len(clauses) > batch_size:
                logger.info(f"[{analysis_id}] 使用批量處理模式，批次大小: {batch_size}")
                initial_analysis = await self.taiwan_llm.analyze_contract_batch(clauses, batch_size=batch_size)
            else:
                logger.info(f"[{analysis_id}] 使用標準處理模式")
                initial_analysis = await self.taiwan_llm.analyze_contract(clauses)
            
            # 檢查初步分析是否出錯
            if "error" in initial_analysis:
                logger.error(f"[{analysis_id}] Taiwan LLM分析出錯: {initial_analysis['error']}")
                return {
                    "analysis": initial_analysis,
                    "status": "error",
                    "error": initial_analysis.get("error", "Taiwan LLM分析失敗"),
                    "metadata": {
                        "duration_seconds": time.time() - start_time,
                        "clauses_count": len(clauses),
                        "analysis_id": analysis_id
                    }
                }
            
            logger.info(f"[{analysis_id}] Taiwan LLM初步分析完成")
            
            # 如果不需要評估，直接返回初步分析結果
            if not use_evaluation:
                return {
                    "analysis": initial_analysis,
                    "status": "success",
                    "metadata": {
                        "duration_seconds": time.time() - start_time,
                        "clauses_count": len(clauses),
                        "analysis_id": analysis_id,
                        "used_evaluation": False,
                        "used_improvement": False
                    }
                }
            
            # 第二步：使用Claude評估初步分析
            logger.info(f"[{analysis_id}] 使用Claude評估分析結果")
            evaluation = await self.claude.evaluate_analysis(initial_analysis, clauses)
            
            # 記錄評估
            await self.learning_recorder.record_interaction(
                analysis_id=analysis_id,
                initial_analysis=initial_analysis,
                evaluation=evaluation
            )
            
            # 如果不需要改進或評估顯示不需要改進，返回初步分析和評估結果
            if not use_improvement or not evaluation.get("needs_improvement", False):
                quality_score = evaluation.get("quality_score", 0)
                logger.info(f"[{analysis_id}] 評估完成，質量評分: {quality_score}/10，無需改進")
                
                return {
                    "analysis": initial_analysis,
                    "evaluation": evaluation,
                    "status": "success",
                    "metadata": {
                        "duration_seconds": time.time() - start_time,
                        "clauses_count": len(clauses),
                        "analysis_id": analysis_id,
                        "used_evaluation": True,
                        "used_improvement": False,
                        "quality_score": quality_score
                    }
                }
            
            # 第三步：如果需要改進，使用Claude改進分析
            logger.info(f"[{analysis_id}] 基於評估反饋改進分析")
            improved_analysis = await self.claude.improve_analysis(
                original_analysis=initial_analysis,
                evaluation=evaluation,
                clauses=clauses
            )
            
            # 記錄改進結果
            await self.learning_recorder.record_improvement(
                analysis_id=analysis_id,
                improved_analysis=improved_analysis
            )
            
            # 計算完整處理時間
            duration = time.time() - start_time
            quality_score = evaluation.get("quality_score", 0)
            logger.info(f"[{analysis_id}] 分析完成，總耗時: {duration:.2f}秒，質量評分: {quality_score}/10")
            
            # 返回完整結果
            return {
                "analysis": improved_analysis,
                "initial_analysis": initial_analysis,
                "evaluation": evaluation,
                "status": "success",
                "metadata": {
                    "duration_seconds": duration,
                    "clauses_count": len(clauses),
                    "analysis_id": analysis_id,
                    "used_evaluation": True,
                    "used_improvement": True,
                    "quality_score": quality_score
                }
            }
            
        except Exception as e:
            # 處理過程中的任何異常
            logger.error(f"[{analysis_id}] 分析過程發生錯誤: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "metadata": {
                    "duration_seconds": time.time() - start_time,
                    "clauses_count": len(clauses),
                    "analysis_id": analysis_id
                }
            }
        finally:
            # 如果暫時關閉了緩存，恢復原始設置
            if ignore_cache:
                self.taiwan_llm.cache_enabled = original_cache_state_taiwan
                self.claude.cache_enabled = original_cache_state_claude
