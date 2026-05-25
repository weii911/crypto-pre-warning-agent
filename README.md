## 🚀 執行方式 (使用 CMD)

請打開命令提示字元 (CMD) 並切換至專案目錄，依序執行以下指令：

### 1. 安裝環境依賴
pip install -r requirements.txt

### 2. 初始化歷史資料庫
python fetch_real_data.py

### 3. 模式 A：運行歷史回測流水線
python main.py

### 4. 模式 B：開啟實時線上監控幣安數據流
python main_live.py

### 5. 啟動 Streamlit 網頁監控儀表板
streamlit run app.py
