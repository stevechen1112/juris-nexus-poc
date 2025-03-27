import os
import re
import logging
from typing import List, Dict, Any, Optional
import pdfplumber
import docx
from app.utils import get_file_extension

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: str) -> str:
    """從PDF文件中提取文本

    Args:
        file_path: PDF文件的路徑

    Returns:
        str: 提取的文本內容
    """
    logger.info(f"正在從PDF提取文本: {file_path}")
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF文本提取失敗: {str(e)}")
        raise Exception(f"無法處理PDF文件: {str(e)}")

def extract_text_from_docx(file_path: str) -> str:
    """從Word文件中提取文本

    Args:
        file_path: Word文件的路徑

    Returns:
        str: 提取的文本內容
    """
    logger.info(f"正在從DOCX提取文本: {file_path}")
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        logger.error(f"DOCX文本提取失敗: {str(e)}")
        raise Exception(f"無法處理DOCX文件: {str(e)}")

def split_into_clauses(document_text: str) -> List[Dict[str, str]]:
    """將文檔文本分割為條款單位

    Args:
        document_text: 文檔的全文本

    Returns:
        List[Dict[str, str]]: 條款列表，每個條款包含ID和內容
    """
    logger.info("正在分割文本為條款")
    
    # 條款標識模式
    # 匹配如"第一條"、"第1條"、"第壹條"等格式，同時處理章節
    clause_pattern = r'(第[一二三四五六七八九十百千萬\d]+[條章節])[：:\s]*(.*?)(?=(第[一二三四五六七八九十百千萬\d]+[條章節])|$)'
    
    # 使用正則表達式找出所有條款
    matches = re.findall(clause_pattern, document_text, re.DOTALL)
    
    if not matches:
        # 如果沒有找到條款，嘗試用段落分割
        paragraphs = [p.strip() for p in document_text.split('\n') if p.strip()]
        return [{"id": f"p{i+1}", "text": p} for i, p in enumerate(paragraphs)]
    
    clauses = []
    for i, match in enumerate(matches):
        clause_id = match[0].strip()
        clause_text = match[1].strip()
        
        # 檢查是否有子條款
        sub_clauses = extract_sub_clauses(clause_text)
        
        if sub_clauses:
            # 如果有子條款，添加主條款和所有子條款
            clauses.append({"id": clause_id, "text": clause_text, "has_sub_clauses": True})
            for sub_id, sub_text in sub_clauses.items():
                clauses.append({
                    "id": f"{clause_id}-{sub_id}",
                    "text": sub_text,
                    "parent_id": clause_id
                })
        else:
            # 如果沒有子條款，只添加主條款
            clauses.append({"id": clause_id, "text": clause_text})
    
    return clauses

def extract_sub_clauses(clause_text: str) -> Dict[str, str]:
    """提取子條款

    Args:
        clause_text: 條款的文本內容

    Returns:
        Dict[str, str]: 子條款ID和內容的字典
    """
    # 匹配如"(一)"、"（一）"等常見的子條款標識
    sub_clause_pattern = r'[（\(]([一二三四五六七八九十]+)[）\)][\s:：]*(.*?)(?=[（\(][一二三四五六七八九十]+[）\)]|$)'
    
    matches = re.findall(sub_clause_pattern, clause_text, re.DOTALL)
    if not matches:
        return {}
    
    sub_clauses = {}
    for match in matches:
        sub_id = match[0].strip()
        sub_text = match[1].strip()
        sub_clauses[sub_id] = sub_text
    
    return sub_clauses

def preprocess_document(file_path: str) -> Dict[str, Any]:
    """文檔預處理主函數

    Args:
        file_path: 文件路徑

    Returns:
        Dict: 包含文檔信息和條款列表的字典
    """
    logger.info(f"開始處理文檔: {file_path}")
    file_extension = get_file_extension(file_path)
    
    # 根據文件類型提取文本
    if file_extension == 'pdf':
        text = extract_text_from_pdf(file_path)
    elif file_extension in ['docx', 'doc']:
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"不支持的文件類型: {file_extension}")
    
    # 分割為條款
    clauses = split_into_clauses(text)
    
    return {
        "document_info": {
            "filename": os.path.basename(file_path),
            "file_type": file_extension,
            "text_length": len(text)
        },
        "full_text": text,
        "clauses": clauses
    }
