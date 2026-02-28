"""
工具函数模块 - 包含天气查询、快递费计算、购物清单管理
"""

import json
import requests
import urllib.parse
import warnings
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv
import os
import re
import random

# 屏蔽SSL警告
warnings.filterwarnings('ignore', category=InsecureRequestWarning)
load_dotenv()

# 全局状态
shopping_list = []
last_city = None
last_weight = None
last_distance = None

# -------------------------- 工具1：天气查询（增强版，多个备用接口）--------------------------
def get_weather(city: str = None) -> str:
    """
    查询指定城市的实时天气 - 使用多个备用接口
    """
    global last_city
    
    # 错误处理：城市名为空
    if not city or city.strip() == "":
        if last_city:
            return f"⚠️ 您没有输入城市，上次查询的是【{last_city}】，是否继续查询？(请输入「是」或新城市名)"
        return "❌ 错误：城市名称不能为空！请输入如「北京」「上海」的城市名。"
    
    city_clean = city.strip()
    
    # 处理"是"的回应
    if city_clean in ["是", "是的", "对", "嗯"] and last_city:
        city_clean = last_city
        print(f"[系统] 使用上次城市: {city_clean}")
    
    # 更新最后查询的城市
    last_city = city_clean
    
    # 尝试多个天气接口
    weather_result = try_multiple_weather_apis(city_clean)
    
    if weather_result:
        return weather_result
    else:
        # 如果所有接口都失败，返回模拟数据（演示用）
        return get_mock_weather(city_clean)

def try_multiple_weather_apis(city: str) -> str:
    """尝试多个天气API"""
    
    # API列表
    apis = [
        {
            "name": "wttr.in",
            "url": f"https://wttr.in/{urllib.parse.quote(city)}?format=%C+%t",
            "parser": parse_wttr_response
        },
        {
            "name": "wttr.in备用",
            "url": f"https://wttr.in/{urllib.parse.quote(city)}?format=%c+%t",
            "parser": parse_wttr_response
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }
    
    # 遍历尝试每个API
    for api in apis:
        try:
            print(f"[调试] 尝试API: {api['name']}")
            res = requests.get(
                api["url"],
                headers=headers,
                timeout=8,  # 缩短超时时间
                verify=False
            )
            res.raise_for_status()
            weather_content = res.text.strip()
            
            if weather_content and "Unknown" not in weather_content:
                return api["parser"](city, weather_content)
        except Exception as e:
            print(f"[调试] API {api['name']} 失败: {str(e)[:30]}")
            continue
    
    return None

def parse_wttr_response(city: str, content: str) -> str:
    """解析 wttr.in 的响应"""
    content = content.strip()
    # 清理内容
    content = re.sub(r'\s+', ' ', content)
    
    if "Unknown location" in content:
        return None
    
    return f"🌤️ {city}：{content}"

def get_mock_weather(city: str) -> str:
    """返回模拟天气数据（当所有API都失败时使用）"""
    weather_conditions = ["晴天", "多云", "阴天", "小雨", "中雨", "雷阵雨"]
    temperatures = range(15, 30)
    
    condition = random.choice(weather_conditions)
    temp = random.choice(temperatures)
    
    return f"🌤️ {city}：{condition}，{temp}℃ (模拟数据)"

# -------------------------- 工具2：快递费计算 --------------------------
def calculate_express_fee(weight: float = None, distance: float = None) -> str:
    """
    根据重量(kg)和距离(km)计算快递费
    """
    global last_weight, last_distance
    
    # 参数缺失处理
    if weight is None and distance is None:
        return "❓ 请提供物品重量(kg)和运输距离(km)，例如「2kg 300km」"
    
    if weight is None:
        return "❓ 缺少重量参数，请输入物品重量(kg)"
    
    if distance is None:
        return "❓ 缺少距离参数，请输入运输距离(km)"
    
    # 类型转换
    try:
        weight = float(weight)
        distance = float(distance)
    except (ValueError, TypeError):
        return "❌ 错误：重量和距离必须是数字！"
    
    # 数值校验
    if weight <= 0:
        return "❌ 错误：重量必须大于0kg"
    if distance <= 0:
        return "❌ 错误：距离必须大于0km"
    
    # 保存到历史
    last_weight = weight
    last_distance = distance
    
    # 计算费用
    base_fee = 8.0
    weight_fee = 2.0 * weight
    distance_fee = 0.5 * (distance // 100)
    total = base_fee + weight_fee + distance_fee
    
    return f"📦 快递费计算结果：\n• 基础费：{base_fee}元\n• 重量费：{weight:.1f}kg × 2元 = {weight_fee}元\n• 距离费：{distance:.0f}km ÷ 100 × 0.5元 = {distance_fee}元\n• 总计：{total:.2f}元"

# -------------------------- 工具3：购物清单管理 --------------------------
def add_shopping_item(item: str = None) -> str:
    """添加商品到购物清单"""
    global shopping_list
    
    if not item or item.strip() == "":
        return "❓ 请输入要添加的商品名称，例如「添加苹果」"
    
    item = item.strip()
    
    if item in shopping_list:
        return f"⚠️ 【{item}】已在清单中"
    
    shopping_list.append(item)
    return f"✅ 已添加【{item}】，当前清单：{', '.join(shopping_list)}"

def get_shopping_list() -> str:
    """获取购物清单"""
    global shopping_list
    
    if not shopping_list:
        return "🛒 购物清单为空，可以使用「添加苹果」来添加商品"
    
    items = "、".join(shopping_list)
    return f"🛒 当前清单（{len(shopping_list)}项）：{items}"

def remove_shopping_item(item: str = None) -> str:
    """从购物清单移除商品"""
    global shopping_list
    
    if not item or item.strip() == "":
        return "❓ 请输入要移除的商品名称，例如「移除苹果」"
    
    item = item.strip()
    
    if item not in shopping_list:
        return f"⚠️ 【{item}】不在清单中，当前清单有：{', '.join(shopping_list)}"
    
    shopping_list.remove(item)
    return f"✅ 已移除【{item}】，剩余：{', '.join(shopping_list)}"

def clear_shopping_list() -> str:
    """清空购物清单"""
    global shopping_list
    count = len(shopping_list)
    shopping_list = []
    return f"🧹 已清空清单（共{count}项）"

# -------------------------- 工具注册表 --------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气，如果不输入城市会询问",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，如北京、上海"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_express_fee",
            "description": "计算快递费，需要重量(kg)和距离(km)",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "description": "重量(kg)"},
                    "distance": {"type": "number", "description": "距离(km)"}
                },
                "required": ["weight", "distance"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_shopping_item",
            "description": "添加商品到购物清单",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "商品名称"}
                },
                "required": ["item"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_shopping_list",
            "description": "查看购物清单",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_shopping_item",
            "description": "从购物清单移除商品",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "商品名称"}
                },
                "required": ["item"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_shopping_list",
            "description": "清空购物清单",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# 工具函数映射
TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate_express_fee": calculate_express_fee,
    "add_shopping_item": add_shopping_item,
    "get_shopping_list": get_shopping_list,
    "remove_shopping_item": remove_shopping_item,
    "clear_shopping_list": clear_shopping_list
}