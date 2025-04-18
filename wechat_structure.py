import os
import time
import datetime
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
import config

def print_element_structure(element, level=0, output_lines=None):
    """递归打印元素结构"""
    if output_lines is None:
        output_lines = []
    
    # 获取元素的基本信息
    try:
        # 获取元素类型
        try:
            control_type = element.control_type()
        except:
            control_type = "Unknown"
            
        # 获取窗口文本
        try:
            window_text = element.window_text()
        except:
            window_text = ""
            
        # 获取位置信息
        try:
            rect = element.rectangle()
            rect_str = f"({rect.left}, {rect.top}, {rect.right}, {rect.bottom})"
        except:
            rect_str = "(Unknown position)"
            
        # 构建元素信息
        element_info = f"{'|    ' * level}{control_type} - '{window_text}'    {rect_str}"
        output_lines.append(element_info)
        
        # 获取元素的类名和自动化ID
        try:
            class_name = element.class_name()
            automation_id = element.automation_id()
            if class_name or automation_id:
                output_lines.append(f"{'|    ' * level}['{class_name}', '{automation_id}']")
        except:
            pass
        
        # 获取元素的子元素
        try:
            children = element.children()
            for child in children:
                print_element_structure(child, level + 1, output_lines)
        except:
            pass
            
    except Exception as e:
        # 将错误信息写入日志文件
        log_filename = f"structure_error_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(config.LOG_PATH, log_filename)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"Error getting element info: {str(e)}")
    
    return output_lines

def export_wechat_structure():
    try:
        print("Connecting to WeChat window...")
        # 使用 UIA 自动化接口连接到微信窗口
        app = Application(backend="uia").connect(class_name=config.WECHAT_WINDOW_CLASS)
        
        # 获取主窗口
        wechat_window = app.window(class_name=config.WECHAT_WINDOW_CLASS)
        
        if not wechat_window.exists():
            raise Exception("WeChat main window not found")
        
        print("Activating WeChat window...")
        # 激活微信窗口
        wechat_window.set_focus()
        time.sleep(2)
        
        print("Opening search box...")
        # 使用快捷键 Ctrl+F 打开搜索框
        send_keys('^f')
        time.sleep(2)
        
        print(f"Searching for group: {config.TARGET_GROUP}")
        # 输入群聊名称并搜索
        send_keys(config.TARGET_GROUP)
        time.sleep(2)
        send_keys('{ENTER}')
        time.sleep(3)
        
        print("Getting chat structure...")
        # 尝试定位消息列表控件
        chat_list = None
        
        # 首先尝试通过标题定位
        try:
            chat_list = wechat_window.child_window(title="消息", control_type="List")
            if chat_list.exists():
                print("Found chat list by title")
        except:
            pass
            
        # 如果没找到，尝试其他方法
        if not chat_list:
            # 获取所有 List 控件
            lists = wechat_window.children(control_type="List")
            if lists:
                # 选择第一个可见的 List 控件
                for lst in lists:
                    if lst.is_visible():
                        chat_list = lst
                        print("Found chat list by visibility")
                        break
        
        if not chat_list:
            raise Exception("Could not find chat message list")
            
        # 确保消息列表获得焦点
        try:
            chat_list.set_focus()
            time.sleep(1)
        except Exception as e:
            print(f"Error setting focus to chat list: {str(e)}")
            
        # 生成文件名（使用当前日期）
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = f"{config.TARGET_GROUP}_structure_{today}.md"
        filepath = os.path.join(config.EXPORT_PATH, filename)
        
        # 确保目录存在
        os.makedirs(config.EXPORT_PATH, exist_ok=True)
        os.makedirs(config.LOG_PATH, exist_ok=True)
        
        # 获取并保存消息结构
        print("Capturing message structure...")
        
        # 用于存储所有结构信息
        all_structure_lines = []
        
        # 循环滚动和捕获结构
        max_scrolls = 50  # 最大滚动次数
        scroll_count = 0
        
        while scroll_count < max_scrolls:
            # 检查是否有"查看更多消息"按钮
            try:
                # 获取所有匹配的按钮
                more_buttons = chat_list.children(title="查看更多消息", control_type="Button")
                # 找到第一个可见的按钮
                visible_button = None
                for button in more_buttons:
                    if button.is_visible():
                        visible_button = button
                        break
                
                if visible_button:
                    print("\nFound '查看更多消息' button, clicking it...")
                    visible_button.click()
                    time.sleep(2)  # 等待加载
                    continue  # 继续检查消息，不执行PageUp
            except Exception as e:
                print(f"Error checking for '查看更多消息' button: {str(e)}")
            
            # 获取当前可见部分的结构
            current_structure = print_element_structure(chat_list)
            all_structure_lines.extend(current_structure)
            
            # 使用键盘 Page Up 实现滚动
            try:
                send_keys('{PGUP}')
                time.sleep(2)
                scroll_count += 1
                print(f"Scrolled {scroll_count} times")
            except Exception as e:
                print(f"Error scrolling messages: {str(e)}")
                break
        
        # 将结构写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_structure_lines))
        
        print(f"Successfully exported chat structure to {filepath}")
        
    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        print(error_msg)
        # 将错误信息写入日志文件
        log_filename = f"error_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(config.LOG_PATH, log_filename)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        raise

if __name__ == "__main__":
    export_wechat_structure() 