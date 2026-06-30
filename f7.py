"""
F7 轮播消息发送工具
按F7键按顺序发送预设消息：就打她 -> 好舒服啊 -> 对面安娜是我前女友 -> 循环
每分钟自动重置顺序
"""
import time
import keyboard
import pyperclip
import threading

# F7 轮播消息配置
F7_MESSAGES = [
    "就打她",
    "对面安娜是我前女友"
]
_f7_send_index = 0


def reset_f7_index():
    """每分钟重置发送顺序"""
    global _f7_send_index
    print(f"[F7] 重置线程已启动，将在60秒后首次重置")
    while True:
        time.sleep(60)
        _f7_send_index = 0
        print(f"[F7] 已重置发送顺序，下次发送将从第1条开始 ({time.strftime('%H:%M:%S')})")


def send_f7_message():
    """
    F7快捷键：轮播发送三条预设消息
    每次按下F7，按顺序发送一条消息：只发就打她 -> 好舒服啊 -> 对面安娜是我前女友 -> 循环
    """
    global _f7_send_index

    msg = F7_MESSAGES[_f7_send_index]
    current_index = _f7_send_index + 1
    total = len(F7_MESSAGES)
    _f7_send_index = (_f7_send_index + 1) % len(F7_MESSAGES)

    print(f"\n[F7] 检测到按键，开始发送 ({time.strftime('%H:%M:%S')})")
    print(f"[F7] 发送第 {current_index}/{total} 条消息")
    print(f"[F7] 消息内容: {msg}")

    print("[F7] 按下Enter打开聊天框")
    keyboard.press('enter')
    keyboard.release('enter')
    time.sleep(0.1)

    print("[F7] 复制消息到剪贴板")
    pyperclip.copy(msg)
    print("[F7] 按下Ctrl+V粘贴消息")
    keyboard.press('ctrl')
    keyboard.press('v')
    keyboard.release('v')
    keyboard.release('ctrl')
    time.sleep(0.3)

    print("[F7] 按下Enter发送消息")
    keyboard.press('enter')
    keyboard.release('enter')
    time.sleep(0.15)

    print(f"[F7] 发送完成，下次将发送第 {(_f7_send_index + 1)}/{total} 条")


def main():
    print("=" * 50)
    print("F7 轮播消息发送工具已启动")
    print("按F7发送消息（轮播顺序：只发就打她 -> 好舒服啊 -> 对面安娜是我前女友）")
    print("按Ctrl+C退出")
    print("=" * 50)

    reset_thread = threading.Thread(target=reset_f7_index, daemon=True)
    reset_thread.start()

    keyboard.on_release_key('f7', lambda _: send_f7_message())

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n程序已退出")


if __name__ == "__main__":
    main()
