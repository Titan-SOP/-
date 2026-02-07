# app.py
# Titan SOP V78.2 - The War Room UI (Final Audit Package)
# [V78.2 Patch]: 
# 1. Upgraded version to 78.2. 
# 2. Unified Window 15/16 UI with correct column order and color styling.
# 3. Locked interaction logic to prevent re-downloading data.
# 4. Corrected all deduction labels to "87MA扣抵預判".
# [CRITICAL FIX]: Corrected data loading logic to prioritize "可轉債市價" for the 'close' field, preventing misidentification with underlying stock price.

import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from config import Config
from knowledge_base import TitanKnowledgeBase
from macro_risk import MacroRiskEngine
from strategy import TitanStrategyEngine
from intelligence import IntelligenceIngestor
from execution import CalendarAgent
import pdfplumber
import re
from datetime import datetime, timedelta
import altair as alt
import yfinance as yf
import plotly.express as px


SIGNAL_MAP = {
    "GREEN_LIGHT": "🟢 綠燈：積極進攻",
    "YELLOW_LIGHT": "🟡 黃燈：區間操作",
    "RED_LIGHT": "🔴 紅燈：現金為王"
}

@st.cache_resource
def load_system():
    kb = TitanKnowledgeBase()
    strategy_engine = TitanStrategyEngine()
    strategy_engine.kb = kb
    from backtest import TitanBacktestEngine
    return kb, MacroRiskEngine(), strategy_engine, IntelligenceIngestor(), CalendarAgent(), TitanBacktestEngine()

kb, macro, strategy, intel, calendar, backtester = load_system()

st.set_page_config(page_title="Titan SOP V78.2", layout="wide", page_icon="🏛️")
st.title("🏛️ Titan SOP 全自動戰情室 (V78.2 雙雷達修復版)")

@st.cache_data(ttl=7200)
def get_macro_data(_macro, _df):
    """快取宏觀風控數據"""
    return _macro.check_market_status(cb_df=_df)

@st.cache_data(ttl=7200)
def get_scan_result(_strat, _df):
    """快取策略掃描結果"""
    return _strat.scan_entire_portfolio(_df)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    if st.button("🔄 清除快取並刷新"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    st.divider()
    st.header("📂 CB 資料上傳")
    f_cb_list = st.file_uploader("1. 上傳 CB 清單 (Excel/CSV)", type=['csv','xlsx'])
    if f_cb_list:
        try:
            df_raw = pd.read_excel(f_cb_list) if f_cb_list.name.endswith('.xlsx') else pd.read_csv(f_cb_list)
            df = df_raw.copy()
            df.columns = [c.strip().replace(" ", "") for c in df.columns]

            # ========== START: BUG FIX LOGIC ==========
            rename_map = {}
            
            # Priority 1: Explicitly find the CB price and map it to 'close'.
            cb_price_col = next((c for c in df.columns if "可轉債市價" in c), None)
            if cb_price_col:
                rename_map[cb_price_col] = 'close'

            # Priority 2: Explicitly find the underlying stock price to avoid confusion.
            underlying_price_col = next((c for c in df.columns if "標的股票市價" in c), None)
            if underlying_price_col:
                rename_map[underlying_price_col] = 'underlying_price'

            # Fallback Logic: Apply original fuzzy search for other columns.
            for col in df.columns:
                if col in rename_map:  # Skip if already mapped by high-priority rules
                    continue
                
                col_lower = col.lower()
                if "代號" in col and "標的" not in col: rename_map[col] = 'code'
                elif "名稱" in col or "標的債券" in col: rename_map[col] = 'name'
                # Fallback for 'close' only if the high-priority CB price column was not found
                elif cb_price_col is None and any(k in col_lower for k in ["市價", "收盤", "close", "成交"]): rename_map[col] = 'close'
                elif any(k in col_lower for k in ["標的", "stock_code"]): rename_map[col] = 'stock_code'
                elif "發行" in col: rename_map[col] = 'list_date'
                elif "賣回" in col: rename_map[col] = 'put_date'
                elif any(k in col for k in ["轉換價", "轉換價格", "最新轉換價"]): rename_map[col] = 'conversion_price'
                elif any(k in col for k in ["已轉換比例", "轉換比例", "轉換率"]): rename_map[col] = 'converted_ratio'
                elif any(k in col for k in ["發行餘額", "流通餘額"]): rename_map[col] = 'outstanding_balance'
                elif "發行總額" in col: rename_map[col] = 'issue_amount'
                elif any(k in col_lower for k in ["均量", "成交量", "avg_vol"]): rename_map[col] = 'avg_volume'
            # ========== END: BUG FIX LOGIC ==========

            df.rename(columns=rename_map, inplace=True)
            df = df.loc[:, ~df.columns.duplicated()]

            required_cols = ['code', 'name', 'stock_code', 'close']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ 檔案缺少必要欄位！請確認包含: {', '.join(missing_cols)}")
            else:
                df['code'] = df['code'].astype(str).str.extract(r'(\d+)')
                df['stock_code'] = df['stock_code'].astype(str).str.extract(r'(\d+)')
                df.dropna(subset=['code', 'stock_code'], inplace=True)
                
                if 'conversion_price' not in df.columns:
                    st.warning("⚠️ 缺少「轉換價」欄位，溢價率將無法計算。")
                    df['conversion_price'] = 0
                
                if 'converted_ratio' not in df.columns:
                    if 'outstanding_balance' in df.columns and 'issue_amount' in df.columns:
                        st.info("ℹ️ 未提供「已轉換比例」，系統將嘗試從發行餘額與總額計算。")
                    else:
                        st.warning("⚠️ 缺少「已轉換比例」相關欄位，籌碼鬆動分析將無法執行。")
                        df['converted_ratio'] = 0

                if 'avg_volume' not in df.columns:
                    st.warning("⚠️ 缺少「均量」欄位，流動性風險分析可能不準確。")
                    vol_col = next((c for c in df.columns if '量' in c or 'volume' in c), None)
                    if vol_col:
                        df.rename(columns={vol_col: 'avg_volume'}, inplace=True)
                    else:
                        df['avg_volume'] = 100

                st.session_state['df'] = df
                st.success(f"✅ 載入 {len(df)} 筆 CB")
                  
        except Exception as e:
            st.error(f"檔案讀取或格式清洗失敗: {e}")

    st.divider()
    st.header("🧠 多源情報獵殺")
    api_key = st.text_input("輸入你的 Gemini API Key (選填)", type="password")
    uploaded_intel_files = st.file_uploader("2. 拖曳情報文件 (PDF, TXT)", type=['pdf', 'txt'], accept_multiple_files=True)
    st.session_state['api_key'] = api_key
    st.session_state['intel_files'] = uploaded_intel_files

df = st.session_state.get('df', pd.DataFrame())

if not df.empty:
    with st.expander("📂 檢視已清洗的 CB 資料庫 (前100筆)"):
        st.dataframe(df.head(100))

# ==========================================
# [Helper Functions] Core Logic & Safety
# ==========================================
def safe_clamp(val, min_v, max_v):
    """防止 Streamlit Widget 因預設值超標而崩潰"""
    if val is None or pd.isna(val): return min_v
    return max(min_v, min(max_v, float(val)))

def calculate_zigzag(df, deviation=0.03):
    df = df.reset_index()
    date_col = next((c for c in df.columns if str(c).lower() in ['date', 'index']), None)
    if date_col: df.rename(columns={date_col: 'Date'}, inplace=True)
    if 'Close' not in df.columns or 'Date' not in df.columns: return pd.DataFrame()
    closes = df['Close'].values; dates = df['Date'].values
    if len(closes) == 0: return pd.DataFrame()
    pivots = [{'idx': 0, 'Price': closes[0], 'Type': 'Start', 'Date': dates[0]}]
    trend = 0; last_p = closes[0]; last_i = 0
    for i in range(1, len(closes)):
        diff = (closes[i] - last_p) / last_p
        if trend == 0:
            if diff > deviation: trend=1; last_p=closes[i]; last_i=i
            elif diff < -deviation: trend=-1; last_p=closes[i]; last_i=i
        elif trend == 1: 
            if closes[i] > last_p: last_p=closes[i]; last_i=i 
            elif diff < -deviation:
                pivots.append({'idx': last_i, 'Price': last_p, 'Type': 'High', 'Date': dates[last_i]})
                trend=-1; last_p=closes[i]; last_i=i
        elif trend == -1:
            if closes[i] < last_p: last_p=closes[i]; last_i=i
            elif diff > deviation:
                pivots.append({'idx': last_i, 'Price': last_p, 'Type': 'Low', 'Date': dates[last_i]})
                trend=1; last_p=closes[i]; last_i=i
    pivots.append({'idx': len(closes)-1, 'Price': closes[-1], 'Type': 'Current', 'Date': dates[-1]})
    return pd.DataFrame(pivots)

def calculate_5_waves(zigzag_df):
    if len(zigzag_df) < 2: return pd.DataFrame()
    last = zigzag_df.iloc[-1]; prev = zigzag_df.iloc[-2]
    current_direction = 1 if last['Price'] > prev['Price'] else -1
    wave_len = abs(last['Price'] - prev['Price'])
    start_date = last['Date']; start_price = last['Price']
    future_points = []
    if current_direction == 1: 
        p1_price = start_price - (wave_len * 0.382)
        p1_date = start_date + pd.Timedelta(days=10)
        future_points.append({'Date': p1_date, 'Price': p1_price, 'Label': 'W2(回)'})
        p2_price = p1_price + (wave_len * 1.618)
        p2_date = p1_date + pd.Timedelta(days=20)
        future_points.append({'Date': p2_date, 'Price': p2_price, 'Label': 'W3(推)'})
        w3_len = p2_price - p1_price
        p3_price = p2_price - (w3_len * 0.382)
        p3_date = p2_date + pd.Timedelta(days=15)
        future_points.append({'Date': p3_date, 'Price': p3_price, 'Label': 'W4(回)'})
        p4_price = p3_price + wave_len
        p4_date = p3_date + pd.Timedelta(days=15)
        future_points.append({'Date': p4_date, 'Price': p4_price, 'Label': 'W5(末)'})
    else: 
        p1_price = start_price + (wave_len * 0.5)
        p1_date = start_date + pd.Timedelta(days=10)
        future_points.append({'Date': p1_date, 'Price': p1_price, 'Label': 'B波(彈)'})
        p2_price = p1_price - (wave_len * 1.0)
        p2_date = p1_date + pd.Timedelta(days=20)
        future_points.append({'Date': p2_date, 'Price': p2_price, 'Label': 'C波(殺)'})
    sim_df = pd.DataFrame(future_points)
    start_row = pd.DataFrame([{'Date': start_date, 'Price': start_price, 'Label': 'Origin'}])
    return pd.concat([start_row, sim_df], ignore_index=True)

def get_advanced_granville(cp, op, ma87_curr, ma87_prev5):
    slope = ma87_curr - ma87_prev5
    bias = ((cp - ma87_curr) / ma87_curr) * 100 if ma87_curr > 0 else 0
    is_rising = slope > 0.3; is_falling = slope < -0.3
    status = "盤整 (無訊號)"; desc = "均線走平，區間震盪"
    if bias > 25: return "🔴 正乖離過大", "乖離 > 25%，過熱"
    if bias < -25: return "🟢 負乖離過大", "乖離 < -25%，超跌"
    if cp > ma87_curr and op < ma87_curr and not is_falling: return "🚀 G1 突破買點", "突破生命線且均線未下彎"
    if cp < ma87_curr and is_rising: return "🛡️ G2 假跌破(買)", "跌破上揚均線"
    if cp > ma87_curr and bias < 3 and is_rising: return "🧱 G3 回測支撐", "回測生命線有守"
    if cp < ma87_curr and op > ma87_curr and not is_rising: return "💀 G4 跌破賣點", "跌破生命線且均線未上揚"
    if cp > ma87_curr and is_falling: return "🎣 G5 假突破(賣)", "突破下彎均線"
    if cp < ma87_curr and bias > -3 and is_falling: return "🚧 G6 反彈遇壓", "反彈生命線不過"
    return status, desc

def calculate_ark_scenarios(rev_ttm, shares, cp, g, m, pe, years=5):
    if rev_ttm is None or shares is None or shares == 0: return None
    scenarios = {}
    cases = {'Bear': {'g_m': 0.8, 'pe_m': 0.8, 'm_adj': -0.05}, 'Base': {'g_m': 1.0, 'pe_m': 1.0, 'm_adj': 0.0}, 'Bull': {'g_m': 1.2, 'pe_m': 1.2, 'm_adj': 0.05}}
    for c, mults in cases.items():
        tg_g = g * mults['g_m']; tg_pe = pe * mults['pe_m']
        tg_m = max(0.01, m + mults['m_adj'])
        target = (rev_ttm * ((1+tg_g)**years) * tg_m * tg_pe) / shares
        cagr = (target/cp)**(1/years)-1 if cp>0 else 0
        scenarios[c] = {"Target": target, "CAGR": cagr}
    return scenarios

def calculate_smart_valuation(eps, rev, shares, g, m, pe, dr=0.1, y=10):
    if rev is None or shares == 0: return 0
    fut_mc = rev * ((1+g)**y) * m * pe
    return (fut_mc / ((1+dr)**y)) / shares

def calculate_futures_targets(ticker="WTX=F"):
    df = macro.get_single_stock_data(ticker, period="max")
    if df.empty or len(df) < 300:
        df = macro.get_single_stock_data("^TWII", period="max") 
        ticker_name = "加權指數(模擬期指)"
    else: ticker_name = "台指期近月"
    if df.empty: return {"error": "無法下載數據"}
    
    df = df.reset_index().loc[:, ~df.reset_index().columns.duplicated()]
    if 'Date' not in df.columns: df.rename(columns={'index': 'Date'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date']); df = df.sort_values('Date')
    df['YM'] = df['Date'].dt.to_period('M')
    
    s_dates = []
    for ym in df['YM'].unique():
        wed = df[(df['YM'] == ym) & (df['Date'].dt.weekday == 2)]
        if len(wed) >= 3:
            d = wed.iloc[2]['Date']; val = d.item() if hasattr(d, 'item') else d
            if not df[df['Date'] >= val].empty: s_dates.append(val)
            
    stats = []
    for i in range(len(s_dates) - 1):
        mask = (df['Date'] > s_dates[i]) & (df['Date'] <= s_dates[i+1])
        m_data = df.loc[mask]
        if not m_data.empty:
            h = m_data['High'].max(); l = m_data['Low'].min()
            hv = h.item() if hasattr(h, 'item') else h; lv = l.item() if hasattr(l, 'item') else l
            stats.append(float(hv) - float(lv))
            
    if len(stats) < 12: return {"error": "資料不足"}
    l12 = stats[-12:]; min_a = min(l12); avg_a = sum(l12)/12; max_a = max(l12)
    
    curr = df[df['Date'] > s_dates[-1]]
    if curr.empty: return {"error": "新合約未開始"}
    op_v = float(curr.iloc[0]['Open']); cl_v = float(curr.iloc[-1]['Close'])
    is_red = cl_v >= op_v; sign = 1 if is_red else -1
    
    targets = {
        "1B": op_v + sign * min_a * 0.5, "2B": op_v + sign * min_a,
        "3B": op_v + sign * avg_a, "HR": op_v + sign * max_a
    }
    return {"name":ticker_name, "anc":op_v, "price":cl_v, "is_red":is_red, "t":targets}

# --- [V78.2 REVISED] Window 15 & 16: 雙雷達趨勢掃描 ---
def render_leader_dashboard(window_title: str, session_state_key: str, fetch_function, top_n: int, sort_key_name: str):
    # This function's title is now part of the expander title, so we can remove the st.header
    st.info(f"此功能將掃描指定股票池，依「{sort_key_name}」找出市場最關注的 Top {top_n}，並對其進行高階趨勢預測。")

    if session_state_key not in st.session_state:
        st.session_state[session_state_key] = pd.DataFrame()

    if st.button(f"🛰️ 掃描 {sort_key_name} Top {top_n}", key=f"btn_{session_state_key}"):
        with st.spinner(f"正在掃描並進行高階運算... (可能需要1-2分鐘)"):
            st.session_state[session_state_key] = fetch_function(top_n=top_n)

    leaders_df = st.session_state[session_state_key]
    
    if not leaders_df.empty:
        if "error" in leaders_df.columns:
            st.error(leaders_df.iloc[0]["error"])
        else:
            def style_status(status):
                if "多頭" in str(status): return f"<span style='color:red;'>{status}</span>"
                if "空頭" in str(status): return f"<span style='color:green;'>{status}</span>"
                return status
            
            def style_deduction(signal):
                if "助漲" in str(signal): return f"<span style='color:red;'>{signal}</span>"
                if "壓力" in str(signal): return f"<span style='color:green;'>{signal}</span>"
                return signal

            display_df = leaders_df.copy()
            display_df['排名'] = display_df['rank']
            display_df['代號'] = display_df['ticker']
            display_df['名稱'] = display_df['name']
            display_df['產業'] = display_df['industry']
            display_df['現價'] = display_df['current_price'].apply(lambda x: f"{x:.2f}")
            display_df['趨勢狀態'] = display_df['trend_status'].apply(style_status)
            display_df['持續天數'] = display_df['trend_days']
            display_df['87MA扣抵預判'] = display_df['deduction_signal'].apply(style_deduction)
            
            st.subheader(f"📈 今日 {sort_key_name} Top {top_n} 榜單")
            
            columns_to_display = ['排名', '代號', '名稱', '產業', '現價', '趨勢狀態', '持續天數', '87MA扣抵預判']
            st.markdown(
                display_df[columns_to_display].to_html(escape=False, index=False), 
                unsafe_allow_html=True
            )
            st.divider()

            st.subheader("🔍 選擇一檔主流股進行深度預測")
            options = [f"{row['rank']}. {row['name']} ({row['ticker']})" for _, row in leaders_df.iterrows()]
            selected_leader_str = st.selectbox("選擇標的", options=options, key=f"select_{session_state_key}")

            if selected_leader_str:
                selected_rank = int(selected_leader_str.split('.')[0])
                selected_data = leaders_df[leaders_df['rank'] == selected_rank].iloc[0]

                # Directly use cached data from session_state, no re-downloading
                stock_df = selected_data['stock_df']
                deduction_df = selected_data['deduction_df']
                adam_df = selected_data['adam_df']
                current_price = selected_data['current_price']
                ma87 = selected_data['ma87']

                kpi_c1, kpi_c2 = st.columns(2)
                kpi_c1.metric("目前股價", f"{current_price:.2f}")
                bias_percent = ((current_price - ma87) / ma87) * 100 if ma87 > 0 else 0
                is_recent_breakout = (current_price > ma87) and (stock_df['Close'].iloc[-5] < ma87)
                granville_status = strategy._get_granville_status(current_price, ma87, is_recent_breakout, bias_percent)
                kpi_c2.metric("格蘭碧法則狀態", granville_status)
                st.markdown("---")

                trend_c1, trend_c2, trend_c3, trend_c4 = st.columns(4)
                trend_c1.metric("趨勢波段", selected_data['trend_status'])
                trend_c2.metric("已持續天數", f"{selected_data['trend_days']} 天")
                trend_c3.metric("生命線斜率", f"{selected_data['ma87_slope']:.2f}°")
                trend_c4.metric("87MA扣抵預判", selected_data['deduction_signal'])

                tab1, tab2 = st.tabs(["**87MA 扣抵值預測**", "**亞當理論二次反射**"])
                with tab1:
                    if not deduction_df.empty:
                        chart_data = deduction_df.reset_index()
                        chart_data['Current_Price'] = current_price
                        base = alt.Chart(chart_data).encode(x='Date:T')
                        line_deduction = base.mark_line(color='orange', strokeDash=[5,5]).encode(y=alt.Y('Deduction_Value', title='Price'), tooltip=['Date', 'Deduction_Value']).properties(title="未來60日 87MA 扣抵值預測")
                        line_current = base.mark_line(color='blue').encode(y='Current_Price')
                        st.altair_chart((line_deduction + line_current).interactive(), use_container_width=True)
                    else: st.warning("歷史資料不足，無法預測均線扣抵值。")
                with tab2:
                    if not adam_df.empty:
                        hist_df = stock_df.iloc[-60:].reset_index(); hist_df['Type'] = '歷史路徑'
                        proj_df = adam_df.reset_index(); proj_df['Type'] = '亞當投影'; proj_df.rename(columns={'Projected_Price': 'Close', 'Date': 'Date'}, inplace=True)
                        chart_data = pd.concat([hist_df[['Date', 'Close', 'Type']], proj_df[['Date', 'Close', 'Type']]])
                        chart = alt.Chart(chart_data).mark_line().encode(x='Date:T', y=alt.Y('Close', title='Price', scale=alt.Scale(zero=False)), color='Type:N', strokeDash='Type:N').properties(title="亞當理論二次反射路徑圖").interactive()
                        st.altair_chart(chart, use_container_width=True)
                    else: st.warning("歷史資料不足，無法進行亞當理論投影。")
    else:
        st.info("點擊上方按鈕以啟動掃描。")

# 建立 5 個戰略分頁 (手機最佳化配置)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛡️ 宏觀大盤",   # Tab 1: Macro Dashboard
    "🏹 獵殺專區",   # Tab 2: Hunter Zone (SOP)
    "🎯 單兵狙擊",   # Tab 3: Sniper HQ
    "🚀 戰力升級",   # Tab 4: Roadmap (Reserved)
    "📚 戰略百科"    # Tab 5: Encyclopedia
])

with tab1: # 宏觀大盤部
    with st.expander("1.1 宏觀風控 (Macro Risk)", expanded=True):
        if not df.empty:
            macro_data = get_macro_data(macro, df)
            c1, c2, c3, c4 = st.columns(4)
            signal_text = SIGNAL_MAP.get(macro_data['signal'], "⚪ 未知")
            signal_emoji, signal_desc = signal_text.split('：') if '：' in signal_text else (signal_text, "")
            c1.metric("🚦 總體燈號", signal_emoji, help=signal_desc)
            c2.metric("😱 VIX恐慌指數", f"{macro_data['vix']:.2f}", "高於25為綠燈")
            c3.metric("🔥 PR90市場熱度", f"{macro_data['price_distribution']['pr90']:.2f}", "高於130為紅燈")
            ptt_ratio = macro_data['ptt_ratio']
            ptt_text = f"{ptt_ratio:.1f}%" if ptt_ratio != -1.0 else "N/A"
            c4.metric("📊 PTT空頭比例", ptt_text, help="空頭家數佔比，高於50%為紅燈")
            
            st.subheader("🇹🇼 台股加權指數深度分析")
            tse_data = macro_data['tse_analysis']
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(f"目前點位: {tse_data['price']:.2f}", tse_data['momentum'])
            kpi2.metric("神奇均線趨勢", tse_data['magic_ma'])
            kpi3.metric("格蘭碧法則", tse_data['granville'])
            st.text("扣抵與斜率: " + " | ".join(tse_data['deduct_slope']))
        else:
            st.info("請於左側上傳 CB 清單以啟動戰情室。")
        
    with st.expander("1.2 高價權值股多空溫度計", expanded=False):
        if 'high_50_sentiment' not in st.session_state:
            st.session_state.high_50_sentiment = None

        if st.button("🔄 刷新市場多空溫度"):
            with st.spinner("正在分析高價權值股..."):
                st.session_state.high_50_sentiment = macro.analyze_high_50_sentiment()

        if st.session_state.high_50_sentiment:
            sentiment_data = st.session_state.high_50_sentiment
            if "error" in sentiment_data:
                st.error(sentiment_data["error"])
            else:
                col1, col2 = st.columns(2)
                col1.metric("市場氣氛", sentiment_data['sentiment'])
                col2.metric("多空比例 (站上/跌破87MA)", f"🐂 {sentiment_data['bull_ratio']:.1f}% | 🐻 {sentiment_data['bear_ratio']:.1f}%", help=f"基於 {sentiment_data['total']} 檔高價權值股分析")
        else:
            st.info("點擊按鈕以分析市場多空溫度。")
        
    with st.expander("1.3 PR90 籌碼分佈圖", expanded=False):
        if not df.empty:
            macro_data = get_macro_data(macro, df)
            price_dist_data = macro_data.get('price_distribution', {})
            chart_data = price_dist_data.get('chart_data')
            if chart_data is not None and not chart_data.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("PR90 (過熱線)", f"{price_dist_data.get('pr90', 0):.2f}")
                c2.metric("PR75 (機會線)", f"{price_dist_data.get('pr75', 0):.2f}")
                c3.metric("市場均價", f"{price_dist_data.get('avg', 0):.2f}")
                st.bar_chart(chart_data.set_index('區間'), use_container_width=True)
            else:
                st.warning("無法生成籌碼分佈圖，請檢查 CB 清單中的價格欄位。")
        else:
            st.info("請上傳 CB 清單以生成籌碼分佈圖。")
        
    with st.expander("1.4 族群熱度雷達 (Sector Heatmap)", expanded=False):
        if not df.empty:
            if 'sector_heatmap' not in st.session_state:
                st.session_state.sector_heatmap = pd.DataFrame()

            if st.button("🛰️ 掃描市場族群熱度"):
                with st.spinner("正在分析族群資金流向..."):
                    st.session_state.sector_heatmap = macro.analyze_sector_heatmap(df, kb)

            if not st.session_state.sector_heatmap.empty:
                st.info("「多頭比例」代表該族群中，有多少比例的標的股價站上 87MA 生命線。")
                st.dataframe(st.session_state.sector_heatmap.fillna(''), use_container_width=True)
            else:
                st.info("點擊按鈕或上傳包含「漲跌幅」欄位的 CB 清單以分析族群熱度。")
        else:
            st.info("請上傳 CB 清單以啟動族群熱度雷達。")
        
    with st.expander("1.5 成交重心即時預測 (動態 Top 100)", expanded=False):
        render_leader_dashboard(
            window_title="成交重心即時預測 (動態 Top 100)",
            session_state_key="w15_data",
            fetch_function=macro.get_dynamic_turnover_leaders,
            top_n=100,
            sort_key_name="成交值"
        )
        
    with st.expander("1.6 高價權值股趨勢雷達 (Top 50)", expanded=False):
        render_leader_dashboard(
            window_title="高價權值股趨勢雷達 (Top 50)",
            session_state_key="w16_data",
            fetch_function=macro.get_high_price_leaders,
            top_n=50,
            sort_key_name="股價"
        )
        
    with st.expander("1.7 台指期月K結算目標價推導 (Settlement Radar)", expanded=False):
        st.info("💡 獨門戰法：利用過去 12 個月結算慣性，推導本月台指期 (TX) 的「虛擬 K 棒」與目標價。")

        with st.spinner("推導台指期..."):
            res = calculate_futures_targets()

        if "error" in res: st.warning(f"⚠️ {res['error']}")
        else:
            is_red = res['is_red']
            st.subheader(f"📊 {res['name']}：{'🔴 多方控盤' if is_red else '🟢 空方控盤'}")
            c1, c2 = st.columns(2)
            c1.metric("定錨開盤價", f"{res['anc']:.0f}"); c2.metric("目前點位", f"{res['price']:.0f}", f"{res['price']-res['anc']:.0f}")
            
            if is_red: st.success("🔥 多方贏慣性：易收長紅。")
            else: st.success("💀 空方贏慣性：易收長黑。")

            t1, t2, t3, t4 = st.columns(4)
            def check_hit(tg): return "✅ 達標" if (is_red and res['price']>=tg) or (not is_red and res['price']<=tg) else "⏳ 未達"
            t1.metric("1壘", f"{res['t']['1B']:.0f}", check_hit(res['t']['1B']))
            t2.metric("2壘", f"{res['t']['2B']:.0f}", check_hit(res['t']['2B']))
            t3.metric("3壘", f"{res['t']['3B']:.0f}", check_hit(res['t']['3B']))
            t4.metric("HR", f"{res['t']['HR']:.0f}", check_hit(res['t']['HR']))

            chart_df = pd.DataFrame({
                "Label": ["本月"], "Anchor": [res['anc']], "Current": [res['price']], 
                "Target_HR": [res['t']['HR']], "Target_1B": [res['t']['1B']], 
                "Target_2B": [res['t']['2B']], "Target_3B": [res['t']['3B']]
            })
            
            base = alt.Chart(chart_df).encode(x=alt.X('Label', axis=None))
            ghost = base.mark_bar(size=40, color="#ffcccc" if is_red else "#ccffcc", opacity=0.5).encode(
                y=alt.Y('Anchor', scale=alt.Scale(zero=False), title='Price'), y2='Target_HR')
            real = base.mark_bar(size=20, color="#d62728" if is_red else "#2ca02c").encode(
                y='Anchor', y2='Current')
            
            chart = ghost + real
            for k in ['1B','2B','3B']:
                chart += base.mark_tick(color='black', thickness=2, size=50).encode(y=f'Target_{k}') + \
                         base.mark_text(dx=35, align='left', color='black').encode(y=f'Target_{k}', text=alt.value(f"{k} {res['t'][k]:.0f}"))
            chart += base.mark_tick(color='red', thickness=4, size=60).encode(y='Target_HR') + \
                     base.mark_text(dx=40, align='left', color='red').encode(y='Target_HR', text=alt.value(f"HR {res['t']['HR']:.0f}"))

            _, chart_col, _ = st.columns([1, 2, 1])
            with chart_col: st.altair_chart(chart, use_container_width=True)

with tab2: # 可轉債獵殺專區
    with st.expander("2.1 自動獵殺推薦 (Auto Sniper)", expanded=True):
        st.info("此模組執行「全市場雙軌普查 (.TW/.TWO)」，並同步更新全系統連動資料庫。")

        col1, col2 = st.columns(2)
        with col1: min_score = st.slider("最低評分門檻", 0, 10, 5)
        with col2: st.caption("普查將抓取即時行情，請耐心等候。")

        if not df.empty:
            if st.button("🚀 啟動 SOP 全市場普查", type="primary"):
                with st.spinner("執行全市場掃描..."):
                    # 1. 資料前處理 (Surgical Fix: Index Fallback & Type Safety)
                    work_df = df.copy()
                    
                    # [修改 1] 擴充欄位對應，加入「餘額比例」
                    rename_map = {
                        '代號': 'code', '名稱': 'name', '可轉債市價': 'price',
                        '轉換價格': 'conv_price', '轉換標的': 'stock_code',
                        '已轉換比例': 'conv_rate', '轉換價值': 'conv_value',
                        '發行日': 'issue_date', '賣回日': 'put_date',
                        '餘額比例': 'balance_ratio' # 新增對應
                    }
                    work_df.rename(columns=lambda c: rename_map.get(c.strip(), c.strip()), inplace=True)

                    # [修改 2] 主流程強制計算：已轉換率 = 100 - 餘額比例
                    # 優先使用餘額比例計算，若無則保留原值
                    if 'balance_ratio' in work_df.columns:
                        # 轉為數值，處理空值
                        bal = pd.to_numeric(work_df['balance_ratio'], errors='coerce').fillna(100.0)
                        work_df['conv_rate'] = 100.0 - bal

                    # 絕對讀取 (Index Fallback)
                    try:
                        # 檢查關鍵欄位是否存在，若不存在則觸發 Index Fallback
                        required_cols = ['conv_price', 'stock_code', 'price', 'conv_rate', 'conv_value']
                        # 注意：這裡稍微放寬檢查，如果 balance_ratio 存在且已算出 conv_rate，也算通過
                        cols_check = [c for c in required_cols if c != 'conv_rate']
                        
                        if not all(col in work_df.columns for col in cols_check) or ('conv_rate' not in work_df.columns):
                            st.warning("⚠️ 偵測到欄位名稱不符，啟用 Index Fallback 強制讀取...")
                            
                            # 確保 f_cb_list 存在才執行
                            if 'f_cb_list' in locals() or 'f_cb_list' in globals():
                                if f_cb_list is not None:
                                    # 重新讀取原始檔案，不使用 header
                                    f_cb_list.seek(0)
                                    df_by_index = pd.read_excel(f_cb_list, header=None) if f_cb_list.name.endswith('.xlsx') else pd.read_csv(f_cb_list, header=None)
                                    
                                    # 跳過標題行
                                    df_by_index = df_by_index.iloc[1:].reset_index(drop=True)

                                    # 強制賦值
                                    work_df['conv_price'] = df_by_index.iloc[:, 9]
                                    work_df['stock_code'] = df_by_index.iloc[:, 10]
                                    work_df['price'] = df_by_index.iloc[:, 13]
                                    work_df['conv_value'] = df_by_index.iloc[:, 18]
                                    
                                    # [修改 3] Fallback 流程修正：讀取 Index 6 (餘額比例) 並計算
                                    # 原始錯誤寫法: work_df['conv_rate'] = df_by_index.iloc[:, 17]
                                    # 正確寫法:
                                    balance_val = pd.to_numeric(df_by_index.iloc[:, 6], errors='coerce').fillna(100.0)
                                    work_df['conv_rate'] = 100.0 - balance_val
                                else:
                                    st.error("無法執行強制讀取：找不到上傳的檔案物件 (f_cb_list)。")
                                    st.stop()
                            else:
                                st.error("變數 f_cb_list 未定義，無法重新讀取檔案。請確認是否已上傳。")
                                st.stop()
                                
                    except Exception as e:
                        st.error(f"Index Fallback 讀取失敗: {e}")
                        st.stop()

                    # 型別安全：確保數值欄位為 float 並填補空值
                    numeric_cols = ['price', 'conv_rate', 'conv_price', 'conv_value']
                    for col in numeric_cols:
                        if col in work_df.columns:
                            work_df[col] = pd.to_numeric(work_df[col], errors='coerce').fillna(0.0) # 嚴禁填入 0 (int)
                        else:
                            work_df[col] = 0.0 # 如果欄位不存在，創建並填入 0.0

                    # 日期欄位處理
                    for date_col in ['issue_date', 'put_date', 'list_date']:
                        if date_col in work_df.columns:
                            work_df[date_col] = pd.to_datetime(work_df[date_col], errors='coerce')
                    if 'issue_date' not in work_df.columns and 'list_date' in work_df.columns:
                        work_df['issue_date'] = work_df['list_date']

                    # 2. 普查迴圈
                    scan_results_df = get_scan_result(strategy, work_df)
                    records = scan_results_df.to_dict('records')
                    
                    total = len(records)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    enriched_data = []
                    
                    for i, row in enumerate(records):
                        name = row.get('name', '')
                        status_text.text(f"普查進行中 ({i+1}/{total}): {name}...")
                        
                        code = str(row.get('stock_code', '')).strip()
                        row['stock_price_real'] = 0.0
                        row['ma87'] = 0.0
                        row['ma284'] = 0.0
                        row['trend_status'] = "⚠️ 資料不足"
                        
                        # 數據傳遞：確保關鍵數據寫入
                        row['cb_price'] = row.get('price', 0.0)
                        row['conv_price_val'] = row.get('conv_price', 0.0)
                        row['conv_value_val'] = row.get('conv_value', 0.0)

                        if code:
                            try:
                                hist = pd.DataFrame()
                                try: hist = yf.Ticker(f"{code}.TW").history(period="2y")
                                except: pass
                                
                                if hist.empty:
                                    try: hist = yf.Ticker(f"{code}.TWO").history(period="2y")
                                    except: pass
                                    
                                if not hist.empty and len(hist) > 284:
                                    curr = float(hist['Close'].iloc[-1])
                                    ma87 = float(hist['Close'].rolling(87).mean().iloc[-1])
                                    ma284 = float(hist['Close'].rolling(284).mean().iloc[-1])
                                    
                                    row['stock_price_real'] = curr
                                    row['ma87'] = ma87
                                    row['ma284'] = ma284
                                    
                                    # [關鍵修正]：只要 87MA > 284MA 即判定為中期多頭 (不強制現價 > 87)
                                    if ma87 > ma284:
                                        row['trend_status'] = "✅ 中期多頭"
                                        row['score'] = min(100, row.get('score', 0) + 20)
                                    else:
                                        row['trend_status'] = "整理/空頭"
                            except: pass
                        
                        enriched_data.append(row)
                        progress_bar.progress((i + 1) / total)
                    
                    # 3. 資料分流
                    full_df_enriched = pd.DataFrame(enriched_data)
                    
                    # 確保有必要的欄位供後續篩選
                    if 'price' not in full_df_enriched.columns: full_df_enriched['price'] = 0.0
                    if 'conv_rate' not in full_df_enriched.columns: full_df_enriched['conv_rate'] = 0.0
                    
                    sop_mask = (
                        (full_df_enriched['price'] < 120) &
                        (full_df_enriched['trend_status'].str.contains("多頭", na=False)) &
                        (full_df_enriched['conv_rate'] < 30)
                    )
                    sop_results = full_df_enriched[sop_mask].sort_values('score', ascending=False)
                    
                    st.session_state['scan_results'] = sop_results
                    st.session_state['full_census_data'] = full_df_enriched.to_dict('records')
                    
                    status_text.text("✅ 普查完成！資料已同步至戰情室與全系統。")
                    st.success(f"全市場掃描結束。符合「SOP 黃金標準」共 {len(sop_results)} 檔。")
                    if not sop_results.empty:
                        st.dataframe(sop_results[['code', 'name', 'price', 'stock_price_real', 'trend_status', 'conv_rate']])

        else:
            st.info("請上傳 CB 清單以啟動自動獵殺掃描。")
        
    with st.expander("2.2 核心策略檢核 (The War Room)", expanded=False):
        # [修復 1] 互動式 K 線圖函式 (具備 5 碼代碼自動轉 4 碼邏輯)
        def plot_candle_chart(cb_code):
            """使用 Altair 繪製互動式 K 線圖 (紅漲綠跌) 並疊加 87/284MA"""
            import yfinance as yf
            import altair as alt
            
            # [關鍵修正]: 若傳入的是 5 碼 CB 代碼 (如 64145)，截取前 4 碼 (6414) 作為股票代碼
            target_code = str(cb_code).strip()
            if len(target_code) == 5 and target_code.isdigit():
                target_code = target_code[:4]
                
            try:
                chart_df = pd.DataFrame()
                # 雙軌下載 (優先試 TW，若無則試 TWO)
                ticker_tw = f"{target_code}.TW"
                ticker_two = f"{target_code}.TWO"
                
                chart_df = yf.download(ticker_tw, period="2y", progress=False)
                if chart_df.empty:
                    chart_df = yf.download(ticker_two, period="2y", progress=False)
                
                if not chart_df.empty:
                    # 解決 yfinance MultiIndex 問題
                    if isinstance(chart_df.columns, pd.MultiIndex):
                        chart_df.columns = chart_df.columns.get_level_values(0)
                    
                    chart_df = chart_df.reset_index()
                    
                    # 計算均線 (87MA 與 284MA)
                    chart_df['MA87'] = chart_df['Close'].rolling(87).mean()
                    chart_df['MA284'] = chart_df['Close'].rolling(284).mean()

                    # 定義 K 線圖基礎
                    base = alt.Chart(chart_df).encode(
                        x=alt.X('Date:T', axis=alt.Axis(title='日期', format='%Y-%m-%d'))
                    )

                    # 紅漲綠跌顏色條件
                    color_condition = alt.condition("datum.Open <= datum.Close", alt.value("#FF4B4B"), alt.value("#26A69A"))

                    # 繪製 K 線
                    candles = base.mark_rule().encode(
                        y=alt.Y('Low', title='股價', scale=alt.Scale(zero=False)),
                        y2='High'
                    ) + base.mark_bar().encode(
                        y='Open',
                        y2='Close',
                        color=color_condition,
                        tooltip=['Date', 'Open', 'Close', 'High', 'Low']
                    )
                    
                    # 繪製均線
                    line_87 = base.mark_line(color='orange', strokeWidth=2).encode(y='MA87')
                    line_284 = base.mark_line(color='#00bfff', strokeWidth=2).encode(y='MA284')
                    
                    final_chart = (candles + line_87 + line_284).interactive()
                    st.altair_chart(final_chart, use_container_width=True)
                    st.caption(f"📈 標的股票代碼: {target_code} | 🔶 橘線: 87MA | 🔷 藍線: 284MA")
                else:
                    st.error(f"❌ Yahoo Finance 查無此標的 K 線資料: {target_code}")
            except Exception as e:
                st.warning(f"K 線圖生成失敗: {e}")

        # --- 主程式邏輯 ---
        if 'full_census_data' not in st.session_state:
            st.warning("⚠️ 請先至本頁上方執行「SOP 全市場普查」。")
        else:
            # 讀取並定義基礎變數
            full_data = pd.DataFrame(st.session_state['full_census_data'])
            
            # [修復 NameError] 定義 now 供後續所有 Tab 使用
            from datetime import datetime
            now = datetime.now()
            
            # 確保日期欄位正確
            if 'issue_date' in full_data.columns:
                full_data['issue_date'] = pd.to_datetime(full_data['issue_date'], errors='coerce')

            # [需求] 修改 Tab 列表，新增 "產業風口榜"
            tab1_w9, tab2_w9, tab3_w9, tab4_w9, tab5_w9 = st.tabs([
                "🏆 SOP 菁英榜", "👶 新券蜜月", "💤 滿年沈澱", "🛡️ 賣回保衛", "🔥 產業風口榜"
            ])
            
            # --- Tab 1: SOP 菁英榜 (鄭思翰 SOP 終極美化版) ---
            with tab1_w9:
                # 篩選邏輯
                if 'scan_results' in st.session_state and not st.session_state['scan_results'].empty:
                    df_t1 = st.session_state['scan_results'].head(20)
                else:
                    mask_t1 = (full_data['price'] < 120) & (full_data['trend_status'].str.contains("多頭", na=False))
                    df_t1 = full_data[mask_t1].sort_values('score', ascending=False).head(20)

                if df_t1.empty:
                    st.info("無符合標準標的。")
                else:
                    for _, row in df_t1.iterrows():
                        cb_name = row.get('name', '未知')
                        cb_code = str(row.get('code', row.get('stock_code', '0000'))).strip()
                        
                        # [關鍵修正]: 已轉換率反轉邏輯 (修正 99.99% 錯誤)
                        raw_conv = pd.to_numeric(row.get('conv_rate', row.get('balance_rate', 100)), errors='coerce') or 100.0
                        # 若數值 > 50 視為「餘額比率」，執行反轉；否則視為已轉換率
                        converted_percentage = (100.0 - raw_conv) if raw_conv > 50 else raw_conv
                        if converted_percentage < 0: converted_percentage = 0.0
                        
                        price = pd.to_numeric(row.get('price'), errors='coerce') or 0.0
                        ma87 = pd.to_numeric(row.get('ma87'), errors='coerce') or 0.0
                        ma284 = pd.to_numeric(row.get('ma284'), errors='coerce') or 0.0
                        score = pd.to_numeric(row.get('score'), errors='coerce') or 0

                        title = f"👑 {cb_name} ({cb_code}) | CB價: {price:.1f} | 評分: {int(score)}"
                        with st.expander(title):
                            # 摘要美化
                            st.markdown(f"### 🛡️ 天條檢核: `✅ 價格<120` | `✅ 均線多頭` | `✅ 已轉換率 {converted_percentage:.2f}%`")
                            st.divider()

                            # 詳細報告
                            with st.expander("📄 查看詳細分析報告 (Detailed Report)", expanded=False):
                                st.markdown(f"## 📊 {cb_name} ({cb_code}) 策略分析")
                                
                                st.info("### 1. 核心策略檢核 (The 4 Commandments)")
                                st.markdown(f"1. 價格天條 (<115): {'✅ 通過' if price < 115 else '⚠️ 警戒'} (目前 **{price:.1f}**)")
                                
                                is_bullish = ma87 > ma284
                                st.markdown(f"2. 中期多頭排列: {'✅ 通過' if is_bullish else '⚠️ 整理中'}")
                                st.markdown(f"> 均線數據: 87MA **{ma87:.2f}** {' > ' if is_bullish else ' < '} 284MA **{ma284:.2f}**")
                                
                                st.markdown("3. 身分認證 (Identity): ☐ 領頭羊 / ☐ 風口豬")
                                st.markdown("> 💡 鄭思翰辨別準則：")
                                st.markdown("> * 領頭羊: 產業族群中率先領漲、最強勢的高價指標股(如 2025年底的群聯與PCB族群集體發債)。")
                                st.markdown("> * 風口豬: 處於主流題材風口的二軍低價股 (如 旺宏)，站在風口上連豬都會飛。")
                                
                                st.markdown("4. 發債故事 (Story): ☐ 從無到有 / ☐ 擴產 / ☐ 政策事件")
                                
                                st.success("### 2. 決策輔助 (Decision Support)")
                                conv_price = pd.to_numeric(row.get('conv_price_val', 0.01), errors='coerce')
                                stock_price = pd.to_numeric(row.get('stock_price_real', 0.0), errors='coerce')
                                parity = (stock_price / conv_price * 100) if conv_price > 0 else 0.0
                                conv_value = pd.to_numeric(row.get('conv_value_val', 0.0), errors='coerce')
                                premium = ((price - conv_value) / conv_value * 100) if conv_value > 0 else 0.0
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("理論價 (Parity)", f"{parity:.2f}")
                                c2.metric("溢價率 (Premium)", f"{premium:.2f}%")
                                c3.metric("已轉換比例", f"{converted_percentage:.2f}%")
                                
                                st.markdown("### 4. 交易計畫 (Trading Plan)")
                                st.warning("🕒 關鍵時段：09:00 開盤後30分鐘 (觀察大戶試撮) / 13:25 收盤前25分鐘 (尾盤定勝負)")
                                st.markdown(f"* 🎯 進場佈局: 建議於 105~115 元 區間佈局加碼。")
                                st.markdown(f"* 🚀 加碼時機: 股價帶量突破 87MA 或 284MA 時。")
                                
                                st.markdown("### 5. 出場/風控 (Exit/Risk)")
                                st.markdown(f"* 🛑 停損: CB 跌破 100 元 (保本天條)。")
                                st.markdown(f"* 💰 停利: 目標價 152 元以上，嚴守 「留魚尾」 策略避免過早出場。")
                                
                                st.divider()
                                # [修復] 在報告內正確渲染 K 線圖
                                plot_candle_chart(cb_code)

            # --- Tab 2: 新券蜜月 (Titan V80.18: 鄭思翰 SOP 新券專用版) ---
            with tab2_w9:
                # [篩選邏輯回歸]：上市 < 90 天、價格 < 130、溢價率 < 20、轉換率 < 30
                mask_t2 = (
                    full_data['issue_date'].notna() &
                    ((now - full_data['issue_date']).dt.days < 90) &
                    (full_data['price'] < 130) &
                    (full_data['conv_rate'] < 30) # 這裡 conv_rate 原始資料通常存的是「餘額」
                )
                df_t2 = full_data[mask_t2].sort_values('issue_date', ascending=False)
                
                if df_t2.empty: 
                    st.info("目前無符合「新券蜜月」標準的標的 (上市<90天, 價格<130, 轉換率<30%)。")
                else:
                    for _, row in df_t2.iterrows():
                        # [1. 數據獲取與型別防護]
                        name = row.get('name', '未知')
                        cb_code = str(row.get('code', row.get('stock_code', '0000'))).strip()
                        days_listed = (now - row['issue_date']).days
                        
                        # [關鍵修正]: 已轉換率智慧反轉邏輯 (修正 99.99% 錯誤)
                        # 假設資料源中的 'conv_rate' 實際存的是「餘額比率」
                        raw_balance = pd.to_numeric(row.get('conv_rate', 100), errors='coerce') or 100.0
                        converted_percentage = (100.0 - raw_balance) if raw_balance > 50 else raw_balance
                        if converted_percentage < 0: converted_percentage = 0.0

                        price = pd.to_numeric(row.get('price'), errors='coerce') or 0.0
                        ma87 = pd.to_numeric(row.get('ma87'), errors='coerce') or 0.0
                        ma284 = pd.to_numeric(row.get('ma284'), errors='coerce') or 0.0
                        
                        # 計算決策數據 (理論價與溢價率)
                        conv_price = pd.to_numeric(row.get('conv_price_val', 0.01), errors='coerce')
                        stock_price = pd.to_numeric(row.get('stock_price_real', 0.0), errors='coerce')
                        parity = (stock_price / conv_price * 100) if conv_price > 0 else 0.0
                        conv_value = pd.to_numeric(row.get('conv_value_val', 0.0), errors='coerce')
                        premium = ((price - conv_value) / conv_value * 100) if conv_value > 0 else 0.0

                        # [2. UI 顯示 - 新券專用卡片]
                        title = f"👶 {name} ({cb_code}) | 上市 {days_listed} 天 | CB價: {price:.1f}"
                        with st.expander(title):
                            
                            # 摘要行: 增大字體與美化
                            st.markdown(f"### 🛡️ 新券檢核: `✅ 上市 {days_listed} 天` | `✅ 價格 < 130` | `✅ 已轉換 {converted_percentage:.2f}%`")
                            st.divider()

                            # [詳細分析報告 - 鄭思翰 SOP 蜜月版]
                            with st.expander("📄 查看蜜月期深度分析 (Honeymoon Report)", expanded=False):
                                st.markdown(f"## 📊 {name} ({cb_code}) 蜜月期戰略")
                                
                                # 區塊 1: 核心策略
                                st.info("### 1. 核心策略檢核 (The 4 Commandments)")
                                st.markdown(f"1. 蜜月期價格: {'✅ 通過' if price < 115 else '⚠️ 監控'} (新券甜蜜區 105-115, 目前 **{price:.1f}**)")
                                
                                # 技術面：新券可能資料不足
                                is_bullish = ma87 > ma284
                                trend_text = "✅ 多頭排列" if is_bullish else ("⚠️ 資料不足或整理中" if ma87 == 0 else "❌ 偏弱")
                                st.markdown(f"2. 中期多頭排列: {trend_text}")
                                if ma87 > 0:
                                    st.markdown(f"> 均線數據: 87MA **{ma87:.2f}** {' > ' if is_bullish else ' < '} 284MA **{ma284:.2f}**")
                                else:
                                    st.caption("(新券上市天數較短，均線指標僅供參考)")
                                
                                st.markdown("3. 身分認證 (Identity): ☐ 領頭羊 / ☐ 風口豬")
                                st.markdown("> 💡 鄭思翰辨別準則：")
                                st.markdown("> * 領頭羊 (Bellwether): 該族群中率先起漲、氣勢最強之標竿 (如 2025 年底群聯帶動的 PCB 族群)。")
                                st.markdown("> * 風口豬 (Wind Pig): 處於主流熱門題材風口 (如 AI、散熱、重電)，站在風口上連豬都會飛。")
                                
                                st.markdown("4. 發債故事 (Story): ☐ 從無到有 / ☐ 擴產 / ☐ 政策事件")
                                
                                # 區塊 2: 決策輔助
                                st.success("### 2. 決策輔助 (Decision Support)")
                                c1, c2, c3 = st.columns(3)
                                c1.metric("理論價 (Parity)", f"{parity:.2f}")
                                c2.metric("溢價率 (Premium)", f"{premium:.2f}%")
                                c3.metric("已轉換比例", f"{converted_percentage:.2f}%")
                                
                                # 區塊 4: 交易計畫
                                st.markdown("### 4. 交易計畫 (Trading Plan)")
                                st.warning("🕒 關鍵時段：09:00 開盤 (觀察大戶試撮氣勢) / 13:25 收盤前 (尾盤定勝負)")
                                st.markdown(f"* 🎯 蜜月期佈局: 新券上市初期若價格在 110 元以下 為極佳安全邊際。")
                                st.markdown(f"* 🚀 加碼時機: 股價帶量突破 87MA 或 284MA。")
                                
                                # 區塊 5: 出場風控
                                st.markdown("### 5. 出場/風控 (Exit/Risk)")
                                st.markdown(f"* 🛑 停損: CB 跌破 100 元 (保本天條，新券下檔有限)。")
                                st.markdown(f"* 💰 停利: 目標價 152 元以上，嚴守 「留魚尾」 策略。")
                                
                                st.divider()
                                # [修復] 呼叫 K 線圖 (自動截取 5 碼轉 4 碼)
                                plot_candle_chart(cb_code)

            # --- Tab 3: 滿年沈澱 (Titan V80.19: 鄭思翰 SOP 滿週年啟動版) ---
            with tab3_w9:
                # [修復] 數據清洗與日期計算
                full_data_t3 = full_data.copy()
                if 'issue_date' in full_data_t3.columns:
                    full_data_t3['issue_date'] = pd.to_datetime(full_data_t3['issue_date'], errors='coerce')
                
                # 計算上市天數
                full_data_t3 = full_data_t3.dropna(subset=['issue_date'])
                full_data_t3['days_old'] = (now - full_data_t3['issue_date']).dt.days
                
                # [核心篩選邏輯修正]
                def check_mask_t3(row):
                    try:
                        if not (350 <= row['days_old'] <= 420): return False
                        p = pd.to_numeric(row.get('price'), errors='coerce') or 0.0
                        if p >= 115 or p <= 0: return False
                        raw_c = pd.to_numeric(row.get('conv_rate', 100), errors='coerce') or 100.0
                        actual_conv = (100.0 - raw_c) if raw_c > 50 else raw_c
                        if actual_conv >= 30: return False
                        return True
                    except:
                        return False

                df_t3 = full_data_t3[full_data_t3.apply(check_mask_t3, axis=1)]
                df_t3 = df_t3.sort_values('days_old', ascending=True)
                
                if df_t3.empty: 
                    st.info("💡 目前無符合「滿年沈澱」標準的標的 (上市滿一年, 價格<115, 轉換率<30%)。")
                else:
                    for _, row in df_t3.iterrows():
                        name = row.get('name', '未知')
                        cb_code = str(row.get('code', row.get('stock_code', '0000'))).strip()
                        days = int(row['days_old'])
                        price = pd.to_numeric(row.get('price'), errors='coerce') or 0.0
                        ma87 = pd.to_numeric(row.get('ma87'), errors='coerce') or 0.0
                        stock_price = pd.to_numeric(row.get('stock_price_real'), errors='coerce') or 0.0
                        raw_c = pd.to_numeric(row.get('conv_rate', 100), errors='coerce') or 100.0
                        converted_percentage = (100.0 - raw_c) if raw_c > 50 else raw_c

                        title = f"💤 {name} ({cb_code}) | 沈澱 {days} 天 (滿週年) | CB價: {price:.1f}"
                        with st.expander(title):
                            is_above_ma87 = stock_price > ma87 if ma87 > 0 else False
                            st.markdown(f"### 🛡️ 沈澱檢核: `✅ 上市 {days} 天` | `✅ 價格 < 115` | `{'✅ 已站上 87MA' if is_above_ma87 else '⚠️ 均線下方'}`")
                            st.divider()

                            with st.expander("📄 查看滿年沈澱深度分析 (Consolidation Report)", expanded=False):
                                st.markdown(f"## 📊 {name} ({cb_code}) 滿年甦醒評估")
                                st.info("### 1. 核心策略檢核 (The 4 Commandments)")
                                st.markdown(f"1. 價格天條 (<115): ✅ 通過 (沈澱期最佳成本區，目前 **{price:.1f}**)")
                                check_trend = "✅ 通過 (已站上 87MA)" if is_above_ma87 else "⚠️ 均線整理中"
                                st.markdown(f"2. 中期多頭排列: {check_trend}")
                                if ma87 > 0:
                                    st.markdown(f"> 均線數據: 現價 **{stock_price:.2f}** {' > ' if is_above_ma87 else ' < '} 87MA **{ma87:.2f}**")
                                st.markdown("3. 身分認證 (Identity): ☐ 領頭羊 / ☐ 風口豬")
                                st.markdown("4. 發債故事 (Story): ☐ 從無到有 / ☐ 擴產 / ☐ 政策事件")
                                st.divider()
                                st.success("### 2. 決策輔助 (Decision Support)")
                                conv_price = pd.to_numeric(row.get('conv_price_val', 0.01), errors='coerce')
                                parity = (stock_price / conv_price * 100) if conv_price > 0 else 0.0
                                conv_value = pd.to_numeric(row.get('conv_value_val', 0.0), errors='coerce')
                                premium = ((price - conv_value) / conv_value * 100) if conv_value > 0 else 0.0
                                c1, c2, c3 = st.columns(3)
                                c1.metric("理論價 (Parity)", f"{parity:.2f}")
                                c2.metric("溢價率 (Premium)", f"{premium:.2f}%")
                                c3.metric("已轉換比例", f"{converted_percentage:.2f}%")
                                st.markdown("### 4. 交易計畫 (Trading Plan)")
                                st.markdown(f"* 🎯 沈澱期佈局: 滿一年後，股價只要「站穩 87MA」即為首波觀察進場點。")
                                st.markdown(f"* 🚀 加碼時機: 當 87MA 正式由平轉上揚，且股價帶量突破橫盤區間。")
                                st.markdown("### 5. 出場/風控 (Exit/Risk)")
                                st.markdown(f"* 🛑 停損: CB 跌破 100 元 (保本天條)。")
                                st.markdown(f"* 💰 停利: 目標價 152 元以上。")
                                st.divider()
                                plot_candle_chart(cb_code)

            # --- Tab 4: 賣回保衛 (Titan V80.20: 鄭思翰 SOP 套利保衛版) ---
            with tab4_w9:
                full_data_t4 = full_data.copy()
                if 'put_date' in full_data_t4.columns:
                    full_data_t4['put_date'] = pd.to_datetime(full_data_t4['put_date'], errors='coerce')
                full_data_t4['days_to_put'] = (full_data_t4['put_date'] - now).dt.days
                
                def check_mask_t4(row):
                    try:
                        if pd.isna(row['days_to_put']) or not (0 < row['days_to_put'] < 180): return False
                        p = pd.to_numeric(row.get('price'), errors='coerce') or 0.0
                        if not (95 <= p <= 105): return False
                        raw_c = pd.to_numeric(row.get('conv_rate', 100), errors='coerce') or 100.0
                        actual_conv = (100.0 - raw_c) if raw_c > 50 else raw_c
                        if actual_conv >= 30: return False
                        return True
                    except:
                        return False

                df_t4 = full_data_t4[full_data_t4.apply(check_mask_t4, axis=1)]
                df_t4 = df_t4.sort_values('days_to_put', ascending=True)
                
                if df_t4.empty: 
                    st.info("💡 目前無符合「賣回保衛」標準的標的 (距賣回<180天, 價格 95~105, 轉換率<30%)。")
                else:
                    for _, row in df_t4.iterrows():
                        name = row.get('name', '未知')
                        cb_code = str(row.get('code', row.get('stock_code', '0000'))).strip()
                        left_days = int(row['days_to_put'])
                        price = pd.to_numeric(row.get('price'), errors='coerce') or 0.0
                        put_date_str = row['put_date'].strftime('%Y-%m-%d')
                        ma87 = pd.to_numeric(row.get('ma87'), errors='coerce') or 0.0
                        ma284 = pd.to_numeric(row.get('ma284'), errors='coerce') or 0.0
                        stock_price = pd.to_numeric(row.get('stock_price_real'), errors='coerce') or 0.0
                        raw_c = pd.to_numeric(row.get('conv_rate', 100), errors='coerce') or 100.0
                        converted_percentage = (100.0 - raw_c) if raw_c > 50 else raw_c

                        title = f"🛡️ {name} ({cb_code}) | 賣回倒數 {left_days} 天 | CB價: {price:.1f}"
                        with st.expander(title):
                            st.markdown(f"### 🚨 保衛警告: `📅 賣回日: {put_date_str}` | `✅ 價格甜甜圈區間` | `✅ 已轉換 {converted_percentage:.2f}%`")
                            st.divider()

                            with st.expander("📄 查看賣回保衛戰術報告 (Put Protection Report)", expanded=False):
                                st.markdown(f"## 📊 {name} ({cb_code}) 賣回壓力測試")
                                st.error("### 1. 核心策略檢核 (The 4 Commandments)")
                                st.markdown(f"1. 價格天條 (95-105): ✅ 通過 (目前 **{price:.1f}**)")
                                is_bullish = ma87 > ma284
                                st.markdown(f"2. 中期多頭排列: {'✅ 通過' if is_bullish else '⚠️ 整理中'}")
                                st.markdown("3. 身分認證 (Identity): ☐ 領頭羊 / ☐ 風口豬")
                                st.markdown("4. 發債故事 (Story): ☐ 從無到有 / ☐ 擴產 / ☐ 政策事件")
                                st.divider()
                                st.success("### 2. 決策輔助 (Decision Support)")
                                conv_price = pd.to_numeric(row.get('conv_price_val', 0.01), errors='coerce')
                                parity = (stock_price / conv_price * 100) if conv_price > 0 else 0.0
                                conv_value = pd.to_numeric(row.get('conv_value_val', 0.0), errors='coerce')
                                premium = ((price - conv_value) / conv_value * 100) if conv_value > 0 else 0.0
                                c1, c2, c3 = st.columns(3)
                                c1.metric("距離賣回", f"{left_days} 天")
                                c2.metric("溢價率 (Premium)", f"{premium:.2f}%")
                                c3.metric("目標價", "152+", delta="保本套利")
                                st.markdown("### 4. 交易計畫 (Trading Plan)")
                                st.markdown(f"* 🎯 進場佈局: 此區間 (95-105) 買入，下檔風險極低。")
                                st.markdown(f"* 🚀 爆發點: 觀察賣回日前 2-3 個月，股價站上 87MA 且量增。")
                                st.markdown("### 5. 出場/風控 (Exit/Risk)")
                                st.markdown(f"* 🛑 停損: 原則上不需停損。")
                                st.markdown(f"* 💰 停利: 目標價 152 元以上，或賣回當天執行。")
                                st.divider()
                                plot_candle_chart(cb_code)

            # ==========================================
            # Tab 5: 產業風口地圖 (Titan V103: IC.TPEX 官方 30 大產業鏈)
            # ==========================================
            with tab5_w9:
                st.subheader("🌌 IC.TPEX 官方產業價值矩陣")
                
                # --- 1. 核心數據處理 (官方 30 大分類引擎) ---
                @st.cache_data(ttl=3600)
                def get_tpex_data(raw_df):
                    # TPEx 官方 30 大產業分類標籤 (基準)
                    # 1.半導體 2.通信網路 3.電腦週邊 4.電子零組件 5.光電 6.電子通路 7.資訊服務 8.其他電子
                    # 9.生技醫療 10.紡織纖維 11.電機機械 12.電器電纜 13.化學工業 14.建材營造 15.航運業
                    # 16.觀光事業 17.金融業 18.貿易百貨 19.油電燃氣 20.文化創意 21.鋼鐵工業 22.橡膠工業
                    # 23.塑膠工業 24.汽車工業 25.食品工業 26.造紙工業 27.綠能環保 28.運動休閒 29.居家生活 30.其他

                    # 精準對應字典 (手動定義精華版 - 擴充至 30 類)
                    chain_map = {
                        # [1. 半導體]
                        '世芯': ('半導體', '⬆️ 上游-IC設計', 'IP/ASIC'), '創意': ('半導體', '⬆️ 上游-IC設計', 'IP/ASIC'),
                        '聯發科': ('半導體', '⬆️ 上游-IC設計', '手機SoC'), '瑞昱': ('半導體', '⬆️ 上游-IC設計', '網通IC'),
                        '台積': ('半導體', '↔️ 中游-製造', '晶圓代工'), '聯電': ('半導體', '↔️ 中游-製造', '晶圓代工'),
                        '弘塑': ('半導體', '↔️ 中游-設備', '濕製程'), '辛耘': ('半導體', '↔️ 中游-設備', 'CoWoS'),
                        '萬潤': ('半導體', '↔️ 中游-設備', '封測設備'), '日月光': ('半導體', '⬇️ 下游-封測', '封裝'),
                        
                        # [2. 通信網路]
                        '智邦': ('通信網路', '⬇️ 下游-網通設備', '交換器'), '啟碁': ('通信網路', '⬇️ 下游-網通設備', '衛星/車用'),
                        '中磊': ('通信網路', '⬇️ 下游-網通設備', '寬頻'), '全新': ('通信網路', '⬆️ 上游-元件', 'PA砷化鎵'),
                        '穩懋': ('通信網路', '⬆️ 上游-元件', 'PA代工'), '華星光': ('通信網路', '↔️ 中游-光通訊', 'CPO模組'),
                        '波若威': ('通信網路', '↔️ 中游-光通訊', '光纖元件'), '聯亞': ('通信網路', '↔️ 中游-光通訊', '雷射二極體'),

                        # [3. 電腦週邊]
                        '廣達': ('電腦週邊', '⬇️ 下游-組裝', 'AI伺服器'), '緯創': ('電腦週邊', '⬇️ 下游-組裝', 'AI伺服器'),
                        '技嘉': ('電腦週邊', '⬇️ 下游-品牌', '板卡/Server'), '微星': ('電腦週邊', '⬇️ 下游-品牌', '電競'),
                        '奇鋐': ('電腦週邊', '↔️ 中游-散熱', '3D VC'), '雙鴻': ('電腦週邊', '↔️ 中游-散熱', '水冷板'),
                        '勤誠': ('電腦週邊', '↔️ 中游-機殼', '伺服器機殼'), '川湖': ('電腦週邊', '↔️ 中游-機構', '導軌'),
                        '樺漢': ('電腦週邊', '⬇️ 下游-工業電腦', 'IPC'), '研華': ('電腦週邊', '⬇️ 下游-工業電腦', 'IPC'),

                        # [4. 電子零組件]
                        '台光電': ('電子零組件', '⬆️ 上游-材料', 'CCL銅箔基板'), '台燿': ('電子零組件', '⬆️ 上游-材料', 'CCL高頻'),
                        '金像電': ('電子零組件', '↔️ 中游-PCB', '伺服器板'), '健鼎': ('電子零組件', '↔️ 中游-PCB', 'HDI'),
                        '欣興': ('電子零組件', '↔️ 中游-PCB', 'ABF載板'), '南電': ('電子零組件', '↔️ 中游-PCB', 'ABF載板'),
                        '國巨': ('電子零組件', '↔️ 中游-被動元件', 'MLCC'), '華新科': ('電子零組件', '↔️ 中游-被動元件', 'MLCC'),
                        '凡甲': ('電子零組件', '↔️ 中游-連接器', '車用/Server'), '嘉澤': ('電子零組件', '↔️ 中游-連接器', 'CPU Socket'),

                        # [5. 光電]
                        '大立光': ('光電', '⬆️ 上游-光學', '鏡頭'), '玉晶光': ('光電', '⬆️ 上游-光學', '鏡頭'),
                        '亞光': ('光電', '⬆️ 上游-光學', '車載鏡頭'), '群創': ('光電', '↔️ 中游-面板', 'LCD'),
                        '友達': ('光電', '↔️ 中游-面板', 'LCD'), '中光電': ('光電', '⬇️ 下游-背光', '背光模組'),

                        # [9. 生技醫療]
                        '藥華藥': ('生技醫療', '⬆️ 上游-新藥', '新藥研發'), '合一': ('生技醫療', '⬆️ 上游-新藥', '新藥研發'),
                        '保瑞': ('生技醫療', '↔️ 中游-製造', 'CDMO'), '美時': ('生技醫療', '↔️ 中游-製造', '學名藥'),
                        '晶碩': ('生技醫療', '⬇️ 下游-醫材', '隱形眼鏡'), '視陽': ('生技醫療', '⬇️ 下游-醫材', '隱形眼鏡'),
                        '大樹': ('生技醫療', '⬇️ 下游-通路', '藥局'), '長佳智能': ('生技醫療', '⬆️ 上游-資訊', 'AI醫療'),

                        # [11. 電機機械]
                        '上銀': ('電機機械', '⬆️ 上游-傳動', '滾珠螺桿'), '亞德客': ('電機機械', '⬆️ 上游-氣動', '氣動元件'),
                        '東元': ('電機機械', '↔️ 中游-馬達', '工業馬達'), '中砂': ('電機機械', '⬆️ 上游-耗材', '鑽石碟'),

                        # [14. 建材營造]
                        '華固': ('建材營造', '⬇️ 下游-建設', '住宅商辦'), '長虹': ('建材營造', '⬇️ 下游-建設', '住宅商辦'),
                        '興富發': ('建材營造', '⬇️ 下游-建設', '住宅'), '遠雄': ('建材營造', '⬇️ 下游-建設', '廠辦'),
                        '國產': ('建材營造', '⬆️ 上游-材料', '預拌混凝土'),

                        # [15. 航運業]
                        '長榮': ('航運業', '↔️ 中游-海運', '貨櫃'), '陽明': ('航運業', '↔️ 中游-海運', '貨櫃'),
                        '萬海': ('航運業', '↔️ 中游-海運', '貨櫃'), '長榮航': ('航運業', '↔️ 中游-空運', '航空'),
                        '華航': ('航運業', '↔️ 中游-空運', '航空'), '星宇': ('航運業', '↔️ 中游-空運', '航空'),
                        '慧洋': ('航運業', '↔️ 中游-散裝', '散裝航運'), '裕民': ('航運業', '↔️ 中游-散裝', '散裝航運'),

                        # [24. 汽車工業]
                        '東陽': ('汽車工業', '↔️ 中游-零組件', 'AM保險桿'), '堤維西': ('汽車工業', '↔️ 中游-零組件', 'AM車燈'),
                        '帝寶': ('汽車工業', '↔️ 中游-零組件', 'AM車燈'), '裕隆': ('汽車工業', '⬇️ 下游-整車', '品牌製造'),
                        '中華': ('汽車工業', '⬇️ 下游-整車', '商用車'), '和泰車': ('汽車工業', '⬇️ 下游-代理', 'TOYOTA'),

                        # [27. 綠能環保 (含重電)]
                        '華城': ('綠能環保', '↔️ 中游-重電', '變壓器'), '士電': ('綠能環保', '↔️ 中游-重電', '配電盤'),
                        '中興電': ('綠能環保', '↔️ 中游-重電', 'GIS開關'), '亞力': ('綠能環保', '↔️ 中游-重電', '輸配電'),
                        '世紀鋼': ('綠能環保', '⬆️ 上游-風電', '水下基礎'), '森崴': ('綠能環保', '⬇️ 下游-能源', '綠電開發'),
                        '雲豹': ('綠能環保', '⬇️ 下游-能源', '儲能/太陽能'),

                        # [30. 其他 (含軍工)]
                        '漢翔': ('其他', '↔️ 中游-航太', '軍工/民航'), '龍德': ('其他', '↔️ 中游-造船', '軍艦'),
                    }
                    
                    def classify(name):
                        # 1. 字典精準匹配
                        for k, v in chain_map.items():
                            if k in name: return v
                        
                        # 2. 關鍵字模糊歸類 (對標官方 30 大)
                        # 半導體
                        if any(x in name for x in ['電', '科', '矽', '晶', '半']): 
                            if '光' in name: return ('光電', '一般光電', '光電')
                            return ('半導體', '其他半導體', '半導體')
                        # 通信網路
                        if any(x in name for x in ['網', '通', '訊']): return ('通信網路', '網通設備', '通信')
                        # 電腦週邊
                        if any(x in name for x in ['腦', '機', '資']): return ('電腦週邊', '系統', '電腦')
                        # 電子零組件
                        if any(x in name for x in ['板', '線', '器', '零']): return ('電子零組件', '被動/連接', '零組件')
                        # 生技醫療
                        if any(x in name for x in ['生', '醫', '藥']): return ('生技醫療', '生技', '醫療')
                        # 綠能環保
                        if any(x in name for x in ['綠', '能', '源', '電', '華城', '重電']): return ('綠能環保', '能源', '綠能')
                        # 航運
                        if any(x in name for x in ['航', '運', '船']): return ('航運業', '運輸', '航運')
                        # 建材營造
                        if any(x in name for x in ['營', '建', '地']): return ('建材營造', '建設', '營造')
                        # 金融
                        if any(x in name for x in ['金', '銀', '保']): return ('金融業', '金融', '金控')
                        # 汽車
                        if any(x in name for x in ['車', '汽']): return ('汽車工業', '零組件', '汽車')
                        
                        return ('其他', '未分類', '其他')

                    d = raw_df.copy()
                    d[['L1', 'L2', 'L3']] = d['name'].apply(lambda x: pd.Series(classify(x)))
                    
                    # 數值清洗 (Sanitization) - 照抄原版邏輯
                    d['ma87'] = pd.to_numeric(d['ma87'], errors='coerce')
                    d['price'] = pd.to_numeric(d['stock_price_real'], errors='coerce')
                    # 若無 MA87，乖離率設為 0 (灰色)
                    d['bias'] = ((d['price'] - d['ma87']) / d['ma87'] * 100)
                    d['bias_clean'] = d['bias'].fillna(0).clip(-25, 25) # 限制顏色範圍
                    d['bias_label'] = d['bias'].apply(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "N/A")
                    d['size_metric'] = d['price'].fillna(10) # 暫用股價當方塊大小
                    
                    return d

                df_galaxy = get_tpex_data(full_data)

                # --- 2. 繪製 Plotly 熱力圖 (照抄原版 UI) ---
                fig = px.treemap(
                    df_galaxy,
                    path=['L1', 'L2', 'L3', 'name'],
                    values='size_metric',
                    color='bias_clean',
                    color_continuous_scale=['#00FF00', '#262730', '#FF0000'], # 綠跌 -> 黑平 -> 紅漲
                    color_continuous_midpoint=0,
                    hover_data={'name':True, 'bias_label':True, 'L3':True, 'size_metric':False, 'bias_clean':False},
                    title='<b>🎯 資金流向熱力圖 (IC.TPEX 官方分類版)</b>'
                )
                fig.update_layout(margin=dict(t=30, l=10, r=10, b=10), height=500, font=dict(size=14))
                fig.update_traces(
                    textinfo="label+text", 
                    texttemplate="%{label}<br>%{customdata[1]}", # 顯示名稱 + 乖離率
                    textposition="middle center"
                )
                st.plotly_chart(fig, use_container_width=True)

                st.divider()

                # --- 3. 全軍戰力排行榜 (TPEx 30大戰區 結構化分組) ---
                st.subheader("🏆 全產業戰力排行榜 (Sector Roster)")
                st.info("💡 點擊下方官方產業板塊，展開查看「上中下游」兵力部署")

                # 計算各板塊平均強弱，並排序
                sector_stats = df_galaxy.groupby('L1')['bias'].mean().sort_values(ascending=False)
                
                # 遍歷排序後的板塊
                for sector, avg_bias in sector_stats.items():
                    # 找出該板塊所有股票
                    sector_df = df_galaxy[df_galaxy['L1'] == sector]
                    count = len(sector_df)
                    if count == 0: continue # 跳過無兵力的戰區

                    bulls = len(sector_df[sector_df['bias'] > 0])
                    
                    # 標題設計 (名次感)
                    header_color = "🔴" if avg_bias > 0 else "🟢"
                    header = f"{header_color} **{sector}** (均 {avg_bias:+.1f}%) | 強勢 {bulls}/{count} 檔"
                    
                    with st.expander(header):
                        # 核心：依照 L2 (上中下游) 分組顯示
                        l2_groups = sector_df.groupby('L2')
                        
                        # 簡單排序：字串排序 (上游 > 下游 > 中游... 中文排序不準，這裡直接遍歷 keys)
                        # 為了符合人類直覺，我們嘗試把 "上游" 排前面
                        sorted_l2 = sorted(l2_groups.groups.keys(), key=lambda x: 0 if '上' in str(x) else (1 if '中' in str(x) else 2))

                        for l2 in sorted_l2:
                            sub_df = l2_groups.get_group(l2).sort_values('bias', ascending=False)
                            st.markdown(f"**{l2}**") # 顯示分組標題 (如 ⬆️ 上游-IC設計)
                            
                            # 製作漂亮的表格或條列 (照抄原版)
                            cols = st.columns(3) 
                            for idx, row in sub_df.iterrows():
                                color = "red" if row['bias'] > 0 else "#00FF00"
                                label = row['bias_label']
                                # 格式： 3661 世芯 (+5.2%)
                                st.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['code']} {row['name']}</span> <span style='color:#aaa; font-size:0.9em;'>({label})</span>", unsafe_allow_html=True)
                            st.markdown("---")
        
    with st.expander("2.3 潛在風險雷達 (Risk Radar)", expanded=False):
        if 'scan_results' in st.session_state and not df.empty:
            scan_results = st.session_state['scan_results']
            st.info("此區塊為「負面表列」清單，旨在警示符合特定風險條件的標的，提醒您「避開誰」。")

            required_risk_cols = ['converted_ratio', 'premium', 'avg_volume']
            if all(col in scan_results.columns for col in required_risk_cols):
                
                tab1_w13, tab2_w13, tab3_w13 = st.tabs(["**☠️ 籌碼鬆動 (主力落跑)**", "**⚠️ 高溢價 (肉少湯喝)**", "**🧊 流動性陷阱 (殭屍債)**"])

                with tab1_w13:
                    abandoned_df = scan_results[scan_results['converted_ratio'] > 30].sort_values('converted_ratio', ascending=False)
                    if not abandoned_df.empty:
                        st.warning(f"發現 {len(abandoned_df)} 檔標的「已轉換比例」 > 30%，特定人可能已在下車。")
                        st.dataframe(abandoned_df[['name', 'code', 'converted_ratio', 'price', 'action']].head(20).fillna(''))
                    else:
                        st.success("✅ 目前無標的觸發「籌碼鬆動」警示。")

                with tab2_w13:
                    overpriced_df = scan_results[scan_results['premium'] > 20].sort_values('premium', ascending=False)
                    if not overpriced_df.empty:
                        st.warning(f"發現 {len(overpriced_df)} 檔標的「溢價率」 > 20%，潛在報酬空間可能受壓縮。")
                        st.dataframe(overpriced_df[['name', 'code', 'premium', 'price', 'parity']].head(20).fillna(0))
                    else:
                        st.success("✅ 目前無標的觸發「高溢價」警示。")

                with tab3_w13:
                    illiquid_df = scan_results[scan_results['avg_volume'] < 10].sort_values('avg_volume', ascending=True)
                    if not illiquid_df.empty:
                        st.error(f"發現 {len(illiquid_df)} 檔標的平均成交量 < 10 張，存在嚴峻的流動性風險！")
                        st.dataframe(illiquid_df[['name', 'code', 'avg_volume', 'price']].head(20).fillna(0))
                    else:
                        st.success("✅ 目前無標的觸發「流動性陷阱」警示。")
            else:
                st.error("掃描結果缺少風險分析所需欄位 (converted_ratio, premium, avg_volume)，請檢查上傳的 Excel 檔案。")
        else:
            st.info("請先執行本頁上方的掃描以啟動風險雷達。")
        
    with st.expander("2.4 資金配置試算 (Position Sizing)", expanded=False):
        # [修正] 直接檢查 scan_results 是否有資料，不再依賴 'action' 欄位
        if 'scan_results' in st.session_state and not st.session_state['scan_results'].empty:
            
            # 視窗 8 篩選出來的結果，就是建議買進名單
            buy_recommendations = st.session_state['scan_results']
            
            st.success(f"已同步獵殺結果：共 {len(buy_recommendations)} 檔可配置標的")

            total_capital = st.number_input("輸入您的總操作資金 (元)", min_value=100000, value=2000000, step=100000)
            
            if not buy_recommendations.empty:
                st.subheader("建議投資組合 (Top 5)")
                portfolio_list = []
                
                # 依分數排序，若無分數則依價格
                sort_col = 'score' if 'score' in buy_recommendations.columns else 'price'
                top_picks = buy_recommendations.sort_values(sort_col, ascending=False).head(5)

                for _, row in top_picks.iterrows():
                    cb_price = row.get('price', 0)
                    name = row.get('name', '未知')
                    code = row.get('code', '0000')
                    
                    if cb_price > 0:
                        # 簡單資金模型：每檔 20%
                        investment_per_stock = total_capital * 0.20
                        # 試算張數 (一張 1000 股，價格單位為元?? 通常 CB 價格是百元報價，一張十萬)
                        # 修正：CB 報價通常為 100-120，一張面額 10 萬，市值約 10-12 萬
                        # 這裡假設 cb_price 是 106.0 這種格式 -> 一張市值 = cb_price * 1000
                        market_value_per_unit = cb_price * 1000
                        num_shares = investment_per_stock / market_value_per_unit
                        
                        portfolio_list.append(
                            f"- **{name} ({code})** | 市價 `{cb_price}` | "
                            f"建議配置 `{int(num_shares)}` 張 (約 {int(investment_per_stock):,} 元)"
                        )
                st.markdown("\n".join(portfolio_list))
            else:
                st.info("目前無符合 SOP 標準之標的。")
        else:
            st.info("請先執行本頁上方的掃描以獲取買進建議。")
        
    with st.expander("2.5 歷史回測驗證 (Strategy Backtest)", expanded=False):
        if 'scan_results' in st.session_state:
            results_df = st.session_state['scan_results']
            if not results_df.empty:
                st.info("對推薦標的進行過去一年的回測，模擬『站上 87MA 買進、跌破賣出』的績效。")
                
                recommendations = results_df[results_df['action'].str.contains('買進', na=False)].head(5)
                
                for _, row in recommendations.iterrows():
                    stock_code = row['stock_code']
                    cb_name = row['name']
                    
                    if st.button(f"🔙 跑回測 (1年): {cb_name}"):
                        with st.spinner(f"正在為 {cb_name} 執行回測..."):
                            ticker = f"{stock_code}.TW"
                            trades_df = backtester.run_simulation(ticker, cb_name)
                            report, detailed_trades = backtester.generate_report(trades_df)
                            
                            st.text(report)
                            if not detailed_trades.empty:
                                st.dataframe(detailed_trades)

            else:
                st.warning("請先點擊本頁上方的掃描按鈕以生成推薦標的。")
        else:
            st.info("請先點擊本頁上方的掃描按鈕以生成推薦標的。")

@st.fragment
def render_sniper_tab():
    """Renders the Sniper Tab content, isolated for performance."""
    with st.expander("3.1 萬用個股狙擊雷達 (Universal Sniper)", expanded=True):
        import numpy as np
        import altair as alt

        st.info("🌍 全球戰情模式：支援台股 (2330)、美股 (TSLA, PLTR)、加密貨幣BTC-USD。已啟動雙軌扣抵預演系統。")

        w17_in = st.text_input("輸入代號或股名", value="2330", key="w17_final_v102").strip()

        if w17_in:
            try:
                from macro_risk import STOCK_METADATA
                N2T = {v['name'].strip(): k for k, v in STOCK_METADATA.items()}
                if w17_in in N2T: w17_in = N2T[w17_in]
            except: pass
            
            cands = [w17_in]
            if w17_in.isdigit(): cands = [f"{w17_in}.TW", f"{w17_in}.TWO"]
            elif not w17_in.endswith((".TW", ".TWO")): cands = [w17_in.upper(), f"{w17_in.upper()}.TW"]
            
            sdf = pd.DataFrame(); v_ticker = None
            with st.spinner("掃描全球資料庫..."):
                for c in cands:
                    temp = macro.get_single_stock_data(c, period="max")
                    # 必須有足夠資料計算 284MA
                    if not temp.empty and len(temp) >= 300: 
                        sdf = temp; v_ticker = c; break
            
            if sdf.empty: 
                st.error("❌ 查無數據，或歷史數據不足 300 天無法計算年線扣抵。")
            else:
                # --- Data Cleaning ---
                try:
                    if isinstance(sdf.columns, pd.MultiIndex): sdf.columns = sdf.columns.get_level_values(0)
                    sdf.columns = [str(c).strip().capitalize() for c in sdf.columns]
                    sdf = sdf.reset_index()
                    # Date Column Normalization
                    date_col = next((c for c in sdf.columns if str(c).lower() in ['date', 'datetime', 'index']), None)
                    if date_col:
                        sdf.rename(columns={date_col: 'Date'}, inplace=True)
                        sdf['Date'] = pd.to_datetime(sdf['Date'])
                        sdf.set_index('Date', inplace=True)
                        sdf.sort_index(inplace=True)
                    
                    col_map = {}
                    for c in sdf.columns:
                        if c.lower() in ['close', 'price']: col_map[c] = 'Close'
                        elif c.lower() in ['volume', 'vol']: col_map[c] = 'Volume'
                    sdf.rename(columns=col_map, inplace=True)
                    
                    for req in ['Open', 'High', 'Low']:
                        if req not in sdf.columns: sdf[req] = sdf['Close']
                    if 'Volume' not in sdf.columns: sdf['Volume'] = 0
                    
                    # Ensure numeric
                    for c in ['Close', 'Open', 'High', 'Low', 'Volume']:
                        sdf[c] = pd.to_numeric(sdf[c], errors='coerce')
                    sdf = sdf.dropna()

                except Exception as e: st.error(f"資料格式錯誤: {e}"); st.stop()

                # --- Base Indicators ---
                sdf['MA87'] = sdf['Close'].rolling(87).mean()
                sdf['MA284'] = sdf['Close'].rolling(284).mean()
                
                # [CRITICAL FIX] 計算 Cross_Signal 避免 Tab 3 報錯
                sdf['Prev_MA87'] = sdf['MA87'].shift(1)
                sdf['Prev_MA284'] = sdf['MA284'].shift(1)
                sdf['Cross_Signal'] = 0
                # 黃金交叉: 昨87<=昨284 且 今87>今284
                sdf.loc[(sdf['Prev_MA87'] <= sdf['Prev_MA284']) & (sdf['MA87'] > sdf['MA284']), 'Cross_Signal'] = 1 
                # 死亡交叉: 昨87>=昨284 且 今87<今284
                sdf.loc[(sdf['Prev_MA87'] >= sdf['Prev_MA284']) & (sdf['MA87'] < sdf['MA284']), 'Cross_Signal'] = -1 
                
                # Latest Values
                cp = float(sdf['Close'].iloc[-1])
                op = float(sdf['Open'].iloc[-1])
                m87 = float(sdf['MA87'].iloc[-1]) if not pd.isna(sdf['MA87'].iloc[-1]) else 0
                m87_prev5 = float(sdf['MA87'].iloc[-6]) if len(sdf) > 6 and not pd.isna(sdf['MA87'].iloc[-6]) else m87
                m284 = float(sdf['MA284'].iloc[-1]) if not pd.isna(sdf['MA284'].iloc[-1]) else 0

                # Status Check
                trend_days = 0; trend_status_str = "整理中"
                if m87 > 0 and m284 > 0:
                    is_bullish = m87 > m284
                    trend_status_str = "🔥 中期多頭 (87>284)" if is_bullish else "❄️ 中期空頭 (87<284)"
                    bull_series = sdf['MA87'] > sdf['MA284']
                    current_state = bull_series.iloc[-1]
                    for i in range(len(bull_series)-1, -1, -1):
                        if bull_series.iloc[i] == current_state: trend_days += 1
                        else: break
                
                granville_title, granville_desc = get_advanced_granville(cp, op, m87, m87_prev5)
                bias = ((cp - m87) / m87) * 100 if m87 > 0 else 0

                # --- Header Metrics ---
                st.subheader(f"🎯 {v_ticker} 戰情報告")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("目前股價", f"{cp:.2f}")
                c2.metric("87MA (季線)", f"{m87:.2f}", f"{cp-m87:.2f}")
                c3.metric("284MA (年線)", f"{m284:.2f}", f"{cp-m284:.2f}")
                c4.metric("乖離率 (Bias)", f"{bias:.1f}%")
                st.markdown("---")

                # --- Tabs Definition ---
                t1, t2, t3, t4, t5, t6, t7 = st.tabs([
                    "🔮 雙軌扣抵預演", "📐 亞當理論", "🕯️ 日 K (含交叉)", 
                    "🗓️ 月 K 線", "🧠 ARK 戰情室", "💎 智能估值", "🌊 5波模擬"
                ])
                
                # ==========================================
                # Tab 1: 量子路徑預演 (Titan V82: Quantum Path Prediction)
                # ==========================================
                with t1:
                    st.markdown("#### 🔮 殿堂級全息戰略預演 (Holographic Strategy)")
                    
                    # --- 1. 參數設定與運算核心 (Smart Calc) ---
                    # 自動計算波動率 (ATR 概念模擬)
                    hist_volatility = sdf['Close'].pct_change().std() * 100 # 歷史波動率
                    current_vol = max(1.5, hist_volatility) # 設一個地板值，避免死魚股波動太小

                    # 擴展版面設定 (手機優化)
                    with st.expander("⚙️ 戰略參數設定 (點擊展開)", expanded=False):
                        c1, c2 = st.columns(2)
                        with c1:
                            sim_days = st.slider("預演天數", 10, 60, 20)
                        with c2:
                            # 不再只是死板輸入，而是作為「動能參數」
                            momentum_input = st.number_input("假設動能 (%)", -10.0, 10.0, 0.0, step=0.5)
                            st.caption(f"目前波動率: {current_vol:.1f}%")
                    
                    # 準備數據
                    future_days = sim_days
                    last_date = sdf.index[-1]
                    future_dates = [last_date + pd.Timedelta(days=i+1) for i in range(future_days)]
                    
                    # --- 2. 建立「五維全息劇本」 (5D Scenarios) ---
                    # 核心邏輯：不是畫一條線，而是畫出「機率錐」
                    
                    # 劇本 A: 慣性 (Inertia) - 跟隨目前 10MA 斜率
                    slope_10 = (sdf['Close'].iloc[-1] - sdf['Close'].iloc[-10]) / 10
                    path_inertia = [cp + slope_10 * (i+1) for i in range(future_days)]
                    
                    # 劇本 B: 波動率上緣 (Bull Case)
                    path_bull = [cp * (1 + (current_vol/100) * np.sqrt(i+1)) for i in range(future_days)]
                    
                    # 劇本 C: 波動率下緣 (Bear Case)
                    path_bear = [cp * (1 - (current_vol/100) * np.sqrt(i+1)) for i in range(future_days)]

                    # 選擇主要顯示路徑 (根據用戶輸入微調)
                    sim_prices = []
                    curr_sim = cp
                    for i in range(future_days):
                        # 基礎波動 + 用戶輸入動能
                        drift = momentum_input / 100
                        curr_sim = curr_sim * (1 + drift)
                        sim_prices.append(curr_sim)
                    
                    # 合併數據計算均線
                    future_series = pd.Series(sim_prices, index=future_dates)
                    combined_series = pd.concat([sdf['Close'], future_series])
                    
                    # 計算均線
                    combined_ma87 = combined_series.rolling(87).mean()
                    combined_ma284 = combined_series.rolling(284).mean()
                    
                    # 提取扣抵值 (Ghost Lines)
                    start_idx = len(sdf)
                    all_closes = combined_series.values
                    deduct_87 = [all_closes[start_idx + i - 87] if (start_idx + i - 87) >= 0 else np.nan for i in range(future_days)]
                    deduct_284 = [all_closes[start_idx + i - 284] if (start_idx + i - 284) >= 0 else np.nan for i in range(future_days)]
                    
                    # 建立 DataFrame
                    f_df = pd.DataFrame({
                        'Date': future_dates,
                        'Sim_Price': sim_prices,
                        'Bull_Bound': path_bull, # 機率錐上緣
                        'Bear_Bound': path_bear, # 機率錐下緣
                        'MA87': combined_ma87.loc[future_dates].values,
                        'MA284': combined_ma284.loc[future_dates].values,
                        'Deduct_87': deduct_87,
                        'Deduct_284': deduct_284
                    })

                    # --- 3. 🤖 G-Score 量化評分系統 (The God Score) ---
                    score = 0
                    reasons = []
                    
                    # 因子 A: 趨勢 (30分)
                    ma87_curr = combined_ma87.iloc[-future_days-1]
                    ma284_curr = combined_ma284.iloc[-future_days-1]
                    if cp > ma87_curr: score += 15
                    if cp > ma284_curr: score += 15
                    
                    # 因子 B: 動能 (20分)
                    if cp > sdf['Close'].iloc[-20:].mean(): score += 20
                    
                    # 因子 C: 雙線結構 (30分)
                    bias_diff = abs(ma87_curr - ma284_curr) / ma284_curr
                    is_squeeze = bias_diff < 0.015 # 乖離小於 1.5% 視為糾纏
                    if ma87_curr > ma284_curr: score += 30 # 黃金排列
                    
                    # 因子 D: 扣抵壓力 (20分)
                    future_deduct_87_avg = np.mean(deduct_87[:20])
                    if future_deduct_87_avg < cp: score += 20 # 扣抵低值
                    
                    # 狀態定義
                    if score >= 80: g_status = "🔥 多頭坦途 (Clear Sky)"
                    elif score >= 50: g_status = "⚠️ 區間震盪 (Range Bound)"
                    else: g_status = "🐻 空頭承壓 (Bearish Pressure)"

                    # --- 4. 📱 總司令戰報 (Commander's Briefing) ---
                    # 這是 V82 的核心：極致細緻的手機版文字介面
                    
                    # 計算關鍵價位
                    fib_high = max(path_bull)
                    fib_low = min(path_bear)
                    fib_0618 = fib_low + (fib_high - fib_low) * 0.618
                    
                    # 雙線糾纏邏輯
                    squeeze_msg = ""
                    if is_squeeze:
                        squeeze_msg = f"🌪️ **螺旋絞殺 (Squeeze)**：87MA 與 284MA 乖離僅 **{bias_diff*100:.2f}%**。兩線打結，預計 **3-5天內** 出現大變盤。"
                    else:
                        if ma87_curr > ma284_curr:
                            squeeze_msg = "🚀 **發散攻擊**：均線呈多頭排列，開口擴大，趨勢明確。"
                        else:
                            squeeze_msg = "📉 **空頭壓制**：均線呈空頭排列，上方層層賣壓。"

                    # 顯示戰報區塊
                    st.markdown(f"""
                    <div style="background-color:#1E1E1E; padding:15px; border-radius:10px; border: 1px solid #444;">
                        <h3 style="color:#FFA500; margin:0;">📊 G-Score 量化總評：{score} 分</h3>
                        <p style="color:#ddd; margin-top:5px;">狀態：<b>{g_status}</b> | 指令：<b>{'積極操作' if score>70 else '觀望/區間' if score>40 else '保守防禦'}</b></p>
                        <hr style="border-top: 1px solid #555;">
                        <h4 style="color:#4db8ff; margin:0;">⚔️ 雙線糾纏場 (Interaction)</h4>
                        <p style="color:#ccc; font-size:14px; margin-top:5px;">{squeeze_msg}</p>
                        <p style="color:#ccc; font-size:14px;">
                           • <b>87MA (季)</b>：{ma87_curr:.1f}元 | 扣抵位置：{deduct_87[0]:.1f}元 ({'扣低助漲' if deduct_87[0]<cp else '扣高壓力'})<br>
                           • <b>284MA (年)</b>：{ma284_curr:.1f}元 | 扣抵位置：{deduct_284[0]:.1f}元
                        </p>
                        <hr style="border-top: 1px solid #555;">
                        <h4 style="color:#98FB98; margin:0;">🔮 五維全息劇本 (Scenarios)</h4>
                        <p style="color:#ccc; font-size:14px; margin-top:5px;">關鍵變盤窗：<b>{(last_date + pd.Timedelta(days=13)).strftime('%m/%d')} (費氏轉折)</b></p>
                        <ul style="color:#ccc; font-size:14px; padding-left:20px;">
                            <li><b>劇本 A (慣性 50%)</b>：股價在 <b>{fib_low:.1f} ~ {fib_high:.1f}元</b> 區間震盪，以盤代跌。</li>
                            <li><b>劇本 B (破底翻 30%)</b>：回測 <b>{fib_0618:.1f}元</b> (Fib 0.618) 支撐不破，V型反轉。</li>
                            <li><b>劇本 C (風險 20%)</b>：若收盤跌破 <b>{min(deduct_87[:5]):.1f}元</b>，確認均線蓋頭，向下尋求支撐。</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("") # Spacer

                    # --- 5. 視覺化 (Altair 波動率機率錐) ---
                    # 這是 User 習慣的介面，加上機率錐 (Band)
                    
                    base = alt.Chart(f_df).encode(x='Date:T')
                    
                    # 機率錐 (Fan Chart)
                    cone = base.mark_area(opacity=0.2, color='gray').encode(
                        y='Bear_Bound:Q', y2='Bull_Bound:Q'
                    )
                    
                    # 模擬線與均線
                    line_sim = base.mark_line(color='white', strokeDash=[4,2]).encode(y='Sim_Price')
                    line_87 = base.mark_line(color='orange', strokeWidth=2).encode(y='MA87')
                    line_284 = base.mark_line(color='#00bfff', strokeWidth=2).encode(y='MA284')
                    
                    # 幽靈線 (Deduction)
                    ghost_87 = base.mark_line(color='red', strokeDash=[1,1], opacity=0.5).encode(y='Deduct_87')
                    ghost_284 = base.mark_line(color='blue', strokeDash=[1,1], opacity=0.3).encode(y='Deduct_284')
                    
                    # 歷史K線 (簡化版)
                    hist_df = sdf.iloc[-60:].reset_index()
                    base_hist = alt.Chart(hist_df).encode(x='Date:T')
                    candle = base_hist.mark_rule().encode(y='Low', y2='High') + \
                             base_hist.mark_bar().encode(y='Open', y2='Close', 
                             color=alt.condition("datum.Open <= datum.Close", alt.value("#FF4B4B"), alt.value("#00AA00")))

                    chart = (cone + candle + line_sim + line_87 + line_284 + ghost_87 + ghost_284).properties(
                        height=500,
                        title="量子路徑預演 (含波動率機率錐)"
                    )
                    
                    st.altair_chart(chart.interactive(), use_container_width=True)
                with t2: # 亞當
                    adf = macro.calculate_adam_projection(sdf, 20)
                    if not adf.empty:
                        h = sdf.iloc[-60:].reset_index(); h['T']='History'
                        p = adf.reset_index(); p['T']='Project'; p.rename(columns={'Projected_Price':'Close'}, inplace=True)
                        st.altair_chart(alt.Chart(pd.concat([h,p])).mark_line().encode(x='Date:T', y=alt.Y('Close', scale=alt.Scale(zero=False)), color='T').interactive(), use_container_width=True)
                    else: st.warning("資料不足。")

                with t3: # 日 K
                    kd = sdf.tail(252).reset_index()
                    x_scale = alt.X('Date:T', axis=alt.Axis(format='%m/%d', title='Date'))
                    base_k = alt.Chart(kd).encode(x=x_scale)
                    candle = base_k.mark_rule().encode(y=alt.Y('Low', scale=alt.Scale(zero=False)), y2='High', color=alt.condition("datum.Open<=datum.Close", alt.value("#FF0000"), alt.value("#00AA00"))) + \
                             base_k.mark_bar().encode(y='Open', y2='Close', color=alt.condition("datum.Open<=datum.Close", alt.value("#FF0000"), alt.value("#00AA00")))
                    l87 = base_k.mark_line(color='blue', strokeWidth=2).encode(y='MA87', tooltip=['MA87'])
                    l284 = base_k.mark_line(color='purple', strokeWidth=2).encode(y='MA284', tooltip=['MA284'])
                    cross_data = kd[kd['Cross_Signal'] != 0]
                    chart_price = candle + l87 + l284
                    if not cross_data.empty:
                        cross_points = alt.Chart(cross_data).mark_point(size=150, filled=True, opacity=1).encode(
                            x='Date:T', y='Close', shape=alt.condition("datum.Cross_Signal > 0", alt.value("triangle-up"), alt.value("triangle-down")),
                            color=alt.condition("datum.Cross_Signal > 0", alt.value("gold"), alt.value("black")),
                            tooltip=['Date', 'Close', 'Cross_Signal']
                        )
                        chart_price += cross_points
                    chart_price = chart_price.properties(height=350, title=f"{v_ticker} 日 K 線圖")
                    chart_vol = base_k.mark_bar().encode(y='Volume', color=alt.condition("datum.Open<=datum.Close", alt.value("#FF0000"), alt.value("#00AA00"))).properties(height=100)
                    st.altair_chart(alt.vconcat(chart_price, chart_vol).resolve_scale(x='shared').interactive(), use_container_width=True)
                    st.caption("指標：🔵 87MA | 🟣 284MA | ▲ 黃金交叉 | ▼ 死亡交叉")

                with t4: # 月 K
                    try:
                        freq = 'ME'
                        try: sdf.resample('ME').last()
                        except: freq = 'M'
                        md = sdf.resample(freq).agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                        if len(md) >= 43:
                            md['MA43'] = md['Close'].rolling(43).mean(); md['MA87'] = md['Close'].rolling(87).mean(); md['MA284'] = md['Close'].rolling(284).mean()
                            pm = md.tail(120).reset_index()
                            bm = alt.Chart(pm).encode(x=alt.X('Date:T', axis=alt.Axis(format='%Y-%m')))
                            mc = bm.mark_rule().encode(y='Low', y2='High', color=alt.condition("datum.Open<=datum.Close", alt.value("#FF0000"), alt.value("#00AA00"))) + \
                                 bm.mark_bar().encode(y='Open', y2='Close', color=alt.condition("datum.Open<=datum.Close", alt.value("#FF0000"), alt.value("#00AA00")))
                            ln43 = bm.mark_line(color='orange').encode(y='MA43'); ln87 = bm.mark_line(color='blue').encode(y='MA87'); ln284 = bm.mark_line(color='purple').encode(y='MA284')
                            st.altair_chart((mc + ln43 + ln87 + ln284).interactive(), use_container_width=True)
                            st.caption("月線指標：🟠 43MA | 🔵 87MA | 🟣 284MA")
                        else: st.warning("月線資料不足。")
                    except Exception as e: st.error(f"月線失敗: {e}")

                # 財務數據 (Fix: Safe Defaults)
                try:
                    stock_info = yf.Ticker(v_ticker).info
                    rev_ttm = stock_info.get('totalRevenue', 0)
                    shares_out = stock_info.get('sharesOutstanding', 0)
                    eps_ttm = stock_info.get('trailingEps', 0)
                    analyst_growth = stock_info.get('revenueGrowth', stock_info.get('earningsGrowth', 0.15))
                    if analyst_growth is None: analyst_growth = 0.15
                    is_us_stock = not v_ticker.endswith(('.TW', '.TWO'))
                    region_tag = "🇺🇸 美股" if is_us_stock else "🇹🇼 台股"
                    region_hint = "美股通常享有較高估值溢價" if is_us_stock else "台股估值相對保守"
                except: rev_ttm=0; shares_out=0; eps_ttm=0; analyst_growth=0.15; is_us_stock=False; region_tag="未知"; region_hint=""

                with t5: # ARK [Fixed: Expanded Range + Safe Clamp]
                    st.markdown(f"### 🧠 ARK 戰情室 ({region_tag})")
                    st.info(f"💡 基於期望值的三情境推演。{region_hint}")
                    if rev_ttm > 0 and shares_out > 0:
                        c1, c2, c3 = st.columns(3)
                        # 範圍解鎖：成長率 -1000% ~ 5000%, 淨利率 -500% ~ 500%, PE 0 ~ 9999
                        safe_g = safe_clamp(analyst_growth, -10.0, 50.0)
                        base_g = c1.number_input("基本成長率", -10.0, 50.0, safe_g, 0.01)
                        base_m = c2.number_input("基本淨利率", -5.0, 5.0, 0.20, 0.01)
                        base_pe = c3.number_input("基本 PE", 0.0, 9999.0, 30.0 if is_us_stock else 20.0, 1.0)
                        
                        scenarios = calculate_ark_scenarios(rev_ttm, shares_out, cp, base_g, base_m, base_pe)
                        if scenarios:
                            st.divider()
                            k1, k2, k3 = st.columns(3)
                            k1.error(f"🐻 熊市\n\n${scenarios['Bear']['Target']:.1f}\n\nCAGR: {scenarios['Bear']['CAGR']:.1%}")
                            k2.info(f"⚖️ 基本\n\n${scenarios['Base']['Target']:.1f}\n\nCAGR: {scenarios['Base']['CAGR']:.1%}")
                            k3.success(f"🐮 牛市\n\n${scenarios['Bull']['Target']:.1f}\n\nCAGR: {scenarios['Bull']['CAGR']:.1%}")
                    else: st.warning("財務數據不足。")

                with t6: # Smart Valuation [Fixed: Expanded Range + Safe Clamp]
                    st.markdown(f"### 💎 智能估值引擎 ({region_tag})")
                    if rev_ttm > 0:
                        ind_opts = ["🚀 軟體/SaaS", "💊 生技", "⚙️ 硬體", "🏭 傳統"]
                        ind_sel = st.selectbox("產業模板：", ind_opts)
                        if "軟體" in ind_sel: def_m=0.25; def_pe=50.0
                        elif "生技" in ind_sel: def_m=0.30; def_pe=40.0
                        elif "硬體" in ind_sel: def_m=0.15; def_pe=25.0
                        else: def_m=0.08; def_pe=15.0
                        if is_us_stock: def_pe *= 1.2
                        
                        s1, s2, s3 = st.columns(3)
                        safe_g_s = safe_clamp(analyst_growth, -10.0, 50.0)
                        # ========== START: MODIFICATION ==========
                        u_growth = s1.number_input("成長率", min_value=-10.0, max_value=None, value=safe_g_s, step=0.01)
                        u_margin = s2.number_input("淨利率", min_value=-5.0, max_value=None, value=float(def_m), step=0.01)
                        u_pe = s3.number_input("終端 PE", min_value=0.0, max_value=None, value=float(def_pe), step=1.0)
                        # ========== END: MODIFICATION ==========
                        
                        fair_val = calculate_smart_valuation(eps_ttm, rev_ttm, shares_out, u_growth, u_margin, u_pe)
                        st.divider()
                        v1, v2 = st.columns(2)
                        v1.metric("目前股價", f"{cp:.2f}")
                        v2.metric("合理估值", f"{fair_val:.2f}", f"{cp-fair_val:.2f}", delta_color="inverse")
                    else: st.warning("數據不足。")

                with t7: # Wave Sim [High Visibility]
                    st.markdown("### 🌊 艾略特 5 波模擬 (Elliott Wave Sim)")
                    st.info("💡 虛線為 AI 模擬路徑。文字已優化，提高辨識度。")
                    zz_df = calculate_zigzag(sdf.tail(300), 0.03)
                    
                    if not zz_df.empty:
                        base_zz = alt.Chart(zz_df).encode(x='Date:T')
                        real_line = base_zz.mark_line(point=True, color='black').encode(
                            y=alt.Y('Price', scale=alt.Scale(zero=False)), tooltip=['Date', 'Price', 'Type'])
                        text_price = base_zz.mark_text(dy=-15, color='blue', fontSize=14, fontWeight='bold').encode(y='Price', text=alt.Text('Price', format='.1f'))
                        
                        chart = real_line + text_price
                        sim_df = calculate_5_waves(zz_df)
                        if not sim_df.empty:
                            sim_line = alt.Chart(sim_df).mark_line(strokeDash=[5,5], color='red').encode(
                                x='Date:T', y='Price', tooltip=['Date', 'Price', 'Label'])
                            sim_point = alt.Chart(sim_df[sim_df['Label'] != 'Origin']).mark_circle(color='red', size=60).encode(x='Date:T', y='Price')
                            # [High Viz]: Blue, Bold, 14px, Larger Offset (dy=30)
                            sim_label = alt.Chart(sim_df[sim_df['Label'] != 'Origin']).mark_text(dy=-30, color='blue', fontSize=14, fontWeight='bold').encode(
                                x='Date:T', y='Price', text='Label')
                            sim_target = alt.Chart(sim_df[sim_df['Label'] != 'Origin']).mark_text(dy=30, color='blue', fontSize=14, fontWeight='bold').encode(
                                x='Date:T', y='Price', text=alt.Text('Price', format='.1f'))
                            
                            chart = chart + sim_line + sim_point + sim_label + sim_target
                        st.altair_chart(chart.interactive(), use_container_width=True)
                    else: st.warning("波動過小，無法計算。")

with tab3: # 單兵狙擊總部
    render_sniper_tab()

with tab4: # 戰力升級預留區
    st.info("⚠️ 系統維修中 (System Under Maintenance)")
    st.markdown("""
    ### 🚧 核彈級戰略升級路徑 (Roadmap)
    本區域預留給以下投行級模組，目前施工中：
    * **1. 黑天鵝壓力測試矩陣 (Black Swan Stress Matrix)**
    * **2. 流動性深度與吃貨估算 (Liquidity & Impact Model)**
    * **3. 凱利公式自動倉位演算 (Kelly Execution Engine)**
    * **4. 組合風險矩陣 (Portfolio Risk Matrix)**
    * **5. AI 財報關鍵字獵殺升級 (AI Keyword Hunter V2)**
    """)

with tab5: # 戰略百科
    with st.expander("5.1 SOP 戰略百科 (SOP Strategy Encyclopedia)", expanded=False):
        with st.expander("點此展開，查核系統內建的完整 SOP 規則庫"):
            if 'all_rules' not in st.session_state:
                st.session_state.all_rules = kb.get_all_rules_for_ui()
            
            all_rules = st.session_state.all_rules

            tab1_w7, tab2_w7, tab3_w7, tab4_w7, tab5_w7 = st.tabs(["**四大時間套利**", "**進出場紀律**", "**產業族群庫**", "**特殊心法**", "**OTC神奇均線**"])

            with tab1_w7:
                st.subheader("SOP 時間套利總覽")
                if all_rules.get("time_arbitrage"):
                    for rule in all_rules["time_arbitrage"]:
                        st.markdown(f"- {rule}")
                else:
                    st.warning("無法載入時間套利規則。")

            with tab2_w7:
                st.subheader("SOP 進出場規則原文 (摘錄)")
                entry_exit_rules = all_rules.get("entry_exit", {})
                st.text_area("進場條件 (Entry)", value=entry_exit_rules.get('entry', '無紀錄'), height=300)
                st.text_area("出場條件 (Exit)", value=entry_exit_rules.get('exit', '無紀錄'), height=300)
            
            with tab3_w7:
                st.subheader("SOP 核心產業與故事")
                industry_info = all_rules.get("industry_story", {})
                
                st.markdown("#### **發債故事總覽**")
                general_stories = industry_info.get("general_issuance_stories", [])
                if general_stories:
                    st.text_area("General Issuance Stories", value="\n\n".join(general_stories), height=200)
                
                st.markdown("---")
                st.markdown("#### **族群與領頭羊對照**")
                sector_map = industry_info.get("sector_map", {})
                if sector_map:
                    sector_data = []
                    for sector, stocks in sorted(sector_map.items()):
                        sector_data.append({"族群 (Sector)": sector, "關聯標的 (Stocks)": ", ".join(sorted(list(stocks)))})
                    st.dataframe(pd.DataFrame(sector_data), use_container_width=True)
                else:
                    st.warning("無法載入產業族群庫。")

            with tab4_w7:
                st.subheader("隱藏心法與特殊策略")
                special_tactics = all_rules.get("special_tactics", [])
                if special_tactics:
                    st.text_area("Tactics & Mindset", value="\n\n---\n\n".join(special_tactics), height=500)
                else:
                    st.warning("無法載入特殊心法。")

            with tab5_w7:
                st.subheader("OTC 神奇均線法則 (OTC Magic MA Rules)")
                otc_rules = kb.get_otc_magic_rules()
                for rule_name, rule_desc in otc_rules.items():
                    st.markdown(f"**{rule_name.replace('_', ' ').title()}**: {rule_desc}")

    with st.expander("5.2 情報獵殺分析結果", expanded=False):
        intel_files = st.session_state.get('intel_files', [])
        api_key = st.session_state.get('api_key', '')

        if intel_files:
            for file in intel_files:
                with st.expander(f"📄 分析報告: {file.name}"):
                    analysis_result = intel.analyze_file(file, kb, df)
                    if "error" in analysis_result:
                        st.error(analysis_result["error"])
                        continue

                    st.markdown(analysis_result.get("local_analysis_md", "本地分析失敗。"))
                    st.divider()

                    if api_key:
                        with st.spinner(f"執行 Gemini AI 深度分析: {file.name}..."):
                            try:
                                genai.configure(api_key=api_key)
                                gemini_report = intel.analyze_with_gemini(analysis_result["full_text"])
                                st.markdown("### 💎 **Gemini AI 深度解析**")
                                st.markdown(gemini_report)
                            except Exception as e:
                                st.error(f"Gemini API Key 設定失敗或無效: {e}")
                    else:
                        st.info("未輸入 Gemini API Key，跳過 AI 深度解析。")
        else:
            st.info("請於左側上傳情報文件以進行分析。")
        
    with st.expander("5.3 CBAS 槓桿試算儀", expanded=False):
        cbas_c1, cbas_c2 = st.columns(2)
        cb_price = cbas_c1.number_input("輸入 CB 市價", min_value=100.0, value=110.0, step=0.5, format="%.2f")
        premium_cost = cb_price - 100

        if premium_cost > 0:
            leverage = cb_price / premium_cost
            
            cbas_c1.metric("💰 理論權利金 (百元)", f"{premium_cost:.2f} 元")
            cbas_c2.metric("⚖️ 槓桿倍數", f"{leverage:.2f} 倍")

            if leverage > 3:
                st.success("🔥 高槓桿甜蜜點：目前槓桿效益佳，適合以小博大。")
            else:
                st.warning("⚠️ 肉少湯喝：槓桿效益較低，風險報酬比可能不佳，建議直接買進 CB 現股。")
        else:
            st.info("CB 市價需高於 100 元才能計算 CBAS 權利金。")
        
    with st.expander("5.4 時間套利行事曆 (Event Calendar)", expanded=False):
        if not df.empty:
            days_ahead = st.slider("選擇要掃描的未來天數", 7, 90, 30)
            
            upcoming_events = []
            today = datetime.now().date()
            future_date = today + timedelta(days=days_ahead)

            for _, row in df.iterrows():
                events = calendar.calculate_time_traps(str(row['code']), str(row.get('list_date', '')), str(row.get('put_date', '')))
                for event in events:
                    event_date = pd.to_datetime(event['date']).date()
                    if today <= event_date <= future_date:
                        upcoming_events.append({
                            "name": row['name'],
                            "date": event_date,
                            "event": event['event'],
                            "desc": event['desc']
                        })

            if upcoming_events:
                upcoming_events.sort(key=lambda x: x['date'])
                st.subheader(f"未來 {days_ahead} 天的關鍵事件")
                
                for event in upcoming_events:
                    days_to_event = (event['date'] - today).days
                    st.markdown(f"📅 **{days_to_event}天後 ({event['date'].strftime('%Y-%m-%d')})**: `{event['name']}` - **{event['event']}**")
                    st.caption(event['desc'])
            else:
                st.info(f"未來 {days_ahead} 天內無觸發任何時間套利事件。")
        else:
            st.info("請上傳 CB 清單以掃描時間套利事件。")
    st.divider()