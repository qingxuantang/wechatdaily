import os
import time
import datetime
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
from pywinauto.mouse import scroll
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
        time.sleep(1)  # 减少等待时间
        
        print("Opening search box...")
        # 使用快捷键 Ctrl+F 打开搜索框
        send_keys('^f')
        time.sleep(1)  # 减少等待时间
        
        print(f"Searching for group: {config.TARGET_GROUP}")
        # 输入群聊名称并搜索
        send_keys(config.TARGET_GROUP)
        time.sleep(1)  # 减少等待时间
        send_keys('{ENTER}')
        time.sleep(2)  # 减少等待时间
        
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
            time.sleep(0.5)  # 减少等待时间
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
        print(f"Maximum scroll attempts: {config.MAX_SCROLL_ATTEMPTS}")
        print(f"Scroll wait time: {config.SCROLL_WAIT_TIME} seconds")
        
        # 用于存储所有结构信息
        all_structure_lines = []
        
        # 循环滚动和捕获结构
        scroll_count = 0
        
        while scroll_count < config.MAX_SCROLL_ATTEMPTS:
            try:
                print(f"\nAttempting to scroll using scrollbar (attempt {scroll_count + 1})")
                
                # 获取消息列表的位置
                rect = chat_list.rectangle()
                
                # 计算滚动条的位置（在右侧）
                scrollbar_x = rect.right - 10  # 滚动条在右侧，留出一些边距
                scrollbar_top = rect.top + 50  # 从顶部开始
                scrollbar_bottom = rect.bottom - 50  # 到底部结束
                
                # 使用鼠标模拟拖动滚动条
                from pywinauto.mouse import press, release, move
                try:
                    # 移动到滚动条顶部
                    move(coords=(scrollbar_x, scrollbar_top))
                    time.sleep(0.2)  # 减少等待时间
                    
                    # 按下鼠标左键
                    press(coords=(scrollbar_x, scrollbar_top))
                    time.sleep(0.2)  # 减少等待时间
                    
                    # 开始缓慢拖动到滚动条底部
                    current_y = scrollbar_top
                    step = 10  # 增加步长，加快拖动速度
                    reached_top = False
                    
                    while current_y < scrollbar_bottom and not reached_top:
                        # 移动一小步
                        current_y += step
                        move(coords=(scrollbar_x, current_y))
                        time.sleep(0.05)  # 减少等待时间
                        
                        # 检查是否到达顶部
                        try:
                            # 获取消息列表中的第一个消息项
                            first_message = chat_list.children(control_type="ListItem")[0]
                            if first_message.is_visible():
                                print("Reached the top of the message list")
                                reached_top = True
                                # 立即释放鼠标
                                release(coords=(scrollbar_x, current_y))
                                break
                        except Exception as e:
                            print(f"Error checking first message: {str(e)}")
                    
                    # 如果还没有到达顶部，继续拖动到底部
                    if not reached_top:
                        move(coords=(scrollbar_x, scrollbar_bottom))
                        time.sleep(0.2)  # 减少等待时间
                        release(coords=(scrollbar_x, scrollbar_bottom))
                    
                    time.sleep(config.SCROLL_WAIT_TIME)
                except Exception as e:
                    print(f"Error in mouse drag: {str(e)}")
                
                # 尝试找到"查看更多消息"按钮
                more_button = None
                try:
                    # 获取所有匹配的按钮
                    more_buttons = chat_list.children(title="查看更多消息", control_type="Button")
                    # 找到第一个可见的按钮
                    for button in more_buttons:
                        if button.is_visible():
                            more_button = button
                            break
                except Exception as e:
                    print(f"Error finding '查看更多消息' button: {str(e)}")
                
                if more_button:
                    print("\nFound '查看更多消息' button, attempting to click...")
                    try:
                        # 获取按钮位置
                        button_rect = more_button.rectangle()
                        button_x = (button_rect.left + button_rect.right) // 2
                        button_y = (button_rect.top + button_rect.bottom) // 2
                        
                        # 移动到按钮位置并点击
                        move(coords=(button_x, button_y))
                        time.sleep(0.2)  # 减少等待时间
                        press(coords=(button_x, button_y))
                        time.sleep(0.1)
                        release(coords=(button_x, button_y))
                        time.sleep(config.SCROLL_WAIT_TIME)
                    except Exception as e:
                        print(f"Error clicking button: {str(e)}")
                
                # 获取所有已加载的消息结构
                print("Capturing structure of all loaded messages...")
                try:
                    # 获取所有消息项
                    messages = chat_list.children(control_type="ListItem")
                    print(f"Found {len(messages)} messages")
                    
                    # 为每个消息获取结构
                    for msg in messages:
                        try:
                            msg_structure = print_element_structure(msg)
                            all_structure_lines.extend(msg_structure)
                        except Exception as e:
                            print(f"Error getting message structure: {str(e)}")
                except Exception as e:
                    print(f"Error getting messages: {str(e)}")
                
                scroll_count += 1
                print(f"Attempt {scroll_count} completed")
            except Exception as e:
                print(f"Error in main loop: {str(e)}")
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