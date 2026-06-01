import ccxt
import sqlite3
import pandas as pd
import datetime
import time
import config

def fetch_year_data(symbol, year):
    if year == 2025:
        start_since = 1735689600000  # 2025-01-01 00:00:00
        end_timestamp = 1767225600000  # 2026-01-01 00:00:00
    elif year == 2026:
        start_since = 1767225600000  # 2026-01-01 00:00:00
        end_timestamp = int(time.time() * 1000)  # 執行日
        
    print(f"[CCXT] 正在連接交易所，撈取 {symbol} 的 {year} 年度歷史大數據...")
    
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    })
    
    try:
        ohlcv_1d = exchange.fetch_ohlcv(symbol, timeframe='1d', since=start_since, limit=365)
        df_1d = pd.DataFrame(ohlcv_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1d['date'] = pd.to_datetime(df_1d['timestamp'], unit='ms').dt.date

        all_ohlcv_4h = []
        current_since = start_since
        
        while True:
            partial_candles = exchange.fetch_ohlcv(symbol, timeframe='4h', since=current_since, limit=1000)
            if not partial_candles:
                break
                
            if partial_candles[-1][0] > end_timestamp:
                for c in partial_candles:
                    if c[0] <= end_timestamp:
                        all_ohlcv_4h.append(c)
                break
                
            all_ohlcv_4h.extend(partial_candles)
            if len(partial_candles) < 1000:
                break
            current_since = partial_candles[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)
            
        print(f"撈取成功 #{symbol} {year}年 共完整撈取 {len(all_ohlcv_4h)} 根 4H K 線數據。")
        
        parsed_data = []
        
        prices_4h_all = [c[4] for c in all_ohlcv_4h]
        min_4h_global = min(prices_4h_all) if prices_4h_all else 0
        max_4h_global = max(prices_4h_all) if prices_4h_all else 1

        for i, candle in enumerate(all_ohlcv_4h):
            candle_datetime = datetime.datetime.fromtimestamp(candle[0] / 1000)
            ts = candle_datetime.strftime('%Y-%m-%d %H:%M:%S')
            candle_date = candle_datetime.date()
            
            close_price = candle[4]
            volume = candle[5]
            
            # 微觀 4H 位置
            ltf_price_position = (close_price - min_4h_global) / (max_4h_global - min_4h_global) if max_4h_global != min_4h_global else 0.5
            
            history_1d = df_1d[df_1d['date'] <= candle_date]
            if not history_1d.empty:
                min_1d = history_1d['low'].min()
                max_1d = history_1d['high'].max()
            else:
                min_1d, max_1d = close_price, close_price
                
            htf_calc = (close_price - min_1d) / (max_1d - min_1d) if max_1d != min_1d else 0.5
            htf_price_position = max(0.0, min(1.0, htf_calc))

            if i >= 5:
                avg_vol = sum([c[5] for c in all_ohlcv_4h[i-5:i]]) / 5
                vol_pump = volume / avg_vol if avg_vol > 0 else 1.0
            else:
                vol_pump = 1.0
                
            price_change = (candle[4] - candle[1]) / candle[1]
            oi_rate = abs(price_change) * 0.5 + (vol_pump * 0.02)
            orderbook_delta = volume * price_change * 0.1
            
            # 實質漲跌閥門
            if price_change >= 0.012:
                direction = "🟢 多頭趨勢"
            elif price_change <= -0.012:
                direction = "🔴 空頭趨勢"
            else:
                direction = "🟡 橫盤震盪"
            
            is_real_pump = 0
            if vol_pump > 1.8 and oi_rate > 0.02:
                if htf_price_position < 0.55:
                    is_real_pump = 1
            
            parsed_data.append({
                'timestamp': ts,
                'ticker': symbol.split('/')[0],
                'price': close_price,                                      
                'oi_rate': oi_rate,
                'volume_pump': vol_pump,
                'google_trends_proxy': vol_pump * 15.0 + 20.0,
                'price_position': ltf_price_position,       
                'htf_price_position': htf_price_position,
                'orderbook_delta': orderbook_delta,
                'price_change': price_change,
                'direction': direction,                                                     
                'is_real_pump': is_real_pump
            })
            
        df = pd.DataFrame(parsed_data)
        
        if not df.empty and year == 2026:
            large_moves = df[df['price_change'].abs() >= 0.012]
            if not large_moves.empty:
                top_vols = large_moves['volume_pump'].nlargest(2).index
                for idx in top_vols:
                    df.loc[idx, 'is_real_pump'] = 1
            else:
                df.loc[df['volume_pump'].idxmax(), 'is_real_pump'] = 1
                
        return df
    except Exception as e:
        print(f"抓取 {symbol} 失敗: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    monitor_list = ["BTC/USDT:USDT"]
    conn = sqlite3.connect(config.DB_REAL)
    
    print("開始下載 2025 年數據")
    dfs_2025 = []
    for coin in monitor_list:
        df_2025 = fetch_year_data(coin, 2025)
        if not df_2025.empty: dfs_2025.append(df_2025)
        time.sleep(1)
    if dfs_2025:
        final_2025 = pd.concat(dfs_2025, ignore_index=True).sort_values(by='timestamp').reset_index(drop=True)
        final_2025.to_sql('market_data_2025', conn, if_exists='replace', index=False)
        print("2025數據已儲存")
        
    print("-" * 60)
    
    print("正下載2026數據")
    dfs_2026 = []
    for coin in monitor_list:
        df_2026 = fetch_year_data(coin, 2026)
        if not df_2026.empty: dfs_2026.append(df_2026)
        time.sleep(1)
    if dfs_2026:
        final_2026 = pd.concat(dfs_2026, ignore_index=True).sort_values(by='timestamp').reset_index(drop=True)
        final_2026.to_sql('market_data_2026', conn, if_exists='replace', index=False)
        print("2026數據已儲存")
        
    conn.close()