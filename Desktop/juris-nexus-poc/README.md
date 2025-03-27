# JURIS NEXUS - 智慧法律助手系統

JURIS NEXUS 是一個基於雙層 AI 架構 (Taiwan LLM + Claude) 的智慧法律助手系統，專為台灣法律環境設計。系統能夠接收並分析法律文件，特別是合同，識別潛在風險，提供專業的法律建議，並支援多輪法律諮詢對話。

## 專案目標

- 實現雙層 AI 架構的協作機制，結合本地化法律知識與先進語言模型
- 專注於合同條款風險識別與分析，提供專業法律建議
- 建立評估框架衡量系統效能，並通過專家反饋持續改進
- 提供穩定可靠的法律 AI 服務，即使在網絡連接不穩定的情況下也能運行

## 系統功能

### 核心功能
- 支援 PDF 和 DOCX 格式文件的處理與分析
- 基於 Taiwan LLM 的初步法律分析，專注於台灣法律環境
- 基於 Claude 的分析評估與優化，提供更深入的法律見解
- 合約風險分析與評估，識別潛在法律風險
- 法律諮詢多輪對話，支援不同法律領域的問答

### 新增功能 (v0.2.0)
- **專家反饋系統**：收集法律專家對 AI 分析結果的評價和建議
- **模擬模式**：在 API 連接不可用時自動切換到模擬模式，確保系統持續運行
- **法律諮詢對話**：支援多輪法律諮詢對話，記錄對話歷史
- **系統狀態監控**：實時監控 API 連接狀態和系統性能
- **反饋數據分析儀表板**：視覺化展示專家反饋數據，幫助系統持續改進

## 安裝與運行

### 系統要求
- Python 3.8+
- FastAPI
- 有效的 Claude API 密鑰
- 有效的 Hugging Face API 密鑰 (用於 Taiwan LLM)

### 安裝步驟

1. 克隆此倉庫
   ```bash
   git clone https://github.com/your-username/juris-nexus-poc.git
   cd juris-nexus-poc
   ```

2. 建立虛擬環境
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. 安裝依賴
   ```bash
   pip install -r requirements.txt
   ```

4. 配置環境變數，創建 .env 文件添加以下內容
   ```
   # API 密鑰
   CLAUDE_API_KEY=your_claude_api_key
   HUGGINGFACE_API_KEY=your_huggingface_api_key
   TAIWAN_LLM_API_URL=https://api.huggingface.co/models/yentinglin/Llama-3-Taiwan-8B-Instruct
   
   # 模擬模式配置
   USE_MOCK_MODE=false
   MOCK_CLAUDE=false
   MOCK_TAIWAN_LLM=false
   
   # 應用配置
   TEMP_UPLOAD_DIR=./app/data/temp
   LEARNING_DATA_DIR=./app/data/learning
   ```

5. 運行應用
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## 使用方法

啟動應用後，可以通過以下途徑訪問系統：

- Web 界面: http://localhost:8000
- API 文檔: http://localhost:8000/docs

### 主要功能頁面
- **首頁**：系統概述和功能導航
- **上傳合約**：上傳合同文件進行風險分析
- **分析歷史**：查看過去的分析結果
- **法律知識庫**：瀏覽法律知識和案例
- **法律諮詢**：進行多輪法律諮詢對話
- **系統狀態**：監控系統狀態和 API 連接

### API 端點
- `/api/analyze-file` - 上傳並分析合同文件
- `/api/analyze-text` - 分析文本中的法律內容
- `/api/conversation` - 法律諮詢對話管理
- `/api/statistics` - 獲取系統統計數據
- `/api/test/claude` - 測試 Claude API 連接
- `/api/test/taiwan-llm` - 測試 Taiwan LLM API 連接

## 專案結構

```
juris-nexus-poc/
├── app/
│   ├── __init__.py
│   ├── main.py                # 應用入口點
│   ├── api.py                 # 主要 API 定義
│   ├── api_conversation.py    # 對話 API
│   ├── api_system.py          # 系統狀態 API
│   ├── config.py              # 配置
│   ├── document_processor.py  # 文檔處理
│   ├── dual_ai_engine.py      # 雙 AI 引擎
│   ├── expert_feedback.py     # 專家反饋系統
│   ├── model_clients.py       # AI 模型客戶端
│   ├── learning_recorder.py   # 學習記錄
│   ├── legal_tasks/           # 法律任務模組
│   │   ├── __init__.py
│   │   ├── consultation_service.py  # 法律諮詢服務
│   │   ├── contract_analyzer.py     # 合約分析器
│   │   ├── document_drafter.py      # 文件草擬助手
│   │   ├── litigation_helper.py     # 訴訟助手
│   │   └── research_assistant.py    # 法律研究助手
│   ├── prompt_engine/         # 提示詞引擎
│   │   ├── __init__.py
│   │   ├── prompt_manager.py        # 提示詞管理
│   │   ├── template_optimizer.py    # 模板優化
│   │   ├── template_selector.py     # 模板選擇
│   │   └── feedback_analyzer.py     # 反饋分析
│   ├── static/                # 靜態資源
│   ├── templates/             # HTML 模板
│   └── utils.py               # 工具函數
├── tests/                     # 測試文件
├── references/                # 參考資料
├── .env.example               # 環境變數範例
├── requirements.txt           # 依賴項
└── README.md                  # 說明文檔
```

## 當前系統狀態

- **版本**：v0.2.0
- **狀態**：概念驗證階段
- **Claude API**：已支援最新版本 (claude-3-5-sonnet-20241022)
- **Taiwan LLM**：使用 Llama-3-Taiwan-8B-Instruct 模型
- **模擬模式**：已實現，可在 API 連接不可用時自動切換

## 注意事項

- 本系統提供的分析僅供參考，不構成法律建議。請諮詢專業律師獲取具體法律意見。
- 使用前請確保您有有效的 API 密鑰，或啟用模擬模式進行測試。
- 系統處理的所有文件和數據僅在本地存儲，不會上傳到外部服務器。

## 授權

本專案僅用於概念驗證和研究目的，未經授權不得用於商業用途。