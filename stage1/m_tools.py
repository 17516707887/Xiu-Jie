import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# -------------------------- 工具1：查询实时天气 --------------------------
def get_weather(city: str) -> str:
    """
    查询指定城市的实时天气（使用wttr.in公开接口）
    :param city: 城市名，如"北京"
    :return: 天气信息字符串
    """
    try:
        url = f"http://wttr.in/{city}?format=%C+%t"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return f"{city} 当前天气：{res.text.strip()}"
        else:
            return f"{city} 天气查询失败"
    except Exception as e:
        return f"暂时无法获取 {city} 天气：{str(e)}"

# -------------------------- 工具2：计算快递费 --------------------------
def calculate_express_fee(weight: float, distance: float) -> str:
    """
    根据重量和距离计算快递费（示例规则）
    :param weight: 物品重量，单位kg
    :param distance: 距离，单位km
    :return: 快递费字符串
    """
    if weight <= 0 or distance <= 0:
        return "重量和距离必须大于0"
    
    base_fee = 8.0  # 基础费用
    weight_fee = 2.0 * weight  # 每公斤2元
    distance_fee = 0.5 * (distance // 100)  # 每100公里0.5元
    
    total = base_fee + weight_fee + distance_fee
    return f"快递费计算：基础费{base_fee}元 + 重量费{weight_fee}元 + 距离费{distance_fee}元 = 总计{total:.2f}元"

# -------------------------- 工具3：记录购物清单 --------------------------
shopping_list = []

def add_shopping_item(item: str) -> str:
    """
    添加商品到购物清单
    :param item: 商品名称
    :return: 操作结果
    """
    if item in shopping_list:
        return f"{item} 已经在购物清单中了。"
    shopping_list.append(item)
    return f"已将 {item} 添加到购物清单。当前清单：{', '.join(shopping_list)}"

def get_shopping_list() -> str:
    """
    获取当前购物清单
    """
    if not shopping_list:
        return "购物清单为空。"
    return "当前购物清单：" + ", ".join(shopping_list)

# 工具注册表（符合千问API格式要求）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "要查询天气的城市名称，如'北京'"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_express_fee",
            "description": "根据物品重量和距离计算快递费",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "description": "物品重量，单位kg"},
                    "distance": {"type": "number", "description": "距离，单位km"}
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
                    "item": {"type": "string", "description": "要添加的商品名称"}
                },
                "required": ["item"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_shopping_list",
            "description": "获取当前购物清单",
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
    "get_shopping_list": get_shopping_list
}