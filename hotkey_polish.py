"""
AI 热键润色助手
选中文字后按 Ctrl+X，自动剪切 → AI润色 → 复制到剪贴板
系统托盘控制：启用/停用热键、退出
"""
import pyperclip
import keyboard
import time
import threading
import ctypes
import sys
import logging
import tkinter as tk
from tkinter import scrolledtext, messagebox
from queue import Queue
from datetime import datetime
from ai_polish import polish_text

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    print("[提示] 未安装 pystray/pillow，托盘功能不可用")
    print("       安装命令: pip install pystray pillow")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

HOTKEY = 'ctrl+x'
_is_processing = threading.Event()
_should_exit = threading.Event()
_hotkey_enabled = threading.Event()
_hotkey_enabled.set()
_task_queue = Queue(maxsize=1)
_icon = None
_hotkey_hook = None

# 日志缓存
_log_cache = []
_log_cache_lock = threading.Lock()
MAX_LOG_ENTRIES = 50


def add_log_entry(title, content):
    """添加日志条目到缓存"""
    entry = {
        'time': datetime.now().strftime('%H:%M:%S'),
        'title': title,
        'content': content
    }
    with _log_cache_lock:
        _log_cache.append(entry)
        if len(_log_cache) > MAX_LOG_ENTRIES:
            _log_cache.pop(0)


def show_log_window():
    """显示日志窗口"""
    log_window = None
    text_widget = None
    _log_window_ref = [None]  # 使用引用保存窗口

    def on_copy():
        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                pyperclip.copy(selected_text)
                messagebox.showinfo("提示", "已复制到剪贴板")
        except tk.TclError:
            messagebox.showwarning("提示", "请先选中要复制的内容")

    def on_copy_all():
        all_text = text_widget.get('1.0', tk.END)
        pyperclip.copy(all_text)
        messagebox.showinfo("提示", "已复制全部内容到剪贴板")

    def on_pin(window):
        """切换置顶状态"""
        current = window.attributes('-topmost')
        window.attributes('-topmost', not current)

    def update_log_display():
        """实时更新日志显示（倒序，最新的在上）"""
        if text_widget and log_window:
            try:
                with _log_cache_lock:
                    # 倒序获取日志（最新的在前）
                    display_logs = list(reversed(_log_cache))

                text_widget.config(state=tk.NORMAL)
                text_widget.delete('1.0', tk.END)

                for entry in display_logs:
                    text_widget.insert(tk.END, f"[{entry['time']}] {entry['title']}\n", 'title')
                    text_widget.insert(tk.END, f"{entry['content']}\n\n", 'content')

                text_widget.config(state=tk.DISABLED)

                # 滚动到最上方显示最新日志
                text_widget.yview_moveto(0)
            except:
                pass

            # 继续定时更新
            if log_window and log_window.winfo_exists():
                log_window.after(500, update_log_display)

    def on_window_focus_out(window):
        """窗口失焦时移除置顶"""
        window.attributes('-topmost', False)

    root = tk.Tk()
    log_window = root
    _log_window_ref[0] = root
    root.title("提取结果日志")
    root.geometry("600x400")

    # 初始置顶，但失焦后会自动解除
    root.attributes('-topmost', True)

    # 绑定失焦事件
    root.bind('<FocusOut>', lambda e: on_window_focus_out(root))

    # 按钮
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill=tk.X, padx=5, pady=5)

    tk.Button(btn_frame, text="复制选中", command=on_copy).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="复制全部", command=on_copy_all).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="置顶", command=lambda: on_pin(root)).pack(side=tk.LEFT, padx=5)

    # 文本区域
    text_widget = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=('Microsoft YaHei', 10))
    text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    text_widget.tag_config('title', foreground='blue', font=('Microsoft YaHei', 10, 'bold'))
    text_widget.tag_config('content', foreground='black', font=('Microsoft YaHei', 10))

    # 初始显示
    update_log_display()

    root.mainloop()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def safe_paste(max_retries=3, delay=0.1):
    for _ in range(max_retries):
        try:
            text = pyperclip.paste()
            if text is not None:
                return text
        except Exception as e:
            logging.warning(f"剪贴板读取失败: {e}")
        time.sleep(delay)
    return ""


def safe_copy(text, max_retries=3, delay=0.1):
    for _ in range(max_retries):
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            logging.warning(f"剪贴板写入失败: {e}")
        time.sleep(delay)
    return False


def heartbeat_monitor():
    counter = 0
    while not _should_exit.is_set():
        time.sleep(60)
        if not _should_exit.is_set():
            counter += 1
            status = "运行中" if not _is_processing.is_set() else "处理中"
            enabled = "已启用" if _hotkey_enabled.is_set() else "已停用"
            logging.info(f"[心跳] {enabled} | {status} (已运行 {counter} 分钟)")


def do_polish_work():
    if _is_processing.is_set():
        logging.warning("[Ctrl+X] 正在处理中，请稍候...")
        return

    if not _hotkey_enabled.is_set():
        return

    _is_processing.set()
    original_text = ""

    try:
        logging.info("[Ctrl+X] 开始处理...")

        saved_clipboard = safe_paste()

        keyboard.send('ctrl+c')
        time.sleep(0.15)

        clipped_text = safe_paste()

        if not clipped_text or not clipped_text.strip():
            logging.info("[Ctrl+X] 未检测到文本，恢复剪贴板")
            safe_copy(saved_clipboard)
            return

        keyboard.send('delete')
        time.sleep(0.1)

        original_text = clipped_text
        logging.info(f"[润色中] 原文: {clipped_text[:60]}{'...' if len(clipped_text) > 60 else ''}")

        results = polish_text(clipped_text)

        if results and len(results) >= 1:
            polished = results[0]
            logging.info(f"[完成] {polished[:60]}")

            # 保存结果到日志缓存
            result_text = f"原文: {clipped_text}\n\n候选结果 (共 {len(results)} 个):\n"
            for i, r in enumerate(results, 1):
                result_text += f"   {i}. {r}\n"
            add_log_entry(f"[提取结果] JSON解析成功，找到 {len(results)} 个候选结果", result_text)

            safe_copy(polished)
            time.sleep(0.05)
            keyboard.send('z')
            logging.info("[提示] 已按下 Z 键，结果已复制到剪贴板")
        else:
            logging.info("[完成] (无匹配，使用原文)")

            # 保存无匹配结果到日志缓存
            add_log_entry("[提取结果] 无匹配结果", f"原文: {clipped_text}")

            safe_copy(clipped_text)
            time.sleep(0.05)
            keyboard.send('z')
            logging.info("[提示] 已按下 Z 键，原文已复制到剪贴板")

    except Exception as e:
        logging.error(f"[错误] 处理失败: {e}")
        if original_text:
            try:
                safe_copy(original_text)
                keyboard.send('ctrl+v')
            except:
                pass
    finally:
        _is_processing.clear()


def worker_thread():
    while not _should_exit.is_set():
        try:
            task = _task_queue.get(timeout=0.5)
            if task == 'polish':
                do_polish_work()
            _task_queue.task_done()
        except:
            pass


def on_ctrl_x():
    if _is_processing.is_set() or not _hotkey_enabled.is_set():
        return
    try:
        _task_queue.put_nowait('polish')
        logging.debug("[Ctrl+X] 任务入队")
    except:
        logging.debug("[Ctrl+X] 队列已满，任务丢弃")


def register_hotkey():
    global _hotkey_hook
    try:
        _hotkey_hook = keyboard.add_hotkey(HOTKEY, on_ctrl_x, suppress=False)
        logging.info(f"[热键已注册] {HOTKEY}")
        return True
    except Exception as e:
        logging.error(f"[错误] 注册热键失败: {e}")
        return False


def unregister_hotkey():
    global _hotkey_hook
    try:
        if _hotkey_hook:
            keyboard.remove_hotkey(_hotkey_hook)
            _hotkey_hook = None
            logging.info("[热键已注销]")
    except Exception as e:
        logging.error(f"[错误] 注销热键失败: {e}")


def create_tray_image(status):
    color = (34, 197, 94, 255) if status == 'running' else (239, 68, 68, 255)
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([4, 4, 60, 60], fill=color)
    draw.ellipse([16, 16, 48, 48], fill=(255, 255, 255, 255))
    return image


def update_tray_icon():
    global _icon
    if _icon and HAS_TRAY:
        if _hotkey_enabled.is_set():
            _icon.icon = create_tray_image('running')
            _icon.title = "热键润色助手 - 运行中"
        else:
            _icon.icon = create_tray_image('stopped')
            _icon.title = "热键润色助手 - 已暂停"


def tray_toggle(icon, item):
    if _hotkey_enabled.is_set():
        _hotkey_enabled.clear()
        unregister_hotkey()
        logging.info("[托盘] 热键已停用")
    else:
        if register_hotkey():
            _hotkey_enabled.set()
            logging.info("[托盘] 热键已启用")
    update_tray_icon()


def tray_enable(icon, item):
    if not _hotkey_enabled.is_set():
        if register_hotkey():
            _hotkey_enabled.set()
            logging.info("[托盘] 热键已启用")
            update_tray_icon()


def tray_disable(icon, item):
    if _hotkey_enabled.is_set():
        _hotkey_enabled.clear()
        unregister_hotkey()
        logging.info("[托盘] 热键已停用")
        update_tray_icon()


def tray_quit(icon, item):
    logging.info("[托盘] 退出程序")
    _should_exit.set()
    try:
        icon.stop()
    except:
        pass


def tray_show_log(icon, item):
    """托盘菜单：显示日志窗口"""
    logging.info("[托盘] 显示日志窗口")
    # pystray回调在线程中执行，直接创建窗口会有Tcl警告但不影响功能
    threading.Thread(target=show_log_window, daemon=True).start()


def tray_thread_func():
    global _icon
    if not HAS_TRAY:
        return

    menu = pystray.Menu(
        pystray.MenuItem("启用/停用", tray_toggle, default=True),
        pystray.MenuItem("启用热键", tray_enable, enabled=lambda item: not _hotkey_enabled.is_set()),
        pystray.MenuItem("停用热键", tray_disable, enabled=lambda item: _hotkey_enabled.is_set()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("显示日志", tray_show_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", tray_quit)
    )

    _icon = pystray.Icon(
        "hotkey_polish",
        create_tray_image('running'),
        "热键润色助手 - 运行中",
        menu
    )

    _icon.run()


def main():
    logging.info("=" * 50)
    logging.info("  AI 热键润色助手 启动")
    logging.info("=" * 50)
    logging.info("使用方法：选中文字 → 按 Ctrl+X")
    logging.info("自动完成：剪切 → AI润色 → 复制到剪贴板")
    logging.info("=" * 50)

    if not is_admin():
        logging.warning("[警告] 未以管理员身份运行，热键可能无法正常工作")
        logging.warning("[提示] 建议右键以管理员身份运行此程序")

    heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
    heartbeat_thread.start()

    worker = threading.Thread(target=worker_thread, daemon=True)
    worker.start()

    if not register_hotkey():
        logging.error("[错误] 热键注册失败，程序退出")
        sys.exit(1)

    if HAS_TRAY:
        tray_thread = threading.Thread(target=tray_thread_func, daemon=True)
        tray_thread.start()
        logging.info("[托盘] 系统托盘已启动，右键托盘图标可控制")
    else:
        logging.info("[提示] 托盘功能不可用，按 Ctrl+C 退出程序")

    try:
        while not _should_exit.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("[退出] 用户按下 Ctrl+C")
    finally:
        _should_exit.set()
        try:
            keyboard.unhook_all()
        except:
            pass
        if _icon and HAS_TRAY:
            try:
                _icon.stop()
            except:
                pass
        logging.info("[退出] 程序已退出，感谢使用")


if __name__ == "__main__":
    main()
