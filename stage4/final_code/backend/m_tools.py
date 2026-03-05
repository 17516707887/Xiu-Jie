
﻿"""
工具函数模块 - 高德实时天气版
支持：天气查询、快递费计算、日期查询、出行建议、购物清单管理
"""

import requests
from datetime import datetime, timedelta
import warnings
from urllib3.exceptions import InsecureRequestWarning

# 屏蔽SSL警告
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# ===================== 高德地图API配置 =====================
# ⚠️ 重要：请替换为你自己的高德API Key
# 申请地址：https://lbs.amap.com/
AMAP_KEY = "3c7234efc680b152b5cfa7b9ebd2633d"  # 你的API Key
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# 支持的城市列表
SUPPORTED_CITIES = [
    "北京", "上海", "广州", "深圳", "天津", "重庆",
    "南京", "杭州", "成都", "武汉", "西安", "济南",
    "青岛", "大连", "厦门", "苏州", "郑州", "长沙"
]

# ===================== 全局状态 =====================
shopping_list = []
last_city = None


# ===================== 工具1：实时天气查询 =====================
def get_weather(city: str = None, **kwargs) -> str:
    """查询城市实时天气（高德API，100%真实数据）"""
    global last_city
    
    # 参数校验
    if not city or city.strip() == "":
        if last_city:
            return f"⚠️ 上次查询的是【{last_city}】，输入「是」可继续查询"
        return "❓ 请输入要查询的城市（如：上海、北京）"
    
    city_clean = city.strip()
    
    # 支持"是"复用上次城市
    if city_clean in ["是", "是的", "对", "嗯"] and last_city:
        city_clean = last_city
    
    # 校验城市支持
    if city_clean not in SUPPORTED_CITIES:
        return f"❌ 暂不支持【{city_clean}】，支持城市：{', '.join(SUPPORTED_CITIES[:8])}..."
    
    # 调用高德API
    try:
        response = requests.get(
            url=AMAP_WEATHER_URL,
            params={
                "city": city_clean,
                "key": AMAP_KEY,
                "extensions": "base",
                "output": "json"
            },
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        data = response.json()
        
        # 检查返回状态
        if data.get("status") != "1" or not data.get("lives"):
            error_info = data.get("info", "未知错误")
            return f"⚠️ 天气接口返回错误：{error_info}"
        
        # 解析天气数据
        live = data["lives"][0]
        weather = live["weather"]
        temp = live["temperature"]
        humidity = live["humidity"]
        wind_dir = live["winddirection"]
        wind_power = live["windpower"]
        
        last_city = city_clean
        
        return f"🌤️ {city_clean}：{weather}，{temp}℃，湿度{humidity}%，{wind_dir}风{wind_power}级"
        
    except requests.exceptions.Timeout:
        return "⚠️ 天气查询超时，请稍后再试"
    except requests.exceptions.RequestException as e:
        return f"⚠️ 网络请求失败：{str(e)[:20]}"
    except Exception as e:
        return f"⚠️ 天气查询异常：{str(e)[:20]}"


# ===================== 工具2：快递费计算 =====================
def calculate_express_fee(weight: float = None, distance: float = None, **kwargs) -> str:
    """计算快递费"""
    
    # 参数校验
    if weight is None and distance is None:
        return "❓ 请提供行李重量(kg)和距离(km)，例如：weight=2, distance=300"
    
    if weight is None:
        return "❓ 缺少重量参数，请输入行李重量(kg)"
    
    if distance is None:
        return "❓ 缺少距离参数，请输入运输距离(km)"
    
    # 类型转换
    try:
        w = float(weight)
        d = float(distance)
    except (ValueError, TypeError):
        return "❌ 重量和距离必须是数字"
    
    # 数值校验
    if w <= 0:
        return "❌ 重量必须大于0kg"
    if d <= 0:
        return "❌ 距离必须大于0km"
    
    # 计费规则
    base_fee = 8.0                    # 基础费
    weight_fee = 2.0 * w              # 重量费：2元/kg
    distance_fee = 0.5 * (d // 100)   # 距离费：每100公里0.5元
    
    total = base_fee + weight_fee + distance_fee
    
    return (f"📦 快递费：{total:.2f}元\n"
            f"   • 基础费：{base_fee}元\n"
            f"   • 重量费：{w:.1f}kg × 2元 = {weight_fee:.1f}元\n"
            f"   • 距离费：{d:.0f}km ÷ 100 × 0.5元 = {distance_fee:.1f}元")


# ===================== 工具3：日期查询 =====================
def get_date_info(offset_days: int = 0, **kwargs) -> str:
    """查询日期和星期"""
    try:
        offset = int(offset_days) if offset_days is not None else 0
    except (ValueError, TypeError):
        offset = 0
    
    target = datetime.now() + timedelta(days=offset)
    
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[target.weekday()]
    date_str = target.strftime("%Y年%m月%d日")
    
    if offset == 0:
        return f"📅 今天是 {date_str} {weekday}"
    elif offset == 1:
        return f"📅 明天是 {date_str} {weekday}"
    elif offset == -1:
        return f"📅 昨天是 {date_str} {weekday}"
    elif offset > 0:
        return f"📅 {offset}天后是 {date_str} {weekday}"
    else:
        return f"📅 {abs(offset)}天前是 {date_str} {weekday}"


# ===================== 工具4：出行建议 =====================
def get_travel_preparation(city: str = None, weight: float = None, 
                          distance: float = None, travel_date: str = None, **kwargs) -> str:
    """生成出行建议"""
    
    # 参数校验
    if not city:
        return "❓ 请提供目的地城市"
    if weight is None:
        return "❓ 请提供行李重量(kg)"
    if distance is None:
        return "❓ 请提供路程距离(km)"
    
    # 先获取天气
    weather_info = get_weather(city)
    
    # 根据天气生成建议
    if "🌤️" in weather_info:
        # 解析天气
        weather_detail = weather_info.split("：")[1] if "：" in weather_info else ""
        
        if "雨" in weather_detail:
            items = "雨伞、雨衣、防水袋"
        elif "雪" in weather_detail:
            items = "羽绒服、手套、暖宝宝"
        elif "晴" in weather_detail:
            items = "防晒霜、太阳镜、帽子"
        else:
            items = "常规衣物"
        
        # 根据重量建议
        if weight > 10:
            items += "，建议使用行李箱托运"
        elif weight > 5:
            items += "，建议使用大背包"
        elif weight > 2:
            items += "，建议使用双肩包"
        else:
            items += "，可手提"
        
        # 根据距离建议
        if distance > 500:
            items += "，长途准备充电宝、颈枕、眼罩"
        elif distance > 200:
            items += "，中途准备零食、饮用水"
        
        date_hint = f"（{travel_date}）" if travel_date else ""
        return f"✈️ 去{city}{date_hint}：{items}，{weather_info}"
    else:
        # 天气查询失败，给出基础建议
        return f"✈️ 去{city}：携带常规衣物，{weather_info}"


# ===================== 工具5-8：购物清单管理 =====================
def add_shopping_item(item: str = None, **kwargs) -> str:
    """添加商品到购物清单"""
    if not item or item.strip() == "":
        return "❓ 请输入要添加的商品名称"
    
    item_clean = item.strip()
    
    if item_clean in shopping_list:
        return f"⚠️ 【{item_clean}】已在清单中"
    
    shopping_list.append(item_clean)
    current = "、".join(shopping_list) if shopping_list else "空"
    return f"✅ 已添加【{item_clean}】，当前清单：{current}"


def get_shopping_list(**kwargs) -> str:
    """查看购物清单"""
    if not shopping_list:
        return "🛒 购物清单为空"
    
    items = "、".join(shopping_list)
    return f"🛒 购物清单（{len(shopping_list)}项）：{items}"


def remove_shopping_item(item: str = None, **kwargs) -> str:
    """从购物清单移除商品"""
    if not item or item.strip() == "":
        return "❓ 请输入要移除的商品名称"
    
    item_clean = item.strip()
    
    if item_clean not in shopping_list:
        return f"⚠️ 【{item_clean}】不在清单中"
    
    shopping_list.remove(item_clean)
    
    if shopping_list:
        return f"✅ 已移除【{item_clean}】，剩余：{', '.join(shopping_list)}"
    else:
        return f"✅ 已移除【{item_clean}】，清单已清空"


def clear_shopping_list(**kwargs) -> str:
    """清空购物清单"""
    global shopping_list
    count = len(shopping_list)
    shopping_list = []
    return f"🧹 已清空购物清单（共移除{count}项）"


# ===================== 工具注册表 =====================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市实时天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，如上海、北京"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_express_fee",
            "description": "根据重量和距离计算快递费",
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
            "name": "get_date_info",
            "description": "查询日期和星期",
            "parameters": {
                "type": "object",
                "properties": {
                    "offset_days": {"type": "integer", "description": "偏移天数，0=今天，1=明天，-1=昨天"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_travel_preparation",
            "description": "生成出行建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目的地城市"},
                    "weight": {"type": "number", "description": "行李重量(kg)"},
                    "distance": {"type": "number", "description": "路程距离(km)"},
                    "travel_date": {"type": "string", "description": "出行日期（可选）"}
                },
                "required": ["city", "weight", "distance"]
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
            "parameters": {"type": "object", "properties": {}}
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
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

# 工具函数映射
TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate_express_fee": calculate_express_fee,
    "get_date_info": get_date_info,
    "get_travel_preparation": get_travel_preparation,
    "add_shopping_item": add_shopping_item,
    "get_shopping_list": get_shopping_list,
    "remove_shopping_item": remove_shopping_item,
    "clear_shopping_list": clear_shopping_list
}

