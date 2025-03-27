"""
模板選擇器 - 根據任務類型和上下文選擇最合適的提示詞模板
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

from app.prompt_engine.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class TemplateSelector:
    """模板選擇器 - 根據任務類型和上下文選擇最合適的提示詞模板"""
    
    def __init__(self, prompt_manager: PromptManager):
        """初始化模板選擇器
        
        Args:
            prompt_manager: 提示詞管理器
        """
        self.prompt_manager = prompt_manager
    
    def select_template(self, task_type: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """選擇最合適的模板
        
        Args:
            task_type: 任務類型
            context: 上下文信息（可選）
            
        Returns:
            選擇的模板或None（如果沒有合適的模板）
        """
        # 如果沒有提供上下文，初始化為空字典
        if context is None:
            context = {}
        
        # 首先檢查是否有對應的法律任務
        legal_task = self.prompt_manager.get_legal_task(task_type)
        if legal_task:
            return self._select_from_legal_task(legal_task, context)
        
        # 如果沒有對應的法律任務，從基礎提示詞模板中選擇
        return self._select_from_prompt_templates(task_type, context)
    
    def _select_from_legal_task(self, legal_task: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """從法律任務中選擇模板
        
        Args:
            legal_task: 法律任務
            context: 上下文信息
            
        Returns:
            選擇的模板或None（如果沒有合適的模板）
        """
        if "templates" not in legal_task or not legal_task["templates"]:
            logger.warning(f"法律任務 {legal_task.get('task_id')} 沒有可用的模板")
            return None
        
        # 如果上下文中指定了模板ID，直接使用
        if "template_id" in context:
            specified_template_id = context["template_id"]
            for template in legal_task["templates"]:
                if template.get("template_id") == specified_template_id:
                    logger.info(f"使用指定的模板: {specified_template_id}")
                    return template
            
            logger.warning(f"指定的模板 {specified_template_id} 在法律任務 {legal_task.get('task_id')} 中不存在")
        
        # 根據上下文選擇最合適的模板
        return self._rank_templates(legal_task["templates"], context)
    
    def _select_from_prompt_templates(self, task_type: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """從基礎提示詞模板中選擇
        
        Args:
            task_type: 任務類型
            context: 上下文信息
            
        Returns:
            選擇的模板或None（如果沒有合適的模板）
        """
        # 如果上下文中指定了模板ID，直接使用
        if "template_id" in context:
            specified_template_id = context["template_id"]
            template = self.prompt_manager.get_prompt_template(specified_template_id)
            if template:
                logger.info(f"使用指定的模板: {specified_template_id}")
                return template
            
            logger.warning(f"指定的模板 {specified_template_id} 不存在")
        
        # 篩選出與任務類型匹配的模板
        matching_templates = []
        for template in self.prompt_manager.templates["prompt_templates"].values():
            if template.get("task_type") == task_type:
                matching_templates.append(template)
        
        if not matching_templates:
            logger.warning(f"沒有找到與任務類型 {task_type} 匹配的模板")
            return None
        
        # 根據上下文選擇最合適的模板
        return self._rank_templates(matching_templates, context)
    
    def _rank_templates(self, templates: List[Dict[str, Any]], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """根據上下文對模板進行排名
        
        Args:
            templates: 候選模板列表
            context: 上下文信息
            
        Returns:
            排名最高的模板或None（如果沒有模板）
        """
        if not templates:
            return None
        
        # 計算每個模板的分數
        scored_templates = []
        for template in templates:
            score = self._calculate_template_score(template, context)
            scored_templates.append((template, score))
        
        # 按分數降序排序
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        
        # 返回分數最高的模板
        best_template = scored_templates[0][0]
        logger.info(f"選擇了模板: {best_template.get('template_id')} (分數: {scored_templates[0][1]})")
        return best_template
    
    def _calculate_template_score(self, template: Dict[str, Any], context: Dict[str, Any]) -> float:
        """計算模板與上下文的匹配分數
        
        Args:
            template: 模板
            context: 上下文信息
            
        Returns:
            匹配分數
        """
        score = 0.0
        
        # 1. 基礎分數 - 所有模板的起始分數
        score += 1.0
        
        # 2. 參數匹配分數 - 檢查模板所需的參數是否都在上下文中
        template_params = template.get("parameters", [])
        if template_params:
            available_params = sum(1 for param in template_params if param in context)
            param_ratio = available_params / len(template_params)
            score += param_ratio * 2.0
        
        # 3. 模型類型匹配分數 - 如果上下文指定了模型類型，檢查是否匹配
        if "model_type" in context and "model_type" in template:
            if context["model_type"] == template["model_type"]:
                score += 1.5
        
        # 4. 輸出格式匹配分數 - 如果上下文指定了輸出格式，檢查是否匹配
        if "output_format" in context and "expected_output_format" in template:
            if context["output_format"] == template["expected_output_format"]:
                score += 1.0
        
        # 5. 標籤匹配分數 - 檢查上下文中的標籤是否與模板標籤匹配
        if "tags" in context and "tags" in template:
            context_tags = context["tags"] if isinstance(context["tags"], list) else [context["tags"]]
            template_tags = template["tags"] if isinstance(template["tags"], list) else [template["tags"]]
            
            matching_tags = sum(1 for tag in context_tags if tag in template_tags)
            if matching_tags > 0:
                score += matching_tags * 0.5
        
        # 6. 性能指標分數 - 優先選擇性能較好的模板
        if "performance_metrics" in template:
            metrics = template["performance_metrics"]
            
            # 平均評分
            avg_rating = metrics.get("average_quality_score", 0)
            if avg_rating > 0:
                score += min(avg_rating / 10.0, 1.0) * 1.5
            
            # 使用次數（優先選擇經過更多測試的模板）
            usage_count = metrics.get("usage_count", 0)
            if usage_count > 0:
                score += min(usage_count / 100.0, 1.0) * 0.5
        
        # 7. 特殊上下文處理
        # 如果上下文中有"with_knowledge_base"標誌，優先選擇RAG模板
        if context.get("with_knowledge_base", False) and "tags" in template:
            if "rag" in template["tags"] or "context_aware" in template["tags"]:
                score += 2.0
        
        # 如果上下文中有"conversation_history"，優先選擇對話模板
        if "conversation_history" in context and "tags" in template:
            if "dialogue" in template["tags"] or "qa" in template["tags"]:
                score += 2.0
        
        # 如果上下文中有"domain"（專業領域），優先選擇該領域的專業模板
        if "domain" in context and "tags" in template:
            domain = context["domain"]
            if domain in template["tags"] or f"{domain}_law" in template["tags"]:
                score += 2.0
        
        return score
    
    def get_template_parameters(self, template: Dict[str, Any]) -> List[str]:
        """獲取模板所需的參數列表
        
        Args:
            template: 模板
            
        Returns:
            參數列表
        """
        return template.get("parameters", [])
    
    def list_available_templates(self, task_type: str = None, tags: List[str] = None) -> List[Dict[str, Any]]:
        """列出可用的模板
        
        Args:
            task_type: 任務類型（可選）
            tags: 標籤列表（可選）
            
        Returns:
            符合條件的模板列表
        """
        templates = []
        
        # 收集所有模板
        all_templates = []
        
        # 添加提示詞模板
        for template in self.prompt_manager.templates["prompt_templates"].values():
            all_templates.append(template)
        
        # 添加法律任務模板
        for task in self.prompt_manager.templates["legal_tasks"].values():
            if "templates" in task:
                all_templates.extend(task["templates"])
        
        # 過濾模板
        for template in all_templates:
            # 如果指定了任務類型，檢查是否匹配
            if task_type and template.get("task_type") != task_type:
                continue
            
            # 如果指定了標籤，檢查是否匹配
            if tags:
                template_tags = template.get("tags", [])
                if not any(tag in template_tags for tag in tags):
                    continue
            
            # 添加到結果列表
            templates.append({
                "template_id": template.get("template_id"),
                "template_name": template.get("template_name"),
                "task_type": template.get("task_type"),
                "model_type": template.get("model_type"),
                "parameters": template.get("parameters", []),
                "expected_output_format": template.get("expected_output_format"),
                "tags": template.get("tags", [])
            })
        
        return templates
