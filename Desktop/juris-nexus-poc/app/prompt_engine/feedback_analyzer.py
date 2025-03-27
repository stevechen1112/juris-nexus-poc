"""
反饋分析器 - 分析用戶反饋，提取有用信息用於模板優化
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

from app.prompt_engine.prompt_manager import PromptManager
from app.learning_recorder import LearningRecorder

logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    """反饋分析器 - 分析用戶反饋，提取有用信息用於模板優化"""
    
    def __init__(self, prompt_manager: PromptManager, learning_recorder: LearningRecorder, claude_client=None):
        """初始化反饋分析器
        
        Args:
            prompt_manager: 提示詞管理器
            learning_recorder: 學習記錄器
            claude_client: Claude API客戶端（如果為None，將在需要時創建）
        """
        self.prompt_manager = prompt_manager
        self.learning_recorder = learning_recorder
        self.claude_client = claude_client
    
    async def analyze_feedback(self, template_id: str) -> Dict[str, Any]:
        """分析特定模板的反饋
        
        Args:
            template_id: 模板ID
            
        Returns:
            反饋分析結果
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
        
        if not feedback_data:
            return {
                "template_id": template_id,
                "template_name": template.get("template_name", "未命名模板"),
                "feedback_count": 0,
                "message": "沒有可用的反饋數據"
            }
        
        # 基本統計分析
        basic_stats = self._calculate_basic_stats(feedback_data)
        
        # 提取常見問題和優勢
        issues_strengths = self._extract_issues_and_strengths(feedback_data)
        
        # 提取改進建議
        improvement_suggestions = self._extract_improvement_suggestions(feedback_data)
        
        # 深度分析（使用Claude）
        deep_analysis = await self._perform_deep_analysis(template, feedback_data)
        
        return {
            "template_id": template_id,
            "template_name": template.get("template_name", "未命名模板"),
            "feedback_count": len(feedback_data),
            "basic_stats": basic_stats,
            "issues_and_strengths": issues_strengths,
            "improvement_suggestions": improvement_suggestions,
            "deep_analysis": deep_analysis
        }
    
    def _calculate_basic_stats(self, feedback_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """計算基本統計數據
        
        Args:
            feedback_data: 反饋數據列表
            
        Returns:
            基本統計結果
        """
        # 提取評分
        ratings = [feedback.get("rating", 0) for feedback in feedback_data if "rating" in feedback]
        
        # 計算平均評分和分布
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        rating_distribution = Counter(ratings)
        
        # 計算時間趨勢
        time_sorted_feedback = sorted(
            [f for f in feedback_data if "timestamp" in f],
            key=lambda x: x["timestamp"]
        )
        
        # 如果有足夠的數據，計算趨勢
        trend = "stable"
        if len(time_sorted_feedback) >= 5:
            early_ratings = [f.get("rating", 0) for f in time_sorted_feedback[:len(time_sorted_feedback)//2]]
            late_ratings = [f.get("rating", 0) for f in time_sorted_feedback[len(time_sorted_feedback)//2:]]
            
            early_avg = sum(early_ratings) / len(early_ratings) if early_ratings else 0
            late_avg = sum(late_ratings) / len(late_ratings) if late_ratings else 0
            
            if late_avg > early_avg + 0.5:
                trend = "improving"
            elif late_avg < early_avg - 0.5:
                trend = "declining"
        
        return {
            "average_rating": avg_rating,
            "rating_distribution": {str(k): v for k, v in rating_distribution.items()},
            "total_feedback": len(feedback_data),
            "trend": trend
        }
    
    def _extract_issues_and_strengths(self, feedback_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取常見問題和優勢
        
        Args:
            feedback_data: 反饋數據列表
            
        Returns:
            問題和優勢分析
        """
        # 提取問題和優勢
        all_issues = []
        all_strengths = []
        
        for feedback in feedback_data:
            issues = feedback.get("issues", [])
            strengths = feedback.get("strengths", [])
            
            if isinstance(issues, list):
                all_issues.extend(issues)
            if isinstance(strengths, list):
                all_strengths.extend(strengths)
        
        # 計算頻率
        issue_counter = Counter(all_issues)
        strength_counter = Counter(all_strengths)
        
        # 轉換為列表格式
        common_issues = [{"issue": issue, "count": count} 
                        for issue, count in issue_counter.most_common(10)]
        common_strengths = [{"strength": strength, "count": count} 
                           for strength, count in strength_counter.most_common(10)]
        
        return {
            "common_issues": common_issues,
            "common_strengths": common_strengths
        }
    
    def _extract_improvement_suggestions(self, feedback_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取改進建議
        
        Args:
            feedback_data: 反饋數據列表
            
        Returns:
            改進建議列表
        """
        suggestions = []
        
        for feedback in feedback_data:
            suggestion = feedback.get("improvement_suggestion")
            if suggestion and isinstance(suggestion, str) and len(suggestion) > 10:
                rating = feedback.get("rating", 0)
                timestamp = feedback.get("timestamp", "")
                
                suggestions.append({
                    "suggestion": suggestion,
                    "rating": rating,
                    "timestamp": timestamp
                })
        
        # 按評分排序（低評分的建議可能更有價值）
        return sorted(suggestions, key=lambda x: x["rating"])
    
    async def _perform_deep_analysis(self, template: Dict[str, Any], 
                                   feedback_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用Claude進行深度分析
        
        Args:
            template: 模板數據
            feedback_data: 反饋數據列表
            
        Returns:
            深度分析結果
        """
        # 如果未提供Claude客戶端，嘗試導入並創建
        if not self.claude_client:
            try:
                from app.model_clients import ClaudeClient
                self.claude_client = ClaudeClient()
            except ImportError:
                logger.error("無法導入ClaudeClient")
                return {"error": "無法訪問Claude API進行深度分析"}
        
        # 如果反饋數據太少，不進行深度分析
        if len(feedback_data) < 3:
            return {"message": "反饋數據不足，無法進行深度分析"}
        
        # 準備分析提示
        analysis_prompt = self._create_analysis_prompt(template, feedback_data)
        
        try:
            # 調用Claude API
            response = await self.claude_client.generate(analysis_prompt)
            
            # 從回應中提取JSON
            json_str = self._extract_json(response)
            if not json_str:
                logger.error("無法從Claude回應中提取JSON")
                return {"error": "無法解析Claude回應"}
                
            # 解析JSON
            analysis_result = json.loads(json_str)
            return analysis_result
            
        except Exception as e:
            logger.error(f"調用Claude API進行反饋分析時發生錯誤: {str(e)}")
            return {"error": f"分析過程中發生錯誤: {str(e)}"}
    
    def _create_analysis_prompt(self, template: Dict[str, Any], 
                              feedback_data: List[Dict[str, Any]]) -> str:
        """創建用於深度分析的提示
        
        Args:
            template: 模板數據
            feedback_data: 反饋數據列表
            
        Returns:
            分析提示
        """
        # 格式化反饋數據
        formatted_feedback = json.dumps(feedback_data, ensure_ascii=False, indent=2)
        
        # 構建分析提示
        prompt = f"""作為一位專精於台灣法律領域的AI反饋分析專家，請深入分析以下提示詞模板的用戶反饋數據。

模板信息:
模板ID: {template.get('template_id')}
模板名稱: {template.get('template_name')}
模板版本: {template.get('template_version')}
任務類型: {template.get('task_type')}

提示詞模板:
```
{template.get('prompt_template')}
```

用戶反饋數據:
{formatted_feedback}

請進行全面、深入的分析，包括但不限於:
1. 反饋模式和趨勢
2. 模板的主要優勢和不足
3. 用戶期望與實際效果的差距
4. 模板在法律專業性方面的表現
5. 具體的改進機會和建議
6. 模板優化的優先事項

請以JSON格式回覆:
{{
  "patterns_and_trends": {{
    "main_patterns": ["主要模式1", "主要模式2", ...],
    "feedback_trends": "反饋趨勢描述",
    "user_expectations": ["用戶期望1", "用戶期望2", ...]
  }},
  "strengths_and_weaknesses": {{
    "key_strengths": ["主要優勢1", "主要優勢2", ...],
    "key_weaknesses": ["主要不足1", "主要不足2", ...],
    "professional_legal_quality": "法律專業性評估"
  }},
  "improvement_opportunities": {{
    "high_priority_improvements": ["高優先級改進1", "高優先級改進2", ...],
    "medium_priority_improvements": ["中優先級改進1", "中優先級改進2", ...],
    "specific_suggestions": ["具體建議1", "具體建議2", ...]
  }},
  "optimization_strategy": {{
    "recommended_approach": "建議的優化方法",
    "expected_impact": "預期影響",
    "potential_risks": ["潛在風險1", "潛在風險2", ...]
  }}
}}
"""
        return prompt
    
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
    
    async def analyze_all_templates(self) -> Dict[str, Any]:
        """分析所有模板的反饋
        
        Returns:
            所有模板的反饋分析結果
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
        
        # 分析所有模板的反饋
        analysis_results = {}
        for template_id in all_templates:
            result = await self.analyze_feedback(template_id)
            analysis_results[template_id] = result
        
        # 生成摘要
        templates_with_feedback = sum(1 for r in analysis_results.values() if r.get("feedback_count", 0) > 0)
        
        return {
            "total_templates": len(all_templates),
            "templates_with_feedback": templates_with_feedback,
            "analysis_results": analysis_results
        }
