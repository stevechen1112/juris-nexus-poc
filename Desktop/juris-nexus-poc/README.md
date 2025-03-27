# JURIS NEXUS - 法律AI助手概念驗證

JURIS NEXUS是一個基於雙層AI架構(Taiwan LLM + Claude)的法律助手系統的概念驗證(PoC)原型。系統能夠接收並分析法律文件，特別是合同，識別潛在風險，並提供專業的法律建議。

## 專案目標

- 實現雙層AI架構的基本協作機制
- 專注於合同條款風險識別與分析
- 建立基本評估框架衡量系統效能
- 完成一個可演示的工作原型

## 系統功能

- 支援PDF和DOCX格式文件的處理
- 基於Taiwan LLM的初步法律分析
- 基於Claude的分析評估與優化
- 通過API提供服務

## 安裝與運行

1. 克隆此倉庫
2. 建立虛擬環境

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 安裝依賴

```bash
pip install -r requirements.txt
```

4. 配置環境變數，創建.env文件添加以下內容

```
CLAUDE_API_KEY=your_claude_api_key
TAIWAN_LLM_API_KEY=your_taiwan_llm_api_key
TAIWAN_LLM_API_URL=your_taiwan_llm_api_url
```

5. 運行應用

```bash
uvicorn app.main:app --reload --port 8000
```

## API使用

啟動應用後，可以通過以下途徑訪問API：

- API文檔: http://localhost:8000/docs
- 主要端點: `/api/analyze-contract` - 用於上傳合同文件並進行分析

## 專案結構

```
legal-ai-poc/
├── app/
│   ├── __init__.py
│   ├── main.py             # 應用入口點
│   ├── api.py              # API定義
│   ├── config.py           # 配置
│   ├── document_processor.py  # 文檔處理
│   ├── dual_ai_engine.py   # 雙AI引擎
│   ├── model_clients.py    # AI模型客戶端
│   ├── learning_recorder.py  # 學習記錄
│   └── utils.py            # 工具函數
├── tests/                  # 測試文件
├── data/                   # 數據存儲
│   ├── samples/            # 示例文檔
│   ├── temp/               # 臨時文件
│   └── learning/           # 學習數據
├── requirements.txt        # 依賴項
└── README.md               # 說明文檔
``` 