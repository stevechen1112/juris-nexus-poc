"""
訴訟助手 - 協助進行訴訟準備和訴訟策略規劃
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

class LitigationHelper:
    """訴訟助手 - 協助進行訴訟準備和訴訟策略規劃"""
    
    def __init__(self, prompt_manager: PromptManager, claude_client: ClaudeClient = None):
        """初始化訴訟助手
        
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
    
    async def analyze_case(self, case_type: str, case_facts: str, 
                         party_information: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析案件
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            party_information: 當事人信息
            context: 上下文信息（可選）
            
        Returns:
            案件分析結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "litigation_prep"
        
        # 準備參數
        parameters = {
            "case_type": case_type,
            "case_facts": case_facts,
            "party_information": party_information
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["case_analysis"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於案件分析任務")
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
        party_hash = hashlib.md5(party_information.encode()).hexdigest()
        cache_key = f"case_analysis_{case_type}_{facts_hash[:8]}_{party_hash[:8]}"
        
        # 調用Claude API分析案件
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回案件分析結果
            return {
                "case_analysis": response,
                "metadata": {
                    "case_type": case_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"分析案件時發生錯誤: {str(e)}")
            return {
                "error": f"分析案件時發生錯誤: {str(e)}",
                "case_type": case_type
            }
    
    async def organize_evidence(self, case_type: str, case_facts: str, 
                             evidence_list: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """整理證據
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            evidence_list: 證據清單
            context: 上下文信息（可選）
            
        Returns:
            證據整理結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "litigation_prep"
        
        # 準備參數
        parameters = {
            "case_type": case_type,
            "case_facts": case_facts,
            "evidence_list": evidence_list
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["evidence_organization"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於證據整理任務")
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
        evidence_hash = hashlib.md5(evidence_list.encode()).hexdigest()
        cache_key = f"evidence_organization_{case_type}_{facts_hash[:8]}_{evidence_hash[:8]}"
        
        # 調用Claude API整理證據
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回證據整理結果
            return {
                "evidence_organization": response,
                "metadata": {
                    "case_type": case_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"整理證據時發生錯誤: {str(e)}")
            return {
                "error": f"整理證據時發生錯誤: {str(e)}",
                "case_type": case_type
            }
    
    async def plan_litigation_strategy(self, case_type: str, case_facts: str, 
                                    party_information: str, case_analysis: str,
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """規劃訴訟策略
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            party_information: 當事人信息
            case_analysis: 案件分析
            context: 上下文信息（可選）
            
        Returns:
            訴訟策略規劃結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "litigation_prep"
        
        # 準備參數
        parameters = {
            "case_type": case_type,
            "case_facts": case_facts,
            "party_information": party_information,
            "case_analysis": case_analysis
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["litigation_strategy"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於訴訟策略規劃任務")
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
        analysis_hash = hashlib.md5(case_analysis.encode()).hexdigest()
        cache_key = f"litigation_strategy_{case_type}_{facts_hash[:8]}_{analysis_hash[:8]}"
        
        # 調用Claude API規劃訴訟策略
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回訴訟策略規劃結果
            return {
                "litigation_strategy": response,
                "metadata": {
                    "case_type": case_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"規劃訴訟策略時發生錯誤: {str(e)}")
            return {
                "error": f"規劃訴訟策略時發生錯誤: {str(e)}",
                "case_type": case_type
            }
    
    async def prepare_witness(self, case_type: str, case_facts: str, 
                           witness_information: str, expected_testimony: str,
                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """準備證人
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            witness_information: 證人信息
            expected_testimony: 預期證詞要點
            context: 上下文信息（可選）
            
        Returns:
            證人準備結果
        """
        if context is None:
            context = {}
            
        # 設置任務類型
        task_type = "litigation_prep"
        
        # 準備參數
        parameters = {
            "case_type": case_type,
            "case_facts": case_facts,
            "witness_information": witness_information,
            "expected_testimony": expected_testimony
        }
            
        # 合併上下文
        context.update(parameters)
        context["tags"] = ["witness_preparation"]
        
        # 選擇模板
        template = self.template_selector.select_template(task_type, context)
        if not template:
            logger.error(f"沒有找到適合的模板用於證人準備任務")
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
        witness_hash = hashlib.md5(witness_information.encode()).hexdigest()
        testimony_hash = hashlib.md5(expected_testimony.encode()).hexdigest()
        cache_key = f"witness_prep_{case_type}_{witness_hash[:8]}_{testimony_hash[:8]}"
        
        # 調用Claude API準備證人
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回證人準備結果
            return {
                "witness_preparation": response,
                "metadata": {
                    "case_type": case_type,
                    "template_id": template_id
                }
            }
                
        except Exception as e:
            logger.error(f"準備證人時發生錯誤: {str(e)}")
            return {
                "error": f"準備證人時發生錯誤: {str(e)}",
                "case_type": case_type
            }
    
    async def prepare_cross_examination(self, case_type: str, case_facts: str, 
                                     witness_information: str, expected_testimony: str,
                                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """準備交叉詰問
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            witness_information: 證人信息
            expected_testimony: 預期證詞要點
            context: 上下文信息（可選）
            
        Returns:
            交叉詰問準備結果
        """
        if context is None:
            context = {}
            
        # 構建交叉詰問提示
        prompt = f"""作為台灣訴訟法專家，請協助準備以下案件中對證人的交叉詰問：

案件類型：{case_type}

案件事實：
{case_facts}

證人信息：
{witness_information}

預期證詞要點：
{expected_testimony}

請提供：

1. 交叉詰問策略
   - 詰問目標和重點
   - 詰問順序和邏輯
   - 需要特別注意的事項

2. 交叉詰問問題清單
   - 身分背景確認問題
   - 關鍵事實質疑問題
   - 證詞一致性檢驗問題
   - 證人可信度質疑問題

3. 可能的證人回應和後續問題
   - 預期的證人回應
   - 針對不同回應的後續問題
   - 應對策略

4. 法庭技巧和注意事項
   - 詰問語氣和方式
   - 法庭禮儀和規則
   - 常見錯誤和避免方法

請確保詰問問題專業、有針對性，並符合台灣法庭實務和證人詰問規則。
"""
            
        # 生成緩存鍵
        witness_hash = hashlib.md5(witness_information.encode()).hexdigest()
        testimony_hash = hashlib.md5(expected_testimony.encode()).hexdigest()
        cache_key = f"cross_exam_{case_type}_{witness_hash[:8]}_{testimony_hash[:8]}"
        
        # 調用Claude API準備交叉詰問
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回交叉詰問準備結果
            return {
                "cross_examination": response,
                "metadata": {
                    "case_type": case_type
                }
            }
                
        except Exception as e:
            logger.error(f"準備交叉詰問時發生錯誤: {str(e)}")
            return {
                "error": f"準備交叉詰問時發生錯誤: {str(e)}",
                "case_type": case_type
            }
    
    async def analyze_legal_precedents(self, case_type: str, case_facts: str, 
                                    legal_issues: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析法律先例
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            legal_issues: 法律爭點
            context: 上下文信息（可選）
            
        Returns:
            法律先例分析結果
        """
        if context is None:
            context = {}
            
        # 構建法律先例分析提示
        prompt = f"""作為台灣法律專家，請分析以下案件相關的法律先例：

案件類型：{case_type}

案件事實：
{case_facts}

法律爭點：
{legal_issues}

請提供：

1. 相關法律先例清單
   - 最高法院判例
   - 最高行政法院判例（如適用）
   - 大法官解釋（如適用）
   - 其他重要判決

2. 各先例的關鍵要點
   - 案件事實摘要
   - 法院認定的法律原則
   - 與本案相關性分析

3. 先例對本案的應用
   - 有利的先例及應用方式
   - 不利的先例及區分方法
   - 先例間的衝突及調和

4. 先例趨勢分析
   - 法院見解的發展趨勢
   - 最新判決的影響
   - 可能的未來發展

請確保分析全面、準確，並引用具體的判決字號和關鍵段落。
"""
            
        # 生成緩存鍵
        facts_hash = hashlib.md5(case_facts.encode()).hexdigest()
        issues_hash = hashlib.md5(legal_issues.encode()).hexdigest()
        cache_key = f"precedent_analysis_{case_type}_{facts_hash[:8]}_{issues_hash[:8]}"
        
        # 調用Claude API分析法律先例
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回法律先例分析結果
            return {
                "precedent_analysis": response,
                "metadata": {
                    "case_type": case_type
                }
            }
                
        except Exception as e:
            logger.error(f"分析法律先例時發生錯誤: {str(e)}")
            return {
                "error": f"分析法律先例時發生錯誤: {str(e)}",
                "case_type": case_type
            }
    
    async def prepare_settlement_strategy(self, case_type: str, case_facts: str, 
                                       party_information: str, case_analysis: str,
                                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """準備和解策略
        
        Args:
            case_type: 案件類型
            case_facts: 案件事實
            party_information: 當事人信息
            case_analysis: 案件分析
            context: 上下文信息（可選）
            
        Returns:
            和解策略準備結果
        """
        if context is None:
            context = {}
            
        # 構建和解策略提示
        prompt = f"""作為台灣法律談判專家，請為以下案件制定和解策略：

案件類型：{case_type}

案件事實：
{case_facts}

當事人信息：
{party_information}

案件分析：
{case_analysis}

請提供：

1. 和解目標設定
   - 最佳結果
   - 可接受範圍
   - 底線設定

2. 和解條件分析
   - 核心條件
   - 次要條件
   - 可讓步條件

3. 談判策略
   - 開場策略
   - 讓步策略
   - 應對對方策略
   - 談判技巧

4. 和解協議草擬要點
   - 必要條款
   - 保障條款
   - 執行機制

5. 風險評估
   - 和解風險
   - 不和解風險
   - 風險管理建議

請確保策略全面、務實，並符合台灣法律實務和談判慣例。
"""
            
        # 生成緩存鍵
        facts_hash = hashlib.md5(case_facts.encode()).hexdigest()
        analysis_hash = hashlib.md5(case_analysis.encode()).hexdigest()
        cache_key = f"settlement_strategy_{case_type}_{facts_hash[:8]}_{analysis_hash[:8]}"
        
        # 調用Claude API準備和解策略
        try:
            response = await self.claude_client.generate(prompt, cache_key=cache_key)
            
            # 返回和解策略準備結果
            return {
                "settlement_strategy": response,
                "metadata": {
                    "case_type": case_type
                }
            }
                
        except Exception as e:
            logger.error(f"準備和解策略時發生錯誤: {str(e)}")
            return {
                "error": f"準備和解策略時發生錯誤: {str(e)}",
                "case_type": case_type
            }
