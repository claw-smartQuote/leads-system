#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
港車北上報價系統 - Android App
使用 KivyMD 框架開發
"""

import os
os.environ['KIVY_NO_ARGS'] = '1'

from kivy.config import Config
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
Config.set('graphics', 'resizable', '0')

from kivy.core.window import Window
Window.size = (360, 640)

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, ObjectProperty

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dropdownitem import MDDropDownItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView

from quotation_system import InsuranceQuotationSystem

# KV Language Layout
KV = '''
ScreenManager:
    HomeScreen:
    QuoteScreen:
    ResultScreen:

<HomeScreen>:
    name: 'home'
    
    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)
        
        MDLabel:
            text: '港車北上'
            font_style: 'H3'
            halign: 'center'
            size_hint_y: None
            height: dp(60)
            theme_text_color: 'Primary'
        
        MDLabel:
            text: '報價系統'
            font_style: 'H4'
            halign: 'center'
            size_hint_y: None
            height: dp(50)
            theme_text_color: 'Secondary'
        
        Widget:
            size_hint_y: 0.3
        
        MDRaisedButton:
            text: '開始報價'
            font_size: dp(18)
            size_hint: None, None
            size: dp(200), dp(50)
            pos_hint: {'center_x': 0.5}
            on_release: root.manager.current = 'quote'
        
        MDFlatButton:
            text: '查看費率說明'
            font_size: dp(14)
            size_hint: None, None
            size: dp(200), dp(40)
            pos_hint: {'center_x': 0.5}
            on_release: app.show_info()
        
        Widget:
            size_hint_y: 0.5

<QuoteScreen>:
    name: 'quote'
    plate_input: plate_input
    fuel_type: fuel_type
    category: category
    passenger_input: passenger_input
    age_input: age_input
    third_party: third_party
    
    MDScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(20)
            spacing: dp(15)
            size_hint_y: None
            height: self.minimum_height
            
            MDLabel:
                text: '車輛信息'
                font_style: 'H5'
                size_hint_y: None
                height: dp(40)
            
            MDTextField:
                id: plate_input
                hint_text: '車牌號碼'
                helper_text: '例如：JD360'
                helper_text_mode: 'on_focus'
                size_hint_y: None
                height: dp(50)
            
            MDLabel:
                text: '車輛類型'
                size_hint_y: None
                height: dp(30)
            
            MDDropDownItem:
                id: fuel_type
                text: '燃油車'
                size_hint_y: None
                height: dp(50)
                on_release: app.menu_fuel.open()
            
            MDLabel:
                text: '使用性質'
                size_hint_y: None
                height: dp(30)
            
            MDDropDownItem:
                id: category
                text: '6座以下个人'
                size_hint_y: None
                height: dp(50)
                on_release: app.menu_category.open()
            
            MDTextField:
                id: passenger_input
                hint_text: '乘客數量'
                helper_text: '不含司機'
                helper_text_mode: 'on_focus'
                input_filter: 'int'
                text: '4'
                size_hint_y: None
                height: dp(50)
            
            MDLabel:
                text: '車齡計算方式'
                size_hint_y: None
                height: dp(30)
            
            MDDropDownItem:
                id: age_method
                text: '直接輸入車齡'
                size_hint_y: None
                height: dp(50)
                on_release: app.menu_age_method.open()
            
            # 方式1：直接輸入車齡
            MDTextField:
                id: age_input
                hint_text: '車齡（年）'
                helper_text: '例如：3.5'
                helper_text_mode: 'on_focus'
                input_filter: 'float'
                text: '3'
                size_hint_y: None
                height: dp(50)
                disabled: False
            
            # 方式2：輸入年份月份
            MDBoxLayout:
                id: year_month_box
                size_hint_y: None
                height: dp(50)
                spacing: dp(10)
                disabled: True
                opacity: 0
                
                MDTextField:
                    id: year_input
                    hint_text: '登記年份'
                    helper_text: '如：2021'
                    helper_text_mode: 'on_focus'
                    input_filter: 'int'
                    text: ''
                    size_hint_x: 0.5
                
                MDTextField:
                    id: month_input
                    hint_text: '月份(1-12)'
                    helper_text: '如：6'
                    helper_text_mode: 'on_focus'
                    input_filter: 'int'
                    text: ''
                    size_hint_x: 0.5
            
            MDLabel:
                text: '第三者責任險'
                size_hint_y: None
                height: dp(30)
            
            MDDropDownItem:
                id: third_party
                text: '300萬'
                size_hint_y: None
                height: dp(50)
                on_release: app.menu_third.open()
            
            MDBoxLayout:
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                MDRaisedButton:
                    text: '計算報價'
                    size_hint: 0.5, None
                    height: dp(50)
                    on_release: root.calculate_quote()
                
                MDFlatButton:
                    text: '返回'
                    size_hint: 0.5, None
                    height: dp(50)
                    on_release: root.manager.current = 'home'

<ResultScreen>:
    name: 'result'
    result_card: result_card
    
    MDScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(20)
            spacing: dp(15)
            size_hint_y: None
            height: self.minimum_height
            
            MDLabel:
                text: '報價單'
                font_style: 'H4'
                halign: 'center'
                size_hint_y: None
                height: dp(50)
            
            MDCard:
                id: result_card
                orientation: 'vertical'
                padding: dp(20)
                spacing: dp(10)
                size_hint_y: None
                height: self.minimum_height
                elevation: 4
                
                MDLabel:
                    text: '計算結果將顯示在這裡'
                    halign: 'center'
            
            MDBoxLayout:
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                MDRaisedButton:
                    text: '重新報價'
                    size_hint: 0.5, None
                    height: dp(50)
                    on_release: root.manager.current = 'quote'
                
                MDRaisedButton:
                    text: '分享報價'
                    size_hint: 0.5, None
                    height: dp(50)
                    on_release: root.share_quote()
'''

class HomeScreen(MDScreen):
    pass

class QuoteScreen(MDScreen):
    plate_input = ObjectProperty(None)
    fuel_type = ObjectProperty(None)
    category = ObjectProperty(None)
    passenger_input = ObjectProperty(None)
    age_method = ObjectProperty(None)
    age_input = ObjectProperty(None)
    year_input = ObjectProperty(None)
    month_input = ObjectProperty(None)
    year_month_box = ObjectProperty(None)
    third_party = ObjectProperty(None)
    
    def calculate_quote(self):
        app = MDApp.get_running_app()
        
        # 獲取輸入值
        plate = self.plate_input.text.strip()
        fuel = self.fuel_type.text.replace('車', '车')
        category = self.category.text
        age_method = self.age_method.text
        
        try:
            passengers = int(self.passenger_input.text or 4)
            third = int(self.third_party.text.replace('萬', '万').replace('万', ''))
        except ValueError:
            app.show_error("請檢查輸入的數值是否正確")
            return
        
        if not plate:
            app.show_error("請輸入車牌號碼")
            return
        
        # 根據選擇的方式計算車齡
        try:
            if age_method == '直接輸入車齡':
                vehicle_age = float(self.age_input.text or 3)
                quote = app.system.generate_quote_by_age(
                    license_plate=plate,
                    vehicle_fuel_type=fuel,
                    vehicle_category=category,
                    passenger_count=passengers,
                    vehicle_age=vehicle_age,
                    third_party_limit=third,
                    has_passenger=False,
                    driving_accident_type="无"
                )
            else:  # 年份月份方式
                year = int(self.year_input.text)
                month = int(self.month_input.text)
                if month < 1 or month > 12:
                    app.show_error("月份必須在1-12之間")
                    return
                
                quote = app.system.generate_quote_by_year_month(
                    license_plate=plate,
                    vehicle_fuel_type=fuel,
                    vehicle_category=category,
                    passenger_count=passengers,
                    register_year=year,
                    register_month=month,
                    third_party_limit=third,
                    has_passenger=False,
                    driving_accident_type="无"
                )
            
            # 保存結果並跳轉
            app.current_quote = quote
            self.manager.get_screen('result').display_result(quote)
            self.manager.current = 'result'
            
        except Exception as e:
            app.show_error(f"計算出錯：{str(e)}")

class ResultScreen(MDScreen):
    result_card = ObjectProperty(None)
    
    def display_result(self, quote):
        # 清空現有內容
        self.result_card.clear_widgets()
        
        # 添加結果標籤
        result_text = f"""
[size=18][b]車輛信息[/b][/size]
車牌號：{quote.license_plate}
車輛類型：{quote.vehicle_fuel_type}
使用性質：{quote.vehicle_category}
乘客數：{quote.passenger_count}人
車齡：{quote.vehicle_age}年
商業險折扣：{quote.commercial_discount:.1f}折

[size=18][b]保費明細[/b][/size]
交強險：{quote.compulsory_premium:.2f} 元
第三者責任險 ({quote.third_party_limit}萬)：{quote.third_party_premium:.2f} 元
醫保外用藥：{quote.medical_outside_third:.2f} 元
道路救援：免費

[size=20][b]保費合計：{quote.total_premium:.2f} 元[/b][/size]
        """
        
        label = MDLabel(
            text=result_text,
            markup=True,
            size_hint_y=None,
            height=self.result_card.height
        )
        label.bind(texture_size=label.setter('size'))
        self.result_card.add_widget(label)
    
    def share_quote(self):
        app = MDApp.get_running_app()
        if hasattr(app, 'current_quote'):
            quote = app.current_quote
            share_text = f"""港車北上報價單
車牌：{quote.license_plate}
車型：{quote.vehicle_fuel_type}
保費：{quote.total_premium:.2f}元（人民幣）

此報價僅供參考"""
            
            # 調用系統分享功能
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(share_text)
            app.show_info("報價單已復制到剪貼板")

class GangCheApp(MDApp):
    system = None
    current_quote = None
    menu_fuel = None
    menu_category = None
    menu_third = None
    menu_age_method = None
    
    def build(self):
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.theme_style = 'Light'
        
        # 初始化報價系統
        self.system = InsuranceQuotationSystem()
        
        # 加載KV
        return Builder.load_string(KV)
    
    def on_start(self):
        # 創建下拉菜單
        self.create_menus()
    
    def create_menus(self):
        # 車輛類型菜單
        fuel_items = [
            {"text": "燃油車", "on_release": lambda x="燃油車": self.set_fuel(x)},
            {"text": "新能源車", "on_release": lambda x="新能源車": self.set_fuel(x)},
        ]
        self.menu_fuel = MDDropdownMenu(
            caller=self.root.get_screen('quote').fuel_type,
            items=fuel_items,
            width_mult=4,
        )
        
        # 使用性質菜單
        category_items = [
            {"text": "6座以下个人", "on_release": lambda x="6座以下个人": self.set_category(x)},
            {"text": "6座以下企业", "on_release": lambda x="6座以下企业": self.set_category(x)},
            {"text": "6-10座个人", "on_release": lambda x="6-10座个人": self.set_category(x)},
            {"text": "6-10座企业", "on_release": lambda x="6-10座企业": self.set_category(x)},
        ]
        self.menu_category = MDDropdownMenu(
            caller=self.root.get_screen('quote').category,
            items=category_items,
            width_mult=4,
        )
        
        # 車齡計算方式菜單
        age_method_items = [
            {"text": "直接輸入車齡", "on_release": lambda x="直接輸入車齡": self.set_age_method(x)},
            {"text": "年份和月份", "on_release": lambda x="年份和月份": self.set_age_method(x)},
        ]
        self.menu_age_method = MDDropdownMenu(
            caller=self.root.get_screen('quote').age_method,
            items=age_method_items,
            width_mult=4,
        )
        
        # 第三者保額菜單
        third_items = [
            {"text": "100萬", "on_release": lambda x="100萬": self.set_third(x)},
            {"text": "150萬", "on_release": lambda x="150萬": self.set_third(x)},
            {"text": "200萬", "on_release": lambda x="200萬": self.set_third(x)},
            {"text": "300萬", "on_release": lambda x="300萬": self.set_third(x)},
            {"text": "400萬", "on_release": lambda x="400萬": self.set_third(x)},
            {"text": "500萬", "on_release": lambda x="500萬": self.set_third(x)},
        ]
        self.menu_third = MDDropdownMenu(
            caller=self.root.get_screen('quote').third_party,
            items=third_items,
            width_mult=4,
        )
    
    def set_fuel(self, text):
        self.root.get_screen('quote').fuel_type.text = text
        self.menu_fuel.dismiss()
    
    def set_category(self, text):
        self.root.get_screen('quote').category.text = text
        self.menu_category.dismiss()
    
    def set_third(self, text):
        self.root.get_screen('quote').third_party.text = text
        self.menu_third.dismiss()
    
    def set_age_method(self, text):
        quote_screen = self.root.get_screen('quote')
        quote_screen.age_method.text = text
        
        # 切換輸入框顯示
        if text == '直接輸入車齡':
            quote_screen.age_input.disabled = False
            quote_screen.age_input.opacity = 1
            quote_screen.year_month_box.disabled = True
            quote_screen.year_month_box.opacity = 0
        else:  # 年份和月份
            quote_screen.age_input.disabled = True
            quote_screen.age_input.opacity = 0
            quote_screen.year_month_box.disabled = False
            quote_screen.year_month_box.opacity = 1
        
        self.menu_age_method.dismiss()
    
    def show_info(self, message=""):
        if not message:
            message = """費率說明：
\n燃油車折扣：
- 3年以上：七折
- 2年以上：八折  
- 2年以下：九折
\n新能源車：固定九折
\n駕意險：
- 30萬：每位40元
- 50萬：每位60元"""
        
        dialog = MDDialog(
            title="港車北上報價系統",
            text=message,
            buttons=[
                MDFlatButton(
                    text="確定",
                    on_release=lambda x: dialog.dismiss()
                ),
            ],
        )
        dialog.open()
    
    def show_error(self, message):
        dialog = MDDialog(
            title="出錯",
            text=message,
            buttons=[
                MDFlatButton(
                    text="確定",
                    on_release=lambda x: dialog.dismiss()
                ),
            ],
        )
        dialog.open()

if __name__ == '__main__':
    GangCheApp().run()
