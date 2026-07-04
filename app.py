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
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/您的試算表ID/edit?usp=sharing"

# 自動刷新：每 60 秒刷新一次
st_autorefresh(interval=60000, limit=None, key="retirement_refresh")

# 香港時間設定
hk_tz = pytz.timezone('Asia/Hong_Kong')
hk_time = datetime.now(hk_tz)
st.write(f"系統時間 (HKT): **{hk_time.strftime('%Y-%m-%d %H:%M:%S')}** | 🔄 顏色視覺增強版同步中...")

# 2. Google Sheet 網址格式轉換器
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
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error("❌ 無法連線至您的 Google Sheet，請檢查共用權限。")
        return pd.DataFrame()

# 4. 自動將 Google 格式 (HKG:0700) 翻譯為 Yahoo 格式 (0700.HK)
def convert_ticker_for_yahoo(sheet_ticker):
    ticker = str(sheet_ticker).strip().upper()
    if ticker.startswith("HKG:"):
        code = ticker.split("HKG:")[1].strip()
        return f"{code}.HK"
    elif ticker.isdigit() and len(ticker) == 4:
        return f"{ticker}.HK"
    return ticker

# 5. 獲取實時數據
def fetch_stock_data(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='1d')
        if not hist.empty:
            return hist['Close'].iloc[-1], t.info.get('dividendYield', 0.0) or 0.0
    except:
        return None, 0.0
    return None, 0.0

# 手動強制刷新按鈕
col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("⚡ 立即強行同步雲端"):
        st.cache_data.clear()
        st.rerun()

# 執行讀取
df_sheet = load_portfolio(GOOGLE_SHEET_URL)

if not df_sheet.empty:
    required_cols = ['stock code', 'stock name', 'share', 'cost']
    if not all(col in df_sheet.columns for col in required_cols):
        st.error(f"❌ 欄位名稱不符！目前偵測到的是: {list(df_sheet.columns)}")
    else:
        total_value_hkd = 0.0
        total_dividend_hkd = 0.0
        portfolio_details = []
        USD_HKD = 7.8
        
        with st.spinner("🚀 正在為您精算即時賺蝕與帳面回報..."):
            for _, row in df_sheet.iterrows():
                sheet_ticker = str(row['stock code']).strip()
                stock_name = str(row['stock name']).strip()
                shares = float(row['share'])
                cost = float(row['cost'])
                
                yahoo_ticker = convert_ticker_for_yahoo(sheet_ticker)
                is_us = not yahoo_ticker.endswith(".HK")
                
                price, div_y = fetch_stock_data(yahoo_ticker)
                
                if price:
                    # 計算港幣總市值
                    value_hkd = (price * shares * USD_HKD) if is_us else (price * shares)
                    # 計算總成本 (港幣)
                    total_cost_hkd = (cost * shares * USD_HKD) if is_us else (cost * shares)
                    
                    total_value_hkd += value_hkd
                    total_dividend_hkd += (value_hkd * div_y)
                    
                    # 核心新增：計算「帳面回報價（HKD）」與「帳面回報率」
                    gain_loss_price_hkd = value_hkd - total_cost_hkd
                    gain_pct = ((price - cost) / cost) * 100 if cost > 0 else 0.0
                    
                    portfolio_details.append({
                        "股票名稱": stock_name,
                        "股票代碼": sheet_ticker,
                        "持股數量": shares,
                        "買入成本": f"${round(cost,2)} {'USD' if is_us else 'HKD'}",
                        "目前市價": f"${round(price,2)} {'USD' if is_us else 'HKD'}",
                        "持倉總值 (HKD)": round(value_hkd, 2),
                        "帳面回報價 (HKD)": round(gain_loss_price_hkd, 2),
                        "帳面回報率": round(gain_pct, 2),
                        "預估股息率": f"{round(div_y * 100, 2)}%"
                    })
        
        # 6. 渲染大盤指標
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
        
        # 7. 核心視覺功能：使用 Pandas Styler 為指定欄位著色
        df_display = pd.DataFrame(portfolio_details)
        
        def color_gain_loss(val):
            try:
                numeric_val = float(val)
                if numeric_val > 0:
                    return 'color: #00AD45; font-weight: bold;'  # 獲利顯示綠色
                elif numeric_val < 0:
                    return 'color: #FF3B30; font-weight: bold;'  # 虧損顯示紅色
            except:
                pass
            return ''

        # 格式化顯示效果，為百分比加上 % 正負號字尾
        styled_df = df_display.style.applymap(color_gain_loss, subset=["帳面回報價 (HKD)", "帳面回報率"])\
                                    .format({"帳面回報率": "{:+.2f}%", 
                                             "帳面回報價 (HKD)": "{:+,2f}"})
        
        # 將帶有紅綠色彩的精美表格渲染至網頁上
        st.dataframe(styled_df, use_container_width=True)
