import logging
import json
import asyncio
import httpx
import hashlib
from typing import Dict, Any, List, Optional, Union, Tuple
from anthropic import Anthropic
from anthropic.types import MessageParam

from app.config import (
    CLAUDE_API_KEY, 
    TAIWAN_LLM_API_KEY, 
    TAIWAN_LLM_API_URL,
    HUGGINGFACE_API_KEY,
    CLAUDE_MODEL,
    TAIWAN_LLM_MODEL,
    MAX_TOKENS_CLAUDE,
    MAX_TOKENS_TAIWAN_LLM
)

logger = logging.getLogger(__name__)

# 簡單內存緩存實現
class SimpleCache:
    """簡單的內存緩存實現"""
    
    def __init__(self, ttl=3600):
        """初始化緩存

        Args:
            ttl: 緩存生存時間(秒)
        """
        self.cache = {}
        self.ttl = ttl
        self.timestamps = {}
    
    def get(self, key):
        """獲取緩存值

        Args:
            key: 緩存鍵

        Returns:
            Any: 緩存值或None
        """
        if key not in self.cache:
            return None
        
        # 檢查過期
        timestamp = self.timestamps.get(key, 0)
        if timestamp + self.ttl < asyncio.get_event_loop().time():
            # 已過期
            del self.cache[key]
            del self.timestamps[key]
            return None
            
        return self.cache[key]
    
    def set(self, key, value):
        """設置緩存值

        Args:
            key: 緩存鍵
            value: 緩存值
        """
        self.cache[key] = value
        self.timestamps[key] = asyncio.get_event_loop().time()
    
    def clear(self):
        """清空緩存"""
        self.cache.clear()
        self.timestamps.clear()


class TaiwanLLMClient:
    """Taiwan LLM API客戶端 - 使用HuggingFace API和Llama-3-Taiwan-8B-Instruct模型"""
    
    def __init__(
        self, 
        api_key: str = HUGGINGFACE_API_KEY, 
        api_url: str = TAIWAN_LLM_API_URL,
        model: str = TAIWAN_LLM_MODEL,
        max_tokens: int = MAX_TOKENS_TAIWAN_LLM
    ):
        """初始化Taiwan LLM客戶端

        Args:
            api_key: HuggingFace API密鑰
            api_url: API端點URL
            model: 使用的模型名稱
            max_tokens: 最大生成令牌數
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.max_tokens = max_tokens
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.max_retries = 3
        self.base_delay = 2  # 初始重試延遲(秒)
        self.cache = SimpleCache()  # 添加緩存
        self.cache_enabled = True
        
        if not api_key:
            logger.warning("未設置HuggingFace API密鑰")
    
    async def generate(self, prompt: str, max_tokens: Optional[int] = None, cache_key: Optional[str] = None) -> str:
        """生成文本回應

        Args:
            prompt: 提示詞
            max_tokens: 可選的最大生成令牌數，覆蓋默認值
            cache_key: 可選的緩存鍵，如果提供則啟用緩存

        Returns:
            str: 模型生成的回應文本
        """
        # 生成緩存鍵
        if self.cache_enabled and cache_key is None and len(prompt) > 0:
            cache_key = hashlib.md5(prompt.encode()).hexdigest()
        
        # 檢查緩存
        if self.cache_enabled and cache_key:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"使用緩存結果 (key: {cache_key[:8]}...)")
                return cached_result
        
        # 模擬模式
        if self.api_key == "mock_key" or not self.api_key:
            logger.warning("使用模擬模式，返回預設回應")
            result = MOCK_RESPONSES.get("default_analysis", "{}")
            
            # 緩存結果
            if self.cache_enabled and cache_key:
                self.cache.set(cache_key, result)
                
            return result
            
        max_tokens = max_tokens or self.max_tokens
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.95,
                "do_sample": True
            }
        }
        
        # 使用指數退避進行重試
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:  # 增加超時時間
                    response = await client.post(
                        self.api_url,
                        headers=self.headers,
                        json=payload
                    )
                    
                    # 檢查HTTP狀態碼
                    response.raise_for_status()
                    
                    # HuggingFace API返回格式解析
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get("generated_text", "")
                    elif isinstance(result, dict):
                        generated_text = result.get("generated_text", "")
                    else:
                        generated_text = str(result)
                    
                    # 緩存結果
                    if self.cache_enabled and cache_key:
                        self.cache.set(cache_key, generated_text)
                    
                    return generated_text
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Taiwan LLM API請求失敗 (嘗試 {attempt+1}/{self.max_retries}): HTTP {e.response.status_code}")
                
                # 處理特定HTTP錯誤
                if e.response.status_code == 429:  # 速率限制
                    delay = self.base_delay * (2 ** attempt)  # 指數退避
                    logger.info(f"達到速率限制，等待 {delay} 秒後重試")
                    await asyncio.sleep(delay)
                    continue
                elif e.response.status_code >= 500:  # 服務器錯誤
                    if attempt < self.max_retries - 1:
                        delay = self.base_delay * (2 ** attempt)
                        logger.info(f"服務器錯誤，等待 {delay} 秒後重試")
                        await asyncio.sleep(delay)
                        continue
                
                # 其他HTTP錯誤
                raise Exception(f"Taiwan LLM API錯誤: {str(e)}")
                
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                logger.error(f"Taiwan LLM API連接錯誤 (嘗試 {attempt+1}/{self.max_retries}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.info(f"連接錯誤，等待 {delay} 秒後重試")
                    await asyncio.sleep(delay)
                    continue
                
                raise Exception(f"無法連接到Taiwan LLM API: {str(e)}")
                
            except Exception as e:
                logger.error(f"Taiwan LLM調用時發生未知錯誤: {str(e)}")
                raise
        
        # 如果所有重試都失敗
        raise Exception(f"所有Taiwan LLM API請求嘗試均失敗")
    
    async def analyze_contract(self, clauses: List[Dict[str, str]]) -> Dict[str, Any]:
        """分析合同條款並識別風險

        Args:
            clauses: 合同條款列表

        Returns:
            Dict: 包含分析結果的字典
        """
        if len(clauses) > 5:
            # 對於較大的合約，使用批量處理
            return await self.analyze_contract_batch(clauses)
            
        # 格式化條款為提示的一部分
        formatted_clauses = ""
        for clause in clauses:
            formatted_clauses += f"{clause['id']}: {clause['text']}\n\n"
        
        # 使用8B模型優化的簡化提示模板
        prompt = f"""您是台灣法律專家，請分析以下合約條款的風險:

合同條款:
{formatted_clauses}

請提供:
1. 每個條款的潛在風險
2. 風險嚴重程度(高/中/低)
3. 相關法律依據
4. 改進建議

請以JSON格式輸出:
{{
  "analysis": [
    {{
      "clause_id": "條款ID",
      "clause_text": "條款原文",
      "risks": [
        {{
          "risk_description": "風險描述",
          "severity": "風險嚴重程度",
          "legal_basis": "法律依據",
          "recommendation": "改進建議"
        }}
      ]
    }}
  ],
  "summary": {{
    "high_risks_count": 高風險數量,
    "medium_risks_count": 中風險數量,
    "low_risks_count": 低風險數量,
    "overall_risk_assessment": "總體風險評估"
  }}
}}
"""
        
        # 生成緩存鍵
        cache_key = f"contract_{','.join([c['id'] for c in clauses])}"
        
        # 調用API生成分析
        response_text = await self.generate(prompt, cache_key=cache_key)
        
        # 嘗試解析JSON
        try:
            # 去除可能的前綴或後綴文本(模型可能會在JSON前後添加說明)
            json_str = self._extract_json(response_text)
            analysis_result = json.loads(json_str)
            return analysis_result
        except json.JSONDecodeError as e:
            logger.error(f"無法解析Taiwan LLM回應為JSON: {str(e)}")
            logger.debug(f"原始回應: {response_text}")
            
            # 返回錯誤信息而不是引發異常，這樣整個流程不會中斷
            return {
                "error": "無法解析模型回應為JSON格式",
                "raw_response": response_text
            }
    
    async def analyze_contract_batch(self, clauses: List[Dict[str, str]], batch_size: int = 3) -> Dict[str, Any]:
        """批量處理合同條款分析

        Args:
            clauses: 全部合同條款列表
            batch_size: 每批處理的條款數量

        Returns:
            Dict: 綜合分析結果
        """
        logger.info(f"使用批量處理分析合同，共{len(clauses)}個條款，批次大小={batch_size}")
        
        # 分批處理
        batches = []
        for i in range(0, len(clauses), batch_size):
            batch = clauses[i:i+batch_size]
            batches.append(batch)
        
        # 並行處理每個批次
        batch_results = []
        for i, batch in enumerate(batches):
            logger.info(f"處理批次 {i+1}/{len(batches)}，包含{len(batch)}個條款")
            result = await self.analyze_contract(batch)
            batch_results.append(result)
            
            # 如果不是最後一個批次，添加短暫延遲避免API限流
            if i < len(batches) - 1:
                await asyncio.sleep(1.0)
        
        # 合併結果
        return self._merge_batch_results(batch_results)
    
    def _merge_batch_results(self, batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合併批量處理結果

        Args:
            batch_results: 各批次分析結果列表

        Returns:
            Dict: 合併後的結果
        """
        # 檢查是否有錯誤結果
        error_results = [r for r in batch_results if "error" in r]
        if error_results:
            logger.warning(f"批量處理中有{len(error_results)}/{len(batch_results)}個批次出錯")
        
        # 初始化合併結果
        merged_analysis = []
        high_risks = 0
        medium_risks = 0
        low_risks = 0
        
        # 合併分析結果
        for result in batch_results:
            if "error" in result:
                continue
                
            analysis_list = result.get("analysis", [])
            merged_analysis.extend(analysis_list)
            
            # 合併風險計數
            summary = result.get("summary", {})
            high_risks += summary.get("high_risks_count", 0)
            medium_risks += summary.get("medium_risks_count", 0)
            low_risks += summary.get("low_risks_count", 0)
        
        # 生成整體風險評估
        risk_level = "低"
        if high_risks > 0:
            risk_level = "高"
        elif medium_risks > 0:
            risk_level = "中"
            
        overall_assessment = f"此合約共有{high_risks}個高風險項、{medium_risks}個中風險項和{low_risks}個低風險項，整體風險等級為{risk_level}級。"
        
        # 構建最終結果
        return {
            "analysis": merged_analysis,
            "summary": {
                "high_risks_count": high_risks,
                "medium_risks_count": medium_risks,
                "low_risks_count": low_risks,
                "overall_risk_assessment": overall_assessment
            }
        }
    
    def _extract_json(self, text: str) -> str:
        """從文本中提取JSON字符串

        Args:
            text: 可能包含JSON的文本

        Returns:
            str: 提取的JSON字符串
        """
        # 嘗試查找JSON開始和結束的位置
        start_pos = text.find('{')
        end_pos = text.rfind('}')
        
        if start_pos >= 0 and end_pos > start_pos:
            return text[start_pos:end_pos+1]
        
        # 如果找不到JSON格式，返回原始文本
        return text


class ClaudeClient:
    """Anthropic Claude API客戶端"""
    
    def __init__(
        self,
        api_key: str = CLAUDE_API_KEY,
        model: str = CLAUDE_MODEL,
        max_tokens: int = MAX_TOKENS_CLAUDE
    ):
        """初始化Claude客戶端

        Args:
            api_key: Anthropic API密鑰
            model: 使用的模型名稱
            max_tokens: 最大生成令牌數
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.client = Anthropic(api_key=api_key) if api_key else None
        self.cache = SimpleCache()  # 添加緩存
        self.cache_enabled = True
        
        if not api_key:
            logger.warning("未設置Anthropic API密鑰")
    
    async def generate(self, prompt: str, max_tokens: Optional[int] = None, cache_key: Optional[str] = None) -> str:
        """生成文本回應

        Args:
            prompt: 提示詞
            max_tokens: 可選的最大生成令牌數，覆蓋默認值
            cache_key: 可選的緩存鍵，如果提供則啟用緩存

        Returns:
            str: 模型生成的回應文本
        """
        # 生成緩存鍵
        if self.cache_enabled and cache_key is None and len(prompt) > 0:
            cache_key = hashlib.md5(prompt.encode()).hexdigest()
        
        # 檢查緩存
        if self.cache_enabled and cache_key:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"使用緩存結果 (key: {cache_key[:8]}...)")
                return cached_result
        
        # 模擬模式
        if self.api_key == "mock_key" or not self.api_key or not self.client:
            logger.warning("使用模擬模式，返回預設回應")
            result = MOCK_RESPONSES.get("default_evaluation", "{}")
            
            # 緩存結果
            if self.cache_enabled and cache_key:
                self.cache.set(cache_key, result)
                
            return result
            
        max_tokens = max_tokens or self.max_tokens
        
        # 準備消息
        message = MessageParam(
            role="user",
            content=prompt
        )
        
        try:
            # 使用asyncio.to_thread可以在不阻塞的情況下調用同步API
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=max_tokens,
                messages=[message]
            )
            
            result = response.content[0].text
            
            # 緩存結果
            if self.cache_enabled and cache_key:
                self.cache.set(cache_key, result)
                
            return result
            
        except Exception as e:
            logger.error(f"Claude API調用錯誤: {str(e)}")
            raise Exception(f"Claude API調用失敗: {str(e)}")
    
    async def evaluate_analysis(self, analysis: Dict[str, Any], clauses: List[Dict[str, str]]) -> Dict[str, Any]:
        """評估由Taiwan LLM生成的分析結果

        Args:
            analysis: Taiwan LLM生成的分析結果
            clauses: 原始合同條款列表

        Returns:
            Dict: 包含評估結果的字典
        """
        # 檢查analysis是否有錯誤
        if "error" in analysis:
            logger.warning("無法評估存在錯誤的分析結果")
            return {
                "quality_score": 0,
                "feedback": "無法評估，台灣模型分析產生錯誤",
                "needs_improvement": True
            }
            
        # 確保clauses為非空
        if not clauses:
            return {
                "quality_score": 0,
                "feedback": "無法評估，未提供合同條款",
                "needs_improvement": False
            }
            
        # 格式化原始條款和分析結果
        formatted_clauses = ""
        for clause in clauses:
            formatted_clauses += f"{clause['id']}: {clause['text']}\n\n"
            
        # 將分析結果轉為字符串
        analysis_str = json.dumps(analysis, ensure_ascii=False, indent=2)
        
        # 構建評估提示
        prompt = f"""作為台灣法律專家，請評估以下合同條款分析的品質和準確性。

原始合同條款:
{formatted_clauses}

分析結果:
{analysis_str}

請評估:
1. 分析品質 (滿分10分)
2. 識別了哪些風險
3. 可能漏掉了哪些重要風險
4. 風險嚴重程度評估是否合理
5. 是否需要補充或修正

請用JSON格式回覆:
{{
  "quality_score": 評分(1-10),
  "feedback": "詳細反饋意見",
  "missing_risks": [
    {{
      "clause_id": "條款ID",
      "risk_description": "漏掉的風險描述",
      "severity": "風險嚴重程度"
    }}
  ],
  "improvement_suggestions": "具體改進建議",
  "needs_improvement": true/false
}}
"""
        
        # 生成緩存鍵
        cache_key = f"evaluation_{','.join([c['id'] for c in clauses])}"
        
        # 調用Claude API進行評估
        response_text = await self.generate(prompt, cache_key=cache_key)
        
        # 嘗試解析JSON
        try:
            # 去除可能的前綴或後綴文本
            json_str = self._extract_json(response_text)
            evaluation_result = json.loads(json_str)
            return evaluation_result
        except json.JSONDecodeError as e:
            logger.error(f"無法解析Claude回應為JSON: {str(e)}")
            logger.debug(f"原始回應: {response_text}")
            
            # 返回錯誤信息
            return {
                "quality_score": 5,
                "feedback": "無法解析評估結果為JSON格式，但已完成評估",
                "needs_improvement": True,
                "raw_response": response_text
            }
    
    async def improve_analysis(self, original_analysis: Dict[str, Any], evaluation: Dict[str, Any], clauses: List[Dict[str, str]]) -> Dict[str, Any]:
        """基於評估結果改進分析

        Args:
            original_analysis: 原始分析結果
            evaluation: 評估結果
            clauses: 原始合同條款

        Returns:
            Dict: 改進後的分析結果
        """
        # 檢查是否有原始分析或評估
        if "error" in original_analysis or not evaluation:
            logger.warning("無法改進分析，缺少有效的原始分析或評估")
            return original_analysis
            
        # 如果評估顯示不需要改進，直接返回原始分析
        if not evaluation.get("needs_improvement", False):
            logger.info("評估顯示分析無需改進")
            return original_analysis
            
        # 格式化條款
        formatted_clauses = ""
        for clause in clauses:
            formatted_clauses += f"{clause['id']}: {clause['text']}\n\n"
            
        # 將原始分析和評估轉為字符串
        original_analysis_str = json.dumps(original_analysis, ensure_ascii=False, indent=2)
        evaluation_str = json.dumps(evaluation, ensure_ascii=False, indent=2)
        
        # 構建改進提示
        prompt = f"""作為台灣法律專家，請根據評估反饋，改進以下合同條款的分析。

原始合同條款:
{formatted_clauses}

原始分析:
{original_analysis_str}

評估反饋:
{evaluation_str}

請提供改進後的完整分析，修正漏洞，增加遺漏的風險，並優化建議。
請使用與原始分析相同的JSON格式，但內容應當更全面、更準確。
"""
        
        # 生成緩存鍵
        cache_key = f"improvement_{','.join([c['id'] for c in clauses])}"
        
        # 調用Claude API進行改進
        response_text = await self.generate(prompt, cache_key=cache_key)
        
        # 嘗試解析JSON
        try:
            # 去除可能的前綴或後綴文本
            json_str = self._extract_json(response_text)
            improved_analysis = json.loads(json_str)
            return improved_analysis
        except json.JSONDecodeError as e:
            logger.error(f"無法解析Claude改進回應為JSON: {str(e)}")
            logger.debug(f"原始回應: {response_text}")
            
            # 返回原始分析結果，而不是出錯
            return original_analysis
    
    def _extract_json(self, text: str) -> str:
        """從文本中提取JSON字符串

        Args:
            text: 可能包含JSON的文本

        Returns:
            str: 提取的JSON字符串
        """
        # 嘗試查找JSON開始和結束的位置
        start_pos = text.find('{')
        end_pos = text.rfind('}')
        
        if start_pos >= 0 and end_pos > start_pos:
            return text[start_pos:end_pos+1]
        
        # 如果找不到JSON格式，返回原始文本
        return text


# 預先準備的模擬回應，用於無API密鑰時測試
MOCK_RESPONSES = {
    "default_analysis": """
{
  "analysis": [
    {
      "clause_id": "1",
      "clause_text": "甲方可在任何時間單方面終止合約，無需提前通知。",
      "risks": [
        {
          "risk_description": "條款高度不平等，賦予甲方過大權力，乙方權益無保障",
          "severity": "高",
          "legal_basis": "民法第247條之1",
          "recommendation": "修改為雙方均需提前通知才能終止合約，並規定合理通知期限"
        }
      ]
    }
  ],
  "summary": {
    "high_risks_count": 1,
    "medium_risks_count": 0,
    "low_risks_count": 0,
    "overall_risk_assessment": "此合約存在高風險條款，建議謹慎處理"
  }
}
""",
    "default_evaluation": """
{
  "quality_score": 7,
  "feedback": "分析大致準確，但可以更詳細說明相關法規依據",
  "missing_risks": [],
  "improvement_suggestions": "加強法律依據的引用，並提供更具體的建議",
  "needs_improvement": true
}
"""
}
