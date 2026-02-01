# knowledge_base.py
# Titan SOP V71.0 - Knowledge Base (Audited)
# 狀態: 核心大腦 (存放所有策略定義與邏輯)
# [V71.0 Audit]: Added get_advanced_theory_text() to extract specific theoretical texts for the new Window 14. No other changes needed.

import json
import os
import re
from typing import Dict, List, Set, Tuple

class TitanKnowledgeBase:
    def __init__(self, db_path='full_sop_database.json'):
        self.db_path = db_path
        self.config = None # 延後載入 Config
        
        # --- 動態資料結構 ---
        self.sector_bellwether_map: Dict[str, Set[str]] = {}
        self.bellwethers: Set[str] = set()
        self.stock_stories: Dict[str, str] = {}
        self.full_strategy_text = {"entry": "", "exit": "", "cbas": "", "time": ""}
        self.time_arbitrage_events = []
        
        # --- [V62.0 ADDITION] ---
        self.hidden_strategies: Set[str] = set()
        self.general_issuance_stories: Set[str] = set()

        self._load_database()

    def _load_database(self):
        """解析 JSON 資料庫，完整提取所有欄位，絕不閹割"""
        if not os.path.exists(self.db_path):
            print(f"⚠️ 警告: 找不到 {self.db_path}")
            return

        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for entry in data:
                try:
                    # 處理巢狀 JSON 字串
                    raw = entry.get('analysis')
                    content = json.loads(raw) if isinstance(raw, str) else raw
                    
                    # --- A. 提取族群與領頭羊 (建立關聯) ---
                    ind = content.get('industry_and_story', {})
                    sectors = []
                    
                    if ind and ind.get('issuance_story'):
                        self.general_issuance_stories.add(ind.get('issuance_story').strip())
                        
                    if 'wind_pig_sector' in ind and ind['wind_pig_sector']:
                        raw_sectors = [s.strip().replace('風口豬', '').replace('產業', '') for s in ind['wind_pig_sector'].split(',')]
                        sectors.extend(raw_sectors)
                    
                    if 'bellwether_stock' in ind and ind['bellwether_stock']:
                        story = ind.get('issuance_story', '無記載')
                        raw_stocks = ind['bellwether_stock'].split(',')
                        
                        for s in raw_stocks:
                            clean_name = re.split(r'[(\d]', s)[0].strip()
                            clean_code = re.search(r'\d{4}', s)
                            code_str = clean_code.group() if clean_code else ""
                            
                            keys_to_add = []
                            if code_str: keys_to_add.append(code_str)
                            if clean_name: keys_to_add.append(clean_name)
                            
                            for key in keys_to_add:
                                self.bellwethers.add(key)
                                self.stock_stories[key] = story
                                for sector in sectors:
                                    if sector not in self.sector_bellwether_map:
                                        self.sector_bellwether_map[sector] = set()
                                    self.sector_bellwether_map[sector].add(key)

                    # --- B. 提取量化規則 (Quantitative Rules) ---
                    quant = content.get('quantitative_rules', {})
                    if quant and quant.get('entry'):
                        self.full_strategy_text['entry'] += quant.get('entry', '') + "\n\n"
                    if quant and quant.get('exit'):
                        self.full_strategy_text['exit'] += quant.get('exit', '') + "\n\n"

                    # --- C. 提取時間套利 (含 Calendar) ---
                    time_arb = content.get('time_arbitrage_rules', {})
                    if time_arb:
                        if time_arb.get('three_month'):
                            self.full_strategy_text['time'] += f"三個月規則: {time_arb.get('three_month')}\n"
                        if time_arb.get('one_year'):
                            self.full_strategy_text['time'] += f"一年規則: {time_arb.get('one_year')}\n"
                        
                        calendar_events = time_arb.get('calendar', [])
                        if calendar_events:
                            self.time_arbitrage_events.extend(calendar_events)

                    # --- [V62.0 ADDITION] D. 提取隱藏心法 ---
                    other = content.get('other_hidden_strategies', [])
                    if isinstance(other, list):
                        for item in other:
                            if isinstance(item, str):
                                self.hidden_strategies.add(item.strip())
                            elif isinstance(item, dict) and 'name' in item:
                                strat_text = f"**{item.get('name', '策略')}**:\n"
                                details = item.get('details', '')
                                if isinstance(details, list):
                                    strat_text += "\n".join([f"- {d}" for d in details if isinstance(d, str)])
                                elif isinstance(details, str):
                                    strat_text += f"- {details}"
                                self.hidden_strategies.add(strat_text)
                                
                except Exception:
                    continue
        except Exception as e:
            print(f"KB Error: {e}")

    def get_all_rules_for_ui(self) -> Dict:
        """[V62.0] 提取所有規則，用於 UI 百科全書"""
        return {
            "time_arbitrage": self.get_time_arbitrage_rules(),
            "entry_exit": {
                'entry': self.full_strategy_text['entry'].strip(),
                'exit': self.full_strategy_text['exit'].strip(),
                'time': self.full_strategy_text['time'].strip()
            },
            "industry_story": {
                "sector_map": self.sector_bellwether_map,
                "general_issuance_stories": sorted(list(self.general_issuance_stories))
            },
            "special_tactics": sorted(list(self.hidden_strategies))
        }

    def get_advanced_theory_text(self) -> Dict[str, str]:
        """[V71.0] 提取高階理論的文字描述"""
        adam_theory_texts = []
        deduction_texts = []
        for strategy in self.hidden_strategies:
            if "亞當理論" in strategy:
                adam_theory_texts.append(strategy)
            if "扣抵值" in strategy:
                deduction_texts.append(strategy)
        
        return {
            "adam_theory": "\n\n---\n\n".join(adam_theory_texts) or "未在資料庫中找到亞當理論的相關描述。",
            "deduction": "\n\n---\n\n".join(deduction_texts) or "未在資料庫中找到均線扣抵的相關描述。"
        }

    def is_bellwether(self, name_or_code: str) -> bool:
        """判斷是否為領頭羊 (核心邏輯)"""
        for b in self.bellwethers:
            if b in name_or_code: return True
        return False

    def analyze_sector_role(self, name: str, code: str, sector: str, my_price: float, sector_prices: List[float]) -> Dict:
        is_leader = self.is_bellwether(name) or self.is_bellwether(code)
        
        if is_leader:
            return {
                "role": "👑 領頭羊 (Leader)",
                "strategy": "強勢主攻 (Momentum)",
                "msg": "族群指標股。動力最強，若回測 87MA 或位於甜蜜點，為首選標的。"
            }
        
        if not sector_prices:
            return {"role": "❓ 未知", "strategy": "觀察", "msg": "無同族群參考數據"}
            
        leader_price_max = max(sector_prices)
        
        if my_price < leader_price_max * 0.8:
            return {
                "role": "🔥 風口豬 (Laggard)",
                "strategy": "落後補漲 (Value)",
                "msg": f"具比價效應 (現價 {my_price} < 領頭羊 {leader_price_max})，適合低接。"
            }
            
        return {
            "role": "😐 跟隨者",
            "strategy": "中性",
            "msg": "非領頭羊且價格優勢不明顯。"
        }

    def get_otc_magic_rules(self) -> Dict[str, str]:
        return {
            "bull_cycle": "🔥 中期多頭：OTC指數站上 87MA 生命線，且 87MA 黃金交叉 284MA (平均漲2年)。",
            "bear_cycle": "❄️ 中期空頭：OTC指數跌破 87MA 生命線，且 87MA 死亡交叉 284MA (平均跌1年)。",
            "granville_buy": "📈 格蘭碧買點：回測 87MA 支撐 (買2) 或 負乖離過大 (買4)。",
            "granville_sell": "📉 格蘭碧賣點：正乖離過大 (賣4) 或 跌破後反彈不過 (賣2)。"
        }

    def get_story(self, name_or_code: str) -> str:
        for k, v in self.stock_stories.items():
            if k in name_or_code: return v
        return ""
    
    def check_story_quality(self, story_text: str) -> int:
        score = 0
        if any(x in story_text for x in ["擴產", "新廠", "資本支出", "研發"]): score += 20
        if any(x in story_text for x in ["借新還舊", "償還銀行借款"]): score += 10
        return score

    def get_full_strategy(self) -> Dict:
        return self.full_strategy_text

    def get_time_arbitrage_rules(self) -> List[str]:
        rules = [
            "1. 新債蜜月期 (Listing+90): 敲鑼打鼓，最容易動。",
            "2. 沈睡一年甦醒 (Dormant Awakening): 若前3個月不動，通常滿一年後發動 (SOP核心)。",
            "3. 避稅行情 (Put-180): 賣回日前半年，公司派拉抬動機強。",
            "4. 融券與除權息 (Event-Driven): 3-4月回補、6-8月除權息降轉。"
        ]
        for i, evt in enumerate(self.time_arbitrage_events):
            desc = ""
            if isinstance(evt, dict) and 'event' in evt:
                desc = evt['event']
            elif isinstance(evt, str):
                desc = evt
            
            if desc:
                rules.append(f"• 季節性題材: {desc[:30]}...")
        return list(set(rules))