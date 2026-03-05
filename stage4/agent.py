"""
生活助手AI Agent - 完整版（修复上下文记忆问题）
修复：当用户说"明天呢"时，正确结合历史对话查询天气而不是日期
"""

import dashscope
from dashscope import Generation
import json
import re
import ast
from datetime import datetime
from dotenv import load_dotenv
import os

# 导入工具模块
from m_tools import TOOL_FUNCTIONS, TOOLS, SUPPORTED_CITIES

# ===================== 初始化配置 =====================
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope.api_key:
    print("⚠️ 警告: 未配置API Key，将使用模拟模式")
    # 设置一个模拟key避免报错
    dashscope.api_key = "mock_key"


# ===================== 对话记忆管理类 =====================
class ConversationMemory:
    """增强版对话记忆管理 - 支持多轮上下文"""
    
    def __init__(self, max_rounds: int = 10):
        self.history = []          # 对话历史
        self.max_rounds = max_rounds
        self.context = {            # 上下文信息
            "last_city": None,
            "last_weight": None,
            "last_distance": None,
            "last_topic": None,
            "last_date_offset": 0,
            "last_tool_called": None  # 新增：记录上次调用的工具
        }
    
    def add(self, user_input: str, assistant_response: str, tool_used: str = None):
        """添加一轮对话"""
        interaction = {
            "user": user_input,
            "assistant": assistant_response,
            "tool": tool_used,
            "timestamp": datetime.now().isoformat()
        }
        self.history.append(interaction)
        
        # 更新上次调用的工具
        if tool_used:
            self.context["last_tool_called"] = tool_used
        
        # 提取上下文信息
        self._extract_context(user_input)
        
        # 限制历史长度
        if len(self.history) > self.max_rounds:
            self.history.pop(0)
    
    def _extract_context(self, text: str):
        """从用户输入提取关键信息"""
        # 提取城市
        for city in SUPPORTED_CITIES:
            if city in text:
                self.context["last_city"] = city
                break
        
        # 提取数字（重量/距离）
        numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
        if numbers:
            if "kg" in text or "公斤" in text or "重量" in text or "行李" in text:
                self.context["last_weight"] = float(numbers[-1])
            if "km" in text or "公里" in text or "距离" in text or "路程" in text:
                self.context["last_distance"] = float(numbers[-1])
        
        # 提取话题
        if "天气" in text:
            self.context["last_topic"] = "weather"
        elif "快递" in text or "运费" in text or "费用" in text:
            self.context["last_topic"] = "express"
        elif "购物" in text or "清单" in text or "买" in text:
            self.context["last_topic"] = "shopping"
        elif "明天" in text and "天气" not in text:
            # 单独的"明天"可能是延续上一个话题
            pass
    
    def get_last_topic_context(self) -> dict:
        """获取上一个话题的上下文"""
        return {
            "last_city": self.context["last_city"],
            "last_topic": self.context["last_topic"],
            "last_tool_called": self.context["last_tool_called"]
        }
    
    def get_recent_context(self) -> str:
        """获取最近的上下文摘要"""
        if not self.history:
            return "暂无对话历史"
        
        summary = "【📝 最近对话】\n"
        for i, item in enumerate(self.history[-3:], 1):
            user_short = item['user'][:20] + "..." if len(item['user']) > 20 else item['user']
            summary += f"{i}. 用户: {user_short}\n"
            if item.get('tool'):
                summary += f"   工具: {item['tool']}\n"
        
        if self.context["last_city"]:
            summary += f"📍 上次城市：{self.context['last_city']}\n"
        if self.context["last_weight"]:
            summary += f"⚖️ 上次重量：{self.context['last_weight']}kg\n"
        if self.context["last_distance"]:
            summary += f"📏 上次距离：{self.context['last_distance']}km\n"
        if self.context["last_tool_called"]:
            summary += f"🛠️ 上次工具：{self.context['last_tool_called']}\n"
        
        return summary
    
    def get_messages_for_llm(self):
        """转换为LLM需要的消息格式"""
        messages = []
        for item in self.history[-5:]:
            messages.append({"role": "user", "content": item["user"]})
            messages.append({"role": "assistant", "content": item["assistant"]})
        return messages
    
    def clear(self):
        """清空记忆"""
        self.history = []
        self.context = {
            "last_city": None,
            "last_weight": None,
            "last_distance": None,
            "last_topic": None,
            "last_date_offset": 0,
            "last_tool_called": None
        }
        return "🧹 对话记忆已清空"


# 创建全局记忆实例
memory = ConversationMemory()


# ===================== 任务规划器 =====================
class TaskPlanner:
    """复杂任务规划器 - 将用户需求拆解为工具调用步骤"""
    
    @staticmethod
    def parse_tool_steps(llm_response: str) -> list:
        """解析LLM返回的工具调用步骤"""
        tool_steps = []
        lines = llm_response.strip().split("\n")
        
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or line_clean.startswith("#"):
                continue
            
            # 匹配函数调用格式: get_weather(city="上海")
            func_pattern = re.compile(r'^(\w+)\((.*)\)$')
            func_match = func_pattern.match(line_clean)
            
            if func_match:
                tool_name = func_match.group(1)
                params_str = func_match.group(2)
                
                # 解析参数
                params = {}
                if params_str.strip():
                    try:
                        # 尝试用ast.literal_eval安全解析
                        # 将 "city='上海', offset_days=1" 格式转为字典
                        params_dict = {}
                        # 简单的参数解析
                        param_pairs = re.findall(r'(\w+)\s*=\s*([^,)]+)', params_str)
                        for key, value in param_pairs:
                            value = value.strip().strip('"').strip("'")
                            # 尝试转换为数字
                            try:
                                if '.' in value:
                                    params_dict[key] = float(value)
                                else:
                                    params_dict[key] = int(value)
                            except ValueError:
                                params_dict[key] = value
                        params = params_dict
                    except:
                        params = {}
                
                tool_steps.append({
                    "step": idx + 1,
                    "tool": tool_name,
                    "params": params
                })
        
        return tool_steps
    
    @staticmethod
    def plan(user_input: str, context: dict, history: list) -> list:
        """根据用户输入和上下文生成工具调用计划"""
        
        # 判断是否是延续性问题（明天呢、后天呢）
        is_followup = False
        expected_tool = None
        
        # 检查是否是时间延续性问题
        time_patterns = {
            r"明天.*": 1,
            r"后天.*": 2,
            r"昨天.*": -1
        }
        
        for pattern, offset in time_patterns.items():
            if re.search(pattern, user_input):
                is_followup = True
                # 如果上次调用的是天气工具，这次应该还是天气
                if context.get("last_tool_called") == "get_weather":
                    expected_tool = "get_weather"
                break
        
        # 构建上下文提示
        context_hint = ""
        if context.get("last_city") and is_followup:
            if expected_tool == "get_weather":
                context_hint = f"用户上次查询的城市是【{context['last_city']}】，这次说'{user_input}'应该查询同一城市的天气。"
            else:
                context_hint = f"注意：用户上次查询的是【{context['last_city']}】，可能指同一城市。"
        
        # 如果有明确的预期工具，直接返回
        if expected_tool == "get_weather" and context.get("last_city"):
            print(f"\n📋 【上下文推理】检测到延续性问题，使用上次城市: {context['last_city']}")
            return [{
                "step": 1,
                "tool": "get_weather",
                "params": {"city": context["last_city"]}
            }]
        
        planning_prompt = f"""你是一个智能任务规划专家，需要将用户的生活需求拆解为工具调用步骤。

【可用工具列表】
- get_weather(city="城市名"): 查询城市实时天气
- calculate_express_fee(weight=重量, distance=距离): 计算快递费
- get_date_info(offset_days=偏移天数): 查询日期（0=今天，1=明天，-1=昨天）
- get_travel_preparation(city="城市", weight=重量, distance=距离, travel_date="日期"): 出行建议
- add_shopping_item(item="商品"): 添加购物项
- get_shopping_list(): 查看购物清单
- remove_shopping_item(item="商品"): 移除购物项
- clear_shopping_list(): 清空购物清单

【用户需求】{user_input}

【对话上下文】
{context_hint}
上次话题: {context.get('last_topic', '无')}
上次城市: {context.get('last_city', '无')}

【最近对话历史】
{chr(10).join([f"用户: {h['user']}" for h in history[-2:]]) if history else "无"}

【拆解规则】
1. 如果需求需要多个工具，按逻辑顺序列出，每行一个工具调用
2. 必须使用严格的函数调用格式，例如：get_weather(city="上海")
3. 参数值必须从用户输入中提取，不要编造
4. **特别注意：如果用户说"明天呢"、"后天呢"等延续性问题，应该延续上一个话题**
   - 如果上次是查天气，这次应该用 get_weather(city="上次的城市")
   - 不要错误地调用 get_date_info

请直接输出工具调用步骤，不要添加任何解释："""

        try:
            response = Generation.call(
                model="qwen-turbo",
                messages=[{"role": "user", "content": planning_prompt}],
                result_format="message",
                temperature=0.1,
                max_tokens=500
            )
            
            plan_text = response.output.choices[0].message.content
            print(f"\n📋 【任务规划】\n{plan_text}")
            
            steps = TaskPlanner.parse_tool_steps(plan_text)
            
            # 后处理：检查是否应该用天气而不是日期
            if steps and len(steps) == 1:
                first_step = steps[0]
                # 如果规划结果是日期，但根据上下文应该是天气
                if first_step["tool"] == "get_date_info" and context.get("last_tool_called") == "get_weather":
                    if context.get("last_city"):
                        print(f"⚠️ 检测到规划错误，修正为天气查询: {context['last_city']}")
                        steps[0] = {
                            "step": 1,
                            "tool": "get_weather",
                            "params": {"city": context["last_city"]}
                        }
            
            return steps
            
        except Exception as e:
            print(f"⚠️ 任务规划失败：{e}")
            return []


# ===================== 结果整合器 =====================
class ResultIntegrator:
    """将多个工具结果整合为自然语言"""
    
    @staticmethod
    def integrate(user_input: str, tool_results: list) -> str:
        """整合工具结果"""
        
        # 如果只有一个结果，直接返回
        if len(tool_results) == 1:
            return tool_results[0]
        
        # 多个结果需要整合
        integration_prompt = f"""你是一个友好的生活助手，需要将多个工具的结果整合成一段流畅、自然的回答。

【用户问题】{user_input}

【工具返回结果】
{chr(10).join([f"{i+1}. {res}" for i, res in enumerate(tool_results)])}

【整合要求】
1. 将所有信息整合成一段连贯的话，不要分条列出
2. 语言自然亲切，像朋友聊天一样
3. 如果包含天气、费用、建议等信息，合理安排顺序
4. 不要重复信息，不要添加未提供的内容

请输出整合后的回答："""

        try:
            response = Generation.call(
                model="qwen-turbo",
                messages=[{"role": "user", "content": integration_prompt}],
                result_format="message",
                temperature=0.3,
                max_tokens=800
            )
            return response.output.choices[0].message.content
        except Exception:
            # 降级方案：简单拼接
            return " ".join(tool_results)


# ===================== Agent主函数 =====================
def agent_run(user_input: str) -> str:
    """
    生活助手主函数 - 整合所有功能
    """
    global memory
    
    # 处理特殊指令
    special_commands = {
        "/clear": lambda: memory.clear(),
        "/history": lambda: memory.get_recent_context(),
        "/help": lambda: get_help_text(),
        "/tools": lambda: get_tools_list(),
        "清空记忆": lambda: memory.clear(),
        "查看历史": lambda: memory.get_recent_context(),
        "帮助": lambda: get_help_text()
    }
    
    if user_input in special_commands:
        return special_commands[user_input]()
    
    # 第一步：判断是否为简单指令（直接调用工具）
    if is_simple_query(user_input):
        return handle_simple_query(user_input)
    
    # 第二步：复杂指令 - 任务规划（传入上下文和历史）
    steps = TaskPlanner.plan(user_input, memory.context, memory.history)
    
    if not steps:
        # 规划失败，直接询问LLM
        return handle_direct_llm(user_input)
    
    # 第三步：执行工具调用
    tool_results = []
    tool_names = []
    
    for step in steps:
        tool_name = step["tool"]
        params = step["params"]
        
        # 补充缺失参数（从上下文获取）
        params = enrich_params(tool_name, params, user_input)
        
        print(f"\n🔧 执行步骤{step['step']}: {tool_name}({params})")
        
        if tool_name in TOOL_FUNCTIONS:
            try:
                result = TOOL_FUNCTIONS[tool_name](**params)
                tool_results.append(result)
                tool_names.append(tool_name)
                print(f"✅ 结果: {result[:50]}...")
            except Exception as e:
                error_msg = f"❌ {tool_name} 执行失败: {str(e)[:30]}"
                tool_results.append(error_msg)
        else:
            tool_results.append(f"❌ 未知工具: {tool_name}")
    
    # 第四步：整合结果
    if len(tool_results) == 1:
        final_answer = tool_results[0]
    else:
        final_answer = ResultIntegrator.integrate(user_input, tool_results)
    
    # 第五步：更新记忆（记录实际调用的工具）
    memory.add(user_input, final_answer, tool_names[0] if tool_names else None)
    
    return final_answer


def is_simple_query(user_input: str) -> bool:
    """判断是否为简单查询"""
    simple_patterns = [
        r".*天气.*", r".*快递.*", r".*购物.*", r".*清单.*",
        r".*添加.*", r".*移除.*", r".*清空.*", r".*今天.*",
        r".*明天.*", r".*后天.*", r".*昨天.*"
    ]
    for pattern in simple_patterns:
        if re.search(pattern, user_input):
            return True
    return False


def handle_simple_query(user_input: str) -> str:
    """处理简单查询（使用标准工具调用流程）"""
    
    # 增强系统提示，加入上下文
    context_info = memory.get_last_topic_context()
    
    system_prompt = f"""你是一个生活助手，可以调用工具帮助用户。

【当前上下文】
- 上次话题: {context_info.get('last_topic', '无')}
- 上次城市: {context_info.get('last_city', '无')}
- 上次工具: {context_info.get('last_tool_called', '无')}

【重要规则】
- 如果用户说"明天呢"、"后天呢"等，应该延续上一个话题
- 如果上次是查天气，这次应该继续查同一城市的天气
- 不要混淆天气查询和日期查询

【最近对话】
{memory.get_recent_context()}

根据用户问题，判断是否需要调用工具。如果需要，返回工具调用；否则直接回答。"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        *memory.get_messages_for_llm(),
        {"role": "user", "content": user_input}
    ]
    
    try:
        response = Generation.call(
            model="qwen-max",
            messages=messages,
            tools=TOOLS,
            result_format="message"
        )
        
        if response.status_code != 200:
            return f"❌ 服务异常: {response.message}"
        
        assistant_msg = response.output.choices[0].message
        messages.append(assistant_msg)
        
        # 检查是否需要调用工具
        if "tool_calls" in assistant_msg and assistant_msg["tool_calls"]:
            tool_call = assistant_msg["tool_calls"][0]
            tool_name = tool_call["function"]["name"]
            
            try:
                tool_args = json.loads(tool_call["function"]["arguments"])
            except:
                tool_args = {}
            
            # 后处理：如果是延续性问题，修正参数
            if "明天" in user_input and tool_name == "get_date_info":
                # 检查是否应该用天气
                if context_info.get("last_tool_called") == "get_weather" and context_info.get("last_city"):
                    tool_name = "get_weather"
                    tool_args = {"city": context_info["last_city"]}
                    print(f"🔄 修正：将日期查询改为天气查询，城市: {context_info['last_city']}")
            
            if tool_name in TOOL_FUNCTIONS:
                tool_result = TOOL_FUNCTIONS[tool_name](**tool_args)
                
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "name": tool_name
                })
                
                final_response = Generation.call(
                    model="qwen-max",
                    messages=messages
                )
                
                if final_response.status_code == 200:
                    answer = final_response.output.choices[0].message.content
                else:
                    answer = tool_result
                
                memory.add(user_input, answer, tool_name)
                return answer
            else:
                return f"❌ 未知工具: {tool_name}"
        else:
            # 直接回答
            answer = assistant_msg.get("content", "好的")
            memory.add(user_input, answer, None)
            return answer
            
    except Exception as e:
        return f"😓 处理出错: {str(e)[:30]}"


def handle_direct_llm(user_input: str) -> str:
    """直接调用LLM回答"""
    try:
        response = Generation.call(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": "你是一个友好的生活助手。"},
                *memory.get_messages_for_llm(),
                {"role": "user", "content": user_input}
            ]
        )
        answer = response.output.choices[0].message.content
        memory.add(user_input, answer, None)
        return answer
    except Exception as e:
        return f"😓 服务繁忙: {str(e)[:20]}"


def enrich_params(tool_name: str, params: dict, user_input: str) -> dict:
    """补充缺失的参数（从上下文获取）"""
    enriched = params.copy()
    
    if tool_name == "get_weather":
        if "city" not in enriched or not enriched["city"]:
            # 检查是否是延续性问题
            if memory.context["last_city"]:
                # 如果是时间词，很可能延续上次城市
                if any(word in user_input for word in ["明天", "后天", "今天", "昨天"]):
                    enriched["city"] = memory.context["last_city"]
                    print(f"🔄 从上下文补充城市: {enriched['city']}")
    
    elif tool_name == "calculate_express_fee":
        if "weight" not in enriched and memory.context["last_weight"]:
            enriched["weight"] = memory.context["last_weight"]
        if "distance" not in enriched and memory.context["last_distance"]:
            enriched["distance"] = memory.context["last_distance"]
    
    elif tool_name == "get_date_info":
        if "offset_days" not in enriched:
            if "明天" in user_input:
                enriched["offset_days"] = 1
            elif "后天" in user_input:
                enriched["offset_days"] = 2
            elif "昨天" in user_input:
                enriched["offset_days"] = -1
            else:
                enriched["offset_days"] = 0
    
    return enriched


def get_help_text() -> str:
    """获取帮助信息"""
    return """🤖 生活助手使用指南

【基础功能】
🌤️ 天气查询：上海天气、北京明天天气、济南今天天气
📦 快递费计算：计算快递费 2kg 300km、2公斤行李300公里运费
🛒 购物清单：添加苹果、查看清单、移除牛奶、清空清单
📅 日期查询：今天星期几、明天日期、后天
✈️ 出行建议：去上海带2kg行李300km需要准备什么

【高级功能】
🔍 多任务：帮我规划去上海的行程，带2kg行李，路程300km，明天出发
🔍 上下文记忆：查北京天气 → 明天呢 → 后天呢
🔍 模糊指令：算一下费用 → 自动追问

【记忆管理】
/history - 查看对话历史
/clear - 清空记忆
/tools - 查看可用工具
/help - 显示本帮助

输入 'exit' 或 '退出' 结束对话"""


def get_tools_list() -> str:
    """获取工具列表"""
    return f"""🛠️ 可用工具列表（{len(TOOL_FUNCTIONS)}个）：
{chr(10).join([f"  • {name}" for name in TOOL_FUNCTIONS.keys()])}

支持的城市：{', '.join(SUPPORTED_CITIES)}"""


# ===================== 主程序入口 =====================
def main():
    """交互主循环"""
    print("=" * 80)
    print("🤖 生活助手 AI Agent - 完整版（修复上下文记忆）")
    print("=" * 80)
    print(get_help_text())
    print("=" * 80)
    
    while True:
        try:
            user_input = input("\n👤 你: ").strip()
            
            if user_input.lower() in ["exit", "退出", "quit"]:
                print("👋 感谢使用，再见！")
                break
            
            if not user_input:
                continue
            
            response = agent_run(user_input)
            print(f"🤖 助手: {response}")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"😓 系统错误: {e}")


if __name__ == "__main__":
    main()