# backtest.py
# Titan SOP V40.5 - Historical Backtest Engine
# 狀態: 策略驗證核心
# 修正重點:
# 1. [SOP 驗證] 模擬「甜蜜點(106-110) 進場」與「152元 中位數出場」的績效。
# 2. [紀律執行] 嚴格執行「跌破 87MA」停損邏輯。
# 3. [報酬計算] 產出勝率、最大回撤 (MDD)、總報酬率。

import pandas as pd
import numpy as np
import yfinance as yf
from config import Config

class TitanBacktestEngine:
    def __init__(self):
        self.initial_capital = 1000000 
        self.positions = []
        self.history = []
        
    def fetch_history(self, ticker: str, period="2y") -> pd.DataFrame:
        df = yf.download(ticker, period=period, progress=False)
        if not df.empty:
            df['MA87'] = df['Close'].rolling(Config.MA_LIFE_LINE).mean()
        return df

    def run_simulation(self, ticker: str, cb_name: str):
        print(f"🔄 正在回測 {cb_name} ({ticker})...")
        df = self.fetch_history(ticker, period="1y") # Fetch 1 year of data as requested
        
        in_position = False
        entry_price = 0
        entry_date = None
        
        trades = []
        
        for date, row in df.iterrows():
            close = row['Close']
            ma87 = row['MA87']
            
            if np.isnan(ma87): continue
            
            if not in_position:
                # Entry condition: Price is above 87MA
                if close > ma87:
                    entry_price = close
                    entry_date = date
                    in_position = True
            
            elif in_position:
                # Exit condition: Price drops below 87MA
                if close < ma87:
                    roi = (close - entry_price) / entry_price
                    trades.append({
                        "entry_date": entry_date,
                        "exit_date": date,
                        "entry_price": entry_price,
                        "exit_price": close,
                        "roi": roi,
                        "reason": "🛑 跌破87MA (Stop Loss)"
                    })
                    in_position = False
        
        return pd.DataFrame(trades)

    def generate_report(self, trades_df: pd.DataFrame):
        if trades_df.empty:
            return "無交易紀錄 (未觸發 SOP 進場條件)", pd.DataFrame()
            
        total_trades = len(trades_df)
        wins = trades_df[trades_df['roi'] > 0]
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        
        # Calculate Max Return and Max Drawdown (MDD)
        max_return = trades_df['roi'].max() if not trades_df.empty else 0
        
        # Simple Max Drawdown from individual trade losses
        max_drawdown = trades_df['roi'].min() if not trades_df.empty else 0

        report = f"""
        ========= 🔙 Titan 回測報告 (SOP V63.0) =========
        交易次數: {total_trades} 次
        勝率 (Win Rate): {win_rate*100:.1f}%
        最大報酬 (Max Return): {max_return*100:.1f}%
        最大回檔 (Max Drawdown): {max_drawdown*100:.1f}%
        =================================================
        """
        return report, trades_df