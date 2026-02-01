# execution.py
# Titan SOP V40.5 - Execution & Calendar Agent
# 狀態: 時間套利執行引擎 (計算所有關鍵日期)
# 修正重點:
# 1. [完整收錄] 實作四大時間套利邏輯 (IPO, 甦醒, 避稅, 行事曆)。
# 2. [沈睡甦醒] 新增上市滿一年的「第二波攻擊日」計算。
# 3. [行事曆事件] 自動計算當年度的融券回補與除權息旺季。

import pandas as pd
from datetime import datetime, timedelta
from config import Config
from typing import List, Dict

class CalendarAgent:
    
    def _get_current_year_events(self) -> List[Dict]:
        """計算當年度的固定行事曆事件 (融券/除權息)"""
        events = []
        current_year = datetime.now().year
        
        short_cover_start = datetime(current_year, Config.EVENT_SHORT_COVER_MONTHS[0], 1)
        events.append({
            "date": short_cover_start.strftime('%Y-%m-%d'),
            "event": "📅 融券回補旺季 (Short Cover)",
            "desc": "每年3-4月，空單強制回補，易有軋空行情 (Event-Driven)。",
            "type": "Calendar"
        })
        
        dividend_start = datetime(current_year, Config.EVENT_DIVIDEND_MONTHS[0], 1)
        events.append({
            "date": dividend_start.strftime('%Y-%m-%d'),
            "event": "📅 除權息降轉旺季 (Anti-Dilution)",
            "desc": "每年6-8月，除權息後轉換價調降，有利可轉債價格提升。",
            "type": "Calendar"
        })
        
        return events

    def calculate_time_traps(self, stock_code: str, listing_date_str: str, put_date_str: str) -> List[Dict]:
        """
        計算該檔 CB 的所有時間套利陷阱
        """
        events = []
        fmt = '%Y-%m-%d'
        
        try:
            l_date = pd.to_datetime(listing_date_str, errors='coerce')
            p_date = pd.to_datetime(put_date_str, errors='coerce')
            if pd.isna(l_date) or pd.isna(p_date):
                return []
        except:
            return [] 
            
        honeymoon_end = l_date + timedelta(days=Config.LISTING_HONEYMOON_DAYS)
        events.append({
            "date": honeymoon_end.strftime(fmt),
            "event": "🔔 蜜月期滿 (Listing+90)",
            "desc": "上市滿3個月(敲鑼打鼓期)，留意解禁後的賣壓或主力拉抬方向。",
            "type": "IPO"
        })
        
        awakening_date = l_date + timedelta(days=Config.LISTING_DORMANT_DAYS)
        events.append({
            "date": awakening_date.strftime(fmt),
            "event": "⏰ 沈睡甦醒 (Listing+365)",
            "desc": "鄭思翰法則：新債若首季未動，滿一週年常有「甦醒行情」。",
            "type": "Awakening"
        })
        
        tax_rally_start = p_date - timedelta(days=Config.PUT_AVOID_TAX_DAYS)
        events.append({
            "date": tax_rally_start.strftime(fmt),
            "event": "🚀 避稅行情啟動 (Put-180)",
            "desc": "進入賣回日前半年。若股價低於轉換價，公司派易拉抬以避免債券持有人執行賣回。",
            "type": "PutBack"
        })
        
        events.append({
            "date": p_date.strftime(fmt),
            "event": "⚠️ 賣回基準日 (Put Date)",
            "desc": "投資人可選擇以保本價賣回給公司的日子。此日前股價若未拉過轉換價，需提防違約風險。",
            "type": "Risk"
        })
        
        calendar_evts = self._get_current_year_events()
        events.extend(calendar_evts)
        
        events.sort(key=lambda x: x['date'])
        
        return events