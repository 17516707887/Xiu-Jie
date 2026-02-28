import dashscope
from dashscope import Generation
import json
from m_tools import TOOLS, TOOL_FUNCTIONS
from dotenv import load_dotenv
import os
import re
from datetime import datetime

load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# -------------------------- 增强版记忆管理类 --------------------------
class ConversationMemory:
    """对话记忆管理类 - 存储历史并提取关键信息"""
    
    def __init__(self, max_rounds: int = 10):
        self.history = []  # 对话历史
        self.max_rounds = max_rounds
        self.context = {  # 上下文信息
            "last_city": None,
            "last_weight": None,
            "last_distance": None,
            "last_topic": None
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
        
        # 提取上下文信息
        self._extract_context(user_input)
        
        # 限制历史长度
        if len(self.history) > self.max_rounds:
            self.history.pop(0)
    
    def _extract_context(self, text: str):
        """从用户输入提取关键信息"""
        # 提取城市
        cities = re.findall(r'[北京上海广州深圳杭州南京成都武汉]', text)
        if cities:
            self.context["last_city"] = cities[-1]
        
        # 提取数字
        numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
        if numbers:
            if "kg" in text or "公斤" in text or "重量" in text:
                self.context["last_weight"] = float(numbers[-1])
            if "km" in text or "公里" in text or "距离" in text:
                self.context["last_distance"] = float(numbers[-1])
        
        # 提取话题
        if "天气" in text:
            self.context["last_topic"] = "weather"
        elif "快递" in text or "运费" in text:
            self.context["last_topic"] = "express"
        elif "购物" in text or "清单" in text:
            self.context["last_topic"] = "shopping"
    
    def get_recent_context(self) -> str:
        """获取最近的上下文摘要"""
        if not self.history:
            return "暂无对话历史"
        
        summary = "【最近对话】\n"
        for i, item in enumerate(self.history[-3:], 1):
            summary += f"{i}. 用户: {item['user'][:20]}...\n"
        
        if self.context["last_city"]:
            summary += f"📍 上次城市：{self.context['last_city']}\n"
        
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
            "last_topic": None
        }
        return "🧹 对话记忆已清空"

# 创建全局记忆实例 - 这里修正了类名
memory = ConversationMemory()  # 原来是 ConversationHistory，现在改成 ConversationMemory

def clear_history():
    """清空对话历史"""
    return memory.clear()

def agent_run(user_input: str) -> str:
    """
    Agent 主逻辑：LLM 解析意图 -> 选择工具 -> 执行工具 -> 返回结果
    集成：上下文记忆、错误处理、Prompt 优化
    """
    global memory
    
    # 特殊指令处理
    if user_input.lower() in ["清空历史", "清空记忆", "clear"]:
        return memory.clear()
    
    if user_input.lower() in ["查看历史", "历史", "history"]:
        return memory.get_recent_context()
    
    # 1. 构建含上下文的消息体
    system_prompt = f"""
    你是一个具备会话记忆的智能生活助手AI Agent，严格遵守以下规则：
    
    【上下文信息】
    {memory.get_recent_context()}
    
    【核心规则】
    1. 上下文记忆：必须结合历史对话内容理解当前问题，用户未明确参数时优先从历史中提取。
    2. 主动追问：若用户指令缺失工具必需参数，或指令模糊（如“算快递费”“查天气”），必须主动追问缺失的关键信息。
    3. 错误反馈：工具执行返回错误时，需将错误信息清晰告知用户，并引导修正输入。
    4. 工具调用：仅在参数完整时调用工具，无需调用工具时直接自然语言回答。
    5. 多轮交互：用户提出关联问题（如先问“北京天气”，再问“明天呢”）时，需结合历史补全参数。
    
    【模糊指令示例】
    - 用户说“明天呢” → 结合历史，如果是查天气就继续查同一城市明天天气
    - 用户说“算一下快递费” → 追问具体重量和距离
    - 用户说“添加购物清单” → 追问具体商品名称
    """
    
    # 初始化消息
    messages = [{"role": "system", "content": system_prompt.strip()}]
    
    # 添加历史记忆
    history_messages = memory.get_messages_for_llm()
    messages.extend(history_messages)
    
    # 添加当前用户输入
    messages.append({"role": "user", "content": user_input})
    
    try:
        # 2. 第一次调用LLM：意图解析与工具选择
        response = Generation.call(
            model="qwen-max",
            messages=messages,
            tools=TOOLS,
            result_format="message",
            timeout=30
        )
        
        # 错误处理1：LLM调用失败
        if response.status_code != 200:
            error_msg = f"❌ 服务暂时不可用：{response.message}"
            memory.add(user_input, error_msg, None)
            return error_msg
        
        # 错误处理2：返回格式异常
        if not hasattr(response, "output") or not response.output.choices:
            error_msg = "❌ LLM返回格式异常"
            memory.add(user_input, error_msg, None)
            return error_msg
        
        assistant_message = response.output.choices[0].message
        messages.append(assistant_message)
        
        # 3. 工具调用逻辑
        final_answer = ""
        tool_used = None
        
        if "tool_calls" in assistant_message and assistant_message["tool_calls"]:
            try:
                tool_call = assistant_message["tool_calls"][0]
                tool_name = tool_call["function"]["name"]
                tool_used = tool_name
                
                # 错误处理3：参数解析失败
                try:
                    tool_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    return "❌ 参数解析失败，请重新描述您的问题"
                
                # 工具存在性校验
                if tool_name not in TOOL_FUNCTIONS:
                    final_answer = f"❌ 未知工具：{tool_name}"
                else:
                    # 执行工具
                    print(f"[调试] 调用工具: {tool_name}, 参数: {tool_args}")
                    tool_result = TOOL_FUNCTIONS[tool_name](**tool_args)
                    
                    # 添加工具结果
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "name": tool_name
                    })
                    
                    # 第二次调用LLM：整理结果
                    final_response = Generation.call(
                        model="qwen-max",
                        messages=messages,
                        timeout=20
                    )
                    
                    if final_response.status_code == 200 and final_response.output.choices:
                        final_answer = final_response.output.choices[0].message.content
                    else:
                        final_answer = f"工具执行结果：{tool_result}"
                        
            except Exception as e:
                final_answer = f"❌ 工具执行出错：{str(e)}"
        else:
            # 直接回答
            final_answer = assistant_message.get("content", "好的，已收到")
        
        # 4. 更新记忆
        memory.add(user_input, final_answer, tool_used)
        
        return final_answer
        
    except Exception as e:
        # 全局异常处理
        error_msg = f"😓 系统繁忙：{str(e)[:50]}"
        memory.add(user_input, error_msg, None)
        return error_msg

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI Agent 第二阶段 - 智能生活助手")
    print("=" * 60)
    print("支持功能：")
    print("1. 天气查询：北京天气、明天呢、上海后天天气")
    print("2. 快递费计算：计算快递费 2kg 300km")
    print("3. 购物清单：添加苹果、查看清单")
    print("4. 记忆管理：/history 查看历史，/clear 清空记忆，/exit 退出")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n👤 用户: ").strip()
            
            if user_input.lower() in ["/exit", "exit", "退出"]:
                print("👋 再见！")
                break
            elif not user_input:
                continue
            
            response = agent_run(user_input)
            print(f"🤖 Agent: {response}")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"😓 错误: {e}")