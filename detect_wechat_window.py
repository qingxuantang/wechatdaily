import sys
import os
from pywinauto.application import Application
from pywinauto import Desktop
import time

def detect_wechat_windows():
    """检测所有可能的微信窗口"""
    print("正在检测微信窗口...")
    print("=" * 50)
    
    # 方法1: 尝试通过标题查找
    print("方法1: 通过窗口标题查找")
    try:
        # 尝试不同的标题
        possible_titles = ["微信", "WeChat", "微信PC版"]
        for title in possible_titles:
            try:
                app = Application(backend="uia").connect(title=title)
                print(f"✓ 找到微信窗口，标题: {title}")
                print(f"  窗口类名: {app.window(title=title).class_name()}")
                return app.window(title=title).class_name()
            except Exception as e:
                print(f"✗ 标题 '{title}' 未找到: {str(e)}")
    except Exception as e:
        print(f"通过标题查找失败: {str(e)}")
    
    print()
    
    # 方法2: 列出所有窗口，查找包含"微信"或"WeChat"的窗口
    print("方法2: 列出所有窗口")
    try:
        windows = Desktop(backend="uia").windows()
        wechat_windows = []
        
        for window in windows:
            try:
                title = window.window_text()
                class_name = window.class_name()
                
                # 检查是否包含微信相关关键词
                if any(keyword in title.lower() for keyword in ['微信', 'wechat']) or \
                   any(keyword in class_name.lower() for keyword in ['wechat', 'wx']):
                    wechat_windows.append((title, class_name))
                    print(f"✓ 可能的微信窗口:")
                    print(f"  标题: {title}")
                    print(f"  类名: {class_name}")
                    print()
            except:
                continue
        
        if wechat_windows:
            print("找到以下可能的微信窗口:")
            for i, (title, class_name) in enumerate(wechat_windows, 1):
                print(f"{i}. 标题: {title}")
                print(f"   类名: {class_name}")
                print()
            return wechat_windows[0][1]  # 返回第一个找到的类名
        else:
            print("未找到任何可能的微信窗口")
            
    except Exception as e:
        print(f"列出窗口失败: {str(e)}")
    
    print()
    
    # 方法3: 尝试常见的微信窗口类名
    print("方法3: 尝试常见的微信窗口类名")
    common_class_names = [
        "WeChatMainWndForPC",
        "WeChatMainWnd",
        "WeChatWindow",
        "WeChat",
        "WxMainWindow",
        "WxWindow"
    ]
    
    for class_name in common_class_names:
        try:
            app = Application(backend="uia").connect(class_name=class_name)
            print(f"✓ 找到微信窗口，类名: {class_name}")
            return class_name
        except Exception as e:
            print(f"✗ 类名 '{class_name}' 未找到: {str(e)}")
    
    print()
    print("=" * 50)
    print("检测完成。如果未找到微信窗口，请确保:")
    print("1. 微信PC客户端已启动")
    print("2. 微信窗口处于可见状态")
    print("3. 微信版本兼容")
    
    return None

def test_connection(class_name):
    """测试连接到指定类名的窗口"""
    if not class_name:
        print("没有可用的类名进行测试")
        return False
    
    print(f"\n正在测试连接到类名: {class_name}")
    try:
        app = Application(backend="uia").connect(class_name=class_name)
        window = app.window(class_name=class_name)
        
        if window.exists():
            print(f"✓ 成功连接到窗口: {class_name}")
            print(f"  窗口标题: {window.window_text()}")
            return True
        else:
            print(f"✗ 窗口存在但无法访问: {class_name}")
            return False
    except Exception as e:
        print(f"✗ 连接失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("微信窗口检测工具")
    print("请确保微信PC客户端已启动并可见")
    print()
    
    # 检测微信窗口
    detected_class_name = detect_wechat_windows()
    
    if detected_class_name:
        print(f"\n建议更新配置文件中的 WECHAT_WINDOW_CLASS 为: {detected_class_name}")
        
        # 测试连接
        if test_connection(detected_class_name):
            print("\n✓ 连接测试成功！可以更新配置文件。")
        else:
            print("\n✗ 连接测试失败，可能需要其他方法。")
    else:
        print("\n未检测到微信窗口，请检查微信是否正常运行。") 