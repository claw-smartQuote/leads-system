"""
Excel 匯出模組 - 將潛客資料匯出為 Excel
"""
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

EXPORTS_DIR = Path(__file__).parent / "exports"

class ExcelExporter:
    def __init__(self):
        self.exports_dir = EXPORTS_DIR
        self.exports_dir.mkdir(exist_ok=True)
    
    def export_all_leads(self, leads: list, filename=None) -> str:
        """匯出所有潛客到 Excel
        
        Args:
            leads: 潛客列表
            filename: 自定義檔名（可選）
            
        Returns:
            匯出檔案的路徑
        """
        if not filename:
            filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        filepath = self.exports_dir / filename
        
        # 轉換為 DataFrame
        df = pd.DataFrame(leads)
        
        if df.empty:
            # 創建空表格結構
            df = pd.DataFrame(columns=[
                'id', 'name', 'phone', 'email', 'car_plate', 'car_model',
                'car_year', 'current_insurer', 'expiry_date', 'inquiry_type',
                'notes', 'created_at', 'status', 'follow_up_date'
            ])
        
        # 重新命名欄位為中文
        column_mapping = {
            'id': '編號',
            'name': '姓名',
            'phone': '電話',
            'email': '電郵',
            'car_plate': '車牌',
            'car_model': '車型',
            'car_year': '年份',
            'current_insurer': '現有保險公司',
            'expiry_date': '保單到期日',
            'inquiry_type': '查詢類型',
            'notes': '備註',
            'created_at': '提交時間',
            'status': '狀態',
            'follow_up_date': '跟進日期'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 使用 ExcelWriter 創建多個工作表
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 所有潛客
            df.to_excel(writer, sheet_name='所有潛客', index=False)
            
            # 按狀態分類
            if not df.empty and '狀態' in df.columns:
                for status in df['狀態'].unique():
                    df_status = df[df['狀態'] == status]
                    sheet_name = status[:31]  # Excel 工作表名稱最多 31 字符
                    df_status.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 今日新潛客
            today = datetime.now().strftime('%Y-%m-%d')
            if not df.empty and '提交時間' in df.columns:
                df_today = df[df['提交時間'].str.startswith(today, na=False)]
                if not df_today.empty:
                    df_today.to_excel(writer, sheet_name='今日新潛客', index=False)
        
        print(f"✅ Excel 匯出完成: {filepath}")
        return str(filepath)
    
    def export_by_date_range(self, leads: list, start_date: str, end_date: str) -> str:
        """根據日期範圍匯出"""
        filename = f"leads_{start_date}_to_{end_date}.xlsx"
        return self.export_all_leads(leads, filename)
    
    def export_daily_report(self, leads: list, date=None) -> str:
        """匯出每日報表"""
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        filename = f"daily_report_{date}.xlsx"
        filepath = self.exports_dir / filename
        
        df = pd.DataFrame(leads)
        
        if df.empty:
            df = pd.DataFrame(columns=['編號', '姓名', '電話', '車型', '查詢類型', '狀態', '提交時間'])
        else:
            # 選擇關鍵欄位
            key_columns = ['id', 'name', 'phone', 'car_model', 'inquiry_type', 'status', 'created_at']
            df = df[key_columns]
            
            column_mapping = {
                'id': '編號',
                'name': '姓名',
                'phone': '電話',
                'car_model': '車型',
                'inquiry_type': '查詢類型',
                'status': '狀態',
                'created_at': '提交時間'
            }
            df = df.rename(columns=column_mapping)
        
        # 添加統計資訊
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 主要數據
            df.to_excel(writer, sheet_name='潛客列表', index=False)
            
            # 統計摘要
            if not df.empty:
                summary_data = {
                    '項目': ['總數', '新潛客', '已聯絡', '已報價', '已成交', '已結案'],
                    '數量': [
                        len(df),
                        len(df[df['狀態'] == '新潛客']) if '狀態' in df.columns else 0,
                        len(df[df['狀態'] == '已聯絡']) if '狀態' in df.columns else 0,
                        len(df[df['狀態'] == '已報價']) if '狀態' in df.columns else 0,
                        len(df[df['狀態'] == '已成交']) if '狀態' in df.columns else 0,
                        len(df[df['狀態'] == '已結案']) if '狀態' in df.columns else 0,
                    ]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='統計摘要', index=False)
                
                # 按類型分類
                if '查詢類型' in df.columns:
                    type_counts = df['查詢類型'].value_counts().reset_index()
                    type_counts.columns = ['查詢類型', '數量']
                    type_counts.to_excel(writer, sheet_name='類型分布', index=False)
        
        print(f"✅ 每日報表匯出完成: {filepath}")
        return str(filepath)
    
    def get_export_list(self):
        """獲取所有匯出檔案列表"""
        files = []
        for f in self.exports_dir.glob("*.xlsx"):
            files.append({
                'filename': f.name,
                'path': str(f),
                'size': f.stat().st_size,
                'created': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # 按時間排序
        files.sort(key=lambda x: x['created'], reverse=True)
        return files

# 測試
if __name__ == "__main__":
    exporter = ExcelExporter()
    
    # 測試數據
    test_leads = [
        {
            'id': 1,
            'name': '張先生',
            'phone': '91234567',
            'email': 'mr.cheung@example.com',
            'car_plate': 'AB1234',
            'car_model': 'Toyota Camry',
            'car_year': '2020',
            'current_insurer': 'AIG',
            'expiry_date': '2025-04-15',
            'inquiry_type': '續保',
            'notes': '希望比較價格',
            'created_at': '2025-03-18 10:30:00',
            'status': '新潛客',
            'follow_up_date': None
        }
    ]
    
    filepath = exporter.export_all_leads(test_leads)
    print(f"✅ 測試匯出: {filepath}")