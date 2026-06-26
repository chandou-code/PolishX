"""
热键润色助手
选中文字后按 Ctrl+X，剪切 → AI润色 → 自动粘贴
"""
import pyperclip
import keyboard
import time
import threading
import ctypes
import sys
import logging
from queue import Queue
from ai_polish import polish_text

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

HOTKEY = 'ctrl+x'
_is_processing = threading.Event()
_should_exit = threading.Event()
_task_queue = Queue(maxsize=1)


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
            logging.info(f"[心跳] 程序状态: {status} (已运行 {counter} 分钟)")


def do_polish_work():
    """在独立线程中执行润色工作"""
    if _is_processing.is_set():
        logging.warning("[Ctrl+X] 正在处理中，请稍候...")
        return

    _is_processing.set()
    original_text = ""

    try:
        logging.info("[Ctrl+X] 开始处理...")

        saved_clipboard = safe_paste()

        # 使用 ctrl+c 复制 + delete 删除来等效实现剪切
        # 这样不会触发我们注册的 ctrl+x 热键钩子
        keyboard.send('ctrl+c')
        time.sleep(0.15)

        clipped_text = safe_paste()

        if not clipped_text or not clipped_text.strip():
            logging.info("[Ctrl+X] 未检测到文本，恢复剪贴板")
            safe_copy(saved_clipboard)
            return

        # 删除选中的文字
        keyboard.send('delete')
        time.sleep(0.1)

        original_text = clipped_text
        logging.info(f"[润色中] 原文: {clipped_text[:60]}{'...' if len(clipped_text) > 60 else ''}")

        results = polish_text(clipped_text)

        if results and len(results) >= 1:
            polished = results[0]
            logging.info(f"[完成] {polished[:60]}")
            safe_copy(polished)
            time.sleep(0.1)
            keyboard.send('ctrl+v')
            time.sleep(0.1)
        else:
            logging.info("[完成] (无匹配，使用原文)")
            safe_copy(clipped_text)
            time.sleep(0.1)
            keyboard.send('ctrl+v')
            time.sleep(0.1)

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
    """工作线程，从队列中取任务执行"""
    while not _should_exit.is_set():
        try:
            task = _task_queue.get(timeout=0.5)
            if task == 'polish':
                do_polish_work()
            _task_queue.task_done()
        except:
            pass


def on_ctrl_x():
    """Ctrl+X 热键回调 - 只往队列里放任务，不做实际处理"""
    if _is_processing.is_set():
        return
    try:
        _task_queue.put_nowait('polish')
        logging.debug("[Ctrl+X] 任务入队")
    except:
        logging.debug("[Ctrl+X] 队列已满，任务丢弃")


def main():
    logging.info("=" * 50)
    logging.info("  AI 热键润色助手 启动")
    logging.info("=" * 50)
    logging.info("使用方法：选中文字 → 按 Ctrl+X")
    logging.info("自动完成：剪切 → AI润色 → 粘贴")
    logging.info("按 Ctrl+C 或关闭窗口退出程序")
    logging.info("=" * 50)

    if not is_admin():
        logging.warning("[警告] 未以管理员身份运行，热键可能无法正常工作")
        logging.warning("[提示] 建议右键以管理员身份运行此程序")

    heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
    heartbeat_thread.start()

    worker = threading.Thread(target=worker_thread, daemon=True)
    worker.start()

    try:
        keyboard.add_hotkey(HOTKEY, on_ctrl_x, suppress=True)
        logging.info(f"[热键已注册] {HOTKEY}")
    except Exception as e:
        logging.error(f"[错误] 注册热键失败: {e}")
        logging.error("[提示] 请确保没有其他程序占用 Ctrl+X 热键")
        input("按回车键退出...")
        return

    logging.info("[运行中] 程序进入后台运行状态...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("[退出] 用户按下 Ctrl+C")
    except Exception as e:
        logging.error(f"[异常] 程序异常退出: {e}")
    finally:
        _should_exit.set()
        try:
            keyboard.unhook_all()
        except:
            pass
        logging.info("[退出] 程序已退出，感谢使用")


if __name__ == "__main__":
    main()