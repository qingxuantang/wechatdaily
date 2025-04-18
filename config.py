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

# 消息时间范围配置
# 时间格式：YYYY-MM-DD HH:MM:SS 日期和时间中间有一个空格
START_TIME = os.getenv("START_TIME", "2025-04-17 22:30:00")  # 空字符串表示不限制开始时间
END_TIME = os.getenv("END_TIME", "2025-04-18 19:00:00")      # 空字符串表示不限制结束时间

# 结构导出配置
MAX_SCROLL_ATTEMPTS = int(os.getenv("MAX_SCROLL_ATTEMPTS", "1"))  # 最大滚动次数
SCROLL_WAIT_TIME = float(os.getenv("SCROLL_WAIT_TIME", "0.5"))      # 每次滚动后的等待时间（秒）

# 确保导出目录和日志目录存在
os.makedirs(EXPORT_PATH, exist_ok=True)
os.makedirs(LOG_PATH, exist_ok=True) 