import os
import time
import datetime
import schedule
import argparse
import sys
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
import config
import logging
import re
from tqdm import tqdm
from pywinauto.mouse import press, release, move
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import threading
import math
import json

# 配置日志
def setup_logging():
    # 确保日志目录存在
    os.makedirs(config.LOG_PATH, exist_ok=True)
    
    # 创建日志文件名
    log_filename = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(config.LOG_PATH, log_filename)
    
    # 配置日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    return logging.getLogger(__name__)

class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.console = sys.stdout
        self.log = None
        try:
            # 确保日志目录存在
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            self.log = open(log_file, 'w', encoding='utf-8')
        except Exception as e:
            print(f"Warning: Could not initialize log file: {str(e)}")
            print("Logging will continue to console only")
        
    def write(self, message):
        try:
            if self.console:
                self.console.write(message)
        except Exception as e:
            pass
            
        if self.log is not None:
            try:
                self.log.write(message)
                self.log.flush()
            except Exception as e:
                pass
        
    def close(self):
        if self.log is not None:
            try:
                self.log.close()
            except Exception as e:
                pass

def get_latest_message_time(messages):
    """从消息列表中获取最新的消息时间"""
    latest_time = None
    for msg in messages:
        if is_timestamp(msg):
            try:
                # 尝试解析完整日期时间
                date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日 (\d{1,2}):(\d{2})'
                time_pattern = r'(\d{1,2}):(\d{2})'
                
                match = re.search(date_pattern, msg)
                if match:
                    year, month, day, hour, minute = map(int, match.groups())
                    msg_time = datetime.datetime(year, month, day, hour, minute)
                else:
                    match = re.search(time_pattern, msg)
                    if match:
                        hour, minute = map(int, match.groups())
                        today = datetime.datetime.now()
                        msg_time = datetime.datetime(today.year, today.month, today.day, hour, minute)
                    else:
                        continue
                        
                if latest_time is None or msg_time > latest_time:
                    latest_time = msg_time
            except:
                continue
                
    return latest_time

def is_in_time_range(text, start_time):
    """检查消息是否在时间范围内"""
    try:
        # 尝试从消息文本中提取日期
        date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日 (\d{1,2}):(\d{2})'
        time_pattern = r'(\d{1,2}):(\d{2})'
        
        # 尝试匹配完整日期
        match = re.search(date_pattern, text)
        if match:
            year, month, day, hour, minute = map(int, match.groups())
            message_time = datetime.datetime(year, month, day, hour, minute)
            return start_time <= message_time
            
        # 尝试匹配时间（假设是今天的消息）
        match = re.search(time_pattern, text)
        if match:
            hour, minute = map(int, match.groups())
            today = datetime.datetime.now()
            message_time = datetime.datetime(today.year, today.month, today.day, hour, minute)
            return start_time <= message_time
            
        return False
    except:
        return False

def extract_text_content(element, messages=None):
    """递归提取元素中的文本内容"""
    if messages is None:
        messages = []
    
    try:
        # 获取窗口文本
        text = element.window_text()
        if text and text.strip():  # 只保存非空文本
            messages.append(text)
            
        # 递归处理子元素
        children = element.children()
        for child in children:
            extract_text_content(child, messages)
    except Exception as e:
        logging.error(f"Error extracting text content: {str(e)}")
    
    return messages

def is_timestamp(text):
    """检查文本是否是时间戳"""
    # 匹配完整日期时间格式：2025年4月10日 20:44
    full_pattern = r'\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}:\d{2}'
    # 匹配只有时间格式：20:44
    time_pattern = r'^\d{1,2}:\d{2}$'
    # 匹配昨天格式：昨天 20:44
    yesterday_pattern = r'^昨天 \d{1,2}:\d{2}$'
    # 匹配星期格式：星期天 20:44
    weekday_pattern = r'^(星期一|星期二|星期三|星期四|星期五|星期六|星期天) \d{1,2}:\d{2}$'
    
    return bool(re.match(full_pattern, text) or 
                re.match(time_pattern, text) or 
                re.match(yesterday_pattern, text) or
                re.match(weekday_pattern, text))

def is_system_message(text):
    """检查是否是系统消息"""
    system_messages = ["消息", "查看更多消息", "[图片]", "撤回了一条消息"]
    return any(msg in text for msg in system_messages)

def remove_duplicates(messages):
    """去除重复的消息，但保留必要的发言者信息"""
    unique_messages = []
    last_timestamp = None
    last_sender = None
    
    for msg in messages:
        # 跳过空消息
        if not msg.strip():
            continue
            
        # 处理时间戳
        if is_timestamp(msg):
            last_timestamp = msg
            unique_messages.append(msg)
            continue
            
        # 处理系统消息
        if is_system_message(msg):
            unique_messages.append(msg)
            continue
            
        # 处理发言者名称
        # 如果当前消息不是时间戳也不是系统消息，且与上一条消息不同，则认为是新的发言者
        if msg != last_sender and not is_timestamp(msg) and not is_system_message(msg):
            last_sender = msg
            unique_messages.append(msg)
            continue
            
        # 处理消息内容
        # 如果当前消息与上一条消息相同，且不是时间戳、系统消息或发言者名称，则跳过
        if msg in unique_messages and not is_timestamp(msg) and not is_system_message(msg):
            continue
            
        unique_messages.append(msg)
    
    return unique_messages

def parse_message_time(msg):
    """解析消息中的时间"""
    try:
        # 尝试解析中文日期时间格式：2025年4月10日 20:44
        full_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日 (\d{1,2}):(\d{2})'
        time_pattern = r'(\d{1,2}):(\d{2})'
        yesterday_pattern = r'昨天 (\d{1,2}):(\d{2})'
        weekday_pattern = r'(星期一|星期二|星期三|星期四|星期五|星期六|星期天) (\d{1,2}):(\d{2})'
        
        # 先尝试解析完整日期时间
        match = re.search(full_pattern, msg)
        if match:
            year, month, day, hour, minute = map(int, match.groups())
            msg_time = datetime.datetime(year, month, day, hour, minute)
            print(f"Parsed full timestamp: {msg_time}")
            return msg_time
            
        # 尝试解析"昨天"格式
        match = re.search(yesterday_pattern, msg)
        if match:
            hour, minute = map(int, match.groups())
            # 使用昨天的日期
            yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
            msg_time = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, hour, minute)
            print(f"Parsed yesterday timestamp: {msg_time}")
            return msg_time
            
        # 尝试解析星期格式
        match = re.search(weekday_pattern, msg)
        if match:
            weekday, hour, minute = match.groups()
            # 将中文星期转换为数字（0-6，0表示星期一）
            weekday_map = {
                '星期一': 0, '星期二': 1, '星期三': 2, '星期四': 3,
                '星期五': 4, '星期六': 5, '星期天': 6
            }
            target_weekday = weekday_map[weekday]
            
            # 获取当前日期
            today = datetime.datetime.now()
            current_weekday = today.weekday()
            
            # 计算目标日期
            days_diff = (current_weekday - target_weekday) % 7
            if days_diff == 0:  # 如果是同一天，使用当前日期
                target_date = today
            else:
                target_date = today - datetime.timedelta(days=days_diff)
                
            msg_time = datetime.datetime(target_date.year, target_date.month, target_date.day, 
                                       int(hour), int(minute))
            print(f"Parsed weekday timestamp: {msg_time}")
            return msg_time
            
        # 如果完整日期时间、"昨天"格式和星期格式都解析失败，尝试解析只有时间的情况
        match = re.search(time_pattern, msg)
        if match:
            hour, minute = map(int, match.groups())
            # 使用当前日期
            today = datetime.datetime.now()
            msg_time = datetime.datetime(today.year, today.month, today.day, hour, minute)
            print(f"Parsed time-only: {msg_time}")
            return msg_time
            
        return None
    except Exception as e:
        logging.error(f"Error parsing message time: {str(e)}")
        return None

def find_target_time_point(chat_list, user_input):
    """查找目标时间点"""
    # 根据用户输入确定目标时间
    if user_input['start']:
        # 如果设置了开始时间，使用用户输入的开始时间
        target_time = datetime.datetime.strptime(user_input['start'], "%Y-%m-%d %H:%M:%S")
        logging.info(f"Using user input start time: {target_time}")
    else:
        # 如果没有设置开始时间，使用当前时间
        target_time = datetime.datetime.now()
        logging.info("No start time configured, using current time")
    
    # 如果设置了结束时间，记录日志
    if user_input['end']:
        end_time = datetime.datetime.strptime(user_input['end'], "%Y-%m-%d %H:%M:%S")
        logging.info(f"User input end time: {end_time}")
        
        # 计算时间跨度（小时）
        time_span = end_time - target_time
        hours_span = int(math.ceil(time_span.total_seconds() / 3600) * 1.5)  # 向下取整
        #if hours_span >= 15:
        #    hours_span = 15
        logging.info(f"Time span for scrolling: {hours_span}")
    else:
        hours_span = 3  # 如果没有结束时间，默认1小时
    
    # 获取消息列表的位置
    rect = chat_list.rectangle()
    
    # 在消息列表区域中心点击，确保焦点
    center_x = (rect.left + rect.right) // 2
    center_y = (rect.top + rect.bottom) // 2
    
    # 点击消息列表区域
    move(coords=(center_x, center_y))
    #time.sleep(0.2)
    press(coords=(center_x, center_y))
    #time.sleep(0.1)
    release(coords=(center_x, center_y))
    #time.sleep(0.5)
    
    # 最大尝试次数
    max_attempts = 50  # 可以根据需要调整
    attempt = 0
    
    # 用于存储找到的时间点
    found_times = []
    
    while attempt < max_attempts:
        try:
            # 每 hours_span 次尝试才进行一次消息爬取和时间检查
            if attempt % hours_span == 0:
                # 获取当前可见的消息
                messages = extract_text_content(chat_list)
                print(f"\nAttempt {attempt + 1}: Checking {len(messages)} visible messages")
                
                # 检查每条消息
                for msg in messages:
                    if is_timestamp(msg):
                        msg_time = parse_message_time(msg)
                        if msg_time:
                            print(f"Found timestamp: {msg_time}")
                            # 检查是否找到目标时间点
                            if msg_time <= target_time:
                                print(f"Found message before target time: {msg_time}")
                                logging.info(f"Found message before target time: {msg_time}")
                                found_times.append(msg_time)
                                # 如果找到两个时间点，返回第二个时间点
                                if len(found_times) >= 2:
                                    return found_times[-1]
                            else:
                                # 如果没有找到足够的时间点，继续滚动
                                print(f"Target time not found in visible messages, scrolling up...")
            
            # 获取消息列表的位置
            rect = chat_list.rectangle()
            
            # 在消息列表区域中心点击，确保焦点
            center_x = (rect.left + rect.right) // 2
            center_y = (rect.top + rect.bottom) // 2
            
            # 点击消息列表区域
            move(coords=(center_x, center_y))
            #time.sleep(0.2)
            press(coords=(center_x, center_y))
            #time.sleep(0.1)
            release(coords=(center_x, center_y))
            #time.sleep(0.5)
            
            # 模拟按下 Page Up 键5次
            for i in range(5):
                send_keys('{PGUP}')
                #time.sleep(0.2)  # 每次按键后短暂等待
            
            #time.sleep(0.5)  # 等待页面加载
            
            # 尝试找到并点击"查看更多消息"按钮
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
                logging.error(f"Error finding '查看更多消息' button: {str(e)}")
            
            if more_button:
                print("\nFound '查看更多消息' button, attempting to click...")
                try:
                    # 获取按钮位置
                    button_rect = more_button.rectangle()
                    button_x = (button_rect.left + button_rect.right) // 2
                    button_y = (button_rect.top + button_rect.bottom) // 2
                    
                    # 移动到按钮位置并点击
                    move(coords=(button_x, button_y))
                    #time.sleep(0.2)
                    press(coords=(button_x, button_y))
                    #time.sleep(0.1)
                    release(coords=(button_x, button_y))
                    #time.sleep(1)  # 等待加载更多消息
                except Exception as e:
                    logging.error(f"Error clicking button: {str(e)}")
            
            attempt += 1
            
        except Exception as e:
            logging.error(f"Error during scrolling attempt {attempt + 1}: {str(e)}")
            attempt += 1
    
    # 如果找到至少一个时间点，返回最后一个找到的时间点
    if found_times:
        return found_times[-1]
    
    print("\nReached maximum attempts without finding target time")
    return None

def collect_messages_after_time(chat_list, target_time):
    """收集指定时间之后的所有消息"""
    # 获取当前可见的消息
    messages = extract_text_content(chat_list)
    
    # 过滤消息，只保留目标时间之后的
    filtered_messages = []
    for msg in messages:
        if is_timestamp(msg):
            msg_time = parse_message_time(msg)
            if msg_time:
                # 如果设置了结束时间，检查消息是否在时间范围内
                if msg_time >= target_time:
                    filtered_messages.append(msg)
        else:
            filtered_messages.append(msg)
            
    return filtered_messages

def export_wechat_messages(user_input):
    try:
        logging.info("Connecting to WeChat window...")
        # 使用 UIA 自动化接口连接到微信窗口
        app = Application(backend="uia").connect(class_name=config.WECHAT_WINDOW_CLASS)
        
        # 获取主窗口
        wechat_window = app.window(class_name=config.WECHAT_WINDOW_CLASS)
        
        if not wechat_window.exists():
            raise Exception("WeChat main window not found")
        
        logging.info("Activating WeChat window...")
        # 激活微信窗口
        wechat_window.set_focus()
        time.sleep(0.5)
        
        logging.info("Opening search box...")
        # 使用快捷键 Ctrl+F 打开搜索框
        send_keys('^f')
        time.sleep(0.5)
        
        logging.info(f"Searching for group: {user_input['group']}")
        # 输入群聊名称并搜索，使用 {SPACE} 来正确处理空格
        group_name = user_input['group'].replace(' ', '{SPACE}')
        send_keys(group_name)
        time.sleep(2)
        send_keys('{ENTER}')
        
        logging.info("Getting chat messages...")
        # 尝试定位消息列表控件
        chat_list = None
        
        # 首先尝试通过标题定位
        try:
            chat_list = wechat_window.child_window(title="消息", control_type="List")
            if chat_list.exists():
                logging.info("Found chat list by title")
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
                        logging.info("Found chat list by visibility")
                        break
        
        if not chat_list:
            raise Exception("Could not find chat message list")
            
        # 确保消息列表获得焦点
        try:
            # 获取消息列表的位置
            rect = chat_list.rectangle()
            
            # 在消息列表区域中心点击，确保焦点
            center_x = (rect.left + rect.right) // 2
            center_y = (rect.top + rect.bottom) // 2
            
            # 点击消息列表区域
            move(coords=(center_x, center_y))
            press(coords=(center_x, center_y))
            release(coords=(center_x, center_y))
        except Exception as e:
            logging.error(f"Error setting focus to chat list: {str(e)}")
        
        # 查找目标时间点
        target_time = find_target_time_point(chat_list, user_input)
        if target_time is None:
            raise Exception("Could not find target time point")
            
        # 收集目标时间之后的消息
        messages = collect_messages_after_time(chat_list, target_time)
        
        # 生成文件名（使用当前日期和时间）
        now = datetime.datetime.now()
        start_time_str = datetime.datetime.strptime(user_input['start'], "%Y-%m-%d %H:%M:%S").strftime("%y%m%d%H%M")
        end_time_str = datetime.datetime.strptime(user_input['end'], "%Y-%m-%d %H:%M:%S").strftime("%y%m%d%H%M")
        export_time_str = now.strftime("%y%m%d%H%M")
        filename = f"{user_input['group']}_messages_{start_time_str}-{end_time_str}_{export_time_str}.md"
        filepath = os.path.join(config.EXPORT_PATH, filename)
        
        # 确保目录存在
        os.makedirs(config.EXPORT_PATH, exist_ok=True)
        os.makedirs(config.LOG_PATH, exist_ok=True)
        
        # 去除重复消息
        unique_messages = remove_duplicates(messages)
        
        # 将消息写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {user_input['group']} 聊天记录 - {now.strftime('%Y-%m-%d %H:%M')}\n\n")
            if user_input['start']:
                f.write(f"开始时间: {user_input['start']}\n")
            if user_input['end']:
                f.write(f"结束时间: {user_input['end']}\n")
            f.write(f"导出时间: {now}\n\n")
            for message in unique_messages:
                f.write(f"{message}\n\n")
        
        logging.info(f"Successfully exported {len(unique_messages)} messages to {filepath}")
        
        
    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        logging.error(error_msg)
        raise

class InputWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("微信导出 参数设置")
        self.root.geometry("600x500")  # 增加窗口宽度和高度以适应新功能
        self.root.configure(bg='white')
        
        # 设置窗口置顶
        self.root.attributes('-topmost', True)
        
        # 加载群聊列表
        self.groups_list = config.load_groups_config()
        
        # 获取所有群聊的最新信息
        try:
            self.groups_info = config.get_all_groups_latest_info()
        except Exception as e:
            print(f"Warning: Could not get groups info: {str(e)}")
            self.groups_info = {}
        
        # 群聊名称选择框架
        group_frame = tk.Frame(self.root, bg='white')
        group_frame.pack(pady=10, padx=20, fill=tk.X)
        
        tk.Label(group_frame, text="群聊名称:", bg='white').pack(anchor=tk.W)
        
        # 群聊选择子框架
        group_select_frame = tk.Frame(group_frame, bg='white')
        group_select_frame.pack(fill=tk.X, pady=5)
        
        # 群聊名称下拉菜单
        self.group_name = ttk.Combobox(group_select_frame, width=30, values=self.groups_list)
        self.group_name.pack(side=tk.LEFT, padx=(0, 10))
        self.group_name.set("请选择或输入群聊名称")
        
        # 检查按钮
        self.check_button = ttk.Button(group_select_frame, text="检查", command=self.check_group_info)
        self.check_button.pack(side=tk.LEFT)
        
        # 群聊信息显示框架
        self.info_frame = tk.Frame(group_frame, bg='white')
        self.info_frame.pack(fill=tk.X, pady=5)
        
        # 群聊信息标签
        self.group_info_label = tk.Label(
            self.info_frame, 
            text="", 
            bg='white', 
            fg='blue',
            font=("Arial", 9),
            wraplength=550
        )
        self.group_info_label.pack(anchor=tk.W)
        
        # 绑定下拉菜单选择事件
        self.group_name.bind('<<ComboboxSelected>>', self.on_group_selected)
        
        # 创建时间选择框架
        time_frame = tk.Frame(self.root, bg='white')
        time_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # 开始时间选择
        start_frame = tk.Frame(time_frame, bg='white')
        start_frame.pack(pady=5)
        tk.Label(start_frame, text="开始时间:", bg='white').pack(side=tk.LEFT, padx=5)
        
        # 开始日期选择器
        self.start_date = DateEntry(start_frame, width=12, background='darkblue',
                                  foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date.pack(side=tk.LEFT, padx=5)
        
        # 开始时间选择（小时）
        self.start_hour = ttk.Combobox(start_frame, width=3, values=[f"{i:02d}" for i in range(24)])
        self.start_hour.set("00")
        self.start_hour.pack(side=tk.LEFT, padx=2)
        tk.Label(start_frame, text=":", bg='white').pack(side=tk.LEFT)
        
        # 开始时间选择（分钟）
        self.start_minute = ttk.Combobox(start_frame, width=3, values=[f"{i:02d}" for i in range(60)])
        self.start_minute.set("00")
        self.start_minute.pack(side=tk.LEFT, padx=2)
        
        # 结束时间选择
        end_frame = tk.Frame(time_frame, bg='white')
        end_frame.pack(pady=5)
        tk.Label(end_frame, text="结束时间:", bg='white').pack(side=tk.LEFT, padx=5)
        
        # 结束日期选择器
        self.end_date = DateEntry(end_frame, width=12, background='darkblue',
                                foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date.pack(side=tk.LEFT, padx=5)
        
        # 结束时间选择（小时）
        self.end_hour = ttk.Combobox(end_frame, width=3, values=[f"{i:02d}" for i in range(24)])
        self.end_hour.set("23")
        self.end_hour.pack(side=tk.LEFT, padx=2)
        tk.Label(end_frame, text=":", bg='white').pack(side=tk.LEFT)
        
        # 结束时间选择（分钟）
        self.end_minute = ttk.Combobox(end_frame, width=3, values=[f"{i:02d}" for i in range(60)])
        self.end_minute.set("59")
        self.end_minute.pack(side=tk.LEFT, padx=2)
        
        # 快捷时间范围按钮框架
        quick_time_frame = tk.Frame(self.root, bg='white')
        quick_time_frame.pack(pady=10, padx=20)
        
        # 添加快捷时间范围按钮
        ttk.Button(quick_time_frame, text="最近8小时", 
                  command=lambda: self.set_quick_time_range(8)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_time_frame, text="最近1天", 
                  command=lambda: self.set_quick_time_range(24)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_time_frame, text="最近1周", 
                  command=lambda: self.set_quick_time_range(24*7)).pack(side=tk.LEFT, padx=5)
        
        # 确认按钮
        self.confirm_button = tk.Button(
            self.root,
            text="开始导出",
            command=self.confirm,
            width=20,
            height=2
        )
        self.confirm_button.pack(pady=20)
        
        # 存储用户输入
        self.user_input = None
        
    def add_group_to_list(self, group_name):
        """添加新群聊到下拉列表"""
        try:
            # 添加到配置文件
            if config.add_group_to_config(group_name):
                # 重新加载群聊列表
                self.groups_list = config.load_groups_config()
                # 更新下拉菜单
                self.group_name['values'] = self.groups_list
                print(f"已添加新群聊到下拉列表: {group_name}")
                
                # 显示成功信息
                messagebox.showinfo("成功", f"已将群聊 '{group_name}' 添加到下拉列表中")
        except Exception as e:
            print(f"添加群聊到列表时出错: {str(e)}")
            messagebox.showerror("错误", f"添加群聊失败: {str(e)}")
        
    def on_group_selected(self, event):
        """当下拉菜单选择群聊时触发"""
        selected_group = self.group_name.get()
        if selected_group and selected_group != "请选择或输入群聊名称":
            self.update_group_info_display(selected_group)
    
    def check_group_info(self):
        """检查按钮点击事件"""
        group_name = self.group_name.get().strip()
        if group_name and group_name != "请选择或输入群聊名称":
            # 重新获取群聊信息（以防新的导出文件）
            try:
                self.groups_info = config.get_all_groups_latest_info()
            except Exception as e:
                print(f"Warning: Could not get groups info: {str(e)}")
                
            self.update_group_info_display(group_name)
        else:
            messagebox.showwarning("警告", "请先输入或选择群聊名称")
    
    def update_group_info_display(self, group_name):
        """更新群聊信息显示"""
        if not self.groups_info:
            self.group_info_label.config(text="无法获取群聊信息", fg='red')
            return
            
        info = self.groups_info.get(group_name)
        
        if info:
            info_text = f"最新获取记录: {info['start_time']} 至 {info['end_time']} (导出时间: {info['export_time']})"
            self.group_info_label.config(text=info_text, fg='green')
            
            # 检查是否需要添加到下拉菜单
            if group_name not in self.groups_list:
                self.add_group_to_list(group_name)
        else:
            self.group_info_label.config(text="暂无获取记录", fg='red')
        
    def set_quick_time_range(self, hours):
        """设置快捷时间范围"""
        # 获取当前时间
        now = datetime.datetime.now()
        # 结束时间设置为当前时间减去2小时
        end_time = now - datetime.timedelta(hours=2)
        # 开始时间设置为结束时间减去指定小时数
        start_time = end_time - datetime.timedelta(hours=hours)
        
        # 设置开始时间
        self.start_date.set_date(start_time.date())
        self.start_hour.set(f"{start_time.hour:02d}")
        self.start_minute.set(f"{start_time.minute:02d}")
        
        # 设置结束时间
        self.end_date.set_date(end_time.date())
        self.end_hour.set(f"{end_time.hour:02d}")
        self.end_minute.set(f"{end_time.minute:02d}")
        
    def get_datetime_string(self, date_entry, hour, minute):
        """将日期和时间组合成datetime字符串"""
        date = date_entry.get_date()
        return f"{date.strftime('%Y-%m-%d')} {hour}:{minute}:00"
        
    def confirm(self):
        group = self.group_name.get().strip()
        
        # 验证输入
        if not group or group == "请选择或输入群聊名称":
            messagebox.showerror("错误", "请选择或输入群聊名称")
            return
            
        # 获取开始和结束时间
        start = self.get_datetime_string(self.start_date, self.start_hour.get(), self.start_minute.get())
        end = self.get_datetime_string(self.end_date, self.end_hour.get(), self.end_minute.get())
        
        # 验证时间
        try:
            start_dt = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
            
            if end_dt <= start_dt:
                messagebox.showerror("错误", "结束时间必须晚于开始时间")
                return
                
        except ValueError as e:
            messagebox.showerror("错误", f"时间格式错误: {str(e)}")
            return
            
        # 存储用户输入
        self.user_input = {
            'group': group,
            'start': start,
            'end': end
        }
        
        # 关闭窗口
        self.root.destroy()
        
    def show(self):
        self.root.mainloop()
        return self.user_input

class ProgressWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("微信导出 执行进度")
        self.root.geometry("400x200")
        
        # 设置窗口样式
        self.root.configure(bg='white')
        
        # 创建进度条
        self.progress = ttk.Progressbar(
            self.root, 
            orient="horizontal",
            length=300,
            mode="determinate"
        )
        self.progress.pack(pady=20)
        
        # 创建状态标签
        self.status_label = tk.Label(
            self.root,
            text="正在初始化...",
            font=("Arial", 12),
            bg='white'
        )
        self.status_label.pack(pady=10)
        
        # 创建详细信息标签
        self.detail_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 10),
            bg='white',
            wraplength=380
        )
        self.detail_label.pack(pady=10)
        
        # 设置窗口置顶
        self.root.attributes('-topmost', True)
        
    def update_progress(self, value, status, detail=""):
        self.progress['value'] = value
        self.status_label['text'] = status
        self.detail_label['text'] = detail
        self.root.update()
        
    def show(self):
        self.root.mainloop()
        
    def close(self):
        self.root.destroy()

# 创建全局进度窗口实例
progress_window = None

def update_progress(value, status, detail=""):
    if progress_window:
        progress_window.update_progress(value, status, detail)

def main():
    global progress_window
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 处理协议调用
        if sys.argv[1].startswith("mydaily://"):
            url = sys.argv[1]
            try:
                # 解析URL参数
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                
                # 获取参数
                group = params.get('group', [''])[0]
                start = params.get('startTime', [''])[0]
                end = params.get('endTime', [''])[0]
                
                # 验证参数
                if not group:
                    raise ValueError("群聊名称不能为空")
                
                # 创建用户输入对象
                user_input = {
                    'group': group,
                    'start': start,
                    'end': end
                }
                
                # 创建并显示进度窗口
                progress_window = ProgressWindow()
                
                # 在新线程中运行主程序
                def run_program():
                    try:
                        # 确保导出目录存在
                        os.makedirs(config.EXPORT_PATH, exist_ok=True)
                        
                        # 设置日志
                        logger = setup_logging()
                        
                        update_progress(10, "正在初始化...", "准备开始导出消息")
                        
                        try:
                            logger.info("Starting WeChat Exporter...")
                            update_progress(20, "正在连接微信...", f"准备导出群聊 '{user_input['group']}' 的消息")
                            
                            logger.info(f"Will export messages from group '{user_input['group']}'")
                            if user_input['start']:
                                logger.info(f"Start time: {user_input['start']}")
                                update_progress(30, "正在连接微信...", f"开始时间: {user_input['start']}")
                            if user_input['end']:
                                logger.info(f"End time: {user_input['end']}")
                                update_progress(30, "正在连接微信...", f"结束时间: {user_input['end']}")
                            
                            # 立即执行导出
                            update_progress(40, "正在导出消息...", "请确保微信窗口已打开")
                            export_wechat_messages(user_input)
                            
                            update_progress(100, "导出完成", "消息已成功导出")
                            time.sleep(2)  # 显示完成状态2秒
                            
                        except Exception as e:
                            error_msg = f"导出失败: {str(e)}"
                            logger.error(error_msg)
                            update_progress(0, "导出失败", error_msg)
                            time.sleep(5)  # 显示错误状态5秒
                            raise
                            
                    finally:
                        # 关闭进度窗口
                        if progress_window:
                            progress_window.close()
                
                # 启动程序线程
                program_thread = threading.Thread(target=run_program)
                program_thread.start()
                
                # 显示进度窗口
                progress_window.show()
                
            except Exception as e:
                # 显示错误消息框
                tk.messagebox.showerror("错误", str(e))
                return
    else:
        # 显示输入窗口
        input_window = InputWindow()
        user_input = input_window.show()
        
        if not user_input:
            return  # 用户取消输入
        
        # 创建并显示进度窗口
        progress_window = ProgressWindow()
        
        # 在新线程中运行主程序
        def run_program():
            try:
                # 确保导出目录存在
                os.makedirs(config.EXPORT_PATH, exist_ok=True)
                
                # 设置日志
                logger = setup_logging()
                
                update_progress(10, "正在初始化...", "准备开始导出消息")
                
                try:
                    logger.info("Starting WeChat Exporter...")
                    update_progress(20, "正在连接微信...", f"准备导出群聊 '{user_input['group']}' 的消息")
                    
                    logger.info(f"Will export messages from group '{user_input['group']}'")
                    if user_input['start']:
                        logger.info(f"Start time: {user_input['start']}")
                        update_progress(30, "正在连接微信...", f"开始时间: {user_input['start']}")
                    if user_input['end']:
                        logger.info(f"End time: {user_input['end']}")
                        update_progress(30, "正在连接微信...", f"结束时间: {user_input['end']}")
                    
                    # 立即执行导出
                    update_progress(40, "正在导出消息...", "请确保微信窗口已打开")
                    export_wechat_messages(user_input)
                    
                    update_progress(100, "导出完成", "消息已成功导出")
                    time.sleep(2)  # 显示完成状态2秒
                    
                except Exception as e:
                    error_msg = f"导出失败: {str(e)}"
                    logger.error(error_msg)
                    update_progress(0, "导出失败", error_msg)
                    time.sleep(5)  # 显示错误状态5秒
                    raise
                    
            finally:
                # 关闭进度窗口
                if progress_window:
                    progress_window.close()
        
        # 启动程序线程
        program_thread = threading.Thread(target=run_program)
        program_thread.start()
        
        # 显示进度窗口
        progress_window.show()

    print("sys.executable:", sys.executable)
    print("BASE_DIR:", config.BASE_DIR)
    print("EXPORT_PATH:", config.EXPORT_PATH)

if __name__ == "__main__":
    main() 