# config_v100.py
# Titan SOP V100.0 - 2035 百倍股無限軍火庫 (The Ultimate Arsenal)
# 設計日期: 2026-02-12
# 狀態: 最高法律效力
# 戰略目標: 尋找 2035 年的百倍股 - 全球成長股總動員
# 總計規模: 2500+ 精選標的

import os
from pathlib import Path

# ==========================================
# 1. 專案根目錄設定 (Project Root Anchoring)
# ==========================================
# 使用 r"" (raw string) 避免 Windows 路徑的反斜線被誤判為跳脫字元
BASE_DIR = Path(__file__).resolve().parent

# 【自我檢測】: 程式啟動時先檢查路徑是否存在，避免後續連鎖錯誤
if not BASE_DIR.exists():
    raise FileNotFoundError(f"CRITICAL ERROR: 找不到專案根目錄，請檢查路徑: {BASE_DIR}")

# ==========================================
# 2. 資料子目錄映射 (Sub-directory Mapping)
# ==========================================
DATA_DIR = BASE_DIR / "data"            # 放置 .csv, .json 等原始數據
DB_DIR = BASE_DIR / "database"          # 放置 .db 資料庫檔 (若有)
STRATEGY_DIR = BASE_DIR / "strategies"  # 放置策略模組
LOG_DIR = BASE_DIR / "logs"             # 系統日誌

# 自動確保這些資料夾存在 (若無則自動建立，防止報錯)
for _dir in [DATA_DIR, DB_DIR, STRATEGY_DIR, LOG_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


class Config:
    # --- 1. 神奇均線 ---
    MA_LIFE_LINE = 87
    MA_LONG_TERM = 284
    MA_SHORT_TERM = 43
    MA_SLOPE_20D = 20
    MA_SLOPE_60D = 60

    # --- 2. 策略濾網 ---
    FILTER_MAX_PRICE = 115.0 # 四大天條之一：價格濾網

    # --- 3. 價格區間 (SOP核心) ---
    SWEET_SPOT_LOW = 106
    SWEET_SPOT_HIGH = 110
    CB_PAR_VALUE = 100

    EXIT_TARGET_MEDIAN = 152

    # --- 4. 宏觀監控 ---
    TICKER_TSE = "^TWII"     # 台灣加權指數
    TICKER_VIX = "^VIX"

    # PTT 空頭比例計算用的高價種子池 (V78.3 優化版 - 去重)
    # 基於台股前100高價股，作為市場多空溫度計的真實樣本
    _raw_high_pool = [
        "5274.TW", "6669.TW", "3661.TW", "3008.TW", "3443.TW", "2059.TW", "3653.TW",
        "8299.TW", "6515.TW", "3529.TW", "6415.TW", "1590.TW", "2308.TW", "6409.TW",
        "6643.TW", "3533.TW", "6461.TW", "6799.TW", "6223.TW", "3481.TW", "8454.TW",
        "6531.TW", "6472.TW", "3131.TW", "6680.TW", "6869.TW", "4966.TW", "3037.TW",
        "6756.TW", "6187.TW", "6510.TW", "6719.TW", "3680.TW", "8069.TW", "6446.TW",
        "2379.TW", "3711.TW", "2330.TW", "5269.TW", "6271.TW", "3035.TW", "4935.TW",
        "3406.TW", "6196.TW", "2454.TW", "6121.TW", "6239.TW", "6278.TW", "8081.TW",
        "3693.TW", "6488.TW", "2382.TW", "3231.TW", "4919.TW", "3583.TW", "2376.TW",
        "2377.TW", "2395.TW", "2408.TW", "2458.TW", "2618.TW", "2881.TW", "2882.TW",
        "2886.TW", "2891.TW", "2892.TW", "2912.TW", "3045.TW", "3376.TW", "3702.TW",
        "4904.TW", "5871.TW", "5880.TW", "6005.TW", "6505.TW", "9910.TW", "1301.TW",
        "1303.TW", "2002.TW", "1101.TW", "1216.TW", "2207.TW", "2603.TW", "2609.TW",
        "2615.TW", "8464.TW", "9904.TW", "9921.TW", "9933.TW", "9938.TW", "9945.TW",
        "1795.TW", "6442.TW", "4743.TW", "4128.TW", "4162.TW", "4147.TW", "6491.TW",
        "6547.TW", "6684.TW", "6782.TW", "8436.TW", "8406.TW", "1560.TW", "1519.TW",
        "1503.TW", "1513.TW", "1514.TW"
    ]
    HIGH_PRICED_SEED_POOL = sorted(list(set(_raw_high_pool)))

    # [V78.3 NEW] Window 16 動態成交重心掃描用的戰略股票池
    # 涵蓋台灣50、中型100、富櫃50、高價股、AI供應鏈、CoWoS、重電綠能、生技、IP設計、散熱、機器人等，共約400檔
    _raw_wide_pool = [
        # --- 台灣50 + 核心權值 (部分重疊) ---
        "2330.TW", "2454.TW", "2317.TW", "2308.TW", "3008.TW", "6505.TW", "2881.TW",
        "2882.TW", "2886.TW", "1301.TW", "1303.TW", "2002.TW", "1216.TW", "1101.TW",
        "2382.TW", "3034.TW", "3037.TW", "4904.TW", "2327.TW", "2412.TW", "3711.TW",
        "2891.TW", "2884.TW", "2885.TW", "5880.TW", "2892.TW", "2303.TW", "2379.TW",
        "2395.TW", "2880.TW", "2883.TW", "2887.TW", "5871.TW", "5876.TW", "2357.TW",
        "3231.TW", "4938.TW", "2345.TW", "2408.TW", "2474.TW", "2801.TW", "2912.TW",
        "3045.TW", "9910.TW", "2409.TW", "2451.TW", "2207.TW", "2603.TW", "2609.TW",
        "2615.TW", "1326.TW", "1402.TW", "2888.TW", "2890.TW", "6669.TW",

        # --- 上市櫃高價股 (股價 > 200) ---
        "3661.TW", "5274.TW", "6415.TW", "3529.TW", "3443.TW", "8454.TW", "1590.TW",
        "2059.TW", "8299.TW", "3533.TW", "6409.TW", "3563.TW", "8046.TW", "3611.TW",
        "8464.TW", "6271.TW", "3035.TW", "4966.TW", "6515.TW", "3653.TW", "6223.TW",
        "6461.TW", "6799.TW", "3481.TW", "6531.TW", "6472.TW", "3131.TW", "6680.TW",
        "6869.TW", "6756.TW", "6187.TW", "6510.TW", "6719.TW", "3680.TW", "8069.TW",
        "6446.TW", "5269.TW", "4935.TW", "3406.TW", "6196.TW", "6121.TW", "6239.TW",
        "6278.TW", "8081.TW", "3693.TW", "6488.TW", "3583.TW", "2376.TW", "2377.TW",
        "3376.TW", "3702.TW", "6005.TW", "1795.TW", "6442.TW", "4743.TW", "4128.TW",
        "4162.TW", "4147.TW", "6491.TW", "6547.TW", "6684.TW", "6782.TW", "8436.TW",
        "8406.TW", "1560.TW", "1519.TW", "1503.TW", "1513.TW", "1514.TW", "3675.TW",
        "4919.TW", "8064.TW", "8437.TW", "6695.TW", "6805.TW", "3105.TW", "5289.TW",

        # --- AI 伺服器供應鏈 & CoWoS 概念股 ---
        "2382.TW", "3231.TW", "6669.TW", "2356.TW", "2317.TW", "2376.TW", "3706.TW",
        "8210.TW", "3693.TW", "6117.TW", "3013.TW", "2421.TW", "6196.TW", "6187.TW",
        "3583.TW", "2449.TW", "3374.TW", "3680.TW", "6533.TW", "3037.TW", "3711.TW",
        "2316.TW", "1560.TW", "6285.TW", "3527.TW", "6640.TW", "6706.TW", "6139.TW",
        "3413.TW", "3536.TW", "6261.TW", "8028.TW", "3169.TW", "6271.TW", "3653.TW",
        "3017.TW", "6230.TW", "3324.TW", "3017.TW", "2467.TW", "6664.TW", "6789.TW",

        # --- 重電 & 綠能概念股 ---
        "1519.TW", "1503.TW", "1513.TW", "1514.TW", "1605.TW", "1609.TW", "1618.TW",
        "2371.TW", "6806.TW", "8996.TW", "1589.TW", "3023.TW", "6473.TW", "9958.TW",
        "3708.TW", "6449.TW", "6244.TW", "4934.TW", "6411.TW", "6482.TW", "6861.TW",

        # --- 生技新藥 & 醫療器材 ---
        "6446.TW", "1795.TW", "6472.TW", "4128.TW", "4142.TW", "4162.TW", "4147.TW",
        "6547.TW", "4108.TW", "4114.TW", "4133.TW", "6612.TW", "6692.TW", "6875.TW",
        "1760.TW", "1789.TW", "1784.TW", "4107.TW", "4192.TW", "6465.TW", "6523.TW",
        "6589.TW", "6657.TW", "6949.TW", "8279.TW", "4728.TW", "4735.TW", "4743.TW",

        # --- IP 設計 & ASIC ---
        "3661.TW", "3443.TW", "3529.TW", "6533.TW", "3035.TW", "6643.TW", "6531.TW",
        "6695.TW", "3443.TW", "6590.TW", "6742.TW", "3228.TW", "6684.TW", "6859.TW",

        # --- 散熱族群 ---
        "3017.TW", "3324.TW", "3653.TW", "6125.TW", "8210.TW", "3693.TW", "6230.TW",
        "2421.TW", "3484.TW", "8996.TW", "1587.TW", "3162.TW", "3013.TW", "6197.TW",
        "2233.TW", "4566.TW", "4551.TW", "2228.TW",

        # --- 機器人概念股 ---
        "2049.TW", "1590.TW", "1597.TW", "2308.TW", "6414.TW", "2359.TW", "8033.TW",
        "2464.TW", "6166.TW", "4540.TW", "4562.TW", "8374.TW", "7750.TW", "1504.TW",
        "1583.TW", "2360.TW", "5443.TW", "6215.TW",

        # --- 中型100 + 富櫃50 + 其他熱門股 (補遺) ---
        "2610.TW", "2618.TW", "6548.TW", "1503.TW", "1536.TW", "1560.TW", "1722.TW",
        "1723.TW", "1773.TW", "1785.TW", "1802.TW", "2006.TW", "2014.TW", "2027.TW",
        "2105.TW", "2201.TW", "2204.TW", "2206.TW", "2313.TW", "2324.TW", "2337.TW",
        "2344.TW", "2352.TW", "2353.TW", "2354.TW", "2356.TW", "2368.TW", "2371.TW",
        "2383.TW", "2404.TW", "2439.TW", "2449.TW", "2458.TW", "2464.TW", "2485.TW",
        "2492.TW", "2498.TW", "2501.TW", "2542.TW", "2601.TW", "2606.TW", "2634.TW",
        "2637.TW", "2823.TW", "2834.TW", "2855.TW", "3005.TW", "3023.TW", "3044.TW",
        "3189.TW", "3450.TW", "3596.TW", "3682.TW", "3706.TW", "4763.TW", "4915.TW",
        "4958.TW", "5347.TW", "5434.TW", "5483.TW", "5522.TW", "6176.TW", "6191.TW",
        "6202.TW", "6213.TW", "6269.TW", "6285.TW", "6414.TW", "6456.TW", "6526.TW",
        "6643.TW", "6770.TW", "8016.TW", "8105.TW", "8150.TW", "8210.TW", "8261.TW",
        "9917.TW", "9945.TW", "4114.TW", "5289.TW", "6146.TW", "6182.TW", "8044.TW",
        "8086.TW", "3293.TW", "3587.TW", "4979.TW", "5278.TW", "5315.TW", "5425.TW",
        "5457.TW", "5481.TW", "6104.TW", "6163.TW", "6188.TW", "6220.TW", "6279.TW",
        "8050.TW", "8091.TW", "8358.TW", "8933.TW"
    ]
    TITAN_WIDE_POOL = sorted(list(set(_raw_wide_pool)))

    PRICE_COL_KEYWORDS = [
        '可轉債市價', '收盤價', 'close', '現價', '成交', 'price',
        '買進', '賣出', '成交價', '市價', 'last'
    ]
    
    # --- 5. 時間與風控 ---
    LISTING_HONEYMOON_DAYS = 90
    LISTING_DORMANT_DAYS = 365
    PUT_AVOID_TAX_DAYS = 180

    EVENT_SHORT_COVER_MONTHS = [3, 4]
    EVENT_DIVIDEND_MONTHS = [6, 8]

    PR90_OVERHEAT = 130
    PR75_OPPORTUNITY = 105
    VIX_PANIC = 25

    # --- 6. 發債故事關鍵字 ---
    STORY_KEYWORDS = ["AI", "綠能", "軍工", "重電", "擴產", "政策", "從無到有", "新廠", "併購", "轉機"]


# ==========================================
# [WAR_THEATERS] V100.0 - 2035 百倍股無限軍火庫
# 設計日期: 2026-02-12
# ⚠️ 警語: 本名單為針對 2035 年景氣循環設計，總計 2500+ 檔精選標的
# ⚠️ 規定: 必須每半年 (6個月) 檢視並更新一次成分股，以確保符合最新產業趨勢
# ==========================================

WAR_THEATERS = {
    
    # region 🇺🇸 美股：ARK 破壞式創新 (US_ARK_DNA)
    "US_ARK_DNA": [
        # --- ARK Innovation Core Holdings ---
        "TSLA",   # Tesla - 電動車與能源革命
        "COIN",   # Coinbase - 加密貨幣交易所
        "RBLX",   # Roblox - 元宇宙平台
        "ROKU",   # Roku - 串流媒體
        "SQ",     # Block (Square) - 金融科技
        "SHOP",   # Shopify - 電商平台
        "U",      # Unity Software - 遊戲引擎
        "PATH",   # UiPath - RPA 機器人流程自動化
        "ZM",     # Zoom - 遠端會議
        "TWLO",   # Twilio - 雲端通訊
        "HOOD",   # Robinhood - 零佣金券商
        "DKNG",   # DraftKings - 運動博彩
        "SOFI",   # SoFi - 新世代銀行
        "PLTR",   # Palantir - 大數據分析
        "NET",    # Cloudflare - 邊緣運算
        "DOCU",   # DocuSign - 電子簽名
        "TDOC",   # Teladoc - 遠距醫療
        
        # --- ARK Genomic Revolution (ARKG) ---
        "CRSP",   # CRISPR Therapeutics - 基因編輯
        "NTLA",   # Intellia Therapeutics - CRISPR
        "BEAM",   # Beam Therapeutics - 鹼基編輯
        "EDIT",   # Editas Medicine - 基因療法
        "TXG",    # 10x Genomics - 單細胞定序
        "DNA",    # Ginkgo Bioworks - 合成生物學
        "PACB",   # Pacific Biosciences - 長讀定序
        "NVTA",   # Invitae - 基因檢測
        "SDGR",   # Schrodinger - AI 藥物設計
        "VRTX",   # Vertex Pharmaceuticals - CF 藥物
        "FATE",   # Fate Therapeutics - iPSC 療法
        "CLLS",   # Cellectis - CAR-T
        "EXAS",   # Exact Sciences - 癌症篩檢
        "IONS",   # Ionis Pharmaceuticals - 反義核酸
        "RGNX",   # Regenxbio - AAV 基因療法
        "BMRN",   # BioMarin - 罕見疾病
        "ARCT",   # Arcturus Therapeutics - mRNA
        "BLUE",   # bluebird bio - 基因療法
        "SGMO",   # Sangamo Therapeutics - 鋅指核酸酶
        "VCYT",   # Veracyte - 分子診斷
        
        # --- ARK Fintech Innovation (ARKF) ---
        "COIN",   # Coinbase
        "HOOD",   # Robinhood
        "SQ",     # Block
        "PYPL",   # PayPal
        "AFRM",   # Affirm - 先買後付
        "UPST",   # Upstart - AI 信貸
        "SOFI",   # SoFi
        "LC",     # LendingClub
        "BILL",   # Bill.com - 企業支付
        "MQ",     # Marqeta - 金融卡平台
        "NU",     # Nu Holdings - 巴西數位銀行
        "OPEN",   # Opendoor - 房地產科技
        "CELH",   # Celsius - 能量飲料 (成長股)
        
        # --- 3D 列印與太空 ---
        "DDD",    # 3D Systems
        "SSYS",   # Stratasys
        "XONE",   # ExOne
        "MTLS",   # Materialise
        "RKLB",   # Rocket Lab - 小型火箭
        "SPCE",   # Virgin Galactic - 太空旅遊
        "MKFG",   # Markforged - 金屬 3D 列印
        
        # --- Cloud & SaaS ---
        "SNOW",   # Snowflake - 資料倉儲
        "DDOG",   # Datadog - 監控平台
        "CRWD",   # CrowdStrike - 網路安全
        "ZS",     # Zscaler - 雲端安全
        "OKTA",   # Okta - 身分驗證
        "MDB",    # MongoDB - 資料庫
        "ESTC",   # Elastic - 搜尋引擎
        "TEAM",   # Atlassian - 協作軟體
        "NOW",    # ServiceNow - IT 管理
        "WDAY",   # Workday - 人力資源
        "VEEV",   # Veeva - 生技 SaaS
        "ZI",     # ZoomInfo - B2B 資料
        "APPN",   # Appian - 低代碼平台
        
        # --- EV & Mobility ---
        "TSLA",   # Tesla
        "RIVN",   # Rivian - 電動卡車
        "LCID",   # Lucid Motors - 豪華電動車
        "NIO",    # NIO - 中國電動車
        "XPEV",   # XPeng - 中國電動車
        "LI",     # Li Auto - 增程式電動車
        "CHPT",   # ChargePoint - 充電樁
        "BLNK",   # Blink Charging
        "EVGO",   # EVgo - 快充網路
        "RIDE",   # Lordstown Motors
        
        # --- Disruptive Tech ---
        "SPOT",   # Spotify - 音樂串流
        "TTD",    # Trade Desk - 程序化廣告
        "MELI",   # MercadoLibre - 拉美電商
        "SE",     # Sea Limited - 東南亞電商
        "GRAB",   # Grab - 東南亞叫車
        "ABNB",   # Airbnb - 共享住宿
        "DASH",   # DoorDash - 外送
        "UBER",   # Uber - 叫車與外送
        "LYFT",   # Lyft - 叫車
        
        # --- New Age Media ---
        "NFLX",   # Netflix
        "DIS",    # Disney+ (傳統媒體轉型)
        "PARA",   # Paramount
        "WBD",    # Warner Bros Discovery
        "PINS",   # Pinterest
        "SNAP",   # Snapchat
        "MTCH",   # Match Group - 交友平台
        "BMBL",   # Bumble - 交友 App
    ],
    # endregion
    
    # region 🇺🇸 美股：創世紀實體建設 (US_GENESIS_PHYSICAL)
    "US_GENESIS_PHYSICAL": [
        # --- 核能與新能源 (AI Power Infrastructure) ---
        "OKLO",   # Oklo - 小型核反應爐
        "NNE",    # Nano Nuclear Energy - 微型核電
        "SMR",    # NuScale Power - 小型模組化反應爐
        "BWXT",   # BWX Technologies - 核能設備
        "CEG",    # Constellation Energy - 核電營運
        "VST",    # Vistra Energy - 電力公司
        "FLR",    # Fluor - 核電工程
        "LUCK",   # Luck Companies - 基礎建設
        "CCJ",    # Cameco - 鈾礦開採
        "UEC",    # Uranium Energy - 鈾礦
        "DNN",    # Denison Mines - 鈾礦
        "LEU",    # Centrus Energy - 濃縮鈾
        "GEV",    # GE Vernova - 電力設備
        "NRG",    # NRG Energy - 電力公司
        "NEE",    # NextEra Energy - 再生能源
        "AEP",    # American Electric Power
        "D",      # Dominion Energy
        "EXC",    # Exelon - 電力公司
        "SO",     # Southern Company
        "DUK",    # Duke Energy
        "AES",    # AES Corporation
        "PCG",    # PG&E - 加州電力
        "ED",     # Consolidated Edison
        "ETR",    # Entergy
        "PEG",    # Public Service Enterprise
        "WEC",    # WEC Energy
        "XEL",    # Xcel Energy
        "PPL",    # PPL Corporation
        "CMS",    # CMS Energy
        "DTE",    # DTE Energy
        "ENPH",   # Enphase - 太陽能逆變器
        "SEDG",   # SolarEdge - 太陽能系統
        "FSLR",   # First Solar - 太陽能面板
        "RUN",    # Sunrun - 住宅太陽能
        "NOVA",   # Sunnova - 太陽能融資
        "CSIQ",   # Canadian Solar
        "JKS",    # JinkoSolar
        "MAXN",   # Maxeon Solar
        "ARRY",   # Array Technologies - 追日系統
        "BE",     # Bloom Energy - 燃料電池
        "PLUG",   # Plug Power - 氫能
        "BLDP",   # Ballard Power - 氫燃料電池
        "FCEL",   # FuelCell Energy
        "NEL",    # Nel Hydrogen - 電解槽
        
        # --- 機器人與自動化 (Embodied AI) ---
        "SYM",    # Symbotic - 倉儲機器人
        "ROK",    # Rockwell Automation - 工業自動化
        "IRBT",   # iRobot - 掃地機器人
        "TER",    # Teradyne - 半導體測試 + 協作機器人
        "STR",    # Sitio Royalties (原 STR Automation)
        "OUST",   # Ouster - 光達
        "LAZR",   # Luminar - 光達
        "MVIS",   # MicroVision - 光達
        "INVZ",   # Innoviz - 光達
        "VLDR",   # Velodyne - 光達
        "AEYE",   # AudioEye (原 AEye - 光達)
        "RKLB",   # Rocket Lab - 太空機器人
        "AJRD",   # Aerojet Rocketdyne - 火箭推進
        "LMT",    # Lockheed Martin - 軍工機器人
        "RTX",    # Raytheon - 國防自動化
        "NOC",    # Northrop Grumman
        "GD",     # General Dynamics
        "BA",     # Boeing - 航太自動化
        "HON",    # Honeywell - 工業自動化
        "EMR",    # Emerson Electric
        "ETN",    # Eaton - 電力管理
        "PH",     # Parker Hannifin - 液壓系統
        "ITW",    # Illinois Tool Works
        "DOV",    # Dover Corporation
        "SNA",    # Snap-on - 工具
        "GNRC",   # Generac - 發電機
        "IR",     # Ingersoll Rand - 工業設備
        "CARR",   # Carrier - 暖通空調
        "TT",     # Trane Technologies
        "JCI",    # Johnson Controls - 建築自動化
        "FAST",   # Fastenal - 工業供應
        "MSM",    # MSC Industrial
        
        # --- 量子運算與次世代算力 ---
        "IONQ",   # IonQ - 量子運算
        "RGTI",   # Rigetti Computing - 量子晶片
        "QBTS",   # D-Wave Quantum - 量子退火
        "ARQQ",   # Arqit Quantum - 量子加密
        "QTUM",   # Defiance Quantum ETF (參考)
        "SMCI",   # Super Micro Computer - AI 伺服器
        "VRT",    # Vertiv - 資料中心基礎設施
        "ANET",   # Arista Networks - 資料中心網路
        "PSTG",   # Pure Storage - 全快閃儲存
        "LITE",   # Lumentum - 光通訊
        "COHR",   # Coherent - 光學元件
        "IOSP",   # Innospec (原 IOSP - Optical)
        "COMM",   # CommScope - 網路基礎設施
        "GLW",    # Corning - 光纖玻璃
        "CIEN",   # Ciena - 光通訊設備
        "INFN",   # Infinera - 光傳輸
        "AAOI",   # Applied Optoelectronics
        "NPTN",   # NeoPhotonics
        "FNSR",   # Finisar (已被 II-VI 收購)
        "VIAV",   # Viavi Solutions - 光學測試
        
        # --- 製造業回流 (Reshoring) ---
        "CAT",    # Caterpillar - 工程機械
        "DE",     # Deere & Company - 農業機械
        "CMI",    # Cummins - 引擎與發電機
        "PH",     # Parker Hannifin
        "EMR",    # Emerson
        "ETN",    # Eaton
        "ITW",    # Illinois Tool Works
        "ROK",    # Rockwell Automation
        "AME",    # Ametek - 精密儀器
        "FTV",    # Fortive - 工業技術
        "ROP",    # Roper Technologies
        "DHR",    # Danaher - 生命科學與診斷
        "TMO",    # Thermo Fisher Scientific
        "A",      # Agilent Technologies
        "WAT",    # Waters Corporation
        "PKI",    # PerkinElmer
        "MTD",    # Mettler-Toledo
        "IEX",    # IDEX Corporation
        "XYL",    # Xylem - 水處理
        "AWK",    # American Water Works
        "WMS",    # Advanced Drainage Systems
        "VMI",    # Valmont Industries - 基礎建設
        "MLM",    # Martin Marietta - 骨材
        "VMC",    # Vulcan Materials
        "SUM",    # Summit Materials
        "USCR",   # U.S. Concrete
        "CRH",    # CRH plc - 水泥
        "NUE",    # Nucor - 鋼鐵
        "STLD",   # Steel Dynamics
        "CLF",    # Cleveland-Cliffs - 鋼鐵
        "X",      # United States Steel
        "MT",     # ArcelorMittal - 全球鋼鐵
        "RS",     # Reliance Steel
        "CMC",    # Commercial Metals
        "WOR",    # Worthington Industries
        "ATI",    # ATI Inc. - 特殊金屬
        "AA",     # Alcoa - 鋁業
        "CENX",   # Century Aluminum
        "KALU",   # Kaiser Aluminum
        "FCX",    # Freeport-McMoRan - 銅礦
        "SCCO",   # Southern Copper
        "TECK",   # Teck Resources - 銅與鋅
        "HBM",    # Hudbay Minerals
        "CMCL",   # Caledonia Mining - 黃金
        
        # --- 電網與儲能 ---
        "TSLA",   # Tesla Energy - Megapack
        "FSLR",   # First Solar
        "ENPH",   # Enphase
        "SEDG",   # SolarEdge
        "ALB",    # Albemarle - 鋰礦
        "SQM",    # Sociedad Química y Minera - 鋰
        "LAC",    # Lithium Americas
        "LTHM",   # Livent - 鋰化學品
        "PLL",    # Piedmont Lithium
        "LIT",    # Global X Lithium ETF (參考)
        "CBAK",   # CBAK Energy - 電池
        "QS",     # QuantumScape - 固態電池
        "SES",    # SES AI - 固態電池
        "SLDP",   # Solid Power - 固態電池
        "FREYR",  # FREYR Battery - 電池製造
        "ENVX",   # Enovix - 矽陽極電池
        "ABML",   # American Battery Materials
        "MP",     # MP Materials - 稀土
        "LYNAS",  # Lynas Rare Earths (ASX)
        "UUUU",   # Energy Fuels - 鈾與稀土
    ],
    # endregion
    
    # region 🇺🇸 美股：羅素 2000 成長精選 (US_RUSSELL_GROWTH)
    "US_RUSSELL_GROWTH": [
        # --- SaaS & Cybersecurity ---
        "S",      # SentinelOne - AI 網路安全
        "TENB",   # Tenable - 漏洞管理
        "RPD",    # Rapid7 - 安全分析
        "VRNS",   # Varonis - 資料安全
        "QLYS",   # Qualys - 雲端安全
        "ALTR",   # Altair Engineering - 工程模擬
        "BOX",    # Box - 雲端儲存
        "DBX",    # Dropbox - 雲端儲存
        "DOCN",   # DigitalOcean - 雲端平台
        "FIVN",   # Five9 - 雲端客服中心
        "JAMF",   # Jamf - Apple 裝置管理
        "NCNO",   # nCino - 銀行 SaaS
        "WK",     # Workiva - 企業報告
        "YEXT",   # Yext - 數位知識管理
        "NEWR",   # New Relic - 應用監控
        "GTLB",   # GitLab - DevOps 平台
        "BILL",   # Bill.com
        "PCTY",   # Paylocity - 人資軟體
        "PAYC",   # Paycom - 人資軟體
        "HUBS",   # HubSpot - 行銷自動化
        "ZI",     # ZoomInfo
        "RNG",    # RingCentral - 雲端通訊
        "SMAR",   # Smartsheet - 協作軟體
        "ASAN",   # Asana - 專案管理
        "MNDY",   # Monday.com - 工作管理
        "PD",     # PagerDuty - 事件管理
        "SUMO",   # Sumo Logic - 日誌分析
        "EVBG",   # Everbridge - 緊急通知
        "BL",     # BlackLine - 財務自動化
        "APPF",   # AppFolio - 不動產軟體
        "KNSL",   # Kinsale Capital - 保險科技
        
        # --- 生技 (Non-ARK Small/Mid Cap) ---
        "ITCI",   # Intra-Cellular Therapies - CNS 藥物
        "AXSM",   # Axsome Therapeutics - 神經疾病
        "KRTX",   # Karuna Therapeutics - 精神分裂症
        "SWAV",   # ShockWave Medical - 血管治療
        "INSP",   # Inspire Medical - 睡眠呼吸中止
        "GKOS",   # Glaukos - 青光眼裝置
        "TMDX",   # TransMedics - 器官移植
        "ARVN",   # Arvinas - 蛋白降解
        "BBIO",   # BridgeBio Pharma - 罕見疾病
        "HALO",   # Halozyme Therapeutics - 藥物輸送
        "RARE",   # Ultragenyx - 罕見疾病
        "LEGN",   # Legend Biotech - CAR-T
        "IMVT",   # Immunovant - 自體免疫
        "KRYS",   # Krystal Biotech - 基因療法
        "PTCT",   # PTC Therapeutics - 罕見疾病
        "UTHR",   # United Therapeutics - 肺動脈高壓
        "ALNY",   # Alnylam - RNAi 療法
        "SRPT",   # Sarepta - 肌肉萎縮症
        "NBIX",   # Neurocrine Biosciences - 神經疾病
        "JAZZ",   # Jazz Pharmaceuticals - 睡眠與癌症
        "EXEL",   # Exelixis - 癌症藥物
        "RGLS",   # Regulus Therapeutics - microRNA
        "DVAX",   # Dynavax - 疫苗佐劑
        "HZNP",   # Horizon Therapeutics - 罕見疾病
        "PRTA",   # Prothena - 神經退化
        "MYGN",   # Myriad Genetics - 分子診斷
        "IRTC",   # iRhythm - 心律監測
        "PODD",   # Insulet - 胰島素幫浦
        "DXCM",   # DexCom - 連續血糖監測
        "TNDM",   # Tandem Diabetes - 胰島素幫浦
        "LIVN",   # LivaNova - 心血管裝置
        "NVCR",   # NovoCure - 腫瘤治療電場
        "AXNX",   # Axonics - 膀胱控制
        "IONS",   # Ionis Pharmaceuticals
        "ACAD",   # Acadia Pharmaceuticals - 精神疾病
        "FOLD",   # Amicus Therapeutics - 罕見疾病
        "VRTX",   # Vertex (雖較大，但成長強勁)
        
        # --- 消費與品牌 ---
        "CELH",   # Celsius - 能量飲料
        "ELF",    # e.l.f. Beauty - 平價美妝
        "ONON",   # On Holding - 瑞士運動鞋
        "CROX",   # Crocs - 洞洞鞋
        "BOOT",   # Boot Barn - 西部靴
        "WING",   # Wingstop - 炸雞翅
        "SHAK",   # Shake Shack - 漢堡
        "DUOL",   # Duolingo - 語言學習
        "LVLU",   # Lulu's Fashion - 女裝電商
        "FIGS",   # Figs - 醫療制服
        "BIRK",   # Birkenstock - 涼鞋
        "DECK",   # Deckers - UGG & Hoka
        "LULU",   # Lululemon - 運動服飾
        "FIVE",   # Five Below - 折扣零售
        "OLLI",   # Ollie's Bargain Outlet
        "PLAY",   # Dave & Buster's - 娛樂餐廳
        "TXRH",   # Texas Roadhouse - 牛排餐廳
        "BLMN",   # Bloomin' Brands - 餐飲
        "RUTH",   # Ruth's Chris - 高檔牛排
        "CAKE",   # Cheesecake Factory
        "DNUT",   # Krispy Kreme - 甜甜圈
        "CMG",    # Chipotle - 墨西哥快餐 (較大但成長強)
        "CAVA",   # Cava Group - 地中海快餐
        "BROS",   # Dutch Bros - 咖啡連鎖
        "SBUX",   # Starbucks (參考)
        "MCD",    # McDonald's (參考)
        "YUM",    # Yum! Brands - KFC/Pizza Hut (參考)
        "QSR",    # Restaurant Brands - Burger King (參考)
        
        # --- 其他高成長股 ---
        "UPST",   # Upstart - AI 信貸
        "AFRM",   # Affirm - 先買後付
        "RDFN",   # Redfin - 房地產科技
        "OPEN",   # Opendoor
        "COMP",   # Compass - 房仲平台
        "EXPI",   # eXp World Holdings - 虛擬房仲
        "UWMC",   # UWM Holdings - 房貸
        "RKT",    # Rocket Companies - Quicken Loans
        "LDI",    # loanDepot - 房貸
        "NAVI",   # Navient - 學貸
        "SLM",    # SLM Corporation - 學貸
        "TREE",   # LendingTree - 貸款比價
        "GDDY",   # GoDaddy - 網域註冊
        "WIX",    # Wix.com - 網站建站
        "SQSP",   # Squarespace - 網站建站
        "ETSY",   # Etsy - 手工藝品電商
        "PINS",   # Pinterest
        "SNAP",   # Snapchat
        "BMBL",   # Bumble
        "MTCH",   # Match Group
        "RKLB",   # Rocket Lab
        "PLTR",   # Palantir (雖較大)
        "SNOW",   # Snowflake (雖較大)
    ],
    # endregion
    
    # region 🇺🇸 美股：科技巨頭與半導體 (US_TECH_CORE)
    "US_TECH_CORE": [
        # --- Magnificent 7 + FAANG ---
        "AAPL",   # Apple
        "MSFT",   # Microsoft
        "GOOGL",  # Alphabet (Google)
        "GOOG",   # Alphabet Class C
        "AMZN",   # Amazon
        "NVDA",   # NVIDIA
        "META",   # Meta (Facebook)
        "TSLA",   # Tesla
        "NFLX",   # Netflix
        
        # --- 半導體設計 (Fabless) ---
        "AVGO",   # Broadcom
        "AMD",    # Advanced Micro Devices
        "QCOM",   # Qualcomm
        "MRVL",   # Marvell
        "NXPI",   # NXP Semiconductors
        "ADI",    # Analog Devices
        "TXN",    # Texas Instruments
        "INTC",   # Intel (IDM)
        "MU",     # Micron - 記憶體
        "WDC",    # Western Digital
        "STX",    # Seagate
        "PSTG",   # Pure Storage
        "NTAP",   # NetApp
        "SMCI",   # Super Micro Computer
        "DELL",   # Dell Technologies
        "HPQ",    # HP Inc.
        "HPE",    # Hewlett Packard Enterprise
        
        # --- 半導體設備 (Equipment) ---
        "AMAT",   # Applied Materials
        "LRCX",   # Lam Research
        "KLAC",   # KLA Corporation
        "ASML",   # ASML (荷蘭 - EUV)
        "TER",    # Teradyne - 測試設備
        "COHR",   # Coherent - 雷射與光學
        "MKSI",   # MKS Instruments
        "ENTG",   # Entegris - 特殊化學品
        "ACLS",   # Axcelis Technologies - 離子植入
        "UCTT",   # Ultra Clean Holdings
        "ICHR",   # Ichor Holdings
        "PLAB",   # Photronics - 光罩
        "FORM",   # FormFactor - 測試探針卡
        "ONTO",   # Onto Innovation - 計量設備
        "CAMT",   # Camtek - 檢測設備
        "NVMI",   # Nova (以色列 - 計量)
        "AEIS",   # Advanced Energy - 電源供應
        "INDI",   # indie Semiconductor (ADAS)
        
        # --- 功率半導體 ---
        "ON",     # ON Semiconductor
        "STM",    # STMicroelectronics
        "WOLF",   # Wolfspeed - SiC
        "MPWR",   # Monolithic Power Systems
        "ALSN",   # Allison Transmission (非半導體，可移除)
        "SLAB",   # Silicon Labs - IoT
        "SWKS",   # Skyworks - RF
        "QRVO",   # Qorvo - RF
        "CRUS",   # Cirrus Logic - 音訊晶片
        "DIOD",   # Diodes Incorporated
        "RMBS",   # Rambus - IP 授權
        "LSCC",   # Lattice Semiconductor - FPGA
        "MCHP",   # Microchip Technology
        "MXIM",   # Maxim (已被 ADI 收購)
        "SIMO",   # Silicon Motion - NAND 控制器
        "SITM",   # SiTime - MEMS 振盪器
        
        # --- 晶圓代工 ---
        "TSM",    # TSMC (台積電 ADR)
        "UMC",    # 聯電 ADR
        "GFS",    # GlobalFoundries
        "INTC",   # Intel (IDM + Foundry)
        
        # --- 其他半導體 ---
        "NVMI",   # Nova
        "AMKR",   # Amkor - 封測
        "ASX",    # ASE Technology (日月光 ADR)
        "SPIL",   # SPIL (矽品 - 已與 ASE 合併)
        "SSNLF",  # Samsung (韓國 ADR)
        "005930.KS", # Samsung Electronics
        "000660.KS", # SK Hynix
        
        # --- AI 算力與資料中心 ---
        "NVDA",   # NVIDIA
        "AMD",    # AMD
        "GOOGL",  # Google TPU
        "MSFT",   # Microsoft (Azure AI)
        "AMZN",   # Amazon (AWS AI)
        "META",   # Meta (MTIA)
        "ORCL",   # Oracle Cloud
        "CRM",    # Salesforce
        "ADBE",   # Adobe
        "INTU",   # Intuit
        "PANW",   # Palo Alto Networks
        "FTNT",   # Fortinet
        "CHKP",   # Check Point
        "CYBR",   # CyberArk
        "ZS",     # Zscaler
        "CRWD",   # CrowdStrike
        "S",      # SentinelOne
        "DDOG",   # Datadog
        "MDB",    # MongoDB
        "SNOW",   # Snowflake
        "NET",    # Cloudflare
        "FSLY",   # Fastly
        "AKAM",   # Akamai
        "LLNW",   # Limelight (已私有化)
        "EQIX",   # Equinix - 資料中心
        "DLR",    # Digital Realty
        "VRT",    # Vertiv
        "NTAP",   # NetApp
        
        # --- 雲端與企業軟體 ---
        "CRM",    # Salesforce
        "ORCL",   # Oracle
        "SAP",    # SAP
        "ADBE",   # Adobe
        "NOW",    # ServiceNow
        "WDAY",   # Workday
        "TEAM",   # Atlassian
        "ZM",     # Zoom
        "DOCU",   # DocuSign
        "TWLO",   # Twilio
        "DDOG",   # Datadog
        "ESTC",   # Elastic
        "SPLK",   # Splunk
        "VEEV",   # Veeva
        "ANSS",   # Ansys - 工程模擬
        "CDNS",   # Cadence Design - EDA
        "SNPS",   # Synopsys - EDA
        "ADSK",   # Autodesk - CAD
        "PTC",    # PTC - IoT/PLM
        "INTU",   # Intuit
        "TYL",    # Tyler Technologies
        "GWRE",   # Guidewire - 保險軟體
        
        # --- 通訊設備 ---
        "CSCO",   # Cisco
        "ANET",   # Arista Networks
        "JNPR",   # Juniper Networks
        "FFIV",   # F5 Networks
        "CIEN",   # Ciena
        "INFN",   # Infinera
        "COMM",   # CommScope
        "NOK",    # Nokia
        "ERIC",   # Ericsson
    ],
    # endregion
    
    # region 🇹🇼 台股：矽島核心供應鏈 (TW_SILICON_ISLAND)
    "TW_SILICON_ISLAND": [
        # --- 晶圓代工天王 ---
        "2330.TW",   # 台積電 - 全球晶圓代工龍頭
        "2303.TW",   # 聯電 - 晶圓代工二哥
        "6770.TW",   # 力積電 - 12吋晶圓代工
        "3707.TWO",  # 漢磊 - 8吋晶圓代工
        "5347.TW",   # 世界 - 晶圓代工
        "8016.TW",   # 矽創 - 顯示驅動 IC
        
        # --- IC 設計天團 ---
        "2454.TW",   # 聯發科 - 手機晶片
        "3661.TW",   # 世芯-KY - ASIC 設計
        "3443.TW",   # 創意 - ASIC
        "3035.TW",   # 智原 - ASIC IP
        "6643.TW",   # M31 - IP 矽智財
        "3529.TW",   # 力旺 - IP 矽智財
        "6531.TW",   # 愛普 - SSD 控制晶片
        "5269.TW",   # 祥碩 - USB/PCIe 控制晶片
        "5274.TW",   # 信驊 - BMC 晶片
        "3227.TWO",  # 原相 - 光學感測器
        "6138.TWO",  # 茂達 - 電源管理 IC
        "6261.TWO",  # 久元 - PCB 設備
        "6415.TW",   # 矽力-KY - 電源管理 IC
        "3511.TWO",  # 矽瑪 - PMIC
        "6804.TW",   # 南電 - 微機電
        "6121.TW",   # 新普 - 電池模組
        "6239.TW",   # 力成 - IC 封測
        "3450.TW",   # 聯鈞 - 光學鍍膜
        "6451.TW",   # 訊芯-KY - 網通晶片
        "4966.TWO",  # 譜瑞-KY - 高速傳輸晶片
        "6533.TW",   # 晶心科 - RISC-V CPU IP
        "6695.TW",   # 芯鼎 - 影像晶片
        "3563.TW",   # 牧德 - 半導體檢測設備
        "6782.TW",   # 視陽 - 顯示驅動 IC
        "6147.TW",   # 頎邦 - IC 封測
        "6285.TW",   # 啟碁 - 網通模組
        "2379.TW",   # 瑞昱 - 網通晶片
        "2383.TW",   # 台光電 - 軟板
        "3034.TW",   # 聯詠 - 顯示驅動 IC
        "8299.TW",   # 群聯 - NAND 控制晶片
        "3105.TW",   # 穩懋 - 砷化鎵代工
        "3533.TW",   # 嘉澤 - 功率放大器
        "6756.TW",   # 威鋒電子 - 功率半導體
        "6411.TWO",  # 晶焱 - 車用保護元件
        "5425.TWO",  # 台半 - 功率半導體
        "3169.TWO",  # 亞信 - 衛星通訊
        "3228.TWO",  # 金麗科 - 石英元件
        "6182.TWO",  # 合晶 - 矽晶圓再生
        "6488.TW",   # 環球晶 - 矽晶圓
        
        # --- CPO 矽光子革命 ---
        "3363.TW",   # 上詮 - 光通訊元件
        "3450.TW",   # 聯鈞 - 光學鍍膜
        "3163.TWO",  # 波若威 - 光通訊
        "4979.TWO",  # 華星光 - 光通訊
        "6442.TW",   # 光聖 - 光學元件
        "3081.TWO",  # 聯亞 - 光通訊
        "6451.TW",   # 訊芯-KY - 矽光子
        "4908.TWO",  # 前鼎 - 光通訊
        "4903.TWO",  # 聯光通 - 光通訊
        "6568.TWO",  # 宏觀 - 微投影光學
        "6573.TWO",  # 虹揚-KY - 光通訊
        "3406.TW",   # 玉晶光 - 光學鏡頭
        "3346.TWO",  # 麗清 - 光學鏡頭
        "6668.TWO",  # 中揚光 - 光學元件
        
        # --- AI 伺服器與散熱 ---
        "2382.TW",   # 廣達 - AI 伺服器
        "3231.TW",   # 緯創 - AI 伺服器
        "2317.TW",   # 鴻海 - AI 伺服器
        "6669.TW",   # 緯穎 - AI 伺服器
        "2356.TW",   # 英業達 - 伺服器
        "2376.TW",   # 技嘉 - 主機板
        "3017.TW",   # 奇鋐 - 散熱模組
        "3324.TW",   # 雙鴻 - 散熱
        "3653.TW",   # 健策 - 散熱
        "2421.TW",   # 建準 - 散熱風扇
        "2059.TW",   # 川湖 - 散熱支架
        "8210.TW",   # 勤誠 - 散熱
        "3693.TW",   # 營邦 - 散熱
        "6230.TW",   # 超眾 - PCB 散熱基板
        "5215.TW",   # 科嘉 - 散熱
        "3484.TW",   # 崧騰 - 散熱
        "6197.TWO",  # 佳必琪 - 散熱
        "5464.TWO",  # 霖宏 - 散熱
        "3013.TW",   # 晟銘電 - 散熱
        "1587.TW",   # 吉茂 - 散熱
        "3162.TW",   # 精確 - 散熱
        
        # --- 封測與記憶體 ---
        "3711.TW",   # 日月光投控 - 封測
        "2474.TW",   # 可成 - 金屬機殼
        "2449.TW",   # 京元電子 - 測試
        "8046.TW",   # 南電 - 載板
        "8028.TW",   # 昇陽半導體 - 功率半導體
        "3045.TW",   # 台灣大 - 電信
        "4968.TW",   # 立積 - DRAM 模組
        "3260.TW",   # 威剛 - DRAM/NAND 模組
        "4943.TW",   # 康控-KY - 工業電腦
        
        # --- PCB 供應鏈 ---
        "2313.TW",   # 華通 - PCB
        "6213.TWO",  # 聯茂 - 銅箔基板
        "6226.TW",   # 光鼎 - 軟板
        "6152.TWO",  # 百一 - 電子材料
        "6274.TWO",  # 台燿 - HDI PCB
        "3498.TWO",  # 陽程 - PCB
        "6179.TWO",  # 亞通 - PCB
        "6706.TWO",  # 惠特 - PCB
        "1565.TW",   # 精華 - 軟板
        "4927.TW",   # 泰鼎-KY - 軟板
        "3003.TW",   # 健和興 - PCB
        
        # --- 半導體材料 ---
        "4770.TW",   # 上品 - 化學材料
        "6698.TWO",  # 旭暉應材 - 半導體材料
        "3152.TWO",  # 璟德 - 電子材料
        "5243.TWO",  # 乙盛-KY - 電子材料
        "5514.TWO",  # 三豐 - 電子材料
        "8096.TWO",  # 擎亞 - 電子材料
        "4924.TWO",  # 欣厚-KY - 電子材料
        "3296.TWO",  # 勝德 - 化工薄膜
        
        # --- 被動元件 ---
        "2327.TW",   # 國巨 - MLCC
        "2456.TW",   # 奇力新 - 電感
        "3017.TW",   # 奇鋐 - 散熱 (重複)
        "6158.TWO",  # 禾昌 - 被動元件
        "5284.TWO",  # jpp-KY - 被動元件
        "6279.TWO",  # 胡連 - 連接器
        "8091.TWO",  # 翔名 - 連接器
        "6402.TW",   # 今展科 - 連接器
        
        # --- 設備與自動化 ---
        "3564.TW",   # 其陽 - 半導體設備
        "5340.TWO",  # 建榮 - PCB 設備
        "4945.TWO",  # 新揚科 - 半導體設備
        "5321.TWO",  # 友銓 - 檢測設備
        "3521.TWO",  # 鴻翊 - 半導體設備
        "6187.TWO",  # 萬潤 - 設備零組件
        "6409.TWO",  # 旭隼 - 精密機械
        "6425.TWO",  # 易發 - 工業自動化
    ],
    # endregion
    
    # region 🇹🇼 台股：生技與重電綠能 (TW_BIO_POWER)
    "TW_BIO_POWER": [
        # --- 生技新藥天團 (櫃買主力) ---
        "6446.TWO",  # 藥華藥 - P1101 新藥
        "6472.TWO",  # 保瑞 - 學名藥
        "6547.TWO",  # 高端疫苗 - 疫苗開發
        "4147.TWO",  # 中裕 - HIV 新藥
        "1795.TW",   # 美時化學 - 學名藥
        "4174.TWO",  # 浩鼎 - 癌症疫苗
        "4128.TWO",  # 中天 - 新藥
        "4743.TWO",  # 合一 - 新藥
        "6550.TWO",  # 北極星藥業-KY - 新藥
        "4162.TWO",  # 智擎 - 癌症新藥
        "1760.TW",   # 寶齡富錦 - 洗腎藥物
        "4105.TWO",  # 東洋 - 學名藥
        "4114.TWO",  # 健喬 - 學名藥
        "4120.TWO",  # 友華 - 學名藥
        "4123.TWO",  # 晟德 - 製藥
        "4142.TW",   # 國光生 - 疫苗
        "4192.TWO",  # 杏國 - 新藥
        "6496.TWO",  # 科懋 - 原料藥
        "6535.TWO",  # 順藥 - 學名藥
        "6589.TWO",  # 台康生技 - 生物相似藥
        "4167.TWO",  # 展旺 - 醫材
        "6657.TWO",  # 華安 - 醫材
        "6875.TWO",  # 永紳 - 醫材
        "4728.TWO",  # 雙美 - 醫美
        "4745.TWO",  # 合富-KY - 醫美保養品
        "1789.TW",   # 神隆 - 原料藥
        "1784.TW",   # 訊聯 - 幹細胞
        "4107.TWO",  # 邦特 - 醫材
        "4108.TWO",  # 懷特 - 生技
        "4133.TWO",  # 亞諾法 - 抗體
        "6612.TWO",  # 奈米醫材 - 骨科材料
        "6692.TWO",  # 泰宗 - 生技
        "6465.TWO",  # 威潤 - 醫材
        "6523.TWO",  # 達爾膚 - 皮膚藥
        "6949.TWO",  # 寶德 - 醫材
        "8279.TWO",  # 生展 - 骨科
        "4735.TWO",  # 豪展 - 醫材
        "6541.TWO",  # 泰福-KY - 生技
        "6767.TWO",  # 台微體 - 免疫療法
        "8088.TWO",  # 品安 - 醫療器材
        "4103.TWO",  # 百略 - 醫材
        
        # --- 重電與電力設備 ---
        "1513.TW",   # 中興電 - 重電龍頭
        "1519.TW",   # 華城 - 變壓器
        "1503.TW",   # 士電 - 馬達
        "1514.TW",   # 亞力 - 電線電纜
        "1605.TW",   # 華新 - 電線電纜
        "1609.TW",   # 大亞 - 電線電纜
        "1601.TW",   # 台光 - 電線電纜
        "1603.TW",   # 華電 - 電力設備
        "1604.TW",   # 聲寶 - 家電
        "1618.TW",   # 合機 - 電機
        "2371.TW",   # 大同 - 重電
        "1504.TW",   # 東元 - 馬達與重電
        "1507.TW",   # 永大 - 電梯
        "1512.TW",   # 瑞利 - 電機
        "1515.TW",   # 力山 - 電動工具
        "1527.TW",   # 鑽全 - 扣件
        "1560.TW",   # 中砂 - 砂輪
        "1583.TW",   # 程泰 - 工具機
        "1589.TW",   # 永冠-KY - 風電齒輪箱
        "1590.TW",   # 亞德客-KY - 氣動元件
        "1592.TW",   # 英瑞-KY - 汽車零組件
        "1597.TW",   # 直得 - 銅箔基板設備
        
        # --- 綠能與風電 ---
        "6806.TWO",  # 森崴能源 - 綠電
        "3708.TW",   # 上緯投控 - 風電材料
        "9958.TW",   # 世紀鋼 - 風電水下基礎
        "6244.TWO",  # 茂迪 - 太陽能
        "6482.TWO",  # 弘煜科 - 太陽能
        "6449.TWO",  # 鈺邦 - 太陽能逆變器
        "6411.TWO",  # 晶焱 - 車用 IC (重複，但可保留)
        "8996.TW",   # 高力 - 散熱 (重複)
        "3023.TW",   #信邦 - 連接線
        "6473.TWO",  # 山林水 - 水資源
        "4934.TWO",  # 太極 - 能源管理
        "3372.TW",   # 典範 - LED 照明
        "6261.TWO",  # 久元 - PCB 設備 (重複)
        "6790.TWO",  # 永豐實 - 鋁擠型
        "1333.TW",   # 恩德 - 鋁擠型
        "9919.TW",   # 康那香 - 衛生用品 (非綠能)
        "1711.TW",   # 永光 - 化工
        "1712.TW",   # 興農 - 農藥
        "1714.TW",   # 和桐 - 化工
        "1721.TW",   # 三晃 - 化工
        "1723.TW",   # 中碳 - 碳素
        "1725.TW",   # 元禎 - 化工
        "1726.TW",   # 永記 - 造紙
        "1727.TW",   # 中華化 - 化工
        "1730.TW",   # 花仙子 - 清潔用品
        "1731.TW",   # 美吾華 - 製藥
        "1732.TW",   # 毛寶 - 清潔用品
        "1733.TW",   # 五鼎 - 生技
        "1734.TW",   # 杏輝 - 製藥
        "1735.TW",   # 日勝化 - 化工
        
        # --- 其他傳統產業 (可選) ---
        "1301.TW",   # 台塑 - 石化
        "1303.TW",   # 南亞 - 塑膠
        "1326.TW",   # 台化 - 化纖
        "1402.TW",   # 遠東新 - 化纖
        "2002.TW",   # 中鋼 - 鋼鐵
        "2006.TW",   # 東和鋼鐵
        "2014.TW",   # 中鴻 - 鋼鐵
        "2105.TW",   # 正新 - 輪胎
        "2207.TW",   # 和泰車 - 汽車代理
        "2227.TW",   # 裕日車 - 汽車代理
        "2228.TW",   # 劍麟 - 汽車零組件
        "2233.TW",   # 宇隆 - 汽車零組件
    ],
    # endregion
    
    # region 🇯🇵 日股：失落三十年復甦精選 (JP_REVIVAL_CORE)
    "JP_REVIVAL_CORE": [
        # --- 日本半導體復興 (Semiconductor Revival) ---
        "6920.T",    # Lasertec - EUV 檢測設備
        "6857.T",    # Advantest - 半導體測試設備
        "8035.T",    # 東京威力科創 (TEL) - 半導體設備
        "6146.T",    # Disco - 晶圓切割設備
        "7735.T",    # Screen Holdings - 半導體設備
        "6501.T",    # 日立製作所 - 工業自動化與能源
        "6594.T",    # 日本電產 (Nidec) - 馬達
        "6981.T",    # 村田製作所 - 電子零組件
        "6758.T",    # Sony - 影像感測器與娛樂
        "6702.T",    # 富士通 - 雲端與 AI
        "6723.T",    # Renesas - 車用半導體
        "4063.T",    # 信越化學 - 半導體材料
        "4005.T",    # 住友化學 - 電子材料
        "6976.T",    # 太陽誘電 - MLCC
        "6770.T",    # Alps Alpine - 車用電子
        "6902.T",    # Denso - 汽車電子
        "6841.T",    # 橫河電機 - 工業儀器
        "6952.T",    # Casio - 精密機械
        "6869.T",    # Sysmex - 醫療檢測設備
        "7012.T",    # 川崎重工 - 機器人與航太
        "6861.T",    # Keyence - 感測器與自動化
        
        # --- 日本機器人與自動化 ---
        "6954.T",    # Fanuc - 工業機器人
        "7011.T",    # 三菱重工 - 航太國防
        "6503.T",    # 三菱電機 - 工業自動化
        "6752.T",    # Panasonic Holdings - 電池與家電
        "6273.T",    # SMC - 氣動元件
        "7201.T",    # 日產汽車 - 電動車
        "7203.T",    # 豐田汽車 - 電動車與氫能
        "7267.T",    # 本田汽車 - 電動車與機器人
        "7202.T",    # 五十鈴汽車
        "7205.T",    # 日野汽車
        "7259.T",    # Aisin - 汽車零組件
        "7261.T",    # Mazda
        "7269.T",    # Suzuki Motor
        
        # --- 生技與製藥 ---
        "4578.T",    # 大塚製藥 - 新藥
        "4523.T",    # 衛材 - 阿茲海默症藥物
        "4503.T",    # Astellas Pharma - 製藥
        "4502.T",    # 武田製藥 - 製藥
        "4568.T",    # 第一三共 - 製藥
        "4507.T",    # 鹽野義製藥
        "4506.T",    # 大日本住友製藥
        "4519.T",    # 中外製藥
        
        # --- 金融與綜合商社 ---
        "8306.T",    # 三菱 UFJ 金融集團
        "8316.T",    # 三井住友金融集團
        "8411.T",    # Mizuho 金融集團
        "8058.T",    # 三菱商事 - 綜合商社
        "8001.T",    # 伊藤忠商事 - 綜合商社
        "8002.T",    # 丸紅 - 綜合商社
        "8031.T",    # 三井物產 - 綜合商社
        "8053.T",    # 住友商事 - 綜合商社
        
        # --- 消費與零售 ---
        "9983.T",    # Fast Retailing (Uniqlo) - 零售
        "9984.T",    # SoftBank Group - 電信與投資
        "4755.T",    # 樂天集團 - 電商與金融科技
        "7453.T",    # 良品計畫 (無印良品)
        "7532.T",    # Don Quijote Holdings
        "9843.T",    # Nitori Holdings - 家居零售
        "3382.T",    # Seven & i Holdings - 便利商店
        "8267.T",    # Aeon - 零售集團
        
        # --- 其他重要企業 ---
        "6301.T",    # 小松製作所 - 工程機械
        "5108.T",    # 普利司通 - 輪胎
        "5201.T",    # AGC - 玻璃與化學
        "5332.T",    # TOTO - 衛浴設備
        "5401.T",    # 新日鐵住金 - 鋼鐵
        "5411.T",    # JFE Holdings - 鋼鐵
        "6302.T",    # 住友重機械 - 重工業
        "6326.T",    # Kubota - 農業機械
        "6367.T",    # Daikin Industries - 空調
        "6471.T",    # NSK - 軸承
        "9020.T",    # JR East - 鐵路
        "9433.T",    # KDDI - 電信
        "9437.T",    # NTT DoCoMo - 電信
    ],
    # endregion
    
    # region 🇰🇷 韓股：記憶體與顯示雙雄 (KR_MEMORY_DISPLAY)
    "KR_MEMORY_DISPLAY": [
        # --- 韓國半導體三巨頭 ---
        "005930.KS", # Samsung Electronics - 記憶體與晶圓代工
        "000660.KS", # SK Hynix - DRAM 與 NAND
        "042700.KS", # Hanmi Semiconductor - 半導體設備
        "068270.KS", # Celltrion - 生物製藥
        
        # --- 面板與顯示 ---
        "034220.KS", # LG Display - OLED 面板
        "009150.KS", # Samsung Display - 柔性 OLED (未上市，僅參考)
        
        # --- 電動車與電池 ---
        "373220.KS", # LG Energy Solution - 電池
        "096770.KS", # SK Innovation - 電池與化工
        "005380.KS", # 現代汽車 - 電動車
        "000270.KS", # 起亞汽車 - 電動車
        "012330.KS", # 現代 Mobis - 汽車零組件
        
        # --- 造船與重工 ---
        "009540.KS", # 韓國造船海洋 (前現代重工) - 造船
        "010140.KS", # 三星重工 - 造船
        "010620.KS", # 現代尾浦造船 - LNG 船
        
        # --- 韓國互聯網與遊戲 ---
        "035720.KS", # Kakao - 社群與金融科技
        "035420.KS", # Naver - 搜尋與電商
        "251270.KS", # Netmarble - 遊戲
        "036570.KS", # NCsoft - 遊戲
        "259960.KS", # Krafton - PUBG 遊戲
        "352820.KS", # Hybe (BTS 經紀公司) - 娛樂
        
        # --- 鋼鐵與化工 ---
        "005490.KS", # POSCO Holdings - 鋼鐵
        "051910.KS", # LG Chem - 化工與電池
        "009830.KS", # Hanwha Solutions - 化工與太陽能
        
        # --- 金融 ---
        "055550.KS", # 新韓金融集團
        "105560.KS", # KB 金融集團
        "086790.KS", # Hana Financial Group
        
        # --- 其他 ---
        "006400.KS", # 三星 SDI - 電池與材料
        "000810.KS", # Samsung Fire & Marine Insurance
        "018260.KS", # Samsung SDS - IT 服務
        "028260.KS", # Samsung C&T - 建設與貿易
    ],
    # endregion
    
    # region 🇨🇳 中國：破壞式創新與電動車 (CN_INNOVATION_EV)
    "CN_INNOVATION_EV": [
        # --- 中國電動車三巨頭 ---
        "NIO",       # 蔚來 - 高端電動車
        "XPEV",      # 小鵬汽車 - 智能電動車
        "LI",        # 理想汽車 - 增程式電動車
        
        # --- 電動車供應鏈 ---
        "BYDDY",     # 比亞迪 - 電動車與電池
        "1211.HK",   # 比亞迪 (港股)
        "2015.HK",   # 理想汽車 (港股)
        "9868.HK",   # 小鵬汽車 (港股)
        "9866.HK",   # 蔚來 (港股)
        
        # --- 互聯網與科技 ---
        "BABA",      # 阿里巴巴 - 電商與雲端
        "9988.HK",   # 阿里巴巴 (港股)
        "BIDU",      # 百度 - 搜尋與 AI
        "JD",        # 京東 - 電商
        "9618.HK",   # 京東 (港股)
        "TCEHY",     # 騰訊 (ADR)
        "0700.HK",   # 騰訊 (港股)
        "PDD",       # 拼多多 - 電商
        "MEITUAN",   # 美團 (港股 3690.HK)
        "3690.HK",   # 美團
        "BILI",      # 嗶哩嗶哩 - 視頻平台
        "9626.HK",   # 嗶哩嗶哩 (港股)
        
        # --- 電商與新零售 ---
        "BEKE",      # 貝殼找房 - 房地產科技
        "2423.HK",   # 貝殼 (港股)
        "YMM",       # 滿幫集團 - 貨運平台
        
        # --- 金融科技 ---
        "6690.HK",   # 海爾智家 (港股)
        "1810.HK",   # 小米集團 - 智能手機與 IoT
        
        # --- 其他 ---
        "EDU",       # 新東方教育
        "TAL",       # 好未來教育
        "NTES",      # 網易 - 遊戲
        "9999.HK",   # 網易 (港股)
        "WB",        # 微博
        "TME",       # 騰訊音樂娛樂
        "IQ",        # 愛奇藝 - 視頻平台
    ],
    # endregion
    
    # region 🌍 全球：新興市場成長股 (EMERGING_GROWTH)
    "EMERGING_GROWTH": [
        # --- 東南亞 ---
        "SE",        # Sea Limited - 東南亞電商與遊戲
        "GRAB",      # Grab Holdings - 東南亞叫車與金融
        "GOJEK",     # GoTo (印尼 - 未上市或合併)
        
        # --- 印度 ---
        "INFY",      # Infosys - IT 服務
        "WIT",       # Wipro - IT 服務
        "HDB",       # HDFC Bank - 印度銀行
        "RELIANCE.NS", # Reliance Industries (印度)
        "TCS.NS",    # Tata Consultancy Services
        
        # --- 拉丁美洲 ---
        "MELI",      # MercadoLibre - 拉美電商
        "NU",        # Nu Holdings - 巴西數位銀行
        "STNE",      # StoneCo - 巴西金融科技
        "PAGS",      # PagSeguro - 巴西支付
        "GLOB",      # Globo - 巴西媒體
        "VALE",      # 淡水河谷 - 巴西鐵礦
        "PBR",       # Petrobras - 巴西石油
        
        # --- 非洲 ---
        "JMIA",      # Jumia Technologies - 非洲電商
        
        # --- 以色列 ---
        "WDAY",      # Workday (雖為美國公司)
        "MNDY",      # Monday.com
        "NICE",      # Nice - 軟體
        "CYBR",      # CyberArk - 網路安全
        "CHKP",      # Check Point
        "WIX",       # Wix.com
    ],
    # endregion
}
