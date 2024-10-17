import json
import time

import pandas as pd
from scipy.spatial.distance import cosine
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.utils.discovery import all_functions

from llm import Embedding,enc,super_eval,llm4
import numpy as np
from copy import deepcopy
# 假设您的CSV文件名为data.csv
csv_file = 'rag_data/rag_search1.csv'

# 读取CSV文件
df = pd.read_csv(csv_file)
df['embedding'] = df['embedding'].apply(lambda x: np.array(eval(x)))
df['name_embedding'] = df['name_embedding'].apply(lambda x: np.array(eval(x)))





# 搜索函数
def search_data(search_json):
    # 过滤出目标包
    if search_json['package'] == 'all' or search_json[
        'package'] not in 'networkx, igraph, cdlib, karateclub, littleballoffur, graspologic':
        filtered_df = deepcopy(df)
    else:
        filtered_df = df[df['package'] == search_json['package']]

    if 'name' in search_json and search_json['name']:
        name_filtered_df = filtered_df[filtered_df['name'].apply(lambda x:bool([i for i in  search_json['name'] if i in str(x)]))]

        if len(name_filtered_df):
            return name_filtered_df.to_dict(orient='records')

    # 计算余弦相似度
    embedding = Embedding(search_json['documentation'])

    # 计算每个文档的余弦距离
    filtered_df['cosine_distance'] = filtered_df['embedding'].apply(
        lambda x: cosine(x, embedding)
    )

    # 计算关键词匹配数量
    key_words = search_json['key_words']
    filtered_df['key_words_count'] = filtered_df['documentation'].apply(
        lambda doc: len([word for word in key_words if word in str(doc)])
    )

    # 根据余弦距离和关键词匹配数量排序，距离越小越相似，关键词匹配数量越多越相关
    # 这里假设我们更重视关键词匹配，因此给关键词匹配更高的权重
    filtered_df['score'] = filtered_df['cosine_distance'] + (1 - filtered_df['key_words_count'] / len(key_words))
    print(filtered_df['score'])
    # 获取最匹配的三条数据
    top3_results = filtered_df.nsmallest(3, 'score')

    # 将结果转换为JSON格式
    top3_results = top3_results.drop(columns=['embedding', 'cosine_distance', 'key_words_count', 'score']).to_dict(
        orient='records')

    return top3_results



def question_rag(question):
    filtered_df = deepcopy(df)
    # 计算余弦相似度
    embedding = Embedding(question)

    # 计算每个文档的余弦距离
    filtered_df['score'] = filtered_df['embedding'].apply(
        lambda x: cosine(x, embedding)
    )


    # 获取最匹配的三条数据
    top3_results = filtered_df.nsmallest(5, 'score')

    # 将结果转换为JSON格式
    top3_results = top3_results.drop(columns=['embedding', 'score']).to_dict(
        orient='records')

    doc = ''
    for i in top3_results:
        doc += f'''
------
method path:`{i["name"]}`
method doc:
```{i["documentation"]}
```
'''

    return doc

def list2doc(doc_list):
    doc = []
    for sub_doc in doc_list:
        # print(f"---\n\n{sub_doc}\n\n---\n\n")
        doc.append(f'''
package:{sub_doc['package']}
method path:{sub_doc['name']}
method doc:
```
{sub_doc['documentation']}
```
''')

    return '\n'.join(set(doc))

def recall_doc_by_function_name(query_list):
    try:
        if isinstance(query_list, dict):
            query_list = [query_list]
        all_function_doc = []
        for query in query_list:
            function_doc = []
            if query['package'] == 'all' or query[
                'package'] in 'networkx, igraph, cdlib, karateclub, littleballoffur, graspologic':
                filtered_df = df[df['package'] == query['package']]
            else:
                break
            if 'method' in query and query['method']:
                def filter_function_name(x):

                    if '.' not in query['method'] in str(x).split('.'):
                        return True
                    else:
                        return  query['method'] in str(x)
                name_filtered_df = filtered_df[filtered_df['name'].apply(filter_function_name)]
                function_doc = name_filtered_df.to_dict(orient='records')
                if len(function_doc) > 5:
                    break

                if not function_doc:
                    def filter_function_doc(x):
                        return query['method'] in str(x)
                    name_filtered_df = filtered_df[filtered_df['documentation'].apply(filter_function_doc)]
                    function_doc = name_filtered_df.to_dict(orient='records')
                    if len(function_doc) > 5:
                        break
                    if not function_doc:
                        embedding = Embedding(query['method'])
                        filtered_df['score'] = filtered_df['embedding'].apply(
                            lambda x: cosine(x, embedding)
                        )
                        top1_results = filtered_df.nsmallest(1, 'score')
                        function_doc = top1_results.drop(columns=['embedding', 'score']).to_dict(
                            orient='records')

                if not function_doc:
                    print(query)
            all_function_doc.extend(function_doc)
        return list2doc(all_function_doc)
    except:
        return ''

def super_rag(question):
    prompt = '''
Your task is to analyze the required packages for the graph analysis functions mentioned in the problem. You should prioritize the use of the following six packages when considering graph analysis functionalities:
```networkx, igraph, cdlib, karateclub, littleballoffur, graspologic```
Please output the information in the following JSON format and ensure the output is enclosed within ```json ```:
```json
[
{"package":"xxx","method":"xxx","is_force":true/false,"is_out":true/false},
{"package":"xxx","method":"xxx","is_force":true/false,"is_out":true/false},
...
]
```
In this format, "package" must be one of the packages listed as options. "method" refers to the potential method that may be used. "is_force" indicates whether the use of a specific method is mandatory; if a problem explicitly requires a certain method, this should be set to true, otherwise, it should be false. "is_out" signifies whether the method is from a package outside the six mentioned above. You should list as many potential methods as possible. If a function is available in multiple packages, list them all. You will first analyze the functions required by the problem and then provide the JSON output.
'''
    messages = [{'role':'system','content':prompt},{'role':'user','content':question}]
    res = llm4(messages)
    return super_eval(res)


if __name__ == '__main__':

    with open('Final_Example_rag2.json',encoding='utf8') as f:
        data = json.load(f)
        for i in data:
            try:
                if len(enc.encode(recall_doc_by_function_name(i['packages'])))>5000:
                    print(i['packages'])
                print()
            except:
                ...

    # from concurrent.futures import ThreadPoolExecutor, as_completed
    # import json
    #
    # with open('../Final_Example.json', encoding='utf8') as f:
    #     data_list = json.load(f)
    #
    #
    # def process_item(item):
    #     try:
    #         packages = super_rag(item['question'])
    #         item['packages'] = packages
    #         return item
    #     except Exception as e:
    #         import traceback
    #         traceback.print_exc()
    #         return None
    #
    #
    # def main():
    #     with ThreadPoolExecutor(max_workers=5) as executor:
    #         future_to_item = {executor.submit(process_item, i): i for i in data_list}
    #         for future in as_completed(future_to_item):
    #             item = future.result()
    #             if item is not None:
    #                 with open('data1.json', 'a', encoding='utf8') as f:
    #                     f.write(json.dumps(item, ensure_ascii=False))
    #                     f.write('\n')
    # main()
    # time.sleep(10)
    #
    # with open('Final_Example_rag2.json','w',encoding='utf8') as f:
    #     json.dump(data_list,f,ensure_ascii=False)

