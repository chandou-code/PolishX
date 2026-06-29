"""
硅基流动 AI 润色模块
调用 SiliconFlow /v1/messages 接口对文本进行润色
"""
import requests
import json
import re
import time
import os
import csv
from typing import Optional, List
from datetime import datetime

# 读取配置
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
_api_config = {}

def _load_config():
    """从json文件加载配置"""
    global _api_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            _api_config = json.load(f)
    except Exception as e:
        print(f"[配置] 加载配置文件失败: {e}")
        _api_config = {}

_load_config()

API_KEY = _api_config.get('api_key', '')
BASE_URL = _api_config.get('base_url', 'https://api.siliconflow.cn/v1/chat/completions')
DEFAULT_MODEL = _api_config.get('default_model', 'deepseek-ai/DeepSeek-V4-Flash')
MAX_TOKENS = _api_config.get('max_tokens', 300)
TEMPERATURE = _api_config.get('temperature', 0.5)
TOP_P = _api_config.get('top_p', 0.9)
TOP_K = _api_config.get('top_k', 50)
FREQUENCY_PENALTY = _api_config.get('frequency_penalty', 0.5)
THINKING_BUDGET = _api_config.get('thinking_budget', 1024)
REASONING_EFFORT = _api_config.get('reasoning_effort', 'high')

# 请求日志文件
LOG_FILE = os.path.join(os.path.dirname(__file__), "request_log.csv")

def _append_request_log(input_text, thinking, output):
    """追加请求日志到CSV表格"""
    try:
        # 解析输出结果
        output_text = output
        try:
            output_data = json.loads(output)
            if isinstance(output_data, dict) and 'results' in output_data:
                output_text = ' | '.join(output_data['results'])
        except:
            pass

        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            input_text,
            thinking if thinking else '无',
            output_text
        ]

        file_exists = os.path.exists(LOG_FILE)
        with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['时间', '输入', '思考部分', '输出结果'])
            writer.writerow(row)
    except Exception as e:
        print(f"[日志] 写入请求日志失败: {e}")

SYSTEM_PROMPT = """
严格按照以下JSON格式输出，不要输出任何其他内容：
{"results": ["改写后的句子1", "改写后的句子2", "改写后的句子3"]}
确保JSON格式正确，不要包含markdown代码块标记。"""


def polish_text(text: str, model: str = DEFAULT_MODEL, max_retries: int = 3) -> list:
    """
    调用硅基流动API润色文本

    Args:
        text: 需要润色的原始文本
        model: 使用的模型名称
        max_retries: 最大重试次数

    Returns:
        润色后的文本列表（可能有多个结果）
    """
    if not text or not text.strip():
        return [text]

    user_prompt = f'"{text}" 改成更口语化通顺的嘲讽表达，可以恶心人但不能有脏话。不要引号。重点是模拟我主动开口的语气，绝对不要写成是在回复别人，不要用比喻'

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": False
    }

    # 仅在有意义时添加思考参数
    if THINKING_BUDGET > 0:
        payload["thinking_budget"] = THINKING_BUDGET
        payload["reasoning_effort"] = REASONING_EFFORT



    print("\n[发送请求] ====================")
    print(f"模型: {model}")
    print(f"用户输入: {user_prompt}")
    print("============================\n")

    try:
        response = requests.post(
            BASE_URL,
            headers=headers,
            json=payload,
            timeout=30,
            verify=True
        )

        response.raise_for_status()
        data = response.json()

        print("[原始响应] ====================")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(data, ensure_ascii=False)[:500]}")
        usage = data.get('usage', {})
        print(f"token消耗: 输入{usage.get('input_tokens', 0)} 输出{usage.get('output_tokens', 0)}")
        print("============================\n")

        # 提取思考内容
        thinking_content = _extract_thinking_from_response(data)
        if thinking_content:
            print(f"[思考过程] {thinking_content[:200]}...")

        content = _extract_content_from_response(data)

        if not content:
            print(f"[AI润色] 无法从响应中提取内容: {data}")
            # 即使提取失败也记录日志
            _append_request_log(user_prompt, thinking_content or "无", f"提取失败: {data}")
            return [text]

        results = _extract_from_json(content)

        if results:
            print(f"[提取结果] JSON解析成功，找到 {len(results)} 个候选结果:")
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r}")
            final_output = json.dumps({"results": results}, ensure_ascii=False)
            _append_request_log(user_prompt, thinking_content or "无", final_output)
            return results

        results = _extract_multiple_quoted_texts(content)

        if results:
            print(f"[提取结果] 正则匹配成功，找到 {len(results)} 个候选结果:")
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r}")
            final_output = json.dumps({"results": results}, ensure_ascii=False)
            _append_request_log(user_prompt, thinking_content or "无", final_output)
            return results

        _append_request_log(user_prompt, thinking_content or "无", content)
        return [content]

    except Exception as e:
        print(f"[AI润色] 请求失败: {e}")
        _append_request_log(user_prompt, "请求异常", f"错误: {e}")
        return [text]


def _extract_content_from_response(data: dict) -> Optional[str]:
    """从API响应中提取文本内容，兼容多种响应格式"""
    if not isinstance(data, dict):
        return None

    if "content" in data and isinstance(data["content"], list):
        for block in data["content"]:
            if isinstance(block, dict) and block.get("type") == "text" and "text" in block:
                return str(block["text"]).strip()
        for block in data["content"]:
            if isinstance(block, str):
                return block.strip()
            if isinstance(block, dict) and "text" in block:
                return str(block["text"]).strip()

    if "choices" in data and isinstance(data["choices"], list) and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if isinstance(choice, dict) and "message" in choice:
            msg = choice["message"]
            if isinstance(msg, dict) and "content" in msg:
                return str(msg["content"]).strip()

    for key in ("content", "text", "output", "message"):
        if key in data and isinstance(data[key], str):
            return data[key].strip()

    return None


def _extract_thinking_from_response(data: dict) -> Optional[str]:
    """从API响应中提取思考内容"""
    if not isinstance(data, dict):
        return None

    # 尝试从thinking字段提取
    if "thinking" in data:
        return str(data["thinking"]).strip()

    # 尝试从metadata.thinking提取
    if "metadata" in data and isinstance(data["metadata"], dict):
        if "thinking" in data["metadata"]:
            return str(data["metadata"]["thinking"]).strip()

    # 尝试从content中的thinking类型提取
    if "content" in data and isinstance(data["content"], list):
        for block in data["content"]:
            if isinstance(block, dict) and block.get("type") == "thinking":
                return str(block.get("text", "")).strip()

    # 尝试从choices[0].message.reasoning_content提取（SiliconFlow API格式）
    if "choices" in data and isinstance(data["choices"], list) and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if isinstance(choice, dict) and "message" in choice:
            msg = choice["message"]
            if isinstance(msg, dict) and "reasoning_content" in msg:
                rc = msg["reasoning_content"]
                if rc and str(rc).strip():
                    return str(rc).strip()

    return None


def _extract_from_json(content: str) -> list:
    """从内容中提取JSON格式的results列表"""
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "results" in data:
            results = data["results"]
            if isinstance(results, list):
                return [str(r).strip() for r in results if r and str(r).strip()]
        return []
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    if isinstance(results, list):
                        return [str(r).strip() for r in results if r and str(r).strip()]
            except json.JSONDecodeError:
                pass
        return []


def _extract_multiple_quoted_texts(content: str) -> list:
    """正则匹配所有 "xxx" 或 'xxx' 包围的文本，返回列表（按顺序）"""
    patterns = [
        r'"([^"]+)"',
        r"'([^']+)'",
    ]

    results = []
    seen = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            cleaned = match.strip()
            if cleaned and len(cleaned) > 1 and cleaned not in seen:
                results.append(cleaned)
                seen.add(cleaned)

    return results


if __name__ == "__main__":
    test_text = "好舒服啊"
    print(f"原文: {test_text}")
    print("正在润色...")
    result = polish_text(test_text)
    print(f"\n最终结果: {result}")
