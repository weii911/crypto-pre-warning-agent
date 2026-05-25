# 基於強化學習之加密貨幣智能預警系統

本專案為期末專題課堂作業成果提交。本系統整合深度強化學習（PPO）演算法與本地大型語言模型（Ollama），針對加密貨幣衍生品市場進行真錢籌碼面特徵提取（持倉暴增率、成交量放大倍數、盤口買賣單失衡差值），並透過雙層降頻過濾閘門實施策略剪枝，打造具備高效硬體算力防禦與一天一報冷卻機制的動態實時監控預警 Agent。

---

## 環境需求 (Requirements)
* **作業系統**：Windows 10/11, macOS, 或 Linux
* **Python 版本**：`Python 3.13`
* **本地 LLM 推理引擎**：Ollama (需預先下載並部屬 `gemma` 模型權重)

---

##  申辦與手動配置 Telegram 預警機器人

本系統具備動態推播功能，使用者**必須先配置自己的 Telegram 機器人金鑰**，程式在觸發 Level 2 深度通報時，才有辦法將大模型的微觀資金診斷戰報精準發送到您的手機。請跟著以下步驟完成配置：

### 步驟 1：獲取的Bot Token
1. 打開 Telegram 軟體，在搜尋欄輸入官方帳號 `@BotFather` 並開啟對話。
2. 輸入指令 `/newbot`，依據提示幫預警機器人取一個名稱與使用者帳號（帳號結尾必須是 `bot`）。
3. 建立成功後，`BotFather` 會直接噴出一串金鑰，這就是 **TELEGRAM_TOKEN**（例如：`123456789:ABCdefGhIJKlmNoPQ...`）。

### 步驟 2：獲取Chat ID
1. 在 Telegram 搜尋欄輸入帳號 `@userinfobot` 並點擊啟動。
2. 它會立刻自動傳回一串數字，這就是個人 **TELEGRAM_CHAT_ID**（例如：`987654321`）。
3. **核心防呆提醒**：拿到金鑰後，請務必先隨便傳送一個訊息給剛建好的預警機器人以啟動對話（點擊 Start 即可），否則機器人會因為沒有權限而無法發送簡訊。

### 步驟 3：手動修改 `config.py` 配置檔案
打開本專案根目錄底下的 `config.py`，將剛剛獲取的真實 Token 與 Chat ID 直接替換進引號內並存檔：

```python
# config.py

DB_REAL = "crypto_market_data.db"
OLLAMA_MODEL = "gemma"

# 請在此處手動替換成您剛剛向官方申辦的真實金鑰 
TELEGRAM_TOKEN = "機器人Token填在這裡"
TELEGRAM_CHAT_ID = "個人ChatID填在這裡"

```
步驟 1：切換至專案所在目錄
請根據電腦中專案資料夾的真實路徑進行切換（以路徑在桌面為例）：

Bash
cd Desktop/crypto_project
步驟 2：一鍵安裝所有必要 Python 套件
讓系統自動讀取環境清單，安裝強化學習（Stable-Baselines3）與交易所協議（CCXT）等依賴套件：

Bash
pip install -r requirements.txt
步驟 3：初始化 SQLite 歷史資料庫
直接連線交易所 API 撈取實體真數據，在本地生成 crypto_market_data.db 資料庫檔案：
Bash
python fetch_real_data.py

步驟 4：選擇模式執行主程式 (二選一)
模式 A：運行歷史回測
載入訓練好的神經網路權重模型，對歷史數據進行離線樣本外 blind test 回放盲測：

Bash
python main.py
模式 B：開啟「實時線上秒級風控預警」
直接連線幣安（Binance）交易所期貨實體 API。系統將每 10 秒進行一次秒級截面掃描，一旦特徵穿透 2.2% 剛性閥門，將即時喚醒 Ollama 大模型解算並直接推播 Telegram 實戰戰報（按 Ctrl + C 可安全關閉）：

Bash
python main_live.py

步驟 5：啟動網頁數據監控儀表板
請另外打開一個全新的 CMD 視窗，同樣 cd 進入專案資料夾後執行以下指令，即可直觀觀看策略收斂圓餅圖與事件日誌：

Bash
streamlit run app.py
啟動完成後，瀏覽器將自動彈出訪問網址：http://localhost:8501
