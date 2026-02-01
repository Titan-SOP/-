# macro_risk.py
# Titan SOP V78.4 - Macro Risk Engine (King Rescue Protocol)
# [V78.4 Patch]:
# 1. Implemented "VIP Rescue Protocol" in _get_leader_analysis.
#    - Automatically detects if market kings (5274, 3661, etc.) are missing from batch download.
#    - Forces a single-thread re-download for these VIPs to ensure Window 16 accuracy.
# 2. Enhanced sorting logic to strictly respect price/turnover values.

import numpy as np
import pandas as pd
import yfinance as yf
from config import Config
from knowledge_base import TitanKnowledgeBase
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import re

# 內建台股熱門股名稱與產業對照表 (Metadata Injection)
STOCK_METADATA = {
    "2330.TW": {"name": "台積電", "industry": "半導體/晶圓代工"}, "2454.TW": {"name": "聯發科", "industry": "半導體/IC設計"},
    "2317.TW": {"name": "鴻海", "industry": "電子代工"}, "2308.TW": {"name": "台達電", "industry": "電源/電子零組件"},
    "3008.TW": {"name": "大立光", "industry": "光學鏡頭"}, "6505.TW": {"name": "台塑化", "industry": "塑化"},
    "2881.TW": {"name": "富邦金", "industry": "金融"}, "2882.TW": {"name": "國泰金", "industry": "金融"},
    "2886.TW": {"name": "兆豐金", "industry": "金融"}, "1301.TW": {"name": "台塑", "industry": "塑化"},
    "1303.TW": {"name": "南亞", "industry": "塑化"}, "2002.TW": {"name": "中鋼", "industry": "鋼鐵"},
    "1216.TW": {"name": "統一", "industry": "食品"}, "1101.TW": {"name": "台泥", "industry": "水泥/儲能"},
    "2382.TW": {"name": "廣達", "industry": "AI伺服器/代工"}, "3034.TW": {"name": "聯詠", "industry": "半導體/驅動IC"},
    "3037.TW": {"name": "欣興", "industry": "PCB"}, "4904.TW": {"name": "遠傳", "industry": "通信服務"},
    "2327.TW": {"name": "國巨", "industry": "被動元件"}, "2412.TW": {"name": "中華電", "industry": "通信服務"},
    "3711.TW": {"name": "日月光投控", "industry": "半導體/封測"}, "2891.TW": {"name": "中信金", "industry": "金融"},
    "2884.TW": {"name": "玉山金", "industry": "金融"}, "2885.TW": {"name": "元大金", "industry": "金融"},
    "5880.TW": {"name": "合庫金", "industry": "金融"}, "2892.TW": {"name": "第一金", "industry": "金融"},
    "2303.TW": {"name": "聯電", "industry": "半導體/晶圓代工"}, "2379.TW": {"name": "瑞昱", "industry": "半導體/IC設計"},
    "2395.TW": {"name": "研華", "industry": "工業電腦"}, "6669.TW": {"name": "緯穎", "industry": "AI伺服器"},
    "3661.TW": {"name": "世芯-KY", "industry": "半導體/IP設計"}, "5274.TW": {"name": "信驊", "industry": "半導體/伺服器IC"},
    "6415.TW": {"name": "矽力-KY", "industry": "半導體/電源管理IC"}, "3529.TW": {"name": "力旺", "industry": "半導體/IP設計"},
    "3443.TW": {"name": "創意", "industry": "半導體/IP設計"}, "8454.TW": {"name": "富邦媒", "industry": "電子商務"},
    "1590.TW": {"name": "亞德客-KY", "industry": "精密機械"}, "2059.TW": {"name": "川湖", "industry": "電腦硬體/導軌"},
    "8299.TW": {"name": "群聯", "industry": "半導體/NAND控制IC"}, "3533.TW": {"name": "嘉澤", "industry": "電子零組件/連接器"},
    "6409.TW": {"name": "旭隼", "industry": "電子零_電源"}, "3563.TW": {"name": "牧德", "industry": "電子設備/AOI"},
    "8046.TW": {"name": "南電", "industry": "PCB"}, "3611.TW": {"name": "鼎翰", "industry": "電腦週邊"},
    "8464.TW": {"name": "億豐", "industry": "家居"}, "9910.TW": {"name": "豐泰", "industry": "製鞋"},
    "6271.TW": {"name": "同欣電", "industry": "半導體/封測"}, "3035.TW": {"name": "智原", "industry": "半導體/IP設計"},
    "4966.TW": {"name": "譜瑞-KY", "industry": "半導體/IC設計"}, "2451.TW": {"name": "創見", "industry": "記憶體模組"},
    "2207.TW": {"name": "和泰車", "industry": "汽車銷售"}, "2603.TW": {"name": "長榮", "industry": "航運/貨櫃"},
    "2609.TW": {"name": "陽明", "industry": "航運/貨櫃"}, "2615.TW": {"name": "萬海", "industry": "航運/貨櫃"},
    "5871.TW": {"name": "中租-KY", "industry": "租賃"}, "2880.TW": {"name": "華南金", "industry": "金融"},
    "2883.TW": {"name": "開發金", "industry": "金融"}, "2887.TW": {"name": "台新金", "industry": "金融"},
    "5876.TW": {"name": "上海商銀", "industry": "金融"}, "2357.TW": {"name": "華碩", "industry": "電腦品牌"},
    "3231.TW": {"name": "緯創", "industry": "AI伺服器/代工"}, "4938.TW": {"name": "和碩", "industry": "電子代工"},
    "2345.TW": {"name": "智邦", "industry": "網通設備"}, "2610.TW": {"name": "華航", "industry": "航運/航空"},
    "2618.TW": {"name": "長榮航", "industry": "航運/航空"}, "1795.TW": {"name": "美時", "industry": "生技/製藥"},
    "6548.TW": {"name": "長科*", "industry": "半導體/導線架"}, "1503.TW": {"name": "士電", "industry": "重電"},
    "1513.TW": {"name": "中興電", "industry": "重電/綠能"}, "1514.TW": {"name": "亞力", "industry": "重電"},
    "1524.TW": {"name": "耿鼎", "industry": "汽車零組件"}, "1536.TW": {"name": "和大", "industry": "汽車零組件"},
    "1560.TW": {"name": "中砂", "industry": "半導體/砂輪"}, "1589.TW": {"name": "永冠-KY", "industry": "風電鑄件"},
    "1605.TW": {"name": "華新", "industry": "電線電纜/不鏽鋼"}, "1722.TW": {"name": "台肥", "industry": "化工"},
    "1723.TW": {"name": "中碳", "industry": "化工"}, "1773.TW": {"name": "勝一", "industry": "化工"},
    "1785.TW": {"name": "光洋科", "industry": "貴金屬回收"}, "1802.TW": {"name": "台玻", "industry": "玻璃"},
    "2006.TW": {"name": "東和鋼鐵", "industry": "鋼鐵"}, "2014.TW": {"name": "中鴻", "industry": "鋼鐵"},
    "2027.TW": {"name": "大成鋼", "industry": "鋼鐵"}, "2049.TW": {"name": "上銀", "industry": "精密機械"},
    "2105.TW": {"name": "正新", "industry": "輪胎"}, "2201.TW": {"name": "裕隆", "industry": "汽車製造"},
    "2204.TW": {"name": "中華", "industry": "汽車製造"}, "2206.TW": {"name": "三陽工業", "industry": "汽機車"},
    "2313.TW": {"name": "華通", "industry": "PCB"}, "2324.TW": {"name": "仁寶", "industry": "電子代工"},
    "2337.TW": {"name": "旺宏", "industry": "半導體/記憶體"}, "2344.TW": {"name": "華邦電", "industry": "半導體/記憶體"},
    "2352.TW": {"name": "佳世達", "industry": "電腦週邊/醫療"}, "2353.TW": {"name": "宏碁", "industry": "電腦品牌"},
    "2354.TW": {"name": "鴻準", "industry": "金屬機殼"}, "2356.TW": {"name": "英業達", "industry": "電子代工"},
    "2360.TW": {"name": "致茂", "industry": "電子檢測設備"}, "2368.TW": {"name": "金像電", "industry": "PCB"},
    "2371.TW": {"name": "大同", "industry": "家電/重電"}, "2376.TW": {"name": "技嘉", "industry": "電腦硬體"},
    "2377.TW": {"name": "微星", "industry": "電腦硬體"}, "2383.TW": {"name": "台光電", "industry": "PCB/CCL"},
    "2404.TW": {"name": "漢唐", "industry": "無塵室工程"}, "2408.TW": {"name": "南亞科", "industry": "半導體/記憶體"},
    "2409.TW": {"name": "友達", "industry": "光電/面板"}, "2421.TW": {"name": "建準", "industry": "散熱"},
    "2439.TW": {"name": "美律", "industry": "聲學元件"}, "2449.TW": {"name": "京元電子", "industry": "半導體/封測"},
    "2458.TW": {"name": "義隆", "industry": "半導體/IC設計"}, "2464.TW": {"name": "盟立", "industry": "自動化設備"},
    "2474.TW": {"name": "可成", "industry": "金屬機殼"}, "2485.TW": {"name": "兆赫", "industry": "網通"},
    "2492.TW": {"name": "華新科", "industry": "被動元件"}, "2498.TW": {"name": "宏達電", "industry": "手機/VR"},
    "2501.TW": {"name": "國建", "industry": "營建"}, "2542.TW": {"name": "興富發", "industry": "營建"},
    "2601.TW": {"name": "益航", "industry": "航運/散裝"}, "2606.TW": {"name": "裕民", "industry": "航運/散裝"},
    "2634.TW": {"name": "漢翔", "industry": "軍工/航太"}, "2637.TW": {"name": "慧洋-KY", "industry": "航運/散裝"},
    "2801.TW": {"name": "彰銀", "industry": "金融"}, "2823.TW": {"name": "中壽", "industry": "金融"},
    "2834.TW": {"name": "臺企銀", "industry": "金融"}, "2855.TW": {"name": "統一證", "industry": "金融"},
    "2912.TW": {"name": "統一超", "industry": "零售通路"}, "3005.TW": {"name": "神基", "industry": "強固電腦"},
    "3017.TW": {"name": "奇鋐", "industry": "散熱"}, "3023.TW": {"name": "信邦", "industry": "連接器/線束"},
    "3044.TW": {"name": "健鼎", "industry": "PCB"}, "3045.TW": {"name": "台灣大", "industry": "通信服務"},
    "3189.TW": {"name": "景碩", "industry": "PCB/載板"}, "3376.TW": {"name": "新日興", "industry": "樞紐"},
    "3406.TW": {"name": "玉晶光", "industry": "光學鏡頭"}, "3450.TW": {"name": "聯鈞", "industry": "光通訊"},
    "3481.TW": {"name": "群創", "industry": "光電/面板"}, "3596.TW": {"name": "智易", "industry": "網通"},
    "3653.TW": {"name": "健策", "industry": "散熱/均熱片"}, "3682.TW": {"name": "亞太電", "industry": "通信服務"},
    "3702.TW": {"name": "大聯大", "industry": "電子通路"}, "3706.TW": {"name": "神達", "industry": "電腦週邊"},
    "4128.TW": {"name": "中天", "industry": "生技/新藥"}, "4763.TW": {"name": "材料-KY", "industry": "化工"},
    "4915.TW": {"name": "致伸", "industry": "電腦週邊"}, "4919.TW": {"name": "新唐", "industry": "半導體/MCU"},
    "4958.TW": {"name": "臻鼎-KY", "industry": "PCB"}, "5269.TW": {"name": "祥碩", "industry": "半導體/IC設計"},
    "5347.TW": {"name": "世界", "industry": "半導體/晶圓代工"}, "5434.TW": {"name": "崇越", "industry": "半導體/通路"},
    "5483.TW": {"name": "中美晶", "industry": "半導體/矽晶圓"}, "5522.TW": {"name": "遠雄", "industry": "營建"},
    "6005.TW": {"name": "群益證", "industry": "金融"}, "6176.TW": {"name": "瑞儀", "industry": "光電/背光模組"},
    "6191.TW": {"name": "精成科", "industry": "PCB"}, "6202.TW": {"name": "盛群", "industry": "半導體/MCU"},
    "6213.TW": {"name": "聯茂", "industry": "PCB/CCL"}, "6239.TW": {"name": "力成", "industry": "半導體/封測"},
    "6269.TW": {"name": "台郡", "industry": "PCB/軟板"}, "6278.TW": {"name": "台表科", "industry": "SMT"},
    "6285.TW": {"name": "啟碁", "industry": "網通"}, "6414.TW": {"name": "樺漢", "industry": "工業電腦"},
    "6446.TW": {"name": "藥華藥", "industry": "生技/新藥"}, "6456.TW": {"name": "GIS-KY", "industry": "觸控模組"},
    "6461.TW": {"name": "益得", "industry": "生技/製藥"}, "6526.TW": {"name": "達爾膚", "industry": "生技/美妝"},
    "6531.TW": {"name": "愛普*", "industry": "半導體/IP設計"}, "6643.TW": {"name": "M31", "industry": "半導體/IP設計"},
    "6770.TW": {"name": "力積電", "industry": "半導體/晶圓代工"}, "8016.TW": {"name": "矽創", "industry": "半導體/驅動IC"},
    "8028.TW": {"name": "昇陽半導體", "industry": "半導體/再生晶圓"}, "8069.TW": {"name": "元太", "industry": "電子紙"},
    "8105.TW": {"name": "凌巨", "industry": "光電/面板"}, "8150.TW": {"name": "南茂", "industry": "半導體/封測"},
    "8210.TW": {"name": "勤誠", "industry": "伺服器機殼"}, "8261.TW": {"name": "富鼎", "industry": "半導體/MOSFET"},
    "8436.TW": {"name": "大江", "industry": "生技/保健"}, "9904.TW": {"name": "寶成", "industry": "製鞋"},
    "9917.TW": {"name": "中保科", "industry": "安控"}, "9921.TW": {"name": "巨大", "industry": "自行車"},
    "9933.TW": {"name": "中鼎", "industry": "工程"}, "9938.TW": {"name": "百和", "industry": "紡織副料"},
    "9945.TW": {"name": "潤泰新", "industry": "營建/零售"}, "4114.TW": {"name": "健喬", "industry": "生技/製藥"},
    "4162.TW": {"name": "智擎", "industry": "生技/新藥"}, "4743.TW": {"name": "合一", "industry": "生技/新藥"},
    "5289.TW": {"name": "宜鼎", "industry": "記憶體模組"}, "6121.TW": {"name": "新普", "industry": "電池模組"},
    "6146.TW": {"name": "耕興", "industry": "電子檢測"}, "6182.TW": {"name": "合晶", "industry": "半導體/矽晶圓"},
    "6244.TW": {"name": "茂迪", "industry": "太陽能"}, "8044.TW": {"name": "網家", "industry": "電子商務"},
    "8086.TW": {"name": "宏捷科", "industry": "半導體/PA"}, "8437.TW": {"name": "F-IET", "industry": "半導體/PA"},
    "3105.TW": {"name": "穩懋", "industry": "半導體/PA"}, "3131.TW": {"name": "弘塑", "industry": "半導體設備"},
    "3293.TW": {"name": "鈊象", "industry": "遊戲"}, "3527.TW": {"name": "聚積", "industry": "半導體/驅動IC"},
    "3587.TW": {"name": "閎康", "industry": "半導體檢測"}, "3693.TW": {"name": "營邦", "industry": "伺服器機殼"},
    "4979.TW": {"name": "華星光", "industry": "光通訊"}, "5278.TW": {"name": "尚凡", "industry": "軟體/網路"},
    "5315.TW": {"name": "光聯", "industry": "光電/面板"}, "5425.TW": {"name": "台半", "industry": "半導體/二極體"},
    "5457.TW": {"name": "宣德", "industry": "連接器"}, "5481.TW": {"name": "群聯", "industry": "半導體/NAND控制IC"},
    "6104.TW": {"name": "創惟", "industry": "半導體/IC設計"}, "6163.TW": {"name": "華電網", "industry": "網通整合"},
    "6188.TW": {"name": "廣明", "industry": "電腦週邊/機器人"}, "6220.TW": {"name": "岳豐", "industry": "連接線材"},
    "6279.TW": {"name": "胡連", "industry": "汽車零組件"}, "6488.TW": {"name": "環球晶", "industry": "半導體/矽晶圓"},
    "8050.TW": {"name": "廣積", "industry": "工業電腦"}, "8091.TW": {"name": "翔名", "industry": "半導體設備"},
    "8358.TW": {"name": "金居", "industry": "PCB/銅箔"}, "8933.TW": {"name": "愛山林", "industry": "營建"}
}

class MacroRiskEngine:
    def __init__(self):
        self.cache_data = {}

    def _safe_get_close(self, df: pd.DataFrame) -> pd.Series:
        if df.empty: return pd.Series(dtype=float)
        try:
            close = df['Close']
            if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
            # [V78.2 Fix] 強制補值，確保均線計算不會因單日 NaN 而斷裂
            return close.ffill().bfill().dropna()
        except: return pd.Series(dtype=float)

    def _calculate_slope(self, series: pd.Series, window: int) -> float:
        if len(series) < window: return 0.0
        y = series.iloc[-window:].values
        x = np.arange(len(y))
        slope, _ = np.polyfit(x, y, 1)
        normalized_slope = (slope / np.mean(y)) * 100 if np.mean(y) != 0 else 0
        return normalized_slope

    def _analyze_granville_bias(self, price: float, ma: float, ma_type: str) -> str:
        if price == 0 or ma == 0: return "N/A"
        bias = ((price - ma) / ma) * 100
        if bias > 20: return f"📈 {ma_type}乖離過熱 (賣4)"
        elif bias > 0: return f"👍 {ma_type}之上 (持有)"
        elif bias > -20: return f"📉 回測{ma_type} (買2)"
        else: return f"❄️ {ma_type}乖離超跌 (買4)"

    def _analyze_tse_technicals(self) -> Dict:
        res = {
            "name": "台股加權指數", "price": 0, "momentum": "N/A", "magic_ma": "N/A",
            "deduct_slope": [], "granville": "N/A"
        }
        try:
            df = yf.download(Config.TICKER_TSE, period="2y", progress=False)
            if df.empty:
                res["magic_ma"] = "❌ 數據斷線"
                return res

            close = self._safe_get_close(df)
            if len(close) < Config.MA_LONG_TERM:
                res["magic_ma"] = "❌ 數據不足"
                return res

            price = close.iloc[-1]
            res["price"] = float(price)

            high_3d = close.iloc[-3:].max()
            prev_high_5d = close.iloc[-8:-3].max()
            if price >= high_3d: res["momentum"] = "🚀 強勢創高"
            elif high_3d < prev_high_5d: res["momentum"] = "📉 趨勢趨緩"
            else: res["momentum"] = "⏳ 區間盤整"

            ma87_series = close.rolling(Config.MA_LIFE_LINE).mean()
            ma284_series = close.rolling(Config.MA_LONG_TERM).mean()
            ma87 = ma87_series.iloc[-1]
            ma284 = ma284_series.iloc[-1]
            if ma87 > ma284: res["magic_ma"] = "🔥 中期多頭"
            else: res["magic_ma"] = "❄️ 中期空頭"

            res["granville"] = self._analyze_granville_bias(price, ma87, "87MA")

            slopes = []
            for window, name, series in [(Config.MA_LIFE_LINE, "87MA", ma87_series), (Config.MA_LONG_TERM, "284MA", ma284_series)]:
                if len(close) < window: continue
                slope = self._calculate_slope(series, 10)
                deduct_price = close.iloc[-window]
                deduct_status = "🔥 扣低助漲" if price > deduct_price else "❄️ 扣高助跌"
                slopes.append(f"{name}: {slope:.2f}° ({deduct_status})")
            res["deduct_slope"] = slopes

            return res
        except Exception:
            res["magic_ma"] = "❌ 分析錯誤"
            return res

    def get_single_stock_data(self, ticker: str, period: str = "2y") -> pd.DataFrame:
        if ticker in self.cache_data and (datetime.now() - self.cache_data[ticker]['timestamp']).total_seconds() < 600:
            return self.cache_data[ticker]['data']
        
        try:
            df = yf.download(ticker, period=period, progress=False)
            if df.empty:
                return pd.DataFrame()
            self.cache_data[ticker] = {'timestamp': datetime.now(), 'data': df}
            return df
        except Exception:
            return pd.DataFrame()

    def calculate_ma_deduction_forecast(self, df: pd.DataFrame, ma_period: int = 87, forecast_days: int = 60) -> pd.DataFrame:
        if df.empty or len(df) < ma_period:
            return pd.DataFrame()

        close_prices = self._safe_get_close(df)
        
        deduction_series = close_prices.shift(ma_period - 1).iloc[-(forecast_days + len(close_prices) - (ma_period -1)):]
        
        if deduction_series.empty:
            return pd.DataFrame()

        future_dates = pd.bdate_range(start=df.index[-1] + timedelta(days=1), periods=len(deduction_series))
        
        forecast_df = pd.DataFrame({
            'Date': future_dates,
            'Deduction_Value': deduction_series.values
        }).set_index('Date')
        
        return forecast_df

    def calculate_adam_projection(self, df: pd.DataFrame, lookback_days: int = 20) -> pd.DataFrame:
        if df.empty or len(df) < lookback_days:
            return pd.DataFrame()

        close_prices = self._safe_get_close(df)
        recent_prices = close_prices.iloc[-lookback_days:]
        
        price_diffs = recent_prices.diff().dropna()
        
        last_price = recent_prices.iloc[-1]
        projection = [last_price]
        for diff in price_diffs:
            next_price = projection[-1] + diff
            projection.append(next_price)
            
        future_dates = pd.bdate_range(start=df.index[-1], periods=len(projection))

        projection_df = pd.DataFrame({
            'Date': future_dates,
            'Projected_Price': projection
        }).set_index('Date')

        return projection_df

    def _get_leader_analysis(self, tickers: List[str], sort_key: str, top_n: int) -> pd.DataFrame:
        # [V78.4 Fix] VIP 股王救援機制與去重
        unique_tickers = sorted(list(set(tickers)))
        
        # 定義必須確保存在的 VIP 股王清單 (防止 yfinance 批次下載時遺漏)
        # 包括: 信驊, 世芯, 力旺, 大立光, 緯穎, 創意, 川湖, 祥碩, 嘉澤
        VIP_KINGS = ["5274.TW", "3661.TW", "3529.TW", "3008.TW", "6669.TW", "3443.TW", "2059.TW", "5269.TW", "3533.TW"]

        # 1. 批次下載 (Batch Download)
        try:
            data = yf.download(unique_tickers, period="2y", progress=False, group_by='ticker', threads=True)
            if data.empty:
                data = pd.DataFrame() # 初始化為空，等待救援
        except Exception:
            data = pd.DataFrame()

        leader_list = []
        
        # 2. 處理批次數據
        processed_tickers = set()
        if not data.empty:
            for ticker in unique_tickers:
                try:
                    if len(unique_tickers) > 1:
                        if ticker not in data.columns.levels[0]: continue
                        stock_df = data[ticker]
                    else:
                        stock_df = data

                    if stock_df.empty or stock_df['Close'].isnull().all(): continue
                    
                    close_prices = self._safe_get_close(stock_df)
                    if close_prices.empty: continue
                    last_close = close_prices.iloc[-1]
                    if pd.isna(last_close): continue

                    value = 0
                    if sort_key == 'turnover':
                        last_volume = stock_df['Volume'].ffill().iloc[-1]
                        value = last_close * last_volume if not pd.isna(last_volume) else 0
                    elif sort_key == 'price':
                        value = last_close
                    
                    leader_list.append({"ticker": ticker, "value": value, "df": stock_df})
                    processed_tickers.add(ticker)
                except Exception: continue

        # 3. [V78.4 New] VIP 股王救援行動 (Rescue Protocol)
        # 如果是針對價格排序 (Window 16)，且關鍵股王不在已處理名單中，強制單獨下載
        if sort_key == 'price':
            for vip in VIP_KINGS:
                if vip in unique_tickers and vip not in processed_tickers:
                    try:
                        # 強制單獨下載救援
                        rescue_df = yf.download(vip, period="2y", progress=False)
                        if not rescue_df.empty and not rescue_df['Close'].isnull().all():
                            close_prices = self._safe_get_close(rescue_df)
                            if not close_prices.empty:
                                last_close = close_prices.iloc[-1]
                                leader_list.append({"ticker": vip, "value": last_close, "df": rescue_df})
                    except Exception:
                        pass # 救援失敗則放棄

        if not leader_list:
            return pd.DataFrame([{"error": "無法計算任何股票的排序值"}])

        # 4. 排序與選取 Top N
        sorted_leaders = sorted(leader_list, key=lambda x: x['value'], reverse=True)
        top_leaders = sorted_leaders[:top_n]

        results = []
        for i, leader in enumerate(top_leaders):
            try:
                ticker = leader['ticker']
                stock_df = leader['df'] # 直接使用已保存的 DataFrame (無論是批次還是救援的)
                
                close_prices = self._safe_get_close(stock_df)
                if len(close_prices) < Config.MA_LONG_TERM: continue

                metadata = STOCK_METADATA.get(ticker, {"name": re.sub(r'\.TW$', '', ticker), "industry": "N/A"})
                current_price = close_prices.iloc[-1]
                
                ma87_series = close_prices.rolling(Config.MA_LIFE_LINE).mean()
                ma284_series = close_prices.rolling(Config.MA_LONG_TERM).mean()
                ma87 = ma87_series.iloc[-1]
                ma284 = ma284_series.iloc[-1]

                is_bullish = ma87_series > ma284_series
                trend_status = "中期多頭 (黃金交叉)" if is_bullish.iloc[-1] else "中期空頭 (死亡交叉)"
                
                try:
                    trend_groups = is_bullish.ne(is_bullish.shift()).cumsum()
                    trend_days = trend_groups.groupby(trend_groups).cumcount().iloc[-1] + 1
                except: trend_days = 0

                ma87_slope = self._calculate_slope(ma87_series, 20)
                
                deduction_price = close_prices.iloc[-Config.MA_LIFE_LINE]
                deduction_signal = "📈 助漲 (扣低)" if current_price > deduction_price else "📉 壓力 (扣高)"

                results.append({
                    "rank": i + 1,
                    "ticker": ticker,
                    "name": metadata["name"],
                    "industry": metadata["industry"],
                    "sort_value": leader['value'],
                    "current_price": current_price,
                    "trend_status": trend_status,
                    "trend_days": int(trend_days),
                    "ma87_slope": ma87_slope,
                    "deduction_signal": deduction_signal,
                    "ma87": ma87,
                    "stock_df": stock_df,
                    "deduction_df": self.calculate_ma_deduction_forecast(stock_df, ma_period=Config.MA_LIFE_LINE, forecast_days=60),
                    "adam_df": self.calculate_adam_projection(stock_df, lookback_days=20)
                })
            except Exception: continue
        
        # 最終再次重新排序並重置 Rank，確保救援進來的股王位置正確
        final_df = pd.DataFrame(results)
        if not final_df.empty:
            final_df = final_df.sort_values('sort_value', ascending=False).reset_index(drop=True)
            final_df['rank'] = final_df.index + 1
            
        return final_df

    def get_dynamic_turnover_leaders(self, top_n: int = 100) -> pd.DataFrame:
        return self._get_leader_analysis(Config.TITAN_WIDE_POOL, 'turnover', top_n)

    def get_high_price_leaders(self, top_n: int = 50) -> pd.DataFrame:
        return self._get_leader_analysis(Config.HIGH_PRICED_SEED_POOL, 'price', top_n)

    def calculate_ptt_bearish_ratio(self, cb_df: pd.DataFrame = None) -> float:
        tickers = Config.HIGH_PRICED_SEED_POOL
        
        try:
            data = yf.download(tickers, period="150d", progress=False, group_by='ticker', threads=True)
            if data.empty or data.isnull().all().all():
                raise ValueError("Primary yfinance download failed")
        except Exception:
            if cb_df is None or cb_df.empty or 'stock_code' not in cb_df.columns:
                return -1.0
            
            unique_codes = cb_df['stock_code'].dropna().unique()
            tickers = [f"{code}.TW" for code in unique_codes]
            if not tickers: return -1.0
            
            try:
                data = yf.download(tickers, period="150d", progress=False, group_by='ticker', threads=True)
            except Exception:
                return -1.0

        bearish_count = 0
        valid_stocks = 0
        for ticker in tickers:
            try:
                stock_df = data[ticker] if len(tickers) > 1 and ticker in data.columns.levels[0] else data
                if stock_df.empty or len(stock_df) < Config.MA_SLOPE_60D: continue
                
                close = self._safe_get_close(stock_df)
                if close.empty: continue

                ma60 = close.rolling(Config.MA_SLOPE_60D).mean().iloc[-1]
                
                if not np.isnan(ma60) and close.iloc[-1] < ma60:
                    bearish_count += 1
                valid_stocks += 1
            except (KeyError, IndexError):
                continue
        
        if valid_stocks == 0: return -1.0
        return (bearish_count / valid_stocks) * 100

    def calculate_price_distribution(self, cb_df: pd.DataFrame) -> Dict:
        distribution_data = {"pr90": 0.0, "pr75": 0.0, "avg": 0.0, "chart_data": pd.DataFrame()}
        if cb_df is None or cb_df.empty or 'close' not in cb_df.columns:
            return distribution_data

        prices = pd.to_numeric(cb_df['close'], errors='coerce').dropna()
        prices = prices[(prices > 70) & (prices < 500)]
        if len(prices) < 5: return distribution_data

        distribution_data["pr90"] = float(np.percentile(prices, 90))
        distribution_data["pr75"] = float(np.percentile(prices, 75))
        distribution_data["avg"] = float(prices.mean())

        counts, bin_edges = np.histogram(prices, bins=20)
        chart_df = pd.DataFrame({
            '區間': [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(counts))],
            '數量': counts
        })
        distribution_data["chart_data"] = chart_df
        
        return distribution_data

    def analyze_high_50_sentiment(self) -> Dict:
        tickers = Config.HIGH_PRICED_SEED_POOL
        bull_count = 0
        bear_count = 0
        total_analyzed = 0
        
        try:
            data = yf.download(tickers, period="1y", progress=False, group_by='ticker', threads=True)
            if data.empty:
                return {"error": "無法下載高價權值股數據。"}

            for ticker in tickers:
                try:
                    stock_df = data[ticker] if len(tickers) > 1 and ticker in data.columns.levels[0] else data
                    if stock_df.empty or len(stock_df) < Config.MA_LIFE_LINE:
                        continue

                    close = self._safe_get_close(stock_df)
                    if close.empty:
                        continue
                    
                    price = close.iloc[-1]
                    ma87 = close.rolling(Config.MA_LIFE_LINE).mean().iloc[-1]

                    if pd.isna(price) or pd.isna(ma87):
                        continue
                    
                    if price > ma87:
                        bull_count += 1
                    else:
                        bear_count += 1
                    total_analyzed += 1
                except (KeyError, IndexError):
                    continue
            
            if total_analyzed == 0:
                return {"error": "高價權值股數據不足，無法分析。"}

            bull_ratio = (bull_count / total_analyzed) * 100
            bear_ratio = (bear_count / total_analyzed) * 100
            
            sentiment = "😐 中性"
            if bull_ratio > 65:
                sentiment = "🐂 極度樂觀"
            elif bull_ratio > 50:
                sentiment = "🔥 偏多"
            elif bear_ratio > 65:
                sentiment = "🐻 極度悲觀"
            elif bear_ratio > 50:
                sentiment = "❄️ 偏空"

            return {
                "bull_ratio": bull_ratio,
                "bear_ratio": bear_ratio,
                "sentiment": sentiment,
                "total": total_analyzed
            }

        except Exception as e:
            return {"error": f"分析失敗: {str(e)}"}

    def analyze_sector_heatmap(self, df: pd.DataFrame, kb: TitanKnowledgeBase) -> pd.DataFrame:
        from strategy import TitanStrategyEngine 

        if df.empty or 'stock_code' not in df.columns:
            return pd.DataFrame()
        
        local_df = df.copy()

        if 'stock_price' not in local_df.columns or 'MA87' not in local_df.columns:
            local_df = TitanStrategyEngine()._batch_enrich_data(local_df)

        heatmap_data = []
        all_cb_stocks = set(local_df['stock_code'].astype(str).tolist())

        for sector, stocks in kb.sector_bellwether_map.items():
            relevant_stocks = all_cb_stocks.intersection(set(stocks))
            if not relevant_stocks:
                continue

            sector_df = local_df[local_df['stock_code'].isin(relevant_stocks)]
            if sector_df.empty:
                continue

            total_count = len(sector_df)
            
            above_ma87_count = (sector_df['stock_price'] > sector_df['MA87']).sum()
            above_ma87_ratio = (above_ma87_count / total_count) * 100 if total_count > 0 else 0

            change_col = next((col for col in local_df.columns if '%' in col or '漲跌' in col), None)
            avg_change = pd.to_numeric(sector_df[change_col], errors='coerce').mean() if change_col else np.nan

            sector_bellwethers = kb.sector_bellwether_map.get(sector, set())

            heatmap_data.append({
                "族群": sector,
                "領頭羊": ", ".join(sorted(list(sector_bellwethers))),
                "檔數": total_count,
                "多頭比例 (%)": f"{above_ma87_ratio:.1f}",
                "平均漲跌幅 (%)": f"{avg_change:.2f}" if not np.isnan(avg_change) else "N/A"
            })
        
        if not heatmap_data:
            return pd.DataFrame([{"族群": "無匹配族群", "領頭羊": "N/A", "檔數": 0, "多頭比例 (%)": "N/A", "平均漲跌幅 (%)": "N/A"}])

        heatmap_df = pd.DataFrame(heatmap_data).sort_values(by="多頭比例 (%)", ascending=False)
        heatmap_df = heatmap_df[["族群", "領頭羊", "檔數", "多頭比例 (%)", "平均漲跌幅 (%)"]]
        return heatmap_df.reset_index(drop=True)

    def check_market_status(self, cb_df: pd.DataFrame = None) -> Dict:
        signals = []

        try:
            vix = float(self._safe_get_close(yf.download(Config.TICKER_VIX, period="5d", progress=False)).iloc[-1])
        except: vix = 15.0
        if vix > Config.VIX_PANIC: signals.append("GREEN")

        price_dist = self.calculate_price_distribution(cb_df)
        if price_dist["pr90"] > Config.PR90_OVERHEAT: signals.append("RED")
        elif price_dist["pr90"] < Config.PR75_OPPORTUNITY and price_dist["pr90"] > 0: signals.append("GREEN")

        tse_analysis = self._analyze_tse_technicals()
        if "空頭" in tse_analysis["magic_ma"]: signals.append("RED")

        ptt_ratio = self.calculate_ptt_bearish_ratio(cb_df)
        if ptt_ratio > 50: signals.append("RED")

        final = "YELLOW_LIGHT"
        if "RED" in signals: final = "RED_LIGHT"
        elif "GREEN" in signals and "RED" not in signals: final = "GREEN_LIGHT"

        return {
            "signal": final, "vix": vix, "ptt_ratio": ptt_ratio,
            "price_distribution": price_dist, "tse_analysis": tse_analysis
        }