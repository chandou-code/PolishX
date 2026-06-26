"""
硅基流动 AI 润色模块
调用 SiliconFlow /v1/messages 接口对文本进行润色
"""
import requests
import json
import re
import time

API_KEY = ""
BASE_URL = "https://api.siliconflow.cn/v1/messages"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"

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

    user_prompt = f'"{text}" 改成更口语化通顺的嘲讽表达，可以恶心人但不能有脏话。不要引号。重点是模拟我主动开口的语气，绝对不要写成是在回复别人'

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.5,
        "stream": False,
        "thinking_budget": 0
    }

    print("\n[发送请求] ====================")
    print(f"模型: {model}")
    print(f"用户输入: {user_prompt}")
    print("============================\n")

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                BASE_URL,
                headers=headers,
                json=payload,
                timeout=30,
                verify=True
            )

            if response.status_code == 429:
                wait_time = min(2 ** attempt, 10)
                print(f"[AI润色] 请求过快(429)，等待 {wait_time} 秒后重试")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            print("[原始响应] ====================")
            print(f"状态码: {response.status_code}")
            print(f"返回内容: {data.get('content', 'N/A')}")
            print(f"token消耗: 输入{data.get('usage', {}).get('input_tokens', 0)} 输出{data.get('usage', {}).get('output_tokens', 0)}")
            print("============================\n")

            content = _extract_content_from_response(data)

            if not content:
                print(f"[AI润色] 无法从响应中提取内容: {data}")
                return [text]

            results = _extract_from_json(content)

            if results:
                print(f"[提取结果] JSON解析成功，找到 {len(results)} 个候选结果:")
                for i, r in enumerate(results, 1):
                    print(f"  {i}. {r}")
                return results

            results = _extract_multiple_quoted_texts(content)

            if results:
                print(f"[提取结果] 正则匹配成功，找到 {len(results)} 个候选结果:")
                for i, r in enumerate(results, 1):
                    print(f"  {i}. {r}")
                return results

            return [content]

        except requests.exceptions.Timeout:
            print(f"[AI润色] 第{attempt + 1}次请求超时")
            if attempt < max_retries:
                time.sleep(1)
                continue
            else:
                print(f"[AI润色] 所有重试失败，返回原文本")
                return [text]
        except requests.exceptions.ConnectionError:
            print(f"[AI润色] 第{attempt + 1}次请求连接失败，请检查网络")
            if attempt < max_retries:
                time.sleep(2)
                continue
            else:
                print(f"[AI润色] 所有重试失败，返回原文本")
                return [text]
        except requests.exceptions.HTTPError as e:
            print(f"[AI润色] 第{attempt + 1}次请求HTTP错误: {e}")
            if attempt < max_retries:
                time.sleep(1)
                continue
            else:
                print(f"[AI润色] 所有重试失败，返回原文本")
                return [text]
        except json.JSONDecodeError:
            print(f"[AI润色] 第{attempt + 1}次请求响应不是有效JSON")
            if attempt < max_retries:
                continue
            else:
                print(f"[AI润色] 所有重试失败，返回原文本")
                return [text]
        except Exception as e:
            print(f"[AI润色] 第{attempt + 1}次请求失败: {e}")
            if attempt < max_retries:
                time.sleep(1)
                continue
            else:
                print(f"[AI润色] 所有重试失败，返回原文本")
                return [text]

    return [text]


def _extract_content_from_response(data: dict) -> str | None:
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