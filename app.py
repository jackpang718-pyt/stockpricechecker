import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. 網頁基本設定
st.set_page_config(page_title="65歲200萬退休衝刺系統", layout="wide")
st.title("🎯 65歲退休資產與每月$1萬被動收入衝刺儀表板")

# --- 💡 請在此處精確貼上您的 Google Sheet 網址 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/11vTIsQ8OIGLAqrVcp4nPk7ONRpEL6plSGq3F73IYLMQ/edit?usp=sharing"

# 自動刷新：每 60 秒刷新一次
st_autorefresh(interval=60000, limit=None, key="retirement_refresh")

# 香港時間設定
hk_tz = pytz.timezone('Asia/Hong_Kong')
hk_time = datetime.now(hk_tz)
st.write(f"系統時間 (HKT): **{hk_time.strftime('%Y-%m-%d %H:%M:%S')}** | 🔄 全自動同步中...")

# 2. 強化版 Google Sheet 網址格式轉換器
def get_csv_download_url(url):
    try:
        if "/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    except:
        return None
    return None

# 3. 讀取數據
@st.cache_data(ttl=30)
def load_portfolio(url):
    csv_url = get_csv_download_url(url)
    if not csv_url:
        st.error("❌ Google Sheet 網址解析失敗")
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_url)
        # 統一將欄位名稱清理並轉為小寫
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error("❌ 無法連線至您的 Google Sheet，請檢查共用權限是否已設定為「任何人均可檢視」。")
        return pd.DataFrame()

# 4. 獲取實時數據
def fetch_stock_data(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='1d')
        if not hist.empty:
            return hist['Close'].iloc[-1], t.info.get('dividendYield', 0.0) or 0.0
    except:
        return None, 0.0
    return None, 0.0

# 控制清除緩存的強制刷新按鈕
col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("⚡ 立即強行同步雲端"):
        st.cache_data.clear()
        st.rerun()

# 執行讀取
df_sheet = load_portfolio(GOOGLE_SHEET_URL)

if not df_sheet.empty:
    # 檢查必填欄位
    required_cols = ['stock code', 'stock name', 'share', 'cost']
    if not all(col in df_sheet.columns for col in required_cols):
        st.error(f"❌ 您的 Google Sheet 頂部欄位名稱不符！目前偵測到的是: {list(df_sheet.columns)}")
        st.info("💡 **請修正 Google Sheet 第一行**，精確填入這四個小寫標題：`stock code`、`stock name`、`share`、`cost`")
    else:
        total_value_hkd = 0.0
        total_dividend_hkd = 0.0
        portfolio_details = []
        USD_HKD = 7.8
        
        with st.spinner("🚀 正在為您同步全球交易所最新數據..."):
            for _, row in df_sheet.iterrows():
                ticker = str(row['stock code']).strip()
                # 直接讀取 Google Sheet 裡的中文或英文股票名稱
                stock_name = str(row['stock name']).strip()
                shares = float(row['share'])
                cost = float(row['cost'])
                
                is_us = not ticker.endswith(".HK")
                price, div_y = fetch_stock_data(ticker)
                
                if price:
                    value_hkd = (price * shares * USD_HKD) if is_us else (price * shares)
                    total_value_hkd += value_hkd
                    total_dividend_hkd += (value_hkd * div_y)
                    
                    gain_pct = ((price - cost) / cost) * 100 if cost > 0 else 0.0
                    
                    portfolio_details.append({
                        "股票名稱": stock_name,
                        "股票代碼": ticker,
                        "持股數量": shares,
                        "買入成本": f"${round(cost,2)} {'USD' if is_us else 'HKD'}",
                        "目前市價": f"${round(price,2)} {'USD' if is_us else 'HKD'}",
                        "持倉總值 (HKD)": round(value_hkd, 2),
                        "帳面回報率": f"{round(gain_pct, 2)}%",
                        "預估股息率": f"{round(div_y * 100, 2)}%"
                    })
        
        # 5. 渲染退休大盤指標
        TARGET_CAPITAL = 2000000.0
        TARGET_MONTHLY = 10000.0
        
        st.subheader("🏁 65歲退休目標達成率看板")
        cap_progress = min(total_value_hkd / TARGET_CAPITAL, 1.0)
        current_monthly = (total_dividend_hkd / 12.0)
        income_progress = min(current_monthly / TARGET_MONTHLY, 1.0)
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric(label="當前組合總市值 (HKD)", value=f"${round(total_value_hkd, 2)}", 
                      delta=f"距離200萬目標還差: ${round(max(TARGET_CAPITAL - total_value_hkd, 0.0), 2)}")
            st.progress(cap_progress, text=f"本金進度: {round(cap_progress * 100, 2)}%")
        with c2:
            st.metric(label="預估現狀每月被動收入 (HKD)", value=f"${round(current_monthly, 2)}", delta="退休目標: 每月 $10,000")
            st.progress(income_progress, text=f"被動收入進度: {round(income_progress * 100, 2)}%")
            
        st.markdown("---")
        st.subheader("📋 雲端聯動 · 真實資產明細表")
        st.dataframe(pd.DataFrame(portfolio_details), use_container_width=True)
