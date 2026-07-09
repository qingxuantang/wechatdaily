# WeChat Daily Exporter

导出 Windows 版微信里指定群聊 / 联系人在某个时间段内的聊天记录到 Markdown 文件，用于生成摘要、导图、Q&A 等。

在经典逐条滚动导出之外，本项目提供了一个**快速滚动**导出器（`fast_export.py`）：用鼠标滚轮批量上滚 + 只读列表顶部判断加载进度，大群导出速度远快于逐条 PageUp 方案。

## 功能特点

- 导出指定群聊 / 联系人的聊天记录到 Markdown
- 自定义时间范围；不给开始时间时自动“接上次导出结束时间”继续导
- 自动去重
- 两种用法：图形界面（`wechat_exporter.py`）与命令行快速导出（`fast_export.py`）
- 安全校验：打开的聊天标题与目标不符会立刻中止，绝不抓取其它聊天

## 运行环境

- Windows + 微信 PC 版 **3.9.12.x**（窗口类 `WeChatMainWndForPC`）。请勿升级微信，高版本 UI 结构变化会导致失效。
- Python 3.11
- 普通权限即可，无需管理员 / UAC。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并按需修改：

```env
TARGET_GROUP=My Group          # 目标群聊名称（也可运行时 --group 指定）
EXPORT_PATH=exports            # 导出文件目录
LOG_PATH=logs                 # 日志目录
START_TIME=                   # 留空表示不限制；格式 YYYY-MM-DD HH:MM:SS
END_TIME=
MAX_SCROLL_ATTEMPTS=50
SCROLL_WAIT_TIME=0.5
```

群聊列表可复制 `groups_config.example.json` 为 `groups_config.json` 自行维护（该文件已被 `.gitignore` 忽略，不会进版本库）。

## 用法

### 1) 图形界面

```bash
python wechat_exporter.py
```

按窗口提示选择群聊、时间范围后导出。

### 2) 命令行快速导出（推荐用于大群）

```bash
# 指定时间范围
python fast_export.py --group "My Group" --start "2025-05-30 13:00:00" --end "2025-05-30 18:00:00"

# 不给 --end 时默认导到「现在 - 2 小时」
python fast_export.py --group "My Group" --start "2025-05-30 13:00:00"

# 不给 --start 时自动接上该群上次导出的结束时间（本地 exports 目录里）
python fast_export.py --group "My Group"

# 只查询该群上次导出到哪，不实际导出
python fast_export.py --group "My Group" --show-last
```

运行时请**保持微信在前台、不要动鼠标键盘**——脚本会接管几下按键/滚轮把群聊搜出来并滚动加载历史。

## 工作原理（快速导出器）

- **自动搜进群聊**：`Ctrl+F` 打开搜索 → 用 `send_keys` 逐字符发送中文群名（基于 `KEYEVENTF_UNICODE`，不依赖输入法）→ 回车进入第一个结果。若目标聊天已在前台则跳过导航。
- **只用鼠标滚轮上滚**：实测滚轮加载历史有效且快（约 3 聊天小时/秒），PageUp 基本加载不动。
- **只读列表顶部判断进度**：每轮只读消息列表最前约 12 项找最早时间（O(1)，约 45ms），不做全树遍历，几千条的大群也不卡。
- **到顶自动停**：连续多轮无进展且已无“查看更多消息”按钮时判定到顶，提前结束。

## 安全说明

- 打开的聊天顶部标题必须包含目标名称，否则立即中止，不做任何抓取。
- 导出结果仅写入本地 `exports/` 目录。本开源版**不包含任何上传 / 外发功能**。

## License

见 [LICENSE](LICENSE)。
