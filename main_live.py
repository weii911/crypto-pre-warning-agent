import time
import os
import datetime
import numpy as np
import ccxt
from stable_baselines3 import PPO
import tools
import config

def fetch_live_state(symbol="BTC/USDT:USDT"):
    exchange = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
    try:
        ohlcv_4h = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=20)
        ohlcv_1d = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=30)
        
        prices_1d = [c[4] for c in ohlcv_1d]
        current_price = prices_1d[-1]
        htf_price_position = (current_price - min(prices_1d)) / (max(prices_1d) - min(prices_1d)) if max(prices_1d) != min(prices_1d) else 0.5
        
        last_candle = ohlcv_4h[-1]
        open_p, close_p, volume = last_candle[1], last_candle[4], last_candle[5]
        price_change = (close_p - open_p) / open_p
        
        prices_4h = [c[4] for c in ohlcv_4h]
        price_position = (close_p - min(prices_4h)) / (max(prices_4h) - min(prices_4h)) if max(prices_4h) != min(prices_4h) else 0.5
        
        avg_vol = sum([c[5] for c in ohlcv_4h[-6:-1]]) / 5
        volume_pump = volume / avg_vol if avg_vol > 0 else 1.0
        
        oi_rate = abs(price_change) * 0.5 + (volume_pump * 0.02)
        orderbook_delta = volume * price_change * 0.1
        
        direction = "🟢 多頭趨勢" if price_change >= 0.012 else "🔴 空頭趨勢" if price_change <= -0.012 else "🟡 橫盤震盪/主力洗盤"
        is_real_pump = 1 if (volume_pump > 1.8 and oi_rate > 0.02) else 0
        
        return {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': symbol.split('/')[0],
            'price': current_price,
            'oi_rate': oi_rate,
            'volume_pump': volume_pump,
            'price_position': price_position,
            'htf_price_position': htf_price_position,
            'orderbook_delta': orderbook_delta,
            'price_change': price_change,
            'direction': direction,
            'is_real_pump': is_real_pump
        }
    except Exception as e:
        print(f"📡 實時數據流採集延遲: {e}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("加密貨幣預警 Agent")
    print("=" * 50)
    
    model_path = "best_crypto_agent.zip"
    if os.path.exists(model_path):
        print("已成功載入 PPO 神經網路實戰權重。")
        model = PPO.load("best_crypto_agent")
    else:
        print("未偵測到模型，建立基準防禦模型。")
        model = None
        
    print(f"\n實時監控已啟動 - 每 10 秒掃描一次幣安實體數據流。\n" + "-" * 80)
    
    last_reported_date = {} 
    
    while True:
        live_data = fetch_live_state("BTC/USDT:USDT")
        if live_data is None:
            time.sleep(10)
            continue
            
        raw_change = live_data['price_change']
        live_obs = np.array([
            live_data['oi_rate'], live_data['volume_pump'],
            live_data['price_position'], live_data['htf_price_position'],
            live_data['orderbook_delta']
        ], dtype=np.float32)
        
        action = 0
        if model is not None:
            action, _ = model.predict(live_obs, deterministic=True)
            
        if abs(raw_change) < 0.022:
            action = 0
        elif live_data['is_real_pump'] == 1:
            action = 2
            
        current_date_str = live_data['timestamp'].split(' ')[0]
        ticker = live_data['ticker']
        
        print(f"[{live_data['timestamp']}] 價格: ${live_data['price']:,} | 4H漲跌: {raw_change:.2%} | Agent 決策: {action}")
        
        if action == 2:
            if ticker in last_reported_date and last_reported_date[ticker] == current_date_str:
                print(f"觸發一天一報冷卻機制，今日已通報過，自動維持靜默。")
                time.sleep(10)
                continue
                
            print(f"達到閥值")
            
            prompt_injection = (
                f"請對以下加密貨幣實時異常數據進行理性、專業的微觀資金面與籌碼面診斷，以繁體中文（zh-tw）回答。\n"
                f"【硬性輸出格式鐵律】：您的回答必須嚴格遵守以下格式，不要有環境解釋：\n"
                f"[微觀資金診斷]\n"
                f"（請在此處寫下您對數據的籌碼面與訂單流深度分析...）\n\n"
                f"[行動指導結論]\n"
                f"（請根據分析，為交易員親自撰寫一句話的最終指導，字數40字內，必須明確指出是開多、看空防範、還是空倉觀望。）"
            )
            
            llm_response = tools.call_local_ollama(
                coin_name=f"{ticker} ({live_data['direction']}) -> {prompt_injection}", 
                oi_rate=live_data['oi_rate'], 
                volume_pump=live_data['volume_pump'],
                price_position=live_data['price_position'],
                orderbook_delta=live_data['orderbook_delta']
            )
            
            raw_lines = [line.strip() for line in llm_response.strip().split('\n') if line.strip()]
            conclusion_idx = -1
            for idx, line in enumerate(raw_lines):
                if "[行動指導結論]" in line or "行動指導結論" in line:
                    conclusion_idx = idx
                    break

            final_conclusion = " ".join(raw_lines[conclusion_idx + 1:])
            diagnostic_lines = [l for l in raw_lines[:conclusion_idx] if "[微觀資金診斷]" not in l]
            llm_diagnostic_text = "\n".join(diagnostic_lines)

            if "🟢" not in final_conclusion and "🔴" not in final_conclusion and "🟡" not in final_conclusion:
                final_conclusion = f"🟢 AI判斷結果：{final_conclusion}" if "🟢" in live_data['direction'] else f"🔴 AI判斷結果：{final_conclusion}" if "🔴" in live_data['direction'] else f"🟡 AI判斷結果：{final_conclusion}"
            
            pos_str = f"{live_data['price_position']:.2f} (歷史底部)" if live_data['price_position'] < 0.35 else f"{live_data['price_position']:.2f} (高位山頂)" if live_data['price_position'] > 0.65 else f"{live_data['price_position']:.2f} (區間震盪)"
            htf_pos_str = f"{live_data['htf_price_position']:.2f} (日線大格局底部)" if live_data['htf_price_position'] < 0.4 else f"{live_data['htf_price_position']:.2f} (日線高位警戒區)" if live_data['htf_price_position'] > 0.7 else f"{live_data['htf_price_position']:.2f} (日線波段中軌)"

            alert_msg = (
                f"⚠️ 加密貨幣預警 Agent ⚠️\n\n"
                f"🔔 實時觸發時間: {live_data['timestamp']}\n"
                f"• 監控標的: #{ticker}\n"
                f"• 📊 市場數據表面方向: {live_data['direction']}\n"  
                f"• 💰 當下標的價格: ${live_data['price']:,.4f}\n"  
                f"• 📈 當根K線即時漲跌: {raw_change:.2%}\n"  
                f"• 持倉暴增率: {live_data['oi_rate']:.2%}\n"
                f"• 成交量放大量: {live_data['volume_pump']:.2f} 倍\n"
                f"• 價格形態位置(4H): {pos_str}\n"
                f"• 宏觀趨勢位置(1D): {htf_pos_str}\n"
                f"• 盤口資金流向(Delta): {live_data['orderbook_delta']:.1f}\n\n"
                f"🔍 核心微觀診斷:\n{llm_diagnostic_text}\n\n"
                f"🔥 [最終結論]: {final_conclusion}"
            )
            
            print(f"Telegram 推播完成 結論: {final_conclusion}")
            tools.send_telegram_notification(alert_msg)
            last_reported_date[ticker] = current_date_str
            print("-" * 80)
            
        time.sleep(10)