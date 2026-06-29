import datetime
import pyperclip

import datetime



def generate_position_string(target_datetime_str: str, times: str) -> str:
    """生成职位信息字符串（精确到天、小时、分钟）"""
    # 解析目标日期时间
    target_datetime = datetime.datetime.strptime(target_datetime_str, "%Y年%m月%d日%H:%M")
    now = datetime.datetime.now()

    # 计算时间差
    delta = now - target_datetime
    total_seconds = delta.total_seconds()

    # 计算天数、小时和分钟
    days_diff = delta.days
    remaining_seconds = total_seconds - (days_diff * 24 * 3600)
    hours_diff = int(remaining_seconds // 3600)
    minutes_diff = int((remaining_seconds % 3600) // 60)

    # 生成字符串
    return f"我是十六赛季500强第394名（那天是{times}，距离现在过了{days_diff}天）"





def generate_appreciation_string(target_date_str: str, times: str) -> str:
    """生成赞赏信息字符串"""
    # 解析目标日期
    target_date = datetime.datetime.strptime(target_date_str, "%Y年%m月%d日").date()
    today = datetime.date.today()

    # 计算天数差
    delta = today - target_date
    days_diff = delta.days

    # 生成基础字符串
    if days_diff == 0:
        return f"我是五级赞赏（那天是{times}，距离今天过了0天）"
    else:
        return f"我是五级赞赏（那天是{times}，距离今天过了{days_diff}天）"


def generate_gladiator_string(target_date_str: str, times: str) -> str:
    """生成角斗领域全明星支援信息字符串"""
    # 解析目标日期
    target_date = datetime.datetime.strptime(target_date_str, "%Y年%m月%d日").date()
    today = datetime.date.today()

    # 计算天数差
    delta = today - target_date
    days_diff = delta.days

    # 生成基础字符串
    if days_diff == 0:
        return f"我是角斗领域全明星支援（那天是{times}，距离今天过了0天）"
    else:
        return f"我是角斗领域全明星支援（那天是{times}，距离今天过了{days_diff}天）"


def main():
    # 目标日期时间（精确到分钟）
    times = '2025年5月8日12:46:25'
    # 提取日期和小时分钟部分
    date_part = times.split('日')[0] + '日'
    time_part = times.split('日')[1].split(':')[0] + ':' + times.split(':')[1]
    target_datetime_str = date_part + time_part

    # 生成字符串
    result = generate_position_string(target_datetime_str, times)
    return result


def main2():
    # 目标日期
    times = '2025年5月16日13:18:58'
    target_date_str = times.split('日')[0] + '日'

    # 生成字符串
    result = generate_appreciation_string(target_date_str, times)
    return result


def main3():
    # 目标日期
    times = '2025年5月28日13:56:07'
    target_date_str = times.split('日')[0] + '日'

    # 生成字符串
    result = generate_gladiator_string(target_date_str, times)
    return result


if __name__ == "__main__":
    print(main())  # 测试输出
