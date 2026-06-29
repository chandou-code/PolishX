"""
F7 轮播消息发送工具
按F7键按顺序发送预设消息：就打她 -> 好舒服啊 -> 对面安娜是我前女友 -> 循环
"""
import time
import keyboard
import pyperclip

# F7 轮播消息配置
F7_MESSAGES = [
    "就打她",
    "好舒服啊",
    "对面安娜是我前女友"
]
_f7_send_index = 0


def send_f7_message():
    """
    F7快捷键：轮播发送三条预设消息
    每次按下F7，按顺序发送一条消息：只发就打她 -> 好舒服啊 -> 对面安娜是我前女友 -> 循环
    """
    global _f7_send_index

    msg = F7_MESSAGES[_f7_send_index]
    _f7_send_index = (_f7_send_index + 1) % len(F7_MESSAGES)

    keyboard.press_and_release('enter')
    time.sleep(0.05)
    pyperclip.copy(msg)
    keyboard.press_and_release('ctrl+v')
    time.sleep(0.05)
    keyboard.press_and_release('enter')


def main():
    print("=" * 50)
    print("F7 轮播消息发送工具已启动")
    print("按F7发送消息（轮播顺序：只发就打她 -> 好舒服啊 -> 对面安娜是我前女友）")
    print("按Ctrl+C退出")
    print("=" * 50)

    keyboard.on_press_key('f7', lambda _: send_f7_message())

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n程序已退出")


if __name__ == "__main__":
    main()
