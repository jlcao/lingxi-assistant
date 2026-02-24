import logging
from flask import Flask, request, jsonify, render_template_string
from lingxi.core.session import SessionManager
from lingxi.utils.config import get_config
from lingxi.utils.logging import setup_logging

logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 全局会话管理器
session_manager = None

# 初始化函数
def init_app(config=None):
    """初始化Flask应用
    
    Args:
        config: 系统配置
    """
    global session_manager
    
    # 加载配置
    if not config:
        config = get_config()
    
    # 设置日志
    setup_logging(config)
    
    # 创建会话管理器
    session_manager = SessionManager(config)
    
    # 配置Flask
    app.config['SECRET_KEY'] = 'lingxi-secret-key'
    app.config['DEBUG'] = config.get('web', {}).get('debug', False)
    
    logger.info("初始化Web服务器")
    logger.info(f"Web服务器配置: host={config.get('web', {}).get('host')}, port={config.get('web', {}).get('port')}")

# 主页路由
@app.route('/')
def index():
    """主页"""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>灵犀智能任务处理系统</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: white;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                margin-top: 50px;
                border-radius: 8px;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .chat-box {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                height: 400px;
                overflow-y: scroll;
                margin-bottom: 20px;
                background-color: #f9f9f9;
            }
            .message {
                margin-bottom: 10px;
                padding: 10px;
                border-radius: 4px;
            }
            .user-message {
                background-color: #e3f2fd;
                text-align: right;
                margin-left: 20%;
            }
            .assistant-message {
                background-color: #f1f1f1;
                text-align: left;
                margin-right: 20%;
            }
            .input-area {
                display: flex;
            }
            input[type="text"] {
                flex: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px 0 0 4px;
                font-size: 16px;
            }
            button {
                padding: 10px 20px;
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 0 4px 4px 0;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #1976d2;
            }
            .footer {
                text-align: center;
                margin-top: 20px;
                color: #666;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>灵犀智能任务处理系统</h1>
            <div class="chat-box" id="chatBox">
                <div class="message assistant-message">
                    你好！我是灵犀智能助手，很高兴为你服务。
                </div>
            </div>
            <div class="input-area">
                <input type="text" id="userInput" placeholder="请输入你的问题..." autocomplete="off">
                <button onclick="sendMessage()">发送</button>
            </div>
            <div class="footer">
                灵犀智能任务处理系统 v0.1.0
            </div>
        </div>
        <script>
            function sendMessage() {
                const userInput = document.getElementById('userInput');
                const message = userInput.value.trim();
                
                if (message) {
                    // 添加用户消息
                    addMessage('user', message);
                    userInput.value = '';
                    
                    // 发送消息到服务器
                    fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ message: message })
                    })
                    .then(response => response.json())
                    .then(data => {
                        // 添加助手消息
                        addMessage('assistant', data.response);
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        addMessage('assistant', '抱歉，处理请求时出错了。');
                    });
                }
            }
            
            function addMessage(role, content) {
                const chatBox = document.getElementById('chatBox');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}-message`;
                messageDiv.textContent = content;
                chatBox.appendChild(messageDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            
            // 支持回车键发送
            document.getElementById('userInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    ''')

# API路由
@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天API"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not message:
            return jsonify({'error': '缺少消息内容'}), 400
        
        # 处理消息
        response = session_manager.process_input(message, session_id)
        
        return jsonify({'response': response, 'session_id': session_id})
        
    except Exception as e:
        logger.error(f"API错误: {e}")
        return jsonify({'error': str(e)}), 500

# 健康检查路由
@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify({'status': 'healthy', 'service': 'lingxi-web'})

# 启动函数
def run_server(config=None):
    """启动Web服务器
    
    Args:
        config: 系统配置
    """
    if not config:
        config = get_config()
    
    # 初始化应用
    init_app(config)
    
    # 获取Web配置
    web_config = config.get('web', {})
    host = web_config.get('host', 'localhost')
    port = web_config.get('port', 5000)
    debug = web_config.get('debug', False)
    
    logger.info(f"启动Web服务器: http://{host}:{port}")
    
    # 启动服务器
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    # 直接运行Web服务器
    run_server()