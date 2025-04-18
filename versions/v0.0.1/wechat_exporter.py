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

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 设置为DEBUG级别以显示所有日志
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_PATH, 'wechat_exporter.log')),
        logging.StreamHandler()
    ]
)

class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.console = sys.stdout
        self.log = open(log_file, 'w', encoding='utf-8')
        
    def write(self, message):
        self.console.write(message)
        self.log.write(message)
        self.log.flush()
        
    def close(self):
        self.log.close()

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
    
    return bool(re.match(full_pattern, text) or re.match(time_pattern, text))

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
        
        # 先尝试解析完整日期时间
        match = re.search(full_pattern, msg)
        if match:
            year, month, day, hour, minute = map(int, match.groups())
            msg_time = datetime.datetime(year, month, day, hour, minute)
            print(f"Parsed full timestamp: {msg_time}")
            return msg_time
            
        # 如果完整日期时间解析失败，尝试解析只有时间的情况
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

def find_target_time_point(chat_list):
    """查找目标时间点"""
    target_time = datetime.datetime.now() - datetime.timedelta(hours=config.MESSAGE_TIME_RANGE)
    logging.info(f"Target time: {target_time}")
    
    # 获取当前可见的消息
    messages = extract_text_content(chat_list)
    print("\nAll visible messages:")
    for msg in messages:
        print(f"Message: '{msg}'")
        if is_timestamp(msg):
            print(f"  This is a timestamp!")
            msg_time = parse_message_time(msg)
            if msg_time:
                print(f"  Parsed time: {msg_time}")
                # 如果是今天的时间，只比较时分
                if msg_time.date() == datetime.datetime.now().date():
                    target_hour = target_time.hour
                    target_minute = target_time.minute
                    msg_hour = msg_time.hour
                    msg_minute = msg_time.minute
                    
                    # 转换为分钟数进行比较
                    target_minutes = target_hour * 60 + target_minute
                    msg_minutes = msg_hour * 60 + msg_minute
                    
                    print(f"  Today's message comparison:")
                    print(f"  Target minutes: {target_minutes} ({target_hour}:{target_minute})")
                    print(f"  Message minutes: {msg_minutes} ({msg_hour}:{msg_minute})")
                    
                    if msg_minutes <= target_minutes:
                        print(f"Found first message before target time: {msg_time}")
                        logging.info(f"Found first message before target time: {msg_time}")
                        return msg_time
                    else:
                        print(f"Message time {msg_time} is not before target time {target_time}")
                else:
                    # 如果不是今天的消息，直接比较完整时间
                    if msg_time <= target_time:
                        print(f"Found first message before target time: {msg_time}")
                        logging.info(f"Found first message before target time: {msg_time}")
                        return msg_time
                    else:
                        print(f"Message time {msg_time} is not before target time {target_time}")
            else:
                print(f"  Failed to parse time from: {msg}")
        else:
            print(f"  Not a timestamp")
    
    print("\nNo messages found before target time in visible area")
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
            if msg_time and msg_time >= target_time:
                filtered_messages.append(msg)
        else:
            filtered_messages.append(msg)
            
    return filtered_messages

def export_wechat_messages():
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
        time.sleep(2)
        
        logging.info("Opening search box...")
        # 使用快捷键 Ctrl+F 打开搜索框
        send_keys('^f')
        time.sleep(2)
        
        logging.info(f"Searching for group: {config.TARGET_GROUP}")
        # 输入群聊名称并搜索
        send_keys(config.TARGET_GROUP)
        time.sleep(2)
        send_keys('{ENTER}')
        time.sleep(3)
        
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
            chat_list.set_focus()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error setting focus to chat list: {str(e)}")
        
        # 查找目标时间点
        target_time = find_target_time_point(chat_list)
        if target_time is None:
            raise Exception("Could not find target time point")
            
        # 收集目标时间之后的消息
        messages = collect_messages_after_time(chat_list, target_time)
        
        # 生成文件名（使用当前日期和时间）
        now = datetime.datetime.now()
        filename = f"{config.TARGET_GROUP}_messages_{now.strftime('%Y-%m-%d_%H-%M')}.md"
        filepath = os.path.join(config.EXPORT_PATH, filename)
        
        # 确保目录存在
        os.makedirs(config.EXPORT_PATH, exist_ok=True)
        os.makedirs(config.LOG_PATH, exist_ok=True)
        
        # 去除重复消息
        unique_messages = remove_duplicates(messages)
        
        # 将消息写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {config.TARGET_GROUP} 聊天记录 - {now.strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"时间范围: {target_time} 至 {now}\n\n")
            for message in unique_messages:
                f.write(f"{message}\n\n")
        
        logging.info(f"Successfully exported {len(unique_messages)} messages to {filepath}")
        
    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        logging.error(error_msg)
        raise

def main():
    # 确保导出目录和日志目录存在
    os.makedirs(config.EXPORT_PATH, exist_ok=True)
    os.makedirs(config.LOG_PATH, exist_ok=True)
    
    # 设置日志文件
    log_filename = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(config.LOG_PATH, log_filename)
    logger = Logger(log_path)
    sys.stdout = logger
    
    try:
        print("Starting WeChat Message Exporter...")
        print(f"Will export messages from group '{config.TARGET_GROUP}'")
        print(f"Message time range: last {config.MESSAGE_TIME_RANGE} hours")
        
        # 立即执行导出
        export_wechat_messages()
        
    except Exception as e:
        print(f"Export failed: {str(e)}")
    finally:
        # 恢复标准输出并关闭日志文件
        sys.stdout = logger.console
        logger.close()

if __name__ == "__main__":
    main() 