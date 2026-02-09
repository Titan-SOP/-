# config_v89.py
# Titan SOP V89.0 - 創世紀與方舟全境獵殺庫 (Genesis & ARK Fusion)
# 設計日期: 2026-02-09
# 狀態: 最高法律效力
# 戰略目標: 尋找 2033 年的百倍股 - 實體生產力革命 × 破壞式創新

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
# [WAR_THEATERS] 全境獵殺七大戰區清單
# 設計日期: 2026-02-09
# ⚠️ 警語: 本名單為針對 2033 景氣循環設計。
# ⚠️ 規定: 必須每半年 (6個月) 檢視並更新一次成分股，以確保符合最新產業趨勢。
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
        
        # --- ARK Genomic Revolution (ARKG) ---
        "CRSP",   # CRISPR Therapeutics - 基因編輯
        "NTLA",   # Intellia Therapeutics - 基因編輯
        "EDIT",   # Editas Medicine - 基因編輯
        "BEAM",   # Beam Therapeutics - 鹼基編輯
        "TXG",    # 10x Genomics - 基因定序
        "DNA",    # Ginkgo Bioworks - 合成生物學
        "PACB",   # Pacific Biosciences - 長讀長定序
        "NVTA",   # Invitae - 基因檢測
        "SDGR",   # Schrodinger - AI 藥物發現
        "EXAS",   # Exact Sciences - 癌症篩檢
        "FATE",   # Fate Therapeutics - 細胞療法
        "PSNL",   # Personalis - 精準醫療
        "IONS",   # Ionis Pharmaceuticals - RNA 療法
        "VERV",   # Verve Therapeutics - 基因編輯心血管
        "CDNA",   # CareDx - 器官移植監測
        "TWST",   # Twist Bioscience - DNA 合成
        
        # --- ARK Autonomous & Robotics (ARKQ) ---
        "ISRG",   # Intuitive Surgical - 手術機器人
        "AVAV",   # AeroVironment - 無人機
        "KTOS",   # Kratos Defense - 無人戰機
        "BLDE",   # Blade Air Mobility - 電動垂直起降
        "ACHR",   # Archer Aviation - eVTOL
        "JOBY",   # Joby Aviation - 空中計程車
        "TRMB",   # Trimble - 精準定位
        "KMTUY",  # Komatsu - 自動化工程機械
        
        # --- ARK Space Exploration (ARKX) ---
        "IRDM",   # Iridium - 衛星通訊
        "GRMN",   # Garmin - GPS 導航
        "LHX",    # L3Harris - 航太國防
        "VUZI",   # Vuzix - AR 眼鏡
        
        # --- ARK Fintech Innovation (ARKF) ---
        "AFRM",   # Affirm - 先買後付
        "MELI",   # MercadoLibre - 拉美電商
        "NU",     # Nu Holdings - 巴西數位銀行
        "PYPL",   # PayPal - 數位支付
        "MARA",   # Marathon Digital - 比特幣挖礦
        "RIOT",   # Riot Platforms - 比特幣挖礦
        
        # --- Next-Gen Internet & Software ---
        "SNOW",   # Snowflake - 雲端數據倉儲
        "DDOG",   # Datadog - 雲端監控
        "NET",    # Cloudflare - 邊緣運算
        "GTLB",   # GitLab - DevOps 平台
        "MDB",    # MongoDB - NoSQL 資料庫
        "ZS",     # Zscaler - 雲端安全
        "OKTA",   # Okta - 身份驗證
        "DOCN",   # DigitalOcean - 雲端基礎設施
        "BILL",   # Bill.com - 企業支付
        "S",      # SentinelOne - AI 網路安全
        
        # --- 3D Printing & Advanced Manufacturing ---
        "DM",     # Desktop Metal - 3D 列印
        "NNDM",   # Nano Dimension - 電子 3D 列印
        "MTTR",   # Matterport - 3D 空間掃描
    ],
    # endregion
    
    # region 🇺🇸 美股：創世紀實體建設 (US_GENESIS_PHYSICAL)
    "US_GENESIS_PHYSICAL": [
        # --- 核能與 AI 電力基建 (AI Power Revolution) ---
        "OKLO",   # Oklo - 微型核反應爐
        "NNE",    # Nano Nuclear Energy - 微型核電
        "SMR",    # NuScale Power - 小型模組化反應爐
        "BWXT",   # BWX Technologies - 核能組件
        "CEG",    # Constellation Energy - 核電營運
        "VST",    # Vistra - 核電與天然氣
        "FLR",    # Fluor - 核電工程
        "LUCK",   # Luckstone - 數據中心建設
        "CCJ",    # Cameco - 鈾礦開採
        "UEC",    # Uranium Energy - 鈾礦
        "UUUU",   # Energy Fuels - 鈾與稀土
        "DNN",    # Denison Mines - 鈾礦
        "LEU",    # Centrus Energy - 核燃料
        
        # --- 次世代算力基礎設施 (Next-Gen Compute Infra) ---
        "SMCI",   # Super Micro Computer - AI 伺服器
        "VRT",    # Vertiv - 數據中心冷卻與電力
        "ANET",   # Arista Networks - 數據中心網路
        "PSTG",   # Pure Storage - 全快閃儲存
        "CVLT",   # CommVault - 數據備份
        "NTAP",   # NetApp - 混合雲儲存
        "STX",    # Seagate - 硬碟儲存
        "WDC",    # Western Digital - 儲存設備
        
        # --- 光通訊與矽光子 (Optical Interconnect) ---
        "LITE",   # Lumentum - 雷射與光學
        "COHR",   # Coherent - 雷射與光學材料
        "IOSP",   # Innospec - 光學塗層
        "CIEN",   # Ciena - 光纖網路設備
        "INFN",   # Infinera - 光傳輸系統
        "JNPR",   # Juniper Networks - 網路設備
        "AAOI",   # Applied Optoelectronics - 光纖收發器
        
        # --- 機器人與自動化 (Embodied AI) ---
        "ROK",    # Rockwell Automation - 工業自動化
        "IRBT",   # iRobot - 掃地機器人
        "TER",    # Teradyne - 半導體測試機器人
        "GRMN",   # Garmin - 自動駕駛感測器
        "SYM",    # Symbotic - 倉儲自動化
        "EMR",    # Emerson Electric - 自動化設備
        "PH",     # Parker Hannifin - 運動控制
        "ITW",    # Illinois Tool Works - 工業設備
        
        # --- 量子運算 (Quantum Computing) ---
        "IONQ",   # IonQ - 離子阱量子電腦
        "RGTI",   # Rigetti Computing - 超導量子電腦
        "QUBT",   # Quantum Computing Inc - 量子軟體
        
        # --- 太空基建 (Space Infrastructure) ---
        "RKLB",   # Rocket Lab - 小型衛星發射
        "ASTS",   # AST SpaceMobile - 衛星直連手機
        "LUNR",   # Intuitive Machines - 月球登陸器
        "PL",     # Planet Labs - 地球影像衛星
        "SPIR",   # Spire Global - 衛星數據分析
        "SPCE",   # Virgin Galactic - 太空旅遊
        "MAXR",   # Maxar Technologies - 衛星影像
        "SATS",   # EchoStar - 衛星通訊
        
        # --- 先進材料與電池 (Advanced Materials) ---
        "ALB",    # Albemarle - 鋰礦
        "SQM",    # Sociedad Química - 鋰礦
        "LAC",    # Lithium Americas - 鋰礦
        "MP",     # MP Materials - 稀土
        "NOVLF",  # Nova Lithium - 鋰礦勘探
        "QS",     # QuantumScape - 固態電池
        "STEM",   # Stem Inc - 儲能系統
        "FCEL",   # FuelCell Energy - 燃料電池
        "PLUG",   # Plug Power - 氫能源
        "BLDP",   # Ballard Power - 氫燃料電池
        
        # --- AI 晶片代工與設備 (AI Chip Ecosystem) ---
        "ASML",   # ASML - EUV 光刻機
        "LRCX",   # Lam Research - 刻蝕設備
        "KLAC",   # KLA Corporation - 檢測設備
        "AMAT",   # Applied Materials - 半導體設備
        "ENTG",   # Entegris - 半導體材料
        "MKSI",   # MKS Instruments - 真空設備
    ],
    # endregion
    
    # region 🇺🇸 美股：羅素成長精選 (US_RUSSELL_GROWTH)
    "US_RUSSELL_GROWTH": [
        # --- Russell 2000 科技成長股 (高成交量前 200) ---
        # 軟體與雲端
        "QTWO",   # Q2 Holdings - 數位銀行軟體
        "BL",     # BlackLine - 財務自動化
        "ALKT",   # Alkami Technology - 數位銀行
        "ESTC",   # Elastic - 搜尋與分析
        "FROG",   # JFrog - DevOps 軟體
        "NCNO",   # nCino - 銀行軟體
        "APPF",   # AppFolio - 物業管理軟體
        "RPD",    # Rapid7 - 網路安全
        "TENB",   # Tenable - 網路安全
        "QLYS",   # Qualys - 雲端安全
        "VRNS",   # Varonis - 數據安全
        "CYBR",   # CyberArk - 特權存取管理
        "PANW",   # Palo Alto Networks - 網路安全
        
        # 半導體與硬體
        "RMBS",   # Rambus - 記憶體晶片
        "SMTC",   # Semtech - 類比半導體
        "MPWR",   # Monolithic Power - 電源管理
        "WOLF",   # Wolfspeed - 碳化矽半導體
        "CRUS",   # Cirrus Logic - 音訊晶片
        "SWKS",   # Skyworks - RF 晶片
        "QRVO",   # Qorvo - RF 解決方案
        "MTSI",   # MACOM - RF 半導體
        "SLAB",   # Silicon Labs - IoT 晶片
        "HIMX",   # Himax - 顯示驅動晶片
        "AMBA",   # Ambarella - AI 視覺晶片
        "CEVA",   # CEVA - 無線與 AI IP
        "HLIT",   # Harmonic - 視訊編碼晶片
        
        # 生技與醫療
        "NVAX",   # Novavax - mRNA 疫苗
        "MRNA",   # Moderna - mRNA 療法
        "VRTX",   # Vertex Pharmaceuticals - 基因療法
        "BMRN",   # BioMarin - 罕見疾病療法
        "ALNY",   # Alnylam - RNA 干擾療法
        "SGEN",   # Seagen - 抗體藥物偶聯
        "REGN",   # Regeneron - 單株抗體
        "INCY",   # Incyte - 癌症免疫療法
        "JAZZ",   # Jazz Pharmaceuticals - 睡眠障礙藥物
        "UTHR",   # United Therapeutics - 肺動脈高壓
        "FOLD",   # Amicus Therapeutics - 酵素替代療法
        "IMMU",   # Immunomedics - 癌症療法
        "BGNE",   # BeiGene - 癌症藥物
        "HZNP",   # Horizon Therapeutics - 罕見疾病
        
        # 電動車與新能源
        "RIVN",   # Rivian - 電動卡車
        "LCID",   # Lucid Motors - 電動豪華車
        "NKLA",   # Nikola - 電動卡車與氫能
        "CHPT",   # ChargePoint - 充電樁網路
        "BLNK",   # Blink Charging - 充電設備
        "EVGO",   # EVgo - 快速充電網路
        "FSLY",   # Fastly - 邊緣運算 CDN
        
        # 金融科技
        "LPRO",   # Open Lending - AI 信貸承保
        "UPST",   # Upstart - AI 信貸平台
        "LCII",   # LCI Industries - RV 零組件
        "PAYO",   # Payoneer - 跨境支付
        "FOUR",   # Shift4 Payments - 支付處理
        "GPN",    # Global Payments - 支付處理
        
        # 工業與自動化
        "PII",    # Polaris - 越野車輛
        "HOG",    # Harley-Davidson - 電動摩托車
        "GNTX",   # Gentex - 車用電子後視鏡
        "ADNT",   # Adient - 汽車座椅
        "LEA",    # Lear - 汽車電子系統
        "VC",     # Visteon - 車用資訊娛樂
        "APTV",   # Aptiv - 自動駕駛技術
        
        # 零售與消費科技
        "CHWY",   # Chewy - 寵物電商
        "W",      # Wayfair - 家具電商
        "ETSY",   # Etsy - 手工藝品平台
        "CVNA",   # Carvana - 線上二手車
        "BBWI",   # Bath & Body Works - 美妝零售
        "BURL",   # Burlington Stores - 折扣零售
        
        # 能源科技
        "RUN",    # Sunrun - 住宅太陽能
        "ENPH",   # Enphase - 太陽能逆變器
        "SEDG",   # SolarEdge - 太陽能優化器
        "NOVA",   # Sunnova - 太陽能融資
        "ARRY",   # Array Technologies - 太陽能追蹤器
        
        # 數據與分析
        "NEWR",   # New Relic - 應用監控
        "SUMO",   # Sumo Logic - 日誌分析
        "SPLK",   # Splunk - 數據分析
        "ZI",     # ZoomInfo - B2B 數據庫
        
        # 通訊與娛樂
        "SIRI",   # SiriusXM - 衛星廣播
        "MSGS",   # Madison Square Garden Sports
        "FUBO",   # fuboTV - 體育串流
        "TMDX",   # TransMedics - 器官移植保存
    ],
    # endregion
    
    # region 🇺🇸 美股：科技巨頭與半導體 (US_TECH_CORE)
    "US_TECH_CORE": [
        # --- MAG7 科技巨頭 ---
        "AAPL",   # Apple
        "MSFT",   # Microsoft
        "GOOGL",  # Alphabet (Google) - Class A
        "GOOG",   # Alphabet (Google) - Class C
        "AMZN",   # Amazon
        "NVDA",   # NVIDIA
        "META",   # Meta (Facebook)
        "TSLA",   # Tesla
        
        # --- SOX 費城半導體指數完整成分股 ---
        "NVDA",   # NVIDIA - GPU 與 AI 晶片
        "AVGO",   # Broadcom - 數據中心晶片
        "TSM",    # TSMC - 晶圓代工
        "ASML",   # ASML - EUV 光刻機
        "AMD",    # AMD - CPU 與 GPU
        "TXN",    # Texas Instruments - 類比晶片
        "INTC",   # Intel - CPU 與代工
        "QCOM",   # Qualcomm - 手機晶片
        "ADI",    # Analog Devices - 類比晶片
        "AMAT",   # Applied Materials - 半導體設備
        "LRCX",   # Lam Research - 刻蝕設備
        "KLAC",   # KLA - 檢測設備
        "MRVL",   # Marvell - 數據中心晶片
        "NXPI",   # NXP - 車用半導體
        "MU",     # Micron - 記憶體
        "MCHP",   # Microchip - 微控制器
        "SNPS",   # Synopsys - EDA 軟體
        "CDNS",   # Cadence - EDA 軟體
        "ON",     # ON Semiconductor - 功率半導體
        "MPWR",   # Monolithic Power - 電源管理
        "ENTG",   # Entegris - 半導體材料
        "MKSI",   # MKS Instruments - 製程設備
        "SWKS",   # Skyworks - RF 晶片
        "QRVO",   # Qorvo - RF 晶片
        "GFS",    # GlobalFoundries - 晶圓代工
        
        # --- 雲端與企業軟體巨頭 ---
        "CRM",    # Salesforce - CRM 軟體
        "ORCL",   # Oracle - 企業資料庫
        "ADBE",   # Adobe - 創意軟體
        "NOW",    # ServiceNow - IT 服務管理
        "INTU",   # Intuit - 財務軟體
        "WDAY",   # Workday - 人力資源軟體
        "TEAM",   # Atlassian - 協作軟體
        "PANW",   # Palo Alto Networks - 網路安全
        "CRWD",   # CrowdStrike - 端點安全
        "ZS",     # Zscaler - 零信任安全
        "FTNT",   # Fortinet - 網路安全
        
        # --- 電商與數位支付 ---
        "BABA",   # Alibaba - 中國電商
        "JD",     # JD.com - 中國電商
        "PDD",    # Pinduoduo - 中國社交電商
        "MELI",   # MercadoLibre - 拉美電商
        "V",      # Visa - 支付網路
        "MA",     # Mastercard - 支付網路
        "PYPL",   # PayPal - 數位支付
        
        # --- 社群媒體與串流 ---
        "NFLX",   # Netflix - 串流影音
        "DIS",    # Disney - 娛樂與串流
        "SPOT",   # Spotify - 音樂串流
        "SNAP",   # Snap - 社群媒體
        "PINS",   # Pinterest - 圖片社群
        "RDDT",   # Reddit - 社群論壇
    ],
    # endregion
    
    # region 🇹🇼 台股：矽島戰略全境 (TW_ALL_STARS)
    "TW_ALL_STARS": [
        # --- 矽盾核心 (Silicon Shield Core) ---
        "2330.TW",   # 台積電 - 晶圓代工龍頭
        "2454.TW",   # 聯發科 - 手機晶片
        "2317.TW",   # 鴻海 - 電子代工
        "2382.TW",   # 廣達 - 伺服器代工
        "2308.TW",   # 台達電 - 電源管理
        "2303.TW",   # 聯電 - 晶圓代工
        "3711.TW",   # 日月光 - 封測
        "2379.TW",   # 瑞昱 - 網路晶片
        "2408.TW",   # 南亞科 - DRAM
        "3034.TW",   # 聯詠 - 面板驅動晶片
        "2409.TW",   # 友達 - 面板
        "2327.TW",   # 國巨 - 被動元件
        "2313.TW",   # 華通 - PCB
        
        # --- 矽光子 / CPO / 高速傳輸 (Silicon Photonics) ---
        "3363.TW",   # 上詮 - 光通訊元件
        "3450.TW",   # 聯鈞 - 連接器
        "3163.TW",   # 波若威 - 光通訊
        "4979.TW",   # 華星光 - 光通訊元件
        "6442.TW",   # 光聖 - 光學鍍膜
        "3443.TW",   # 創意 - ASIC 設計
        "3081.TW",   # 聯亞 - 光學元件
        "6285.TW",   # 啟碁 - 網通設備
        "2449.TW",   # 京元電 - 測試
        "3036.TW",   # 文曄 - IC 通路
        "6216.TW",   # 居易 - 網通晶片
        
        # --- AI 伺服器 / 散熱 / CoWoS (AI Server Ecosystem) ---
        "3017.TW",   # 奇鋐 - 散熱模組
        "3324.TW",   # 雙鴻 - 散熱
        "2421.TW",   # 建準 - 散熱風扇
        "2059.TW",   # 川湖 - 散熱鉸鏈
        "3231.TW",   # 緯創 - 伺服器代工
        "6669.TW",   # 緯穎 - AI 伺服器
        "2356.TW",   # 英業達 - 伺服器
        "6116.TW",   # 彩晶 - 面板
        "3693.TW",   # 營邦 - 散熱
        "6230.TW",   # 超眾 - HDI PCB
        "8210.TW",   # 勤誠 - 散熱
        "3653.TW",   # 健策 - 齒輪箱散熱
        "3013.TW",   # 晟銘電 - 散熱
        "6196.TW",   # 帆宣 - 廠務工程
        "6187.TW",   # 萬潤 - 半導體設備零組件
        "3583.TW",   # 辛耘 - 半導體設備
        "3680.TW",   # 家登 - 半導體載具
        "6271.TW",   # 同欣電 - 半導體通路
        "3037.TW",   # 欣興 - ABF 載板
        
        # --- 重電 & 綠能 (Heavy Electric & Green Energy) ---
        "1513.TW",   # 中興電 - 重電工程
        "1519.TW",   # 華城 - 電力設備
        "1503.TW",   # 士電 - 變壓器
        "1504.TW",   # 東元 - 馬達與電機
        "6806.TW",   # 森崴能源 - 綠能電廠
        "1605.TW",   # 華新 - 電纜
        "1609.TW",   # 大亞 - 電纜
        "1618.TW",   # 合機 - 工業用電機
        "2371.TW",   # 大同 - 重電
        "3023.TW",   # 信邦 - 電纜連接器
        "6449.TW",   # 鈺邦 - 太陽能逆變器
        "6482.TW",   # 弘煜科 - 太陽能電池
        "8996.TW",   # 高力 - 散熱與風扇
        "1589.TW",   # 永冠-KY - 風電齒輪箱
        "6508.TW",   # 惠光 - 化工材料
        
        # --- 機器人 & 自動化 (Robotics & Automation) ---
        "2049.TW",   # 上銀 - 精密機械
        "1590.TW",   # 亞德客-KY - 氣動元件
        "1597.TW",   # 直得 - 滾珠螺桿
        "6414.TW",   # 樺漢 - 工業電腦
        "2359.TW",   # 所羅門 - 3D 視覺檢測
        "8033.TW",   # 雷虎 - 無人機
        "4540.TW",   # 全宇生技-KY - 醫療自動化
        "5443.TW",   # 均豪 - 半導體自動化設備
        "6166.TW",   # 凌華 - 工業電腦
        "8374.TW",   # 羅昇 - 精密加工
        
        # --- 電動車 & 車用電子 (EV & Auto Electronics) ---
        "2207.TW",   # 和泰車 - 汽車經銷
        "2201.TW",   # 裕隆 - 汽車製造
        "2204.TW",   # 中華 - 汽車製造
        "1514.TW",   # 亞力 - 汽車電子
        "2316.TW",   # 楠梓電 - IC 載板
        "1560.TW",   # 中砂 - 砂輪研磨
        "6508.TW",   # 惠光 - 車用化學材料
        "1229.TW",   # 聯華 - 輪胎
        
        # --- 5G & 通訊設備 (5G & Telecom) ---
        "2474.TW",   # 可成 - 金屬機殼
        "3034.TW",   # 聯詠 - 驅動晶片
        "6205.TW",   # 詮欣 - 網通晶片代理
        "3005.TW",   # 神基 - 強固型電腦
        "2345.TW",   # 智邦 - 網通設備
        "2412.TW",   # 中華電 - 電信營運
        "4904.TW",   # 遠傳 - 電信營運
        "4906.TW",   # 正文 - 網通設備
        "3252.TW",   # 海灣 - 網通
        
        # --- 半導體材料 & 特化 (Semiconductor Materials) ---
        "6121.TW",   # 新普 - 電池模組
        "6239.TW",   # 力成 - 封測
        "3707.TW",   # 漢磊 - 晶圓代工
        "6770.TW",   # 力積電 - DRAM 代工
        "5347.TW",   # 世界 - IC 通路
        "3532.TW",   # 台勝科 - 矽晶圓
        "5483.TW",   # 中美晶 - 矽晶圓與太陽能
        "3562.TW",   # 頂晶科 - 藍寶石基板
        "4966.TW",   # 譜瑞-KY - 高速傳輸晶片
        "8016.TW",   # 矽創 - 面板驅動晶片
        "6257.TW",   # 矽格 - 封測
        
        # --- 醫療器材 & 生技 (Medical Devices & Biotech) ---
        "4142.TW",   # 國光生 - 疫苗
        "4108.TW",   # 懷特 - 新藥
        "4114.TW",   # 健喬 - 學名藥
        "1789.TW",   # 神隆 - 原料藥
        "1760.TW",   # 寶齡富錦 - 製藥
        "4133.TW",   # 亞諾法 - 原料藥
        "1785.TW",   # 光洋科 - 醫材
        "4147.TW",   # 中裕 - 新藥
        "6535.TW",   # 順藥 - 學名藥
        
        # --- 國防 & 軍工 (Defense & Aerospace) ---
        "2206.TW",   # 三陽工業 - 機車與國防
        "9942.TW",   # 茂順 - 密封元件
        "1264.TW",   # 德麥 - 烘焙設備（金屬加工）
        "2642.TW",   # 宅配通 - 物流
        
        # --- 化工 & 材料 (Chemicals & Materials) ---
        "1303.TW",   # 南亞 - 塑化
        "1326.TW",   # 台化 - 石化
        "1301.TW",   # 台塑 - 石化
        "6505.TW",   # 台塑化 - 石化
        "1402.TW",   # 遠東新 - 化纖
        "1409.TW",   # 新纖 - 化纖
        "1476.TW",   # 儒鴻 - 機能布料
        "1707.TW",   # 葡萄王 - 生技保健
        
        # --- 金融保險 (Finance & Insurance) ---
        "2881.TW",   # 富邦金 - 金控
        "2882.TW",   # 國泰金 - 金控
        "2886.TW",   # 兆豐金 - 金控
        "2891.TW",   # 中信金 - 金控
        "2892.TW",   # 第一金 - 金控
        "2884.TW",   # 玉山金 - 金控
        "2885.TW",   # 元大金 - 金控
        "2887.TW",   # 台新金 - 金控
        "2888.TW",   # 新光金 - 金控
        "2890.TW",   # 永豐金 - 金控
        "5880.TW",   # 合庫金 - 金控
        
        # --- 傳產龍頭 (Traditional Industries) ---
        "2002.TW",   # 中鋼 - 鋼鐵
        "2603.TW",   # 長榮 - 海運
        "2609.TW",   # 陽明 - 海運
        "2615.TW",   # 萬海 - 海運
        "2610.TW",   # 華航 - 航空
        "2618.TW",   # 長榮航 - 航空
        "1101.TW",   # 台泥 - 水泥
        "1216.TW",   # 統一 - 食品
        "1301.TW",   # 台塑 - 塑化
        "9904.TW",   # 寶成 - 製鞋
        "9910.TW",   # 豐泰 - 製鞋
        
        # ===== 上櫃精選 (TPEx Growth Stars) =====
        
        # --- IP 矽智財 & ASIC (IP & ASIC Design) ---
        "5274.TWO",  # 信驊 - BMC 晶片設計
        "6643.TWO",  # M31 - 矽智財
        "3035.TWO",  # 智原 - ASIC 設計
        "3529.TWO",  # 力旺 - 矽智財 (NeoBit)
        "3443.TWO",  # 創意 - ASIC 設計 (已移轉上市，保留歷史代碼)
        "6531.TWO",  # 愛普 - ASIC 設計
        "6533.TWO",  # 晶心科 - RISC-V 處理器 IP
        "3661.TWO",  # 世芯-KY - ASIC 設計
        "6695.TWO",  # 芯鼎 - AI 影像晶片
        "6742.TWO",  # 澤米 - 影像處理晶片
        "6859.TWO",  # 動耐 - 車用 IC 設計
        
        # --- 高速傳輸 & 光通訊 (High-Speed & Optical) ---
        "4966.TWO",  # 譜瑞-KY - DisplayPort/USB 晶片
        "6469.TWO",  # 大樹 - 網路交換器晶片
        "3363.TWO",  # 上詮 - 光通訊元件
        "6274.TWO",  # 台燿 - HDI PCB
        "6482.TWO",  # 弘煜科 - 太陽能
        "5287.TWO",  # 數字 - 工業電腦
        
        # --- 半導體設備 & 零組件 (Semiconductor Equipment) ---
        "6187.TWO",  # 萬潤 - 半導體設備零組件
        "3521.TWO",  # 鴻翊 - 半導體設備
        "6488.TWO",  # 環球晶 - 矽晶圓 (已移轉上市)
        "3707.TWO",  # 漢磊 - 晶圓代工
        "6182.TWO",  # 合晶 - 矽晶圓再生
        "8054.TWO",  # 安國 - 記憶體控制晶片
        "6216.TWO",  # 居易 - 網通晶片
        "6274.TWO",  # 台燿 - HDI PCB
        "6698.TWO",  # 旭暉應材 - 半導體材料
        
        # --- 生技新藥 & 精準醫療 (Biotech & Precision Medicine) ---
        "6446.TWO",  # 藥華藥 - 新藥 (P1101)
        "6472.TWO",  # 保瑞 - 學名藥
        "4162.TWO",  # 智擎 - 癌症新藥
        "4147.TWO",  # 中裕 - HIV 新藥
        "4745.TWO",  # 合富-KY - 醫美保養品
        "6547.TWO",  # 高端疫苗 - 疫苗開發
        "6589.TWO",  # 台康生技 - 生物相似藥
        "4120.TWO",  # 友華 - 學名藥
        "4123.TWO",  # 晟德 - 製藥
        "4192.TWO",  # 杏國 - 新藥
        "6496.TWO",  # 科懋 - 原料藥
        "6535.TWO",  # 順藥 - 學名藥
        "4167.TWO",  # 展旺 - 醫材
        "6657.TWO",  # 華安 - 醫材
        "6875.TWO",  # 永紳 - 醫材
        "4728.TWO",  # 雙美 - 醫美
        "4743.TWO",  # 合一 - 新藥
        
        # --- 電動車 & 車用電子 (櫃買) ---
        "3490.TWO",  # 單井 - 車用馬達
        "6411.TWO",  # 晶焱 - 車用 IC 保護元件
        "6561.TWO",  # 是方 - 數據中心
        "6568.TWO",  # 宏觀 - 微投影
        
        # --- 工業自動化 & 精密機械 ---
        "4966.TWO",  # 譜瑞-KY - 高速傳輸
        "3296.TWO",  # 勝德 - 化工薄膜
        "5272.TWO",  # 笙科 - RF 晶片
        "5274.TWO",  # 信驊 - BMC
        "5278.TWO",  # 尚凡 - IoT 晶片
        "5289.TWO",  # 宜鼎 - 工業級儲存
        "6169.TWO",  # 昱泉 - 工業電腦
        "6425.TWO",  # 易發 - 工業自動化
        
        # --- 櫃買其他潛力股 ---
        "3064.TWO",  # 泰偉 - 電源供應器
        "3152.TWO",  # 璟德 - 電子材料
        "3229.TWO",  # 晟鈦 - 石英元件
        "3296.TWO",  # 勝德 - 化工薄膜
        "3346.TWO",  # 麗清 - 光學鏡頭
        "3498.TWO",  # 陽程 - PCB
        "3707.TWO",  # 漢磊 - 晶圓代工
        "4903.TWO",  # 聯光通 - 光通訊
        "4924.TWO",  # 欣厚-KY - 電子材料
        "4934.TWO",  # 太極 - 能源管理
        "4945.TWO",  # 新揚科 - 半導體設備
        "4979.TWO",  # 華星光 - 光通訊
        "5243.TWO",  # 乙盛-KY - 電子材料
        "5259.TWO",  # 清惠 - 工業電腦
        "5276.TWO",  # 達輝-KY - 電源管理
        "5284.TWO",  # jpp-KY - 被動元件
        "5305.TWO",  # 敦南 - IC 通路
        "5321.TWO",  # 友銓 - 檢測設備
        "5340.TWO",  # 建榮 - PCB 設備
        "5388.TWO",  # 中磊 - 網通設備
        "5425.TWO",  # 台半 - 功率半導體
        "5450.TWO",  # 寶聯通 - 網通設備
        "5457.TWO",  # 宣德 - 工業電腦
        "5464.TWO",  # 霖宏 - 散熱
        "5474.TWO",  # 聰泰 - 觸控晶片
        "5475.TWO",  # 德宏 - 車用電子
        "5478.TWO",  # 智冠 - 遊戲
        "5484.TWO",  # 慧友 - 監控軟體
        "5514.TWO",  # 三豐 - 電子材料
        "6112.TWO",  # 聚碩 - 觸控面板
        "6115.TWO",  # 鎰勝 - 金屬機殼
        "6126.TWO",  # 信音 - 電源供應器
        "6148.TWO",  # 驊宏資 - IC 測試
        "6150.TWO",  # 撼訊 - 顯示卡
        "6152.TWO",  # 百一 - 電子材料
        "6158.TWO",  # 禾昌 - 被動元件
        "6173.TWO",  # 信昌電 - 電子零組件
        "6179.TWO",  # 亞通 - PCB
        "6191.TWO",  # 精成科 - 光學鍍膜
        "6197.TWO",  # 佳必琪 - 散熱
        "6213.TWO",  # 聯茂 - CCL 銅箔基板
        "6220.TWO",  # 岳豐 - 紡織
        "6244.TWO",  # 茂迪 - 太陽能
        "6261.TWO",  # 久元 - PCB 設備
        "6279.TWO",  # 胡連 - 連接器
        "6405.TWO",  # 悅城 - 不動產
        "6409.TWO",  # 旭隼 - 精密機械
        "6412.TWO",  # 群電 - 電源供應器
        "6426.TWO",  # 統新 - 光電元件
        "6449.TWO",  # 鈺邦 - 太陽能逆變器
        "6456.TWO",  # GIS-KY - 觸控面板
        "6541.TWO",  # 泰福-KY - 生技
        "6568.TWO",  # 宏觀 - 微投影
        "6573.TWO",  # 虹揚-KY - 光通訊
        "6625.TWO",  # 必應 - 電源管理
        "6641.TWO",  # 基士德-KY - 車用電子
        "6668.TWO",  # 中揚光 - 光學元件
        "6679.TWO",  # 鈺太 - 晶圓測試
        "6706.TWO",  # 惠特 - PCB
        "6741.TWO",  # 91APP-KY - 電商 SaaS
        "6767.TWO",  # 台微體 - 免疫療法
        "6790.TWO",  # 永豐實 - 鋁擠型
        "8027.TWO",  # 鈦昇 - 金屬加工
        "8040.TWO",  # 九暘 - 紡織
        "8043.TWO",  # 蜜望實 - 化工
        "8044.TWO",  # 網家 - 電商
        "8050.TWO",  # 廣積 - 工業電腦
        "8064.TWO",  # 東捷 - 自動化物流
        "8070.TWO",  # 長華 - 材料分析
        "8074.TWO",  # 鉅橡 - 橡膠
        "8076.TWO",  # 伍豐 - 色譜儀
        "8084.TWO",  # 巨虹 - LED
        "8088.TWO",  # 品安 - 醫療器材
        "8091.TWO",  # 翔名 - 連接器
        "8096.TWO",  # 擎亞 - 電子材料
    ],
    # endregion
    
    # region 🇯🇵 日股：失落三十年復甦精選 (JP_REVIVAL_CORE)
    "JP_REVIVAL_CORE": [
        # --- 日本半導體復興 (Semiconductor Revival) ---
        "6920.T",    # 雷射技術 - Lasertec (EUV 檢測設備)
        "6857.T",    # Advantest - 半導體測試設備
        "8035.T",    # 東京威力科創 - 半導體設備
        "6501.T",    # 日立 - 工業自動化與能源
        "6594.T",    # 日本電產 - 馬達與精密機械
        "6981.T",    # 村田製作所 - 電子零組件
        "6758.T",    # Sony - 影像感測器與娛樂
        "7203.T",    # 豐田 - 電動車與氫能
        "6503.T",    # 三菱電機 - 工業自動化
        "6902.T",    # Denso - 汽車電子
        "6952.T",    # Casio - 精密機械
        "7201.T",    # 日產 - 電動車
        "7267.T",    # 本田 - 電動車與機器人
        "6702.T",    # 富士通 - 雲端與 AI
        "6723.T",    # Renesas - 車用半導體
        "4063.T",    # 信越化學 - 半導體材料
        "4005.T",    # 住友化學 - 電子材料
        
        # --- 日本機器人與自動化 ---
        "6954.T",    # Fanuc - 工業機器人
        "7011.T",    # 三菱重工 - 航太國防
        "7012.T",    # 川崎重工 - 機器人與航太
        "6752.T",    # Panasonic - 電池與家電
        "4578.T",    # 大塚製藥 - 新藥
        "4523.T",    # 衛材 - 阿茲海默症藥物
        
        # --- 日本金融與綜合商社 ---
        "8306.T",    # 三菱 UFJ - 金融
        "8316.T",    # 三井住友 - 金融
        "8058.T",    # 三菱商事 - 綜合商社
        "8001.T",    # 伊藤忠 - 綜合商社
        "8002.T",    # 丸紅 - 綜合商社
        "9983.T",    # Fast Retailing (Uniqlo) - 零售
        "9984.T",    # SoftBank - 電信與投資
        "4755.T",    # 樂天 - 電商與金融科技
    ],
    # endregion
    
    # region 🇰🇷 韓股：記憶體與面板雙雄 (KR_MEMORY_DISPLAY)
    "KR_MEMORY_DISPLAY": [
        # --- 韓國半導體三巨頭 ---
        "005930.KS", # Samsung Electronics - 記憶體與晶圓代工
        "000660.KS", # SK Hynix - DRAM 與 NAND
        "042700.KS", # Hanmi Semiconductor - 半導體設備
        
        # --- 面板與顯示 ---
        "034220.KS", # LG Display - OLED 面板
        "009150.KS", # Samsung Display - 柔性 OLED
        
        # --- 電動車與電池 ---
        "373220.KS", # LG Energy Solution - 電池
        "096770.KS", # SK Innovation - 電池與化工
        "005380.KS", # 現代汽車 - 電動車
        "000270.KS", # 起亞汽車 - 電動車
        
        # --- 造船與重工 ---
        "009540.KS", # 現代重工 - 造船
        "010140.KS", # 三星重工 - 造船
        "010620.KS", # 現代尾浦造船 - LNG 船
        
        # --- 韓國互聯網與遊戲 ---
        "035720.KS", # Kakao - 社群與金融科技
        "035420.KS", # Naver - 搜尋與電商
        "251270.KS", # Netmarble - 遊戲
        "036570.KS", # NCsoft - 遊戲
    ],
    # endregion
}
