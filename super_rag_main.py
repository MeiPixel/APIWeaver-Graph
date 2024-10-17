import json
import re
import os
from kernel import CodeKernel, run_code
from llm import llm4, super_eval
from tools.search import search_data,recall_doc_by_function_name


import threading
import functools


class TimeoutException(Exception):
    pass

def timeout_decorator(seconds):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [TimeoutException(f"Function '{func.__name__}' timed out after {seconds} seconds")]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    result[0] = e

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(seconds)
            if thread.is_alive():
                raise TimeoutException(f"Function '{func.__name__}' timed out after {seconds} seconds")
            if isinstance(result[0], Exception):
                raise result[0]
            return result[0]

        return wrapper

    return decorator

def get_error_file(error_message):
    # 正则表达式匹配错误消息中的文件路径
    file_path_regex = r"No such file or directory: '([^']+)'"

    # 使用正则表达式查找文件路径
    match = re.search(file_path_regex, error_message)
    if match:
        file_path = match.group(1)
        file_name = os.path.basename(file_path)
        return file_name


def handle_resp(resp,messages):

    json_str = '''
[
    {
        "package": "The name of the package you want to search for", # Choose one from networkx, igraph, cdlib, karateclub, littleballoffur, graspologic, or 'all' to search all
        "name":  ["function_name1","function_name2"],      #If you want to search for a specific function, you can fill in the function name here,
        "key_words": ["key1", "key2", ...], # The keywords you need to search for, as comprehensive as possible from the documentation
        "documentation": "Functional description, use vector search for documentation. You should write as close to the function description as possible here"
    },
    {
        "package": "The name of the package you want to search for",
        "name": ["function_name1","function_name2"],
        "key_words": ["key1", "key2", ...],
        "documentation": "Functional description, use vector search for documentation"
    },
    ...
]
'''
    if 'Traceback' in resp:
        if len(resp)>3000:
            resp =resp[:3000]
        prompt = f'''
Your code has produced an error message:
```
{resp}
```
To rectify the code, you will need to conduct a query. There are two query modes to choose from.
Mode 1: Applicable to parameter errors
If the error is a result of incorrect function invocation, please utilize the `inspect.getsource` method to examine the source code of the function where the error occurs. You should enclose the code for viewing the function's source code within ```python ```.
Mode 2: Applicable to import errors
If the error is due to the inability to locate the correct package and function, please formulate a search query. I have established a Python documentation search database that encompasses the following fields:
- package: the name of the package
- documentation: the documentation for functions or classes
- name: the path of the function, e.g., networkx.DiGraph.add_nodes_from
- type: method/class
You are required to output in the following JSON format:
```json
{json_str}
```
I will verify the correctness of the JSON format and subsequently furnish you with the search outcomes. From the results provided, identify the suitable function for reprogramming.
Please select the mode and then supply either the python code or the JSON string.
'''
        messages.append({'role':'user','content':prompt})
        if len(messages) > 6:
            messages = messages[:4] + messages[-2:]
        resp = llm4(messages)
        if '```python' in resp and 'inspect.getsource' in resp:
            search_kernel = CodeKernel()
            doc = run_code(resp,search_kernel)
            search_kernel.shutdown()
        elif '```python' in resp:
            return resp
        elif '```json' in resp:
            query_list = super_eval(resp)
            li = []
            for i in query_list:
                li.extend(search_data(i))
            doc = ''
            for i in li:
                doc += f'''
-----
method path:`{i['name']}`
documentation:
```
{i['documentation']}
```
'''

        else:
            return

        prompt = f'''```{doc}```\nThe above is the document found. Please modify the code based on the document'''
        messages.append({'role': 'user', 'content': prompt})
        resp = llm4(messages)
        return resp


def get_q_type(q_type):
    dic =     {"True":"If the question does not require it, only output True/False",
    'draw':"The image needs to be saved. Print key information before drawing, and print the save path after drawing",
    'calculations': "Keep the calculation questions to two decimal places. If there are no special requirements, only output the answer",
    'multi':'Multiple question types mixed, with two answers separated by two line breaks'}
    doc = []
    for k,v in dic.items():
        if k in q_type:
            doc.append(v)

    return '\n'.join(doc)


@timeout_decorator(100)
def write_code(item):

    sys_prompt = f'''
This is an AI programming competition that tests your ability to correctly invoke functions and ensure programming correctness. Users will input function documentation, problem statements, question types, and question requirements.
User files are by default stored in the './data' path, and your code files should be saved in the './result' path. You are expected to think before you code, and output in the following format:
Thought Process:
```md
[Carefully consider the requirements, data, expected results, and the methods chosen]
```
Code:
```python
[Your code]
```
Important: Strictly follow the data and output requirements of the topic
'''
    messages = [{'role': 'system', 'content': sys_prompt},
    {'role': 'user', 'content': f'''
--doc--
{recall_doc_by_function_name(item['packages'])}
-------
--topic--
{item['question']}
--------
-topic type-
{item['problem_type']}
{get_q_type(item['problem_type'])}
---
'''}]
    kernel = CodeKernel()
    run_code('''
import numpy as np
import warnings
import pandas as pd
np.set_printoptions(precision=2)
np.set_printoptions(edgeitems=5, threshold=10)
warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 10)
pd.set_option('display.large_repr', 'truncate')
pd.set_option('display.precision', 2)
''',True)
    print(messages)
    code_message = llm4(messages)
    res = run_code(code_message, kernel)
    file_error = get_error_file(res)
    if file_error and file_error not in item['question'] and re.search('Final requirement.{1,3}Code',code_message):
        kernel.shutdown()
        return code_message, messages

    for _ in range(5):
        new_message = handle_resp(res,messages)
        if new_message is None:
            break
        else:
            res = run_code(new_message, kernel)
            # print(Colors.BG_MAGENTA + res + Colors.RESET)

    kernel.shutdown()
    return res,messages


from concurrent.futures import ThreadPoolExecutor, as_completed

with open('answer13.json', encoding='utf8') as f:
    ids = [json.loads(i)['ID'] for i in f]
with open('Final_Example_rag3.json', encoding='utf8') as f:
    data_list = json.load(f)
    data_list = [i for i in data_list if i['ID'] not in ids]


def process_item(item):
    try:
        answer, messages = write_code(item)
        item['answer'] = answer
        item['messages'] = messages
        match = re.search(r'```python(.*?)```', messages[-1]['content'], re.DOTALL)
        if match:
            python_str_run = match.group(1)
            item['code'] = python_str_run
        return item
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def main():
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_item = {executor.submit(process_item, i): i for i in data_list}
        for future in as_completed(future_to_item):
            item = future.result()
            if item is not None:
                with open('answer13.json', 'a', encoding='utf8') as f:
                    f.write(json.dumps(item, ensure_ascii=False))
                    f.write('\n')


if __name__ == '__main__':
    main()