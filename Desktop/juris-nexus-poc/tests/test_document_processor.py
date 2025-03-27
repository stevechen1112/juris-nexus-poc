import pytest
import os
import tempfile
from app.document_processor import (
    extract_text_from_pdf, 
    extract_text_from_docx, 
    split_into_clauses,
    extract_sub_clauses,
    preprocess_document
)

# 測試條款分割功能
def test_split_into_clauses():
    # 測試文本
    test_text = """
    第一條：總則
    本合同由甲方和乙方簽訂。
    
    第二條：權利與義務
    （一）甲方的權利和義務
    1. 甲方應支付費用。
    2. 甲方有權獲得服務。
    
    （二）乙方的權利和義務
    1. 乙方應提供服務。
    2. 乙方有權獲得報酬。
    
    第三條：合同期限
    本合同有效期為一年。
    """
    
    # 執行條款分割
    clauses = split_into_clauses(test_text)
    
    # 驗證結果
    assert len(clauses) >= 3  # 至少有3個主條款
    
    # 檢查第一條
    first_clause = next((c for c in clauses if c['id'] == '第一條'), None)
    assert first_clause is not None
    assert '總則' in first_clause['text']
    
    # 檢查第二條
    second_clause = next((c for c in clauses if c['id'] == '第二條'), None)
    assert second_clause is not None
    assert '權利與義務' in second_clause['text']
    assert second_clause.get('has_sub_clauses') is True
    
    # 檢查子條款
    sub_clause = next((c for c in clauses if c['id'] == '第二條-一'), None)
    assert sub_clause is not None
    assert '甲方的權利和義務' in sub_clause['text']

# 測試子條款提取功能
def test_extract_sub_clauses():
    # 測試文本
    clause_text = """權利與義務
    （一）甲方的權利和義務
    1. 甲方應支付費用。
    2. 甲方有權獲得服務。
    
    （二）乙方的權利和義務
    1. 乙方應提供服務。
    2. 乙方有權獲得報酬。
    """
    
    # 執行子條款提取
    sub_clauses = extract_sub_clauses(clause_text)
    
    # 驗證結果
    assert len(sub_clauses) == 2
    assert '一' in sub_clauses
    assert '二' in sub_clauses
    assert '甲方的權利和義務' in sub_clauses['一']
    assert '乙方的權利和義務' in sub_clauses['二']

# 測試沒有條款格式的情況
def test_split_into_clauses_no_format():
    # 測試文本
    test_text = """
    這是一個沒有標準條款格式的文本。
    它應該被分割成段落。
    
    這是第二段。
    """
    
    # 執行條款分割
    clauses = split_into_clauses(test_text)
    
    # 驗證結果
    assert len(clauses) > 0
    # 檢查是否使用段落標識
    assert clauses[0]['id'].startswith('p')

# 如果可以創建臨時PDF/DOCX文件，可以添加以下測試
# 但這需要實際文件操作，可能需要模擬
"""
def test_extract_text_from_pdf():
    # 創建臨時PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp:
        temp_name = temp.name
    
    try:
        # TODO: 寫入PDF內容
        # 測試提取
        text = extract_text_from_pdf(temp_name)
        assert text is not None
    finally:
        # 清理
        if os.path.exists(temp_name):
            os.remove(temp_name)

def test_extract_text_from_docx():
    # 創建臨時DOCX
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp:
        temp_name = temp.name
    
    try:
        # TODO: 寫入DOCX內容
        # 測試提取
        text = extract_text_from_docx(temp_name)
        assert text is not None
    finally:
        # 清理
        if os.path.exists(temp_name):
            os.remove(temp_name)
"""
