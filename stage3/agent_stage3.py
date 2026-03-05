"""
AI Agent 阶段3：任务规划与多工具协作
文件名：agent_stage3.py
"""
import dashscope
from dashscope import Generation
import re
import os
from dotenv import load_dotenv
# 改为导入整个m_tools模块，而非单独变量（核心修复）
import m_tools

# ===================== 初始化配置 =====================
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope.api_key:
    raise ValueError("❌ 请在.env文件中配置DASHSCOPE_API_KEY（阿里云千问大模型API密钥）")

# ===================== 核心函数1：解析LLM返回的工具调用步骤（完全保留） =====================
def parse_tool_steps(llm_response: str) -> list:
    """
    解析千问返回的工具调用步骤，提取工具名称和参数
    返回格式：[{"step": 1, "tool": "get_weather", "params": {"city": "上海"}}, ...]
    """
    tool_steps = []
    lines = llm_response.strip().split("\n")
    
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        
        # 匹配格式1：函数调用式（如 get_weather(city="上海")）
        func_pattern = re.compile(r'^(\w+)\((.*)\)$')
        func_match = func_pattern.match(line_clean)
        if func_match:
            tool_name = func_match.group(1)
            params_str = func_match.group(2)
            
            # 解析参数（如 city="上海", weight=2.0）
            params = {}
            param_pattern = re.compile(r'(\w+)\s*=\s*([^,]+)')
            param_matches = param_pattern.findall(params_str)
            for key, value in param_matches:
                val_clean = value.strip().strip('"').strip("'")
                # 尝试转换为数字类型
                try:
                    if "." in val_clean:
                        params[key] = float(val_clean)
                    else:
                        params[key] = int(val_clean)
                except ValueError:
                    params[key] = val_clean
            
            tool_steps.append({
                "step": idx + 1,
                "tool": tool_name,
                "params": params
            })
            continue
        
        # 匹配格式2：自然语言步骤式（如 1. 调用get_weather，参数：city=上海）
        step_pattern = re.compile(r'(\d+)\. 调用(\w+)[，,].*参数：(.*)')
        step_match = step_pattern.match(line_clean)
        if step_match:
            step_num = int(step_match.group(1))
            tool_name = step_match.group(2)
            params_str = step_match.group(3)
            
            # 解析参数
            params = {}
            param_pattern = re.compile(r'(\w+)=([^，,]+)')
            param_matches = param_pattern.findall(params_str)
            for key, value in param_matches:
                val_clean = value.strip().strip('"').strip("'")
                if key in ["weight", "distance", "offset_days"]:
                    try:
                        params[key] = float(val_clean) if "." in val_clean else int(val_clean)
                    except ValueError:
                        params[key] = val_clean
                else:
                    params[key] = val_clean
            
            tool_steps.append({
                "step": step_num,
                "tool": tool_name,
                "params": params
            })
    
    return tool_steps

# ===================== 核心函数2：调用指定工具（改为访问m_tools.TOOL_FUNCTIONS） =====================
def call_tool(tool_name: str, params: dict) -> str:
    """调用指定的工具函数，返回执行结果"""
    if tool_name not in m_tools.TOOL_FUNCTIONS:
        return f"❌ 工具【{tool_name}】不存在，支持的工具：{list(m_tools.TOOL_FUNCTIONS.keys())}"
    
    try:
        tool_func = m_tools.TOOL_FUNCTIONS[tool_name]
        result = tool_func(** params)
        return result
    except Exception as e:
        return f"⚠️ 工具【{tool_name}】调用失败：{str(e)[:30]}"

# ===================== 核心函数3：整合工具结果为自然语言（完全保留） =====================
def integrate_results(user_input: str, tool_results: list) -> str:
    """将多个工具的执行结果整合为流畅的自然语言回答"""
    # 系统提示：定义整合规则
    system_prompt = """你是一个专业的行程规划助手，需要将工具调用结果整合为自然、流畅的回答：
    1. 覆盖所有工具的核心结果，不遗漏关键信息（天气、快递费、日期、出行建议、购物清单）；
    2. 语言通俗易懂，符合日常交流习惯，避免技术术语；
    3. 结构清晰，可分点说明，但不要使用工具调用的原始格式；
    4. 如果有错误信息，委婉提示，优先展示可用结果。"""
    
    # 用户提示：传入需求和工具结果
    user_prompt = f"""用户需求：{user_input}
工具调用结果列表：
{chr(10).join([f"{i+1}. {res}" for i, res in enumerate(tool_results)])}

请根据以上信息，生成一份清晰、自然的行程规划回答："""
    
    # 调用千问模型整合结果
    try:
        response = Generation.call(
            model="qwen-turbo",  # 千问轻量版，响应快且稳定
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            result_format="message",
            temperature=0.3,  # 低随机性，保证回答稳定
            max_tokens=1000
        )
        return response.output.choices[0].message.content
    except Exception as e:
        # 降级方案：直接拼接结果
        fallback_answer = "✅ 你的行程规划信息如下：\n"
        for idx, res in enumerate(tool_results):
            if not res.startswith("❌"):
                fallback_answer += f"{idx+1}. {res}\n"
        return fallback_answer

# ===================== 核心函数4：Agent主流程（修复last_city访问方式） =====================
def agent_run(user_input: str) -> str:
    """Agent主运行流程：拆解需求→解析步骤→调用工具→整合结果"""
    # ===================== 多轮天气指令识别（核心修复：访问m_tools.last_city） =====================
    input_clean = user_input.strip().lower()
    if input_clean in ["明天", "明天呢", "后天", "后天呢", "昨天", "昨天呢"]:
        # 访问m_tools模块中的last_city，获取最新值
        if not m_tools.last_city:
            return "⚠️ 请先查询一个城市的天气（如：上海天气），再问明天/后天哦～"
        offset_map = {
            "明天": 1, "明天呢": 1,
            "后天": 2, "后天呢": 2,
            "昨天": -1, "昨天呢": -1
        }
        offset_days = offset_map[input_clean]
        # 复用m_tools.last_city查询预报
        return call_tool("get_weather", {"city": m_tools.last_city, "offset_days": offset_days})
    
    # ===================== 原有逻辑：强制分步拆解（完全保留） =====================
    step_prompt = """你是专业的行程规划拆解专家，必须严格按照以下规则拆解用户需求：
1. 核心规则：只要需求包含行程规划（城市+行李+路程+日期），必须分步调用以下4个工具，缺一不可：
   - get_weather：查询目的地实时天气（必填参数：city）
   - calculate_express_fee：计算快递费（必填参数：weight、distance）
   - get_date_info：查询出行日期（必填参数：offset_days，0=今天，1=明天，-1=昨天）
   - get_travel_preparation：生成出行建议（必填参数：city、weight、distance；可选：travel_date）
2. 格式要求：每行只写一个工具调用，严格使用函数格式，无额外说明，示例：
get_weather(city="上海")
calculate_express_fee(weight=2.0, distance=300.0)
get_date_info(offset_days=1)
get_travel_preparation(city="上海", weight=2.0, distance=300.0, travel_date="2026年03月04日")
3. 补充规则：
   - 若需求包含购物清单（添加/查看/移除/清空），额外添加对应工具调用（add_shopping_item/get_shopping_list等）
   - 参数值必须和用户需求完全匹配（如用户说2kg行李，weight=2.0；300km路程，distance=300.0）

用户需求：{user_input}
请严格按照示例格式生成工具调用步骤，仅返回步骤，不要添加任何额外文字：""".format(user_input=user_input)
    
    try:
        # 调用千问生成步骤
        step_response = Generation.call(
            model="qwen-turbo",
            messages=[{"role": "user", "content": step_prompt}],
            result_format="message",
            temperature=0.1,  # 极低随机性，保证格式正确
            max_tokens=500
        )
        step_text = step_response.output.choices[0].message.content
        print(f"\n📝 【任务拆解步骤】\n{step_text}")
    except Exception as e:
        return f"❌ 需求拆解失败：{str(e)[:40]}"
    
    # 步骤2：解析工具调用步骤
    tool_steps = parse_tool_steps(step_text)
    if not tool_steps:
        return "❌ 未解析到有效的工具调用步骤，请重新输入需求（如：帮我规划去上海的行程，带2kg行李，路程300km）"
    
    # 步骤3：执行工具调用
    tool_results = []
    for step in tool_steps:
        print(f"\n🔧 【执行步骤{step['step']}】调用工具：{step['tool']}，参数：{step['params']}")
        result = call_tool(step["tool"], step["params"])
        tool_results.append(result)
        print(f"✅ 【步骤{step['step']}结果】{result}")
    
    # 步骤4：整合结果并返回
    final_answer = integrate_results(user_input, tool_results)
    return final_answer

# ===================== 交互主函数（完全保留） =====================
def main():
    """用户交互入口，支持持续对话"""
    print("=" * 80)
    print("🤖 AI 行程规划助手")
    print("=" * 80)
    print("📌 支持的功能：")
    print("  1. 查询城市实时天气/预报（上海、北京、济南等）")
    print("  2. 计算行李快递费（重量+距离）")
    print("  3. 查询日期/星期（今天/明天/昨天）")
    print("  4. 生成出行建议（结合天气/行李/路程）")
    print("  5. 管理购物清单（添加/查看/移除/清空）")
    print("📌 示例指令：")
    print("  - 帮我规划去上海的行程，带2kg行李，路程300km，明天出发")
    print("  - 上海天气 → 明天呢（多轮查询）")
    print("  - 添加雨伞到购物清单，查看当前清单")
    print("📌 退出指令：exit / 退出 / q / quit")
    print("=" * 80)
    
    # 持续对话循环
    while True:
        user_input = input("\n👤 你：").strip()
        
        # 退出逻辑
        if user_input.lower() in ["exit", "退出", "q", "quit"]:
            print("👋 感谢使用，再见！")
            break
        
        # 空输入处理
        if not user_input:
            print("❌ 请输入有效的行程规划需求（如：帮我规划去上海的行程）")
            continue
        
        # 运行Agent并返回结果
        try:
            answer = agent_run(user_input)
            print(f"\n🤖 助手：{answer}")
        except Exception as e:
            print(f"\n❌ 运行异常：{str(e)[:50]}")

# ===================== 程序入口 =====================
if __name__ == "__main__":
    main()
