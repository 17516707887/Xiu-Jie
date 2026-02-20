import dashscope
from dashscope import Generation
import json
from m_tools import TOOLS, TOOL_FUNCTIONS
from dotenv import load_dotenv
import os

load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")  # 或直接赋值千问API Key

def agent_run(user_input: str) -> str:
    """
    Agent 主逻辑：LLM 解析意图 -> 选择工具 -> 执行工具 -> 返回结果
    """
    messages = [
        {"role": "system", "content": "你是一个生活助手AI Agent，可以调用工具来帮助用户。你需要根据用户的问题，判断是否需要调用工具。如果需要，就按照工具的格式要求生成调用参数；如果不需要，就直接回答用户。"},
        {"role": "user", "content": user_input}
    ]

    # 第一次调用 LLM，判断是否需要调用工具
    response = Generation.call(
        model="qwen-max",
        messages=messages,
        tools=TOOLS,
        result_format="message"
    )

    if response.status_code == 200:
        assistant_message = response.output.choices[0].message
        messages.append(assistant_message)

        # 如果 LLM 决定调用工具
        if "tool_calls" in assistant_message:
            tool_call = assistant_message["tool_calls"][0]
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])

            # 执行工具
            if tool_name in TOOL_FUNCTIONS:
                tool_result = TOOL_FUNCTIONS[tool_name](**tool_args)
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "name": tool_name
                })

                # 第二次调用 LLM，将工具结果整理成自然语言回答
                final_response = Generation.call(
                    model="qwen-max",
                    messages=messages
                )
                if final_response.status_code == 200:
                    return final_response.output.choices[0].message.content
                else:
                    return f"LLM 调用失败：{final_response.message}"
            else:
                return f"未知工具：{tool_name}"
        else:
            # 不需要调用工具，直接返回 LLM 回答
            return assistant_message["content"]
    else:
        return f"LLM 调用失败：{response.message}"

if __name__ == "__main__":
    print("生活助手 AI Agent 已启动，输入 'exit' 退出。")
    while True:
        user_input = input("你：")
        if user_input.lower() == "exit":
            print("再见！")
            break
        result = agent_run(user_input)
        print(f"AI：{result}")