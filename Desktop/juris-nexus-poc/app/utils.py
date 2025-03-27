import os
import uuid
import logging
from fastapi import UploadFile
import shutil
from typing import Dict, List, Any, Tuple
import json

from app.config import TEMP_UPLOAD_DIR

logger = logging.getLogger(__name__)

async def save_upload_file_temporarily(upload_file: UploadFile) -> str:
    """
    將上傳的文件臨時保存到磁盤，返回臨時文件路徑

    Args:
        upload_file: 上傳的文件對象

    Returns:
        str: 臨時文件的路徑
    """
    try:
        # 創建唯一文件名
        file_extension = os.path.splitext(upload_file.filename)[1]
        temp_filename = f"{uuid.uuid4()}{file_extension}"
        temp_file_path = os.path.join(TEMP_UPLOAD_DIR, temp_filename)
        
        # 保存文件
        with open(temp_file_path, "wb") as temp_file:
            content = await upload_file.read()
            temp_file.write(content)
            
        logger.info(f"臨時文件已保存: {temp_file_path}")
        return temp_file_path
    
    except Exception as e:
        logger.error(f"保存上傳文件時出錯: {str(e)}")
        raise e
        
def get_file_extension(file_path: str) -> str:
    """
    獲取文件擴展名

    Args:
        file_path: 文件路徑

    Returns:
        str: 小寫的文件擴展名（不含點）
    """
    return os.path.splitext(file_path)[1].lower().lstrip('.')

def format_json_response(data: Dict) -> Dict:
    """
    格式化JSON響應

    Args:
        data: 要格式化的數據

    Returns:
        Dict: 格式化後的JSON響應
    """
    return {
        "status": "success",
        "data": data
    }

def format_error_response(error_message: str, error_code: str = "error") -> Dict:
    """
    格式化錯誤響應

    Args:
        error_message: 錯誤訊息
        error_code: 錯誤代碼

    Returns:
        Dict: 格式化後的錯誤響應
    """
    return {
        "status": "error",
        "error": {
            "code": error_code,
            "message": error_message
        }
    }

def validate_json_string(json_str: str) -> Tuple[bool, Any]:
    """
    驗證JSON字符串是否有效

    Args:
        json_str: JSON字符串

    Returns:
        Tuple[bool, Any]: (是否有效, 解析後的對象或錯誤訊息)
    """
    try:
        data = json.loads(json_str)
        return True, data
    except json.JSONDecodeError as e:
        return False, str(e)
