import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import time
import os

from app.config import APP_NAME, APP_VERSION, APP_DESCRIPTION
from app.api import router as api_router

# 設置日誌
logger = logging.getLogger(__name__)

# 創建FastAPI應用
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該限制來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 設置模板
templates = Jinja2Templates(directory="app/templates")

# 添加API路由
app.include_router(api_router)

# 請求計時中間件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """計算請求處理時間的中間件

    Args:
        request: 請求對象
        call_next: 下一個處理函數

    Returns:
        Response: 回應對象
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 前端路由
@app.get("/")
async def home(request: Request):
    """首頁

    Args:
        request: 請求對象

    Returns:
        TemplateResponse: 渲染後的首頁
    """
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/upload")
async def upload_page(request: Request):
    """文件上傳頁面

    Args:
        request: 請求對象

    Returns:
        TemplateResponse: 渲染後的上傳頁面
    """
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/analysis-results")
async def analysis_results(request: Request, id: str = None):
    """分析結果頁面

    Args:
        request: 請求對象
        id: 文件ID

    Returns:
        TemplateResponse: 渲染後的結果頁面
    """
    # 模擬數據 - 實際應從數據庫獲取
    document = {
        "filename": "合約樣本.pdf",
        "upload_time": "2023-11-18 14:30",
        "analysis_time": "2023-11-18 14:35"
    }
    
    analysis = {
        "analysis": [
            {
                "clause_id": "1",
                "clause_text": "甲方可在任何時間單方面終止合約，無需提前通知",
                "risks": [
                    {
                        "risk_description": "條款不平等，對乙方極不利",
                        "severity": "高",
                        "legal_basis": "民法第247條之1不公平條款原則",
                        "recommendation": "修改為雙方都需提前合理通知才能終止合約"
                    }
                ]
            },
            {
                "clause_id": "2",
                "clause_text": "乙方需承擔所有風險和責任，包括但不限於間接損失、後果性損害及利潤損失",
                "risks": [
                    {
                        "risk_description": "免責條款過於廣泛，可能無效",
                        "severity": "高",
                        "legal_basis": "民法第247條之1及消費者保護法相關規定",
                        "recommendation": "限制責任範圍，明確排除故意或重大過失"
                    },
                    {
                        "risk_description": "用詞模糊，範圍不明確",
                        "severity": "中",
                        "legal_basis": "契約明確性原則",
                        "recommendation": "具體列舉責任項目，避免使用「包括但不限於」等模糊用語"
                    }
                ]
            },
            {
                "clause_id": "3",
                "clause_text": "本合約適用甲方所在地法律，爭議由甲方所在地法院管轄",
                "risks": [
                    {
                        "risk_description": "管轄權約定對乙方不公平",
                        "severity": "中",
                        "legal_basis": "民事訴訟法第25、28條規定",
                        "recommendation": "考慮協議仲裁或選擇中立地區法院管轄"
                    }
                ]
            }
        ],
        "summary": {
            "high_risks_count": 2,
            "medium_risks_count": 2,
            "low_risks_count": 0,
            "overall_risk_assessment": "此合約存在嚴重法律風險，建議在簽署前進行全面修改。特別是終止條款、責任限制和爭議解決機制都需要重新協商。"
        }
    }
    
    # 獲取高風險項目作為重點顯示
    top_risks = []
    for clause in analysis["analysis"]:
        for risk in clause["risks"]:
            if risk["severity"] == "高":
                risk["clause_id"] = clause["clause_id"]
                top_risks.append(risk)
    
    # 生成分享URL
    share_url = f"{request.base_url}share/{id if id else '123456'}"
    
    return templates.TemplateResponse(
        "analysis_results.html", 
        {
            "request": request,
            "document": document,
            "analysis": analysis,
            "top_risks": top_risks,
            "share_url": share_url
        }
    )

@app.get("/api")
async def api_info():
    """API信息

    Returns:
        Dict: API信息
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "docs_url": "/docs",
        "api_prefix": "/api"
    }

# 全局異常處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局異常處理器

    Args:
        request: 請求對象
        exc: 異常對象

    Returns:
        JSONResponse: 錯誤回應
    """
    logger.error(f"全局異常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "服務器內部錯誤",
            "detail": str(exc)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
