# WeChat Message Exporter

一个用于导出微信聊天记录到 Markdown 文件的工具。

## 功能特点

- 自动导出指定群聊的聊天记录
- 支持自定义时间范围导出
- 自动去除重复消息
- 支持导出图片、语音等多媒体消息

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

在项目根目录创建 `.env` 文件，配置以下参数：

```env
# 目标群聊名称
TARGET_GROUP=嗨小宝贝儿

# 导出文件保存路径
EXPORT_PATH=exports

# 日志文件保存路径
LOG_PATH=logs

# 消息时间范围配置
# 时间格式：YYYY-MM-DD HH:MM:SS
START_TIME=2025-04-17 15:30:00
END_TIME=2025-04-17 16:30:00
```

### 时间范围配置说明

时间范围通过 `START_TIME` 和 `END_TIME` 配置：
- 格式：`YYYY-MM-DD HH:MM:SS`
- 示例：
  ```
  START_TIME=2025-04-17 15:30:00
  END_TIME=2025-04-17 16:30:00
  ```
- 注意：
  - `START_TIME` 和 `END_TIME` 可以只设置一个
  - 时间格式必须严格遵循 `YYYY-MM-DD HH:MM:SS`
  - 月份、日期、小时、分钟、秒数如果是个位数，前面要补0
  - 如果都不设置，则导出所有可见消息

## 使用方法

1. 确保微信 PC 客户端已登录并打开
2. 运行程序：
   ```bash
   python wechat_exporter.py
   ```
3. 程序会自动：
   - 查找并激活目标群聊
   - 导出消息到 Markdown 文件
   - 文件命名格式：`群名_messages_YYYY-MM-DD_HH-MM.md`

## 输出文件说明

导出的 Markdown 文件包含：
- 群聊名称
- 导出时间
- 配置的时间范围（如果设置了）
- 聊天记录内容

## 注意事项

1. 确保微信窗口处于可见状态
2. 导出过程中不要操作微信窗口
3. 如果遇到问题，查看 logs 目录下的日志文件
4. 建议先使用小范围时间测试，确认无误后再导出大量消息

## 常见问题

1. 找不到微信窗口
   - 确保微信已登录并窗口可见
   - 检查 WECHAT_WINDOW_CLASS 配置是否正确

2. 时间范围配置无效
   - 检查时间格式是否正确
   - 确保使用24小时制
   - 检查月份、日期、时间是否补零 