"""
模板優化器 - 基於反饋數據優化提示詞模板
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from app.prompt_engine.prompt_manager import PromptManager
from app.learning_recorder import LearningRecorder

logger = logging.getLogger(__name__)

class TemplateOptimizer:
    """模板優化器 - 基於反饋數據優化提示詞模板"""
    
    def __init__(self, prompt_manager: PromptManager, learning_recorder: LearningRecorder, claude_client=None):
        """初始化模板優化器
        
        Args:
            prompt_manager: 提示詞管理器
            learning_recorder: 學習記錄器
            claude_client: Claude API客戶端（如果為None，將在需要時創建）
        """
        self.prompt_manager = prompt_manager
        self.learning_recorder = learning_recorder
        self.claude_client = claude_client
        
        # 優化閾值 - 當模板平均評分低於此值時觸發優化
        self.optimization_threshold = 7.0
        # 最小反饋數 - 至少需要這麼多反饋才考慮優化
        self.min_feedback_count = 3
    
    async def analyze_template_performance(self, template_id: str) -> Dict[str, Any]:
        """分析模板性能
        
        Args:
            template_id: 模板ID
            
        Returns:
            性能分析結果
        """
        # 獲取模板
        template = self.prompt_manager.get_prompt_template(template_id)
        if not template:
            # 嘗試在法律任務模板中查找
            for task in self.prompt_manager.templates["legal_tasks"].values():
                if "templates" in task:
                    for t in task["templates"]:
                        if t.get("template_id") == template_id:
                            template = t
                            break
                    if template:
                        break
        
        if not template:
            logger.error(f"未找到模板: {template_id}")
            return {"error": "未找到模板", "template_id": template_id}
        
        # 獲取模板的反饋數據
        feedback_data = await self.learning_recorder.get_template_feedback(template_id)
        
        # 計算性能指標
        total_ratings = len(feedback_data)
        if total_ratings == 0:
            return {
                "template_id": template_id,
                "template_name": template.get("template_name", "未命名模板"),
                "total_feedback": 0,
                "average_rating": None,
                "needs_optimization": False,
                "common_issues": [],
                "strengths": []
            }
        
        # 計算平均評分
        ratings = [feedback.get("rating", 0) for feedback in feedback_data if "rating" in feedback]
        average_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # 分析常見問題和優勢
        issues = [feedback.get("issues", []) for feedback in feedback_data if "issues" in feedback]
        strengths = [feedback.get("strengths", []) for feedback in feedback_data if "strengths" in feedback]
        
        # 展平列表
        all_issues = [issue for sublist in issues for issue in sublist]
        all_strengths = [strength for sublist in strengths for strength in sublist]
        
        # 計算問題和優勢的頻率
        issue_frequency = {}
        for issue in all_issues:
            issue_frequency[issue] = issue_frequency.get(issue, 0) + 1
            
        strength_frequency = {}
        for strength in all_strengths:
            strength_frequency[strength] = strength_frequency.get(strength, 0) + 1
            
        # 排序問題和優勢
        common_issues = sorted(issue_frequency.items(), key=lambda x: x[1], reverse=True)
        common_strengths = sorted(strength_frequency.items(), key=lambda x: x[1], reverse=True)
        
        # 判斷是否需要優化
        needs_optimization = (
            average_rating < self.optimization_threshold and 
            total_ratings >= self.min_feedback_count
        )
        
        return {
            "template_id": template_id,
            "template_name": template.get("template_name", "未命名模板"),
            "total_feedback": total_ratings,
            "average_rating": average_rating,
            "needs_optimization": needs_optimization,
            "common_issues": [{"issue": issue, "frequency": freq} for issue, freq in common_issues[:5]],
            "strengths": [{"strength": strength, "frequency": freq} for strength, freq in common_strengths[:5]]
        }
    
    async def optimize_template(self, template_id: str, force: bool = False) -> Dict[str, Any]:
        """優化特定模板
        
        Args:
            template_id: 模板ID
            force: 是否強制優化（即使不滿足優化條件）
            
        Returns:
            優化結果
        """
        # 分析模板性能
        performance = await self.analyze_template_performance(template_id)
        
        # 檢查是否需要優化
        if not force and not performance.get("needs_optimization", False):
            return {
                "template_id": template_id,
                "optimized": False,
                "reason": "模板性能良好，不需要優化",
                "performance": performance
            }
        
        # 獲取模板
        template = self.prompt_manager.get_prompt_template(template_id)
        if not template:
            # 嘗試在法律任務模板中查找
            for task in self.prompt_manager.templates["legal_tasks"].values():
                if "templates" in task:
                    for t in task["templates"]:
                        if t.get("template_id") == template_id:
                            template = t
                            break
                    if template:
                        break
        
        if not template:
            logger.error(f"未找到模板: {template_id}")
            return {"error": "未找到模板", "template_id": template_id}
        
        # 獲取模板的反饋數據
        feedback_data = await self.learning_recorder.get_template_feedback(template_id)
        
        # 如果沒有足夠的反饋數據，無法優化
        if len(feedback_data) < self.min_feedback_count and not force:
            return {
                "template_id": template_id,
                "optimized": False,
                "reason": f"反饋數據不足，需要至少 {self.min_feedback_count} 條反饋",
                "performance": performance
            }
        
        # 準備優化提示
        optimization_prompt = self._create_optimization_prompt(template, performance, feedback_data)
        
        # 調用Claude API進行優化
        optimized_template = await self._call_claude_for_optimization(optimization_prompt, template)
        
        if not optimized_template:
            return {
                "template_id": template_id,
                "optimized": False,
                "reason": "優化過程中發生錯誤",
                "performance": performance
            }
        
        # 更新模板
        success = self.prompt_manager.save_prompt_template(optimized_template)
        
        if not success:
            return {
                "template_id": template_id,
                "optimized": False,
                "reason": "保存優化後的模板失敗",
                "performance": performance
            }
        
        # 更新模板性能指標
        metrics_update = {
            "improvement_count": template.get("performance_metrics", {}).get("improvement_count", 0) + 1,
            "last_optimized": optimized_template.get("updated_at")
        }
        self.prompt_manager.update_template_metrics(template_id, metrics_update)
        
        return {
            "template_id": template_id,
            "optimized": True,
            "old_template": template.get("prompt_template"),
            "new_template": optimized_template.get("prompt_template"),
            "performance": performance,
            "optimization_summary": optimized_template.get("optimization_summary", "")
        }
    
    def _create_optimization_prompt(self, template: Dict[str, Any], 
                                   performance: Dict[str, Any], 
                                   feedback_data: List[Dict[str, Any]]) -> str:
        """創建用於優化模板的提示
        
        Args:
            template: 原始模板
            performance: 性能分析結果
            feedback_data: 反饋數據
            
        Returns:
            優化提示
        """
        # 格式化反饋數據
        formatted_feedback = json.dumps(feedback_data, ensure_ascii=False, indent=2)
        
        # 格式化性能分析
        formatted_performance = json.dumps(performance, ensure_ascii=False, indent=2)
        
        # 構建優化提示
        prompt = f"""作為一位專精於台灣法律領域的AI提示詞工程專家，請優化以下提示詞模板，使其在法律應用中更有效。

原始模板信息:
模板ID: {template.get('template_id')}
模板名稱: {template.get('template_name')}
模板版本: {template.get('template_version')}
任務類型: {template.get('task_type')}
模型類型: {template.get('model_type')}

原始提示詞模板:
```
{template.get('prompt_template')}
```

模板參數: {', '.join(template.get('parameters', []))}
預期輸出格式: {template.get('expected_output_format')}

性能分析:
{formatted_performance}

用戶反饋:
{formatted_feedback}

請根據以上信息，優化提示詞模板，使其:
1. 更好地符合台灣法律專業要求
2. 解決用戶反饋中提到的常見問題
3. 保留原模板的優勢
4. 提高輸出的準確性和專業性
5. 保持模板的參數和輸出格式不變

請提供:
1. 優化後的完整提示詞模板
2. 優化摘要，說明做了哪些改進及其理由

請以JSON格式回覆:
{{
  "template_id": "{template.get('template_id')}",
  "template_name": "{template.get('template_name')}",
  "template_version": "{float(template.get('template_version', 1.0)) + 0.1:.1f}",
  "task_type": "{template.get('task_type')}",
  "model_type": "{template.get('model_type')}",
  "prompt_template": "優化後的提示詞模板",
  "parameters": {json.dumps(template.get('parameters', []))},
  "expected_output_format": "{template.get('expected_output_format')}",
  "performance_metrics": {json.dumps(template.get('performance_metrics', {}))},
  "tags": {json.dumps(template.get('tags', []))},
  "optimization_summary": "優化摘要",
  "created_at": "{template.get('created_at')}",
  "updated_at": "當前時間戳"
}}
"""
        return prompt
    
    async def _call_claude_for_optimization(self, optimization_prompt: str, 
                                          original_template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """調用Claude API進行模板優化
        
        Args:
            optimization_prompt: 優化提示
            original_template: 原始模板
            
        Returns:
            優化後的模板或None（如果發生錯誤）
        """
        # 如果未提供Claude客戶端，嘗試導入並創建
        if not self.claude_client:
            try:
                from app.model_clients import ClaudeClient
                self.claude_client = ClaudeClient()
            except ImportError:
                logger.error("無法導入ClaudeClient")
                return None
        
        try:
            # 調用Claude API
            response = await self.claude_client.generate(optimization_prompt)
            
            # 從回應中提取JSON
            json_str = self._extract_json(response)
            if not json_str:
                logger.error("無法從Claude回應中提取JSON")
                return None
                
            # 解析JSON
            optimized_template = json.loads(json_str)
            
            # 驗證優化後的模板
            if not self._validate_optimized_template(optimized_template, original_template):
                logger.error("優化後的模板驗證失敗")
                return None
                
            return optimized_template
            
        except Exception as e:
            logger.error(f"調用Claude API進行模板優化時發生錯誤: {str(e)}")
            return None
    
    def _extract_json(self, text: str) -> Optional[str]:
        """從文本中提取JSON字符串
        
        Args:
            text: 可能包含JSON的文本
            
        Returns:
            提取的JSON字符串或None（如果未找到）
        """
        # 嘗試查找JSON開始和結束的位置
        start_pos = text.find('{')
        end_pos = text.rfind('}')
        
        if start_pos >= 0 and end_pos > start_pos:
            return text[start_pos:end_pos+1]
            
        return None
    
    def _validate_optimized_template(self, optimized_template: Dict[str, Any], 
                                   original_template: Dict[str, Any]) -> bool:
        """驗證優化後的模板
        
        Args:
            optimized_template: 優化後的模板
            original_template: 原始模板
            
        Returns:
            是否通過驗證
        """
        # 檢查必要字段
        required_fields = ["template_id", "prompt_template", "parameters"]
        for field in required_fields:
            if field not in optimized_template:
                logger.error(f"優化後的模板缺少必要字段: {field}")
                return False
        
        # 檢查模板ID是否一致
        if optimized_template["template_id"] != original_template["template_id"]:
            logger.error("優化後的模板ID與原始模板不一致")
            return False
        
        # 檢查參數是否一致
        if set(optimized_template["parameters"]) != set(original_template.get("parameters", [])):
            logger.error("優化後的模板參數與原始模板不一致")
            return False
        
        # 檢查輸出格式是否一致
        if optimized_template.get("expected_output_format") != original_template.get("expected_output_format"):
            logger.error("優化後的模板輸出格式與原始模板不一致")
            return False
        
        return True
    
    async def auto_optimize_templates(self) -> Dict[str, Any]:
        """自動優化所有需要優化的模板
        
        Returns:
            優化結果摘要
        """
        # 獲取所有模板
        all_templates = []
        
        # 添加提示詞模板
        for template_id in self.prompt_manager.templates["prompt_templates"]:
            all_templates.append(template_id)
            
        # 添加法律任務模板
        for task in self.prompt_manager.templates["legal_tasks"].values():
            if "templates" in task:
                for template in task["templates"]:
                    template_id = template.get("template_id")
                    if template_id:
                        all_templates.append(template_id)
        
        # 分析所有模板性能
        optimization_results = []
        for template_id in all_templates:
            performance = await self.analyze_template_performance(template_id)
            
            # 如果需要優化，進行優化
            if performance.get("needs_optimization", False):
                result = await self.optimize_template(template_id)
                optimization_results.append(result)
        
        # 生成摘要
        optimized_count = sum(1 for result in optimization_results if result.get("optimized", False))
        
        return {
            "total_templates": len(all_templates),
            "analyzed_templates": len(all_templates),
            "templates_needing_optimization": len(optimization_results),
            "templates_optimized": optimized_count,
            "optimization_results": optimization_results
        }
