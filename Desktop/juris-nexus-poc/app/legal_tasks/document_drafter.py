"""
法律文件草擬助手 - 協助草擬各類法律文件
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

class LegalDocumentDrafter:
    """法律文件草擬助手 - 協助草擬各類法律文件"""
    
    def __init__(self, prompt_manager: PromptManager, claude_client: ClaudeClient = None):
        """初始化法律文件草擬助手
        
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
    
    async def draft_contract(self, contract_type: str, requirements: str, 
                           party_information: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """草擬合同
        
        Args:
            contract_type: 合同類型
            requirements: 合同需求
            party_information: 當事人信息（可選）
            context: 上下文信息（可選）
            
        Returns:
            草擬的合同
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "document_drafting"
        
        # 準備參數
        parameters = {
            "contract_type": contract_type,
            "requirements": requirements
        }
        
        if party_information:
            parameters["party_information"] = party_information
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["contract", "document_generation", "drafting"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於合同草擬任務")
            return {
                "error": "沒有找到適合的模板",
                "contract_type": contract_type
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
        cache_key = f"contract_draft_{contract_type}_{hashlib.md5(requirements.encode()).hexdigest()}"
        
        # 調用Claude API草擬合同
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回草擬的合同
            return {
                "contract": response,
                "metadata": {
                    "contract_type": contract_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"草擬合同時發生錯誤: {str(e)}")
            return {
                "error": f"草擬合同時發生錯誤: {str(e)}",
                "contract_type": contract_type
            }
    
    async def draft_legal_opinion(self, case_type: str, case_facts: str, 
                                legal_questions: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """草擬法律意見書
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            legal_questions: 法律問題
            context: 上下文信息（可選）
            
        Returns:
            草擬的法律意見書
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "document_drafting"
        
        # 準備參數
        parameters = {
            "case_type": case_type,
            "case_facts": case_facts,
            "legal_questions": legal_questions
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["legal_opinion", "document_generation", "drafting"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於法律意見書草擬任務")
            return {
                "error": "沒有找到適合的模板",
                "case_type": case_type
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
        facts_hash = hashlib.md5(case_facts.encode()).hexdigest()
        questions_hash = hashlib.md5(legal_questions.encode()).hexdigest()
        cache_key = f"legal_opinion_{case_type}_{facts_hash[:8]}_{questions_hash[:8]}"
        
        # 調用Claude API草擬法律意見書
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回草擬的法律意見書
            return {
                "legal_opinion": response,
                "metadata": {
                    "case_type": case_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"草擬法律意見書時發生錯誤: {str(e)}")
            return {
                "error": f"草擬法律意見書時發生錯誤: {str(e)}",
                "case_type": case_type
            }
    
    async def draft_litigation_document(self, document_type: str, case_type: str, 
                                      case_facts: str, party_information: str,
                                      claims: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """草擬訴訟文件
        
        Args:
            document_type: 文件類型（如起訴狀、答辯狀等）
            case_type: 案件類型
            case_facts: 案件事實
            party_information: 當事人信息
            claims: 請求事項（可選）
            context: 上下文信息（可選）
            
        Returns:
            草擬的訴訟文件
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "document_drafting"
        
        # 準備參數
        parameters = {
            "document_type": document_type,
            "case_type": case_type,
            "case_facts": case_facts,
            "party_information": party_information
        }
        
        if claims:
            parameters["claims"] = claims
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["litigation", "document_generation", "drafting"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於訴訟文件草擬任務")
            return {
                "error": "沒有找到適合的模板",
                "document_type": document_type,
                "case_type": case_type
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
        facts_hash = hashlib.md5(case_facts.encode()).hexdigest()
        party_hash = hashlib.md5(party_information.encode()).hexdigest()
        cache_key = f"litigation_doc_{document_type}_{case_type}_{facts_hash[:8]}_{party_hash[:8]}"
        
        # 調用Claude API草擬訴訟文件
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回草擬的訴訟文件
            return {
                "litigation_document": response,
                "metadata": {
                    "document_type": document_type,
                    "case_type": case_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"草擬訴訟文件時發生錯誤: {str(e)}")
            return {
                "error": f"草擬訴訟文件時發生錯誤: {str(e)}",
                "document_type": document_type,
                "case_type": case_type
            }
    
    async def draft_administrative_document(self, document_type: str, case_type: str, 
                                         case_facts: str, party_information: str,
                                         administrative_decision: str = None, 
                                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """草擬行政文件
        
        Args:
            document_type: 文件類型（如訴願書、行政訴訟狀等）
            case_type: 案件類型
            case_facts: 案件事實
            party_information: 當事人信息
            administrative_decision: 原行政處分（可選）
            context: 上下文信息（可選）
            
        Returns:
            草擬的行政文件
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "document_drafting"
        
        # 準備參數
        parameters = {
            "document_type": document_type,
            "case_type": case_type,
            "case_facts": case_facts,
            "party_information": party_information
        }
        
        if administrative_decision:
            parameters["administrative_decision"] = administrative_decision
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["administrative", "document_generation", "drafting"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於行政文件草擬任務")
            return {
                "error": "沒有找到適合的模板",
                "document_type": document_type,
                "case_type": case_type
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
        facts_hash = hashlib.md5(case_facts.encode()).hexdigest()
        party_hash = hashlib.md5(party_information.encode()).hexdigest()
        cache_key = f"admin_doc_{document_type}_{case_type}_{facts_hash[:8]}_{party_hash[:8]}"
        
        # 調用Claude API草擬行政文件
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回草擬的行政文件
            return {
                "administrative_document": response,
                "metadata": {
                    "document_type": document_type,
                    "case_type": case_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"草擬行政文件時發生錯誤: {str(e)}")
            return {
                "error": f"草擬行政文件時發生錯誤: {str(e)}",
                "document_type": document_type,
                "case_type": case_type
            }
    
    async def revise_document(self, document_type: str, original_document: str, 
                           revision_instructions: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """修改法律文件
        
        Args:
            document_type: 文件類型
            original_document: 原始文件
            revision_instructions: 修改指示
            context: 上下文信息（可選）
            
        Returns:
            修改後的文件
        """
        if context is None:
            context = {}
            
        # 構建修改提示
        prompt = f"""作為台灣法律專家，請根據以下指示修改法律文件：

文件類型：{document_type}

原始文件：
{original_document}

修改指示：
{revision_instructions}

請提供完整的修改後文件，保持專業法律格式和用語。請確保修改符合台灣法律規範和實務標準。
"""
            
        # 生成緩存鍵
        doc_hash = hashlib.md5(original_document.encode()).hexdigest()
        instr_hash = hashlib.md5(revision_instructions.encode()).hexdigest()
        cache_key = f"doc_revision_{document_type}_{doc_hash[:8]}_{instr_hash[:8]}"
        
        # 調用Claude API修改文件
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回修改後的文件
            return {
                "revised_document": response,
                "metadata": {
                    "document_type": document_type
                }
            }
                
        except Exception as e:
            logger.error(f"修改法律文件時發生錯誤: {str(e)}")
            return {
                "error": f"修改法律文件時發生錯誤: {str(e)}",
                "document_type": document_type
            }
    
    async def evaluate_document(self, document_type: str, document_text: str, 
                             evaluation_criteria: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """評估法律文件
        
        Args:
            document_type: 文件類型
            document_text: 文件內容
            evaluation_criteria: 評估標準（可選）
            context: 上下文信息（可選）
            
        Returns:
            評估結果
        """
        if context is None:
            context = {}
            
        # 構建評估提示
        if not evaluation_criteria:
            evaluation_criteria = """
1. 法律準確性
2. 結構完整性
3. 語言清晰度
4. 專業術語使用
5. 法律論證邏輯性
6. 潛在風險和漏洞
"""
            
        prompt = f"""作為台灣法律專家，請評估以下法律文件：

文件類型：{document_type}

文件內容：
{document_text}

評估標準：
{evaluation_criteria}

請提供詳細的評估報告，包括：
1. 各評估標準的得分（1-10分）和具體評價
2. 文件的優點和亮點
3. 需要改進的地方和具體建議
4. 潛在的法律風險和問題
5. 整體評估和總結

請確保評估專業、客觀、全面，並提供具體的改進建議。
"""
            
        # 生成緩存鍵
        doc_hash = hashlib.md5(document_text.encode()).hexdigest()
        cache_key = f"doc_evaluation_{document_type}_{doc_hash[:8]}"
        
        # 調用Claude API評估文件
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回評估結果
            return {
                "evaluation": response,
                "metadata": {
                    "document_type": document_type
                }
            }
                
        except Exception as e:
            logger.error(f"評估法律文件時發生錯誤: {str(e)}")
            return {
                "error": f"評估法律文件時發生錯誤: {str(e)}",
                "document_type": document_type
            }
