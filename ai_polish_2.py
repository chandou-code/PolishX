import requests
import json
import time
import os

_config = None


def _load_config():
    global _config
    if _config is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            _config = json.load(f)
    return _config


def get_config():
    return _load_config()


_last_usage = None
_last_elapsed = None


def get_last_usage():
    return _last_usage


def get_last_elapsed():
    return _last_elapsed


def polish_text(text, max_retries=None):
    """
    润色文本的函数，返回候选结果列表
    """
    global _last_usage, _last_elapsed
    _last_usage = None
    _last_elapsed = None

    cfg = _load_config()
    if max_retries is None:
        max_retries = cfg['request']['max_retries']

    api_url = cfg['api']['url']
    api_key = cfg['api']['key']
    model_cfg = cfg['model']
    prompt_cfg = cfg['prompt']
    request_cfg = cfg['request']

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    start_time = time.time()

    user_prompt = prompt_cfg['user_template'].format(text=text)

    data = {
        "model": model_cfg['name'],
        "messages": [
            {
                "role": "system",
                "content": prompt_cfg['system']
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "max_tokens": model_cfg['max_tokens'],
        "temperature": model_cfg['temperature'],
        "top_p": model_cfg['top_p'],
        "top_k": model_cfg['top_k'],
        "stream": False,
        "stop_sequences": request_cfg['stop_sequences']
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=request_cfg['timeout']
            )
            response.raise_for_status()

            result = response.json()
            trace_id = response.headers.get('x-siliconcloud-trace-id', 'N/A')

            # 提取文本内容
            if "content" in result:
                for content_block in result["content"]:
                    block_type = content_block.get("type")

                    if block_type == "text":
                        text_content = content_block.get("text", "").strip()
                        if text_content:
                            _last_elapsed = time.time() - start_time
                            _last_usage = result.get('usage', {})
                            print(f"✅ 请求成功！Trace ID: {trace_id}")
                            print(f"📝 原文: {text}")
                            print(f"✨ 改写结果: {text_content}")
                            print(f"📊 Token使用情况: {_last_usage}")
                            print(f"⏱️  耗时: {_last_elapsed:.2f} 秒")
                            return [text_content]

                    elif block_type == "thinking":
                        thinking_content = content_block.get("thinking", "").strip()
                        print(f"⚠️ 模型进入思考模式: {thinking_content[:100]}...")
                        if attempt < max_retries - 1:
                            print(f"🔄 第 {attempt + 1} 次尝试失败，正在重试...")
                            time.sleep(1)
                            continue

            # 如果没有找到有效内容
            print(f"⚠️ 未找到有效文本内容，Trace ID: {trace_id}")
            print(f"📄 完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误详情: {e.response.text}")

            if attempt < max_retries - 1:
                print(f"🔄 正在重试...")
                time.sleep(2)
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"🔄 正在重试...")
                time.sleep(1)

    print(f"❌ 达到最大重试次数 ({max_retries})，请求失败")
    _last_elapsed = time.time() - start_time
    return []


def batch_polish(texts):
    """
    批量润色多个文本
    """
    results = []
    for i, text in enumerate(texts, 1):
        print(f"\n{'=' * 50}")
        print(f"处理第 {i}/{len(texts)} 条文本")
        result = polish_text(text)
        results.append({
            "original": text,
            "polished": result
        })
        time.sleep(1)  # 避免请求过快

    print(f"\n{'=' * 50}")
    print("📋 批量处理结果汇总:")
    for item in results:
        print(f"原文: {item['original']}")
        print(f"改写: {item['polished']}")
        print("-" * 30)

    return results


if __name__ == "__main__":
    # 单个文本测试
    test_text = "你朋友出不去也不管管吗"
    print("🎯 开始润色文本...")
    result = polish_text(test_text)

    if result:
        print(f"\n🎉 最终改写结果: {result}")

    # 批量测试（可选）
    # test_texts = [
    #     "组排真牛啊欺负人",
    #     "你们这配合太默契了",
    #     "打不过就加入呗"
    # ]
    # batch_results = batch_polish(test_texts)
