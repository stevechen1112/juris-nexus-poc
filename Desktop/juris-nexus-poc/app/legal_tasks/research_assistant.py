"""
法律研究助手 - 協助進行法律研究和案例分析
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union

from app.prompt_engine.prompt_manager import PromptManager
from app.prompt_engine.template_selector import TemplateSelector
from app.model_clients import ClaudeClient, TaiwanLLMClient

logger = logging.getLogger(__name__)

class LegalResearchAssistant:
    """法律研究助手 - 協助進行法律研究和案例分析"""
    
    def __init__(self, prompt_manager: PromptManager, claude_client: ClaudeClient = None, 
                taiwan_llm_client: TaiwanLLMClient = None):
        """初始化法律研究助手
        
        Args:
            prompt_manager: 提示詞管理器
            claude_client: Claude客戶端（如果為None，將在需要時創建）
            taiwan_llm_client: Taiwan LLM客戶端（如果為None，將在需要時創建）
        """
        self.prompt_manager = prompt_manager
        self.template_selector = TemplateSelector(prompt_manager)
        self.claude_client = claude_client
        self.taiwan_llm_client = taiwan_llm_client
        
        # 如果未提供客戶端，創建它們
        if not self.claude_client:
            self.claude_client = ClaudeClient()
        if not self.taiwan_llm_client:
            self.taiwan_llm_client = TaiwanLLMClient()
    
    async def research_legal_topic(self, topic: str, background: str = None, 
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """研究法律主題
        
        Args:
            topic: 研究主題
            background: 背景信息（可選）
            context: 上下文信息（可選）
            
        Returns:
            研究結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "legal_research"
        
        # 準備參數
        parameters = {
            "legal_question": topic
        }
        
        if background:
            parameters["background"] = background
            
        # 合併上下文
        context.update(parameters)
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於法律研究任務")
            return {
                "error": "沒有找到適合的模板",
                "topic": topic
            }
            
        # 獲取模板ID
        template_id = template.get("template_id")
        
        # 格式化提示詞
        prompt = self.prompt_manager.format_prompt(template_id, parameters)
        if not prompt:
            logger.error(f"格式化提示詞失敗: {template_id}")
            return {
                "error": "格式化提示詞失敗",
                "template_id": template_id
            }
            
        # 根據模板的模型類型選擇客戶端
        model_type = template.get("model_type", "claude")
        client = self.claude_client if model_type == "claude" else self.taiwan_llm_client
        
        # 生成緩存鍵
        cache_key = f"legal_research_{topic}"
        
        # 調用模型生成研究結果
        try:
            response = await client.generate(prompt, cache_key=cache_key)
            
            # 根據預期輸出格式處理回應
            expected_format = template.get("expected_output_format", "text")
            
            if expected_format == "json":
                # 嘗試解析JSON
                try:
                    # 從回應中提取JSON
                    json_str = self._extract_json(response)
                    result = json.loads(json_str)
                    
                    # 添加元數據
                    result["metadata"] = {
                        "topic": topic,
                        "template_id": template_id,
                        "model_type": model_type
                    }
                    
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"無法解析回應為JSON: {str(e)}")
                    return {
                        "error": "無法解析回應為JSON",
                        "raw_response": response,
                        "topic": topic
                    }
            else:
                # 文本格式
                return {
                    "research_results": response,
                    "metadata": {
                        "topic": topic,
                        "template_id": template_id,
                        "model_type": model_type
                    }
                }
                
        except Exception as e:
            logger.error(f"生成研究結果時發生錯誤: {str(e)}")
            return {
                "error": f"生成研究結果時發生錯誤: {str(e)}",
                "topic": topic
            }
    
    async def find_relevant_cases(self, query: str, filters: Dict[str, Any] = None, 
                                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """查找相關案例
        
        Args:
            query: 查詢內容
            filters: 過濾條件（可選）
            context: 上下文信息（可選）
            
        Returns:
            相關案例列表
        """
        if context is None:
            context = {}
        if filters is None:
            filters = {}
            
        # 設置任務類型
        task_type = "legal_research"
        
        # 準備參數
        parameters = {
            "legal_question": f"請查找與以下問題相關的判例: {query}",
            "background": f"過濾條件: {json.dumps(filters, ensure_ascii=False)}"
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["case_law_research"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於案例查找任務")
            return {
                "error": "沒有找到適合的模板",
                "query": query
            }
            
        # 獲取模板ID
        template_id = template.get("template_id")
        
        # 格式化提示詞
        prompt = self.prompt_manager.format_prompt(template_id, parameters)
        if not prompt:
            logger.error(f"格式化提示詞失敗: {template_id}")
            return {
                "error": "格式化提示詞失敗",
                "template_id": template_id
            }
            
        # 根據模板的模型類型選擇客戶端
        model_type = template.get("model_type", "claude")
        client = self.claude_client if model_type == "claude" else self.taiwan_llm_client
        
        # 生成緩存鍵
        cache_key = f"case_search_{query}_{json.dumps(filters, ensure_ascii=False)}"
        
        # 調用模型查找案例
        try:
            response = await client.generate(prompt, cache_key=cache_key)
            
            # 根據預期輸出格式處理回應
            expected_format = template.get("expected_output_format", "text")
            
            if expected_format == "json":
                # 嘗試解析JSON
                try:
                    # 從回應中提取JSON
                    json_str = self._extract_json(response)
                    result = json.loads(json_str)
                    
                    # 添加元數據
                    result["metadata"] = {
                        "query": query,
                        "filters": filters,
                        "template_id": template_id,
                        "model_type": model_type
                    }
                    
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"無法解析回應為JSON: {str(e)}")
                    return {
                        "error": "無法解析回應為JSON",
                        "raw_response": response,
                        "query": query
                    }
            else:
                # 文本格式
                return {
                    "cases": response,
                    "metadata": {
                        "query": query,
                        "filters": filters,
                        "template_id": template_id,
                        "model_type": model_type
                    }
                }
                
        except Exception as e:
            logger.error(f"查找案例時發生錯誤: {str(e)}")
            return {
                "error": f"查找案例時發生錯誤: {str(e)}",
                "query": query
            }
    
    async def analyze_legal_document(self, document_text: str, analysis_type: str = "general", 
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析法律文件
        
        Args:
            document_text: 文件內容
            analysis_type: 分析類型（general, contract, judgment, legislation等）
            context: 上下文信息（可選）
            
        Returns:
            分析結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "legal_research"
        
        # 準備參數
        parameters = {
            "legal_question": f"請分析以下{analysis_type}類型的法律文件",
            "background": document_text
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["document_analysis"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於法律文件分析任務")
            return {
                "error": "沒有找到適合的模板",
                "analysis_type": analysis_type
            }
            
        # 獲取模板ID
        template_id = template.get("template_id")
        
        # 格式化提示詞
        prompt = self.prompt_manager.format_prompt(template_id, parameters)
        if not prompt:
            logger.error(f"格式化提示詞失敗: {template_id}")
            return {
                "error": "格式化提示詞失敗",
                "template_id": template_id
            }
            
        # 根據模板的模型類型選擇客戶端
        model_type = template.get("model_type", "claude")
        client = self.claude_client if model_type == "claude" else self.taiwan_llm_client
        
        # 生成緩存鍵
        document_hash = hashlib.md5(document_text.encode()).hexdigest()
        cache_key = f"document_analysis_{analysis_type}_{document_hash}"
        
        # 調用模型分析文件
        try:
            response = await client.generate(prompt, cache_key=cache_key)
            
            # 根據預期輸出格式處理回應
            expected_format = template.get("expected_output_format", "text")
            
            if expected_format == "json":
                # 嘗試解析JSON
                try:
                    # 從回應中提取JSON
                    json_str = self._extract_json(response)
                    result = json.loads(json_str)
                    
                    # 添加元數據
                    result["metadata"] = {
                        "analysis_type": analysis_type,
                        "template_id": template_id,
                        "model_type": model_type
                    }
                    
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"無法解析回應為JSON: {str(e)}")
                    return {
                        "error": "無法解析回應為JSON",
                        "raw_response": response,
                        "analysis_type": analysis_type
                    }
            else:
                # 文本格式
                return {
                    "analysis": response,
                    "metadata": {
                        "analysis_type": analysis_type,
                        "template_id": template_id,
                        "model_type": model_type
                    }
                }
                
        except Exception as e:
            logger.error(f"分析法律文件時發生錯誤: {str(e)}")
            return {
                "error": f"分析法律文件時發生錯誤: {str(e)}",
                "analysis_type": analysis_type
            }
    
    def _extract_json(self, text: str) -> str:
        """從文本中提取JSON字符串
        
        Args:
            text: 可能包含JSON的文本
            
        Returns:
            提取的JSON字符串
        """
        # 嘗試查找JSON開始和結束的位置
        start_pos = text.find('{')
        end_pos = text.rfind('}')
        
        if start_pos >= 0 and end_pos > start_pos:
            return text[start_pos:end_pos+1]
        
        # 如果沒有找到JSON，返回原始文本
        return text
