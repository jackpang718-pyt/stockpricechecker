import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 1. 網頁基本設定
st.set_page_config(page_title="Gemini 價值投資核心監控", layout="wide")
st.title("📊 2026 價值投資核心資產實時監控 (帶當日最高價記錄)")

# 2. 精確修復香港時間 (HKT)
hk_tz = pytz.timezone('Asia/Hong_Kong')
hk_time = datetime.now(hk_tz)
st.write(f"系統時間 (HKT): {hk_time.strftime('%Y-%m-%d %H:%M:%S')}")

# 3. 定義您的核心自選股名單
WATCHLIST = {
    "Tesla (TSLA)": "TSLA",
    "Apple (AAPL)": "AAPL",
    "Coupang (CPNG)": "CPNG",
    "騰訊控股 (0700)": "0700.HK",
    "阿里巴巴 (9988)": "9988.HK",
    "耀才證券 (1428)": "1428.HK"
}

# 4. 初始化應用的「短期記憶體」
# 如果記憶體中還沒有最高價的記錄字典，就幫它建立一個
if "highest_prices" not in st.session_state:
    st.session_state.highest_prices = {}

# 5. 獲取實時數據並記錄盤中最高價的函數
def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        todays_data = ticker.history(period='1d')
        
        if not todays_data.empty:
            latest_price = todays_data['Close'].iloc[-1]
            open_price = todays_data['Open'].iloc[-1]
            price_change = latest_price - open_price
            pct_change = (price_change / open_price) * 100
            
            # --- 核心新增：動態更新及儲存當日最高價 ---
            # 如果是第一次抓取該股票，或者當前抓到的價格比記憶體中的歷史最高價還要高
            current_saved_high = st.session_state.highest_prices.get(ticker_symbol, 0.0)
            if latest_price > current_saved_high:
                st.session_state.highest_prices[ticker_symbol] = latest_price
                display_high = latest_price
            else:
                display_high = current_saved_high
            # ----------------------------------------
            
            # 獲取價值投資基礎指標
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
                "今日記錄最高價": round(display_high, 2), # 新增此輸出欄位
                "今日漲跌": round(price_change, 2),
                "漲跌幅": f"{round(pct_change, 2)}%",
                "市盈率 (P/E)": round(pe_ratio, 2) if isinstance(pe_ratio, (int, float)) else pe_ratio,
                "市淨率 (P/B)": round(pb_ratio, 2) if isinstance(pb_ratio, (int, float)) else pb_ratio,
                "股息率": div_yield
            }
    except Exception as e:
        return None

# 6. 控制版面組件
col_btn1, col_btn2 = st.columns([1, 8])
with col_btn1:
    if st.button("🔄 刷新數據"):
        st.rerun()
with col_btn2:
    if st.button("🗑️ 重設最高價記錄"):
        st.session_state.highest_prices = {}
        st.rerun()

st.markdown("---")

# 7. 渲染核心持倉看板
st.subheader("核心持倉實時看板 (每點擊刷新將自動對比最高價)")
cols = st.columns(3)

for idx, (name, ticker) in enumerate(WATCHLIST.items()):
    data = get_stock_data(ticker)
    if data:
        with cols[idx % 3]:
            delta_str = f"{data['今日漲跌']} ({data['漲跌幅']})"
            st.metric(
                label=name, 
                value=f"${data['最新股價']}", 
                delta=delta_str
            )
            # 在下方精美地展示今日錄得的最高股價與基本面數據
            st.markdown(f"🔥 **今日監控最高點:** `${data['今日記錄最高價']}`")
            st.caption(f"**P/E:** {data['市盈率 (P/E)']} | **P/B:** {data['市淨率 (P/B)']} | **股息率:** {data['股息率']}")
            st.markdown("---")

# 8. 自定義查詢板塊
st.subheader("🔍 查詢其他股票基本面")
custom_ticker = st.text_input("輸入股票代碼 (例如 NVDA 或 0941.HK):", "").strip()

if custom_ticker:
    with st.spinner("正在檢索數據..."):
        custom_data = get_stock_data(custom_ticker)
        if custom_data:
            st.success(f"成功獲取 {custom_ticker} 的最新數據！")
            st.table(pd.DataFrame([custom_data]))
        else:
            st.error("未能讀取該代碼，請檢查輸入是否正確（港股記得加 .HK）。")
