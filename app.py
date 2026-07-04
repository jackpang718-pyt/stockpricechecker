import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. 網頁基本設定
st.set_page_config(page_title="65歲200萬退休衝刺系統", layout="wide")
st.title("🎯 65歲退休資產與每月$1萬被動收入衝刺儀表板")

# 自動刷新：每 60 秒 (60000 毫秒) 刷新一次
refresh_count = st_autorefresh(interval=60000, limit=None, key="retirement_refresh")

# 香港時間設定
hk_tz = pytz.timezone('Asia/Hong_Kong')
hk_time = datetime.now(hk_tz)
st.write(f"系統時間 (HKT): **{hk_time.strftime('%Y-%m-%d %H:%M:%S')}** | 🔄 已自動更新: `{refresh_count}` 次")

st.markdown("---")

# 2. 【核心設定】請在下方輸入您實際持有的股票數量 (此處為模擬數字，可自由修改)
# 您可以隨時在代碼中修改這些數字，以反映您真實的持倉
MY_PORTFOLIO = {
    "TSLA": {"shares": 40, "cost": 215.0, "type": "US"},
    "AAPL": {"shares": 10, "cost": 212.0, "type": "US"},
    "NVDA": {"shares": 50, "cost": 105.0, "type": "US"},
    "0700.HK": {"shares": 300, "cost": 463.0, "type": "HK"},
    "9988.HK": {"shares": 1000, "cost": 105.0, "type": "HK"}
}

# 退休目標設定
TARGET_CAPITAL = 2000000.0  # 200萬港元
TARGET_MONTHLY_INCOME = 10000.0  # 每月1萬被動收入

# 3. 獲取實時價格函數
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

# 4. 計算資產總值與進度
total_portfolio_value_hkd = 0.0
estimated_annual_dividend_hkd = 0.0
portfolio_details = []

# 假設美金兌港元匯率為 7.8
USD_HKD = 7.8

with st.spinner("正在計算您的退休金實時進度..."):
    for ticker, info in MY_PORTFOLIO.items():
        price, div_y = fetch_stock_price(ticker)
        if price:
            # 轉換為港幣計算
            if info["type"] == "US":
                value_hkd = price * info["shares"] * USD_HKD
                current_price_display = f"${round(price, 2)} USD"
            else:
                value_hkd = price * info["shares"]
                current_price_display = f"${round(price, 2)} HKD"
            
            total_portfolio_value_hkd += value_hkd
            estimated_annual_dividend_hkd += (value_hkd * div_y)
            
            portfolio_details.append({
                "股票代碼": ticker,
                "持股數量": info["shares"],
                "目前市價": current_price_display,
                "持倉總值 (HKD)": round(value_hkd, 2),
                "預估股息率": f"{round(div_y * 100, 2)}%"
            })

# 5. 【看板主介面】三大退休指標
st.subheader("🏁 65歲退休目標達成率")

cap_progress = min(total_portfolio_value_hkd / TARGET_CAPITAL, 1.0)
current_monthly_income = estimated_annual_dividend_hkd / 12.0
income_progress = min(current_monthly_income / TARGET_MONTHLY_INCOME, 1.0)

col1, col2 = st.columns(2)
with col1:
    st.metric(label="當前組合總市值 (HKD)", value=f"${round(total_portfolio_value_hkd, 2)}", delta=f"距離200萬目標還差: ${round(max(TARGET_CAPITAL - total_portfolio_value_hkd, 0.0), 2)}")
    st.progress(cap_progress, text=f"本金進度: {round(cap_progress * 100, 2)}%")

with col2:
    st.metric(label="預估現狀每月被動收入 (HKD)", value=f"${round(current_monthly_income, 2)}", delta="退休目標: 每月 $10,000")
    st.progress(income_progress, text=f"被動收入進度: {round(income_progress * 100, 2)}%")

st.markdown("---")

# 6. 持倉明細表格
st.subheader("📋 目前資產清單明細")
df = pd.DataFrame(portfolio_details)
st.dataframe(df, use_container_width=True)

# 7. 退休衝刺溫馨提示
st.subheader("💡 退休策略看盤思維")
if total_portfolio_value_hkd < TARGET_CAPITAL:
    st.info(f"親愛的投資者，您目前距離 65 歲退休還有 8 年。目前現有資產已完成目標的 **{round(cap_progress * 100, 1)}%**。當前策略：無需恐慌騰訊等優質資產的短期回落，利用主動收入與股息繼續「低位吸納」，同時放手讓 Nvidia / Tesla 零成本部位奔跑，靜待複利奇蹟！")
else:
    st.success("🎉 太棒了！您的資產規模已跨越 200 萬港元門檻。接下來的任務是逐步在未來幾年將高波動的科技股，轉化為年化 6% 以上的穩定高息資產（如港股國企藍籌或高息 ETF），鎖定每月 1 萬元的現金流。")
