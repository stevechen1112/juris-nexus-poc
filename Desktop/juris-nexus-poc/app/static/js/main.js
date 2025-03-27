// JURIS NEXUS 前端功能實現

// DOM元素加載完成後執行
document.addEventListener('DOMContentLoaded', function() {
  // 初始化功能
  initFileUpload();
  initTabNavigation();
  initContractAnalysis();
  initExpertFeedbackForm(); // 初始化專家反饋表單
});

/**
 * 初始化檔案上傳功能
 */
function initFileUpload() {
  const uploadArea = document.querySelector('.upload-area');
  const fileInput = document.getElementById('file-input');
  const uploadForm = document.getElementById('upload-form');
  
  // 如果頁面上沒有上傳區域，則跳過
  if (!uploadArea) return;
  
  // 點擊上傳區域時觸發文件選擇
  uploadArea.addEventListener('click', function() {
    fileInput.click();
  });
  
  // 拖拽文件到上傳區域
  uploadArea.addEventListener('dragover', function(e) {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
  });
  
  uploadArea.addEventListener('dragleave', function() {
    uploadArea.classList.remove('drag-over');
  });
  
  uploadArea.addEventListener('drop', function(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      updateFileInfo(fileInput.files[0]);
    }
  });
  
  // 文件選擇變更時
  if (fileInput) {
    fileInput.addEventListener('change', function() {
      if (fileInput.files.length) {
        updateFileInfo(fileInput.files[0]);
      }
    });
  }
  
  // 表單提交處理
  if (uploadForm) {
    uploadForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      if (!fileInput.files.length) {
        showNotification('請選擇檔案', 'warning');
        return;
      }
      
      uploadFile(new FormData(uploadForm));
    });
  }
}

/**
 * 更新選擇的文件信息顯示
 */
function updateFileInfo(file) {
  const fileInfoElement = document.getElementById('file-info');
  if (!fileInfoElement) return;
  
  const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
  
  if (!allowedTypes.includes(file.type)) {
    showNotification('僅支援PDF和DOCX格式文件', 'error');
    return;
  }
  
  const fileIcon = file.type.includes('pdf') ? '📄' : '📝';
  const fileSize = (file.size / 1024 / 1024).toFixed(2);
  
  fileInfoElement.innerHTML = `
    <div class="file-details">
      <span class="file-icon">${fileIcon}</span>
      <div class="file-meta">
        <div class="file-name">${file.name}</div>
        <div class="file-size">${fileSize} MB</div>
      </div>
    </div>
    <button type="submit" class="btn btn-primary">開始分析</button>
  `;
  
  fileInfoElement.classList.remove('hidden');
}

/**
 * 上傳文件至伺服器
 */
function uploadFile(formData) {
  const progressElement = document.getElementById('upload-progress');
  const progressBar = document.querySelector('.progress-bar');
  
  // 顯示進度條
  if (progressElement) {
    progressElement.classList.remove('hidden');
  }
  
  // 執行文件上傳
  fetch('/api/documents/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('上傳失敗');
    }
    return response.json();
  })
  .then(data => {
    showNotification('文件上傳成功', 'success');
    
    // 更新進度條模擬處理過程
    simulateProcessing(progressBar, data.document_id);
  })
  .catch(error => {
    console.error('上傳錯誤:', error);
    showNotification('上傳失敗: ' + error.message, 'error');
    
    if (progressElement) {
      progressElement.classList.add('hidden');
    }
  });
}

/**
 * 模擬處理進度
 */
function simulateProcessing(progressBar, documentId) {
  let progress = 0;
  const interval = setInterval(() => {
    progress += 5;
    if (progressBar) {
      progressBar.style.width = `${progress}%`;
    }
    
    if (progress >= 100) {
      clearInterval(interval);
      
      // 分析完成，跳轉到結果頁面
      window.location.href = `/analysis-results?id=${documentId}`;
    }
  }, 300);
}

/**
 * 初始化頁籤切換功能
 */
function initTabNavigation() {
  const tabLinks = document.querySelectorAll('.tab-link');
  const tabContents = document.querySelectorAll('.tab-content');
  
  tabLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      
      // 移除所有活動標記
      tabLinks.forEach(l => l.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      
      // 啟用當前標記
      this.classList.add('active');
      
      // 顯示目標內容
      const targetId = this.getAttribute('data-tab');
      document.getElementById(targetId).classList.add('active');
    });
  });
}

/**
 * 初始化合約分析結果功能
 */
function initContractAnalysis() {
  const clauseLinks = document.querySelectorAll('.clause-item');
  
  clauseLinks.forEach(link => {
    link.addEventListener('click', function() {
      // 移除所有活動標記
      clauseLinks.forEach(l => l.classList.remove('active'));
      
      // 啟用當前標記
      this.classList.add('active');
      
      // 獲取條款ID
      const clauseId = this.getAttribute('data-id');
      
      // 載入條款內容和風險分析
      loadClauseContent(clauseId);
    });
  });
}

/**
 * 載入條款內容和風險分析
 */
function loadClauseContent(clauseId) {
  const contentArea = document.querySelector('.content-area');
  const sidebarArea = document.querySelector('.sidebar');
  
  if (!contentArea || !sidebarArea) return;
  
  // 顯示載入中動畫
  contentArea.innerHTML = '<div class="loading">載入中...</div>';
  sidebarArea.innerHTML = '<div class="loading">載入中...</div>';
  
  // 獲取條款詳情
  fetch(`/api/analysis/clauses/${clauseId}`)
  .then(response => response.json())
  .then(data => {
    // 更新條款內容
    contentArea.innerHTML = `
      <h3>條款 #${data.clause_id}</h3>
      <div class="clause-text">${data.clause_text}</div>
      
      <div class="risk-analysis">
        <h4>風險分析</h4>
        <ul class="risk-list">
          ${data.risks.map(risk => `
            <li class="risk-item">
              <div class="risk-header">
                <span class="badge badge-${risk.severity.toLowerCase()}">${risk.severity}</span>
                <span class="risk-title">${risk.risk_description}</span>
              </div>
              <div class="risk-details">
                ${risk.legal_basis ? `<p><strong>法律依據:</strong> ${risk.legal_basis}</p>` : ''}
                <p><strong>改進建議:</strong> ${risk.recommendation}</p>
              </div>
            </li>
          `).join('')}
        </ul>
      </div>
    `;
    
    // 更新建議面板
    sidebarArea.innerHTML = `
      <h3>改進建議</h3>
      <div class="recommendations">
        ${data.risks.map(risk => `
          <div class="recommendation-item">
            <h4>${risk.risk_description}</h4>
            <p>${risk.recommendation}</p>
          </div>
        `).join('')}
      </div>
      
      <div class="feedback-section">
        <h3>專家反饋</h3>
        <div class="rating">
          <span>分析準確性:</span>
          <div class="stars">
            ${generateStars(5)}
          </div>
        </div>
        <textarea class="form-control" placeholder="請提供您的專業意見..."></textarea>
        <button class="btn btn-primary mt-2">提交反饋</button>
      </div>
    `;
    
    // 初始化評分功能
    initRating();
    
    // 顯示專家反饋表單
    showExpertFeedbackForm();
  })
  .catch(error => {
    console.error('載入失敗:', error);
    contentArea.innerHTML = '<div class="error">載入失敗，請重試</div>';
  });
}

/**
 * 產生評星HTML
 */
function generateStars(count) {
  let stars = '';
  for (let i = 1; i <= 5; i++) {
    stars += `<span class="star" data-value="${i}">${i <= count ? '★' : '☆'}</span>`;
  }
  return stars;
}

/**
 * 初始化評分功能
 */
function initRating() {
  const stars = document.querySelectorAll('.star');
  
  stars.forEach(star => {
    star.addEventListener('click', function() {
      const value = this.getAttribute('data-value');
      
      // 更新星星顯示
      stars.forEach(s => {
        const starValue = s.getAttribute('data-value');
        s.textContent = starValue <= value ? '★' : '☆';
      });
    });
  });
}

/**
 * 顯示通知訊息
 */
function showNotification(message, type = 'info') {
  // 檢查是否已有通知容器
  let container = document.querySelector('.notification-container');
  
  if (!container) {
    container = document.createElement('div');
    container.className = 'notification-container';
    document.body.appendChild(container);
  }
  
  // 創建新通知
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <div class="notification-content">${message}</div>
    <button class="notification-close">&times;</button>
  `;
  
  // 添加關閉按鈕功能
  notification.querySelector('.notification-close').addEventListener('click', function() {
    container.removeChild(notification);
  });
  
  // 添加到容器並設置自動關閉
  container.appendChild(notification);
  
  // 動畫效果
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);
  
  // 自動關閉
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => {
      if (container.contains(notification)) {
        container.removeChild(notification);
      }
    }, 300);
  }, 5000);
}

/**
 * 初始化專家反饋表單
 */
function initExpertFeedbackForm() {
  // 檢查是否在分析結果頁面
  const expertFeedbackContainer = document.getElementById('expert-feedback-container');
  if (!expertFeedbackContainer) return;
  
  // 載入 ExpertFeedbackForm 組件
  const script = document.createElement('script');
  script.src = '/static/js/components/ExpertFeedbackForm.js';
  script.onload = function() {
    // 初始化 Vue 應用
    const app = Vue.createApp({
      components: {
        'expert-feedback-form': ExpertFeedbackForm
      },
      data() {
        return {
          analysisId: this.getAnalysisId(),
          showNotification: false,
          notificationMessage: '',
          notificationType: 'info'
        };
      },
      methods: {
        getAnalysisId() {
          if (window.analysisData) {
            const urlParams = new URLSearchParams(window.location.search);
            const idFromUrl = urlParams.get('id');
            if (idFromUrl) return idFromUrl;
            
            if (window.analysisData.id) return window.analysisData.id;
            if (window.analysisData.analysis && window.analysisData.analysis.id) 
              return window.analysisData.analysis.id;
            if (window.analysisData.document && window.analysisData.document.id) 
              return window.analysisData.document.id;
              
            if (window.analysisData.document && window.analysisData.document.filename) {
              const filename = window.analysisData.document.filename.replace(/\s+/g, '_').toLowerCase();
              return `analysis_${filename}_${Date.now()}`;
            }
          }
          
          return `analysis_${Date.now()}`;
        },
        handleSubmitted(result) {
          console.log('反饋已提交:', result);
          this.showNotification = true;
          this.notificationMessage = '感謝您的反饋！';
          this.notificationType = 'success';
          
          setTimeout(() => {
            this.showNotification = false;
          }, 3000);
        },
        handleError(message) {
          console.error('反饋提交錯誤:', message);
          this.showNotification = true;
          this.notificationMessage = message;
          this.notificationType = 'error';
          
          setTimeout(() => {
            this.showNotification = false;
          }, 3000);
        }
      },
      template: `
        <div>
          <expert-feedback-form 
            :analysis-id="analysisId"
            @submitted="handleSubmitted"
            @error="handleError"
          ></expert-feedback-form>
          
          <div v-if="showNotification" :class="'notification notification-' + notificationType">
            {{ notificationMessage }}
          </div>
        </div>
      `
    });
    
    app.mount('#expert-feedback-form');
  };
  
  document.head.appendChild(script);
}

/**
 * 顯示專家反饋表單
 */
function showExpertFeedbackForm() {
  const initialMessage = document.getElementById('sidebar-initial-message');
  const feedbackContainer = document.getElementById('expert-feedback-container');
  
  if (initialMessage && feedbackContainer) {
    initialMessage.style.display = 'none';
    feedbackContainer.style.display = 'block';
  }
}