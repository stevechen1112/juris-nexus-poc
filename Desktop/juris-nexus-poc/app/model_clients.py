import logging
import json
import asyncio
import httpx
import hashlib
import datetime
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
    MAX_TOKENS_TAIWAN_LLM,
    MOCK_TAIWAN_LLM,
    MOCK_CLAUDE,
    USE_MOCK_MODE
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
        max_tokens: int = MAX_TOKENS_TAIWAN_LLM,
        use_mock: bool = MOCK_TAIWAN_LLM
    ):
        """初始化Taiwan LLM客戶端

        Args:
            api_key: HuggingFace API密鑰
            api_url: API端點URL
            model: 使用的模型名稱
            max_tokens: 最大生成令牌數
            use_mock: 是否使用模擬模式
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.max_tokens = max_tokens
        self.use_mock = use_mock
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.max_retries = 3
        self.base_delay = 2  # 初始重試延遲(秒)
        self.cache = SimpleCache()  # 添加緩存
        self.cache_enabled = True
        
        # 檢查是否應該使用模擬模式
        if self.use_mock:
            logger.info("Taiwan LLM 客戶端已配置為使用模擬模式")
            self.api_key = "mock_key"
        elif not api_key:
            logger.warning("未設置HuggingFace API密鑰，將使用模擬模式")
            self.api_key = "mock_key"
            self.use_mock = True
    
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
        
        # 確保 API URL 是有效的
        api_url = self.api_url
        if not api_url.startswith(('http://', 'https://')):
            api_url = f"https://{api_url}"
            logger.info(f"已添加 HTTPS 協議到 API URL: {api_url}")
        
        # 檢查 API URL 是否包含 "your_taiwan_llm_api_url"（未設置的預設值）
        if "your_taiwan_llm_api_url" in api_url:
            api_url = "https://api.huggingface.co/models/yentinglin/Llama-3-Taiwan-8B-Instruct"
            logger.info(f"使用默認的 Taiwan LLM API URL: {api_url}")
        
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
                        api_url,
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
            except httpx.RequestError as e:
                logger.error(f"Taiwan LLM API連接錯誤 (嘗試 {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.info(f"連接錯誤，等待 {delay} 秒後重試")
                    await asyncio.sleep(delay)
                else:
                    raise Exception(f"無法連接到Taiwan LLM API: {str(e)}")
        
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
        prompt = f"""您是台灣法律專家，請分析以下合約條款的風險：

合同條款：
{formatted_clauses}

請提供：
1. 每個條款的潛在風險
2. 風險嚴重程度(高/中/低)
3. 相關法律依據
4. 改進建議

請以JSON格式輸出：
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

    async def improve_with_feedback(
        self,
        original_analysis: Dict[str, Any],
        feedback: Dict[str, Any],
        clauses: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """基於專家反饋改進合同分析
        
        Args:
            original_analysis: 原始分析結果
            feedback: 專家反饋
            clauses: 合同條款列表

        Returns:
            Dict: 改進後的分析結果
        """
        # 如果原始分析有錯誤或反饋不完整，直接返回原始分析
        if "error" in original_analysis or not feedback:
            return original_analysis
            
        # 準備條款文本
        clauses_text = "\n\n".join([f"{c['id']}: {c['text']}" for c in clauses])
        
        # 將原始分析和反饋轉換為JSON字符串
        original_analysis_json = json.dumps(original_analysis, ensure_ascii=False, indent=2)
        feedback_json = json.dumps(feedback, ensure_ascii=False, indent=2)
        
        # 構建改進提示
        prompt = f"""
作為台灣法律專家，請根據專家反饋意見改進合同分析結果。

【原始合同條款】
{clauses_text}

【原始分析結果】
{original_analysis_json}

【專家反饋】
{feedback_json}

請仔細分析專家反饋，重點關注：
1. 專家指出的弱點和不足之處
2. 專家建議的改進方向
3. 需要重點加強的分析領域

請提供改進後的完整分析結果，修正不足之處，同時保留原始分析中專家認可的優點。
回覆必須使用與原始分析相同的JSON格式，確保包含所有必要字段。分析應更加全面、專業，並且直接回覆JSON格式結果。
"""
        
        # 生成緩存鍵
        cache_key = f"improve_feedback_{feedback.get('feedback_id', '')}"
        
        # 調用模型生成改進分析
        try:
            response_text = await self.generate(prompt, cache_key=cache_key)
            
            # 提取JSON部分
            start_pos = response_text.find('{')
            end_pos = response_text.rfind('}')
            
            if start_pos >= 0 and end_pos > start_pos:
                json_str = response_text[start_pos:end_pos+1]
                improved_analysis = json.loads(json_str)
                
                # 添加改進元數據
                if "metadata" not in improved_analysis:
                    improved_analysis["metadata"] = {}
                    
                improved_analysis["metadata"]["improved_by_expert_feedback"] = True
                improved_analysis["metadata"]["feedback_id"] = feedback.get("feedback_id", "")
                improved_analysis["metadata"]["taiwan_llm_improvement"] = True
                improved_analysis["metadata"]["improvement_timestamp"] = datetime.datetime.now().isoformat()
                
                return improved_analysis
            else:
                logger.error("Taiwan LLM回應中找不到有效的JSON")
                return original_analysis
                
        except Exception as e:
            logger.error(f"Taiwan LLM改進分析失敗: {str(e)}")
            return {
                **original_analysis,
                "metadata": {
                    **(original_analysis.get("metadata", {})),
                    "improvement_error": f"Taiwan LLM改進失敗: {str(e)}",
                    "feedback_applied": False
                }
            }


class ClaudeClient:
    """Anthropic Claude API客戶端"""
    
    def __init__(
        self,
        api_key: str = CLAUDE_API_KEY,
        model: str = CLAUDE_MODEL,
        max_tokens: int = MAX_TOKENS_CLAUDE,
        use_mock: bool = MOCK_CLAUDE
    ):
        """初始化Claude客戶端

        Args:
            api_key: Anthropic API密鑰
            model: 使用的模型名稱
            max_tokens: 最大生成令牌數
            use_mock: 是否使用模擬模式
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.use_mock = use_mock
        
        # 檢查是否應該使用模擬模式
        if self.use_mock:
            logger.info("Claude 客戶端已配置為使用模擬模式")
            self.api_key = "mock_key"
            self.client = None
        # 檢查 API 密鑰格式
        elif api_key and api_key.startswith("sk-"):
            # 檢查是否包含預設值（未設置的情況）
            if "your_claude_api_key" in api_key:
                logger.warning("使用的是預設 API 密鑰，將使用模擬模式")
                self.api_key = "mock_key"
                self.client = None
                self.use_mock = True
            else:
                try:
                    self.client = Anthropic(api_key=api_key)
                    logger.info(f"成功初始化 Claude API 客戶端，使用模型: {model}")
                except Exception as e:
                    logger.error(f"初始化 Claude API 客戶端時出錯: {str(e)}")
                    logger.warning("由於初始化錯誤，將使用模擬模式")
                    self.client = None
                    self.use_mock = True
        else:
            logger.warning("未提供有效的 Anthropic API 密鑰，將使用模擬模式")
            self.client = None
            self.use_mock = True
            
        self.cache = SimpleCache()  # 添加緩存
        self.cache_enabled = True
    
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
            error_msg = str(e)
            if "invalid x-api-key" in error_msg.lower():
                logger.error(f"Claude API 密鑰無效: {error_msg}")
                raise Exception(f"Claude API 密鑰無效，請檢查您的 API 密鑰設置")
            else:
                logger.error(f"Claude API調用錯誤: {error_msg}")
                raise Exception(f"Claude API調用失敗: {error_msg}")
    
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

原始合同條款：
{formatted_clauses}

分析結果：
{analysis_str}

請評估：
1. 分析品質 (滿分10分)
2. 識別了哪些風險
3. 可能漏掉了哪些重要風險
4. 風險嚴重程度評估是否合理
5. 是否需要補充或修正

請用JSON格式回覆：
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

原始合同條款：
{formatted_clauses}

原始分析：
{original_analysis_str}

評估反饋：
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

    async def improve_analysis_with_feedback(
        self,
        original_analysis: Dict[str, Any],
        clauses: List[Dict[str, str]],
        feedback: Dict[str, Any],
        priority_areas: List[str] = None
    ) -> Dict[str, Any]:
        """基於專家反饋改進分析

        Args:
            original_analysis: 原始分析結果
            clauses: 原始合同條款
            feedback: 專家反饋分析
            priority_areas: 優先改進領域

        Returns:
            Dict: 改進後的分析結果
        """
        # 檢查是否有原始分析或反饋
        if "error" in original_analysis or not feedback:
            logger.warning("無法基於專家反饋改進分析，缺少有效的原始分析或反饋")
            return original_analysis
            
        # 格式化條款
        formatted_clauses = ""
        for clause in clauses:
            formatted_clauses += f"{clause['id']}: {clause['text']}\n\n"
            
        # 將原始分析和反饋轉為字符串
        original_analysis_str = json.dumps(original_analysis, ensure_ascii=False, indent=2)
        feedback_str = json.dumps(feedback, ensure_ascii=False, indent=2)
        
        # 構建優先領域部分
        priority_areas_text = ""
        if priority_areas and len(priority_areas) > 0:
            priority_areas_text = f"優先改進領域:\n" + "\n".join([f"- {area}" for area in priority_areas])
        
        # 構建改進提示
        prompt = f"""作為台灣法律專家，請根據專家反饋，改進以下合同條款的分析。

原始合同條款：
{formatted_clauses}

原始分析：
{original_analysis_str}

專家反饋：
{feedback_str}

{priority_areas_text}

請基於專家反饋提供改進後的完整分析，特別關注以下方面：
1. 修正專家指出的弱點和不足
2. 添加專家建議的改進
3. 保留專家認為的優勢

如果專家反饋中包含可行的改進建議，請確保在改進版本中充分反映。
請使用與原始分析相同的JSON格式，但內容應當根據專家反饋進行改進。
"""
        
        # 生成緩存鍵
        cache_key = f"expert_improvement_{feedback.get('feedback_id', '')}"
        
        # 調用Claude API進行改進
        response_text = await self.generate(prompt, cache_key=cache_key)
        
        # 嘗試解析JSON
        try:
            # 去除可能的前綴或後綴文本
            json_str = self._extract_json(response_text)
            improved_analysis = json.loads(json_str)
            
            # 添加改進元數據
            improved_analysis["metadata"] = improved_analysis.get("metadata", {})
            improved_analysis["metadata"]["improved_by_expert_feedback"] = True
            improved_analysis["metadata"]["feedback_id"] = feedback.get("feedback_id", "")
            improved_analysis["metadata"]["improvement_timestamp"] = datetime.datetime.now().isoformat()
            
            return improved_analysis
        except json.JSONDecodeError as e:
            logger.error(f"無法解析Claude專家反饋改進回應為JSON: {str(e)}")
            logger.debug(f"原始回應: {response_text}")
            
            # 返回原始分析結果，而不是出錯
            return {
                **original_analysis,
                "metadata": {
                    **(original_analysis.get("metadata", {})),
                    "improvement_error": f"無法解析改進結果: {str(e)}",
                    "feedback_applied": False
                }
            }


# 預先準備的模擬回應，用於無API密鑰時測試
MOCK_RESPONSES = {
    "default_analysis": """
{
  "analysis": [
    {
      "clause_id": "1",
      "risks": [
        {
          "description": "付款條款不明確，未規定逾期付款的處理方式",
          "severity": "中",
          "legal_basis": "民法第229條"
        }
      ],
      "recommendations": "建議明確規定付款期限、逾期利息及違約金"
    },
    {
      "clause_id": "2",
      "risks": [
        {
          "description": "保密義務過於寬泛，可能難以執行",
          "severity": "中",
          "legal_basis": "營業秘密法第2條、第10條"
        }
      ],
      "recommendations": "建議明確定義保密資訊範圍，並設定合理的保密期限"
    }
  ],
  "overall_risk_level": "中",
  "summary": "合約整體風險中等，主要問題在於付款條款不明確和保密義務過於寬泛"
}
""",
    "default_evaluation": """
{
  "quality_score": 7,
  "feedback": "分析大致準確，但可以更詳細說明相關法規依據",
  "missing_risks": [],
  "improvement_areas": ["法規引用可更完整", "風險評估可更具體"],
  "needs_improvement": true
}
""",
    "legal_research": """
台灣的法律體系是以成文法為主的大陸法系，主要受德國和日本法律影響。其基本架構包括：

1. 憲法：國家最高法律，規定國家組織、人民權利義務等基本原則
2. 法律：由立法院制定，規範各領域的具體法律關係
3. 命令：由行政機關依法律授權制定的規範
4. 自治法規：地方政府制定的法規

司法體系方面，台灣採三級三審制：
- 地方法院（一審）
- 高等法院（二審）
- 最高法院（三審）

此外還有專業法院如行政法院、智慧財產法院等。

台灣法律的主要法典包括民法、刑法、民事訴訟法、刑事訴訟法、行政法等。近年來，台灣法律持續現代化，增加了消費者保護法、個人資料保護法等新興法律領域。
""",
    "contract_analysis": """
{
  "analysis": [
    {
      "clause_id": "1",
      "title": "服務範圍",
      "risks": [
        {
          "description": "服務範圍定義不明確，可能導致後續爭議",
          "severity": "高",
          "legal_basis": "民法第153條契約解釋原則"
        }
      ],
      "recommendations": "建議明確列舉服務項目，並說明哪些服務需額外付費"
    },
    {
      "clause_id": "2",
      "title": "付款條件",
      "risks": [
        {
          "description": "付款條件未規定逾期付款的處理方式",
          "severity": "中",
          "legal_basis": "民法第229條遲延責任"
        }
      ],
      "recommendations": "建議明確規定付款期限、逾期利息及違約金"
    },
    {
      "clause_id": "3",
      "title": "保密條款",
      "risks": [
        {
          "description": "保密義務期限過長（10年），可能不合理",
          "severity": "中",
          "legal_basis": "營業秘密法第10條、公平交易法第19條"
        }
      ],
      "recommendations": "建議將保密期限縮短至3-5年，或針對不同類型資訊設定不同期限"
    },
    {
      "clause_id": "4",
      "title": "智慧財產權",
      "risks": [
        {
          "description": "未明確規定委託開發之智慧財產權歸屬",
          "severity": "高",
          "legal_basis": "著作權法第11條、專利法第7條"
        }
      ],
      "recommendations": "建議明確約定智慧財產權歸屬及授權範圍"
    },
    {
      "clause_id": "5",
      "title": "終止條款",
      "risks": [
        {
          "description": "終止通知期過短（7天），可能無法妥善處理交接",
          "severity": "中",
          "legal_basis": "民法第263條"
        }
      ],
      "recommendations": "建議延長終止通知期至30天，並明確規定終止後的交接義務"
    }
  ],
  "overall_risk_level": "中高",
  "summary": "合約整體風險中高，主要問題在於服務範圍不明確、智慧財產權歸屬未明確規定，以及終止條款通知期過短。建議修改上述條款以降低風險。"
}
""",
    "legal_consultation": """
關於您詢問的勞資爭議問題，根據台灣《勞動基準法》的規定，我可以提供以下法律意見：

1. 加班費計算：
   - 法律依據：勞基法第24條
   - 平日加班前2小時，按平日每小時工資加給1/3計算
   - 平日加班第3小時起，按平日每小時工資加給2/3計算
   - 休息日工作，按平日每小時工資加給1/3計算（前2小時）及加給2/3計算（第3小時起）

2. 特休未休完的處理：
   - 法律依據：勞基法第38條
   - 特休應於年度終結或契約終止前休畢
   - 雇主應發給未休日數之工資

3. 不當解僱的救濟途徑：
   - 可向當地勞工局申訴
   - 可申請勞資爭議調解
   - 可向法院提起訴訟，主張資遣費、預告工資或非法解僱之損害賠償

建議您保留相關證據（如工時紀錄、薪資單、通訊紀錄等），並儘快向當地勞工局申請勞資爭議調解。調解不成時，再考慮提起訴訟。

此外，您可以尋求工會協助或委託律師代理，以保障自身權益。
""",
    "document_drafting": """
台北地方法院民事庭　　　　　　　　　　起訴狀

原告：王大明
    國民身分證統一編號：A123456789
    住：台北市中正區忠孝東路一段1號
    電話：02-12345678
    
被告：台灣某某股份有限公司
    統一編號：12345678
    設：台北市信義區信義路五段7號
    代表人：張董事長
    
訴訟標的金額：新台幣50萬元整

民事訴訟費用：新台幣9,000元整（已依法繳納，收據附後）

訴訟類別：請求給付貨款事件

壹、聲明：
一、被告應給付原告新台幣50萬元整，及自起訴狀繕本送達翌日起至清償日止，按年息5%計算之利息。
二、訴訟費用由被告負擔。
三、願供擔保，請准宣告假執行。

貳、事實及理由：
一、原告於民國112年1月1日與被告簽訂買賣契約（證物1），約定被告向原告購買電腦設備一批，總價金新台幣50萬元整。
二、依契約約定，被告應於收到貨品後30日內支付全部價金。
三、原告已於民國112年1月15日依約交付全部貨品（證物2：送貨單），被告亦已簽收。
四、被告應於民國112年2月14日前支付價金，然迄今仍未給付，原告多次催討未果。
五、依民法第367條規定，買受人應支付約定之價金，被告未依約給付，已構成給付遲延，原告自得請求給付。

參、證據：
一、買賣契約書影本一份（證物1）
二、送貨單影本一份（證物2）
三、催款信函及存證信函影本各一份（證物3、4）

此　致
台北地方法院民事庭

具狀人：王大明　　　　　　　（簽名或蓋章）

中　華　民　國　112　年　3　月　15　日
"""
}
