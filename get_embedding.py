from llm import Embedding
import pandas as pd
import json
import os
import traceback

package_json = [i for i in os.listdir('rag_data') if 'json' in i]

all_json = []
for i in package_json:
    json_path = os.path.join('rag_data',i)

    with open(json_path,encoding='utf8') as f:
        data = json.load(f)

        for j in data:
            j['package'] = i.replace('.json','')

            all_json.append(j)


def batch_generator(input_list, batch_size):
    for i in range(0, len(input_list), batch_size):
        yield input_list[i:i + batch_size]

ebd = []
for text_batch in batch_generator(all_json, 100):
    try:
        text_batch2 = [str(i['name']) for i in text_batch]

        es = Embedding(text_batch2)

        for dic,e in zip(text_batch,es):
            dic['name_embedding'] = e

        ebd.extend(text_batch)
        if len(ebd)%1000==0:
            pd.DataFrame(ebd).to_csv('rag_data/name_rag_search.csv', index=0)

    except:
        traceback.print_exc()


pd.DataFrame(ebd).to_csv('rag_data/name_rag_search.csv', index=0)