#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
永诚保险整合报价系统
支持燃油车与新能源车报价
版本: 2.0 (V.13 费率表 - 2026-08-21)
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum

# 系统版本
SYSTEM_VERSION = "2.0"
RATE_VERSION = "V.13"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VehicleType(Enum):
    """车辆类型"""
    FUEL_6_SEAT_BELOW_PERSONAL = "6座以下个人"      # 燃油车
    FUEL_6_SEAT_BELOW_BUSINESS = "6座以下企业"
    FUEL_6_10_SEAT_PERSONAL = "6-10座个人"
    FUEL_6_10_SEAT_BUSINESS = "6-10座企业"
    
    EV_6_SEAT_BELOW_PERSONAL = "新能源_6座以下个人"   # 新能源车
    EV_6_SEAT_BELOW_BUSINESS = "新能源_6座以下企业"
    EV_6_10_SEAT_PERSONAL = "新能源_6-10座个人"
    EV_6_10_SEAT_BUSINESS = "新能源_6-10座企业"


class VehicleFuelType(Enum):
    """车辆燃料类型"""
    FUEL = "燃油车"
    ELECTRIC = "新能源车"


# ========== 费率表 ==========

# 燃油车 - 第三者责任险费率 (基础保费，未折扣)
FUEL_THIRD_PARTY_RATES = {
    "6座以下个人": {100: 755.20, 150: 843.43, 200: 922.08, 300: 1074.67, 400: 1224.08, 500: 1370.37},
    "6座以下企业": {100: 926.69, 150: 1021.67, 200: 1106.37, 300: 1270.71, 400: 1431.67, 500: 1589.21},
    "6-10座个人": {100: 893.52, 150: 997.93, 200: 1090.99, 300: 1271.49, 400: 1448.28, 500: 1621.36},
    "6-10座企业": {100: 1066.80, 150: 1176.13, 200: 1273.65, 300: 1462.85, 400: 1648.15, 500: 1829.55},
}

# 新能源车 - 第三者责任险费率 (V.13)
EV_THIRD_PARTY_RATES = {
    "6座以下个人": {100: 755.20, 150: 843.42, 200: 922.08, 300: 1074.67, 400: 1224.08, 500: 1370.38},
    "6座以下企业": {100: 945.22, 150: 1042.11, 200: 1128.51, 300: 1296.12, 400: 1460.31, 500: 1621.00},
    "6-10座个人": {100: 893.52, 150: 997.93, 200: 1090.99, 300: 1271.49, 400: 1448.28, 500: 1621.36},
    "6-10座企业": {100: 1088.14, 150: 1199.66, 200: 1299.13, 300: 1492.11, 400: 1866.14, 500: 2047.18},
}

# 燃油车 - 车上人员费率 (每座1万保额)
FUEL_PASSENGER_RATES = {
    "6座以下个人": {"driver": 28.99, "passenger": 18.63},
    "6座以下企业": {"driver": 28.99, "passenger": 17.95},
    "6-10座个人": {"driver": 27.60, "passenger": 17.95},
    "6-10座企业": {"driver": 26.91, "passenger": 15.87},
}

# 新能源车 - 车上人员费率 (V.13)
EV_PASSENGER_RATES = {
    "6座以下个人": {"driver": 25.58, "passenger": 16.44},
    "6座以下企业": {"driver": 25.58, "passenger": 15.84},
    "6-10座个人": {"driver": 24.35, "passenger": 15.84},
    "6-10座企业": {"driver": 23.74, "passenger": 14.00},
}

# 医保外用药费率
FUEL_MEDICAL_OUTSIDE_RATES = {0: 0, 10: 73.33, 20: 102.67, 30: 124.00, 50: 158.67, 100: 221.33}
EV_MEDICAL_OUTSIDE_RATES = {0: 0, 10: 64.71, 20: 90.59, 30: 109.41, 50: 140.00, 100: 195.29}  # V.13

# 駕意險費率 (V.13 - 按座位數計費)
# 格式: {座位數: {"30万": 單價, "50万": 單價, "80万": 單價}}
# 2座按3座價格
DRIVING_ACCIDENT_RATES_BY_SEAT = {
    2: {"30万": 120, "50万": 180, "80万": 294},
    3: {"30万": 120, "50万": 180, "80万": 294},
    4: {"30万": 160, "50万": 240, "80万": 392},
    5: {"30万": 200, "50万": 300, "80万": 490},
    6: {"30万": 240, "50万": 360, "80万": 540},
    7: {"30万": 280, "50万": 420, "80万": 630},
    8: {"30万": 320, "50万": 480, "80万": 720},
}

# 舊版駕意險費率（兼容舊接口）
DRIVING_ACCIDENT_RATES = {
    "30万": 40,  # 每位乘客40元
    "50万": 60,  # 每位乘客60元
}

# 交强险基础费率（需要乘以折扣）
COMPULSORY_BASE_RATES = {
    "6座以下个人": 950,
    "6座以下企业": 1000,
    "6-10座个人": 1100,
    "6-10座企业": 1130,
}

# 系统参数
SYSTEM_PARAMS = {
    "fuel": {
        "exchange_rate": 1.10,      # 港币汇率（显示用，计算中不使用）
        "commercial_discount": 0.7,  # 商业险折扣（不投保节假日翻倍）
        "commercial_discount_with_double": 1.0,  # 投保节假日翻倍不打折
        "has_holiday_double": True,  # 支持节假日翻倍
        "has_medical_driver": True,  # 支持司机医保外
        "has_medical_passenger": True,  # 支持乘客医保外
        "has_mental_comfort": True,  # 支持精神抚慰金
    },
    "ev": {
        "exchange_rate": 1.09,      # 港币汇率（显示用，计算中不使用）
        "commercial_discount": 0.9,  # 新能源商业险折扣（固定九折）
        "has_holiday_double": False,
        "has_medical_driver": False,
        "has_medical_passenger": False,
        "has_mental_comfort": False,
    }
}


@dataclass
class InsuranceQuote:
    """保险报价数据类"""
    # 车辆信息
    license_plate: str
    vehicle_fuel_type: str  # 燃油车/新能源车
    vehicle_category: str   # 6座以下个人/企业 等
    passenger_count: int
    
    # 保费明细
    compulsory_premium: float      # 交强险
    third_party_premium: float     # 第三者责任险
    passenger_driver_premium: float    # 车上人员（司机）
    passenger_occupant_premium: float  # 车上人员（乘客）
    medical_outside_third: float   # 医保外用药（三者）
    medical_outside_driver: float  # 医保外用药（司机）- 仅燃油车
    medical_outside_passenger: float  # 医保外用药（乘客）- 仅燃油车
    holiday_double_premium: float  # 节假日翻倍 - 仅燃油车
    mental_comfort_premium: float  # 精神抚慰金 - 仅燃油车
    road_rescue_premium: float     # 道路救援
    driving_accident_premium: float # 驾意险
    
    # 汇总
    commercial_total: float        # 商业险合计
    total_premium: float           # 保费总计
    
    # 参数
    third_party_limit: int         # 第三者保额（万）
    medical_outside_limit: int     # 医保外保额（万）
    has_holiday_double: bool       # 是否投保节假日翻倍
    exchange_rate: float           # 汇率
    vehicle_age: float             # 车龄（年）
    commercial_discount: float     # 商业险折扣
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "车辆信息": {
                "车牌号": self.license_plate,
                "车辆类型": self.vehicle_fuel_type,
                "使用性质": self.vehicle_category,
                "乘客数": self.passenger_count,
            },
            "保费明细": {
                "交强险": round(self.compulsory_premium, 2),
                "第三者责任险": round(self.third_party_premium, 2),
                "车上人员（司机）": round(self.passenger_driver_premium, 2),
                "车上人员（乘客）": round(self.passenger_occupant_premium, 2),
                "医保外用药（三者）": round(self.medical_outside_third, 2),
                "医保外用药（司机）": round(self.medical_outside_driver, 2) if self.medical_outside_driver > 0 else "未投保",
                "医保外用药（乘客）": round(self.medical_outside_passenger, 2) if self.medical_outside_passenger > 0 else "未投保",
                "节假日限额翻倍": round(self.holiday_double_premium, 2) if self.holiday_double_premium > 0 else "未投保",
                "精神抚慰金": round(self.mental_comfort_premium, 2) if self.mental_comfort_premium > 0 else "未投保",
                "道路救援": "免费" if self.road_rescue_premium == 0 else round(self.road_rescue_premium, 2),
                "驾意险": round(self.driving_accident_premium, 2) if self.driving_accident_premium > 0 else "未投保",
            },
            "保费汇总": {
                "商业险保费": round(self.commercial_total, 2),
                "交强险保费": round(self.compulsory_premium, 2),
                "保费合计（人民币）": round(self.total_premium, 2),
            },
            "投保参数": {
                "第三者责任险保额": f"{self.third_party_limit}万",
                "医保外用药保额": f"{self.medical_outside_limit}万" if self.medical_outside_limit > 0 else "未投保",
                "节假日翻倍": "是" if self.has_holiday_double else "否",
                "汇率": self.exchange_rate,
                "车龄": f"{self.vehicle_age}年",
                "商业险折扣": f"{self.commercial_discount:.1f}",
            }
        }


class InsuranceQuotationSystem:
    """永诚保险报价系统"""
    
    def __init__(self):
        self.system_name = "永诚保险报价系统"
        self.version = SYSTEM_VERSION
        self.rate_version = RATE_VERSION
        logger.info(f"初始化 {self.system_name} v{self.version} ({self.rate_version})")
    
    def calculate_third_party_premium(self, vehicle_fuel_type: str, vehicle_category: str, 
                                       limit: int, discount: float) -> float:
        """计算第三者责任险保费
        
        注意：根据Excel实际计算逻辑，不使用汇率
        保费 = 基础保费 × 折扣
        """
        # 根据车辆类型选择费率表
        if vehicle_fuel_type == "燃油车":
            rates = FUEL_THIRD_PARTY_RATES.get(vehicle_category, {})
        else:
            rates = EV_THIRD_PARTY_RATES.get(vehicle_category, {})
        
        # 获取基础保费
        base_premium = rates.get(limit, 0)
        
        # 应用折扣（不使用汇率）
        final_premium = base_premium * discount
        
        return final_premium
    
    def calculate_passenger_premium(self, vehicle_fuel_type: str, vehicle_category: str,
                                     passenger_count: int) -> Tuple[float, float]:
        """计算车上人员保费 (司机, 乘客总额)"""
        if vehicle_fuel_type == "燃油车":
            rates = FUEL_PASSENGER_RATES.get(vehicle_category, {"driver": 0, "passenger": 0})
        else:
            rates = EV_PASSENGER_RATES.get(vehicle_category, {"driver": 0, "passenger": 0})
        
        driver_premium = rates["driver"]
        passenger_premium = rates["passenger"] * passenger_count
        
        return driver_premium, passenger_premium
    
    def calculate_medical_outside_premium(self, vehicle_fuel_type: str, limit: int) -> float:
        """计算医保外用药保费"""
        if vehicle_fuel_type == "燃油车":
            rates = FUEL_MEDICAL_OUTSIDE_RATES
        else:
            rates = EV_MEDICAL_OUTSIDE_RATES
        
        return rates.get(limit, 0)
    
    def calculate_age_from_year_month(self, year: int, month: int) -> float:
        """
        從車輛登記年份和月份計算車齡
        
        Args:
            year: 登記年份（如 2021）
            month: 登記月份（1-12）
            
        Returns:
            車齡（年，保留1位小數）
        """
        from datetime import datetime
        
        # 獲取當前日期
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        # 計算年份差
        age_year = current_year - year
        
        # 如果當前月份還沒到登記月份，減1年
        if current_month < month:
            age_year -= 1
            month_diff = 12 - month + current_month
        else:
            month_diff = current_month - month
        
        # 計算總車齡（帶小數）
        age = age_year + (month_diff / 12)
        
        return round(age, 1)
    
    def calculate_age_direct(self, age: float) -> float:
        """
        直接使用輸入的車齡
        
        Args:
            age: 車齡（年）
            
        Returns:
            車齡（年）
        """
        return float(age)
    
    def calculate_commercial_discount(self, vehicle_fuel_type: str, vehicle_age: float) -> float:
        """
        计算商业险折扣（同时用于交強險折扣）
        
        规则（燃油车和新能源车统一根据车龄计算）:
        - 3年以上: 七折 (0.7)
        - 2年以上: 八折 (0.8)
        - 2年以下: 九折 (0.9)
        
        Args:
            vehicle_fuel_type: 车辆类型（燃油车/新能源车）
            vehicle_age: 车龄（年）
            
        Returns:
            商业险折扣系数
        """
        # 燃油车和新能源车统一根据车龄计算折扣
        if vehicle_age >= 3:
            return 0.7
        elif vehicle_age >= 2:
            return 0.8
        else:
            return 0.9  # 2年以下都是九折
    
    def calculate_driving_accident_premium(self, coverage_type: str, seat_count: int) -> float:
        """
        计算驾意险保费 (V.13 按座位數計費)
        
        规则:
        - 2座按3座價格
        - 按總座位數查表計費
        
        Args:
            coverage_type: 保额类型（"30万"、"50万"或"80万"）
            seat_count: 座位数（含司机）
            
        Returns:
            驾意险保费
        """
        # 使用V.13座位數費率表
        if seat_count in DRIVING_ACCIDENT_RATES_BY_SEAT:
            rates = DRIVING_ACCIDENT_RATES_BY_SEAT[seat_count]
        elif seat_count <= 2:
            # 2座按3座價格
            rates = DRIVING_ACCIDENT_RATES_BY_SEAT[3]
        elif seat_count > 8:
            # 超過8座按8座計
            rates = DRIVING_ACCIDENT_RATES_BY_SEAT[8]
        else:
            return 0
        
        return rates.get(coverage_type, 0)
    
    def generate_quote(self, 
                       license_plate: str,
                       vehicle_fuel_type: str,  # "燃油车" 或 "新能源车"
                       vehicle_category: str,   # "6座以下个人" 等
                       passenger_count: int,
                       vehicle_age: float = 3.0,  # 车龄（年），默认3年以上
                       third_party_limit: int = 300,  # 默认300万
                       medical_outside_limit: int = 10,  # 默认10万
                       has_holiday_double: bool = False,
                       has_medical_driver: bool = False,
                       has_medical_passenger: bool = False,
                       has_mental_comfort: bool = False,
                       has_passenger: bool = True,  # 是否投保车上人员
                       road_rescue_count: int = 12,
                       driving_accident_type: str = "无") -> InsuranceQuote:
        """
        生成保险报价
        
        Args:
            license_plate: 车牌号
            vehicle_fuel_type: 车辆燃料类型（燃油车/新能源车）
            vehicle_category: 车辆使用性质（6座以下个人等）
            passenger_count: 乘客数量
            third_party_limit: 第三者责任险保额（万）
            medical_outside_limit: 医保外用药保额（万）
            has_holiday_double: 是否投保节假日限额翻倍
            has_medical_driver: 是否投保司机医保外用药
            has_medical_passenger: 是否投保乘客医保外用药
            has_mental_comfort: 是否投保精神抚慰金
            has_passenger: 是否投保车上人员（默认True）
            road_rescue_count: 道路救援次数
            driving_accident_type: 驾意险类型
            
        Returns:
            InsuranceQuote: 报价对象
        """
        logger.info(f"开始生成报价: {license_plate}, {vehicle_fuel_type}, {vehicle_category}")
        
        # 获取系统参数
        params = SYSTEM_PARAMS["fuel"] if vehicle_fuel_type == "燃油车" else SYSTEM_PARAMS["ev"]
        
        # 1. 交强险保费（根据车龄计算折扣）
        compulsory_base = COMPULSORY_BASE_RATES.get(vehicle_category, 950)
        compulsory_discount = self.calculate_commercial_discount(vehicle_fuel_type, vehicle_age)
        compulsory_premium = compulsory_base * compulsory_discount
        
        # 2. 商业险折扣
        # 新能源车：整個商業險固定九折；燃油车：根据车龄折扣
        if vehicle_fuel_type == "新能源车":
            commercial_discount = 0.9  # 新能源车整個商業險固定九折
            third_party_discount = 0.9  # 新能源车第三者责任险固定九折
        else:
            commercial_discount = self.calculate_commercial_discount(vehicle_fuel_type, vehicle_age)
            third_party_discount = commercial_discount
        
        third_party_premium = self.calculate_third_party_premium(
            vehicle_fuel_type, vehicle_category, third_party_limit, 
            third_party_discount
        )
        
        # 4. 车上人员（根据参数决定是否投保）
        if has_passenger:
            passenger_driver_premium, passenger_occupant_premium = self.calculate_passenger_premium(
                vehicle_fuel_type, vehicle_category, passenger_count
            )
        else:
            passenger_driver_premium, passenger_occupant_premium = 0, 0
        
        # 5. 医保外用药（三者）- 新能源车固定九折
        medical_outside_third = self.calculate_medical_outside_premium(
            vehicle_fuel_type, medical_outside_limit
        ) * commercial_discount  # 应用商业险折扣
        
        # 6. 医保外用药（司机/乘客）- 仅燃油车支持
        medical_outside_driver = 0
        medical_outside_passenger = 0
        if vehicle_fuel_type == "燃油车":
            if has_medical_driver:
                medical_outside_driver = self.calculate_medical_outside_premium(vehicle_fuel_type, 10) * commercial_discount
            if has_medical_passenger:
                medical_outside_passenger = self.calculate_medical_outside_premium(vehicle_fuel_type, 10) * commercial_discount
        
        # 7. 节假日翻倍 - 仅燃油车支持
        holiday_double_premium = 0
        if vehicle_fuel_type == "燃油车" and has_holiday_double:
            # 节假日翻倍保费计算（根据原表逻辑）
            base_for_double = FUEL_THIRD_PARTY_RATES.get(vehicle_category, {}).get(
                third_party_limit if third_party_limit <= 300 else 300, 0
            )
            holiday_double_premium = base_for_double * params["exchange_rate"] - third_party_premium
            if holiday_double_premium < 0:
                holiday_double_premium = 0
        
        # 8. 精神抚慰金 - 仅燃油车支持
        mental_comfort_premium = 0
        if vehicle_fuel_type == "燃油车" and has_mental_comfort:
            mental_comfort_premium = 0  # 根据实际需求添加费率
        
        # 9. 道路救援（通常免费）
        road_rescue_premium = 0
        
        # 10. 驾意险（使用总座位数 = 乘客 + 司机）
        driving_accident_premium = 0
        if driving_accident_type != "无":
            total_seats = passenger_count + 1  # 总座位数 = 乘客 + 司机
            driving_accident_premium = self.calculate_driving_accident_premium(driving_accident_type, total_seats)
        
        # 计算商业险合计
        commercial_total = (
            third_party_premium + 
            passenger_driver_premium + 
            passenger_occupant_premium +
            medical_outside_third +
            medical_outside_driver +
            medical_outside_passenger +
            holiday_double_premium +
            mental_comfort_premium +
            road_rescue_premium +
            driving_accident_premium
        )
        
        # 计算总保费
        total_premium = compulsory_premium + commercial_total
        
        logger.info(f"报价生成完成: {license_plate}, 总保费: {total_premium:.2f}")
        
        return InsuranceQuote(
            license_plate=license_plate,
            vehicle_fuel_type=vehicle_fuel_type,
            vehicle_category=vehicle_category,
            passenger_count=passenger_count,
            compulsory_premium=compulsory_premium,
            third_party_premium=third_party_premium,
            passenger_driver_premium=passenger_driver_premium,
            passenger_occupant_premium=passenger_occupant_premium,
            medical_outside_third=medical_outside_third,
            medical_outside_driver=medical_outside_driver,
            medical_outside_passenger=medical_outside_passenger,
            holiday_double_premium=holiday_double_premium,
            mental_comfort_premium=mental_comfort_premium,
            road_rescue_premium=road_rescue_premium,
            driving_accident_premium=driving_accident_premium,
            commercial_total=commercial_total,
            total_premium=total_premium,
            third_party_limit=third_party_limit,
            medical_outside_limit=medical_outside_limit,
            has_holiday_double=has_holiday_double,
            exchange_rate=params["exchange_rate"],
            vehicle_age=vehicle_age,
            commercial_discount=commercial_discount
        )
    
    def generate_quote_by_year_month(self,
                                     license_plate: str,
                                     vehicle_fuel_type: str,
                                     vehicle_category: str,
                                     passenger_count: int,
                                     register_year: int,
                                     register_month: int,
                                     **kwargs) -> InsuranceQuote:
        """
        通過登記年份和月份計算車齡並生成報價
        
        Args:
            license_plate: 車牌號
            vehicle_fuel_type: 燃油車/新能源車
            vehicle_category: 6座以下個人等
            passenger_count: 乘客數
            register_year: 登記年份（如 2021）
            register_month: 登記月份（1-12）
            **kwargs: 其他可選參數（third_party_limit, has_passenger等）
            
        Returns:
            InsuranceQuote: 報價對象
        """
        # 計算車齡
        vehicle_age = self.calculate_age_from_year_month(register_year, register_month)
        logger.info(f"從年月計算車齡: {register_year}-{register_month:02d} -> {vehicle_age}年")
        
        # 調用原始生成方法
        return self.generate_quote(
            license_plate=license_plate,
            vehicle_fuel_type=vehicle_fuel_type,
            vehicle_category=vehicle_category,
            passenger_count=passenger_count,
            vehicle_age=vehicle_age,
            **kwargs
        )
    
    def generate_quote_by_age(self,
                              license_plate: str,
                              vehicle_fuel_type: str,
                              vehicle_category: str,
                              passenger_count: int,
                              vehicle_age: float,
                              **kwargs) -> InsuranceQuote:
        """
        直接輸入車齡生成報價
        
        Args:
            license_plate: 車牌號
            vehicle_fuel_type: 燃油車/新能源車
            vehicle_category: 6座以下個人等
            passenger_count: 乘客數
            vehicle_age: 車齡（年）
            **kwargs: 其他可選參數
            
        Returns:
            InsuranceQuote: 報價對象
        """
        logger.info(f"直接使用車齡: {vehicle_age}年")
        
        # 調用原始生成方法
        return self.generate_quote(
            license_plate=license_plate,
            vehicle_fuel_type=vehicle_fuel_type,
            vehicle_category=vehicle_category,
            passenger_count=passenger_count,
            vehicle_age=vehicle_age,
            **kwargs
        )
    
    def format_quote_text(self, quote: InsuranceQuote) -> str:
        """格式化报价单文本"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"永诚保险报价单 [v{SYSTEM_VERSION} - {RATE_VERSION}]")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"车牌号: {quote.license_plate}")
        lines.append(f"车辆类型: {quote.vehicle_fuel_type} - {quote.vehicle_category}")
        lines.append(f"乘客数: {quote.passenger_count}")
        lines.append(f"车龄: {quote.vehicle_age}年")
        lines.append(f"商业险折扣: {quote.commercial_discount:.1f}折")
        lines.append("")
        lines.append("-" * 50)
        lines.append("保费明细")
        lines.append("-" * 50)
        lines.append(f"交强险: {quote.compulsory_premium:.2f} 元")
        lines.append(f"第三者责任险 ({quote.third_party_limit}万): {quote.third_party_premium:.2f} 元")
        lines.append(f"车上人员（司机）: {quote.passenger_driver_premium:.2f} 元")
        lines.append(f"车上人员（乘客）: {quote.passenger_occupant_premium:.2f} 元")
        lines.append(f"医保外用药（三者）: {quote.medical_outside_third:.2f} 元")
        
        if quote.vehicle_fuel_type == "燃油车":
            if quote.medical_outside_driver > 0:
                lines.append(f"医保外用药（司机）: {quote.medical_outside_driver:.2f} 元")
            if quote.medical_outside_passenger > 0:
                lines.append(f"医保外用药（乘客）: {quote.medical_outside_passenger:.2f} 元")
            if quote.holiday_double_premium > 0:
                lines.append(f"节假日限额翻倍: {quote.holiday_double_premium:.2f} 元")
            if quote.mental_comfort_premium > 0:
                lines.append(f"精神抚慰金: {quote.mental_comfort_premium:.2f} 元")
        
        if quote.driving_accident_premium > 0:
            lines.append(f"驾意险: {quote.driving_accident_premium:.2f} 元")
        
        lines.append(f"道路救援: 免费（{quote.road_rescue_premium}次）")
        lines.append("")
        lines.append("-" * 50)
        lines.append("保费汇总")
        lines.append("-" * 50)
        lines.append(f"商业险保费: {quote.commercial_total:.2f} 元")
        lines.append(f"交强险保费: {quote.compulsory_premium:.2f} 元")
        lines.append("")
        lines.append(f"保费合计: {quote.total_premium:.2f} 元（人民币）")
        lines.append("")
        lines.append("=" * 50)
        lines.append("注：该报价仅供参考，具体保费金额以投保时系统金额为准。")
        lines.append("=" * 50)
        
        return "\n".join(lines)


# ========== 快捷使用函数 ==========

def quick_quote_fuel(license_plate: str, vehicle_category: str = "6座以下个人",
                      passenger_count: int = 4, third_party_limit: int = 300,
                      vehicle_age: float = 3.0) -> str:
    """
    快速生成燃油车报价
    
    示例:
        quote = quick_quote_fuel("粤B12345", "6座以下个人", 4, 300, 3.0)
        print(quote)
    """
    system = InsuranceQuotationSystem()
    quote = system.generate_quote(
        license_plate=license_plate,
        vehicle_fuel_type="燃油车",
        vehicle_category=vehicle_category,
        passenger_count=passenger_count,
        vehicle_age=vehicle_age,
        third_party_limit=third_party_limit,
        medical_outside_limit=10,
        has_holiday_double=False
    )
    return system.format_quote_text(quote)


def quick_quote_ev(license_plate: str, vehicle_category: str = "6座以下个人",
                    passenger_count: int = 4, third_party_limit: int = 300,
                    vehicle_age: float = 3.0) -> str:
    """
    快速生成新能源车报价
    
    示例:
        quote = quick_quote_ev("粤B12345", "6座以下个人", 4, 300, 3.0)
        print(quote)
    """
    system = InsuranceQuotationSystem()
    quote = system.generate_quote(
        license_plate=license_plate,
        vehicle_fuel_type="新能源车",
        vehicle_category=vehicle_category,
        passenger_count=passenger_count,
        vehicle_age=vehicle_age,
        third_party_limit=third_party_limit,
        medical_outside_limit=10
    )
    return system.format_quote_text(quote)


def compare_quotes(license_plate: str, vehicle_category: str = "6座以下个人",
                   passenger_count: int = 4, third_party_limit: int = 300,
                   vehicle_age: float = 3.0) -> str:
    """
    对比燃油车和新能源车报价
    """
    system = InsuranceQuotationSystem()
    
    fuel_quote = system.generate_quote(
        license_plate=license_plate,
        vehicle_fuel_type="燃油车",
        vehicle_category=vehicle_category,
        passenger_count=passenger_count,
        vehicle_age=vehicle_age,
        third_party_limit=third_party_limit,
        medical_outside_limit=10
    )
    
    ev_quote = system.generate_quote(
        license_plate=license_plate,
        vehicle_fuel_type="新能源车",
        vehicle_category=vehicle_category,
        passenger_count=passenger_count,
        vehicle_age=vehicle_age,
        third_party_limit=third_party_limit,
        medical_outside_limit=10
    )
    
    lines = []
    lines.append("=" * 70)
    lines.append("燃油車 vs 新能源車 報價對比")
    lines.append("=" * 70)
    lines.append(f"車牌號: {license_plate}")
    lines.append(f"車輛類型: {vehicle_category}, 乘客數: {passenger_count}")
    lines.append(f"車齡: {vehicle_age}年")
    lines.append(f"第三者責任險保額: {third_party_limit}萬")
    lines.append("")
    lines.append(f"商業險折扣: 燃油車 {fuel_quote.commercial_discount:.1f}折 / 新能源車 {ev_quote.commercial_discount:.1f}折")
    lines.append("")
    lines.append(f"{'項目':<20} {'燃油車':>15} {'新能源車':>15} {'差額':>10}")
    lines.append("-" * 70)
    lines.append(f"{'交強險':<20} {fuel_quote.compulsory_premium:>15.2f} {ev_quote.compulsory_premium:>15.2f} {ev_quote.compulsory_premium - fuel_quote.compulsory_premium:>10.2f}")
    lines.append(f"{'第三者責任險':<20} {fuel_quote.third_party_premium:>15.2f} {ev_quote.third_party_premium:>15.2f} {ev_quote.third_party_premium - fuel_quote.third_party_premium:>10.2f}")
    lines.append(f"{'車上人員':<20} {fuel_quote.passenger_driver_premium + fuel_quote.passenger_occupant_premium:>15.2f} {ev_quote.passenger_driver_premium + ev_quote.passenger_occupant_premium:>15.2f} {(ev_quote.passenger_driver_premium + ev_quote.passenger_occupant_premium) - (fuel_quote.passenger_driver_premium + fuel_quote.passenger_occupant_premium):>10.2f}")
    lines.append(f"{'醫保外用藥':<20} {fuel_quote.medical_outside_third:>15.2f} {ev_quote.medical_outside_third:>15.2f} {ev_quote.medical_outside_third - fuel_quote.medical_outside_third:>10.2f}")
    lines.append("-" * 70)
    lines.append(f"{'商業險合計':<20} {fuel_quote.commercial_total:>15.2f} {ev_quote.commercial_total:>15.2f} {ev_quote.commercial_total - fuel_quote.commercial_total:>10.2f}")
    lines.append(f"{'保費總計':<20} {fuel_quote.total_premium:>15.2f} {ev_quote.total_premium:>15.2f} {ev_quote.total_premium - fuel_quote.total_premium:>10.2f}")
    lines.append("=" * 70)
    
    diff = ev_quote.total_premium - fuel_quote.total_premium
    if diff > 0:
        lines.append(f"新能源車比燃油車貴: {diff:.2f} 元 ({diff/fuel_quote.total_premium*100:.1f}%)")
    else:
        lines.append(f"新能源車比燃油車便宜: {abs(diff):.2f} 元 ({abs(diff)/fuel_quote.total_premium*100:.1f}%)")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ========== 主程序 ==========

if __name__ == "__main__":
    # 示例：生成燃油车报价
    print("=== 燃油车报价示例 ===")
    print(quick_quote_fuel("粤B12345", "6座以下个人", 4, 300))
    print("\n\n")
    
    # 示例：生成新能源车报价
    print("=== 新能源车报价示例 ===")
    print(quick_quote_ev("粤B67890", "6座以下个人", 4, 300))
    print("\n\n")
    
    # 示例：对比报价
    print("=== 报价对比 ===")
    print(compare_quotes("粤B对比", "6座以下个人", 4, 300))
