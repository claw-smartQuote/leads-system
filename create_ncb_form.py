#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NCB 轉移信 - 框線表格風格
每個項目一個行位，帶框線
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import os

def register_chinese_fonts():
    """註冊中文字體"""
    font_paths = [
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                return 'Chinese'
            except:
                continue
    
    return 'Helvetica'

def draw_boxed_row(c, x, y, width, height, label, font_name, font_size=12, label_width_cm=5.0):
    """繪製帶框線的行（左邊標籤，右邊填寫區）"""
    label_width = label_width_cm * cm  # 標籤區寬度（可調整）
    
    # 繪製外框
    c.rect(x, y - height, width, height, fill=0, stroke=1)
    
    # 繪製標籤與填寫區的分隔線（右移）
    c.line(x + label_width, y - height, x + label_width, y)
    
    # 繪製標籤文字（垂直置中）
    c.setFont(font_name, font_size)
    text_y = y - height/2 - font_size/3
    c.drawString(x + 0.3*cm, text_y, label)
    
    return y - height

def create_ncb_letter(output_path):
    """創建 NCB 轉移信 PDF（框線版）"""
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    chinese_font = register_chinese_fonts()
    
    # 邊距
    left_margin = 2.5 * cm
    right_margin = 2.5 * cm
    top_margin = 2.5 * cm
    
    # 計算可用寬度
    usable_width = width - left_margin - right_margin
    
    # 行高（增加行距）
    row_height = 1.3 * cm
    
    # 起始 Y 位置
    y = height - top_margin
    
    # ========== 頂部：日期（靠右）==========
    c.setFont(chinese_font, 12)
    c.drawRightString(width - right_margin, y, "日期：________________")
    y -= 1.5 * cm
    
    # ========== 標題 ==========
    c.setFont(chinese_font, 18)
    title = "有關轉移無賠償折扣(NCB)"
    title_width = c.stringWidth(title, chinese_font, 18)
    c.drawString((width - title_width) / 2, y, title)
    y -= 2.0 * cm
    
    # ========== 分區一：授權人資料 ==========
    # 區塊標題（粗體 14pt）
    c.setFont(chinese_font, 14)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(left_margin, y, "▎授權人資料")
    y -= 1.0 * cm
    
    # 項目 1：本人／本公司（分隔線右移）
    y = draw_boxed_row(c, left_margin, y, usable_width, row_height, 
                       "本人／本公司", chinese_font, 12, label_width_cm=5.0)
    y -= 1.2 * cm  # 增加與下一標題的分隔
    
    # ========== 分區二：保單資料 ==========
    c.setFont(chinese_font, 14)
    c.drawString(left_margin, y, "▎保單資料")
    y -= 1.0 * cm
    
    # 項目 2：保險公司（分隔線右移）
    y = draw_boxed_row(c, left_margin, y, usable_width, row_height, 
                       "保險公司", chinese_font, 12, label_width_cm=5.0)
    y -= 0.4 * cm
    
    # 項目 3：保單號碼（分隔線右移）
    y = draw_boxed_row(c, left_margin, y, usable_width, row_height, 
                       "保單號碼", chinese_font, 12, label_width_cm=5.0)
    y -= 0.4 * cm
    
    # 項目 4：車牌（分隔線右移）
    y = draw_boxed_row(c, left_margin, y, usable_width, row_height, 
                       "車牌", chinese_font, 12, label_width_cm=5.0)
    y -= 0.4 * cm
    
    # 項目 5：NCB 百分比（分隔線右移）
    y = draw_boxed_row(c, left_margin, y, usable_width, row_height, 
                       "無賠償折扣（NCB）%", chinese_font, 12, label_width_cm=5.0)
    y -= 1.2 * cm  # 增加與下一標題的分隔
    
    # ========== 分區三：轉移資料 ==========
    c.setFont(chinese_font, 14)
    c.drawString(left_margin, y, "▎轉移資料")
    y -= 1.0 * cm
    
    # 項目 6：轉移至（對方名稱）（分隔線右移）
    y = draw_boxed_row(c, left_margin, y, usable_width, row_height, 
                       "轉移至（對方名稱）", chinese_font, 12, label_width_cm=5.0)
    y -= 0.4 * cm
    
    # 項目 7：對方車牌（分隔線右移）
    y = draw_boxed_row(c, left_margin, y, usable_width, row_height, 
                       "對方車牌", chinese_font, 12, label_width_cm=5.0)
    y -= 2.0 * cm
    
    # ========== 聲明文字 ==========
    c.setFont(chinese_font, 12)
    statement = "本人／本公司同意將上述無賠償折扣（NCB）轉移至上述名下使用。"
    c.drawString(left_margin, y, statement)
    y -= 1.5 * cm
    
    # ========== 結尾 ==========
    c.setFont(chinese_font, 12)
    c.drawString(left_margin, y, "此致")
    y -= 1.5 * cm  # 減少間距，配合上移
    
    # ========== 簽署區（下移 1cm）==========
    y -= 1.0 * cm  # 下移 1cm
    
    # 方框向上移 3cm
    y += 3 * cm
    
    # 方框改成 3cm 高 × 7cm 長
    sig_box_width = 7 * cm   # 7cm 長
    sig_box_height = 3 * cm  # 3cm 高
    # 置中對齊
    sig_box_x = (width - sig_box_width) / 2
    
    # 先畫方框
    c.setStrokeColorRGB(0, 0, 0)  # 確保框線是黑色
    c.rect(sig_box_x, y - sig_box_height, sig_box_width, sig_box_height, fill=0, stroke=1)
    
    # 方框右手邊畫文字（垂直置中對齊）
    text_x = sig_box_x + sig_box_width + 0.5 * cm  # 方框右邊 + 間距
    text_y = y - sig_box_height / 2 - 6  # 垂直置中（字體大小約12pt，減去一半高度）
    c.setFont(chinese_font, 12)
    c.drawString(text_x, text_y, "簽署及公司印")
    c.setFont(chinese_font, 10)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(text_x, text_y - 0.5 * cm, "Insured's Signature & Chop")
    
    c.save()
    print(f"PDF 已創建: {output_path}")

if __name__ == "__main__":
    output_path = "/Users/claw/.openclaw/workspace/轉_NCB_信_表格版.pdf"
    create_ncb_letter(output_path)
