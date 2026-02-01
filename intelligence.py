# intelligence.py
# Titan SOP V58.0 - Intelligence Ingestor
# 修正重點: 1. 新增 Gemini AI 深度解析功能。 2. [V58.0] 新增 Local Brain 關鍵字比對引擎作為備援。

import re
import pdfplumber
from typing import Dict, List
import pandas as pd
from knowledge_base import TitanKnowledgeBase
from config import Config
import google.generativeai as genai

class IntelligenceIngestor:

    def __init__(self):
        self.bullish_keywords = ["擴產", "資本支出", "新廠", "供不應求", "漲價", "上修", "急單"]
        self.bearish_keywords = ["下修", "庫存調整", "逆風", "不如預期", "砍單", "降價"]

    def _calculate_score(self, text: str) -> int:
        score = 0
        for k in self.bullish_keywords:
            if k in text: score += 10
        for k in self.bearish_keywords:
            if k in text: score -= 10
        return score

    def _local_brain_analysis(self, text: str, kb: TitanKnowledgeBase, df: pd.DataFrame) -> str:
        """[V58.0] SOP 關鍵字比對引擎 (Local Brain)"""
        report = "### 🧠 **SOP 本地大腦分析**\n\n"
        
        # 1. 掃描發債故事關鍵字
        found_story_keywords = [k for k in Config.STORY_KEYWORDS if k in text]
        if found_story_keywords:
            report += f"#### 📄 報告重點 (發債故事)\n- 命中關鍵字: **{', '.join(found_story_keywords)}**\n"
        else:
            report += "#### 📄 報告重點 (發債故事)\n- 未直接命中核心發債故事關鍵字。\n"

        # 2. 掃描族群關鍵字並找出關聯標的
        report += "\n#### 🎯 SOP 關聯標的\n"
        found_stocks = set()
        for sector, stocks in kb.sector_bellwether_map.items():
            if sector in text:
                for stock_identifier in stocks:
                    if not df.empty:
                        match = df[df['stock_code'].str.contains(stock_identifier, na=False) | df['name'].str.contains(stock_identifier, na=False)]
                        if not match.empty:
                            for _, row in match.iterrows():
                                found_stocks.add(f"{row['name']} ({row['stock_code']})")
        
        if found_stocks:
            for stock in sorted(list(found_stocks)):
                report += f"- `{stock}` (關聯族群)\n"
        else:
            report += "- 未在您的 CB 清單中找到與報告相關的族群標的。\n"
            
        return report

    def analyze_file(self, uploaded_file, kb: TitanKnowledgeBase, df: pd.DataFrame) -> Dict:
        """通用檔案分析入口 (支援全格式)"""
        fname = uploaded_file.name.lower()
        text = ""
        try:
            if fname.endswith('.pdf'):
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
            elif fname.endswith('.txt') or 'gmail' in fname:
                text = uploaded_file.getvalue().decode("utf-8")
            elif fname.endswith(('.png', '.jpg', '.jpeg')):
                return self._analyze_image(uploaded_file)
            elif fname.endswith(('.mp3', '.wav', '.mp4', '.m4a')):
                return self._analyze_media(uploaded_file)
            else:
                return {"error": f"尚未支援的檔案格式: {fname}"}

            local_report = self._local_brain_analysis(text, kb, df)
            
            return {
                "type": "文件" if fname.endswith(('.pdf', '.txt')) else "郵件",
                "summary": text[:500] + "...",
                "full_text": text,
                "local_analysis_md": local_report
            }

        except Exception as e:
            return {"error": f"檔案讀取或分析失敗: {str(e)}"}

    def analyze_with_gemini(self, file_content_text: str) -> str:
        """[V50.0] 使用 Gemini AI 進行深度解析"""
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            你是一位頂尖的可轉債（CB）金融分析師，熟悉鄭思翰的波段投資策略。
            請根據以下提供的文件內容，依據鄭思翰的邏輯進行分析：

            1.  **摘要重點**：總結文件核心觀點，不超過 150 字。
            2.  **發債故事比對**：判斷內容是否提及任何潛在的「發債故事」。請直接比對鄭思翰的核心關鍵字，例如：「擴產」、「資本支出」、「新廠」、「併購」、「轉機」、「營收爆發」、「從無到有」、「政策事件」。若有，請直接引用原文句子。
            3.  **多空判斷**：基於文件內容，給出對相關公司或產業的「🔥 樂觀」、「❄️ 悲觀」或「😐 中性」看法，並簡述理由。
            4.  **相關台股標的**：明確列出文件中提及的所有「台股代號」（四位數代碼）與其公司名稱。

            --- 文件內容開始 ---
            {file_content_text[:8000]}
            --- 文件內容結束 ---

            請以 Markdown 格式條列式回覆你的分析報告。
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ **Gemini AI 分析失敗**\n錯誤訊息: {str(e)}\n請檢查您的 API Key 是否正確或網路連線是否正常。"

    def _analyze_image(self, file) -> Dict:
        return {
            "type": "Image (圖檔)", "status": "已接收 (待串接 GPT-4 Vision)", "score": 0,
            "summary": f"收到圖片: {file.name}，正在進行 OCR 與圖表分析..."
        }

    def _analyze_media(self, file) -> Dict:
        return {
            "type": "Media (影音)", "status": "已接收 (待串接 Whisper STT)", "score": 0,
            "summary": f"收到影音檔: {file.name}，正在轉錄逐字稿..."
        }