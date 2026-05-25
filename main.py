import time
import os
import datetime
import sqlite3
import re
import pandas as pd
from stable_baselines3 import PPO
from env import CryptoAgentEnv
import tools
import config

if __name__ == "__main__":
    print("=== 加密貨幣預警 ===")
    
    env = CryptoAgentEnv()
    conn = sqlite3.connect(config.DB_REAL)
    env.df = pd.read_sql_query("SELECT * FROM market_data_2026", conn)
    conn.close()
    env.max_steps = len(env.df) - 1
    
    model_path = "best_crypto_agent.zip"
    if os.path.exists(model_path):
        print(f"已載入模型")
        model = PPO.load("best_crypto_agent", env=env)
    else:
        print("未偵測到模型")
        exit()
        
    print(f"\nrunning\n")
    print("-" * 80)
    
    obs, _ = env.reset()
    done = False
    total_alerts_sent = 0 
    last_reported_date = {} 
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        current_data = env.df.iloc[env.current_step]
        
        raw_change = current_data.get('price_change', 0.0)
        
        # 閥值2.2%
        if abs(raw_change) < 0.022:
            action = 0
        elif current_data['is_real_pump'] == 1:
            action = 2
            
        if action > 0:
            if action == 2:
                current_date_str = current_data['timestamp'].split(' ')[0]
                ticker = current_data['ticker']
                
                # 一天一報
                if ticker in last_reported_date and last_reported_date[ticker] == current_date_str:
                    obs, reward, done, _, _ = env.step(action)
                    continue
                    
                print(f"達到閥值 時間: {current_data['timestamp']} | Ticker: {ticker} (實質漲跌: {raw_change:.2%})")
                
                current_real_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                current_price = current_data.get('price', 'N/A')
                price_display = f"${current_price:,.4f}" if isinstance(current_price, (int, float)) else str(current_price)
                change_display = f"{raw_change:.2%}"
                
                pos_str = f"{current_data['price_position']:.2f} (歷史底部)" if current_data['price_position'] < 0.35 else f"{current_data['price_position']:.2f} (高位山頂)" if current_data['price_position'] > 0.65 else f"{current_data['price_position']:.2f} (區間震盪)"
                htf_pos_str = f"{current_data['htf_price_position']:.2f} (日線大格局底部)" if current_data['htf_price_position'] < 0.4 else f"{current_data['htf_price_position']:.2f} (日線高位警戒區)" if current_data['htf_price_position'] > 0.7 else f"{current_data['htf_price_position']:.2f} (日線波段中軌)"
                
                market_dir = current_data.get('direction', '🟡 橫盤震盪/主力洗盤')
                
                prompt_injection = (
                    f"請對以下加密貨幣異常數據進行理性、專業的微觀資金面與籌碼面診斷，以繁體中文（zh-tw）回答。\n"
                    f"【硬性輸出格式鐵律】：您的回答必須嚴格遵守以下格式，不要有任何多餘的解釋文字：\n"
                    f"[微觀資金診斷]\n"
                    f"（請在此處寫下您對數據的籌碼面與訂單流深度分析...）\n\n"
                    f"[行動指導結論]\n"
                    f"（請根據分析，為交易員親自撰寫一句話的最終指導，字數40字內，必須明確指出是開多、看空防範、還是空倉觀望。）"
                )
                
                llm_response = tools.call_local_ollama(
                    coin_name=f"{ticker} ({market_dir}) -> {prompt_injection}", 
                    oi_rate=current_data['oi_rate'], 
                    volume_pump=current_data['volume_pump'],
                    price_position=current_data['price_position'],
                    orderbook_delta=current_data['orderbook_delta']
                )
                
                raw_lines = [line.strip() for line in llm_response.strip().split('\n') if line.strip()]
                
                llm_diagnostic_text = ""
                final_conclusion = ""
                
                conclusion_idx = -1
                for idx, line in enumerate(raw_lines):
                    if "[行動指導結論]" in line or "行動指導結論" in line:
                        conclusion_idx = idx
                        break

                final_conclusion = " ".join(raw_lines[conclusion_idx + 1:])
                diagnostic_lines = [l for l in raw_lines[:conclusion_idx] if "[微觀資金診斷]" not in l]
                llm_diagnostic_text = "\n".join(diagnostic_lines)
                

                if "🟢" not in final_conclusion and "🔴" not in final_conclusion and "🟡" not in final_conclusion:
                    if "🟢" in market_dir:
                        final_conclusion = f"🟢 AI判斷結果：{final_conclusion}"
                    elif "🔴" in market_dir:
                        final_conclusion = f"🔴 AI判斷結果：{final_conclusion}"
                    else:
                        final_conclusion = f"🟡 AI判斷結果：{final_conclusion}"
                
                alert_msg = (
                    f"⚠️ 加密貨幣預警 Agent ⚠️\n\n"
                    f"🔔 警報發送時間: {current_real_time}\n"
                    f"• 監控標的: #{ticker}\n"
                    f"• 📊 市場數據表面方向: {market_dir}\n"  
                    f"• 💰 當下標的價格: {price_display}\n"  
                    f"• 📈 當根K線真實漲跌: {change_display}\n"  
                    f"• 數據歷史時間: {current_data['timestamp']}\n"  
                    f"• 持倉暴增率: {current_data['oi_rate']:.2%}\n"
                    f"• 成交量放大量: {current_data['volume_pump']:.2f} 倍\n"
                    f"• 價格形態位置(4H): {pos_str}\n"
                    f"• 宏觀趨勢位置(1D): {htf_pos_str}\n"
                    f"• 盤口資金流向(Delta): {current_data['orderbook_delta']:.1f}\n\n" # 👈 這裡已完美斬斷假資料
                    f"🔍 核心微觀診斷:\n{llm_diagnostic_text}\n\n"
                    f"🔥 [最終結論]: {final_conclusion}"
                )
                
                print(f"📝 Ollama 結論: {final_conclusion}")
                tools.send_telegram_notification(alert_msg)
                
                last_reported_date[ticker] = current_date_str
                total_alerts_sent += 1
                print(f"已發送 {total_alerts_sent} 份訊息")
                print("-" * 80)
                
                if total_alerts_sent >= 40:
                    print("\n💡 [安全防禦機制] 已達到最大通報上限，系統安全關閉。")
                    break
                
                time.sleep(0.5)  
            
        obs, reward, done, _, _ = env.step(action)
        
    print("\n已完成歷史回測")