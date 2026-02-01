# app.py
# Titan SOP V78.2 - The War Room UI (Final Audit Package)
# [V78.2 Patch]: 
# 1. Upgraded version to 78.2. 
# 2. Unified Window 15/16 UI with correct column order and color styling.
# 3. Locked interaction logic to prevent re-downloading data.
# 4. Corrected all deduction labels to "87MA扣抵預判".

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

@st.cache_data
def get_macro_data(_macro, _df):
    """快取宏觀風控數據"""
    return _macro.check_market_status(cb_df=_df)

@st.cache_data(ttl=600)
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

            rename_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if "代號" in col and "標的" not in col: rename_map[col] = 'code'
                elif "名稱" in col or "標的債券" in col: rename_map[col] = 'name'
                elif any(k in col_lower for k in ["市價", "收盤", "close", "成交"]): rename_map[col] = 'close'
                elif any(k in col_lower for k in ["標的", "stock_code"]): rename_map[col] = 'stock_code'
                elif "發行" in col: rename_map[col] = 'list_date'
                elif "賣回" in col: rename_map[col] = 'put_date'
                elif any(k in col for k in ["轉換價", "轉換價格", "最新轉換價"]): rename_map[col] = 'conversion_price'
                elif any(k in col for k in ["已轉換比例", "轉換比例", "轉換率"]): rename_map[col] = 'converted_ratio'
                elif any(k in col for k in ["發行餘額", "流通餘額"]): rename_map[col] = 'outstanding_balance'
                elif "發行總額" in col: rename_map[col] = 'issue_amount'
                elif any(k in col_lower for k in ["均量", "成交量", "avg_vol"]): rename_map[col] = 'avg_volume'

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

# --- Window 1: 宏觀風控 ---
st.header("1️⃣ 宏觀風控 (Macro Risk)")
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
st.divider()

# --- Window 2: 高價權值股多空溫度計 ---
st.header("2️⃣ 高價權值股多空溫度計")
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
st.divider()

# --- Window 3: 情報獵殺分析結果 ---
st.header("3️⃣ 情報獵殺分析結果")
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
st.divider()

# --- Window 4: PR90 籌碼分佈圖 ---
st.header("4️⃣ PR90 籌碼分佈圖")
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
st.divider()

# --- Window 5: CBAS 槓桿試算儀 ---
st.header("5️⃣ CBAS 槓桿試算儀")
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
st.divider()

# --- Window 6: 族群熱度雷達 ---
st.header("6️⃣ 族群熱度雷達 (Sector Heatmap)")
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
st.divider()


# --- Window 7: SOP 戰略百科 ---
st.header("7️⃣ SOP 戰略百科 (SOP Strategy Encyclopedia)")
with st.expander("點此展開，查核系統內建的完整 SOP 規則庫"):
    if 'all_rules' not in st.session_state:
        st.session_state.all_rules = kb.get_all_rules_for_ui()
    
    all_rules = st.session_state.all_rules

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["**四大時間套利**", "**進出場紀律**", "**產業族群庫**", "**特殊心法**", "**OTC神奇均線**"])

    with tab1:
        st.subheader("SOP 時間套利總覽")
        if all_rules.get("time_arbitrage"):
            for rule in all_rules["time_arbitrage"]:
                st.markdown(f"- {rule}")
        else:
            st.warning("無法載入時間套利規則。")

    with tab2:
        st.subheader("SOP 進出場規則原文 (摘錄)")
        entry_exit_rules = all_rules.get("entry_exit", {})
        st.text_area("進場條件 (Entry)", value=entry_exit_rules.get('entry', '無紀錄'), height=300)
        st.text_area("出場條件 (Exit)", value=entry_exit_rules.get('exit', '無紀錄'), height=300)
    
    with tab3:
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

    with tab4:
        st.subheader("隱藏心法與特殊策略")
        special_tactics = all_rules.get("special_tactics", [])
        if special_tactics:
            st.text_area("Tactics & Mindset", value="\n\n---\n\n".join(special_tactics), height=500)
        else:
            st.warning("無法載入特殊心法。")

    with tab5:
        st.subheader("OTC 神奇均線法則 (OTC Magic MA Rules)")
        otc_rules = kb.get_otc_magic_rules()
        for rule_name, rule_desc in otc_rules.items():
            st.markdown(f"**{rule_name.replace('_', ' ').title()}**: {rule_desc}")

st.divider()

# --- Window 8: 自動獵殺推薦 ---
st.header("8️⃣ 自動獵殺推薦 (Auto Sniper)")
if not df.empty:
    if st.button("🚀 啟動 SOP 核心策略掃描"):
        with st.spinner("執行全市場掃描..."):
            scan_results = get_scan_result(strategy, df)
            st.session_state['scan_results'] = scan_results
    
    if 'scan_results' in st.session_state:
        scan_results = st.session_state['scan_results']
        buy_recommendations = scan_results[scan_results['action'].str.contains('買進', na=False)]
        
        if not buy_recommendations.empty:
            results_to_show = buy_recommendations.head(20)
            st.success(f"掃描完成！發現 {len(buy_recommendations)} 筆黃金標的，顯示前 {len(results_to_show)} 名。")
            for _, r in results_to_show.iterrows():
                expander_title = f"{r['action']} - {r['name']} ({r['code']}) | CB價: {r.get('price', 0):.2f} | 評分: {int(r.get('score', 0))}"
                with st.expander(expander_title):
                    st.markdown(r.get('full_report', '報告生成失敗。'), unsafe_allow_html=True)
        else:
            st.warning("⚠️ 全市場暫無符合『神奇均線中期多頭 + 115元以下』之黃金標的，建議空手觀察。")
else:
    st.info("請上傳 CB 清單以啟動自動獵殺掃描。")
st.divider()

# --- Window 9: 全市場 Top 20 深度稽核 ---
st.header("9️⃣ 全市場 Top 20 深度稽核 (Logic Audit)")
if 'scan_results' in st.session_state:
    scan_results = st.session_state['scan_results']
    if not scan_results.empty:
        top_20_all = scan_results.head(20)
        st.info("此區塊顯示全市場評分最高的前 20 檔標的，無論其最終操作建議為何，旨在供您檢視系統的評分 logique。")
        
        for i, r in top_20_all.iterrows():
            rank = top_20_all.index.get_loc(i) + 1
            expander_title = (
                f"🏆 Rank {rank} | {r['name']} ({r['code']}) | "
                f"分數: {int(r.get('score', 0))} | "
                f"狀態: {r['action']} | "
                f"CB價: {r.get('price', 0):.2f}"
            )
            with st.expander(expander_title):
                st.markdown(r.get('full_report', '報告生成失敗。'), unsafe_allow_html=True)
    else:
        st.warning("請先點擊 Window 8 的掃描按鈕以生成評分數據。")
else:
    st.info("請先點擊 Window 8 的掃描按鈕以生成評分數據。")
st.divider()

# --- Window 10: 資金配置試算 ---
st.header("🔟 資金配置試算 (Position Sizing)")
if 'scan_results' in st.session_state and not df.empty:
    total_capital = st.number_input("輸入您的總操作資金 (元)", min_value=100000, value=2000000, step=100000)
    
    buy_recommendations = st.session_state['scan_results'][st.session_state['scan_results']['action'].str.contains('買進', na=False)]

    if not buy_recommendations.empty:
        st.subheader("建議投資組合")
        portfolio_list = []
        for _, row in buy_recommendations.head(5).iterrows():
            cb_price = row.get('price', 0)
            if cb_price > 0:
                investment_per_stock = total_capital * 0.20
                num_shares = investment_per_stock / (cb_price * 1000)
                
                portfolio_list.append(
                    f"- **建議買進 {row['name']} ({row['code']})**: "
                    f"`{int(num_shares)}` 張 (佔比約 `20%`)"
                )
        st.markdown("\n".join(portfolio_list))
    else:
        st.info("目前無強力買進標的，無需進行資金配置。")
else:
    st.info("請先執行 Window 8 的掃描以獲取買進建議。")
st.divider()

# --- Window 11: 時間套利行事曆 ---
st.header("1️⃣1️⃣ 時間套利行事曆 (Event Calendar)")
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

# --- Window 12: 歷史回測驗證 ---
st.header("1️⃣2️⃣ 歷史回測驗證 (Strategy Backtest)")
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
        st.warning("請先點擊 Window 8 的掃描按鈕以生成推薦標的。")
else:
    st.info("請先點擊 Window 8 的掃描按鈕以生成推薦標的。")
st.divider()

# --- Window 13: 潛在風險雷達 ---
st.header("1️⃣3️⃣ 潛在風險雷達 (Risk Radar)")
if 'scan_results' in st.session_state and not df.empty:
    scan_results = st.session_state['scan_results']
    st.info("此區塊為「負面表列」清單，旨在警示符合特定風險條件的標的，提醒您「避開誰」。")

    required_risk_cols = ['converted_ratio', 'premium', 'avg_volume']
    if all(col in scan_results.columns for col in required_risk_cols):
        
        tab1, tab2, tab3 = st.tabs(["**☠️ 籌碼鬆動 (主力落跑)**", "**⚠️ 高溢價 (肉少湯喝)**", "**🧊 流動性陷阱 (殭屍債)**"])

        with tab1:
            abandoned_df = scan_results[scan_results['converted_ratio'] > 30].sort_values('converted_ratio', ascending=False)
            if not abandoned_df.empty:
                st.warning(f"發現 {len(abandoned_df)} 檔標的「已轉換比例」 > 30%，特定人可能已在下車。")
                st.dataframe(abandoned_df[['name', 'code', 'converted_ratio', 'price', 'action']].head(20).fillna(''))
            else:
                st.success("✅ 目前無標的觸發「籌碼鬆動」警示。")

        with tab2:
            overpriced_df = scan_results[scan_results['premium'] > 20].sort_values('premium', ascending=False)
            if not overpriced_df.empty:
                st.warning(f"發現 {len(overpriced_df)} 檔標的「溢價率」 > 20%，潛在報酬空間可能受壓縮。")
                st.dataframe(overpriced_df[['name', 'code', 'premium', 'price', 'parity']].head(20).fillna(0))
            else:
                st.success("✅ 目前無標的觸發「高溢價」警示。")

        with tab3:
            illiquid_df = scan_results[scan_results['avg_volume'] < 10].sort_values('avg_volume', ascending=True)
            if not illiquid_df.empty:
                st.error(f"發現 {len(illiquid_df)} 檔標的平均成交量 < 10 張，存在嚴峻的流動性風險！")
                st.dataframe(illiquid_df[['name', 'code', 'avg_volume', 'price']].head(20).fillna(0))
            else:
                st.success("✅ 目前無標的觸發「流動性陷阱」警示。")
    else:
        st.error("掃描結果缺少風險分析所需欄位 (converted_ratio, premium, avg_volume)，請檢查上傳的 Excel 檔案。")
else:
    st.info("請先執行 Window 8 的掃描以啟動風險雷達。")
st.divider()

# --- Window 14: 高階趨勢預測 (扣抵與亞當) ---
st.header("1️⃣4️⃣ 高階趨勢預測 (扣抵與亞當)")
if not df.empty:
    stock_options = [f"{row['name']} ({row['stock_code']})" for index, row in df.iterrows()]
    selected_stock_str = st.selectbox("選擇一檔標的進行高階分析", options=stock_options)

    if selected_stock_str:
        stock_code = re.search(r'\((\d+)\)', selected_stock_str).group(1)
        ticker = f"{stock_code}.TW"
        
        with st.spinner(f"正在為 {selected_stock_str} 進行高階技術分析..."):
            stock_df = macro.get_single_stock_data(ticker, period="2y")

            if stock_df.empty or len(stock_df) < Config.MA_LIFE_LINE:
                st.warning("資料不足，無法進行高階趨勢預測。")
            else:
                deduction_df = macro.calculate_ma_deduction_forecast(stock_df, ma_period=Config.MA_LIFE_LINE, forecast_days=60)
                adam_df = macro.calculate_adam_projection(stock_df, lookback_days=20)
                
                current_price = stock_df['Close'].iloc[-1]
                ma87 = stock_df['Close'].rolling(Config.MA_LIFE_LINE).mean().iloc[-1]
                
                try:
                    if isinstance(ma87, (pd.Series, pd.DataFrame)): ma87 = float(ma87.iloc[-1])
                    if isinstance(current_price, (pd.Series, pd.DataFrame)): current_price = float(current_price.iloc[-1])
                    bias_percent = ((current_price - ma87) / ma87) * 100 if ma87 > 0 else 0
                except Exception: bias_percent = 0

                is_recent_breakout = (current_price > ma87) and (stock_df['Close'].iloc[-5] < ma87)
                
                try:
                    if isinstance(ma87, (pd.Series, pd.DataFrame)): ma87 = float(ma87.iloc[-1])
                    if isinstance(current_price, (pd.Series, pd.DataFrame)): current_price = float(current_price.iloc[-1])
                    if isinstance(is_recent_breakout, (pd.Series, pd.DataFrame)): is_recent_breakout = bool(is_recent_breakout.iloc[-1]) 
                except Exception: is_recent_breakout = False
        
                granville_status = strategy._get_granville_status(current_price, ma87, is_recent_breakout, bias_percent)

                col1, col2, col3 = st.columns(3)
                col1.metric("目前股價", f"{current_price:.2f}")
                col2.metric("格蘭碧法則狀態", granville_status)
                col3.metric("SOP 統計目標價", f"{Config.EXIT_TARGET_MEDIAN} 元")

                tab1, tab2 = st.tabs(["**87MA 扣抵值預測**", "**亞當理論二次反射**"])

                with tab1:
                    if not deduction_df.empty:
                        st.info("扣抵值是計算移動平均線時，將被移除的歷史股價。若未來扣抵值高於現價，均線將承受壓力；反之則有助漲效果。")
                        chart_data = deduction_df.reset_index()
                        chart_data['Current_Price'] = current_price
                        base = alt.Chart(chart_data).encode(x='Date:T')
                        line_deduction = base.mark_line(color='orange', strokeDash=[5,5]).encode(y=alt.Y('Deduction_Value', title='Price'), tooltip=['Date', 'Deduction_Value']).properties(title="未來60日 87MA 扣抵值預測")
                        line_current = base.mark_line(color='blue').encode(y='Current_Price')
                        st.altair_chart((line_deduction + line_current).interactive(), use_container_width=True)
                    else:
                        st.warning("歷史資料不足，無法預測均線扣抵值。")

                with tab2:
                    if not adam_df.empty:
                        st.info("亞當理論二次反射，是將最近一段時間的價格走勢路徑，從目前的時間點重新『鏡像』播放一次，以預測未來可能的路徑。")
                        hist_df = stock_df.iloc[-60:].reset_index(); hist_df['Type'] = '歷史路徑'
                        proj_df = adam_df.reset_index(); proj_df['Type'] = '亞當投影'; proj_df.rename(columns={'Projected_Price': 'Close', 'Date': 'Date'}, inplace=True)
                        chart_data = pd.concat([hist_df[['Date', 'Close', 'Type']], proj_df[['Date', 'Close', 'Type']]])
                        chart = alt.Chart(chart_data).mark_line().encode(x='Date:T', y=alt.Y('Close', title='Price', scale=alt.Scale(zero=False)), color='Type:N', strokeDash='Type:N').properties(title="亞當理論二次反射路徑圖").interactive()
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.warning("歷史資料不足，無法進行亞當理論投影。")
                
                with st.expander("📖 點此查看相關理論說明 (摘錄自 SOP 資料庫)"):
                    theory_texts = kb.get_advanced_theory_text()
                    st.subheader("均線扣抵 (MA Deduction)"); st.markdown(theory_texts['deduction'])
                    st.divider()
                    st.subheader("亞當理論 (Adam Theory)"); st.markdown(theory_texts['adam_theory'])
else:
    st.info("請上傳 CB 清單以啟動高階趨勢預測功能。")
st.divider()

# --- [V78.2 REVISED] Window 15 & 16: 雙雷達趨勢掃描 ---
def render_leader_dashboard(window_title: str, session_state_key: str, fetch_function, top_n: int, sort_key_name: str):
    st.header(window_title)
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

# --- Window 15: 成交重心即時預測 (動態 Top 100) ---
render_leader_dashboard(
    window_title="1️⃣5️⃣ 成交重心即時預測 (動態 Top 100)",
    session_state_key="w15_data",
    fetch_function=macro.get_dynamic_turnover_leaders,
    top_n=100,
    sort_key_name="成交值"
)
st.divider()

# --- Window 16: 高價權值股趨勢雷達 (Top 50) ---
render_leader_dashboard(
    window_title="1️⃣6️⃣ 高價權值股趨勢雷達 (Top 50)",
    session_state_key="w16_data",
    fetch_function=macro.get_high_price_leaders,
    top_n=50,
    sort_key_name="股價"
)
st.divider()
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

# ==========================================
# Window 17: 萬用個股狙擊雷達 (Universal Sniper)
# [V79.5 Final Protocol]: No Swap, Unlocked Params, Wave UI
# ==========================================
st.divider()
st.header("1️⃣7️⃣ 萬用個股狙擊雷達 (Universal Sniper)")
st.info("🌍 全球戰情模式：支援台股 (2330)、美股 (TSLA, PLTR)、加密貨幣。")

w17_in = st.text_input("輸入代號或股名", value="2330", key="w17_final_v99").strip()

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
            if not temp.empty and len(temp) >= 60: sdf = temp; v_ticker = c; break
    if sdf.empty: st.error("❌ 查無數據。")
    else:
        # Data Clean
        try:
            if isinstance(sdf.columns, pd.MultiIndex): sdf.columns = sdf.columns.get_level_values(0)
            sdf.columns = [str(c).strip().capitalize() for c in sdf.columns]
            sdf = sdf.reset_index()
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
            
            # [Fix] Syntax corrected
            for req in ['Open', 'High', 'Low']:
                if req not in sdf.columns: sdf[req] = sdf['Close']
                
            if 'Volume' not in sdf.columns: sdf['Volume'] = 0
        except Exception as e: st.error(f"資料格式錯誤: {e}"); st.stop()

        # Indicators
        sdf['MA87'] = sdf['Close'].rolling(87).mean(); sdf['MA284'] = sdf['Close'].rolling(284).mean()
        sdf['Prev_MA87'] = sdf['MA87'].shift(1); sdf['Prev_MA284'] = sdf['MA284'].shift(1)
        sdf['Cross_Signal'] = 0
        sdf.loc[(sdf['Prev_MA87'] <= sdf['Prev_MA284']) & (sdf['MA87'] > sdf['MA284']), 'Cross_Signal'] = 1
        sdf.loc[(sdf['Prev_MA87'] >= sdf['Prev_MA284']) & (sdf['MA87'] < sdf['MA284']), 'Cross_Signal'] = -1

        cp = float(sdf['Close'].iloc[-1]); op = float(sdf['Open'].iloc[-1])
        m87 = float(sdf['MA87'].iloc[-1]) if not pd.isna(sdf['MA87'].iloc[-1]) else 0
        m87_prev5 = float(sdf['MA87'].iloc[-6]) if len(sdf) > 6 and not pd.isna(sdf['MA87'].iloc[-6]) else m87
        m284 = float(sdf['MA284'].iloc[-1]) if not pd.isna(sdf['MA284'].iloc[-1]) else 0

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

        st.subheader(f"🎯 {v_ticker} 戰情報告")
        r1_c1, r1_c2 = st.columns(2)
        r1_c1.metric("目前股價", f"{cp:.2f}")
        r1_c2.metric("生命線 87MA", f"{m87:.2f}")
        r2_c1, r2_c2 = st.columns(2)
        r2_c1.metric("趨勢狀態", trend_status_str, f"持續 {trend_days} 天")
        r2_c2.metric("格蘭碧法則", granville_title, f"乖離 {bias:.1f}%", help=granville_desc)
        st.markdown("---")

        t1, t2, t3, t4, t5, t6, t7 = st.tabs([
            "**📊 87MA 扣抵**", "**🔮 亞當理論**", "**🕯️ 日 K (含交叉)**", 
            "**🗓️ 月 K 線**", "**🧠 ARK 戰情室**", "**💎 智能估值**", "**🌊 5波模擬**"
        ])
        
        with t1: # 扣抵
            ddf = macro.calculate_ma_deduction_forecast(sdf, 87, 60)
            if not ddf.empty:
                cd = ddf.reset_index(); cd['Cur'] = cp
                base = alt.Chart(cd).encode(x='Date:T')
                l1 = base.mark_line(color='orange', strokeDash=[5,5]).encode(y=alt.Y('Deduction_Value', title='Price'))
                l2 = base.mark_line(color='blue').encode(y='Cur')
                st.altair_chart((l1 + l2).interactive(), use_container_width=True)
            else: st.warning("資料不足。")

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
                u_growth = s1.slider("成長率", -10.0, 50.0, safe_g_s, 0.01)
                u_margin = s2.slider("淨利率", -5.0, 5.0, float(def_m), 0.01)
                u_pe = s3.slider("終端 PE", 0.0, 9999.0, float(def_pe), 1.0)
                
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

# ==========================================
# Window 18: 台指期月K結算目標價推導 (Settlement Radar)
# ==========================================
st.divider()
st.header("1️⃣8️⃣ 台指期月K結算目標價推導 (Settlement Radar)")
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