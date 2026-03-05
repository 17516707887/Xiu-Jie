"""
工具函数模块 - 高德实时天气+预报版
文件名：m_tools.py
"""
import requests
from datetime import datetime, timedelta

# 核心配置：支持的城市列表（高德天气直接适配）
SUPPORTED_CITIES = [
    "上海", "北京", "天津", "重庆", "济南", "青岛",
    "南京", "杭州", "广州", "深圳", "武汉", "成都"
]

# 高德地图API Key（替换为自己的，或保持原有）
AMAP_KEY = "3c7234efc680b152b5cfa7b9ebd2633d"
# 高德天气接口（直接传城市名）
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# 全局状态：购物清单 + 多轮天气核心变量（重点修复）
shopping_list = []
last_city = None  # 保存上一次查询的城市（全局变量，跨函数共享）

# ===================== 核心工具：实时天气+预报查询（支持多轮） =====================
def get_weather(city: str = None, offset_days: int = 0, **kwargs) -> str:
    global last_city  # 声明使用全局变量
    # 空值/上下文处理：复用上次查询的城市
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
    
    try:
        # 根据offset_days选择接口类型：0=实时（base），>0=预报（all）
        extensions = "base" if offset_days == 0 else "all"
        response = requests.get(
            url=AMAP_WEATHER_URL,
            params={
                "city": city_clean,       # 直接传城市名
                "key": AMAP_KEY,          # 你的API Key
                "extensions": extensions, # base=实时，all=实时+预报
                "output": "json"          # 返回JSON格式
            },
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        weather_data = response.json()
        
        # 校验接口返回结果
        if weather_data.get("status") != "1":
            return f"⚠️ 高德接口调用失败：{weather_data.get('info', '未知错误')}"
        
        # 实时天气（offset_days=0）
        if offset_days == 0:
            if not weather_data.get("lives"):
                return f"⚠️ 未获取到{city_clean}的实时天气数据"
            live_data = weather_data["lives"][0]
            result = (f"{city_clean} 当前实时天气：{live_data['weather']}，温度{live_data['temperature']}℃，"
                      f"湿度{live_data['humidity']}%，{live_data['winddirection']}{live_data['windpower']}级")
            # 重点：成功查询实时天气后，更新全局last_city
            last_city = city_clean
        # 预报天气（明天/后天）
        else:
            if not weather_data.get("forecasts"):
                return f"⚠️ 未获取到{city_clean}的天气预报数据"
            forecast_data = weather_data["forecasts"][0]["casts"]
            # 校验offset_days是否在预报范围内（高德默认返回3天预报）
            if offset_days > len(forecast_data):
                return f"⚠️ 仅支持查询未来{len(forecast_data)}天的天气"
            
            # 取对应天数的预报（index=0=今天，1=明天，2=后天）
            target_forecast = forecast_data[offset_days]
            result = (f"{city_clean} {target_forecast['week']}（{target_forecast['date']}）天气："
                      f"{target_forecast['dayweather']}，气温{target_forecast['daytemp']}~{target_forecast['nighttemp']}℃，"
                      f"{target_forecast['daywind']}{target_forecast['daypower']}级")
        
        return result
    
    except Exception as e:
        return f"⚠️ 天气查询失败：{str(e)[:25]}（请检查API Key有效性）"

# ===================== 工具2：计算行李快递费（完全保留） =====================
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

# ===================== 工具3：查询日期和星期（完全保留） =====================
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

# ===================== 工具4：生成出行建议（完全保留） =====================
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

# ===================== 工具5-8：购物清单管理（完全保留） =====================
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

# ===================== 工具注册表（完全保留） =====================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市实时天气/预报（offset_days=0=实时，1=明天，2=后天）",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "要查询的城市名称"},
                    "offset_days": {"type": "integer", "description": "偏移天数，0=实时，1=明天，2=后天"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_express_fee",
            "description": "计算行李快递费（重量+距离）",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "description": "行李重量(kg)"},
                    "distance": {"type": "number", "description": "行程距离(km)"}
                },
                "required": ["weight", "distance"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date_info",
            "description": "查询日期/星期（offset_days=0=今天，1=明天）",
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
            "description": "生成出行建议（城市+重量+路程）",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目的地城市"},
                    "weight": {"type": "number", "description": "行李重量(kg)"},
                    "distance": {"type": "number", "description": "行程距离(km)"},
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
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_shopping_item",
            "description": "移除购物清单商品",
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
