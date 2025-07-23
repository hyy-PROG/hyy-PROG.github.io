import sys
import json
import uuid
import os
import logging
import base64
from functools import wraps
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('hyyhtml')

class JSBridge(QObject):
    callPythonRequested = pyqtSignal(str, list, str, arguments=['funcName', 'args', 'callbackId'])
    callbackToJS = pyqtSignal(str, bool, str, arguments=['callbackId', 'success', 'result'])
    pythonMessage = pyqtSignal(str, arguments=['message'])

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.callPythonRequested.connect(self.handleCall)
        self.pythonMessage.connect(self.logToJS)

    @pyqtSlot(str, list, str)
    def handleCall(self, funcName, args, callbackId):
        try:
            # 检查是否是窗口控制方法
            if hasattr(self.window, funcName) and callable(getattr(self.window, funcName)):
                func = getattr(self.window, funcName)
                result = func(*args) if args else func()
                self.callbackToJS.emit(callbackId, True, json.dumps(result))
                return
            
            # 检查是否是注册的API函数
            if funcName in self.window.exposed_functions:
                func = self.window.exposed_functions[funcName]
                result = func(*args) if args else func()
                self.callbackToJS.emit(callbackId, True, json.dumps(result))
                return
            
            raise Exception(f"Function '{funcName}' not found")
        except Exception as e:
            logger.error(f"Error calling {funcName}: {str(e)}")
            self.callbackToJS.emit(callbackId, False, json.dumps({"error": str(e)}))
    
    @pyqtSlot(str)
    def logToJS(self, message):
        """发送日志消息到JavaScript"""
        self.window.page.runJavaScript(f"logToConsole('{message}', 'info')")


class Window(QMainWindow):
    _app_instance = None
    
    def __init__(self):
        # 确保QApplication实例存在
        if Window._app_instance is None:
            Window._app_instance = QApplication(sys.argv)
        super().__init__()
        
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        
        self.channel = QWebChannel()
        self.bridge = JSBridge(self)
        
        self.page = self.browser.page()
        self.page.setWebChannel(self.channel)
        
        self.timers = {}
        self.exposed_functions = {}
        
        # 注册窗口控制方法
        self.register_window_methods()
        
        # 设置默认窗口
        self.set_defaults()
        
        # 加载HTML页面
        self.load_html()
        
        # 注册桥接对象
        self.channel.registerObject('bridge', self.bridge)

    def register_window_methods(self):
        """注册所有窗口控制方法"""
        self.window_methods = {
            'set_title': self.set_title,
            'set_size': self.set_size,
            'set_icon': self.set_icon,
            'set_position': self.set_position,
            'center': self.center,
            'show': self.show_window,
            'hide': self.hide_window,
            'minimize': self.minimize,
            'maximize': self.maximize,
            'restore': self.restore,
            'fullscreen': self.fullscreen,
            'close': self.close_window,
            'set_min_size': self.set_min_size,
            'set_max_size': self.set_max_size,
            'after': self.after,
            'get_size': self.get_size,
            'get_position': self.get_position,
            'set_opacity': self.set_opacity,
            'set_topmost': self.set_topmost,
            'get_screen_info': self.get_screen_info,
            'set_background_color': self.set_background_color,
            'show_message': self.show_message,
            'get_clipboard_text': self.get_clipboard_text,
            'set_clipboard_text': self.set_clipboard_text,
            'execute_js': self.execute_js,
            'load_url': self.load_url,
            'reload': self.reload_page,
            'go_back': self.go_back,
            'go_forward': self.go_forward,
            'set_zoom': self.set_zoom,
            'get_zoom': self.get_zoom,
            'add_menu': self.add_menu,
            'add_toolbar': self.add_toolbar,
            'add_statusbar': self.add_statusbar,
            'set_statusbar_text': self.set_statusbar_text,
            'show_dialog': self.show_dialog,
            'get_window_state': self.get_window_state,
            'set_window_style': self.set_window_style,
            'set_cursor': self.set_cursor,
            'set_mouse_tracking': self.set_mouse_tracking,
            'capture_screen': self.capture_screen
        }

    def set_defaults(self):
        """设置窗口默认值"""
        self.setWindowTitle("HyyHTML Application")
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        
        # 设置默认图标
        self.setWindowIcon(self.create_default_icon())
        
        # 创建状态栏
        self.statusBar().showMessage("Ready")

    def create_default_icon(self):
        """创建默认应用程序图标"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(70, 130, 180))  # 钢蓝色
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 32, 32)
        
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "H")
        painter.end()
        
        return QIcon(pixmap)
        
    def load_html(self):
        """加载HTML页面"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>HyyHTML Application</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }
                
                body {
                    background: linear-gradient(135deg, #1a2a6c, #b21f1f, #1a2a6c);
                    background-size: 400% 400%;
                    animation: gradientBG 15s ease infinite;
                    color: white;
                    min-height: 100vh;
                    padding: 20px;
                }
                
                @keyframes gradientBG {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                header {
                    text-align: center;
                    padding: 30px 0;
                    margin-bottom: 40px;
                    border-bottom: 2px solid rgba(255, 255, 255, 0.2);
                }
                
                h1 {
                    font-size: 3rem;
                    margin-bottom: 10px;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                }
                
                .subtitle {
                    font-size: 1.2rem;
                    opacity: 0.8;
                    margin-bottom: 20px;
                }
                
                .content {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 30px;
                    margin-bottom: 40px;
                }
                
                .card {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 25px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                }
                
                .card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3);
                }
                
                .card h2 {
                    margin-bottom: 20px;
                    font-size: 1.8rem;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    color: #ffcc00;
                }
                
                .card p {
                    margin-bottom: 20px;
                    line-height: 1.6;
                }
                
                .btn-group {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-top: 15px;
                }
                
                .btn {
                    background: rgba(255, 255, 255, 0.15);
                    border: none;
                    color: white;
                    padding: 12px 25px;
                    border-radius: 50px;
                    font-size: 1rem;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }
                
                .btn:hover {
                    background: rgba(255, 255, 255, 0.25);
                    transform: translateY(-2px);
                }
                
                .btn-primary {
                    background: linear-gradient(135deg, #00b09b, #96c93d);
                }
                
                .btn-primary:hover {
                    background: linear-gradient(135deg, #009a7f, #7db02e);
                }
                
                .btn-danger {
                    background: linear-gradient(135deg, #ff416c, #ff4b2b);
                }
                
                .btn-danger:hover {
                    background: linear-gradient(135deg, #e02e56, #e03a1a);
                }
                
                .btn-info {
                    background: linear-gradient(135deg, #4A00E0, #8E2DE2);
                }
                
                .btn-info:hover {
                    background: linear-gradient(135deg, #3a00b0, #6d1dc2);
                }
                
                .console {
                    background: rgba(0, 0, 0, 0.3);
                    border-radius: 8px;
                    padding: 20px;
                    font-family: 'Courier New', monospace;
                    max-height: 300px;
                    overflow-y: auto;
                    margin-top: 20px;
                }
                
                .console h3 {
                    margin-bottom: 10px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    color: #00ccff;
                }
                
                .log-entry {
                    padding: 8px 0;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    font-size: 0.9rem;
                }
                
                .log-entry:last-child {
                    border-bottom: none;
                }
                
                .success {
                    color: #7eff7e;
                }
                
                .error {
                    color: #ff7e7e;
                }
                
                .info {
                    color: #7ec0ff;
                }
                
                footer {
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid rgba(255, 255, 255, 0.2);
                    font-size: 0.9rem;
                    opacity: 0.7;
                }
                
                .icon {
                    font-size: 1.5rem;
                }
                
                .grid-2 {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                }
                
                @media (max-width: 768px) {
                    .grid-2 {
                        grid-template-columns: 1fr;
                    }
                    
                    h1 {
                        font-size: 2.2rem;
                    }
                }
            </style>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script>
                // 全局hyyhtml对象
                window.hyyhtml = {
                    ready: false,
                    _callbacks: {}
                };
                
                // 初始化函数
                function initHyyHTML() {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        const bridge = channel.objects.bridge;
                        
                        // 处理回调
                        bridge.callbackToJS.connect(function(callbackId, success, result) {
                            const callback = window.hyyhtml._callbacks[callbackId];
                            if (callback) {
                                try {
                                    const parsedResult = JSON.parse(result);
                                    if (success) {
                                        callback.resolve(parsedResult);
                                    } else {
                                        callback.reject(parsedResult.error || "Unknown error");
                                    }
                                } catch (e) {
                                    callback.reject("Error parsing result: " + e);
                                }
                                delete window.hyyhtml._callbacks[callbackId];
                            }
                        });
                        
                        // 创建调用Python函数的统一方法
                        window.hyyhtml.callPython = function(funcName, ...args) {
                            return new Promise((resolve, reject) => {
                                const callbackId = generateUUID();
                                window.hyyhtml._callbacks[callbackId] = { resolve, reject };
                                
                                if (bridge) {
                                    try {
                                        bridge.callPythonRequested(funcName, args, callbackId);
                                    } catch (e) {
                                        reject(`Error calling Python: ${e}`);
                                    }
                                } else {
                                    reject("Bridge not ready");
                                }
                            });
                        };
                        
                        // 标记为就绪
                        window.hyyhtml.ready = true;
                        
                        logToConsole("HyyHTML bridge initialized successfully!", "success");
                        
                        // 初始化UI事件
                        initUIEvents();
                    });
                }
                
                // 生成UUID
                function generateUUID() {
                    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                        const r = Math.random() * 16 | 0;
                        const v = c === 'x' ? r : (r & 0x3 | 0x8);
                        return v.toString(16);
                    });
                }
                
                // 控制台日志函数
                function logToConsole(message, type = "info") {
                    const consoleEl = document.getElementById('console');
                    if (consoleEl) {
                        const entry = document.createElement('div');
                        entry.className = `log-entry ${type}`;
                        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
                        consoleEl.appendChild(entry);
                        consoleEl.scrollTop = consoleEl.scrollHeight;
                    }
                    
                    // 同时输出到浏览器控制台
                    console.log(`[${type.toUpperCase()}] ${message}`);
                }
                
                // 初始化UI事件
                function initUIEvents() {
                    // 设置按钮事件处理程序
                    const bindButton = (id, funcName, ...args) => {
                        const btn = document.getElementById(id);
                        if (btn) {
                            btn.addEventListener('click', () => {
                                window.hyyhtml.callPython(funcName, ...args)
                                    .then(result => {
                                        logToConsole(`Python ${funcName}() succeeded: ${JSON.stringify(result)}`, "success");
                                    })
                                    .catch(error => {
                                        logToConsole(`Error calling ${funcName}(): ${error}`, "error");
                                    });
                            });
                        }
                    };
                    
                    // 绑定按钮
                    bindButton('btn-hello', 'hello');
                    bindButton('btn-destroy', 'destroy');
                    bindButton('btn-move', 'set_position', Math.floor(Math.random() * 500), Math.floor(Math.random() * 300));
                    bindButton('btn-resize', 'set_size', 800, 600);
                    bindButton('btn-center', 'center');
                    bindButton('btn-minimize', 'minimize');
                    bindButton('btn-maximize', 'maximize');
                    bindButton('btn-restore', 'restore');
                    bindButton('btn-fullscreen', 'fullscreen');
                    bindButton('btn-hide', 'hide_window');
                    bindButton('btn-show', 'show_window');
                    bindButton('btn-opacity', 'set_opacity', 0.7);
                    bindButton('btn-topmost', 'set_topmost', true);
                    bindButton('btn-notify', 'show_message', 'Hello from HyyHTML', 'This is a system notification!');
                    bindButton('btn-capture', 'capture_screen');
                    bindButton('btn-screenshot', 'capture_window');
                    bindButton('btn-clipboard', 'set_clipboard_text', 'Text from HyyHTML app');
                    bindButton('btn-js', 'execute_js', 'document.body.style.backgroundColor = "#2c3e50"');
                    bindButton('btn-reload', 'reload');
                    bindButton('btn-zoom', 'set_zoom', 1.2);
                    
                    // 初始日志
                    logToConsole("HyyHTML application started", "info");
                    logToConsole("Click buttons to interact with Python backend", "info");
                }
                
                // 页面加载完成后初始化
                document.addEventListener("DOMContentLoaded", function() {
                    // 初始化hyyhtml
                    initHyyHTML();
                });
            </script>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>HyyHTML Desktop</h1>
                    <div class="subtitle">Seamless Python & JavaScript Integration</div>
                </header>
                
                <div class="content">
                    <div class="card">
                        <h2><span class="icon">🚀</span> Core Functions</h2>
                        <p>Call Python functions directly from JavaScript using the hyyhtml.callPython method.</p>
                        
                        <div class="btn-group">
                            <button id="btn-hello" class="btn btn-primary">
                                <span class="icon">👋</span> Call hello()
                            </button>
                            <button id="btn-destroy" class="btn btn-danger">
                                <span class="icon">❌</span> Call destroy()
                            </button>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2><span class="icon">🖼️</span> Window Control</h2>
                        <p>Control the application window directly from JavaScript.</p>
                        
                        <div class="btn-group">
                            <button id="btn-move" class="btn btn-info">
                                <span class="icon">↕️</span> Move Window
                            </button>
                            <button id="btn-resize" class="btn btn-info">
                                <span class="icon">↔️</span> Resize
                            </button>
                            <button id="btn-center" class="btn btn-info">
                                <span class="icon">🎯</span> Center
                            </button>
                        </div>
                        
                        <div class="btn-group">
                            <button id="btn-minimize" class="btn">
                                <span class="icon">⬇️</span> Minimize
                            </button>
                            <button id="btn-maximize" class="btn">
                                <span class="icon">⬆️</span> Maximize
                            </button>
                            <button id="btn-restore" class="btn">
                                <span class="icon">↩️</span> Restore
                            </button>
                        </div>
                        
                        <div class="btn-group">
                            <button id="btn-fullscreen" class="btn">
                                <span class="icon">📺</span> Fullscreen
                            </button>
                            <button id="btn-hide" class="btn">
                                <span class="icon">👁️</span> Hide
                            </button>
                            <button id="btn-show" class="btn">
                                <span class="icon">👁️‍🗨️</span> Show
                            </button>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2><span class="icon">⚙️</span> Advanced Features</h2>
                        <p>Access advanced window and system features.</p>
                        
                        <div class="btn-group">
                            <button id="btn-opacity" class="btn">
                                <span class="icon">🌫️</span> Set Opacity
                            </button>
                            <button id="btn-topmost" class="btn">
                                <span class="icon">📌</span> Set Topmost
                            </button>
                            <button id="btn-notify" class="btn">
                                <span class="icon">🔔</span> Show Notification
                            </button>
                        </div>
                        
                        <div class="btn-group">
                            <button id="btn-capture" class="btn">
                                <span class="icon">📷</span> Capture Screen
                            </button>
                            <button id="btn-screenshot" class="btn">
                                <span class="icon">🖼️</span> Capture Window
                            </button>
                            <button id="btn-clipboard" class="btn">
                                <span class="icon">📋</span> Set Clipboard
                            </button>
                        </div>
                        
                        <div class="btn-group">
                            <button id="btn-js" class="btn">
                                <span class="icon">🔧</span> Execute JS
                            </button>
                            <button id="btn-reload" class="btn">
                                <span class="icon">🔄</span> Reload
                            </button>
                            <button id="btn-zoom" class="btn">
                                <span class="icon">🔍</span> Zoom In
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3><span class="icon">📝</span> Console Log</h3>
                    <div id="console" class="console"></div>
                </div>
                
                <footer>
                    <p>Powered by HyyHTML | Python + HTML + CSS + JavaScript</p>
                </footer>
            </div>
        </body>
        </html>
        """
        self.browser.setHtml(html_content)

    def api(self, func):
        """装饰器，用于注册Python函数给JavaScript调用"""
        self.exposed_functions[func.__name__] = func
        logger.info(f"Registered function for JavaScript: {func.__name__}")
        return func

    def log(self, message):
        """发送日志消息到JavaScript控制台"""
        self.bridge.pythonMessage.emit(message)

    def start(self):
        """启动应用"""
        self.show()
        logger.info("Application started")
        sys.exit(Window._app_instance.exec())
    
    def set_title(self, title):
        """设置窗口标题"""
        self.setWindowTitle(title)
        self.log(f"Window title set to: {title}")
        return {"status": "success", "title": title}
    
    def set_size(self, width, height):
        """设置窗口大小"""
        super().resize(width, height)
        self.log(f"Window size set to: {width}x{height}")
        return {"status": "success", "width": width, "height": height}
    
    def set_icon(self, icon_path):
        """设置窗口图标"""
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            self.log(f"Window icon set to: {icon_path}")
            return {"status": "success", "icon": icon_path}
        else:
            self.log(f"Icon file not found: {icon_path}")
            return {"status": "error", "message": "Icon file not found"}
    
    def set_position(self, x, y):
        """移动窗口到指定位置"""
        super().move(x, y)
        self.log(f"Window moved to: ({x}, {y})")
        return {"status": "success", "x": x, "y": y}
    
    def center(self):
        """居中窗口"""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        super().move(x, y)
        self.log("Window centered")
        return {"status": "success", "position": "centered"}
    
    def show_window(self):
        """显示窗口"""
        super().show()
        self.log("Window shown")
        return {"status": "success", "visible": True}
    
    def hide_window(self):
        """隐藏窗口"""
        super().hide()
        self.log("Window hidden")
        return {"status": "success", "visible": False}
    
    def minimize(self):
        """最小化窗口"""
        super().showMinimized()
        self.log("Window minimized")
        return {"status": "success", "state": "minimized"}
    
    def maximize(self):
        """最大化窗口"""
        super().showMaximized()
        self.log("Window maximized")
        return {"status": "success", "state": "maximized"}
    
    def restore(self):
        """恢复窗口"""
        super().showNormal()
        self.log("Window restored")
        return {"status": "success", "state": "normal"}
    
    def fullscreen(self):
        """全屏显示"""
        super().showFullScreen()
        self.log("Window set to fullscreen")
        return {"status": "success", "state": "fullscreen"}
    
    def close_window(self):
        """关闭窗口"""
        super().close()
        self.log("Window closed")
        return {"status": "success", "closed": True}
    
    def set_min_size(self, width, height):
        """设置最小尺寸"""
        super().setMinimumSize(width, height)
        self.log(f"Minimum size set to: {width}x{height}")
        return {"status": "success", "min_width": width, "min_height": height}
    
    def set_max_size(self, width, height):
        """设置最大尺寸"""
        super().setMaximumSize(width, height)
        self.log(f"Maximum size set to: {width}x{height}")
        return {"status": "success", "max_width": width, "max_height": height}
    
    def after(self, ms, func_name, *args):
        """在指定毫秒后执行函数"""
        def execute_func():
            if func_name in self.exposed_functions:
                self.exposed_functions[func_name](*args)
            elif hasattr(self, func_name) and callable(getattr(self, func_name)):
                getattr(self, func_name)(*args)
        
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(execute_func)
        timer.start(ms)
        
        self.log(f"Scheduled function '{func_name}' to run after {ms}ms")
        return {"status": "success", "timeout": ms, "function": func_name}
    
    def get_size(self):
        """获取窗口大小"""
        size = self.size()
        return {"width": size.width(), "height": size.height()}
    
    def get_position(self):
        """获取窗口位置"""
        pos = self.pos()
        return {"x": pos.x(), "y": pos.y()}
    
    def set_opacity(self, opacity):
        """设置窗口透明度"""
        if 0.0 <= opacity <= 1.0:
            self.setWindowOpacity(opacity)
            self.log(f"Window opacity set to: {opacity}")
            return {"status": "success", "opacity": opacity}
        else:
            self.log("Invalid opacity value. Must be between 0.0 and 1.0")
            return {"status": "error", "message": "Invalid opacity value"}
    
    def set_topmost(self, topmost):
        """设置窗口置顶"""
        flags = self.windowFlags()
        if topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        
        self.setWindowFlags(flags)
        self.show()  # 需要重新显示窗口使设置生效
        
        status = "topmost" if topmost else "normal"
        self.log(f"Window set to: {status}")
        return {"status": "success", "topmost": topmost}
    
    def get_screen_info(self):
        """获取屏幕信息"""
        screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        return {
            "width": geometry.width(),
            "height": geometry.height(),
            "dpi": screen.logicalDotsPerInch(),
            "name": screen.name(),
            "depth": screen.depth()
        }
    
    def set_background_color(self, color):
        """设置背景颜色"""
        self.browser.page().setBackgroundColor(QColor(color))
        self.log(f"Background color set to: {color}")
        return {"status": "success", "color": color}
    
    def show_message(self, title, message):
        """显示系统通知"""
        QMessageBox.information(self, title, message)
        self.log(f"Showed message: {title} - {message}")
        return {"status": "success", "title": title, "message": message}
    
    def get_clipboard_text(self):
        """获取剪贴板文本"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        self.log("Retrieved text from clipboard")
        return {"status": "success", "text": text}
    
    def set_clipboard_text(self, text):
        """设置剪贴板文本"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.log(f"Set clipboard text to: {text}")
        return {"status": "success", "text": text}
    
    def execute_js(self, code):
        """执行JavaScript代码"""
        self.browser.page().runJavaScript(code)
        self.log(f"Executed JavaScript: {code}")
        return {"status": "success", "code": code}
    
    def load_url(self, url):
        """加载URL"""
        self.browser.load(QUrl(url))
        self.log(f"Loaded URL: {url}")
        return {"status": "success", "url": url}
    
    def reload_page(self):
        """重新加载页面"""
        self.browser.reload()
        self.log("Page reloaded")
        return {"status": "success"}
    
    def go_back(self):
        """导航回退"""
        self.browser.back()
        self.log("Navigated back")
        return {"status": "success"}
    
    def go_forward(self):
        """导航前进"""
        self.browser.forward()
        self.log("Navigated forward")
        return {"status": "success"}
    
    def set_zoom(self, factor):
        """设置缩放因子"""
        self.browser.setZoomFactor(factor)
        self.log(f"Zoom factor set to: {factor}")
        return {"status": "success", "zoom": factor}
    
    def get_zoom(self):
        """获取缩放因子"""
        factor = self.browser.zoomFactor()
        return {"status": "success", "zoom": factor}
    
    def add_menu(self, title):
        """添加菜单栏"""
        menu = self.menuBar().addMenu(title)
        self.log(f"Added menu: {title}")
        return {"status": "success", "title": title}
    
    def add_toolbar(self, title):
        """添加工具栏"""
        toolbar = QToolBar(title, self)
        self.addToolBar(toolbar)
        self.log(f"Added toolbar: {title}")
        return {"status": "success", "title": title}
    
    def add_statusbar(self):
        """添加状态栏"""
        self.statusBar()
        self.log("Status bar added")
        return {"status": "success"}
    
    def set_statusbar_text(self, text):
        """设置状态栏文本"""
        self.statusBar().showMessage(text)
        self.log(f"Status bar text set to: {text}")
        return {"status": "success", "text": text}
    
    def show_dialog(self, dialog_type, title, message):
        """显示对话框"""
        dialog_type = dialog_type.lower()
        if dialog_type == "info":
            QMessageBox.information(self, title, message)
        elif dialog_type == "warning":
            QMessageBox.warning(self, title, message)
        elif dialog_type == "critical":
            QMessageBox.critical(self, title, message)
        elif dialog_type == "question":
            return QMessageBox.question(self, title, message)
        else:
            self.log(f"Unknown dialog type: {dialog_type}")
            return {"status": "error", "message": "Unknown dialog type"}
        
        self.log(f"Showed {dialog_type} dialog: {title}")
        return {"status": "success", "type": dialog_type, "title": title}
    
    def get_window_state(self):
        """获取窗口状态"""
        state = "normal"
        if self.isMinimized():
            state = "minimized"
        elif self.isMaximized():
            state = "maximized"
        elif self.isFullScreen():
            state = "fullscreen"
        
        return {
            "state": state,
            "visible": self.isVisible(),
            "active": self.isActiveWindow(),
            "topmost": bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        }
    
    def set_window_style(self, style):
        """设置窗口样式"""
        self.setStyle(style)
        self.log(f"Window style set to: {style}")
        return {"status": "success", "style": style}
    
    def set_cursor(self, cursor_type):
        """设置鼠标光标"""
        cursor_map = {
            "arrow": Qt.CursorShape.ArrowCursor,
            "wait": Qt.CursorShape.WaitCursor,
            "cross": Qt.CursorShape.CrossCursor,
            "hand": Qt.CursorShape.PointingHandCursor,
            "ibeam": Qt.CursorShape.IBeamCursor,
            "sizev": Qt.CursorShape.SizeVerCursor,
            "sizeh": Qt.CursorShape.SizeHorCursor
        }
        
        if cursor_type in cursor_map:
            self.setCursor(QCursor(cursor_map[cursor_type]))
            self.log(f"Cursor set to: {cursor_type}")
            return {"status": "success", "cursor": cursor_type}
        else:
            self.log(f"Unknown cursor type: {cursor_type}")
            return {"status": "error", "message": "Unknown cursor type"}
    
    def set_mouse_tracking(self, enable):
        """设置鼠标跟踪"""
        self.setMouseTracking(enable)
        self.log(f"Mouse tracking {'enabled' if enable else 'disabled'}")
        return {"status": "success", "enabled": enable}
    
    def capture_screen(self):
        """捕获整个屏幕"""
        screen = QApplication.primaryScreen()
        pixmap = screen.grabWindow(0)
        return self.process_pixmap(pixmap, "screen")
    
    def capture_window(self):
        """捕获当前窗口"""
        pixmap = self.grab()
        return self.process_pixmap(pixmap, "window")
    
    def process_pixmap(self, pixmap, source):
        """处理捕获的图像"""
        # 转换为Base64
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.ReadWrite)
        pixmap.save(buffer, "PNG")
        base64_data = base64.b64encode(buffer.data()).decode('utf-8')
        
        self.log(f"Captured {source} image")
        return {
            "status": "success",
            "source": source,
            "width": pixmap.width(),
            "height": pixmap.height(),
            "format": "PNG",
            "base64": f"data:image/png;base64,{base64_data}"
        }

# ==================================================
# 用户代码 (main.py)
# ==================================================
# 创建窗口实例
window = Window()

# 使用装饰器注册API函数
@window.api
def hello():
    """简单的示例函数"""
    window.log("Hello from Python!")
    return {"message": "Hello from Python!", "status": "success"}

@window.api
def destroy():
    """销毁窗口的函数"""
    window.log("Destroying window...")
    window.close_window()
    return {"status": "closed"}

# 配置窗口
window.set_title("HyyHTML Demo Application")
window.set_size(800, 600)
window.set_min_size(400, 300)
window.center()

# 3秒后调用hello函数
window.after(3000, "hello")

# 启动应用
window.start()