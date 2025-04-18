import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 微信窗口配置
WECHAT_WINDOW_TITLE = "微信"
WECHAT_WINDOW_CLASS = "WeChatMainWndForPC"

# 目标群聊名称
TARGET_GROUP = os.getenv("TARGET_GROUP", "A旗舰船队")

# 导出文件保存路径
EXPORT_PATH = os.getenv("EXPORT_PATH", "exports")

# 日志文件保存路径
LOG_PATH = os.getenv("LOG_PATH", "logs")

# 导出时间设置（24小时制）
EXPORT_TIME = os.getenv("EXPORT_TIME", "23:00")

# 消息获取时间范围（单位：小时）
MESSAGE_TIME_RANGE = int(os.getenv("MESSAGE_TIME_RANGE", "14"))

# 确保导出目录和日志目录存在
os.makedirs(EXPORT_PATH, exist_ok=True)
os.makedirs(LOG_PATH, exist_ok=True) 