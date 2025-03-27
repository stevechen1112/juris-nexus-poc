import os
import json
import logging
import datetime
import asyncio
from typing import Dict, List, Any, Optional
import uuid

from app.config import LEARNING_DATA_DIR

logger = logging.getLogger(__name__)

class LearningRecorder:
    """學習記錄模塊，負責記錄AI交互和分析結果"""
    
    def __init__(self, storage_dir: str = LEARNING_DATA_DIR):
        """初始化學習記錄器

        Args:
            storage_dir: 儲存記錄文件的目錄
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.success_dir = os.path.join(storage_dir, "success")
        self.failure_dir = os.path.join(storage_dir, "failure")
        os.makedirs(self.success_dir, exist_ok=True)
        os.makedirs(self.failure_dir, exist_ok=True)
        logger.info(f"學習記錄器已初始化，記錄目錄: {storage_dir}")
    
    async def record_interaction(
        self, 
        analysis_id: str,
        initial_analysis: Dict[str, Any],
        evaluation: Optional[Dict[str, Any]] = None,
        clauses: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """記錄分析交互過程(異步)

        Args:
            analysis_id: 分析ID
            initial_analysis: 初步分析結果
            evaluation: 評估結果(如有)
            clauses: 原始條款數據(如有)

        Returns:
            str: 記錄文件的ID
        """
        # 使用提供的分析ID或生成新ID
        record_id = analysis_id or str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # 構建記錄數據
        record_data = {
            "id": record_id,
            "timestamp": timestamp,
            "initial_analysis": initial_analysis,
            "metadata": {
                "clauses_count": len(clauses) if clauses else 0,
            }
        }
        
        # 如果有評估結果，添加到記錄中
        if evaluation:
            record_data["evaluation"] = evaluation
            record_data["metadata"]["quality_score"] = evaluation.get("quality_score", 0)
            record_data["metadata"]["needs_improvement"] = evaluation.get("needs_improvement", False)
        
        # 如果有條款數據，添加到記錄中
        if clauses:
            record_data["clauses"] = clauses
        
        # 決定保存目錄(成功或失敗)
        # 將評分大於等於7的記錄視為成功案例
        is_success = (evaluation and 
                     "error" not in evaluation and 
                     evaluation.get("quality_score", 0) >= 7)
        save_dir = self.success_dir if is_success else self.failure_dir
        
        # 保存記錄
        filename = f"{record_id}.json"
        filepath = os.path.join(save_dir, filename)
        
        # 異步寫入文件
        try:
            # 使用asyncio.to_thread進行非阻塞IO
            await asyncio.to_thread(self._write_json_file, filepath, record_data)
            logger.info(f"已記錄交互過程: {filepath}")
            return record_id
        except Exception as e:
            logger.error(f"記錄交互過程時出錯: {str(e)}")
            return ""
    
    async def record_improvement(
        self,
        analysis_id: str,
        improved_analysis: Dict[str, Any]
    ) -> bool:
        """記錄改進的分析結果(異步)

        Args:
            analysis_id: 分析ID，與之前的record_interaction相對應
            improved_analysis: 改進後的分析結果

        Returns:
            bool: 是否成功記錄
        """
        # 嘗試在兩個目錄中尋找記錄文件
        filename = f"{analysis_id}.json"
        success_path = os.path.join(self.success_dir, filename)
        failure_path = os.path.join(self.failure_dir, filename)
        
        # 檢查文件是否存在
        if os.path.exists(success_path):
            filepath = success_path
        elif os.path.exists(failure_path):
            filepath = failure_path
        else:
            logger.warning(f"未找到分析ID為{analysis_id}的記錄文件")
            return False
        
        try:
            # 讀取現有記錄
            data = await asyncio.to_thread(self._read_json_file, filepath)
            if not data:
                return False
            
            # 更新記錄
            data["improved_analysis"] = improved_analysis
            data["metadata"]["improved_timestamp"] = datetime.datetime.now().isoformat()
            
            # 寫回文件
            await asyncio.to_thread(self._write_json_file, filepath, data)
            logger.info(f"已更新記錄文件，添加改進分析: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"更新記錄文件時出錯: {str(e)}")
            return False
    
    def _write_json_file(self, filepath: str, data: Dict[str, Any]) -> bool:
        """同步寫入JSON文件

        Args:
            filepath: 文件路徑
            data: 要寫入的數據

        Returns:
            bool: 是否成功寫入
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"寫入JSON文件時出錯: {filepath}, {str(e)}")
            return False
    
    def _read_json_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        """同步讀取JSON文件

        Args:
            filepath: 文件路徑

        Returns:
            Optional[Dict[str, Any]]: 讀取的數據，如果失敗則返回None
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"讀取JSON文件時出錯: {filepath}, {str(e)}")
            return None
    
    async def get_successful_examples(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取成功案例(異步)
        
        這些案例可以用於未來的模型優化

        Args:
            limit: 返回的最大記錄數量

        Returns:
            List[Dict[str, Any]]: 成功案例列表
        """
        return await self._get_examples(self.success_dir, limit)
    
    async def get_failure_examples(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取失敗案例(異步)
        
        這些案例可以用於分析系統的弱點

        Args:
            limit: 返回的最大記錄數量

        Returns:
            List[Dict[str, Any]]: 失敗案例列表
        """
        return await self._get_examples(self.failure_dir, limit)
    
    async def _get_examples(self, directory: str, limit: int) -> List[Dict[str, Any]]:
        """從目錄獲取實例(異步)

        Args:
            directory: 記錄目錄
            limit: 最大記錄數量

        Returns:
            List[Dict[str, Any]]: 記錄列表
        """
        examples = []
        if not os.path.exists(directory):
            logger.warning(f"記錄目錄不存在: {directory}")
            return examples
        
        # 列出所有JSON文件(同步操作，但文件列表通常較小)
        files = [f for f in os.listdir(directory) if f.endswith(".json")]
        # 按修改時間排序(最新的優先)
        files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
        
        # 並行讀取文件，最多讀取limit個
        async def read_file(filename):
            filepath = os.path.join(directory, filename)
            return await asyncio.to_thread(self._read_json_file, filepath)
        
        # 創建讀取任務
        tasks = [read_file(f) for f in files[:limit]]
        results = await asyncio.gather(*tasks)
        
        # 過濾掉失敗的讀取結果
        examples = [r for r in results if r is not None]
        return examples
    
    async def get_statistics(self) -> Dict[str, Any]:
        """獲取學習數據統計信息(異步)

        Returns:
            Dict[str, Any]: 統計信息
        """
        # 列出文件(同步操作，但通常速度較快)
        success_files = [f for f in os.listdir(self.success_dir) if f.endswith('.json')]
        failure_files = [f for f in os.listdir(self.failure_dir) if f.endswith('.json')]
        
        # 計算成功率
        total = len(success_files) + len(failure_files)
        success_rate = (len(success_files) / total) * 100 if total > 0 else 0
        
        # 讀取最近5個成功案例的分數
        recent_scores = []
        success_files.sort(key=lambda f: os.path.getmtime(os.path.join(self.success_dir, f)), reverse=True)
        
        # 並行讀取
        async def read_score(filename):
            filepath = os.path.join(self.success_dir, filename)
            data = await asyncio.to_thread(self._read_json_file, filepath)
            if data:
                return data.get("evaluation", {}).get("quality_score", 0)
            return None
        
        # 創建讀取任務
        tasks = [read_score(f) for f in success_files[:5]]
        scores = await asyncio.gather(*tasks)
        
        # 過濾掉None值
        recent_scores = [s for s in scores if s is not None]
        avg_recent_score = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        
        return {
            "total_records": total,
            "success_count": len(success_files),
            "failure_count": len(failure_files),
            "success_rate": success_rate,
            "average_recent_score": avg_recent_score,
            "timestamp": datetime.datetime.now().isoformat()
        }

    # 為向後兼容保留的同步方法
    def record_interaction_sync(
        self, 
        input_data: Dict[str, Any], 
        initial_output: Dict[str, Any],
        evaluation: Dict[str, Any], 
        final_output: Dict[str, Any]
    ) -> str:
        """同步記錄交互過程(為兼容舊代碼)"""
        record_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        record_data = {
            "id": record_id,
            "timestamp": timestamp,
            "input_data": input_data,
            "initial_output": initial_output,
            "evaluation": evaluation,
            "final_output": final_output,
            "metadata": {
                "clauses_count": len(input_data.get("clauses", [])),
                "overall_score": evaluation.get("overall_score", 0),
                "improved": evaluation.get("needs_improvement", False)
            }
        }
        
        is_success = "error" not in evaluation and evaluation.get("overall_score", 0) >= 7
        save_dir = self.success_dir if is_success else self.failure_dir
        
        filename = f"{record_id}.json"
        filepath = os.path.join(save_dir, filename)
        
        if self._write_json_file(filepath, record_data):
            return record_id
        return ""
