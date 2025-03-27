"""
提示詞管理器 - 負責加載、存儲和管理提示詞模板
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class PromptManager:
    """提示詞管理器 - 負責加載、存儲和管理提示詞模板"""
    
    def __init__(self, templates_dir: str = None):
        """初始化提示詞管理器
        
        Args:
            templates_dir: 模板目錄路徑，如果為None則使用默認路徑
        """
        if templates_dir is None:
            # 使用相對於應用根目錄的默認路徑
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.templates_dir = os.path.join(base_dir, "data", "templates")
        else:
            self.templates_dir = templates_dir
            
        # 模板緩存
        self.templates = {
            "prompt_templates": {},  # 基礎提示詞模板
            "legal_tasks": {}        # 法律任務模板
        }
        
        # 加載所有模板
        self.load_templates()
    
    def load_templates(self) -> None:
        """加載所有模板"""
        self._load_prompt_templates()
        self._load_legal_task_templates()
        logger.info(f"已加載 {len(self.templates['prompt_templates'])} 個提示詞模板和 {len(self.templates['legal_tasks'])} 個法律任務模板")
    
    def _load_prompt_templates(self) -> None:
        """加載基礎提示詞模板"""
        prompt_templates_dir = os.path.join(self.templates_dir, "prompt_templates")
        if not os.path.exists(prompt_templates_dir):
            logger.warning(f"提示詞模板目錄不存在: {prompt_templates_dir}")
            return
            
        for filename in os.listdir(prompt_templates_dir):
            if not filename.endswith(".json"):
                continue
                
            file_path = os.path.join(prompt_templates_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    
                # 將模板添加到緩存
                if "templates" in template_data:
                    for template in template_data["templates"]:
                        template_id = template.get("template_id")
                        if template_id:
                            self.templates["prompt_templates"][template_id] = template
                            logger.debug(f"已加載提示詞模板: {template_id}")
            except Exception as e:
                logger.error(f"加載提示詞模板文件失敗 {file_path}: {str(e)}")
    
    def _load_legal_task_templates(self) -> None:
        """加載法律任務模板"""
        legal_tasks_dir = os.path.join(self.templates_dir, "legal_tasks")
        if not os.path.exists(legal_tasks_dir):
            logger.warning(f"法律任務模板目錄不存在: {legal_tasks_dir}")
            return
            
        for filename in os.listdir(legal_tasks_dir):
            if not filename.endswith(".json"):
                continue
                
            file_path = os.path.join(legal_tasks_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                    
                # 將任務模板添加到緩存
                task_id = task_data.get("task_id")
                if task_id:
                    self.templates["legal_tasks"][task_id] = task_data
                    logger.debug(f"已加載法律任務模板: {task_id}")
            except Exception as e:
                logger.error(f"加載法律任務模板文件失敗 {file_path}: {str(e)}")
    
    def get_prompt_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """獲取特定提示詞模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板內容或None（如果不存在）
        """
        return self.templates["prompt_templates"].get(template_id)
    
    def get_legal_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """獲取特定法律任務模板
        
        Args:
            task_id: 任務ID
            
        Returns:
            任務模板內容或None（如果不存在）
        """
        return self.templates["legal_tasks"].get(task_id)
    
    def get_task_template(self, task_id: str, template_id: str) -> Optional[Dict[str, Any]]:
        """獲取特定法律任務中的特定模板
        
        Args:
            task_id: 任務ID
            template_id: 模板ID
            
        Returns:
            模板內容或None（如果不存在）
        """
        task = self.get_legal_task(task_id)
        if not task or "templates" not in task:
            return None
            
        for template in task["templates"]:
            if template.get("template_id") == template_id:
                return template
                
        return None
    
    def list_prompt_templates(self, tags: List[str] = None) -> List[Dict[str, Any]]:
        """列出所有提示詞模板，可選按標籤過濾
        
        Args:
            tags: 標籤列表，用於過濾模板
            
        Returns:
            符合條件的模板列表
        """
        if not tags:
            return list(self.templates["prompt_templates"].values())
            
        filtered_templates = []
        for template in self.templates["prompt_templates"].values():
            template_tags = template.get("tags", [])
            if any(tag in template_tags for tag in tags):
                filtered_templates.append(template)
                
        return filtered_templates
    
    def list_legal_tasks(self) -> List[Dict[str, Any]]:
        """列出所有法律任務
        
        Returns:
            法律任務列表
        """
        return list(self.templates["legal_tasks"].values())
    
    def save_prompt_template(self, template: Dict[str, Any]) -> bool:
        """保存或更新提示詞模板
        
        Args:
            template: 模板內容
            
        Returns:
            是否成功保存
        """
        template_id = template.get("template_id")
        if not template_id:
            logger.error("模板缺少template_id")
            return False
            
        # 更新緩存
        self.templates["prompt_templates"][template_id] = template
        
        # 確定保存位置
        template_type = template.get("task_type", "general")
        filename = f"{template_type}.json"
        file_path = os.path.join(self.templates_dir, "prompt_templates", filename)
        
        # 讀取現有文件（如果存在）
        existing_data = {"templates": []}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                logger.error(f"讀取現有模板文件失敗 {file_path}: {str(e)}")
        
        # 更新模板
        updated = False
        if "templates" in existing_data:
            for i, t in enumerate(existing_data["templates"]):
                if t.get("template_id") == template_id:
                    existing_data["templates"][i] = template
                    updated = True
                    break
            
            if not updated:
                existing_data["templates"].append(template)
        else:
            existing_data["templates"] = [template]
        
        # 保存到文件
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存提示詞模板: {template_id}")
            return True
        except Exception as e:
            logger.error(f"保存提示詞模板失敗 {file_path}: {str(e)}")
            return False
    
    def update_template_metrics(self, template_id: str, metrics_update: Dict[str, Any]) -> bool:
        """更新模板性能指標
        
        Args:
            template_id: 模板ID
            metrics_update: 要更新的指標
            
        Returns:
            是否成功更新
        """
        # 先查找是否為提示詞模板
        template = self.get_prompt_template(template_id)
        template_type = "prompt_templates"
        
        # 如果不是提示詞模板，檢查是否為法律任務中的模板
        if not template:
            for task_id, task in self.templates["legal_tasks"].items():
                if "templates" in task:
                    for t in task["templates"]:
                        if t.get("template_id") == template_id:
                            template = t
                            template_type = f"legal_tasks.{task_id}"
                            break
                    if template:
                        break
        
        if not template:
            logger.error(f"未找到模板: {template_id}")
            return False
        
        # 更新指標
        if "performance_metrics" not in template:
            template["performance_metrics"] = {}
            
        for key, value in metrics_update.items():
            template["performance_metrics"][key] = value
            
        # 更新時間戳
        template["performance_metrics"]["last_updated"] = datetime.datetime.now().isoformat()
        
        # 如果是提示詞模板，直接保存
        if template_type == "prompt_templates":
            return self.save_prompt_template(template)
        
        # 如果是法律任務中的模板，需要保存整個任務
        else:
            task_id = template_type.split(".")[1]
            task = self.get_legal_task(task_id)
            if not task:
                logger.error(f"未找到法律任務: {task_id}")
                return False
                
            # 更新任務中的模板
            for i, t in enumerate(task["templates"]):
                if t.get("template_id") == template_id:
                    task["templates"][i] = template
                    break
                    
            # 保存任務
            file_path = os.path.join(self.templates_dir, "legal_tasks", f"{task_id}.json")
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(task, f, ensure_ascii=False, indent=2)
                logger.info(f"已更新法律任務模板: {template_id}")
                return True
            except Exception as e:
                logger.error(f"更新法律任務模板失敗 {file_path}: {str(e)}")
                return False
    
    def format_prompt(self, template_id: str, parameters: Dict[str, Any]) -> Optional[str]:
        """使用參數格式化提示詞模板
        
        Args:
            template_id: 模板ID
            parameters: 參數字典
            
        Returns:
            格式化後的提示詞或None（如果模板不存在）
        """
        template = self.get_prompt_template(template_id)
        
        # 如果在提示詞模板中未找到，嘗試在法律任務模板中查找
        if not template:
            for task in self.templates["legal_tasks"].values():
                if "templates" in task:
                    for t in task["templates"]:
                        if t.get("template_id") == template_id:
                            template = t
                            break
                    if template:
                        break
        
        if not template or "prompt_template" not in template:
            logger.error(f"未找到模板或模板缺少prompt_template: {template_id}")
            return None
            
        prompt_template = template["prompt_template"]
        
        # 檢查是否所有必要參數都已提供
        required_params = template.get("parameters", [])
        missing_params = [param for param in required_params if param not in parameters]
        if missing_params:
            logger.error(f"缺少必要參數: {', '.join(missing_params)}")
            return None
            
        # 格式化提示詞
        try:
            formatted_prompt = prompt_template.format(**parameters)
            
            # 更新使用計數
            if "performance_metrics" in template:
                usage_count = template["performance_metrics"].get("usage_count", 0)
                self.update_template_metrics(template_id, {"usage_count": usage_count + 1})
                
            return formatted_prompt
        except KeyError as e:
            logger.error(f"格式化提示詞時發生錯誤，缺少參數: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"格式化提示詞時發生未知錯誤: {str(e)}")
            return None
