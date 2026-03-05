"""
生活助手AI Agent - Flask后端API
提供RESTful接口供前端调用
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入你的Agent核心代码
from agent import agent_run, memory, get_help_text, get_tools_list

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求，方便前端调试

# 加载环境变量
load_dotenv()

# ===================== API路由 =====================

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    聊天接口
    请求体: {"message": "用户输入"}
    返回: {"response": "助手回复", "history": [...]}
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            }), 400
        
        # 调用你的Agent核心函数
        response = agent_run(user_message)
        
        # 获取最近的对话历史（用于前端显示）
        recent_history = []
        for item in memory.history[-10:]:  # 最近10条
            recent_history.append({
                'user': item['user'],
                'assistant': item['assistant'],
                'tool': item.get('tool'),
                'timestamp': item.get('timestamp')
            })
        
        return jsonify({
            'success': True,
            'response': response,
            'history': recent_history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """获取对话历史"""
    try:
        history = []
        for item in memory.history:
            history.append({
                'user': item['user'],
                'assistant': item['assistant'],
                'tool': item.get('tool'),
                'timestamp': item.get('timestamp')
            })
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_memory():
    """清空记忆"""
    try:
        result = memory.clear()
        return jsonify({
            'success': True,
            'message': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tools', methods=['GET'])
def get_tools():
    """获取工具列表"""
    try:
        tools_info = get_tools_list()
        # 从m_tools导入工具列表
        from m_tools import TOOL_FUNCTIONS, SUPPORTED_CITIES
        tools = {
            'list': list(TOOL_FUNCTIONS.keys()),
            'count': len(TOOL_FUNCTIONS),
            'cities': SUPPORTED_CITIES,
            'description': tools_info
        }
        return jsonify({
            'success': True,
            'tools': tools
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/help', methods=['GET'])
def get_help():
    """获取帮助信息"""
    try:
        help_text = get_help_text()
        return jsonify({
            'success': True,
            'help': help_text
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'status': 'running',
        'version': '1.0.0'
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 生活助手AI Agent - 后端服务")
    print("=" * 60)
    print("启动服务器...")
    print("访问地址: http://localhost:5000")
    print("API文档: http://localhost:5000/api/health")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)