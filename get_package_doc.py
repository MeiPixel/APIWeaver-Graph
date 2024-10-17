
py_code = '''
import inspect
import [pkg]  # 替换为你要检查的包名

def list_members(module, module_name):
    members_list = []
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            class_doc = inspect.getdoc(obj)
            class_info = {
                'type': 'class',
                'name': f"{module_name}.{name}",
                'documentation': class_doc
            }
            members_list.append(class_info)
            for class_name, class_obj in inspect.getmembers(obj):
                if inspect.isfunction(class_obj) or inspect.ismethod(class_obj):
                    method_doc = inspect.getdoc(class_obj)
                    method_info = {
                        'type': 'method',
                        'name': f"{module_name}.{name}.{class_name}",
                        'documentation': method_doc
                    }
                    members_list.append(method_info)
        elif inspect.isfunction(obj):
            func_doc = inspect.getdoc(obj)
            func_info = {
                'type': 'function',
                'name': f"{module_name}.{name}",
                'documentation': func_doc
            }
            members_list.append(func_info)
    return members_list

members_data = list_members([pkg], [pkg].__name__)

#
# import json
#
# with open('rag_data/[pkg].json','w',encoding='utf8')  as f:
#     json.dump(members_data,f)
# # 打印结果
for member in members_data:
    print(member)
'''

for i in ['cdlib','graspologic','igraph','karateclub','networkx','littleballoffur']:
    exec(py_code.replace('[pkg]',i))