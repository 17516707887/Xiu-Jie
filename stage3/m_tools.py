"""
工具函数模块 - 高德实时天气版（完整无删减）
核心：使用高德地图API获取100%实时天气，所有工具逻辑完整可用
文件名：m_tools.py
"""
import requests
from datetime import datetime, timedelta

# 核心配置：支持的城市列表（高德天气直接适配）
SUPPORTED_CITIES = [
    "上海", "北京", "天津", "重庆", "济南", "青岛",
    "南京", "杭州", "广州", "深圳", "武汉", "成都"
]

# 你提供的高德地图API Key（已填入）
AMAP_KEY = "3c7234efc680b152b5cfa7b9ebd2633d"
# 高德实时天气接口（直接传城市名，无需经纬度）
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# 全局状态：购物清单和历史查询城市
shopping_list = []
last_city = None

# ===================== 核心工具：实时天气查询（无模拟） =====================
def get_weather(city: str = None, **kwargs) -> str:
    global last_city
    # 空值/上下文处理
    if not city or city.strip() == "":
        prompt = "⚠️ 请输入要查询的城市（如上海、北京）"
        return prompt if not last_city else f"⚠️ 上次查询的是{last_city}，输入“是”可继续查询"
    
    city_clean = city.strip()
    # 支持“是”来复用上次查询的城市
    if city_clean in ["是", "是的", "对"] and last_city:
        city_clean = last_city
    
    # 校验城市是否支持
    if city_clean not in SUPPORTED_CITIES:
        return f"❌ 暂不支持【{city_clean}】的天气查询，支持列表：{', '.join(SUPPORTED_CITIES)}"
    
    # 调用高德实时天气接口（核心修复：直接传城市名）
    try:
        response = requests.get(
            url=AMAP_WEATHER_URL,
            params={
                "city": city_clean,       # 直接传城市名，无需经纬度
                "key": AMAP_KEY,          # 你的API Key
                "extensions": "base",     # base=实时天气，all=实时+预报
                "output": "json"          # 返回JSON格式
            },
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()  # 触发HTTP错误（如403/500）
        weather_data = response.json()
        
        # 校验接口返回结果
        if weather_data.get("status") != "1" or not weather_data.get("lives"):
            return f"⚠️ 高德接口未返回{city_clean}的实时天气数据"
        
        # 解析实时天气（100%真实数据）
        live_data = weather_data["lives"][0]
        weather_desc = live_data["weather"]       # 实时天气（晴/多云/雨等）
        temperature = live_data["temperature"]    # 实时温度
        wind_dir = live_data["winddirection"]     # 风向
        wind_power = live_data["windpower"]       # 风力
        humidity = live_data["humidity"]          # 湿度
        
        last_city = city_clean
        return (f"{city_clean} 当前实时天气：{weather_desc}，温度{temperature}℃，"
                f"湿度{humidity}%，{wind_dir}{wind_power}级")
    
    except Exception as e:
        # 仅返回真实错误，无任何模拟数据
        return f"⚠️ 实时天气查询失败：{str(e)[:25]}（请检查API Key有效性）"

# ===================== 工具2：计算行李快递费 =====================
def calculate_express_fee(weight: float = None, distance: float = None, **kwargs) -> str:
    if weight is None or distance is None:
        return "❓ 请提供行李重量(kg)和行程距离(km)（如：weight=2，distance=300）"
    try:
        weight_float = float(weight)
        distance_float = float(distance)
        if weight_float <= 0 or distance_float <= 0:
            return "❌ 重量和距离必须大于0"
    except ValueError:
        return "❌ 重量和距离必须是数字（如2.5、300）"
    
    # 计费规则：首重8元 + 2元/kg + 0.5元/100km
    total_fee = 8.0 + (2.0 * weight_float) + (0.5 * (distance_float // 100))
    return f"💰 快递费计算结果：{total_fee:.2f} 元（{weight_float}kg行李，{distance_float}km路程）"

# ===================== 工具3：查询日期和星期 =====================
def get_date_info(offset_days: int = 0, **kwargs) -> str:
    try:
        offset = int(offset_days)
    except (ValueError, TypeError):
        offset = 0
    
    target_date = datetime.now() + timedelta(days=offset)
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[target_date.weekday()]
    date_str = target_date.strftime("%Y年%m月%d日")
    
    if offset == 0:
        return f"📅 今天是：{date_str} {weekday}"
    elif offset == 1:
        return f"📅 明天是：{date_str} {weekday}"
    elif offset == -1:
        return f"📅 昨天是：{date_str} {weekday}"
    else:
        return f"📅 {abs(offset)}天{'后' if offset>0 else '前'}是：{date_str} {weekday}"

# ===================== 工具4：生成出行建议 =====================
def get_travel_preparation(city: str, weight: float, distance: float, travel_date: str = None, **kwargs) -> str:
    # 先获取实时天气
    weather_info = get_weather(city)
    if "⚠️" in weather_info or "❌" in weather_info:
        base_suggest = "携带常规衣物、舒适鞋子，根据行李重量选择背包/行李箱"
        return f"⚠️ {weather_info}，基础出行建议：{base_suggest}"
    
    # 根据天气生成针对性建议
    weather_type = weather_info.split("：")[1].split("，")[0]
    if "雨" in weather_type:
        items = "雨伞、雨衣、防水鞋套"
    elif "雪" in weather_type:
        items = "羽绒服、雪地靴、暖宝宝"
    elif "晴" in weather_type:
        items = "防晒霜、太阳镜、遮阳帽"
    else:
        items = "常规衣物、舒适鞋子"
    
    # 根据行李重量建议收纳方式
    if weight > 5:
        items += "，建议使用行李箱或办理托运"
    elif weight > 2:
        items += "，建议使用双肩包"
    else:
        items += "，可手提或使用小背包"
    
    # 根据路程建议额外准备
    if distance > 500:
        items += "，长途出行建议准备颈枕、眼罩、充电宝"
    elif distance > 200:
        items += "，中途可准备零食和饮用水"
    else:
        items += "，短途出行无需额外准备"
    
    # 拼接最终建议
    date_suffix = f"（{travel_date}）" if travel_date else ""
    return f"✈️ 去{city}{date_suffix}的出行建议：携带{items}，{weather_info}"

# ===================== 工具5-8：购物清单管理 =====================
def add_shopping_item(item: str = None, **kwargs) -> str:
    if not item or item.strip() == "":
        return "❓ 请输入要添加的商品名称（如：雨伞、充电宝）"
    item_clean = item.strip()
    if item_clean in shopping_list:
        return f"⚠️ 【{item_clean}】已在购物清单中，无需重复添加"
    shopping_list.append(item_clean)
    return f"✅ 已添加【{item_clean}】到购物清单，当前清单：{', '.join(shopping_list)}"

def get_shopping_list(**kwargs) -> str:
    if not shopping_list:
        return "🛒 购物清单为空"
    return f"🛒 购物清单：{', '.join(shopping_list)}"

def remove_shopping_item(item: str = None, **kwargs) -> str:
    if not item or item.strip() == "":
        return "❓ 请输入要移除的商品名称"
    item_clean = item.strip()
    if item_clean not in shopping_list:
        return f"⚠️ 【{item_clean}】不在购物清单中"
    shopping_list.remove(item_clean)
    remain = ", ".join(shopping_list) if shopping_list else "空"
    return f"✅ 已移除【{item_clean}】，剩余清单：{remain}"

def clear_shopping_list(**kwargs) -> str:
    count = len(shopping_list)
    shopping_list.clear()
    return f"🧹 已清空购物清单，共移除{count}项商品"

# ===================== 工具注册表（完整，与agent_stage3.py匹配） =====================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市实时天气（支持上海、北京、济南等城市）",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "要查询的城市名称（如上海、北京）"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_express_fee",
            "description": "根据行李重量和行程距离计算快递费",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "description": "行李重量（单位：kg）"},
                    "distance": {"type": "number", "description": "行程距离（单位：km）"}
                },
                "required": ["weight", "distance"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date_info",
            "description": "查询指定偏移天数的日期和星期（0=今天，1=明天，-1=昨天）",
            "parameters": {
                "type": "object",
                "properties": {
                    "offset_days": {"type": "integer", "description": "偏移天数，默认0"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_travel_preparation",
            "description": "根据城市、行李重量、路程生成出行建议（可选出行日期）",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目的地城市"},
                    "weight": {"type": "number", "description": "行李重量(kg)"},
                    "distance": {"type": "number", "description": "行程距离(km)"},
                    "travel_date": {"type": "string", "description": "出行日期（可选，如2026年03月04日）"}
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
            "description": "查看当前购物清单",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_shopping_item",
            "description": "从购物清单移除指定商品",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "要移除的商品名称"}
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
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

# 工具函数映射（agent调用时使用）
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
