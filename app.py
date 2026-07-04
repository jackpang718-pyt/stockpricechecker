import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. 網頁基本設定
st.set_page_config(page_title="65歲200萬退休衝刺系統", layout="wide")
st.title("🎯 65歲退休資產與每月$1萬被動收入衝刺儀表板 (Google Sheet 聯動版)")

# --- 💡 請在下方貼上您的 Google Sheet 網址 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/11vTIsQ8OIGLAqrVcp4nPk7ONRpEL6plSGq3F73IYLMQ/edit?usp=sharing"

# 自動刷新：每 60 秒刷新一次
st_autorefresh(interval=60000, limit=None, key="retirement_refresh")

# 香港時間設定
hk_tz = pytz.timezone('Asia/Hong_Kong')
hk_time = datetime.now(hk_tz)
st.write(f"系統時間 (HKT): **{hk_time.strftime('%Y-%m-%d %H:%M:%S')}** | 🔄 每 60 秒與 Google Sheet 及交易所同步中...")

# 2. 自動顯示股票名稱的內置對照表 (您可以根據名單自由在下方增減)
STOCK_NAME_MAP = {
    "TSLA": "特斯拉 (Tesla)",
    "NVDA": "輝達 (Nvidia)",
    "AAPL": "蘋果 (Apple)",
    "CPNG": "酷澎 (Coupang)",
    "0700.HK": "騰訊控股",
    "9988.HK": "阿里巴巴",
    "1428.HK": "耀才證券",
    "1299.HK": "友邦保險",
    "2800.HK": "盈富基金"
}

# 3. 轉換 Google Sheet 網址為 CSV 下載格式的函數
def convert_google_sheet_url(url):
    try:
        if "navchanges" in url:
            url = url.split("&navchanges")[0]
        base_url = url.split("/edit")[0]
        return f"{base_url}/export?format=csv"
    except:
        return None

# 4. 讀取 Google Sheet 數據
@st.cache_data(ttl=60)  # 緩存 60 秒，避免每秒重覆請求 Google
def load_portfolio_from_sheets(url):
    csv_url = convert_google_sheet_url(url)
    try:
        df = pd.read_csv(csv_url)
        # 確保欄位名稱乾淨沒有空格
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"讀取 Google Sheet 失敗，請檢查權限是否已開啟為「任何人均可檢視」。錯誤資訊: {e}")
        return pd.DataFrame()

# 5. 獲取實時價格與股息率函數
def fetch_stock_price(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        todays_data = ticker.history(period='1d')
        if not todays_data.empty:
            latest_price = todays_data['Close'].iloc[-1]
            info = ticker.info
            div_yield = info.get('dividendYield', 0.0) if info.get('dividendYield') else 0.0
            return latest_price, div_yield
    except:
        return None, 0.0
    return None, 0.0

# 6. 核心業務邏輯計算
TARGET_CAPITAL = 2000000.0  
TARGET_MONTHLY_INCOME = 10000.0  
USD_HKD = 7.8

df_sheet = load_portfolio_from_sheets(GOOGLE_SHEET_URL)

if not df_sheet.empty:
    total_portfolio_value_hkd = 0.0
    estimated_annual_dividend_hkd = 0.0
    portfolio_details = []

    with st.spinner("正在即時同步雲端持倉與華爾街數據..."):
        for index, row in df_sheet.iterrows():
            # 讀取試算表的三個核心欄位
            ticker = str(row['stock code']).strip()
            shares = float(row['share'])
            cost = float(row['cost'])
            
            # 判斷市場類型 (美股或港股)
            is_us = not ticker.endswith(".HK")
            
            # 自動匹配股票名稱，如果對照表沒有，就顯示代碼本身
            stock_name = STOCK_NAME_MAP.get(ticker, f"未知名單 ({ticker})")
            
            price, div_y = fetch_stock_price(ticker)
            
            if price:
                if is_us:
                    value_hkd = price * shares * USD_HKD
                    current_price_display = f"${round(price, 2)} USD"
                    cost_display = f"${round(cost, 2)} USD"
                else:
                    value_hkd = price * shares
                    current_price_display = f"${round(price, 2)} HKD"
                    cost_display = f"${round(cost, 2)} HKD"
                
                total_portfolio_value_hkd += value_hkd
                estimated_annual_dividend_hkd += (value_hkd * div_y)
                
                # 計算單隻股票的賺蝕幅度
                gain_loss_pct = ((price - cost) / cost) * 100 if cost > 0 else 0.0
                
                portfolio_details.append({
                    "股票名稱": stock_name,
                    "股票代碼": ticker,
                    "持股數量": shares,
                    "買入成本": cost_display,
                    "目前市價": current_price_display,
                    "持倉總值 (HKD)": round(value_hkd, 2),
                    "帳面回報率": f"{round(gain_loss_pct, 2)}%",
                    "預估股息率": f"{round(div_y * 100, 2)}%"
                })

    st.markdown("---")

    # 7. 渲染退休大盤指標
    st.subheader("🏁 65歲退休目標達成率看板")
    cap_progress = min(total_portfolio_value_hkd / TARGET_CAPITAL, 1.0)
    current_monthly_income = estimated_annual_dividend_hkd / 12.0
    income_progress = min(current_monthly_income / TARGET_MONTHLY_INCOME, 1.0)

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="當前組合總市值 (HKD)", value=f"${round(total_portfolio_value_hkd, 2)}", 
                  delta=f"距離200萬目標還差: ${round(max(TARGET_CAPITAL - total_portfolio_value_hkd, 0.0), 2)}")
        st.progress(cap_progress, text=f"本金進度: {round(cap_progress * 100, 2)}%")

    with col2:
        st.metric(label="預估現狀每月被動收入 (HKD)", value=f"${round(current_monthly_income, 2)}", delta="退休目標: 每月 $10,000")
        st.progress(income_progress, text=f"被動收入進度: {round(income_progress * 100, 2)}%")

    st.markdown("---")

    # 8. 持倉明細表格 (現在包含精美的股票名稱)
    st.subheader("📋 雲端聯動 · 真實資產明細表")
    df_display = pd.DataFrame(portfolio_details)
    st.dataframe(df_display, use_container_width=True)
    
    # 9. 溫馨提示
    st.info(f"💡 **看盤備忘錄**：資產已完成 200 萬目標的 **{round(cap_progress * 100, 1)}%**。如果新買入了股票，只需直接在手機上修改 Google Sheet，此儀表板會自動同步。")
else:
    st.warning("請確保您的 Google Sheet 網址正確，且包含 stock code, share, cost 三個欄位。")
