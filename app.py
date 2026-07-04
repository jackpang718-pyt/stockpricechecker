import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. 網頁基本設定
st.set_page_config(page_title="65歲200萬退休衝刺系統", layout="wide")
st.title("🎯 65歲退休資產與每月$1萬被動收入衝刺儀表板 (Google Sheet 同步版)")

# 自動刷新：每 60 秒 (60000 毫秒) 刷新一次整個網頁
refresh_count = st_autorefresh(interval=60000, limit=None, key="retirement_refresh")

# 香港時間設定
hk_tz = pytz.timezone('Asia/Hong_Kong')
hk_time = datetime.now(hk_tz)
st.write(f"系統時間 (HKT): **{hk_time.strftime('%Y-%m-%d %H:%M:%S')}** | 🔄 已自動更新: `{refresh_count}` 次")

# 2. 【核心修改】連接您的 Google Sheet
# ⚠️ 請把下面這行引號內的網址，替換成您真實的 Google Sheet 共用網址
GOOGLE_SHEET_URL = "YOUR_GOOGLE_SHEET_URL_HERE"

# 將標準 Google Sheet 網址轉換為 CSV 匯出格式，方便 Python 直接讀取
def convert_google_sheet_url(url):
    if "docs.google.com" in url and "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv"
    return url

# 3. 獲取實時價格、股息率以及【股票名稱】的函數
@st.cache_data(ttl=3600)  # 緩存股票名稱以加快載入速度，每小時更新一次
def fetch_stock_static_info(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        stock_name = info.get('longName', ticker_symbol)
        # 如果是港股，嘗試抓取更友善的名稱，若無則用 longName
        if ".HK" in ticker_symbol:
            stock_name = info.get('shortName', stock_name)
        return stock_name
    except:
        return ticker_symbol

def fetch_stock_live_price(ticker_symbol):
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

# 4. 讀取 Google Sheet 數據
try:
    csv_url = convert_google_sheet_url(GOOGLE_SHEET_URL)
    sheet_data = pd.read_csv(csv_url)
    
    # 清洗數據欄位前後的空格，確保配對正確
    sheet_data.columns = sheet_data.columns.str.strip().str.lower()
    
    total_portfolio_value_hkd = 0.0
    estimated_annual_dividend_hkd = 0.0
    portfolio_details = []
    USD_HKD = 7.8  # 港元兌美金基準匯率
    
    TARGET_CAPITAL = 2000000.0
    TARGET_MONTHLY_INCOME = 10000.0

    with st.spinner("正在同步 Google Sheet 並計算退休金實時進度..."):
        for index, row in sheet_data.iterrows():
            ticker = str(row['stock code']).strip()
            shares = float(row['share'])
            cost = float(row['cost'])
            
            # 自動判斷市場類型
            market_type = "HK" if ".HK" in ticker or ticker.isdigit() else "US"
            # 修正純數字港股代碼（例如輸入 0700 自動補上 .HK）
            if ticker.isdigit():
                ticker = f"{ticker.zfill(4)}.HK"
            
            # 抓取靜態名稱與動態價格
            stock_name = fetch_stock_static_info(ticker)
            price, div_y = fetch_stock_live_price(ticker)
            
            if price:
                if market_type == "US":
                    value_hkd = price * shares * USD_HKD
                    current_price_display = f"${round(price, 2)} USD"
                    cost_display = f"${round(cost, 2)} USD"
                else:
                    value_hkd = price * shares
                    current_price_display = f"${round(price, 2)} HKD"
                    cost_display = f"${round(cost, 2)} HKD"
                
                total_portfolio_value_hkd += value_hkd
                estimated_annual_dividend_hkd += (value_hkd * div_y)
                
                # 計算單隻股票的賺蝕盈虧 (% )
                profit_loss_pct = ((price - cost) / cost) * 100
                
                portfolio_details.append({
                    "Stock Code (代碼)": ticker,
                    "Stock Name (公司名稱)": stock_name,
                    "Shares (持股)": shares,
                    "Cost (成本)": cost_display,
                    "Live Price (現價)": current_price_display,
                    "Total Value (市值 HKD)": round(value_hkd, 2),
                    "盈虧幅 (%)": f"{round(profit_loss_pct, 2)}%",
                    "Yield (預估股息率)": f"{round(div_y * 100, 2)}%"
                })

    # 5. 【看板主介面】三大退休指標
    st.markdown("---")
    st.subheader("🏁 65歲退休目標達成率")

    cap_progress = min(total_portfolio_value_hkd / TARGET_CAPITAL, 1.0)
    current_monthly_income = estimated_annual_dividend_hkd / 12.0
    income_progress = min(current_monthly_income / TARGET_MONTHLY_INCOME, 1.0)

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="當前雲端組合總市值 (HKD)", value=f"${round(total_portfolio_value_hkd, 2)}", 
                  delta=f"距離200萬目標還差: ${round(max(TARGET_CAPITAL - total_portfolio_value_hkd, 0.0), 2)}")
        st.progress(cap_progress, text=f"本金進度: {round(cap_progress * 100, 2)}%")

    with col2:
        st.metric(label="預估現狀每月被動收入 (HKD)", value=f"${round(current_monthly_income, 2)}", 
                  delta="退休目標: 每月 $10,000")
        st.progress(income_progress, text=f"被動收入進度: {round(income_progress * 100, 2)}%")

    st.markdown("---")

    # 6. 持倉明細表格（新增了自動獲取的 Stock Name）
    st.subheader("📋 雲端實時資產清單明細 (自動對齊名稱)")
    df = pd.DataFrame(portfolio_details)
    st.dataframe(df, use_container_width=True)

    # 7. 退休策略導航
    st.subheader("💡 退休衝刺動態建議")
    if total_portfolio_value_hkd < TARGET_CAPITAL:
        st.info(f"您好，目前進度條已加載。現有資產已完成 65 歲目標的 **{round(cap_progress * 100, 1)}%**。現在持股名稱已自動從華爾街/港交所同步。您可以直接在 Google Sheet 增減您的 Share 或調整 Cost，App 每 60 秒會自動為您重新計算盈虧與進度。")
    else:
        st.success("🎉 恭喜！雲端總資產規模已成功跨越 200 萬港元大關！建議逐步鎖定高息防禦資產以確保每月 1 萬被動收入的絕對穩定。")

except Exception as e:
    st.error("無法讀取 Google Sheet 數據，請檢查：")
    st.write("1. 您的 `GOOGLE_SHEET_URL` 是否正確填寫。")
    st.write("2. Google Sheet 是否已開啟「知道連結的任何人均可檢視」權限。")
    st.write("3. 表頭第一行是否精確為 `stock code`, `share`, `cost`。")
