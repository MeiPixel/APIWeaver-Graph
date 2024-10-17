import re



def get_error_function(error_message):
    # 报错信息字符串


    # 正则表达式匹配文件路径
    file_paths = re.findall(r'File\s+(.*?):(\d+)', error_message)

    # 找到最后一个文件路径
    last_file_path,error_line_number = file_paths[-1]
    print(last_file_path)
    # 读取报错行数
    error_line_number = int(error_line_number)

    # 打开文件并读取内容
    with open(last_file_path, 'r') as file:
        lines = file.readlines()
    # 向上找到 def 作为起始点
    start_line_index = error_line_number - 1

    print(start_line_index)

    while start_line_index >= 0:
        if re.match(r'\s*def ', lines[start_line_index]):
            break
        start_line_index -= 1

    # 向下寻找 def class 或者是结束 作为终点
    end_line_index = start_line_index + 1
    while end_line_index < len(lines):
        if re.match(r'\s*(def |\bclass |\bif __name__)', lines[end_line_index]):
            break
        end_line_index += 1

    # 获取函数的所有内容
    function_contents = lines[start_line_index:end_line_index]

    # 输出函数内容
    return ''.join(function_contents)