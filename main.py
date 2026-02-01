# main.py
# Titan SOP V40.5 - Commander Interface
# 狀態: 系統入口 (Entry Point)
# 功能: 提供 CLI 選單，一鍵啟動戰情室或執行回測

import os
import sys
import time
from backtest import TitanBacktestEngine
from config import Config

def print_banner():
    print(r"""
    =======================================================
       _______   _   __                   _____  ____  _____ 
      /_  __(_) | | / /___ _____         / ___/ / __ \/ __ \ 
       / / / /  | |/ / __ `/ __ \ ______ \__ \ / / / / /_/ / 
      / / / /   |   / /_/ / / / //_____/___/ // /_/ / ____/  
     /_/ /_/    |__/\__,_/_/ /_/       /____(_)____/_/       
                                                             
     Titan SOP V40.5 - 鄭思翰全自動戰情室 (War Room)
     "相信邏輯，嚴守紀律，擁抱 152 元中位數"
    =======================================================
    """)

def run_backtest():
    print("\n[啟動] 歷史回測引擎...")
    engine = TitanBacktestEngine()
    
    # 這裡可以讓使用者輸入代號，預設用種子池的一檔示範
    target = input("請輸入回測股票代號 (預設 3548.TW): ") or "3548.TW"
    
    print(f"\n[執行] 正在回測 {target} 的 SOP 績效...")
    print(f"       - 進場: 甜蜜點 < {Config.SWEET_SPOT_HIGH}")
    print(f"       - 出場: 目標價 > {Config.EXIT_TARGET_MEDIAN} 或 跌破 87MA")
    
    try:
        trades = engine.run_simulation(target, "User Choice")
        report, df = engine.generate_report(trades)
        print(report)
        if not df.empty:
            print("\n[詳細交易紀錄]")
            print(df[['entry_date', 'exit_price', 'roi', 'reason']].to_string())
    except Exception as e:
        print(f"❌ 回測失敗: {e}")
        
    input("\n按 Enter 返回主選單...")

def start_war_room():
    print("\n[啟動] Streamlit 戰情室介面...")
    print("正在開啟瀏覽器... (按 Ctrl+C 停止)")
    time.sleep(1)
    # 使用 os.system 呼叫 streamlit run
    os.system("streamlit run app.py")

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        print("1. 🚀 啟動戰情室 (Start War Room)")
        print("2. 🔙 執行歷史回測 (Run Backtest)")
        print("3. 📂 檢查數據狀態 (Check Data)")
        print("4. 🚪 離開 (Exit)")
        
        choice = input("\n請選擇指令 [1-4]: ")
        
        if choice == '1':
            start_war_room()
        elif choice == '2':
            run_backtest()
        elif choice == '3':
            print("\n數據庫路徑: full_sop_database.json")
            if os.path.exists("full_sop_database.json"):
                print("狀態: ✅ 已連結 (Online)")
            else:
                print("狀態: ❌ 未找到 (Offline)")
            input("\n按 Enter 返回...")
        elif choice == '4':
            print("再見，祝操作順利！")
            sys.exit()
        else:
            print("無效指令")
            time.sleep(0.5)

if __name__ == "__main__":
    main()```