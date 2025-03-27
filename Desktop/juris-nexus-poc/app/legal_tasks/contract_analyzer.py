"""
合約分析器 - 專門分析合約條款和風險
"""

import json
import logging
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Union

from app.prompt_engine.prompt_manager import PromptManager
from app.prompt_engine.template_selector import TemplateSelector
from app.model_clients import ClaudeClient, TaiwanLLMClient, DualAIEngine

logger = logging.getLogger(__name__)

class ContractAnalyzer:
    """合約分析器 - 專門分析合約條款和風險"""
    
    def __init__(self, prompt_manager: PromptManager, claude_client: ClaudeClient = None,
                taiwan_llm_client: TaiwanLLMClient = None, dual_engine: DualAIEngine = None):
        """初始化合約分析器
        
        Args:
            prompt_manager: 提示詞管理器
            claude_client: Claude客戶端（如果為None，將在需要時創建）
            taiwan_llm_client: Taiwan LLM客戶端（如果為None，將在需要時創建）
            dual_engine: 雙AI引擎（如果為None，將在需要時創建）
        """
        self.prompt_manager = prompt_manager
        self.template_selector = TemplateSelector(prompt_manager)
        self.claude_client = claude_client
        self.taiwan_llm_client = taiwan_llm_client
        self.dual_engine = dual_engine
        
        # 如果未提供客戶端，創建它們
        if not self.claude_client:
            self.claude_client = ClaudeClient()
        if not self.taiwan_llm_client:
            self.taiwan_llm_client = TaiwanLLMClient()
        if not self.dual_engine:
            self.dual_engine = DualAIEngine(self.claude_client, self.taiwan_llm_client)
    
    async def analyze_contract_clauses(self, contract_text: str, 
                                    analysis_focus: List[str] = None,
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析合約條款
        
        Args:
            contract_text: 合約文本
            analysis_focus: 分析重點（可選）
            context: 上下文信息（可選）
            
        Returns:
            條款分析結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "contract_analysis"
        
        # 準備參數
        parameters = {
            "contract_text": contract_text
        }
        
        if analysis_focus:
            parameters["analysis_focus"] = ", ".join(analysis_focus)
            
        # 合併上下文
        context.update(parameters)
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於合約條款分析任務")
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
        contract_hash = hashlib.md5(contract_text.encode()).hexdigest()
        focus_hash = hashlib.md5(str(analysis_focus or "").encode()).hexdigest()
        cache_key = f"contract_analysis_{contract_hash[:8]}_{focus_hash[:8]}"
        
        # 根據模板的模型類型選擇客戶端
        model_type = template.get("model_type", "claude")
        client = self.claude_client if model_type == "claude" else self.taiwan_llm_client
        
        # 調用模型分析合約條款
        try:
            response = await client.generate(prompt, cache_key=cache_key)
            
            # 返回條款分析結果
            return {
                "clause_analysis": response,
                "metadata": {
                    "template_id": template_id,
                    "model_type": model_type
                }
            }
                
        except Exception as e:
            logger.error(f"分析合約條款時發生錯誤: {str(e)}")
            return {
                "error": f"分析合約條款時發生錯誤: {str(e)}"
            }
    
    async def identify_contract_risks(self, contract_text: str, 
                                   risk_types: List[str] = None,
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """識別合約風險
        
        Args:
            contract_text: 合約文本
            risk_types: 風險類型（可選）
            context: 上下文信息（可選）
            
        Returns:
            風險識別結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "contract_analysis"
        
        # 準備參數
        parameters = {
            "contract_text": contract_text,
            "analysis_focus": "風險識別"
        }
        
        if risk_types:
            parameters["risk_types"] = ", ".join(risk_types)
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["risk_analysis"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於合約風險識別任務")
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
        contract_hash = hashlib.md5(contract_text.encode()).hexdigest()
        risk_hash = hashlib.md5(str(risk_types or "").encode()).hexdigest()
        cache_key = f"contract_risks_{contract_hash[:8]}_{risk_hash[:8]}"
        
        # 根據模板的模型類型選擇客戶端
        model_type = template.get("model_type", "claude")
        client = self.claude_client if model_type == "claude" else self.taiwan_llm_client
        
        # 調用模型識別合約風險
        try:
            response = await client.generate(prompt, cache_key=cache_key)
            
            # 返回風險識別結果
            return {
                "risk_identification": response,
                "metadata": {
                    "template_id": template_id,
                    "model_type": model_type
                }
            }
                
        except Exception as e:
            logger.error(f"識別合約風險時發生錯誤: {str(e)}")
            return {
                "error": f"識別合約風險時發生錯誤: {str(e)}"
            }
    
    async def compare_contracts(self, contract_a: str, contract_b: str, 
                             focus_areas: List[str] = None,
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """比較合約
        
        Args:
            contract_a: 合約A文本
            contract_b: 合約B文本
            focus_areas: 重點比較領域（可選）
            context: 上下文信息（可選）
            
        Returns:
            合約比較結果
        """
        if context is None:
            context = {}
            
        # 構建合約比較提示
        focus_str = ""
        if focus_areas:
            focus_str = f"\n\n請特別關注以下領域的差異：\n" + "\n".join([f"- {area}" for area in focus_areas])
            
        prompt = f"""作為台灣合約法專家，請比較以下兩份合約：

合約A：
{contract_a}

合約B：
{contract_b}
{focus_str}

請提供：

1. 主要條款比較
   - 關鍵條款的異同
   - 條款措辭和結構差異
   - 條款效力差異

2. 權利義務比較
   - 各方權利的差異
   - 各方義務的差異
   - 責任分配的差異

3. 風險比較
   - 合約A特有風險
   - 合約B特有風險
   - 風險程度差異

4. 法律保障比較
   - 保障條款差異
   - 爭議解決機制差異
   - 違約救濟差異

5. 整體評估
   - 各自優勢
   - 各自劣勢
   - 綜合建議

請確保比較全面、客觀，並提供專業法律見解。
"""
            
        # 生成緩存鍵
        a_hash = hashlib.md5(contract_a.encode()).hexdigest()
        b_hash = hashlib.md5(contract_b.encode()).hexdigest()
        cache_key = f"contract_comparison_{a_hash[:8]}_{b_hash[:8]}"
        
        # 調用Claude API比較合約
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回合約比較結果
            return {
                "contract_comparison": response,
                "metadata": {
                    "focus_areas": focus_areas
                }
            }
                
        except Exception as e:
            logger.error(f"比較合約時發生錯誤: {str(e)}")
            return {
                "error": f"比較合約時發生錯誤: {str(e)}"
            }
    
    async def extract_key_terms(self, contract_text: str, 
                             term_types: List[str] = None,
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """提取關鍵條款
        
        Args:
            contract_text: 合約文本
            term_types: 條款類型（可選）
            context: 上下文信息（可選）
            
        Returns:
            關鍵條款提取結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "contract_analysis"
        
        # 準備參數
        parameters = {
            "contract_text": contract_text,
            "analysis_focus": "關鍵條款提取"
        }
        
        if term_types:
            parameters["term_types"] = ", ".join(term_types)
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["key_terms_extraction"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於關鍵條款提取任務")
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
        contract_hash = hashlib.md5(contract_text.encode()).hexdigest()
        terms_hash = hashlib.md5(str(term_types or "").encode()).hexdigest()
        cache_key = f"key_terms_{contract_hash[:8]}_{terms_hash[:8]}"
        
        # 根據模板的模型類型選擇客戶端
        model_type = template.get("model_type", "claude")
        client = self.claude_client if model_type == "claude" else self.taiwan_llm_client
        
        # 調用模型提取關鍵條款
        try:
            response = await client.generate(prompt, cache_key=cache_key)
            
            # 返回關鍵條款提取結果
            return {
                "key_terms": response,
                "metadata": {
                    "template_id": template_id,
                    "model_type": model_type
                }
            }
                
        except Exception as e:
            logger.error(f"提取關鍵條款時發生錯誤: {str(e)}")
            return {
                "error": f"提取關鍵條款時發生錯誤: {str(e)}"
            }
    
    async def suggest_contract_improvements(self, contract_text: str, 
                                         party_perspective: str = "balanced",
                                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """建議合約改進
        
        Args:
            contract_text: 合約文本
            party_perspective: 當事方視角（balanced, party_a, party_b）
            context: 上下文信息（可選）
            
        Returns:
            合約改進建議
        """
        if context is None:
            context = {}
            
        # 構建合約改進建議提示
        prompt = f"""作為台灣合約法專家，請分析以下合約並提供改進建議：

合約文本：
{contract_text}

分析視角：{party_perspective}

請提供：

1. 條款改進建議
   - 不明確條款的修改建議
   - 不平衡條款的修改建議
   - 缺失條款的補充建議

2. 風險防範建議
   - 現有風險的防範措施
   - 潛在風險的預防措施
   - 責任分配的優化建議

3. 法律保障增強
   - 權利保障的增強方式
   - 爭議解決機制的完善
   - 違約救濟的優化

4. 語言和結構優化
   - 語言表述的優化
   - 結構安排的改進
   - 格式規範的建議

5. 具體修改示例
   - 原條款文本
   - 建議修改文本
   - 修改理由說明

請確保建議專業、實用，並符合台灣合約法實務。
"""
            
        # 生成緩存鍵
        contract_hash = hashlib.md5(contract_text.encode()).hexdigest()
        perspective_hash = hashlib.md5(party_perspective.encode()).hexdigest()
        cache_key = f"contract_improvements_{contract_hash[:8]}_{perspective_hash[:8]}"
        
        # 調用Claude API建議合約改進
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回合約改進建議
            return {
                "improvement_suggestions": response,
                "metadata": {
                    "party_perspective": party_perspective
                }
            }
                
        except Exception as e:
            logger.error(f"建議合約改進時發生錯誤: {str(e)}")
            return {
                "error": f"建議合約改進時發生錯誤: {str(e)}"
            }
    
    async def analyze_with_dual_engine(self, contract_text: str, 
                                    analysis_focus: List[str] = None,
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用雙AI引擎分析合約
        
        Args:
            contract_text: 合約文本
            analysis_focus: 分析重點（可選）
            context: 上下文信息（可選）
            
        Returns:
            雙引擎分析結果
        """
        if context is None:
            context = {}
            
        # 將合約文本分割為條款
        clauses = self._split_contract_into_clauses(contract_text)
        
        # 準備條款對象列表
        clause_objects = []
        for i, clause in enumerate(clauses):
            clause_objects.append({
                "id": f"clause_{i+1}",
                "content": clause
            })
            
        # 設置分析參數
        analysis_params = {}
        if analysis_focus:
            analysis_params["focus_areas"] = analysis_focus
            
        # 使用雙AI引擎分析合約
        try:
            result = await self.dual_engine.analyze_contract(clause_objects, **analysis_params)
            return result
                
        except Exception as e:
            logger.error(f"使用雙AI引擎分析合約時發生錯誤: {str(e)}")
            return {
                "error": f"使用雙AI引擎分析合約時發生錯誤: {str(e)}"
            }
    
    def _split_contract_into_clauses(self, contract_text: str) -> List[str]:
        """將合約文本分割為條款
        
        Args:
            contract_text: 合約文本
            
        Returns:
            條款列表
        """
        # 簡單的條款分割邏輯
        # 實際應用中可能需要更複雜的分割邏輯
        
        # 嘗試按照常見的條款標記分割
        clauses = []
        
        # 嘗試按照「第X條」格式分割
        import re
        clause_pattern = r'第[一二三四五六七八九十百零0-9]+條'
        
        # 找到所有匹配的位置
        matches = list(re.finditer(clause_pattern, contract_text))
        
        if matches:
            # 如果找到匹配，按匹配位置分割
            for i in range(len(matches)):
                start = matches[i].start()
                end = matches[i+1].start() if i < len(matches) - 1 else len(contract_text)
                clauses.append(contract_text[start:end].strip())
        else:
            # 如果沒有找到匹配，嘗試按照數字編號分割
            number_pattern = r'\n\s*(\d+\.|\(\d+\)|\d+\)|\d+、)'
            matches = list(re.finditer(number_pattern, contract_text))
            
            if matches:
                for i in range(len(matches)):
                    start = matches[i].start()
                    end = matches[i+1].start() if i < len(matches) - 1 else len(contract_text)
                    clauses.append(contract_text[start:end].strip())
            else:
                # 如果仍然沒有找到匹配，按段落分割
                clauses = [p.strip() for p in contract_text.split('\n\n') if p.strip()]
        
        # 如果沒有成功分割，將整個合約作為一個條款
        if not clauses:
            clauses = [contract_text]
            
        return clauses
