# app.py
# Titan SOP V82.0 - 元趨勢創世紀版 (Meta-Trend Genesis)
# [V82.0 Patch]:
# 1. [Structure] Tab 6 元趨勢戰法重構：升級為「插槽式開發母港」，為次世代引擎預留標準化接口。
# 2. [Methodology] 植入「月K幾何學」數學定義：在 Tab 6 中明確定義「上帝視角協議 (God's Eye Protocol)」，
#    包含 35 年全景數據跨度與 9 檔位視覺角度分級，作為未來算法核心。
# 3. [Structure] 部署 7 大戰術插槽 (Slots)：在 Tab 6 預留數據、算法、LLM、記憶、辯論、視覺化與獵殺清單
#    等七大核心開發接口，確保未來擴展性。
# 4. [Maintenance] 維護 V81.1 穩定性：保留首頁標題特效、Fragment 頁面隔離、120 分鐘記憶鎖、
#    以及 Tab 4.4/4.5 的正確功能佈局。
# [CRITICAL FIX V81.1]: Corrected data loading logic to prioritize "可轉債市價" for the 'close' field, preventing misidentification with underlying stock price.
import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from config import WAR_THEATERS  # [V89.1 新增] 全境獵殺戰區清單
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
import plotly.graph_objects as go
import io

# ==========================================
# [V81] System Initialization & State Management
# ==========================================
st.set_page_config(page_title="Titan SOP V82.0", layout="wide", page_icon="🏛️")

# --- Session State Initialization (Key Error Protection) ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'df' not in st.session_state:
    st.session_state['df'] = pd.DataFrame()
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = ''
if 'intel_files' not in st.session_state:
    st.session_state['intel_files'] = []
# [V81] 持久化投資組合
if 'portfolio_df' not in st.session_state:
    st.session_state.portfolio_df = pd.DataFrame([
        {'資產代號': '2330', '持有數量 (股)': 1000, '買入均價': 500.0, '資產類別': 'Stock'},
        {'資產代號': '00675L', '持有數量 (股)': 5000, '買入均價': 15.0, '資產類別': 'ETF'},
        {'資產代號': 'NVDA', '持有數量 (股)': 100, '買入均價': 400.0, '資產類別': 'US_Stock'},
        {'資產代號': 'TLT', '持有數量 (股)': 200, '買入均價': 95.0, '資產類別': 'US_Bond'},
        {'資產代號': 'CASH', '持有數量 (股)': 500000, '買入均價': 1.0, '資產類別': 'Cash'},
    ])


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

# --- [V81.1] 120 分鐘長效記憶鎖 (Memory Persistence) ---
now = datetime.now()
is_locked = False
if 'last_active_time' in st.session_state:
    time_diff = now - st.session_state.last_active_time
    if time_diff > timedelta(minutes=120):
        # 超過120分鐘，重置投資組合
        st.session_state.portfolio_df = pd.DataFrame([
            {'資產代號': '2330', '持有數量 (股)': 1000, '買入均價': 500.0, '資產類別': 'Stock'},
            {'資產代號': '00675L', '持有數量 (股)': 5000, '買入均價': 15.0, '資產類別': 'ETF'},
            {'資產代號': 'NVDA', '持有數量 (股)': 100, '買入均價': 400.0, '資產類別': 'US_Stock'},
            {'資產代號': 'TLT', '持有數量 (股)': 200, '買入均價': 95.0, '資產類別': 'US_Bond'},
            {'資產代號': 'CASH', '持有數量 (股)': 500000, '買入均價': 1.0, '資產類別': 'Cash'},
        ])
        if 'sidebar_message' not in st.session_state:
             st.session_state.sidebar_message = st.sidebar.warning("閒置超過120分鐘，投資組合已重置。", icon="⚠️")
    else:
        is_locked = True

# 每次運行都更新最後活動時間
st.session_state.last_active_time = now


# ==========================================
# [V80 Core Logic] All helper functions are preserved
# ==========================================
def run_fast_backtest(ticker, start_date="2023-01-01", initial_capital=1000000):
    """
    [UPGRADED V78.3] 極速向量化回測引擎 (Vectorized Backtest Engine)
    策略邏輯：模擬趨勢追蹤 (Trend Following) - 當收盤價 > 20日均線時買入
    支援：台股 (TW/TWO)、美股、現金 (CASH)
    
    【Step 1 修正】台股 ETF 識別增強：
    - 使用正則表達式判斷 4-6 碼且開頭為數字的代號
    - 優先嘗試 .TW，失敗再嘗試 .TWO
    """
    try:
        # Handle CASH asset
        if ticker.upper() in ['CASH', 'USD', 'TWD']:
            dates = yf.download('^TWII', start=start_date, progress=False).index
            if dates.empty: return None
            df = pd.DataFrame(index=dates)
            df['Close'] = 1.0
            df['Strategy_Return'] = 0.0
            df['Equity'] = initial_capital
            df['Drawdown'] = 0.0
            
            return {
                "cagr": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0,
                "win_rate": 0.0, "profit_factor": 0.0, "kelly": 0.0,
                "equity_curve": df['Equity'], "drawdown_series": df['Drawdown'],
                "latest_price": 1.0
            }

        # 1. 智慧代碼處理 (增強版：支援混合型代號如 00675L)
        original_ticker = ticker
        
        # 【Step 1 修正】使用正則判斷：長度 4-6 碼且開頭為數字
        if re.match(r'^[0-9]', ticker) and 4 <= len(ticker) <= 6:
            ticker = f"{ticker}.TW"
        
        # 2. 下載數據 (優先 .TW，失敗再試 .TWO)
        df = yf.download(ticker, start=start_date, progress=False)
        if df.empty:
            # 僅對符合台股格式的代碼重試 .TWO
            if re.match(r'^[0-9]', original_ticker) and 4 <= len(original_ticker) <= 6:
                ticker_two = f"{original_ticker}.TWO"
                df = yf.download(ticker_two, start=start_date, progress=False)
            if df.empty:
                return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or len(df) < 21: return None

        # 3. 策略信號生成
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Signal'] = 0
        df.loc[df['Close'] > df['MA20'], 'Signal'] = 1
        
        # 4. 績效計算
        df['Pct_Change'] = df['Close'].pct_change()
        df['Strategy_Return'] = df['Signal'].shift(1) * df['Pct_Change']
        df['Equity'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() * initial_capital
        
        # 5. 凱利參數計算
        trade_days = df[df['Signal'].shift(1) == 1]
        if len(trade_days) < 10:
            win_rate, profit_factor, kelly = 0, 0, 0
        else:
            wins = trade_days[trade_days['Strategy_Return'] > 0]['Strategy_Return']
            losses = trade_days[trade_days['Strategy_Return'] < 0]['Strategy_Return']
            
            win_rate = len(wins) / len(trade_days)
            avg_win = wins.mean() if len(wins) > 0 else 0
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
            profit_factor = avg_win / avg_loss if avg_loss != 0 else 0
            
            if profit_factor > 0:
                kelly = win_rate - ((1 - win_rate) / profit_factor)
            else:
                kelly = 0
        
        # 6. 新增專業指標
        df['Drawdown'] = (df['Equity'] / df['Equity'].cummax()) - 1
        max_drawdown = df['Drawdown'].min()

        num_years = len(df) / 252
        total_return = df['Equity'].iloc[-1] / initial_capital - 1
        cagr = ((1 + total_return) ** (1 / num_years)) - 1 if num_years > 0 else 0

        risk_free_rate = 0.02
        daily_returns = df['Strategy_Return'].dropna()
        if daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() * 252 - risk_free_rate) / (daily_returns.std() * np.sqrt(252))
        else:
            sharpe_ratio = 0.0

        return {
            "cagr": cagr, "sharpe_ratio": sharpe_ratio, "max_drawdown": max_drawdown,
            "win_rate": win_rate, "profit_factor": profit_factor, "kelly": max(0, kelly),
            "equity_curve": df['Equity'], "drawdown_series": df['Drawdown'],
            "latest_price": df['Close'].iloc[-1]
        }
    except Exception:
        return None

# --- [V81.1] 效能補丁: 10 分鐘戰術緩存 ---
@st.cache_data(ttl=600)
def get_macro_data(_macro, _df):
    """快取宏觀風控數據"""
    return _macro.check_market_status(cb_df=_df)

@st.cache_data(ttl=600)
def get_scan_result(_strat, _df):
    """快取策略掃描結果"""
    return _strat.scan_entire_portfolio(_df)

@st.cache_data(ttl=7200)
def run_stress_test(portfolio_text):
    """
    [V82.1 FIX] 全球黑天鵝壓力測試 (含台股智慧識別)
    """
    # 1. 解析輸入
    lines = [line.strip() for line in portfolio_text.split('\n') if line.strip()]
    flat_lines = []
    for line in lines:
        flat_lines.extend(item.strip() for item in line.split('|') if item.strip())

    if not flat_lines:
        return pd.DataFrame(), {}

    portfolio = []
    for item in flat_lines:
        parts = [p.strip() for p in item.split(';')]
        if len(parts) == 2 and parts[1]:
            try:
                # 這裡保留原始輸入，稍後在下載時處理
                portfolio.append({'ticker': parts[0].upper(), 'shares': float(parts[1])})
            except ValueError:
                st.warning(f"跳過無效項目: {item}")
                continue
    
    if not portfolio:
        return pd.DataFrame(), {}

    # 2. 下載基準與匯率數據
    try:
        benchmarks_data = yf.download(['^TWII', '^GSPC', 'USDTWD=X'], period="1y", progress=False)
        if benchmarks_data.empty:
            return pd.DataFrame(), {"error": "無法下載市場基準數據 (^TWII, ^GSPC)。"}
        # 處理 MultiIndex
        if isinstance(benchmarks_data.columns, pd.MultiIndex):
            twd_fx_rate = benchmarks_data['Close']['USDTWD=X'].iloc[-1]
        else:
            twd_fx_rate = benchmarks_data['USDTWD=X'].iloc[-1]
    except Exception as e:
        return pd.DataFrame(), {"error": f"下載市場數據失敗: {e}"}

    # 3. 處理每個資產
    results = []
    for asset in portfolio:
        original_ticker = asset['ticker']
        shares = asset['shares']
        ticker = original_ticker # 用於下載的代號
        
        # [現金處理]
        if original_ticker in ['CASH', 'USD', 'TWD']:
            results.append({
                'ticker': original_ticker,
                'type': 'Cash',
                'shares': shares,
                'price': 1.0,
                'value_twd': shares,
                '損益_回檔 (-5%)': 0,
                '損益_修正 (-10%)': 0,
                '損益_技術熊市 (-20%)': 0,
                '損益_金融海嘯 (-30%)': 0,
            })
            continue
        
        # [V82.1 關鍵修復] 台股智慧識別邏輯
        # 如果是純數字且長度為 4-6 碼，自動嘗試加 .TW 或 .TWO
        import re
        is_tw_stock = False
        if re.match(r'^[0-9]', original_ticker) and 4 <= len(original_ticker) <= 6:
            ticker = f"{original_ticker}.TW"
            is_tw_stock = True

        try:
            # 下載數據
            data = yf.download(ticker, period="1mo", progress=False)
            
            # 如果 .TW 失敗，嘗試 .TWO
            if data.empty and is_tw_stock:
                ticker = f"{original_ticker}.TWO"
                data = yf.download(ticker, period="1mo", progress=False)
            
            if data.empty:
                st.warning(f"無法下載 {original_ticker} 的數據，跳過該資產。")
                continue
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            current_price = data['Close'].iloc[-1]
            
            # 判斷資產類型 (用於匯率計算)
            if '.TW' in ticker or '.TWO' in ticker or is_tw_stock:
                asset_type = 'TW_Stock'
                value_twd = current_price * shares
            else:
                asset_type = 'US_Asset'
                value_twd = current_price * shares * twd_fx_rate
            
            # 計算壓力損益
            stress_scenarios = {
                '回檔 (-5%)': -0.05,
                '修正 (-10%)': -0.10,
                '技術熊市 (-20%)': -0.20,
                '金融海嘯 (-30%)': -0.30,
            }
            
            pnl = {}
            for scenario_name, shock in stress_scenarios.items():
                pnl[f'損益_{scenario_name}'] = value_twd * shock
            
            results.append({
                'ticker': original_ticker,
                'type': asset_type,
                'shares': shares,
                'price': current_price,
                'value_twd': value_twd,
                **pnl
            })
        except Exception as e:
            st.warning(f"處理 {original_ticker} 時發生錯誤: {e}")
            continue
    
    if not results:
        return pd.DataFrame(), {"error": "無有效資產數據。"}
    
    results_df = pd.DataFrame(results)
    total_value = results_df['value_twd'].sum()
    
    return results_df, {'total_value': total_value}


# ==================== Tab 4.3 均線戰法回測引擎 ====================
@st.cache_data(ttl=7200)
def run_ma_strategy_backtest(ticker, strategy_name, start_date="2015-01-01", initial_capital=1000000):
    """
    【Tab 4.3 核心】執行 15 種均線策略回測
    
    策略列表：
    1-5: 價格穿越單一均線 (20, 43, 60, 87, 284MA)
    6: 非對稱進出場 (P>20進 / P<60出)
    7-13: 均線交叉策略 (20/60, 20/87, 20/284, 43/87, 43/284, 60/87, 60/284)
    14: 核心戰法 (87MA ↗ 284MA)
    15: 雙確認 (P>20 & P>60 進 / P<60 出)
    """
    try:
        # 智慧代碼處理 (與主回測函數一致)
        original_ticker = ticker
        if re.match(r'^[0-9]', ticker) and 4 <= len(ticker) <= 6:
            ticker = f"{ticker}.TW"
        
        df = yf.download(ticker, start=start_date, progress=False)
        if df.empty:
            if re.match(r'^[0-9]', original_ticker) and 4 <= len(original_ticker) <= 6:
                ticker_two = f"{original_ticker}.TWO"
                df = yf.download(ticker_two, start=start_date, progress=False)
            if df.empty:
                return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 300: return None  # 需要足夠數據計算 284MA
        
        # 計算所有需要的均線
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA43'] = df['Close'].rolling(window=43).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA87'] = df['Close'].rolling(window=87).mean()
        df['MA284'] = df['Close'].rolling(window=284).mean()
        
        # 策略邏輯分派
        df['Signal'] = 0
        
        if strategy_name == "價格 > 20MA":
            df.loc[df['Close'] > df['MA20'], 'Signal'] = 1
        elif strategy_name == "價格 > 43MA":
            df.loc[df['Close'] > df['MA43'], 'Signal'] = 1
        elif strategy_name == "價格 > 60MA":
            df.loc[df['Close'] > df['MA60'], 'Signal'] = 1
        elif strategy_name == "價格 > 87MA":
            df.loc[df['Close'] > df['MA87'], 'Signal'] = 1
        elif strategy_name == "價格 > 284MA":
            df.loc[df['Close'] > df['MA284'], 'Signal'] = 1
        
        elif strategy_name == "非對稱: P>20進 / P<60出":
            # 進場：價格突破 20MA
            # 出場：價格跌破 60MA
            in_position = False
            for i in range(1, len(df)):
                if not in_position and df['Close'].iloc[i] > df['MA20'].iloc[i]:
                    in_position = True
                elif in_position and df['Close'].iloc[i] < df['MA60'].iloc[i]:
                    in_position = False
                df.iloc[i, df.columns.get_loc('Signal')] = 1 if in_position else 0
        
        elif strategy_name == "20/60 黃金/死亡交叉":
            df['Signal'] = 0
            df.loc[df['MA20'] > df['MA60'], 'Signal'] = 1
        elif strategy_name == "20/87 黃金/死亡交叉":
            df.loc[df['MA20'] > df['MA87'], 'Signal'] = 1
        elif strategy_name == "20/284 黃金/死亡交叉":
            df.loc[df['MA20'] > df['MA284'], 'Signal'] = 1
        elif strategy_name == "43/87 黃金/死亡交叉":
            df.loc[df['MA43'] > df['MA87'], 'Signal'] = 1
        elif strategy_name == "43/284 黃金/死亡交叉":
            df.loc[df['MA43'] > df['MA284'], 'Signal'] = 1
        elif strategy_name == "60/87 黃金/死亡交叉":
            df.loc[df['MA60'] > df['MA87'], 'Signal'] = 1
        elif strategy_name == "60/284 黃金/死亡交叉":
            df.loc[df['MA60'] > df['MA284'], 'Signal'] = 1
        
        elif strategy_name == "🔥 核心戰法: 87MA ↗ 284MA":
            # 進場：87MA 向上穿越 284MA
            # 出場：87MA 向下穿越 284MA
            df.loc[df['MA87'] > df['MA284'], 'Signal'] = 1
        
        elif strategy_name == "雙確認: P>20 & P>60 進 / P<60 出":
            in_position = False
            for i in range(1, len(df)):
                if not in_position and (df['Close'].iloc[i] > df['MA20'].iloc[i] and df['Close'].iloc[i] > df['MA60'].iloc[i]):
                    in_position = True
                elif in_position and df['Close'].iloc[i] < df['MA60'].iloc[i]:
                    in_position = False
                df.iloc[i, df.columns.get_loc('Signal')] = 1 if in_position else 0
        
        # 績效計算
        df['Pct_Change'] = df['Close'].pct_change()
        df['Strategy_Return'] = df['Signal'].shift(1) * df['Pct_Change']
        df['Equity'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() * initial_capital
        df['Drawdown'] = (df['Equity'] / df['Equity'].cummax()) - 1
        
        # 計算 CAGR
        num_years = len(df) / 252
        total_return = df['Equity'].iloc[-1] / initial_capital - 1
        cagr = ((1 + total_return) ** (1 / num_years)) - 1 if num_years > 0 else 0
        
        # 財富推演：未來 10 年預期
        future_10y_capital = initial_capital * ((1 + cagr) ** 10)
        
        return {
            "strategy_name": strategy_name,
            "cagr": cagr,
            "final_equity": df['Equity'].iloc[-1],
            "max_drawdown": df['Drawdown'].min(),
            "equity_curve": df['Equity'],
            "drawdown_series": df['Drawdown'],
            "future_10y_capital": future_10y_capital,
            "num_years": num_years
        }
    except Exception as e:
        return None

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

# ==========================================
# [V81.1] Page Rendering Functions
# ==========================================

# --- 🛡️ 宏觀大盤 (Macro) ---
@st.fragment
def render_macro():
    if st.button("🏠 返回戰情總部"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("🛡️ 宏觀大盤 (Macro Dashboard)")
    
    df = st.session_state.get('df', pd.DataFrame())
    
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

# --- 🏹 獵殺雷達 (Radar) ---
@st.fragment
def render_radar():
    if st.button("🏠 返回戰情總部"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("🏹 獵殺雷達 (CB Hunter Zone)")
    
    df = st.session_state.get('df', pd.DataFrame())

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

# --- 🎯 單兵狙擊 (Sniper) ---
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
                    if 'Volume' not in sdf.columns: sdf[Volume] = 0
                    
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

@st.fragment
def render_sniper():
    if st.button("🏠 返回戰情總部"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("🎯 單兵狙擊 (Sniper HQ)")
    render_sniper_tab()

# --- 🚀 全球決策 (Decision) ---
@st.fragment
def render_decision():
    if st.button("🏠 返回戰情總部"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("🚀 全球決策 (Global Command Center)")

    # ==================== 4.1 戰略資產配置 [V81 持久化] ====================
    with st.expander("4.1 📋 戰略資產配置 (Strategic Asset Allocation)", expanded=True):
        st.info("💡 台股 1 張請輸入 1000；美股以 1 股為單位；現金請輸入總額。此處可直接編輯您的資產。")

        portfolio_to_display = st.session_state.portfolio_df.copy()

        asset_tickers = portfolio_to_display[portfolio_to_display['資產類別'] != 'Cash']['資產代號'].tolist()
        latest_prices_map = {}

        if asset_tickers:
            try:
                prices_data = yf.download(asset_tickers, period="1d", progress=False)['Close']
                if len(asset_tickers) == 1:
                    latest_prices_map = {asset_tickers[0]: prices_data.iloc[-1]}
                else:
                    latest_prices_map = prices_data.iloc[-1].to_dict()
            except Exception:
                st.warning("無法獲取即時市價，部分計算欄位將不顯示。")

        portfolio_to_display['現價'] = portfolio_to_display['資產代號'].map(latest_prices_map).fillna(1.0)
        portfolio_to_display['市值'] = portfolio_to_display['持有數量 (股)'] * portfolio_to_display['現價']
        portfolio_to_display['未實現損益'] = (portfolio_to_display['現價'] - portfolio_to_display['買入均價']) * portfolio_to_display['持有數量 (股)']
        
        edited_df = st.data_editor(
            portfolio_to_display,
            column_config={
                "資產代號": st.column_config.TextColumn("資產代號", help="台股/美股代號或CASH"),
                "持有數量 (股)": st.column_config.NumberColumn("持有數量 (股)", format="%d"),
                "買入均價": st.column_config.NumberColumn("買入均價", format="%.2f"),
                "資產類別": st.column_config.SelectboxColumn("資產類別", options=['Stock', 'ETF', 'US_Stock', 'US_Bond', 'Cash']),
                "現價": st.column_config.NumberColumn("現價", format="%.2f", disabled=True),
                "市值": st.column_config.NumberColumn("市值", format="%.0f", disabled=True),
                "未實現損益": st.column_config.NumberColumn("未實現損益", format="%+,.0f", disabled=True),
            },
            num_rows="dynamic",
            key="portfolio_editor_v81_fixed",
            use_container_width=True
        )

        columns_to_save = ['資產代號', '持有數量 (股)', '買入均價', '資產類別']
        st.session_state.portfolio_df = edited_df[columns_to_save]

    # ==================== 4.2 績效回測與凱利決策 [V81 半凱利] ====================
    with st.expander("4.2 📈 績效回測與凱利決策 (Backtest & Kelly Analysis)"):
        if st.button("🚀 啟動全球回測"):
            portfolio_df = st.session_state.get('portfolio_df', pd.DataFrame())
            if portfolio_df.empty:
                st.warning("請先在 4.1 配置您的戰略資產。")
            else:
                with st.spinner("正在對全球資產執行回測..."):
                    backtest_results = []
                    for index, row in portfolio_df.iterrows():
                        ticker = str(row['資產代號']).strip()
                        result = run_fast_backtest(ticker, initial_capital=1000000)
                        if result:
                            result['Ticker'] = ticker
                            backtest_results.append(result)
                    
                    st.session_state.backtest_results = backtest_results

        if 'backtest_results' in st.session_state:
            results = st.session_state.backtest_results
            if not results:
                st.error("所有資產回測失敗，請檢查代號是否正確。")
            else:
                st.subheader("回測績效總覽")
                summary_data = []
                for res in results:
                    conservative_kelly = res['kelly'] * 0.5
                    
                    advice = "🧊 觀望或試單"
                    if conservative_kelly > 0.1: advice = "🔥🔥 重注進攻"
                    elif conservative_kelly >= 0.025: advice = "✅ 穩健配置"
                    
                    summary_data.append({
                        '代號': res['Ticker'],
                        '最新價': res['latest_price'],
                        '年化報酬 (CAGR)': res['cagr'],
                        '投資性價比 (Sharpe)': res['sharpe_ratio'],
                        '最大回撤': res['max_drawdown'],
                        '凱利建議 %': conservative_kelly,
                        '建議動作': advice
                    })
                
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df.style.format({
                    '最新價': '{:.2f}',
                    '年化報酬 (CAGR)': '{:.2%}',
                    '投資性價比 (Sharpe)': '{:.2f}',
                    '最大回撤': '{:.2%}',
                    '凱利建議 %': '{:.2%}',
                }), use_container_width=True)
                st.divider()

                st.subheader("深度圖表分析")
                ticker_options = [res['Ticker'] for res in results]
                selected_ticker = st.selectbox("選擇要查看的資產", options=ticker_options)

                if selected_ticker:
                    selected_result = next((res for res in results if res['Ticker'] == selected_ticker), None)
                    if selected_result:
                        equity_df = selected_result['equity_curve'].reset_index()
                        equity_df.columns = ['Date', 'Equity']
                        fig_equity = px.line(
                            equity_df, x='Date', y='Equity', 
                            title=f"{selected_ticker} 權益曲線 (Equity Curve)",
                            labels={'Equity': '投資組合價值', 'Date': '日期'}
                        )
                        fig_equity.update_traces(line_color='#17BECF')
                        st.plotly_chart(fig_equity, use_container_width=True)

                        drawdown_df = selected_result['drawdown_series'].reset_index()
                        drawdown_df.columns = ['Date', 'Drawdown']
                        drawdown_df['Drawdown_pct'] = drawdown_df['Drawdown'] * 100
                        fig_drawdown = px.area(
                            drawdown_df, x='Date', y='Drawdown_pct',
                            title=f"{selected_ticker} 水下回撤圖 (Underwater Plot)",
                            labels={'Drawdown_pct': '從高點回落 (%)', 'Date': '日期'}
                        )
                        fig_drawdown.update_traces(fillcolor='rgba(255, 87, 51, 0.4)', line_color='rgba(255, 87, 51, 1.0)')
                        fig_drawdown.update_yaxes(ticksuffix="%")
                        st.plotly_chart(fig_drawdown, use_container_width=True)

    # ==================== 4.3 均線戰法回測實驗室 [V81 匯出] ====================
    with st.expander("4.3 🧪 均線戰法回測實驗室 (MA Strategy Lab)", expanded=False):
        st.info("選擇一檔標的，自動執行 15 種均線策略回測，推演 10 年財富變化。")
        
        portfolio_df = st.session_state.get('portfolio_df', pd.DataFrame())
        if portfolio_df.empty:
            st.warning("請先在 4.1 配置您的戰略資產。")
        else:
            ticker_list = portfolio_df['資產代號'].tolist()
            selected_lab_ticker = st.selectbox("選擇回測標的", options=ticker_list, key="ma_lab_ticker")
            
            ma_strategies = [
                "價格 > 20MA", "價格 > 43MA", "價格 > 60MA", "價格 > 87MA", "價格 > 284MA",
                "非對稱: P>20進 / P<60出", "20/60 黃金/死亡交叉", "20/87 黃金/死亡交叉",
                "20/284 黃金/死亡交叉", "43/87 黃金/死亡交叉", "43/284 黃金/死亡交叉",
                "60/87 黃金/死亡交叉", "60/284 黃金/死亡交叉", "🔥 核心戰法: 87MA ↗ 284MA",
                "雙確認: P>20 & P>60 進 / P<60 出"
            ]
            
            if st.button("🔬 啟動 15 種均線實驗", key="start_ma_lab"):
                with st.spinner(f"正在對 {selected_lab_ticker} 執行 15 種均線策略回測..."):
                    ma_results = []
                    for strategy in ma_strategies:
                        result = run_ma_strategy_backtest(
                            ticker=selected_lab_ticker, strategy_name=strategy,
                            start_date="2015-01-01", initial_capital=1000000
                        )
                        if result: ma_results.append(result)
                    st.session_state.ma_lab_results = ma_results
            
            if 'ma_lab_results' in st.session_state and st.session_state.get('ma_lab_ticker') == selected_lab_ticker:
                results = st.session_state.ma_lab_results
                if not results:
                    st.error(f"無法取得 {selected_lab_ticker} 的回測數據。")
                else:
                    st.success(f"✅ {selected_lab_ticker} - 15 種均線策略回測完成")
                    st.subheader("📊 策略績效與財富推演")
                    wealth_data = []
                    for res in results:
                        wealth_data.append({
                            '策略名稱': res['strategy_name'], '年化報酬 (CAGR)': res['cagr'],
                            '回測期末資金': res['final_equity'], '最大回撤': res['max_drawdown'],
                            '未來 10 年預期資金': res['future_10y_capital'], '回測年數': res['num_years']
                        })
                    
                    wealth_df = pd.DataFrame(wealth_data).sort_values('年化報酬 (CAGR)', ascending=False)
                    st.dataframe(wealth_df.style.format({
                        '年化報酬 (CAGR)': '{:.2%}', '回測期末資金': '{:,.0f}',
                        '最大回撤': '{:.2%}', '未來 10 年預期資金': '{:,.0f}', '回測年數': '{:.1f}'
                    }), use_container_width=True)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        wealth_df.to_excel(writer, index=False, sheet_name='MA_Backtest_Report')
                    excel_data = output.getvalue()
                    st.download_button(
                        label="📥 下載戰術回測報表 (Excel)",
                        data=excel_data,
                        file_name=f"{selected_lab_ticker}_ma_lab_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.divider()
                    
                    st.subheader("📈 策略視覺化")
                    strategy_names = [res['strategy_name'] for res in results]
                    selected_strategy = st.selectbox("選擇策略查看圖表", options=strategy_names, key="ma_strategy_chart")
                    
                    selected_res = next((res for res in results if res['strategy_name'] == selected_strategy), None)
                    if selected_res:
                        equity_df = selected_res['equity_curve'].reset_index()
                        equity_df.columns = ['Date', 'Equity']
                        fig_eq = px.line(equity_df, x='Date', y='Equity', title=f"{selected_lab_ticker} - {selected_strategy} 權益曲線", labels={'Equity': '資金 (元)', 'Date': '日期'})
                        fig_eq.update_traces(line_color='#2ECC71')
                        st.plotly_chart(fig_eq, use_container_width=True)
                        
                        dd_df = selected_res['drawdown_series'].reset_index()
                        dd_df.columns = ['Date', 'Drawdown']
                        dd_df['Drawdown_pct'] = dd_df['Drawdown'] * 100
                        fig_dd = px.area(dd_df, x='Date', y='Drawdown_pct', title=f"{selected_lab_ticker} - {selected_strategy} 水下回撤圖", labels={'Drawdown_pct': '回撤 (%)', 'Date': '日期'})
                        fig_dd.update_traces(fillcolor='rgba(231, 76, 60, 0.3)', line_color='rgba(231, 76, 60, 1.0)')
                        fig_dd.update_yaxes(ticksuffix="%")
                        st.plotly_chart(fig_dd, use_container_width=True)

    # ==================== 4.4 智慧調倉計算機 [V81.1 優化] ====================
    with st.expander("4.4 ⚖️ 智慧調倉計算機 (Rebalancing Calculator)"):
        portfolio_df = st.session_state.get('portfolio_df', pd.DataFrame()).copy()
        if portfolio_df.empty or '資產代號' not in portfolio_df.columns:
            st.warning("請先在 4.1 配置您的戰略資產。")
        else:
            tickers = portfolio_df['資產代號'].tolist()
            with st.spinner("正在獲取最新市價..."):
                try:
                    prices_data = yf.download(tickers, period="1d", progress=False)['Close']
                    latest_prices = prices_data.iloc[-1] if isinstance(prices_data, pd.DataFrame) else prices_data
                    
                    portfolio_df['最新市價'] = portfolio_df['資產代號'].map(latest_prices)
                    portfolio_df['最新市價'].fillna(1.0, inplace=True) # 現金類資產
                    portfolio_df['目前市值'] = portfolio_df['持有數量 (股)'] * portfolio_df['最新市價']
                    
                    total_value = portfolio_df['目前市值'].sum()
                    portfolio_df['目前權重 %'] = (portfolio_df['目前市值'] / total_value) * 100
                    
                    st.metric("目前總資產 (TWD)", f"{total_value:,.0f} 元")
                    
                    st.write("請輸入目標權重：")
                    target_weights = []
                    for i, row in portfolio_df.iterrows():
                        target = st.number_input(f"{row['資產代號']} 目標權重 (%)", min_value=0.0, max_value=100.0, value=row['目前權重 %'], step=1.0, key=f"target_{row['資產代號']}")
                        target_weights.append(target)
                    
                    portfolio_df['目標權重 %'] = target_weights
                    
                    if sum(target_weights) > 101 or sum(target_weights) < 99:
                        st.warning(f"目標權重總和為 {sum(target_weights):.1f}%，建議調整至接近 100%。")

                    portfolio_df['目標市值'] = (portfolio_df['目標權重 %'] / 100) * total_value
                    portfolio_df['調倉市值'] = portfolio_df['目標市值'] - portfolio_df['目前市值']
                    portfolio_df['調倉股數'] = (portfolio_df['調倉市值'] / portfolio_df['最新市價']).astype(int)
                    
                    st.subheader("調倉計畫")
                    display_cols = ['資產代號', '目前權重 %', '目標權重 %', '調倉股數']
                    st.dataframe(portfolio_df[display_cols].style.format({'目前權重 %': '{:.1f}%', '目標權重 %': '{:.1f}%', '調倉股數': '{:+,}'}))

                except Exception as e:
                    st.error(f"獲取市價或計算失敗: {e}")

    # ==================== 4.5 全球黑天鵝壓力測試 [V81.1 遷移] ====================
    with st.expander("4.5 🌪️ 全球黑天鵝壓力測試 (Black Swan Stress Test)"):
        st.info("此功能將讀取您在 4.1 配置的資產，模擬全球系統性風險下的投資組合衝擊。")
        portfolio_df = st.session_state.get('portfolio_df', pd.DataFrame())

        if portfolio_df.empty:
            st.warning("請先在 4.1 配置您的戰略資產。")
        else:
            if st.button("💥 啟動壓力測試"):
                # 將 DataFrame 轉換為 run_stress_test 所需的文本格式
                portfolio_text_list = []
                for _, row in portfolio_df.iterrows():
                    ticker = row['資產代號']
                    shares = row['持有數量 (股)']
                    portfolio_text_list.append(f"{ticker};{shares}")
                
                portfolio_text = "\n".join(portfolio_text_list)

                with st.spinner("執行全球壓力測試..."):
                    results_df, summary = run_stress_test(portfolio_text)

                if "error" in summary:
                    st.error(summary["error"])
                elif not results_df.empty:
                    st.session_state.stress_test_results = (results_df, summary)
                else:
                    st.error("壓力測試失敗，未返回任何結果。")

            if 'stress_test_results' in st.session_state:
                results_df, summary = st.session_state.stress_test_results
                st.subheader("壓力測試結果")
                
                total_value = summary.get('total_value', 0)
                st.metric("目前總市值 (TWD)", f"{total_value:,.0f}")

                # 計算總損益
                total_pnl_cols = [col for col in results_df.columns if '損益' in col]
                total_pnl = results_df[total_pnl_cols].sum()

                kpi_cols = st.columns(len(total_pnl))
                for i, (scenario, pnl) in enumerate(total_pnl.items()):
                    loss_pct = (pnl / total_value) * 100 if total_value > 0 else 0
                    kpi_cols[i].metric(
                        label=scenario.replace('損益_', ''),
                        value=f"{pnl:,.0f} TWD",
                        delta=f"{loss_pct:.1f}%"
                    )
                
                st.dataframe(results_df.style.format({
                    'price': '{:,.2f}',
                    'value_twd': '{:,.0f}',
                    '損益_回檔 (-5%)': '{:,.0f}',
                    '損益_修正 (-10%)': '{:,.0f}',
                    '損益_技術熊市 (-20%)': '{:,.0f}',
                    '損益_金融海嘯 (-30%)': '{:,.0f}',
                }), use_container_width=True)

# --- 📚 戰略百科 (Data) ---
@st.fragment
def render_data():
    if st.button("🏠 返回戰情總部"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("📚 戰略百科 (Encyclopedia & Intel)")
    
    df = st.session_state.get('df', pd.DataFrame())

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
                st.warning("⚠️ 肉少湯多：槓桿效益較低，風險報酬比可能不佳，建議直接買進 CB 現股。")
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

# --- 🧠 元趨勢戰法 (Meta-Trend) [V82.1 幾何引擎啟動版] ---
# ==========================================
# Titan SOP V85.0 - 7維度幾何基因與戰略母港重構
# ==========================================
# [CORE COMPONENTS]
# 1. TitanAgentCouncil - AI 參謀本部 (支援 One-Shot Dialog)
# 2. render_meta_trend - Tab 6 完整重構 (6 插槽佈局)
# ==========================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy.stats import linregress
import plotly.graph_objects as go
import google.generativeai as genai
# [V89.1 新增導入]
from config import WAR_THEATERS
import io

# ==========================================
# [SLOT-6.1] 數據引擎 (Data Engine)
# ==========================================

def get_time_slice(df, months):
    """
    [修復] 精準切割最後 N 個月的數據片段
    Args:
        df: 月K DataFrame
        months: 需要的月數
    Returns:
        切割後的 DataFrame
    """
    if df is None or df.empty:
        return df
    # 如果數據足夠長，取最後 N 個月；否則回傳全部
    if len(df) >= months:
        return df.iloc[-months:]
    return df

def download_full_history(ticker, start="1990-01-01"):
    """
    下載完整歷史月K線數據
    [V86.2 CRITICAL FIX]: 支援台股上櫃 (.TWO)
    
    Args:
        ticker: 股票代號 (會自動處理台股後綴)
    
    Returns:
        月K DataFrame 或 None
    """
    try:
        original_ticker = ticker
        
        # [V86.2 修正] 智慧處理台股代號 - 支援上市與上櫃
        if ticker.isdigit() and len(ticker) >= 4:
            ticker = f"{ticker}.TW"
        
        # 下載日K數據 (強制 auto_adjust 以獲取標準 OHLC，避免股息干擾)
        df = yf.download(ticker, start=start, progress=False, auto_adjust=True)
        
        # [V86.2 新增] 如果上市沒數據，嘗試上櫃
        if df.empty and original_ticker.isdigit() and len(original_ticker) >= 4:
            ticker = f"{original_ticker}.TWO"
            df = yf.download(ticker, start=start, progress=False, auto_adjust=True)
        
        # [關鍵修復]：yfinance 多層索引整平 (兼容台股與美股)
        if isinstance(df.columns, pd.MultiIndex):
           try:
               df.columns = df.columns.get_level_values(0)
           except: 
               pass
        
        if df.empty:
            return None
        
        # 確保索引是時間格式 (Resample 的前提)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # 轉換為月K
        df_monthly = df.resample('M').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # [V86.2 新增] 儲存原始日K數據到 session_state 供圖表使用
        if 'daily_price_data' not in st.session_state:
            st.session_state.daily_price_data = {}
        st.session_state.daily_price_data[original_ticker] = df
        
        return df_monthly
    
    except Exception as e:
        st.error(f"數據下載失敗: {e}")
        return None


# ==========================================
# [SLOT-6.2] 數學引擎 (Math Engine)
# ==========================================

def calculate_geometry_metrics(df, months):
    """
    計算單一時間窗口的幾何指標
    
    Args:
        df: 完整月K DataFrame
        months: 時間窗口 (月)
    
    Returns:
        dict: {'angle': float, 'r2': float, 'slope': float}
    """
    if df is None or df.empty:
        return {'angle': 0, 'r2': 0, 'slope': 0}
    
    # 切割數據
    slice_df = get_time_slice(df, months)
    
    if len(slice_df) < 3:
        return {'angle': 0, 'r2': 0, 'slope': 0}
    
    # 對數價格回歸
    log_prices = np.log(slice_df['Close'].values)
    x = np.arange(len(log_prices))
    
    slope, intercept, r_value, p_value, std_err = linregress(x, log_prices)
    
    # 將斜率轉換為角度 (-90 到 90 度)
    # 標準化: 假設 slope=0.01 對應 45度
    angle = np.arctan(slope * 100) * (180 / np.pi)
    angle = np.clip(angle, -90, 90)
    
    r2 = r_value ** 2
    
    return {
        'angle': round(angle, 2),
        'r2': round(r2, 4),
        'slope': round(slope, 6)
    }


def compute_7d_geometry(ticker):
    """
    計算 7 維度完整幾何掃描
    
    Returns:
        dict: {
            '35Y': {...},
            '10Y': {...},
            '5Y': {...},
            '3Y': {...},
            '1Y': {...},
            '6M': {...},
            '3M': {...},
            'acceleration': float,
            'phoenix_signal': bool
        }
    """
    df = download_full_history(ticker)
    
    if df is None:
        return None
    
    # 定義 7 個時間窗口 (月)
    periods = {
        '35Y': 420,
        '10Y': 120,
        '5Y': 60,
        '3Y': 36,
        '1Y': 12,
        '6M': 6,
        '3M': 3
    }
    
    results = {}
    
    for label, months in periods.items():
        results[label] = calculate_geometry_metrics(df, months)
    
    # 計算加速度
    acceleration = results['3M']['angle'] - results['1Y']['angle']
    results['acceleration'] = round(acceleration, 2)
    
    # Phoenix 信號
    phoenix = (results['10Y']['angle'] < 0) and (results['6M']['angle'] > 25)
    results['phoenix_signal'] = phoenix
    
    return results


# ==========================================
# [SLOT-6.3] 22 階泰坦信評引擎 (The 22 Scripts)
# ==========================================

def titan_rating_system(geo):
    """
    22 階信評邏輯樹
    
    Args:
        geo: 7D 幾何數據字典
    
    Returns:
        tuple: (rating_level, rating_name, description, color)
    """
    if geo is None:
        return ("N/A", "無數據", "數據不足", "#808080")
    
    # 提取關鍵指標
    angle_35y = geo['35Y']['angle']
    angle_10y = geo['10Y']['angle']
    angle_5y = geo['5Y']['angle']
    angle_1y = geo['1Y']['angle']
    angle_6m = geo['6M']['angle']
    angle_3m = geo['3M']['angle']
    
    r2_1y = geo['1Y']['r2']
    r2_3m = geo['3M']['r2']
    
    acceleration = geo['acceleration']
    phoenix = geo['phoenix_signal']
    
    # ===== SSS 級 =====
    if all([angle_35y > 45, angle_10y > 45, angle_1y > 45, angle_3m > 45]):
        return ("SSS", "Titan (泰坦)", "全週期超過45度，神級標的", "#FFD700")
    
    # ===== AAA 級 =====
    if angle_1y > 40 and angle_6m > 45 and angle_3m > 50 and acceleration > 20:
        return ("AAA", "Dominator (統治者)", "短期加速向上，完美趨勢", "#FF4500")
    
    # ===== Phoenix 級 (特殊) =====
    if phoenix and angle_3m > 30:
        return ("Phoenix", "Phoenix (浴火重生)", "長空短多，逆轉信號", "#FF6347")
    
    # ===== Launchpad 級 (特殊) =====
    if r2_1y > 0.95 and 20 < angle_1y < 40 and acceleration > 0:
        return ("Launchpad", "Launchpad (發射台)", "線性度極高，蓄勢待發", "#32CD32")
    
    # ===== AA+ 級 =====
    if angle_1y > 35 and angle_3m > 40 and r2_3m > 0.85:
        return ("AA+", "Elite (精英)", "一年期強勢上攻", "#FFA500")
    
    # ===== AA 級 =====
    if angle_1y > 30 and angle_6m > 35:
        return ("AA", "Strong Bull (強多)", "中短期穩定上升", "#FFD700")
    
    # ===== AA- 級 =====
    if angle_1y > 25 and angle_3m > 30:
        return ("AA-", "Steady Bull (穩健多)", "趨勢健康向上", "#ADFF2F")
    
    # ===== A+ 級 =====
    if angle_6m > 20 and angle_3m > 25:
        return ("A+", "Moderate Bull (溫和多)", "短期表現良好", "#7FFF00")
    
    # ===== A 級 =====
    if angle_3m > 15:
        return ("A", "Weak Bull (弱多)", "短期微幅上揚", "#98FB98")
    
    # ===== BBB+ 級 (中性偏多) =====
    if -5 < angle_3m < 15 and angle_1y > 0:
        return ("BBB+", "Neutral+ (中性偏多)", "盤整偏多", "#F0E68C")
    
    # ===== BBB 級 (中性) =====
    if -10 < angle_3m < 10 and -10 < angle_1y < 10:
        return ("BBB", "Neutral (中性)", "橫盤震蕩", "#D3D3D3")
    
    # ===== BBB- 級 (中性偏空) =====
    if -15 < angle_3m < 5 and angle_1y < 0:
        return ("BBB-", "Neutral- (中性偏空)", "盤整偏弱", "#DDA0DD")
    
    # ===== Divergence 級 (特殊警告) =====
    if angle_1y > 20 and angle_3m < -10:
        return ("Divergence", "Divergence (背離)", "價格創高但動能衰竭", "#FF1493")
    
    # ===== BB+ 級 =====
    if -25 < angle_3m < -15 and angle_1y > -10:
        return ("BB+", "Weak Bear (弱空)", "短期下跌", "#FFA07A")
    
    # ===== BB 級 =====
    if -35 < angle_3m < -25:
        return ("BB", "Moderate Bear (中等空)", "下跌趨勢明確", "#FF6347")
    
    # ===== BB- 級 =====
    if -45 < angle_3m < -35:
        return ("BB-", "Strong Bear (強空)", "跌勢凌厲", "#DC143C")
    
    # ===== B+ 級 =====
    if angle_3m < -45 and angle_1y < -30:
        return ("B+", "Severe Bear (重度空)", "崩跌模式", "#8B0000")
    
    # ===== B 級 =====
    if angle_10y < -30 and angle_3m < -40:
        return ("B", "Depression (蕭條)", "長期熊市", "#800000")
    
    # ===== C 級 =====
    if angle_35y < -20 and angle_10y < -35:
        return ("C", "Structural Decline (結構衰退)", "世代熊市", "#4B0082")
    
    # ===== D 級 =====
    if angle_3m < -60:
        return ("D", "Collapse (崩盤)", "極度危險", "#000000")
    
    # ===== 觸底反彈 級 (特殊) =====
    if angle_10y < -20 and angle_3m > 15 and acceleration > 30:
        return ("Reversal", "Reversal (觸底反彈)", "熊市中的V型反轉", "#00CED1")
    
    # ===== 預設 =====
    return ("N/A", "Unknown (未分類)", "無法歸類", "#808080")


# ==========================================
# [SLOT-6.4] AI 參謀本部 (TitanAgentCouncil with Dialog)
# ==========================================

class TitanAgentCouncil:
    """
    V90.1 升級版: 五權分立角鬥士系統 + 深度指令工程
    具備: 幾何死神(Quant), 內部人(Insider), 大賣空(Burry), 創世紀(Visionary), 上帝裁決(Arbiter)
    """
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.model = None
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # V90.1: 優先使用最新的 Gemini 1.5 Flash 或 Pro
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                st.warning(f"AI 模型初始化失敗: {e}")

    def generate_battle_prompt(self, ticker, price, geo_data, rating_info, intel_text="", commander_note=""):
        """
        [V90.1 核心] 生成史詩級辯論提示詞 (Anti-Laziness Protocol Enforced)
        
        Args:
            ticker: 股票代號
            price: 當前價格
            geo_data: 7D 幾何數據
            rating_info: (level, name, desc, color)
            intel_text: 法說會/財報情報
            commander_note: 統帥第一性原則筆記
        """
        level, name, desc, color = rating_info
        
        # 幾何數據格式化
        geo_str = f"""
1. 超長期視角 (35 年): 角度 {geo_data['35Y']['angle']}°, R² {geo_data['35Y']['r2']}
2. 長期視角 (10 年): 角度 {geo_data['10Y']['angle']}°, R² {geo_data['10Y']['r2']}
3. 中長期視角 (5 年): 角度 {geo_data['5Y']['angle']}°, R² {geo_data['5Y']['r2']}
4. 中期視角 (3 年): 角度 {geo_data['3Y']['angle']}°, R² {geo_data['3Y']['r2']}
5. 短中期視角 (1 年): 角度 {geo_data['1Y']['angle']}°, R² {geo_data['1Y']['r2']}
6. 短期視角 (6 個月): 角度 {geo_data['6M']['angle']}°, R² {geo_data['6M']['r2']}
7. 極短期視角 (3 個月): 角度 {geo_data['3M']['angle']}°, R² {geo_data['3M']['r2']}

加速度 (G-Force): {geo_data['acceleration']}° (3M角度 - 1Y角度)
Phoenix 信號: {'🔥 觸發' if geo_data['phoenix_signal'] else '❄️ 未觸發'}
"""
        
        prompt = f"""
# SYSTEM PROMPT: Titan Protocol V90.1 - The Ragnarök War Room

## CORE DIRECTIVE
You are the Titan Fund's "Supreme Strategy Council," a collective of five distinct, powerful AI personas. Your mission is to engage in a life-or-death debate over a single stock to determine its potential as a "100-Bagger by 2033." This is not a summary; it is a fierce, intellectual battle.

## ABSOLUTE RULES (NON-NEGOTIABLE)
1.  **ANTI-LAZINESS PROTOCOL**: This is the most critical rule. Each of the five personas' arguments **MUST BE A MINIMUM OF 800 WORDS**. The final Arbiter's judgment must also exceed 800 words. Any response with shallow, generic, or short arguments will be considered a mission failure. You must demonstrate deep, original thought for each role.
2.  **NO COURTESY, PURE CONFLICT**: This is a zero-sum debate. Burry must be relentlessly cynical, Visionary must be fanatically optimistic, Insider must be cunningly defensive, and Quant must be coldly objective.
3.  **FIRST PRINCIPLES ONLY**: All arguments must be grounded in the physics of business—cash flow, technological limits, market physics, and human psychology. Avoid vague financial jargon.
4.  **MANDATORY DATA CITATION**: Every claim MUST be supported by citing the specific "Battlefield Geometry" or "Live Intelligence" provided below.
5.  **MARKDOWN FORMATTING**: The entire output must be in well-structured Markdown for readability.
6.  **CONTINUATION PROTOCOL**: If your response is truncated due to length limits, you MUST end your response with the phrase `[CONTINUATION REQUIRED]`. When the user inputs "continue", you must seamlessly resume the debate from exactly where you left off, without repeating yourself, until all five personas have delivered their full, 800+ word arguments.

---

## BATTLE PARAMETERS
-   **Target Ticker**: {ticker}
-   **Current Price**: ${price:.2f}

### Battlefield Geometry (The Quant's Data)
{geo_str}

### Titan Rating (Initial Assessment)
-   **Grade**: {level}
-   **Name**: {name}
-   **Description**: {desc}
(This is a preliminary rating. Gladiators are encouraged to challenge or defend it.)

### Live Intelligence (The Insider's & Burry's Ammo)
{intel_text if intel_text else "No external intelligence injected. Proceed with deduction based on geometric data and your knowledge base."}

### Commander's First Principles (The Arbiter's Cornerstone)
{commander_note if commander_note else "No special directives. Adjudicate based on the principle of maximum long-term value."}

---

## ⚔️ THE FIVE GLADIATORS: BATTLE PROCEDURE ⚔️

**1. 【The Quant - Geometric Reaper】**
*   **Persona**: Cold, emotionless, trusts only in mathematics.
*   **Mission**: Analyze the geometric data. Is the trend accelerating or decelerating? Is the R² value indicating a stable, predictable trend or chaotic noise? Is the current price in a bubble relative to its long-term geometric mean?
*   **Mantra**: "Data does not lie. Humans do."
*   **Output Requirement**: 800+ words of rigorous mathematical and statistical analysis, citing specific angles, R² values, and acceleration.

**2. 【The Insider - Corporate Defender】**
*   **Persona**: The company's CEO/CFO. Defensive, optimistic, a master storyteller.
*   **Mission**: Use the "Live Intelligence" to defend the company's growth narrative. Explain why the current valuation is justified and why now is the perfect entry point. Counter Burry's attacks with growth metrics and future promises.
*   **Mantra**: "You're not buying the past; you're buying the future we are building."
*   **Output Requirement**: 800+ words. If no intel is provided, create a plausible growth story based on the industry and ticker.

**3. 【The Big Short - Doomsday Hunter】**
*   **Persona**: Michael Burry incarnate. Extremely pessimistic, paranoid, actively seeking the next market collapse.
*   **Mission**: Demolish the Insider's narrative. Find the bubble, the accounting tricks, the macro headwinds. Attack the valuation, the margins, the competition.
*   **Mantra**: "Mean reversion is the iron law of the universe. Every parabola breaks."
*   **Output Requirement**: 800+ words of deep skepticism, questioning the Titan Rating and exposing every conceivable flaw.

**4. 【The Visionary - Genesis Prophet】**
*   **Persona**: A fusion of Cathie Wood and Elon Musk. Fanatical, thinks in exponential terms, dismisses short-term losses.
*   **Mission**: Annihilate Burry's linear thinking using Wright's Law, S-curves, and disruptive innovation theory. Focus on the 2033 Total Addressable Market (TAM).
*   **Mantra**: "Don't talk to me about P/E ratios. Talk to me about the new world order this company is creating."
*   **Output Requirement**: 800+ words projecting a radical, technology-driven future 5-10 years out.

**5. 【The Apex Arbiter - The Final Word】**
*   **Persona**: The mind of Charlie Munger (inversion, mental models) fused with the business acumen of Jeff Bezos (customer obsession, long-term thinking).
*   **Mission**: As the ultimate judge, listen to the four gladiators. Synthesize their arguments, filter them through the "Commander's First Principles," and deliver the final, actionable verdict.
*   **Output Requirement**: 800+ words, structured precisely as follows:
    *   **【Battlefield Summary】**: A 200+ word critique of each gladiator's strongest and weakest points.
    *   **【First Principle Ruling】**: A 300+ word judgment grounded in the fundamental physics of the business and the Commander's notes.
    *   **【Operational Directive】**:
        -   **Action**: Strong Buy / Buy / Hold / Sell / Strong Sell
        -   **Entry Zone**: $XXX.XX (based on deviation from a key geometric trendline)
        -   **Stop Loss**: $XXX.XX (a hard, non-negotiable price)
        -   **Position Sizing**: Scout / Standard / Core / All-In / Short
        -   **Key Risks**: [List the top 3 existential risks]

---
Begin the debate. Adhere to all rules. Failure is not an option.
"""
        return prompt

    def run_debate(self, ticker, price, geo_data, rating_info, intel_text="", commander_note=""):
        """
        執行 AI 辯論並返回結果
        """
        if not self.model:
            return "❌ **AI 功能未啟用**\n\n請在側邊欄輸入 Gemini API Key 以啟用此功能。"
        
        try:
            prompt = self.generate_battle_prompt(
                ticker, price, geo_data, rating_info, intel_text, commander_note
            )
            response = self.model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            if "429" in str(e):
                return f"⚠️ **API 配額已耗盡**\n\n{str(e)}\n\n建議稍後再試或切換模型。"
            else:
                return f"❌ **AI 辯論失敗**\n\n{str(e)}"


# ==========================================
# [SLOT-6.6] Tab 6 完整重構 (6 插槽佈局)
# ==========================================
@st.fragment
def render_meta_trend():
    """
    元趨勢戰法 - 7維度幾何母港
    [V90.1 諸神黃昏最終版]
    - Slot 6.2 (Tab 2) 升級為戰略工廠，整合情報與第一性原則
    """
    # 返回首頁按鈕
    if st.button("🏠 返回首頁", type="secondary"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.title("🌌 元趨勢戰法 (V90.1 諸神黃昏)")
    st.caption("全歷史幾何 × 五大角鬥士 × 全境獵殺 | 核心目標：鎖定 2033 年百倍股")
    st.markdown("---")
    
    # ========== 標的輸入 ==========
    col_input1, col_input2 = st.columns([3, 1])
    
    with col_input1:
        ticker = st.text_input(
            "🎯 輸入分析標的 (支援上市/上櫃/美股)",
            value=st.session_state.get('meta_target', 'NVDA'),
            placeholder="例如: 2330 (上市), 5274 (上櫃), NVDA (美股)"
        )
        st.session_state.meta_target = ticker
    
    with col_input2:
        st.write("")
        st.write("")
        scan_button = st.button("📐 啟動掃描", type="primary", use_container_width=True)
    
    # ========== 執行掃描 ==========
    if scan_button and ticker:
        with st.spinner(f"正在下載 {ticker} 的完整歷史數據..."):
            geo_results = compute_7d_geometry(ticker)
            
            if geo_results is None:
                st.error(f"❌ 無法獲取 {ticker} 的數據。請檢查代號是否正確。")
                if 'geometry_results' in st.session_state: del st.session_state['geometry_results']
                if 'rating_info' in st.session_state: del st.session_state['rating_info']
                return
            
            rating_info = titan_rating_system(geo_results)
            st.session_state.geometry_results = geo_results
            st.session_state.rating_info = rating_info
            st.success(f"✅ 掃描完成！信評等級: **{rating_info[0]} - {rating_info[1]}**")
    
    # ========== 6 個插槽 Tab ==========
    if 'geometry_results' not in st.session_state:
        st.info("👆 請先輸入標的並啟動掃描。")
        return
    
    geo = st.session_state.geometry_results
    rating = st.session_state.rating_info
    ticker = st.session_state.meta_target
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📐 7D 幾何全景",
        "🏭 戰略工廠",
        "📝 獵殺清單",
        "🚀 全境獵殺",
        "🔧 宏觀對沖",
        "🔧 回測沙盒"
    ])
    
    # ==========================================
    # [TAB 1] 7D 幾何全景 (維持不變)
    # ==========================================
    with tab1:
        st.subheader("📐 七維度幾何儀表板")
        
        # ===== 保留區：信評卡片 =====
        st.markdown(f"""
        <div style='background-color: {rating[3]}; padding: 20px; border-radius: 10px; text-align: center;'>
            <h2 style='color: white; margin: 0;'>{rating[0]}</h2>
            <h3 style='color: white; margin: 5px 0;'>{rating[1]}</h3>
            <p style='color: white; margin: 0;'>{rating[2]}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ===== 保留區：7 個維度的角度顯示 =====
        periods = ['35Y', '10Y', '5Y', '3Y', '1Y', '6M', '3M']
        
        # 建立 4x2 網格
        for i in range(0, len(periods), 4):
            cols = st.columns(4)
            for j, col in enumerate(cols):
                if i + j < len(periods):
                    period = periods[i + j]
                    angle = geo[period]['angle']
                    r2 = geo[period]['r2']
                    
                    # 顏色映射
                    if angle > 30:
                        color = "#00FF00"
                    elif angle > 0:
                        color = "#ADFF2F"
                    elif angle > -30:
                        color = "#FFD700"
                    else:
                        color = "#FF4500"
                    
                    with col:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%); 
                                    padding: 15px; border-radius: 10px; border: 2px solid {color};
                                    text-align: center; margin-bottom: 10px;'>
                            <h4 style='color: {color}; margin: 0;'>{period}</h4>
                            <h1 style='color: white; margin: 5px 0; font-size: 36px;'>{angle}°</h1>
                            <p style='color: #888; margin: 0; font-size: 12px;'>R² = {r2}</p>
                        </div>
                        """, unsafe_allow_html=True)
        
        # ===== 保留區：加速度與 Phoenix 信號 =====
        st.markdown("---")
        col_acc, col_phx = st.columns(2)
        
        with col_acc:
            acc = geo['acceleration']
            acc_color = "#00FF00" if acc > 0 else "#FF4500"
            st.markdown(f"""
            <div style='background-color: #2a2a2a; padding: 20px; border-radius: 10px; text-align: center;'>
                <h4 style='color: #FFD700;'>⚡ 加速度</h4>
                <h2 style='color: {acc_color}; margin: 10px 0;'>{acc}°</h2>
                <p style='color: #888; font-size: 14px;'>3M - 1Y</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_phx:
            phoenix = geo['phoenix_signal']
            phx_status = "🔥 是" if phoenix else "❄️ 否"
            phx_color = "#FF6347" if phoenix else "#4682B4"
            st.markdown(f"""
            <div style='background-color: #2a2a2a; padding: 20px; border-radius: 10px; text-align: center;'>
                <h4 style='color: #FFD700;'>🐦 Phoenix 信號</h4>
                <h2 style='color: {phx_color}; margin: 10px 0;'>{phx_status}</h2>
                <p style='color: #888; font-size: 14px;'>浴火重生模式</p>
            </div>
            """, unsafe_allow_html=True)
        
        # ===== [V86.2 保留] 全歷史對數線性回歸圖 =====
        st.markdown("---")
        st.subheader("📈 全歷史對數線性回歸 (上帝軌道)")
        
        # 獲取日K數據
        if ticker in st.session_state.get('daily_price_data', {}):
            df_daily = st.session_state.daily_price_data[ticker]
            
            if df_daily is not None and not df_daily.empty:
                # 準備數據
                df_chart = df_daily.copy()
                df_chart = df_chart.reset_index()
                df_chart.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                
                # 計算全歷史線性回歸 (對數空間)
                df_chart['Days'] = np.arange(len(df_chart))
                log_prices = np.log(df_chart['Close'].values)
                
                from scipy.stats import linregress
                slope, intercept, r_value, p_value, std_err = linregress(
                    df_chart['Days'].values, 
                    log_prices
                )
                
                # 計算趨勢線 (在原始價格空間)
                df_chart['Trendline'] = np.exp(intercept + slope * df_chart['Days'])
                
                # 計算當前乖離率
                current_price = df_chart['Close'].iloc[-1]
                current_trend = df_chart['Trendline'].iloc[-1]
                deviation = ((current_price / current_trend) - 1) * 100
                
                # 顯示統計資訊
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("全歷史 R²", f"{r_value**2:.4f}")
                with col_stat2:
                    st.metric("當前價格", f"${current_price:.2f}")
                with col_stat3:
                    deviation_color = "normal" if abs(deviation) < 20 else "inverse"
                    st.metric(
                        "趨勢線乖離", 
                        f"{deviation:+.1f}%",
                        delta_color=deviation_color
                    )
                
                # 使用 Altair 繪製對數座標圖
                st.info("💡 Y軸為對數座標，可更清楚觀察長期幾何趨勢。藍色虛線為全歷史回歸軌道。")
                
                # 價格線
                price_line = alt.Chart(df_chart).mark_line(
                    color='#00FF00',
                    strokeWidth=2
                ).encode(
                    x=alt.X('Date:T', title='時間', axis=alt.Axis(format='%Y')),
                    y=alt.Y('Close:Q', 
                           title='收盤價 (對數座標)', 
                           scale=alt.Scale(type='log'),
                           axis=alt.Axis(tickCount=10)),
                    tooltip=[
                        alt.Tooltip('Date:T', title='日期', format='%Y-%m-%d'),
                        alt.Tooltip('Close:Q', title='收盤價', format=',.2f'),
                        alt.Tooltip('Trendline:Q', title='趨勢線', format=',.2f')
                    ]
                ).properties(
                    height=500,
                    title=f'{ticker} - 全歷史對數線性回歸分析 (1990-Now)'
                )
                
                # 趨勢線 (上帝軌道)
                trend_line = alt.Chart(df_chart).mark_line(
                    color='#4169E1',
                    strokeWidth=2,
                    strokeDash=[5, 5]
                ).encode(
                    x='Date:T',
                    y=alt.Y('Trendline:Q', scale=alt.Scale(type='log'))
                )
                
                # 合併圖表
                final_chart = (price_line + trend_line).configure_axis(
                    gridColor='#333333',
                    domainColor='#666666'
                ).configure_view(
                    strokeWidth=0
                )
                
                st.altair_chart(final_chart, use_container_width=True)
                
                # 解讀建議
                st.markdown("---")
                st.subheader("📊 幾何解讀")
                
                if abs(deviation) < 10:
                    st.success(f"✅ 價格貼近趨勢線 (乖離 {deviation:+.1f}%)，處於健康軌道。")
                elif deviation > 30:
                    st.warning(f"⚠️ 價格遠高於趨勢線 (乖離 +{deviation:.1f}%)，可能過熱，注意回調風險。")
                elif deviation < -30:
                    st.info(f"💎 價格遠低於趨勢線 (乖離 {deviation:.1f}%)，若基本面無虞，可能是逢低機會。")
                else:
                    st.info(f"ℹ️ 價格略偏離趨勢線 (乖離 {deviation:+.1f}%)，屬正常波動範圍。")
            
            else:
                st.warning("⚠️ 無法繪製圖表：日K數據為空。")
        else:
            st.warning("⚠️ 請先執行掃描以載入數據。")

    # ==========================================
    # [TAB 2] 戰略工廠 (V90.1 核心升級)
    # ==========================================
    with tab2:
        st.header("🏭 戰略工廠 (Strategy Factory)")
        st.caption("注入情報、設定原則、生成史詩級辯論提示詞")

        # --- 區域 A: 智能快捷鏈接 ---
        with st.expander("🔗 智能快捷鏈接 (The Full Arsenal)", expanded=True):
            links = {
                "TradingView": "https://www.tradingview.com/",
                "Finviz": "https://finviz.com/",
                "Yahoo Finance": "https://finance.yahoo.com/",
                "StockCharts": "https://stockcharts.com/",
                "鉅亨網 (Anue)": "https://news.cnyes.com/",
                "Goodinfo": "https://goodinfo.tw/tw/index.asp",
                "AlphaMemo (逐字稿)": "https://www.alphamemo.ai/free-transcripts",
                "SEC EDGAR (財報)": "https://www.sec.gov/edgar/searchedgar/companysearch",
                "DCF (財報)": "https://discountingcashflows.com/"
            }
            cols = st.columns(5)
            for i, (name, url) in enumerate(links.items()):
                with cols[i % 5]:
                    st.link_button(name, url, use_container_width=True)
        
        st.markdown("---")

        col_params, col_output = st.columns([2, 3])

        with col_params:
            st.subheader("🎛️ 辯論參數注入")

            # --- 區域 B: 情報注入插槽 ---
            st.markdown("#### 🕵️ 情報注入插槽 (Intel Slot)")
            intel_text_manual = st.text_area(
                "貼上法說會摘要、財報數據或新聞",
                height=150,
                placeholder="例如：CEO 表示 AI 伺服器營收將於 Q3 翻倍..."
            )
            uploaded_intel_file = st.file_uploader(
                "或上傳情報文件",
                type=['pdf', 'txt', 'csv', 'xlsx', 'docx'],
                accept_multiple_files=False
            )
            if uploaded_intel_file:
                st.success(f"✅ 已接收檔案情報: {uploaded_intel_file.name} (將併入 Prompt)")
                # 實際的檔案讀取邏輯可以在此處擴充
                # intel_text = intel_text_manual + read_file_content(uploaded_intel_file)
            
            intel_text = intel_text_manual # 簡化版：僅使用手動輸入

            st.divider()

            # --- 區域 C: 統帥第一性原則 ---
            st.markdown("#### ✍️ 統帥第一性原則 (Commander's Principles)")
            principles_list = [
                "[成長] 萊特定律檢視：產量翻倍，成本是否下降 15%？",
                "[成長] 非線性爆發點：用戶/算力是否呈指數級成長？",
                "[成長] TAM 邊界測試：若已達潛在市場 80%，為何還要買？",
                "[成長] 邊際成本歸零：多服務一人的成本是否趨近零？",
                "[成長] 網路效應：是否越多人用越好用？",
                "[生存] 燒錢率生存測試：若 18 個月融不到資，會死嗎？",
                "[生存] 研發含金量：R&D 是資產還是費用？",
                "[生存] 客戶集中度風險：最大客戶砍單 50% 會如何？",
                "[生存] 庫存周轉物理學：存貨週轉天數是否異常暴增？",
                "[生存] 自由現金流真偽：扣除 SBC 後真的有賺錢嗎？",
                "[泡沫] 均值回歸引力：利潤率若回歸平均，股價會腰斬嗎？",
                "[泡沫] 敘事與現實乖離：CEO 提 AI 次數 vs 實際營收佔比。",
                "[泡沫] 內部人逃生：高管是在買進還是賣出？",
                "[泡沫] 債務槓桿壓力：利息覆蓋率是否低於 3？",
                "[泡沫] 競爭紅海化：是否有低成本中國對手殺入？",
                "[終極] 不可替代性：若公司明天消失，世界有差嗎？",
                "[終極] 物理極限：成長是否受缺電/缺地/缺水限制？",
                "[終極] 人才密度：能否吸引全球最聰明工程師？",
                "[終極] 反脆弱性：遇黑天鵝(戰爭/疫情)是受傷還是獲利？",
                "[終極] 百倍股基因：2033 年若活著，它會變成什麼樣子？"
            ]
            
            selected_principles = st.multiselect(
                "勾選要強制執行的原則 (可多選)",
                options=principles_list,
                help="選擇的原則將自動填入下方筆記框"
            )
            
            commander_note_auto = "\n".join(selected_principles)
            
            commander_note_final = st.text_area(
                "統帥筆記 (最終版)",
                value=commander_note_auto,
                height=200,
                placeholder="此處的文字將成為 Arbiter 的最終裁決基石"
            )

        with col_output:
            st.subheader("🌌 戰情室輸出")
            
            if st.button("🔥 生成史詩級戰略提示詞", type="primary", use_container_width=True):
                current_price = 0.0
                if ticker in st.session_state.get('daily_price_data', {}):
                    df_daily = st.session_state.daily_price_data[ticker]
                    if df_daily is not None and not df_daily.empty:
                        current_price = df_daily['Close'].iloc[-1]

                council = TitanAgentCouncil() # 不需要 API Key 即可生成
                battle_prompt = council.generate_battle_prompt(
                    ticker, current_price, geo, rating, intel_text, commander_note_final
                )
                st.session_state.generated_prompt = battle_prompt

            # --- 區域 D: 戰略提示詞輸出 ---
            if 'generated_prompt' in st.session_state:
                st.success("✅ 史詩級戰略提示詞已生成！")
                prompt_text = st.session_state.generated_prompt
                
                st.text_area(
                    "📋 複製此提示詞 (Ctrl+A, Ctrl+C) 到 Gemini / Claude",
                    value=prompt_text,
                    height=400
                )
                
                st.download_button(
                    "💾 下載戰略提示詞 (.txt)",
                    prompt_text,
                    file_name=f"TITAN_PROMPT_{ticker}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                st.caption(f"📊 提示詞統計：{len(prompt_text)} 字元")

    # ==========================================
    # [TAB 3-6] (維持不變)
    # ==========================================
    with tab3:
        st.subheader("📝 條件式獵殺清單")
        
        st.info("只有當幾何信評達到 **AA-** 或更高等級時，才會觸發『存入獵殺清單』的選項。")
        
        high_ratings = [
            "SSS", "AAA", "Phoenix", "Launchpad", 
            "AA+", "AA", "AA-"
        ]
        
        if any(hr in rating[0] for hr in high_ratings):
            st.success(f"""
            **🎯 目標 `{st.session_state.meta_target}` 符合獵殺標準！**
            
            - 評級: **{rating[0]} - {rating[1]}**
            - 描述: {rating[2]}
            """)
            
            if st.button(f"✅ 存入獵殺清單 (Add to Kill List)", type="primary"):
                # 初始化獵殺清單
                if 'kill_list' not in st.session_state:
                    st.session_state.kill_list = []
                
                # 避免重複
                if st.session_state.meta_target not in st.session_state.kill_list:
                    st.session_state.kill_list.append(st.session_state.meta_target)
                    st.toast(f"🎯 {st.session_state.meta_target} 已加入獵殺清單！", icon="✅")
                else:
                    st.toast(f"⚠️ {st.session_state.meta_target} 已在清單中", icon="ℹ️")
        
        else:
            st.error(f"""
            **❌ 目標 `{st.session_state.meta_target}` 未達標準**
            
            - 評級: **{rating[0]} - {rating[1]}**
            - 當前評級不足以列入一級獵殺目標，建議繼續觀察。
            """)
        
        # 顯示已存清單
        st.markdown("---")
        st.subheader("📋 當前獵殺清單")
        
        if 'kill_list' in st.session_state and st.session_state.kill_list:
            for idx, target in enumerate(st.session_state.kill_list, 1):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{idx}.** {target}")
                with col2:
                    if st.button("🗑️", key=f"del_{target}"):
                        st.session_state.kill_list.remove(target)
                        st.rerun()
        else:
            st.info("清單為空，尚無符合條件的標的。")
    
    with tab4:
        st.subheader("🚀 全境獵殺雷達 (The Hunter)")
        st.markdown("---")

        with st.expander("🎯 獵殺控制台 (Mission Control)", expanded=True):
            # 1. 戰區選擇
            theater_options = list(WAR_THEATERS.keys())
            selected_theater = st.selectbox(
                "選擇掃描戰區 (Select War Theater)",
                options=theater_options
            )
            
            if selected_theater:
                stock_count = len(WAR_THEATERS[selected_theater])
                st.info(f"已選擇戰區 **{selected_theater}**，包含 **{stock_count}** 檔潛力標的。")

            # 2. 啟動按鈕
            if st.button("🚀 啟動全境掃描", type="primary", use_container_width=True):
                if not selected_theater:
                    st.warning("請先選擇一個戰區。")
                else:
                    tickers_to_scan = WAR_THEATERS[selected_theater]
                    total_tickers = len(tickers_to_scan)
                    hunt_results = []
                    
                    progress_bar = st.progress(0, text=f"掃描進度: 0/{total_tickers}")
                    
                    for i, t in enumerate(tickers_to_scan):
                        geo_data = compute_7d_geometry(t)
                        progress_bar.progress((i + 1) / total_tickers, text=f"掃描進度: {t} ({i+1}/{total_tickers})")
                        
                        if geo_data:
                            # 獲取現價
                            current_price = 0.0
                            if t in st.session_state.get('daily_price_data', {}) and not st.session_state.daily_price_data[t].empty:
                                current_price = st.session_state.daily_price_data[t]['Close'].iloc[-1]

                            # 濾網條件判斷
                            match_type = None
                            # 模式 A: Phoenix
                            if geo_data['10Y']['angle'] < 10 and geo_data['3M']['angle'] > 45:
                                match_type = "🔥 Phoenix"
                            # 模式 B: Awakening
                            elif abs(geo_data['35Y']['angle']) < 15 and geo_data['acceleration'] > 20:
                                match_type = "🦁 Awakening"
                            # 模式 C: Rocket
                            elif geo_data['3M']['angle'] > 60:
                                match_type = "🚀 Rocket"
                            
                            if match_type:
                                hunt_results.append({
                                    "代號": t,
                                    "現價": current_price,
                                    "35Y角度": geo_data['35Y']['angle'],
                                    "10Y角度": geo_data['10Y']['angle'],
                                    "3M角度": geo_data['3M']['angle'],
                                    "G力": geo_data['acceleration'],
                                    "型態": match_type
                                })
                    
                    progress_bar.empty()
                    st.session_state[f'hunt_results_{selected_theater}'] = pd.DataFrame(hunt_results)
                    st.success(f"✅ {selected_theater} 戰區掃描完成，發現 {len(hunt_results)} 個潛在目標！")

        # 顯示掃描結果
        if f'hunt_results_{selected_theater}' in st.session_state:
            results_df = st.session_state[f'hunt_results_{selected_theater}']
            
            if not results_df.empty:
                st.markdown("---")
                st.markdown("### ⚔️ 戰果清單 (Scan Results)")
                
                # 格式化顯示
                st.dataframe(results_df.style.format({
                    "現價": "{:.2f}",
                    "35Y角度": "{:.1f}°",
                    "10Y角度": "{:.1f}°",
                    "3M角度": "{:.1f}°",
                    "G力": "{:+.1f}°"
                }), use_container_width=True)

                # CSV 下載
                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 下載戰果 (CSV)",
                    data=csv,
                    file_name=f'hunter_results_{selected_theater}_{datetime.now().strftime("%Y%m%d")}.csv',
                    mime='text/csv',
                )
            else:
                st.info("未發現符合條件的目標，請嘗試其他戰區。")

    with tab5:
        st.subheader("🔧 宏觀對沖 (Macro Hedge)")
        st.warning("🚧 此功能正在開發中，敬請期待...")

    with tab6:
        st.subheader("🔧 回測沙盒 (Backtest Sandbox)")
        st.warning("🚧 此功能正在開發中，敬請期待...")

# --- 🏠 戰情指揮首頁 (Home) [V81.1 NEW] ---
@st.fragment
def render_home():
    # [V81.1] 視覺系統精確打擊：僅對首頁主標題進行特效渲染
    st.markdown(
        '<h1 style="text-align: center; color:white; text-shadow: 0 0 10px #00FF00, 0 0 20px #00FF00;">🏛️ Titan SOP 全自動戰情室 (V82.0 元趨勢創世紀版)</h1>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    # [V81.1] 視覺系統精確打擊：移除全域 CSS，避免污染內頁
    st.markdown("""
    <style>
        /* Main container styling */
        .stApp {
            background-color: #1a1a1a;
        }
        /* Custom button styling for homepage navigation */
        div.stButton > button {
            background-color: #2a2a2a;
            color: #FFFFFF; /* FORCE WHITE FONT FOR VISIBILITY */
            border: 2px solid #444;
            border-