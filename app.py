# app.py
import streamlit as pd_st
import sqlite3
import pandas as pd
import plotly.express as px
import config

# 設定網頁標題與風格
pd_st.set_page_config(page_title="Crypto Agent 監控儀表板", layout="wide")
pd_st.title("📊 基於強化學習之加密貨幣異動通報優化系統")
pd_st.subheader("系統即時狀態儀表板")

pd_st.success("🟢 當前監控環境：【實驗組】Binance 交易所實體合約數據 (CCXT 即時同步)")

# 連線資料庫讀取數據
try:
    conn = sqlite3.connect(config.DB_REAL)
    df = pd.read_sql("SELECT * FROM market_data_2026", conn)
    conn.close()
    
    if 'action' not in df.columns:
        df['action'] = 0
        df.loc[df['is_real_pump'] == 1, 'action'] = 2
except Exception as e:
    pd_st.error(f"資料庫讀取失敗: {e}")
    df = pd.DataFrame()

if not df.empty:
    total_data = len(df)
    pump_count = int(df['is_real_pump'].sum())
    action_1_count = int((df['action'] == 1).sum())
    action_2_count = int((df['action'] == 2).sum())
    
    col1, col2, col3, col4 = pd_st.columns(4)
    col1.metric("📊 歷史巡檢總時數", f"{total_data} 小時")
    col2.metric("🚨 偵測到莊家建倉點", f"{pump_count} 次")
    col3.metric("🔍 Level 1 輿情探測", f"{action_1_count} 次")
    col4.metric("🤖 Level 2 深度通報", f"{action_2_count} 次")
    
    pd_st.markdown("---")
    
    pd_st.markdown("### 📈 歷史數據回放與指標對齊監控")
    
    unique_tickers = list(df['ticker'].unique()) if 'ticker' in df.columns else []
    selected_ticker = pd_st.selectbox("選擇特定代幣", ["全部資assets池"] + unique_tickers)
    
    if selected_ticker != "全部資產池":
        df_filtered = df[df['ticker'] == selected_ticker].copy()
    else:
        df_filtered = df.copy()
        
    chart_limit = min(150, len(df_filtered))
    df_chart = df_filtered.iloc[0:chart_limit].copy()
    
    fig_line = px.line(
        df_chart, 
        x='timestamp', 
        y=['oi_rate', 'volume_pump'], 
        labels={'value': '指標數值', 'timestamp': '時間軸', 'variable': '指標名稱'},
        title=f"【{selected_ticker}】 持倉暴增率 (OI Rate) 與 成交量放大倍數 趨勢曲線"
    )
    
    fig_line.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    pd_st.plotly_chart(fig_line, width="stretch") 
    
    pd_st.markdown("---")
    
    left_col, right_col = pd_st.columns(2)
    
    with left_col:
        pd_st.markdown("###強化學習 Agent 決策權重比例")
        action_counts = pd.DataFrame({
            '決策動作': ['Level 0 靜默監控', 'Level 1 輿情探測', 'Level 2 深度通報'],
            '觸發次數': [total_data - action_1_count - action_2_count, action_1_count, action_2_count]
        })
        fig_pie = px.pie(
            action_counts, 
            values='觸發次數', 
            names='決策動作', 
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        pd_st.plotly_chart(fig_pie, width="stretch")
        
    with right_col:
        pd_st.markdown("###系統實時通報事件日誌")
        
        target_cols = ['timestamp', 'ticker', 'oi_rate', 'volume_pump']
        display_cols = ['時間軸', '代幣', '持倉暴增率', '成交量放大']
        
        if 'price_position' in df.columns:
            target_cols.append('price_position')
            display_cols.append('微觀位置(4H)')
        if 'htf_price_position' in df.columns:
            target_cols.append('htf_price_position')
            display_cols.append('宏觀位置(1D)')
        if 'orderbook_delta' in df.columns:
            target_cols.append('orderbook_delta')
            display_cols.append('盤口大單流向 (Delta)')
            
        df_alerts = df[df['is_real_pump'] == 1][target_cols].copy()
        
        df_alerts['oi_rate'] = df_alerts['oi_rate'].map(lambda x: f"{x:.2%}")
        df_alerts['volume_pump'] = df_alerts['volume_pump'].map(lambda x: f"{x:.2f} 倍")
        
        if 'price_position' in df.columns:
            df_alerts['price_position'] = df_alerts['price_position'].map(
                lambda x: f"{x:.2f} (底部)" if x < 0.35 else f"{x:.2f} (山頂)" if x > 0.65 else f"{x:.2f} (中軌)"
            )
        if 'htf_price_position' in df.columns:
            df_alerts['htf_price_position'] = df_alerts['htf_price_position'].map(
                lambda x: f"{x:.2f} (宏觀底)" if x < 0.4 else f"{x:.2f} (宏觀頂)" if x > 0.7 else f"{x:.2f} (波段中)"
            )
        if 'orderbook_delta' in df.columns:
            df_alerts['orderbook_delta'] = df_alerts['orderbook_delta'].map(lambda x: f"+{x:.1f}" if x > 0 else f"{x:.1f}")
            
        df_alerts.columns = display_cols
        
        pd_st.dataframe(df_alerts, width="stretch", hide_index=True)

else:
    pd_st.warning("目前資料庫內尚無可供顯示的市場數據。")