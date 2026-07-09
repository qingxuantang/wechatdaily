import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取程序当前所在目录（兼容PyInstaller打包和源码运行）
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 微信窗口配置
WECHAT_WINDOW_TITLE = "微信"
try:
    WECHAT_WINDOW_CLASS = "WeChatMainWndForPC" #微信3.9.12及以前版本
except:
    WECHAT_WINDOW_CLASS = "mmui::MainWindow"

# 目标群聊名称
TARGET_GROUP = os.getenv("TARGET_GROUP", "My Group")

# 导出文件保存路径（始终为程序所在目录下的exports文件夹）
EXPORT_PATH = os.path.join(BASE_DIR, "exports")

# 日志文件保存路径（始终为程序所在目录下的logs文件夹）
LOG_PATH = os.path.join(BASE_DIR, "logs")

# 消息时间范围配置
# 时间格式：YYYY-MM-DD HH:MM:SS 日期和时间中间有一个空格
START_TIME = os.getenv("START_TIME", "2025-05-07 08:00:00")  # 空字符串表示不限制开始时间
END_TIME = os.getenv("END_TIME", "2025-05-07 13:31:00")      # 空字符串表示不限制结束时间

# 结构导出配置
MAX_SCROLL_ATTEMPTS = int(os.getenv("MAX_SCROLL_ATTEMPTS", "50"))  # 最大滚动次数
SCROLL_WAIT_TIME = float(os.getenv("SCROLL_WAIT_TIME", "0.5"))      # 每次滚动后的等待时间（秒）

# 确保导出目录和日志目录存在
os.makedirs(EXPORT_PATH, exist_ok=True)
os.makedirs(LOG_PATH, exist_ok=True)

# 群聊配置文件路径
GROUPS_CONFIG_FILE = os.path.join(BASE_DIR, "groups_config.json")

def get_latest_export_info(group_name):
    """
    获取指定群聊的最新导出信息
    
    Args:
        group_name (str): 群聊名称
        
    Returns:
        dict: 包含最新导出信息的字典，如果没有记录则返回None
    """
    import glob
    import re
    from datetime import datetime
    
    # 检查本地exports目录
    local_pattern = os.path.join(EXPORT_PATH, f"{group_name}_messages_*.md")
    local_files = glob.glob(local_pattern)
    
    all_files = local_files
    
    if not all_files:
        return None
    
    # 解析文件名获取时间信息
    latest_info = None
    latest_export_time = None
    
    for file_path in all_files:
        filename = os.path.basename(file_path)
        # 文件名格式: 群名_messages_开始时间-结束时间_导出时间.md
        # 例如: GroupName_messages_2505151034-2505161839_2505161852.md
        
        # 提取导出时间（最后一个下划线后的部分）
        parts = filename.split('_')
        if len(parts) >= 4:
            export_time_str = parts[-1].replace('.md', '')
            
            try:
                # 解析导出时间 (格式: yymmddHHMM)
                export_time = datetime.strptime(export_time_str, '%y%m%d%H%M')
                
                if latest_export_time is None or export_time > latest_export_time:
                    latest_export_time = export_time
                    
                    # 提取开始和结束时间
                    time_range = parts[-2]  # 例如: 2505151034-2505161839
                    start_end = time_range.split('-')
                    
                    if len(start_end) == 2:
                        start_str, end_str = start_end
                        
                        # 解析开始时间
                        start_time = datetime.strptime(start_str, '%y%m%d%H%M')
                        # 解析结束时间
                        end_time = datetime.strptime(end_str, '%y%m%d%H%M')
                        
                        latest_info = {
                            'start_time': start_time.strftime('%Y-%m-%d %H:%M'),
                            'end_time': end_time.strftime('%Y-%m-%d %H:%M'),
                            'export_time': export_time.strftime('%Y-%m-%d %H:%M'),
                            'file_path': file_path
                        }
                        
            except ValueError:
                continue
    
    return latest_info

def load_groups_config():
    """
    从配置文件加载群聊列表
    
    Returns:
        list: 群聊名称列表
    """
    import json
    
    # 默认预设群聊
    default_groups = [
        "Group A",
        "Group B"
    ]
    
    try:
        if os.path.exists(GROUPS_CONFIG_FILE):
            with open(GROUPS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                saved_groups = config_data.get('groups', [])
                # 合并默认群聊和保存的群聊，去除重复
                all_groups = list(set(default_groups + saved_groups))
                return sorted(all_groups)  # 按字母顺序排序
        else:
            return default_groups
    except Exception as e:
        print(f"Error loading groups config: {str(e)}")
        return default_groups

def save_groups_config(groups):
    """
    保存群聊列表到配置文件
    
    Args:
        groups (list): 群聊名称列表
    """
    import json
    
    try:
        config_data = {
            'groups': sorted(list(set(groups)))  # 去重并排序
        }
        with open(GROUPS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        print(f"Groups config saved: {len(config_data['groups'])} groups")
    except Exception as e:
        print(f"Error saving groups config: {str(e)}")

def add_group_to_config(group_name):
    """
    添加新群聊到配置文件
    
    Args:
        group_name (str): 群聊名称
    
    Returns:
        bool: 是否成功添加
    """
    if not group_name or group_name.strip() == "":
        return False
        
    current_groups = load_groups_config()
    group_name = group_name.strip()
    
    if group_name not in current_groups:
        current_groups.append(group_name)
        save_groups_config(current_groups)
        print(f"Added new group to config: {group_name}")
        return True
    return False

def get_all_groups_latest_info():
    """
    获取所有群聊的最新导出信息
    
    Returns:
        dict: 群聊名称到最新导出信息的映射
    """
    import glob
    
    # 从配置文件加载群聊列表
    config_groups = load_groups_config()
    
    groups_info = {}
    
    # 检查本地exports目录
    local_pattern = os.path.join(EXPORT_PATH, "*_messages_*.md")
    local_files = glob.glob(local_pattern)
    
    # 从文件名中提取群聊名称
    found_groups = set()
    for file_path in local_files:
        filename = os.path.basename(file_path)
        parts = filename.split('_messages_')
        if len(parts) == 2:
            group_name = parts[0]
            found_groups.add(group_name)
    
    # 合并配置中的群聊和发现的群聊
    all_groups = list(set(config_groups + list(found_groups)))
    
    # 如果发现了新的群聊，更新配置文件
    if found_groups - set(config_groups):
        save_groups_config(all_groups)
    
    # 获取每个群聊的最新信息
    for group in all_groups:
        info = get_latest_export_info(group)
        groups_info[group] = info
    
    return groups_info 