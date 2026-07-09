# -*- coding: utf-8 -*-
"""
wechat-export 技能 worker（Windows，普通权限即可——中文群名用 pywinauto send_keys 逐字符发，无需提权/UAC）。

职责：
  1) 在微信里 Ctrl+F 搜到目标群聊并进入（提权后中文注入才稳）；
  2) 校验顶部标题确实是目标聊天，否则立刻中止——绝不碰别的聊天；
  3) 快速向上滚动，把 起始时间→结束时间 的历史消息全部加载进 UIA 树
     （微信会把已加载消息保留在树里，即使滚出屏幕）；
  4) 复用 mydaily 的函数 collect_messages_after_time / remove_duplicates
     抽取去重，按命名写 .md。

用法：
  py -3.11 fast_export.py --group "My Group" --start "2025-05-30 13:00:00" [--end "..."]
  --end 省略时默认 = 现在 - 2 小时。
"""
import sys, os, time, argparse, datetime, glob
import tkinter as tk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ---- 把所有输出 tee 到日志文件 ----
LOG_PATH = os.path.join(BASE_DIR, "logs", "fast_export.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
_LOG = open(LOG_PATH, "w", encoding="utf-8")
class _Tee:
    def __init__(self, *fs): self.fs = fs
    def write(self, s):
        for f in self.fs:
            try: f.write(s); f.flush()
            except Exception: pass
    def flush(self):
        for f in self.fs:
            try: f.flush()
            except Exception: pass
sys.stdout = _Tee(sys.__stdout__, _LOG)
sys.stderr = _Tee(sys.__stderr__, _LOG)
import logging
logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)

import wechat_exporter as MyDaily, config
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
import pywinauto.mouse as M
from pywinauto.uia_defines import IUIA
RAW = IUIA().iuia.RawViewWalker  # 用于"只读顶部"判断最早时间（O(1)，比全树读快~40倍）

def log(*a):
    print(*a, flush=True)

def _escape_send_keys(text):
    # pywinauto send_keys 把 ^ % + ~ ( ) { } [ ] 当控制字符，需用 {} 包成字面量；空格转 {SPACE}。
    # mydaily 只做了 ' '->'{SPACE}'（群名无特殊字符故够用），这里是其超集，更稳。
    special = set('^%+~(){}[]')
    out = []
    for ch in text:
        if ch == ' ':
            out.append('{SPACE}')
        elif ch in special:
            out.append('{' + ch + '}')
        else:
            out.append(ch)
    return ''.join(out)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True)
    ap.add_argument("--start", default="", help='"YYYY-MM-DD HH:MM:SS"；不给则接上该群上次导出的结束时间')
    ap.add_argument("--end", default="")
    ap.add_argument("--max-scroll", type=int, default=2000)  # 活跃大群可能需要上千轮；到顶会自动提前停
    ap.add_argument("--check-every", type=int, default=4)
    ap.add_argument("--show-last", action="store_true",
                    help="只查询该群上次导出信息并退出（不连微信、不滚动、不导出）")
    return ap.parse_args()

def read_open_title(win, mleft):
    """读取当前打开聊天的顶部标题（消息区上方的 Text）。"""
    for el in win.descendants(control_type="Text"):
        try:
            r = el.rectangle(); nm = el.window_text()
        except Exception:
            continue
        if nm and r.top < 60 and (mleft - 40) <= r.left <= (mleft + 600):
            return nm
    return ""

def get_msg_list(win):
    for lst in win.descendants(control_type="List"):
        try:
            if lst.window_text() == "消息":
                return lst
        except Exception:
            pass
    return None

# 衔接"上次导出"扫描的目录：本地 exports。
EXPORT_DIRS = [config.EXPORT_PATH]

def latest_export_end(group, dirs):
    """跨多个 exports 目录，找该群所有导出文件里**最大的结束时间**。
    文件名格式：{群}_messages_{start}-{end}_{exporttime}.md（时间均为 %y%m%d%H%M）。
    返回 (end_datetime 或 None, 来源文件路径 或 None)。"""
    best_end, best_file = None, None
    for d in dirs:
        try:
            if not os.path.isdir(d):
                continue
            for fp in glob.glob(os.path.join(d, f"{group}_messages_*.md")):
                parts = os.path.basename(fp).split('_')
                if len(parts) < 4:
                    continue
                rng = parts[-2].split('-')   # "{start}-{end}"
                if len(rng) != 2:
                    continue
                try:
                    end_dt = datetime.datetime.strptime(rng[1], '%y%m%d%H%M')
                except ValueError:
                    continue
                if best_end is None or end_dt > best_end:
                    best_end, best_file = end_dt, fp
        except Exception:
            continue
    return best_end, best_file

def cheap_oldest(chat_list, n_items=12):
    """只读列表最前面 n_items 项的近邻文本，找最早时间。O(1) 不随总量增长，
    实测 ~45ms（全树读 ~2000ms）。已加载的更早消息排在列表最前面。"""
    el = chat_list.element_info.element
    child = RAW.GetFirstChildElement(el)
    texts, count = [], 0
    while child and count < n_items:
        try:
            nm = child.CurrentName
            if nm: texts.append(nm)
        except Exception: pass
        sub = RAW.GetFirstChildElement(child)
        while sub:
            try:
                sn = sub.CurrentName
                if sn: texts.append(sn)
            except Exception: pass
            sub = RAW.GetNextSiblingElement(sub)
        child = RAW.GetNextSiblingElement(child); count += 1
    oldest = None
    for t in texts:
        if MyDaily.is_timestamp(t):
            d = MyDaily.parse_message_time(t)
            if d and (oldest is None or d < oldest):
                oldest = d
    return oldest

def click_load_more(chat_list):
    """点列表顶部的“查看更多消息”按钮触发加载更早一批。
    用 RAW walker 只看最前几项 → O(1)，大群(几千条)也不卡（旧版 children() 是 O(n)，是大群变慢主因）。"""
    try:
        el = chat_list.element_info.element
        child = RAW.GetFirstChildElement(el); c = 0
        while child and c < 5:
            try:
                if child.CurrentName == "查看更多消息":
                    r = child.CurrentBoundingRectangle  # RECT: left/top/right/bottom
                    bx = (r.left + r.right) // 2; by = (r.top + r.bottom) // 2
                    M.move(coords=(bx, by)); M.press(coords=(bx, by)); M.release(coords=(bx, by))
                    return True
            except Exception:
                pass
            child = RAW.GetNextSiblingElement(child); c += 1
    except Exception:
        pass
    return False

def main():
    args = parse_args()

    # 只查询上次导出信息（给编排层在跑前展示/确认用），不碰微信。跨两个 exports 目录取最新结束时间。
    if args.show_last:
        end_dt_last, src = latest_export_end(args.group, EXPORT_DIRS)
        if end_dt_last:
            log(f"LAST_EXPORT group={args.group} last_end={end_dt_last.strftime('%Y-%m-%d %H:%M')} src={src}")
            log(f"NEXT_START={end_dt_last.strftime('%Y-%m-%d %H:%M')}:00")
        else:
            log(f"NO_PRIOR_EXPORT group={args.group} dirs={EXPORT_DIRS}")
        return

    # 解析开始时间：未给 → 接上该群上次导出的结束时间（跨 dev exports + D:\MyDaily\exports 取最新）
    start_str = args.start
    start_source = "用户指定"
    if not start_str:
        end_dt_last, src = latest_export_end(args.group, EXPORT_DIRS)
        if not end_dt_last:
            raise SystemExit(f"NO_PRIOR_EXPORT: 群 '{args.group}' 在 {EXPORT_DIRS} 都没有历史导出记录，请显式提供 --start。")
        start_str = end_dt_last.strftime("%Y-%m-%d %H:%M:%S")
        start_source = f"接上次导出结束({start_str}) 来自 {os.path.basename(src)}"

    start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    if args.end:
        end_dt = datetime.datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")
    else:
        end_dt = datetime.datetime.now() - datetime.timedelta(hours=2)
    end_s = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    log(f"GROUP={args.group}  START={start_str} ({start_source})  END={end_s}")

    # 连接微信
    app = Application(backend="uia").connect(class_name=config.WECHAT_WINDOW_CLASS, timeout=10)
    win = app.window(class_name=config.WECHAT_WINDOW_CLASS)

    def find_list_title():
        cl = get_msg_list(win)
        tt = read_open_title(win, cl.rectangle().left) if cl else ""
        return cl, tt

    # 若当前已经打开目标聊天 → 跳过 Ctrl+F 导航（免提权、免中文注入）
    chat_list, title = find_list_title()
    if title and args.group in title:
        log("已是目标聊天，跳过导航(免提权):", repr(title))
    else:
        # 自动搜进群聊：直接 send_keys 把中文群名当 Unicode 按键发进搜索框（和 mydaily 完全一致，实测可靠）。
        # 历史教训：曾改用 tkinter 剪贴板 + Ctrl+V，但 Windows 上 tkinter 是“延迟渲染”剪贴板——
        # 微信按 Ctrl+V 来取数据时需要 tk 事件循环现场应答，而 worker 主线程一直 sleep、tk 没在跑循环，
        # 导致微信取到空内容 → “光标在搜索框却没文本”。pywinauto send_keys 用 KEYEVENTF_UNICODE 发字符，
        # 不依赖键盘布局/输入法，中文根本不会被挡（mydaily 一年来都这么用，从不失败）。
        win.set_focus(); time.sleep(0.5)
        send_keys('^f'); time.sleep(0.6)              # 打开搜索（普通按键，Medium 即可）
        send_keys('^a'); time.sleep(0.2)              # 清掉已有内容
        send_keys('{BACKSPACE}'); time.sleep(0.2)     # 确保清空
        send_keys(_escape_send_keys(args.group)); time.sleep(2.0)  # 逐字符发中文群名 → 搜索结果出现
        send_keys('{ENTER}'); time.sleep(1.5)         # 进第一个结果
        title = ""
        for _ in range(6):                            # 进群后界面有渲染延迟，重试读标题
            chat_list, title = find_list_title()
            if title: break
            time.sleep(0.4)
        log("OPENED CHAT TITLE:", repr(title))

    if chat_list is None:
        raise SystemExit("ABORT: 找不到消息列表(消息)，导航可能失败。")
    # 安全校验：顶部标题必须是目标聊天
    if args.group not in title:
        raise SystemExit(f"SAFETY ABORT: 打开的是 '{title}'，不是目标 '{args.group}'，未做任何抓取。")

    # 聚焦消息区
    rect = chat_list.rectangle()
    cx, cy = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
    M.move(coords=(cx, cy)); M.press(coords=(cx, cy)); M.release(coords=(cx, cy)); time.sleep(0.2)

    # ---- 快速上滚：鼠标滚轮上滚 + 点“查看更多消息”；用便宜读判断是否到起点 ----
    # 实测：滚轮有效(~3 聊天小时/秒)，PageUp 无效(加载不动)，故只用滚轮。
    try: win.set_focus()
    except Exception: pass
    t0 = time.time()
    reached = False
    prev_oldest = None
    stale = 0
    STALE_LIMIT = 30          # 连续 ~3s+ 无进展才考虑判到顶（微信批次加载会有停顿）
    for i in range(args.max_scroll):
        M.move(coords=(cx, cy))
        M.scroll(coords=(cx, cy), wheel_dist=8)   # 正值=向上(更早)
        had_button = click_load_more(chat_list)
        time.sleep(0.10)
        ot = cheap_oldest(chat_list)              # 便宜读，每轮都查
        advanced = (ot is not None and (prev_oldest is None or ot < prev_oldest))
        if advanced:
            stale = 0; prev_oldest = ot
        else:
            stale += 1
            # 卡住时加大力度：多滚几下 + 显式点“查看更多” + 重夺焦点 + 多等，给微信加载批次时间
            if stale % 6 == 0:
                for _ in range(4):
                    M.scroll(coords=(cx, cy), wheel_dist=10)
                click_load_more(chat_list)
                try: win.set_focus()
                except Exception: pass
                M.move(coords=(cx, cy)); M.press(coords=(cx, cy)); M.release(coords=(cx, cy))
                time.sleep(0.5)
        if i % args.check_every == 0:
            log(f"[{i}] {time.time()-t0:.1f}s oldest={ot} stale={stale} btn={'Y' if had_button else 'N'}")
        if ot and ot <= start_dt:
            reached = True
            log(f"REACHED start after {i} rounds, {time.time()-t0:.1f}s (oldest={ot})")
            break
        # 仅当长时间无进展 且 已无“查看更多消息”按钮时，才判定到顶（防误判提前停）
        if stale >= STALE_LIMIT and not had_button and not click_load_more(chat_list):
            log(f"NO MORE HISTORY (oldest stuck at {prev_oldest}) after {i} rounds, {time.time()-t0:.1f}s")
            break
    log(f"scroll done: reached={reached}, elapsed={time.time()-t0:.1f}s, oldest={prev_oldest}")

    # ---- 复用 mydaily：抽取 → 去重 → 写文件 →（可选）上传 ----
    messages = MyDaily.collect_messages_after_time(chat_list, start_dt)
    uniq = MyDaily.remove_duplicates(messages)

    now = datetime.datetime.now()
    sts = start_dt.strftime("%y%m%d%H%M")
    ets = end_dt.strftime("%y%m%d%H%M")
    fname = f"{args.group}_messages_{sts}-{ets}_{now.strftime('%y%m%d%H%M')}.md"
    fpath = os.path.join(config.EXPORT_PATH, fname)
    os.makedirs(config.EXPORT_PATH, exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"# {args.group} 聊天记录 - {now.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"开始时间: {start_str}\n结束时间: {end_s}\n导出时间: {now}\n\n")
        for m in uniq:
            f.write(f"{m}\n\n")
    log(f"WROTE {len(uniq)} messages -> {fpath}")

    log("RESULT_OK")

if __name__ == "__main__":
    main()
