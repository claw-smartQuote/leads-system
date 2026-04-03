#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
永诚保险 WhatsApp 报价机器人
支持燃油车和新能源车自动报价，根据车龄计算折扣
"""

import json
import re
from typing import Dict, Optional, Tuple
from quotation_system import InsuranceQuotationSystem

class WhatsAppInsuranceBot:
    """WhatsApp 保险报价机器人"""
    
    def __init__(self):
        self.system = InsuranceQuotationSystem()
        self.sessions = {}  # 存储用户会话状态
        
    def parse_message(self, message: str) -> Dict:
        """
        解析用户消息，提取车辆信息
        
        支持的格式：
        - 报价 粤B12345 燃油车 6座以下个人 4人 3年 300万
        - 报价 粤B12345 新能源 6座以下个人 4人 2年 200万
        - 快速报价 粤B12345 燃油车 3年
        """
        message = message.strip().lower()
        result = {
            "action": None,
            "license_plate": None,
            "vehicle_fuel_type": None,
            "vehicle_category": None,
            "passenger_count": None,
            "vehicle_age": 3.0,  # 默认3年（七折）
            "third_party_limit": 300,  # 默认300万
            "medical_outside_limit": 10,  # 默认10万
            "has_passenger": False,  # 默认不投保车上人员
            "driving_accident_type": "无",  # 默认不投保驾意险
        }
        
        # 检查是否是报价请求
        if "报价" in message or "報價" in message:
            result["action"] = "quote"
            
            # 提取车牌号（支持粤B、港车、澳车等格式）
            # 支持格式：粤B12345, 港车A123, 港A123, 澳车B123, A1234等
            plate_patterns = [
                r'([粤][A-Z]\d{4,5})',      # 粤B12345
                r'(港车[A-Z]?\d{1,5})',     # 港车A123
                r'(港[A-Z]\d{1,5})',        # 港A123
                r'(澳车[A-Z]?\d{1,5})',     # 澳车B123
                r'(澳[A-Z]\d{1,5})',        # 澳B123
                r'(\w{2}\d{4,5})',          # 其他格式如ZK2753
            ]
            
            # 清理消息：统一车/車，并处理"港车"格式
            msg_upper = message.upper()
            msg_upper = msg_upper.replace("車", "车")
            # 将"港 车"合并为"港车"
            msg_upper = msg_upper.replace("港 车", "港车").replace("澳 车", "澳车")
            
            for pattern in plate_patterns:
                plate_match = re.search(pattern, msg_upper)
                if plate_match:
                    result["license_plate"] = plate_match.group(1)
                    break
            
            # 判断车辆类型
            if "燃油" in message or "油車" in message or "fuel" in message:
                result["vehicle_fuel_type"] = "燃油车"
            elif "新能源" in message or "电动" in message or "ev" in message:
                result["vehicle_fuel_type"] = "新能源车"
            
            # 判断使用性质
            if "6-10座企业" in message or "6-10座企業" in message:
                result["vehicle_category"] = "6-10座企业"
            elif "6座以下企业" in message or "6座以下企業" in message:
                result["vehicle_category"] = "6座以下企业"
            elif "6-10座个人" in message or "6-10座個人" in message:
                result["vehicle_category"] = "6-10座个人"
            elif "6座以下个人" in message or "6座以下個人" in message or "個人" in message or "个人" in message:
                result["vehicle_category"] = "6座以下个人"
            
            # 检查是否投保车上人员（默认不投保，与案例一致）
            if "车上人员" in message or "車上人員" in message or "乘客险" in message:
                result["has_passenger"] = True
            else:
                result["has_passenger"] = False  # 默认不投保
            
            # 提取驾意险（30万或50万）
            if "50万驾意" in message or "50萬駕意" in message or "驾意50" in message:
                result["driving_accident_type"] = "50万"
            elif "30万驾意" in message or "30萬駕意" in message or "驾意30" in message or "驾意险" in message or "駕意險" in message:
                result["driving_accident_type"] = "30万"
            else:
                result["driving_accident_type"] = "无"
            
            # 提取乘客数（避免匹配"6座以下"中的6座）
            # 优先匹配 "X人" 或 "X座" 后面不是"以下"的情况
            passenger_pattern = r'(\d+)\s*[人](?!以)'
            passenger_match = re.search(passenger_pattern, message)
            if passenger_match:
                result["passenger_count"] = int(passenger_match.group(1))
            else:
                # 如果没有找到 "X人"，尝试找 "X座"（但排除"6座以下"这种情况）
                # 使用更严格的模式，要求座位数后面跟空格或结束
                seat_pattern = r'(\d+)\s*座(?:\s+|$)'
                seat_match = re.search(seat_pattern, message)
                if seat_match:
                    result["passenger_count"] = int(seat_match.group(1))
            
            # 提取车龄（支持格式：3年、2.5年、1年等）
            age_pattern = r'(\d+(?:\.\d+)?)\s*[年y]'
            age_match = re.search(age_pattern, message)
            if age_match:
                result["vehicle_age"] = float(age_match.group(1))
            
            # 提取第三者保额
            third_party_pattern = r'(\d+)\s*[万萬]'
            third_match = re.search(third_party_pattern, message)
            if third_match:
                limit = int(third_match.group(1))
                if limit in [100, 150, 200, 300, 400, 500]:
                    result["third_party_limit"] = limit
            
            # 提取医保外用药保额（10万或20万）
            if "医保外用药20万" in message or "醫保外用藥20萬" in message or "医保外20" in message or "醫保外20" in message:
                result["medical_outside_limit"] = 20
            elif "医保外用药10万" in message or "醫保外用藥10萬" in message or "医保外10" in message or "醫保外10" in message:
                result["medical_outside_limit"] = 10
            elif "不含医保外" in message or "不含醫保外" in message or "医保外0" in message or "醫保外0" in message:
                result["medical_outside_limit"] = 0
            else:
                result["medical_outside_limit"] = 10  # 默认10万
        
        elif "帮助" in message or "說明" in message or "help" in message:
            result["action"] = "help"
        
        return result
    
    def generate_quote_response(self, params: Dict) -> str:
        """生成报价回复"""
        # 检查必需参数
        if not params["license_plate"]:
            return "❌ 請提供車牌號碼\n\n格式：報價 [車牌號] [燃油車/新能源車] [車輛類型] [乘客數] [車齡] [第三者保額]\n\n例如：報價 粵B12345 燃油車 6座以下個人 4人 3年 300萬"
        
        if not params["vehicle_fuel_type"]:
            return "❌ 請指定車輛類型：燃油車 或 新能源車\n\n例如：報價 粵B12345 燃油車 6座以下個人 4人 3年 300萬"
        
        if not params["vehicle_category"]:
            params["vehicle_category"] = "6座以下个人"  # 默认
        
        if not params["passenger_count"]:
            params["passenger_count"] = 4  # 默认4人
        
        try:
            # 生成报价
            quote = self.system.generate_quote(
                license_plate=params["license_plate"],
                vehicle_fuel_type=params["vehicle_fuel_type"],
                vehicle_category=params["vehicle_category"],
                passenger_count=params["passenger_count"],
                vehicle_age=params["vehicle_age"],
                third_party_limit=params["third_party_limit"],
                medical_outside_limit=params["medical_outside_limit"],
                has_passenger=params.get("has_passenger", False),
                driving_accident_type=params.get("driving_accident_type", "无")
            )
            
            # 格式化回复
            lines = []
            lines.append(f"🚗 *永诚保险报价单*")
            lines.append("")
            lines.append(f"📋 车辆信息")
            lines.append(f"  车牌号: {quote.license_plate}")
            lines.append(f"  车辆类型: {quote.vehicle_fuel_type}")
            lines.append(f"  使用性质: {quote.vehicle_category}")
            lines.append(f"  乘客数: {quote.passenger_count}人")
            lines.append(f"  车龄: {quote.vehicle_age}年")
            lines.append("")
            lines.append(f"💰 保费明细 (商业险{quote.commercial_discount:.1f}折)")
            lines.append(f"  • 交强险: {quote.compulsory_premium:.2f} 元")
            lines.append(f"  • 第三者责任险 ({quote.third_party_limit}万): {quote.third_party_premium:.2f} 元")
            if quote.passenger_driver_premium > 0 or quote.passenger_occupant_premium > 0:
                lines.append(f"  • 车上人员（司机）: {quote.passenger_driver_premium:.2f} 元")
                lines.append(f"  • 车上人员（乘客）: {quote.passenger_occupant_premium:.2f} 元")
            lines.append(f"  • 医保外用药（三者）{quote.medical_outside_limit}万: {quote.medical_outside_third:.2f} 元")
            if quote.driving_accident_premium > 0:
                lines.append(f"  • 驾意险: {quote.driving_accident_premium:.2f} 元")
            lines.append(f"  • 道路救援: 免费（12次）")
            lines.append("")
            lines.append(f"📊 保费汇总")
            lines.append(f"  商业险保费: {quote.commercial_total:.2f} 元")
            lines.append(f"  交强险保费: {quote.compulsory_premium:.2f} 元")
            lines.append(f"  ─────────────")
            lines.append(f"  *保费合计: {quote.total_premium:.2f} 元（人民币）*")
            lines.append("")
            lines.append("⚠️ 此报价仅供参考，具体保费金额以投保时系统金额为准。")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"❌ 计算报价时出错: {str(e)}\n请检查输入参数是否正确。"
    
    def get_help_message(self) -> str:
        """获取帮助信息"""
        lines = []
        lines.append("🤖 *永诚保险报价机器人*")
        lines.append("")
        lines.append("📋 *使用方法*")
        lines.append("发送: 报价 [车牌号] [车辆类型] [使用性质] [乘客数] [车龄] [第三者保额] [选项]")
        lines.append("")
        lines.append("*示例*")
        lines.append("• 报价 粤B12345 燃油车 6座以下个人 4人 3年 300万")
        lines.append("• 报价 港车A123 新能源 6座以下个人 4人 2年 200万")
        lines.append("• 报价 粤B67890 燃油车 6-10座企业 7人 1年 500万 医保外20万")
        lines.append("")
        lines.append("*折扣规则（根据车龄）*")
        lines.append("• 燃油车：")
        lines.append("  - 3年以上：七折 (0.7)")
        lines.append("  - 2年以上：八折 (0.8)")
        lines.append("  - 1年以上：九折 (0.9)")
        lines.append("  - 少于1年：无折扣 (1.0)")
        lines.append("• 新能源车：固定九折 (0.9)，不根据车龄变化")
        lines.append("")
        lines.append("*可选附加险*")
        lines.append("• 医保外用药10万：添加「医保外10万」（默认）")
        lines.append("• 医保外用药20万：添加「医保外20万」")
        lines.append("• 不含医保外用药：添加「不含医保外」")
        lines.append("• 车上人员：添加「车上人员」")
        lines.append("• 驾意险30万：添加「30万驾意」")
        lines.append("• 驾意险50万：添加「50万驾意」")
        lines.append("")
        lines.append("*支持的参数*")
        lines.append("• 车辆类型: 燃油车 / 新能源")
        lines.append("• 使用性质: 6座以下个人 / 6座以下企业 / 6-10座个人 / 6-10座企业")
        lines.append("• 第三者保额: 100万 / 150万 / 200万 / 300万 / 400万 / 500万")
        lines.append("")
        lines.append("*默认参数*")
        lines.append("• 使用性质: 6座以下个人")
        lines.append("• 乘客数: 4人")
        lines.append("• 车龄: 3年（燃油车七折/新能源九折）")
        lines.append("• 第三者保额: 300万")
        lines.append("• 医保外用药: 10万")
        lines.append("• 车上人员: 不投保")
        lines.append("• 驾意险: 不投保")
        lines.append("")
        lines.append("发送「帮助」查看此说明")
        
        return "\n".join(lines)
    
    def handle_message(self, user_id: str, message: str) -> str:
        """
        处理用户消息并返回回复
        
        Args:
            user_id: 用户ID（WhatsApp号码）
            message: 用户发送的消息
            
        Returns:
            回复消息
        """
        # 解析消息
        params = self.parse_message(message)
        
        # 根据动作生成回复
        if params["action"] == "quote":
            return self.generate_quote_response(params)
        elif params["action"] == "help":
            return self.get_help_message()
        else:
            # 默认回复
            return self.get_help_message()


# ========== 快捷使用函数 ==========

def process_whatsapp_message(user_id: str, message: str) -> str:
    """
    处理WhatsApp消息的快捷函数
    
    示例:
        reply = process_whatsapp_message("+85212345678", "报价 粤B12345 燃油车 6座以下个人 4人 3年 300万")
        print(reply)
    """
    bot = WhatsAppInsuranceBot()
    return bot.handle_message(user_id, message)


# ========== 测试 ==========

if __name__ == "__main__":
    bot = WhatsAppInsuranceBot()
    
    # 测试用例
    test_messages = [
        "报价 粤B12345 燃油车 6座以下个人 4人 3年 300万",
        "报价 粤B12345 燃油车 6座以下个人 4人 3年 300万 医保外20万",
        "报价 粤B12345 燃油车 6座以下个人 4人 3年 300万 不含医保外",
        "報價 港車A123 新能源車 6座以下個人 4人 2年 200萬",
        "报价 ZK2753 燃油车 0.5年",
        "帮助",
    ]
    
    print("=== WhatsApp 报价机器人测试 ===\n")
    
    for msg in test_messages:
        print(f"用户输入: {msg}")
        print("-" * 50)
        reply = bot.handle_message("+85212345678", msg)
        print(reply)
        print("\n" + "=" * 50 + "\n")
