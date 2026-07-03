import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="Gemini 價值投資核心監控", layout="wide")
st.title("📊 2026 價值投資核心資產實時監控")
st.write(f"系統時間 (HKT): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 2. 定義您的核心自選股名單 (美股直接輸入代碼，港股用 0700.HK 格式)
WATCHLIST = {
    "Tesla (TSLA)": "TSLA",
    "Apple (AAPL)": "AAPL",
    "Coupang (CPNG)": "CPNG",
    "騰訊控股 (0700)": "0700.HK",
    "阿里巴巴 (9988)": "9988.HK",
    "耀才證券 (1428)": "1428.HK"
}

# 3. 獲取實時數據的函數
def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        # 獲取最新一天的交易數據
        todays_data = ticker.history(period='1d')
        if not todays_data.empty:
            latest_price = todays_data['Close'].iloc[-1]
            open_price = todays_data['Open'].iloc[-1]
            price_change = latest_price - open_price
            pct_change = (price_change / open_price) * 100
            
            # 獲取價值投資看重的基本面數據 (部分海外或港股數據可能視乎Yahoo更新)
            info = ticker.info
            pe_ratio = info.get('trailingPE', 'N/A')
            pb_ratio = info.get('priceToBook', 'N/A')
            div_yield = info.get('dividendYield', 0)
            if div_yield and div_yield != 'N/A':
                div_yield = f"{round(div_yield * 100, 2)}%"
            else:
                div_yield = "無派息/暫無數據"
                
            return {
                "最新股價": round(latest_price, 2),
                "今日漲跌": round(price_change, 2),
                "漲跌幅": f"{round(pct_change, 2)}%",
                "市盈率 (P/E)": round(pe_ratio, 2) if isinstance(pe_ratio, (int, float)) else pe_ratio,
                "市淨率 (P/B)": round(pb_ratio, 2) if isinstance(pb_ratio, (int, float)) else pb_ratio,
                "股息率": div_yield
            }
    except Exception as e:
        return None

# 4. 介面頂部加一個手動刷新按鈕
if st.button("🔄 點擊刷新最新股價"):
    st.rerun()

st.markdown("---")

# 5. 用「卡片 (Metrics)」形式展示美股與港股大廠
st.subheader("核心持倉實時看板")
cols = st.columns(3)

for idx, (name, ticker) in enumerate(WATCHLIST.items()):
    data = get_stock_data(ticker)
    if data:
        with cols[idx % 3]:
            # 根據漲跌調整顏色顯示
            delta_str = f"{data['今日漲跌']} ({data['漲跌幅']})"
            st.metric(
                label=name, 
                value=f"${data['最新股價']}", 
                delta=delta_str
            )
            # 顯示價值投資者關心的安全邊際指標
            st.caption(f"**P/E:** {data['市盈率 (P/E)']} | **P/B:** {data['市淨率 (P/B)']} | **股息率:** {data['股息率']}")
            st.markdown("---")

# 6. 自定義查詢板塊
st.subheader("🔍 查詢其他股票基本面")
custom_ticker = st.text_input("輸入股票代碼 (例如 NVDA 或 0941.HK):", "").strip()

if custom_ticker:
    with st.spinner("正在檢索華爾街與港交所數據..."):
        custom_data = get_stock_data(custom_ticker)
        if custom_data:
            st.success(f"成功獲取 {custom_ticker} 的最新數據！")
            st.table(pd.DataFrame([custom_data]))
        else:
            st.error("未能讀取該代碼，請檢查輸入是否正確（港股記得加 .HK）。")
