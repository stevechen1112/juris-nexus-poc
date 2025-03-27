"""
法律諮詢服務 - 提供法律諮詢和建議
"""

import json
import logging
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Union

from app.prompt_engine.prompt_manager import PromptManager
from app.prompt_engine.template_selector import TemplateSelector
from app.model_clients import ClaudeClient

logger = logging.getLogger(__name__)

class LegalConsultationService:
    """法律諮詢服務 - 提供法律諮詢和建議"""
    
    def __init__(self, prompt_manager: PromptManager, claude_client: ClaudeClient = None):
        """初始化法律諮詢服務
        
        Args:
            prompt_manager: 提示詞管理器
            claude_client: Claude客戶端（如果為None，將在需要時創建）
        """
        self.prompt_manager = prompt_manager
        self.template_selector = TemplateSelector(prompt_manager)
        self.claude_client = claude_client
        
        # 如果未提供客戶端，創建它
        if not self.claude_client:
            self.claude_client = ClaudeClient()
    
    async def provide_legal_advice(self, legal_question: str, client_information: str = None, 
                                 case_facts: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """提供法律建議
        
        Args:
            legal_question: 法律問題
            client_information: 客戶信息（可選）
            case_facts: 案件事實（可選）
            context: 上下文信息（可選）
            
        Returns:
            法律建議
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "legal_consultation"
        
        # 準備參數
        parameters = {
            "legal_question": legal_question
        }
        
        if client_information:
            parameters["client_information"] = client_information
        
        if case_facts:
            parameters["case_facts"] = case_facts
            
        # 合併上下文
        context.update(parameters)
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於法律諮詢任務")
            return {
                "error": "沒有找到適合的模板",
                "legal_question": legal_question
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
            
        # 生成緩存鍵
        question_hash = hashlib.md5(legal_question.encode()).hexdigest()
        facts_hash = hashlib.md5((case_facts or "").encode()).hexdigest()
        cache_key = f"legal_advice_{question_hash[:8]}_{facts_hash[:8]}"
        
        # 調用Claude API提供法律建議
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回法律建議
            return {
                "legal_advice": response,
                "metadata": {
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"提供法律建議時發生錯誤: {str(e)}")
            return {
                "error": f"提供法律建議時發生錯誤: {str(e)}",
                "legal_question": legal_question
            }
    
    async def analyze_legal_situation(self, situation_description: str, 
                                    legal_domain: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析法律情況
        
        Args:
            situation_description: 情況描述
            legal_domain: 法律領域（可選）
            context: 上下文信息（可選）
            
        Returns:
            法律情況分析結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "legal_consultation"
        
        # 準備參數
        parameters = {
            "legal_question": f"請分析以下法律情況",
            "case_facts": situation_description
        }
        
        if legal_domain:
            parameters["legal_domain"] = legal_domain
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["situation_analysis"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於法律情況分析任務")
            return {
                "error": "沒有找到適合的模板"
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
            
        # 生成緩存鍵
        situation_hash = hashlib.md5(situation_description.encode()).hexdigest()
        domain_hash = hashlib.md5((legal_domain or "").encode()).hexdigest()
        cache_key = f"situation_analysis_{situation_hash[:8]}_{domain_hash[:8]}"
        
        # 調用Claude API分析法律情況
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回法律情況分析結果
            return {
                "situation_analysis": response,
                "metadata": {
                    "legal_domain": legal_domain,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"分析法律情況時發生錯誤: {str(e)}")
            return {
                "error": f"分析法律情況時發生錯誤: {str(e)}"
            }
    
    async def explain_legal_concept(self, concept: str, detail_level: str = "standard", 
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """解釋法律概念
        
        Args:
            concept: 法律概念
            detail_level: 詳細程度（basic, standard, advanced）
            context: 上下文信息（可選）
            
        Returns:
            法律概念解釋
        """
        if context is None:
            context = {}
            
        # 構建法律概念解釋提示
        prompt = f"""作為台灣法律專家，請解釋以下法律概念：

法律概念：{concept}

詳細程度：{detail_level}

請提供：

1. 概念定義
   - 法律定義
   - 關鍵要素
   - 適用範圍

2. 法律依據
   - 相關法條
   - 重要判例
   - 學說見解

3. 實務應用
   - 常見情境
   - 適用方式
   - 實務爭議

4. 相關概念
   - 相似概念比較
   - 概念間關係
   - 概念區分

請根據詳細程度調整解釋深度：
- basic：適合法律初學者，使用簡單語言，避免過多專業術語
- standard：適合一般讀者，平衡專業性和可理解性
- advanced：適合法律專業人士，深入探討法理和爭議

請確保解釋準確、全面，並符合台灣法律體系。
"""
            
        # 生成緩存鍵
        concept_hash = hashlib.md5(concept.encode()).hexdigest()
        cache_key = f"concept_explanation_{concept_hash[:8]}_{detail_level}"
        
        # 調用Claude API解釋法律概念
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回法律概念解釋
            return {
                "concept_explanation": response,
                "metadata": {
                    "concept": concept,
                    "detail_level": detail_level
                }
            }
                
        except Exception as e:
            logger.error(f"解釋法律概念時發生錯誤: {str(e)}")
            return {
                "error": f"解釋法律概念時發生錯誤: {str(e)}",
                "concept": concept
            }
    
    async def analyze_legal_risk(self, situation_description: str, 
                              legal_domain: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析法律風險
        
        Args:
            situation_description: 情況描述
            legal_domain: 法律領域（可選）
            context: 上下文信息（可選）
            
        Returns:
            法律風險分析結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "legal_consultation"
        
        # 準備參數
        parameters = {
            "legal_question": f"請分析以下情況的法律風險",
            "case_facts": situation_description
        }
        
        if legal_domain:
            parameters["legal_domain"] = legal_domain
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["risk_analysis"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於法律風險分析任務")
            return {
                "error": "沒有找到適合的模板"
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
            
        # 生成緩存鍵
        situation_hash = hashlib.md5(situation_description.encode()).hexdigest()
        domain_hash = hashlib.md5((legal_domain or "").encode()).hexdigest()
        cache_key = f"risk_analysis_{situation_hash[:8]}_{domain_hash[:8]}"
        
        # 調用Claude API分析法律風險
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回法律風險分析結果
            return {
                "risk_analysis": response,
                "metadata": {
                    "legal_domain": legal_domain,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"分析法律風險時發生錯誤: {str(e)}")
            return {
                "error": f"分析法律風險時發生錯誤: {str(e)}"
            }
    
    async def provide_compliance_advice(self, business_scenario: str, 
                                     industry: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """提供合規建議
        
        Args:
            business_scenario: 業務場景
            industry: 行業（可選）
            context: 上下文信息（可選）
            
        Returns:
            合規建議
        """
        if context is None:
            context = {}
            
        # 構建合規建議提示
        prompt = f"""作為台灣法律合規專家，請為以下業務場景提供合規建議：

業務場景：
{business_scenario}

{f"行業：{industry}" if industry else ""}

請提供：

1. 適用法規識別
   - 主要適用法規
   - 次要適用法規
   - 相關行政規則

2. 合規要求分析
   - 核心合規要求
   - 行業特定要求
   - 最新法規變化

3. 合規風險評估
   - 高風險領域
   - 中風險領域
   - 低風險領域

4. 合規建議
   - 必要合規措施
   - 建議合規措施
   - 最佳實踐建議

5. 合規監控機制
   - 內部監控建議
   - 文件記錄要求
   - 定期審查建議

請確保建議全面、實用，並符合台灣最新法規要求。
"""
            
        # 生成緩存鍵
        scenario_hash = hashlib.md5(business_scenario.encode()).hexdigest()
        industry_hash = hashlib.md5((industry or "").encode()).hexdigest()
        cache_key = f"compliance_advice_{scenario_hash[:8]}_{industry_hash[:8]}"
        
        # 調用Claude API提供合規建議
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回合規建議
            return {
                "compliance_advice": response,
                "metadata": {
                    "industry": industry
                }
            }
                
        except Exception as e:
            logger.error(f"提供合規建議時發生錯誤: {str(e)}")
            return {
                "error": f"提供合規建議時發生錯誤: {str(e)}"
            }
    
    async def handle_conversation(self, conversation_history: List[Dict[str, str]], 
                               new_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """處理多輪對話
        
        Args:
            conversation_history: 對話歷史
            new_message: 新消息
            context: 上下文信息（可選）
            
        Returns:
            回應
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "legal_consultation"
        
        # 準備對話歷史字符串
        history_str = ""
        for msg in conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            history_str += f"{role}: {content}\n\n"
            
        # 準備參數
        parameters = {
            "conversation_history": history_str,
            "new_message": new_message
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["conversation"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於對話任務")
            return {
                "error": "沒有找到適合的模板"
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
            
        # 生成緩存鍵
        message_hash = hashlib.md5(new_message.encode()).hexdigest()
        history_hash = hashlib.md5(history_str.encode()).hexdigest()
        cache_key = f"conversation_{message_hash[:8]}_{history_hash[:8]}"
        
        # 調用Claude API處理對話
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回回應
            return {
                "response": response,
                "metadata": {
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"處理對話時發生錯誤: {str(e)}")
            return {
                "error": f"處理對話時發生錯誤: {str(e)}"
            }
