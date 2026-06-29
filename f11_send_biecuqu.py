"""
F11发送消息模块
可独立进行单元测试

核心功能：
1. 冷却时间控制（5分钟）
2. 冷却结束时发送完整版消息
3. 冷却期间发送短版消息
4. 模拟键盘输入发送消息

独立使用方式：
    from f11_send_biecuqu import BieCuQuSender, send_biecuqu

    # 方式1: 使用默认配置（需要项目环境）
    send_biecuqu()

    # 方式2: 独立创建发送器进行测试
    sender = BieCuQuSender(cooldown=300)
    sender.send()
"""
import time
import random
import keyboard
import pyperclip

# ============================================================================
# 默认配置
# ============================================================================

# 冷却时间（秒）
DEFAULT_COOLDOWN = 300

# 完整版消息
FULL_MESSAGE = "我十六赛季五百强"

# 短版消息生成函数依赖
DEFAULT_EXT500_FUNC = None


# ============================================================================
# BieCuQuSender 类
# ============================================================================

class BieCuQuSender:
    """
    憋粗去消息发送器类
    封装F11功能的发送逻辑，支持独立测试
    """

    def __init__(self, cooldown=DEFAULT_COOLDOWN, ext500_func=None, log_func=None):
        """
        初始化发送器

        Args:
            cooldown: 冷却时间（秒）
            ext500_func: 生成短版消息的函数（返回整数）
            log_func: 日志函数（可选，默认使用print）
        """
        self.cooldown = cooldown
        self.ext500_func = ext500_func or (lambda: 1)
        self.log_func = log_func or self._default_log
        self._last_send_time = 0

    @staticmethod
    def _default_log(msg):
        """默认日志函数"""
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def is_cooldown_ready(self):
        """检查冷却是否就绪"""
        now = time.time()
        return (now - self._last_send_time) >= self.cooldown

    def get_remaining_time(self):
        """获取剩余冷却时间"""
        now = time.time()
        elapsed = now - self._last_send_time
        remaining = self.cooldown - elapsed
        return max(0, int(remaining))

    def generate_messages(self, is_cd_ready):
        """
        根据冷却状态生成消息列表

        Args:
            is_cd_ready: 冷却是否就绪

        Returns:
            list: 消息列表
        """
        if is_cd_ready:
            return [FULL_MESSAGE]
        else:
            # 短版：随机次数（目前固定为1）
            c1 = random.randint(1, 1)
            c2 = random.randint(1, 1)
            c3 = random.randint(1, 1)
            return [self.ext500_func() * c1]

    def send_single_message(self, message, index=1):
        """
        发送单条消息

        Args:
            message: 消息内容
            index: 消息序号
        """
        self.log_func(f"[发送{index}] 按下Enter打开聊天框")
        keyboard.press('enter')
        keyboard.release('enter')
        time.sleep(0.1)

        pyperclip.copy(message)
        keyboard.press('ctrl')
        keyboard.press('v')
        keyboard.release('v')
        keyboard.release('ctrl')
        time.sleep(0.2)

        self.log_func(f"[发送{index}] 按下Enter发送'{message}'")
        keyboard.press('enter')
        keyboard.release('enter')
        time.sleep(0.15)

    def send(self):
        """
        执行发送操作
        根据冷却状态决定发送完整版或短版

        Returns:
            bool: 发送是否成功
        """
        try:
            now = time.time()
            is_cd_ready = (now - self._last_send_time) >= self.cooldown

            self.log_func("\n" + "=" * 50)
            self.log_func("[F11] 执行发送")
            self.log_func("=" * 50)

            messages = self.generate_messages(is_cd_ready)

            if is_cd_ready:
                self._last_send_time = now
                self.log_func("[CD] 冷却已就绪，发送完整版")
            else:
                remaining = self.get_remaining_time()
                self.log_func(f"[CD] 冷却中，发送短版，剩余{remaining}秒")

            for i, message in enumerate(messages, 1):
                self.send_single_message(message, i)

            self.log_func("=" * 50)
            self.log_func("[成功] F11发送完成!")
            self.log_func("=" * 50)

            return True

        except Exception as e:
            self.log_func(f"[错误] F11发送失败: {e}")
            return False


# ============================================================================
# 全局实例（用于兼容 actions.py）
# ============================================================================

_sender_instance = None


def _get_sender():
    """获取或创建全局发送器实例"""
    global _sender_instance
    if _sender_instance is None:
        try:
            from ext500 import main as ext500_main
            _sender_instance = BieCuQuSender(
                cooldown=DEFAULT_COOLDOWN,
                ext500_func=ext500_main
            )
        except ImportError:
            _sender_instance = BieCuQuSender(cooldown=DEFAULT_COOLDOWN)
    return _sender_instance


# ============================================================================
# 兼容性别名
# ============================================================================

def send_biecuqu():
    """
    F11快捷键：发送消息，带5分钟冷却
    兼容 actions.py 的调用方式
    """
    sender = _get_sender()
    sender.send()


def create_f11_module(cooldown=DEFAULT_COOLDOWN, ext500_func=None, log_func=None):
    """
    工厂函数：创建配置好的F11模块

    Args:
        cooldown: 冷却时间（秒）
        ext500_func: 生成短版消息的函数
        log_func: 日志函数

    Returns:
        dict: 包含sender和send_biecuqu函数的字典
    """
    sender = BieCuQuSender(cooldown=cooldown, ext500_func=ext500_func, log_func=log_func)

    def wrapped_send():
        return sender.send()

    return {
        "sender": sender,
        "send_biecuqu": wrapped_send
    }


# ============================================================================
# 单元测试入口
# ============================================================================

def _wait_for_f11():
    """
    阻塞等待F11按键，执行发送操作
    """
    import keyboard

    print("\n[等待F11] 按下F11执行发送，按Ctrl+C退出测试")
    print("=" * 60)

    # 获取已配置好的发送器（包含ext500_func）
    sender = _get_sender()
    sender.log_func = lambda msg: print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    while True:
        try:
            keyboard.wait('f11')
            print("\n[触发] 检测到F11按下，开始发送...")
            sender.send()
            print("\n[等待F11] 发送完成，继续等待...")
        except KeyboardInterrupt:
            print("\n[退出] 测试结束")
            break


def _test_real_send():
    """
    实际发送测试（需要在游戏窗口或其他可接收输入的环境）
    """
    print("\n[实际发送测试]")
    print("注意：此测试会实际发送消息，请确保在聊天输入框聚焦的环境中运行")

    sender = BieCuQuSender(log_func=lambda msg: print(f"[测试] {msg}"))

    # 模拟刚冷却结束，发送完整版
    print("\n--- 测试1: 发送完整版 ---")
    sender._last_send_time = 0  # 重置冷却
    sender.send()

    time.sleep(1)

    # 模拟冷却中，发送短版
    print("\n--- 测试2: 发送短版 ---")
    sender._last_send_time = time.time() - 10  # 10秒前
    sender.send()

    print("\n[实际发送测试完成]")


def _test_message_generation():
    """消息生成测试"""
    print("\n[测试3] 消息生成测试")
    try:
        sender = BieCuQuSender()
        # 强制设置上次发送时间以便测试完整版
        sender._last_send_time = 0
        messages_full = sender.generate_messages(is_cd_ready=True)
        print(f"  - 完整版消息: {messages_full}")

        # 设置最近发送过以便测试短版
        sender._last_send_time = time.time() - 10  # 10秒前
        messages_short = sender.generate_messages(is_cd_ready=False)
        print(f"  - 短版消息: {messages_short}")
        print("[测试3] 通过")
    except Exception as e:
        print(f"[测试3] 失败: {e}")


def _test_cooldown():
    """冷却状态测试"""
    print("\n[测试4] 冷却状态测试")
    try:
        sender = BieCuQuSender()
        print(f"  - 初始状态冷却就绪: {sender.is_cooldown_ready()}")

        # 模拟刚发送过
        sender._last_send_time = time.time()
        print(f"  - 刚发送后冷却就绪: {sender.is_cooldown_ready()}")
        print(f"  - 剩余冷却时间: {sender.get_remaining_time()}秒")

        # 模拟10秒前发送
        sender._last_send_time = time.time() - 10
        print(f"  - 10秒前发送后冷却就绪: {sender.is_cooldown_ready()}")
        print(f"  - 剩余冷却时间: {sender.get_remaining_time()}秒")
        print("[测试4] 通过")
    except Exception as e:
        print(f"[测试4] 失败: {e}")


if __name__ == "__main__":

    _wait_for_f11()

