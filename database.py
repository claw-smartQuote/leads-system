"""
資料庫模組 - 管理潛客資料
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import os

# 支持 Render 環境：使用 /tmp 或環境變數
DB_DIR = Path(os.getenv("RENDER_DISK_PATH", "/tmp" if os.getenv("RENDER") else Path(__file__).parent))
DB_PATH = DB_DIR / "data" / "leads.db"

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """初始化資料庫表格"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                car_plate TEXT,
                car_model TEXT,
                car_year TEXT,
                current_insurer TEXT,
                expiry_date TEXT,
                inquiry_type TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT '新潛客',
                follow_up_date DATE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_lead(self, data: dict) -> int:
        """新增潛客
        
        Args:
            data: 潛客資料字典
            
        Returns:
            新潛客的 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO leads 
            (name, phone, email, car_plate, car_model, car_year, 
             current_insurer, expiry_date, inquiry_type, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name'),
            data.get('phone'),
            data.get('email'),
            data.get('car_plate'),
            data.get('car_model'),
            data.get('car_year'),
            data.get('current_insurer'),
            data.get('expiry_date'),
            data.get('inquiry_type'),
            data.get('notes'),
            '新潛客'
        ))
        
        lead_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return lead_id
    
    def get_all_leads(self, status=None, limit=None):
        """獲取所有潛客
        
        Args:
            status: 篩選狀態（可選）
            limit: 限制數量（可選）
            
        Returns:
            潛客列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM leads"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        leads = [dict(row) for row in rows]
        conn.close()
        
        return leads
    
    def get_lead_by_id(self, lead_id: int):
        """根據 ID 獲取潛客"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        return dict(row) if row else None
    
    def update_status(self, lead_id: int, status: str, follow_up_date=None):
        """更新潛客狀態"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if follow_up_date:
            cursor.execute(
                "UPDATE leads SET status = ?, follow_up_date = ? WHERE id = ?",
                (status, follow_up_date, lead_id)
            )
        else:
            cursor.execute(
                "UPDATE leads SET status = ? WHERE id = ?",
                (status, lead_id)
            )
        
        conn.commit()
        conn.close()
    
    def get_new_leads_count(self, since=None):
        """獲取新潛客數量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if since:
            cursor.execute(
                "SELECT COUNT(*) FROM leads WHERE created_at > ?",
                (since,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = '新潛客'")
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_leads_by_date_range(self, start_date, end_date):
        """根據日期範圍獲取潛客"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM leads 
            WHERE DATE(created_at) BETWEEN ? AND ?
            ORDER BY created_at DESC
        ''', (start_date, end_date))
        
        rows = cursor.fetchall()
        leads = [dict(row) for row in rows]
        conn.close()
        
        return leads

# 測試
if __name__ == "__main__":
    db = Database()
    print("✅ 資料庫初始化成功")
    print(f"📁 資料庫位置: {db.db_path}")