"""
WhatsApp 通知模組 - 收到新潛客時即時通知
"""
import json
from datetime import datetime
from pathlib import Path

# OpenClaw 配置
OPENCLAW_DIR = Path.home() / ".openclaw"
WHATSAPP_TO = "+85221101144"  # 你的 WhatsApp 號碼

class WhatsAppNotifier:
    def __init__(self, to_number: str = WHATSAPP_TO):
        self.to_number = to_number
    
    def send_new_lead_notification(self, lead_data: dict, lead_id: int):
        """發送新潛客通知
        
        Args:
            lead_data: 潛客資料
            lead_id: 潛客 ID
        """
        # 構建消息
        message = self._format_lead_message(lead_data, lead_id)
        
        # 使用 OpenClaw 的 message 工具發送
        # 注意：這會通過 OpenClaw 系統發送
        self._send_whatsapp(message)
    
    def _format_lead_message(self, lead_data: dict, lead_id: int) -> str:
        """格式化潛客資料為 WhatsApp 消息"""
        inquiry_type = lead_data.get('inquiry_type', '查詢')
        
        message = f"""🚗 *新潛客通知*

👤 姓名: {lead_data.get('name', 'N/A')}
📱 電話: {lead_data.get('phone', 'N/A')}
📧 電郵: {lead_data.get('email', 'N/A')}

🚙 車輛資料:
• 車牌: {lead_data.get('car_plate', 'N/A')}
• 型號: {lead_data.get('car_model', 'N/A')}
• 年份: {lead_data.get('car_year', 'N/A')}

📋 查詢類型: {inquiry_type}
📝 備註: {lead_data.get('notes', '無')}

⏰ 提交時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}
🆔 潛客編號: #{lead_id}

👉 回覆此消息開始跟進
"""
        return message
    
    def _send_whatsapp(self, message: str):
        """發送 WhatsApp 消息
        
        這個方法會創建一個觸發文件，由 OpenClaw 系統處理
        實際發送會在 FastAPI 後端中通過 API 調用完成
        """
        # 創建通知觸發文件
        trigger_dir = Path(__file__).parent / "notifications"
        trigger_dir.mkdir(exist_ok=True)
        
        trigger_file = trigger_dir / f"whatsapp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        notification_data = {
            "to": self.to_number,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "type": "new_lead"
        }
        
        with open(trigger_file, 'w', encoding='utf-8') as f:
            json.dump(notification_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ WhatsApp 通知已觸發: {trigger_file}")
    
    def send_daily_summary(self, new_count: int, total_count: int):
        """發送每日摘要"""
        message = f"""📊 *每日潛客摘要*

📈 今日新潛客: {new_count} 個
📁 累積潛客: {total_count} 個

💡 提示: 記得跟進新潛客！
"""
        self._send_whatsapp(message)

# 測試
if __name__ == "__main__":
    notifier = WhatsAppNotifier()
    
    test_data = {
        "name": "測試客戶",
        "phone": "91234567",
        "email": "test@example.com",
        "car_plate": "AB1234",
        "car_model": "Toyota Camry",
        "car_year": "2020",
        "inquiry_type": "續保",
        "notes": "希望比較價格"
    }
    
    notifier.send_new_lead_notification(test_data, 1)
    print("✅ 測試通知已發送")