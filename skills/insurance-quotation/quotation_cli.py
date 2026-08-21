#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
永诚保险报价系统 - 命令行界面
版本: 2.0 (V.13 费率表)
"""

import argparse
import sys
from quotation_system import (
    InsuranceQuotationSystem, 
    quick_quote_fuel, 
    quick_quote_ev, 
    compare_quotes,
    SYSTEM_VERSION,
    RATE_VERSION
)


def main():
    parser = argparse.ArgumentParser(
        description=f'永诚保险报价系统 v{SYSTEM_VERSION} - 支持燃油车与新能源车 (费率: {RATE_VERSION})',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 燃油车报价
  python3 quotation_cli.py fuel -p 粤B12345 -c "6座以下个人" -n 4 -t 300
  
  # 新能源车报价
  python3 quotation_cli.py ev -p 粤B12345 -c "6座以下个人" -n 4 -t 300
  
  # 对比报价
  python3 quotation_cli.py compare -p 粤B12345 -c "6座以下个人" -n 4
  
支持的車輛類型:
  - 6座以下个人
  - 6座以下企业
  - 6-10座个人
  - 6-10座企业

支持的第三者責任險保額:
  - 100, 150, 200, 300, 400, 500 (萬)
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # === 燃油车报价 ===
    fuel_parser = subparsers.add_parser('fuel', help='燃油车报价')
    fuel_parser.add_argument('-p', '--plate', required=True, help='车牌号')
    fuel_parser.add_argument('-c', '--category', default='6座以下个人', 
                            choices=['6座以下个人', '6座以下企业', '6-10座个人', '6-10座企业'],
                            help='车辆类型 (默认: 6座以下个人)')
    fuel_parser.add_argument('-n', '--passengers', type=int, default=4, 
                            help='乘客数量 (默认: 4)')
    fuel_parser.add_argument('-t', '--third-party', type=int, default=300,
                            choices=[100, 150, 200, 300, 400, 500],
                            help='第三者责任险保额/万 (默认: 300)')
    fuel_parser.add_argument('-m', '--medical', type=int, default=10,
                            choices=[0, 10, 20, 30, 50, 100],
                            help='医保外用药保额/万 (默认: 10)')
    fuel_parser.add_argument('--holiday-double', action='store_true',
                            help='投保节假日限额翻倍')
    fuel_parser.add_argument('--medical-driver', action='store_true',
                            help='投保司机医保外用药')
    fuel_parser.add_argument('--medical-passenger', action='store_true',
                            help='投保乘客医保外用药')
    
    # === 新能源车报价 ===
    ev_parser = subparsers.add_parser('ev', help='新能源车报价')
    ev_parser.add_argument('-p', '--plate', required=True, help='车牌号')
    ev_parser.add_argument('-c', '--category', default='6座以下个人',
                          choices=['6座以下个人', '6座以下企业', '6-10座个人', '6-10座企业'],
                          help='车辆类型 (默认: 6座以下个人)')
    ev_parser.add_argument('-n', '--passengers', type=int, default=4,
                          help='乘客数量 (默认: 4)')
    ev_parser.add_argument('-t', '--third-party', type=int, default=300,
                          choices=[100, 150, 200, 300, 400, 500],
                          help='第三者责任险保额/万 (默认: 300)')
    ev_parser.add_argument('-m', '--medical', type=int, default=10,
                          choices=[0, 10, 20, 30, 50, 100],
                          help='医保外用药保额/万 (默认: 10)')
    
    # === 对比报价 ===
    compare_parser = subparsers.add_parser('compare', help='对比燃油车与新能源车报价')
    compare_parser.add_argument('-p', '--plate', required=True, help='车牌号')
    compare_parser.add_argument('-c', '--category', default='6座以下个人',
                               choices=['6座以下个人', '6座以下企业', '6-10座个人', '6-10座企业'],
                               help='车辆类型 (默认: 6座以下个人)')
    compare_parser.add_argument('-n', '--passengers', type=int, default=4,
                               help='乘客数量 (默认: 4)')
    compare_parser.add_argument('-t', '--third-party', type=int, default=300,
                               choices=[100, 150, 200, 300, 400, 500],
                               help='第三者责任险保额/万 (默认: 300)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'fuel':
            # 燃油车报价
            system = InsuranceQuotationSystem()
            quote = system.generate_quote(
                license_plate=args.plate,
                vehicle_fuel_type="燃油车",
                vehicle_category=args.category,
                passenger_count=args.passengers,
                third_party_limit=args.third_party,
                medical_outside_limit=args.medical,
                has_holiday_double=args.holiday_double,
                has_medical_driver=args.medical_driver,
                has_medical_passenger=args.medical_passenger
            )
            print(system.format_quote_text(quote))
            
        elif args.command == 'ev':
            # 新能源车报价
            quote_text = quick_quote_ev(
                args.plate, 
                args.category, 
                args.passengers, 
                args.third_party
            )
            print(quote_text)
            
        elif args.command == 'compare':
            # 对比报价
            comparison = compare_quotes(
                args.plate,
                args.category,
                args.passengers,
                args.third_party
            )
            print(comparison)
            
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
