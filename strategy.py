# strategy.py
# Titan SOP V71.0 - Core Strategy Engine (Audited)
# [V71.0 Audit]: No logic changes required. _get_granville_status will be called by the new Window 14 UI. Version bumped.

import pandas as pd
import numpy as np
import yfinance as yf
from config import Config
from knowledge_base import TitanKnowledgeBase
from execution import CalendarAgent
from datetime import datetime, timedelta

class TitanStrategyEngine:
    def __init__(self):
        self.kb = TitanKnowledgeBase()
        self.calendar = CalendarAgent()

    def _get_granville_status(self, price, ma87, is_recent_breakout, bias_percent):
        """格蘭碧八大法則狀態判讀"""
        if is_recent_breakout:
            return "🔥 突破生命線 (買1)"
        if -20 < bias_percent < 0:
            return "🟢 回測支撐 (買2)"
        if bias_percent < -20:
            return "🟢 乖離過大 (買4 - 假摔)"
        if bias_percent > 20:
            return "🔴 乖離過大 (賣4 - 過熱)"
        return "👍 趨勢健康 (持有)"

    def _generate_single_report(self, row) -> str:
        """[V64.0] 為單一列生成符合四大天條的詳細報告，並增加風險監控、決策輔助及SOP原文引用"""
        name, code, price = row.get('name', 'N/A'), row.get('code', 'N/A'), row.get('price', 0)
        score, action, ma87 = row.get('score', 0), row.get('action', 'N/A'), row.get('MA87', 0)
        ma284, stock_price = row.get('MA284', 0), row.get('stock_price', 0)
        role_info, story = row.get('role', {}), row.get('story', '')
        stock_code = row.get('stock_code', 'N/A')
        
        avg_volume = row.get('avg_volume', 100) 
        liquidity_warning = ""
        if avg_volume < 10:
            liquidity_warning = "**<font color='red'>⚠️ 殭屍債 (流動性風險)</font>**"

        bias_percent = ((stock_price - ma87) / ma87) * 100 if ma87 > 0 else 0
        granville_status = self._get_granville_status(stock_price, ma87, row.get('is_recent_breakout', False), bias_percent)

        report = f"### 🎯 **{name} ({code})**\n\n"
        
        if liquidity_warning:
            report += f"{liquidity_warning}\n\n"
            
        report += f"**綜合評分**: {int(score)} | **操作建議**: {action}\n\n"
        report += f"#### 核心策略檢核 (The 4 Commandments):\n"
        
        reasons = []
        price_ok = price < Config.FILTER_MAX_PRICE
        ma_ok = (stock_price > ma87 > ma284 > 0)
        role_ok = role_info.get('role') in ["👑 領頭羊 (Leader)", "🔥 風口豬 (Laggard)"]
        story_keywords_found = [k for k in Config.STORY_KEYWORDS if k in story]
        story_ok = bool(story_keywords_found)

        reasons.append(f"1.  **價格 < 115 元**: {'✅' if price_ok else '❌'} 目前 CB 市價 **{price:.2f}** 元。")
        reasons.append(f"2.  **中期多頭排列**: {'✅' if ma_ok else '❌'} 股價({stock_price:.2f}) > 87MA({ma87:.2f}) > 284MA({ma284:.2f})。")
        role_text = role_info.get('role', 'N/A')
        reasons.append(f"3.  **身份認證**: {'✅' if role_ok else '❌'} 符合 **{role_text}** 定義。")
        if story_ok:
            reasons.append(f"4.  **發債故事**: ✅ 命中關鍵字: `{', '.join(story_keywords_found)}`。")
        else:
             reasons.append(f"4.  **發債故事**: {'✅ (綜合題材)' if action != '-' else '❌ (無直接命中)'}")

        report += "\n".join(reasons) + "\n"

        # --- [V64.0] 新增決策輔助區塊 ---
        report += "\n#### 🛡️ 決策輔助 (Decision Support):\n"
        support_reasons = []
        premium = row.get('premium', 0)
        converted_ratio = row.get('converted_ratio', 0)
        parity = row.get('parity', 0)

        support_reasons.append(f"- **理論價 (Parity)**: {parity:.2f}")
        if premium > 20:
            support_reasons.append(f"- **<font color='orange'>⚠️ 高溢價 (肉少湯喝)</font>**: **{premium:.1f}%**，潛在報酬空間受壓縮。")
        else:
            support_reasons.append(f"- **溢價率 (Premium)**: {premium:.1f}%")
        
        if converted_ratio > 30:
            support_reasons.append(f"- **<font color='red'>☠️ 籌碼鬆動 (主力下車)</font>**: 已轉換 **{converted_ratio:.1f}%**，超過 30% 警戒線。")
        else:
            support_reasons.append(f"- **已轉換比例**: {converted_ratio:.1f}%")
        report += "\n".join(support_reasons) + "\n"


        report += "\n#### 加分項與時間套利:\n"
        bonus_reasons = []
        bonus_reasons.append(f"- **格蘭碧狀態**: {granville_status}")
        
        events = row.get('events', [])
        has_time_arbitrage = False
        if events:
            future_events = [e for e in events if pd.to_datetime(e['date']).date() > datetime.now().date()]
            for event in future_events[:2]:
                if "蜜月期" in event['event']:
                     bonus_reasons.append(f"- **新債蜜月期**: {event['date']} ({event['event']}) `(SOP 原則: 新債敲鑼打鼓，最易發動)`")
                     has_time_arbitrage = True
                if "避稅" in event['event']:
                     bonus_reasons.append(f"- **避稅行情**: {event['date']} ({event['event']}) `(SOP 原則: 賣回日前半年，拉抬動機強)`")
                     has_time_arbitrage = True
        
        if not has_time_arbitrage:
             bonus_reasons.append("- 暫無觸發主要時間套利。")
        
        report += "\n".join(bonus_reasons) + "\n"

        report += "\n#### 交易計畫 (Trading Plan):\n"
        report += f"- **目標價**: 中期目標可參考歷史統計高點 **{Config.EXIT_TARGET_MEDIAN}** 元。\n"
        report += f"- **停損點**: 若標的股票 **收盤價有效跌破 87MA 生命線** 則考慮分批停損。\n"

        report += "\n#### 出場/風險監控 (Exit & Risk Monitoring):\n"
        risk_reasons = []
        if not row.get('is_making_high', True):
            risk_reasons.append(" - **⚠️ 動能趨緩**: 股價近 3 日未再創高，請留意追高風險。")
        
        ma_diff = ma87 - ma284
        if ma_diff < 0:
            risk_reasons.append(f" - **☠️ 正式進入空頭**: 87MA 已死亡交叉 284MA (差距 {ma_diff:.2f})。")
        elif ma_diff < stock_price * 0.05 and stock_price > 0:
            risk_reasons.append(f" - **⚠️ 均線收斂**: 87MA 與 284MA 差距縮小 (差距 {ma_diff:.2f})，留意趨勢反轉可能。")

        if not risk_reasons:
            risk_reasons.append("- **✅ 動能健康**: 目前技術指標未出現明顯空頭警訊。")
        
        report += "\n".join(risk_reasons) + "\n"
        
        yahoo_link = f"https://tw.stock.yahoo.com/quote/{stock_code}.TW/technical-analysis"
        report += f"\n[📊 **點此查看 K 線 (Yahoo Finance)**]({yahoo_link})\n"

        return report

    def _batch_enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        work_df = df.copy()
        stock_codes = work_df['stock_code'].dropna().unique()
        tickers = [f"{code}.TW" for code in stock_codes]
        
        tech_data = {}
        if not tickers:
            for col in ['stock_price', 'MA87', 'MA284', 'is_recent_breakout', 'is_making_high']:
                work_df[col] = 0 if 'price' in col or 'MA' in col else False
            return work_df

        data = yf.download(tickers, period="2y", group_by='ticker', progress=False, threads=True)
        
        for ticker in tickers:
            stock_code = ticker.split('.')[0]
            try:
                stock_df = data[ticker] if len(tickers) > 1 else data
                if not stock_df.empty and len(stock_df) >= Config.MA_LONG_TERM:
                    close = stock_df['Close']
                    high = stock_df['High']
                    ma87 = close.rolling(Config.MA_LIFE_LINE).mean().iloc[-1]
                    ma284 = close.rolling(Config.MA_LONG_TERM).mean().iloc[-1]
                    
                    is_recent_breakout = (close.iloc[-1] > ma87) and (close.iloc[-5] < ma87)
                    is_making_high = close.iloc[-1] >= high.iloc[-3:].max()

                    if not np.isnan(ma87) and not np.isnan(ma284):
                        tech_data[stock_code] = {
                            "stock_price": close.iloc[-1], 
                            "MA87": ma87, 
                            "MA284": ma284,
                            "is_recent_breakout": is_recent_breakout,
                            "is_making_high": is_making_high
                        }
            except (KeyError, IndexError):
                continue
        
        tech_df = pd.DataFrame.from_dict(tech_data, orient='index').reset_index().rename(columns={'index': 'stock_code'})
        work_df = work_df.merge(tech_df, on='stock_code', how='left')
        
        for col in ['stock_price', 'MA87', 'MA284', 'is_recent_breakout', 'is_making_high']:
            if col not in work_df.columns: 
                work_df[col] = 0 if 'MA' in col or 'price' in col else False
            else: 
                work_df[col].fillna(0 if 'MA' in col or 'price' in col else False, inplace=True)
                
        return work_df

    def _calculate_risk_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """[V64.0] 向量化計算理論價、溢價率、轉換率"""
        work_df = df.copy()

        # --- 確保數值格式 ---
        num_cols = ['stock_price', 'conversion_price', 'price', 'outstanding_balance', 'issue_amount']
        for col in num_cols:
            if col in work_df.columns:
                work_df[col] = pd.to_numeric(work_df[col], errors='coerce')
        
        # --- 理論價 (Parity) ---
        work_df['parity'] = 0.0
        if 'conversion_price' in work_df.columns:
            safe_div_mask = work_df['conversion_price'] > 0
            work_df.loc[safe_div_mask, 'parity'] = (work_df.loc[safe_div_mask, 'stock_price'] / work_df.loc[safe_div_mask, 'conversion_price']) * 100

        # --- 溢價率 (Premium) ---
        work_df['premium'] = 0.0
        if 'parity' in work_df.columns:
            safe_premium_mask = work_df['parity'] > 0
            work_df.loc[safe_premium_mask, 'premium'] = ((work_df.loc[safe_premium_mask, 'price'] - work_df.loc[safe_premium_mask, 'parity']) / work_df.loc[safe_premium_mask, 'parity']) * 100

        # --- 已轉換比例 (Converted Ratio) ---
        if 'converted_ratio' not in work_df.columns or work_df['converted_ratio'].isnull().all():
            work_df['converted_ratio'] = 0.0
            if 'outstanding_balance' in work_df.columns and 'issue_amount' in work_df.columns:
                safe_ratio_mask = work_df['issue_amount'] > 0
                work_df.loc[safe_ratio_mask, 'converted_ratio'] = (1 - (work_df.loc[safe_ratio_mask, 'outstanding_balance'] / work_df.loc[safe_ratio_mask, 'issue_amount'])) * 100
        
        # 填補可能計算失敗的 NaN
        work_df[['parity', 'premium', 'converted_ratio']] = work_df[['parity', 'premium', 'converted_ratio']].fillna(0)
        work_df['converted_ratio'] = work_df['converted_ratio'].clip(0, 100) # 確保比例在 0-100 之間

        return work_df

    def scan_entire_portfolio(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or 'code' not in df.columns or 'name' not in df.columns or 'stock_code' not in df.columns:
            return pd.DataFrame()

        # --- 確保數值與基礎資料 ---
        work_df = df.copy()
        work_df['avg_volume'] = pd.to_numeric(work_df.get('avg_volume', 0), errors='coerce').fillna(0)
        work_df['price'] = pd.to_numeric(work_df['close'], errors='coerce').fillna(0)
        
        # --- 1. 技術指標 & 風險指標計算 ---
        work_df = self._batch_enrich_data(work_df)
        work_df = self._calculate_risk_metrics(work_df)

        # --- 2. 全市場賦予質化資訊 ---
        work_df['role'] = work_df.apply(lambda row: self.kb.analyze_sector_role(str(row['name']), str(row['code']), "Auto", row['price'], []), axis=1)
        work_df['story'] = work_df['stock_code'].apply(lambda x: self.kb.get_story(str(x)))
        work_df['events'] = work_df.apply(lambda row: self.calendar.calculate_time_traps(str(row['code']), str(row.get('list_date', '')), str(row.get('put_date', ''))), axis=1)

        # --- 3. 全市場評分 ---
        work_df['score'] = 0
        
        # 條件檢核
        price_ok = work_df['price'] < Config.FILTER_MAX_PRICE
        magic_ma_ok = (work_df['stock_price'] > work_df['MA87']) & (work_df['MA87'] > work_df['MA284']) & (work_df['MA284'] > 0)
        identity_ok = work_df['role'].apply(lambda x: x.get('role') in ["👑 領頭羊 (Leader)", "🔥 風口豬 (Laggard)"])
        story_regex = '|'.join(Config.STORY_KEYWORDS)
        story_ok = work_df['story'].str.contains(story_regex, case=False, na=False)
        
        # 核心四大天條計分
        work_df['score'] += np.where(price_ok, 20, 0)
        work_df['score'] += np.where(magic_ma_ok, 40, 0)
        work_df['score'] += np.where(identity_ok, 10, 0)
        work_df['score'] += np.where(story_ok, 10, 0)
        
        # 加分項
        work_df['score'] += np.where(work_df['is_recent_breakout'], 5, 0)
        
        now = datetime.now()
        def check_events(events):
            is_honeymoon = any("蜜月期" in e['event'] and pd.to_datetime(e['date']).date() >= now.date() for e in events)
            is_put_rally = any("避稅" in e['event'] and pd.to_datetime(e['date']).date() >= now.date() for e in events)
            return is_honeymoon, is_put_rally

        event_scores = work_df['events'].apply(check_events)
        work_df['score'] += np.where(event_scores.apply(lambda x: x[0]), 5, 0)
        work_df['score'] += np.where(event_scores.apply(lambda x: x[1]), 5, 0)

        # [V64.0] 風險扣分項
        work_df['score'] -= np.where(work_df['premium'] > 20, 10, 0)
        work_df['score'] -= np.where(work_df['converted_ratio'] > 30, 20, 0)
        work_df['score'] -= np.where(work_df['avg_volume'] < 10, 15, 0)

        work_df['score'] = work_df['score'].clip(0, 100)

        # --- 4. 根據分數與核心條件決定操作建議 ---
        action_conditions = [
            (price_ok & magic_ma_ok & (work_df['score'] >= 80)),
            (price_ok & magic_ma_ok & (work_df['score'] >= 60))
        ]
        action_choices = ['🔥 強力買進', '✅ 買進/觀察']
        work_df['action'] = np.select(action_conditions, action_choices, default='-')
        
        # --- 5. 生成報告並回傳完整結果 ---
        results_df = work_df.sort_values(by='score', ascending=False).reset_index(drop=True)
        results_df['full_report'] = results_df.apply(self._generate_single_report, axis=1)
        
        # 確保所有需要的欄位都存在
        final_cols = list(df.columns) + [
            'price', 'stock_price', 'score', 'action', 'full_report', 
            'parity', 'premium', 'converted_ratio', 'avg_volume'
        ]
        # 去除重複欄位
        final_cols = list(dict.fromkeys(final_cols))
        
        return results_df.reindex(columns=final_cols).fillna({'full_report': '報告生成失敗'})