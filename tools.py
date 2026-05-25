import requests
import config

def call_local_ollama(coin_name, oi_rate, volume_pump, price_position, orderbook_delta):
    url = f"http://localhost:11434/api/generate"
    
    # 根據歷史價格位置給予人類可讀的描述
    pos_desc = "【歷史極低位（強烈超賣、底部盤整）】" if price_position < 0.35 else \
               "【歷史極高位（風險極高、山頂過熱）】" if price_position > 0.65 else "【波段中位震盪區】"
               
    delta_desc = f"主動買盤極度強勁 (Delta: +{orderbook_delta:.1f})" if orderbook_delta > 0 else \
                 f"主力暗中大單拋售出貨 (Delta: {orderbook_delta:.1f})"
    
    # 打造高專業度的量化分析 Prompt
    prompt = (
        f"你是一名專精於加密貨幣鏈上數據與盤口微觀結構的頂尖量化交易員。\n"
        f"請針對以下突發異動數據，進行多因子交叉驗證，並給出具體的莊家意圖核心診斷(限制 80 字內，一針見血，不說廢話)：\n\n"
        f"📋 【市場即時監控數據】\n"
        f"• 標的物: #{coin_name}\n"
        f"• 合約持倉量(OI)變化率: {oi_rate:.2%}\n"
        f"• 交易量放大倍數: {volume_pump:.2f} 倍\n"
        f"• 當前價格所處歷史位置: {price_position:.2f} -> {pos_desc}\n"
        f"• 盤口訂單簿買賣流向(Orderbook Delta): {delta_desc}\n"
        f"請直接輸出核心診斷，格式如：此為... 訊號。暗示..."
    )
    
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get("response", "大腦思考中...").strip()
        return "【Ollama 回傳異常】無法取得深度診斷。"
    except Exception:
        return f"本地 {config.OLLAMA_MODEL} 連線異常"

def send_telegram_notification(message):
    
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Telegram API 發送失敗 狀態碼: {response.status_code} | 回傳內容: {response.text}")
            return False
        return True
    except Exception as e:
        print(f"Telegram 連線異常: {e}")
        return False