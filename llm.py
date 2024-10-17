import requests
import functools
import time
import re
import json
from openai import OpenAI


openai_client = OpenAI(
    api_key='',
    base_url=""
)


def try_n_times(n):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(n):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    if i == n - 1:  # 当达到最大尝试次数时，抛出异常
                        raise e
                    print(f"Attempt {i + 1} failed. Retrying...")
                    time.sleep(10)  # 可选，等待1秒后重试

        return wrapper

    return decorator

def super_eval(json_str, try_num=0):
    if try_num > 3:
        return 'json格式错误'
    json_str = json_str.replace('：', ':')
    try:
        all_json = re.findall('```json(.*?)```', json_str, re.DOTALL)
        if all_json:
            try:
                return eval(all_json[-1])
            except:

                return json.loads(all_json[-1])
        if '```json' in json_str:
            json_str = json_str.replace('```json', '')
        json_str = json_str.replace('```', '')
        try:
            return eval(json_str)
        except:
            return json.loads(json_str)
    except:
        text = llm(f"输出以下内容的json部分并修复成正确格式备注仅仅输出最后的json:```{json_str}```")
        try_num += 1
        return super_eval(text, try_num)

import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")
@try_n_times(5)
def llm(prompt, print_str=True):
    if len(enc.encode(str(prompt))) > 20000:
        raise ValueError('长度受限制')
    if isinstance(prompt, str):
        messages = [{'role': 'user', 'content': prompt}]
    elif isinstance(prompt, list):
        if len(prompt) > 15:
            raise ValueError('太长了')
        messages = prompt
    else:
        raise ValueError
    url = 'https://？？？？？.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-05-01-preview'
    headers = {
        "Content-Type": "application/json",
        "api-key": ''
    }

    payload = {
        "model": 'gpt-4o',
        "messages": messages,
        "temperature": 0.9,
        "top_p": 1,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    try:
        answer = response.json()['choices'][0]['message']['content']
        if isinstance(prompt, list):
            prompt.append({"role": "assistant", "content": answer})
        if print_str:
            print(answer)
            print(response.json()['usage'])
        return answer
    except:
        print(response.json())
        raise ValueError


@try_n_times(3)
def llm_eval(content, check_function=None):
    if check_function:
        llm_res = llm(content)

        res = super_eval(llm_res)
        if check_function(json.dumps(res)):
            return res
        else:
            messages = [{'role': 'user', 'content': content},
                        {'role': 'assistant', 'content': llm_res},
                        {'role': 'user',
                         'content': 'json格式化检查未通过，请严格按照json格式输出,并且将json内容放在```json\n```内'}
                        ]
            llm_res = llm(messages)
            res = super_eval(llm_res)
            if check_function(json.dumps(res)):
                return res
            else:
                raise ValueError
    else:
        return super_eval(llm(content))

def Embedding(x):
    if isinstance(x, str):
        return openai_client.embeddings.create(input=x, model='text-embedding-3-small').data[0].embedding
    if isinstance(x, list):
        embeddings = openai_client.embeddings.create(input=x, model='text-embedding-3-small').data
        return [i.embedding for i in embeddings]

