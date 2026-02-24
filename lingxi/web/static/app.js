let ws = null;
let isConnected = false;
let streamMode = false;
let currentSessionId = 'session_' + Date.now().toString(36);
let sessions = [];

function connect() {
    const wsUrl = 'ws://localhost:5000/ws';
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        isConnected = true;
        updateStatus(true);
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleMessage(message);
    };

    ws.onclose = () => {
        isConnected = false;
        updateStatus(false);
    };

    ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
    };
}

function updateStatus(connected) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');

    if (connected) {
        dot.className = 'status-dot connected';
        text.textContent = '已连接';
    } else {
        dot.className = 'status-dot disconnected';
        text.textContent = '未连接';
    }
}

function handleMessage(message) {
    switch (message.type) {
        case 'welcome':
            if (message.data && message.data.session_id) {
                currentSessionId = message.data.session_id;
            }
            break;
        case 'chat':
            hideWelcome();
            addAssistantMessage(message.data.content);
            break;
        case 'stream_start':
            hideWelcome();
            startStreaming();
            break;
        case 'stream_chunk':
            appendStreamContent(message.content);
            break;
        case 'stream_end':
            finishStreaming();
            loadSessionList();
            break;
        case 'command':
            hideWelcome();
            handleCommandResponse(message);
            break;
        case 'success':
            if (typeof message.data === 'string') {
                addSystemMessage(message.data);
            } else {
                addSystemMessage('操作成功');
            }
            break;
        case 'error':
            addSystemMessage('错误: ' + message.error);
            break;
        default:
            console.log('未知消息类型:', message.type);
    }
}

function handleCommandResponse(message) {
    const result = message.data.result;
    let content = '';

    if (typeof result === 'string') {
        content = result;
    } else if (Array.isArray(result)) {
        content = result.map(item => '- ' + (item.name || item)).join('\n');
    } else if (typeof result === 'object') {
        content = JSON.stringify(result, null, 2);
    }

    addAssistantMessage(content);
}

function hideWelcome() {
    const welcome = document.getElementById('welcomeScreen');
    if (welcome) {
        welcome.classList.add('hidden');
    }
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message) return;

    if (!isConnected) {
        addSystemMessage('请先连接服务器');
        return;
    }

    hideWelcome();
    addUserMessage(message);
    input.value = '';
    input.style.height = 'auto';

    const messageType = streamMode ? 'stream_chat' : 'chat';
    const request = {
        type: messageType,
        content: message,
        session_id: currentSessionId
    };

    ws.send(JSON.stringify(request));
}

function executeCommand(command) {
    if (!isConnected) {
        addSystemMessage('请先连接服务器');
        return;
    }

    const request = {
        type: 'command',
        command: command,
        args: {},
        session_id: currentSessionId
    };

    ws.send(JSON.stringify(request));
}

async function loadSessionList() {
    try {
        const response = await fetch('/api/sessions');
        const result = await response.json();

        if (result.success) {
            sessions = result.sessions;
            renderSessionList();
        } else {
            console.error('加载会话列表失败:', result);
        }
    } catch (error) {
        console.error('加载会话列表失败:', error);
    }
}

function renderSessionList() {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;

    historyList.innerHTML = '';

    if (!sessions || sessions.length === 0) {
        historyList.innerHTML = '<div style="padding: 12px; color: var(--text-muted); font-size: 13px; text-align: center;">暂无历史对话</div>';
        return;
    }

    sessions.forEach(session => {
        const isActive = session.session_id === currentSessionId;
        const title = session.first_message || session.session_id;
        const preview = session.first_message ? `${session.message_count} 条消息` : '新对话';
        const icon = getSessionIcon(title);

        const itemDiv = document.createElement('div');
        itemDiv.className = `history-item ${isActive ? 'active' : ''}`;
        itemDiv.dataset.sessionId = session.session_id;
        
        const button = document.createElement('button');
        button.className = 'history-menu-btn';
        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="1"></circle>
                <circle cx="12" cy="5" r="1"></circle>
                <circle cx="12" cy="19" r="1"></circle>
            </svg>
        `;
        button.onclick = (e) => toggleMenu(e, session.session_id, title.substring(0, 20));
        
        const iconDiv = document.createElement('div');
        iconDiv.className = 'history-icon';
        iconDiv.textContent = icon;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'history-content';
        contentDiv.innerHTML = `
            <div class="history-title">${escapeHtml(title.substring(0, 30))}${title.length > 30 ? '...' : ''}</div>
            <div class="history-preview">${preview}</div>
        `;
        
        itemDiv.appendChild(iconDiv);
        itemDiv.appendChild(contentDiv);
        itemDiv.appendChild(button);
        
        itemDiv.onclick = (e) => {
            if (!e.target.closest('.history-menu-btn')) {
                switchSession(session.session_id);
            }
        };
        historyList.appendChild(itemDiv);
    });
}

function getSessionIcon(title) {
    const icons = ['💬', '📝', '💡', '🔍', '📊', '🛠️', '📚', '🎯'];
    const hash = title.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    return icons[hash % icons.length];
}

async function switchSession(sessionId) {
    if (!isConnected) return;

    currentSessionId = sessionId;

    const request = {
        type: 'session',
        action: 'switch',
        new_session_id: sessionId,
        session_id: sessionId
    };
    ws.send(JSON.stringify(request));

    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.sessionId === sessionId) {
            item.classList.add('active');
        }
    });

    await loadSessionHistory(sessionId);
}

async function loadSessionHistory(sessionId) {
    try {
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">加载历史消息中...</div>';

        const response = await fetch(`/api/sessions/${sessionId}/history`);
        const result = await response.json();

        messagesDiv.innerHTML = '';
        
        if (result.history && result.history.length > 0) {
            hideWelcome();
            result.history.forEach(msg => {
                const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);
                if (msg.role === 'user') {
                    addUserMessage(content);
                } else if (msg.role === 'assistant') {
                    addAssistantMessage(content);
                }
            });
        } else {
            showWelcome();
        }
    } catch (error) {
        console.error('加载会话历史失败:', error);
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = '';
        showWelcome();
        addSystemMessage('加载历史消息失败: ' + error.message);
    }
}

function showWelcome() {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = `
        <div class="welcome-screen" id="welcomeScreen">
            <div class="welcome-icon">🤖</div>
            <h2 class="welcome-title">你好，我是灵犀助手</h2>
            <p class="welcome-subtitle">我可以帮你回答问题、写作、编程等，有什么我可以帮助你的吗？</p>
            <div class="quick-actions">
                <button class="quick-action-btn" onclick="quickAction('帮我写一封邮件')">
                    <div class="title">📧 写邮件</div>
                    <div class="desc">帮我起草一封专业邮件</div>
                </button>
                <button class="quick-action-btn" onclick="quickAction('解释一段代码')">
                    <div class="title">💻 代码解释</div>
                    <div class="desc">帮我理解复杂的代码逻辑</div>
                </button>
                <button class="quick-action-btn" onclick="quickAction('帮我写一篇文章')">
                    <div class="title">📝 写文章</div>
                    <div class="desc">帮我撰写各类文章内容</div>
                </button>
                <button class="quick-action-btn" onclick="quickAction('翻译成英文')">
                    <div class="title">🌐 翻译</div>
                    <div class="desc">中英文互译及其他语言</div>
                </button>
            </div>
        </div>
    `;
}

function addUserMessage(content) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';
    const renderedContent = marked.parse(content);
    messageDiv.innerHTML = `
        <div class="message-avatar user">👤</div>
        <div class="message-body">
            <div class="message-content">${renderedContent}</div>
        </div>
    `;
    messagesDiv.appendChild(messageDiv);
    scrollToBottom();
}

function addAssistantMessage(content) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    const renderedContent = marked.parse(content);
    messageDiv.innerHTML = `
        <div class="message-avatar assistant">🤖</div>
        <div class="message-body">
            <div class="message-content">${renderedContent}</div>
        </div>
    `;
    messagesDiv.appendChild(messageDiv);
    scrollToBottom();
}

function addSystemMessage(content) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system';
    messageDiv.innerHTML = `<div class="message-content">${escapeHtml(content)}</div>`;
    messagesDiv.appendChild(messageDiv);
    scrollToBottom();
}

function startStreaming() {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant streaming';
    messageDiv.innerHTML = `
        <div class="message-avatar assistant">🤖</div>
        <div class="message-body">
            <div class="message-content"></div>
        </div>
    `;
    messagesDiv.appendChild(messageDiv);
}

function appendStreamContent(content) {
    const messagesDiv = document.getElementById('messages');
    const streamingMsg = messagesDiv.querySelector('.streaming .message-content');
    if (streamingMsg) {
        streamingMsg.textContent += content;
        scrollToBottom();
    }
}

function finishStreaming() {
    const messagesDiv = document.getElementById('messages');
    const streamingMsg = messagesDiv.querySelector('.streaming');
    if (streamingMsg) {
        const contentDiv = streamingMsg.querySelector('.message-content');
        const rawContent = contentDiv.textContent;
        const renderedContent = marked.parse(rawContent);
        contentDiv.innerHTML = renderedContent;
        streamingMsg.classList.remove('streaming');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    let escaped = div.innerHTML;
    escaped = escaped.replace(/'/g, "\\'");
    escaped = escaped.replace(/"/g, '&quot;');
    return escaped;
}

function scrollToBottom() {
    const container = document.querySelector('.messages-container');
    container.scrollTop = container.scrollHeight;
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function createNewSession() {
    currentSessionId = 'session_' + Date.now().toString(36);
    showWelcome();

    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });

    if (isConnected) {
        const request = {
            type: 'session',
            action: 'switch',
            new_session_id: currentSessionId,
            session_id: currentSessionId
        };
        ws.send(JSON.stringify(request));
    }
}

function toggleMenu(event, sessionId, title) {
    event.stopPropagation();

    const openMenus = document.querySelectorAll('.dropdown-menu');
    openMenus.forEach(menu => menu.remove());

    const historyItem = event.currentTarget.closest('.history-item');

    const menu = document.createElement('div');
    menu.className = 'dropdown-menu';
    menu.innerHTML = `
        <div class="dropdown-item" onclick="renameSession('${sessionId}', '${title}')">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            重命名
        </div>
        <div class="dropdown-item danger" onclick="deleteSession('${sessionId}')">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            删除
        </div>
    `;

    historyItem.appendChild(menu);

    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 10);
}

async function renameSession(sessionId, currentTitle) {
    const newTitle = prompt('请输入新的对话标题:', currentTitle);
    if (newTitle && newTitle !== currentTitle) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}?new_title=${encodeURIComponent(newTitle)}`, {
                method: 'PATCH'
            });
            const result = await response.json();

            if (result.success) {
                addSystemMessage(result.message);
                loadSessionList();
            } else {
                addSystemMessage('重命名失败: ' + (result.detail || '未知错误'));
            }
        } catch (error) {
            console.error('重命名会话失败:', error);
            addSystemMessage('重命名会话失败: ' + error.message);
        }
    }
}

async function deleteSession(sessionId) {
    if (!confirm('确定要删除这个对话吗？此操作不可恢复。')) return;

    try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        const result = await response.json();

        if (result.success) {
            addSystemMessage(result.message);
            loadSessionList();

            if (sessionId === currentSessionId) {
                createNewSession();
            }
        } else {
            addSystemMessage('删除失败: ' + (result.detail || '未知错误'));
        }
    } catch (error) {
        console.error('删除会话失败:', error);
        addSystemMessage('删除会话失败: ' + error.message);
    }
}

function toggleStream() {
    streamMode = !streamMode;
    const btn = document.getElementById('streamBtn');
    btn.classList.toggle('active', streamMode);
}

function quickAction(text) {
    document.getElementById('messageInput').value = text;
    sendMessage();
}

function toggleSettings() {
    addSystemMessage('设置功能开发中...');
}

window.onload = () => {
    connect();
    loadSessionList();
};

window.onbeforeunload = () => {
    if (ws) {
        ws.close();
    }
};
