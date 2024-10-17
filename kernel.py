    import json
import traceback
from pprint import pprint
import queue
import re
from subprocess import PIPE
from typing import Literal
import time
import jupyter_client
from dataclasses import dataclass
from typing import Any
from uuid import uuid1


@dataclass
class ToolObservation:
    content_type: str
    text: str
    image_url: str | None = None
    role_metadata: str | None = None
    metadata: Any = None


IPYKERNEL = 'my_kernel'  # Ensure this matches the name of your installed kernel

ANSI_ESCAPE = re.compile(r'(\x9B|\x1B\[|\u001b\[)[0-?]*[ -/]*[@-~]')
CODE = re.compile(r'```([^\n]*)\n(.*?)```')

clear_list = [
    "Note: to be able to use all crisp methods, you need to install some additional packages:  {'bayanpy', 'graph_tool', 'wurlitzer', 'infomap'}",
    "Note: to be able to use all crisp methods, you need to install some additional packages:  {'pyclustering', 'ASLPAw'}",
    "Note: to be able to use all crisp methods, you need to install some additional packages:  {'wurlitzer', 'infomap'}",
]


def clean_traceback(traceback_list):
    cleaned_traceback = []
    for line in traceback_list:
        # 去掉ANSI转义字符
        clean_line = re.sub(r'\x1b\[.*?m', '', line)
        cleaned_traceback.append(clean_line)
    return '\n'.join(cleaned_traceback)


def clean_output(output_list):
    output_list = [i for i in output_list if i]
    for i in range(len(output_list)-2,-1,-1):
        s = output_list[i]
        output_list[i] = ''
        if s not in '\n'.join(output_list):
            output_list[i] = s
    for i in range(len(output_list)-1):
        s = output_list[i]
        output_list[i] = ''
        if s.split('结果为:',1)[-1] not in '\n'.join(output_list):
            output_list[i] = s
    return output_list


class CodeKernel:
    def __init__(self,
                 kernel_name='kernel',
                 kernel_id=None,
                 kernel_config_path="",
                 python_path=None,
                 ipython_path=None,
                 init_file_path="./startup.py",
                 verbose=1):

        self.kernel_name = kernel_name
        self.kernel_id = kernel_id
        self.kernel_config_path = kernel_config_path
        self.python_path = python_path
        self.ipython_path = ipython_path
        self.init_file_path = init_file_path
        self.verbose = verbose
        self.cache_code = ''
        self.task_id = str(uuid1()).split('-', 3)[-1]
        self.cache_code_list = []

        if python_path is None and ipython_path is None:
            env = None
        else:
            env = {"PATH": self.python_path + ":$PATH", "PYTHONPATH": self.python_path}

        # Initialize the backend kernel
        self.kernel_manager = jupyter_client.KernelManager(kernel_name=IPYKERNEL,
                                                           connection_file=self.kernel_config_path,
                                                           exec_files=[self.init_file_path],
                                                           env=env)
        if self.kernel_config_path:
            self.kernel_manager.load_connection_file()
            self.kernel_manager.start_kernel(stdout=PIPE, stderr=PIPE)

        else:
            self.kernel_manager.start_kernel(stdout=PIPE, stderr=PIPE)


        # Initialize the code kernel
        self.kernel = self.kernel_manager.blocking_client()
        # self.kernel.load_connection_file()
        self.kernel.start_channels()
        print("Code kernel started.")

    def execute(self, code, add=True):
        if code.startswith('def') and code in self.cache_code:
            return '已经定义的函数，无需重复执行'
        all_msg_out = []
        all_msg_out_len = 0
        self.kernel.execute(code)
        try:
            # shell_msg = self.kernel.get_shell_msg(timeout=60)
            io_msg_content = self.kernel.get_iopub_msg(timeout=30)['content']
            while True:
                time.sleep(0.1)
                msg_out = io_msg_content
                if 'text' in msg_out:
                    all_msg_out.extend(msg_out['text'].split('\n'))
                elif 'traceback' in msg_out:
                    # all_msg_out = clean_output(all_msg_out)
                    raw = '\n'.join(all_msg_out)
                    if len(raw) > 1000:
                        msg = raw[:200] + '\n\n中间内容省略\n\n' + raw[-500:]
                    else:
                        msg = raw
                    msg+=clean_traceback(msg_out['traceback'])
                    return msg
                ### Poll the message
                try:
                    io_msg_content = self.kernel.get_iopub_msg(timeout=30)['content']
                    if 'execution_state' in io_msg_content and io_msg_content['execution_state'] == 'idle':
                        break
                except queue.Empty:
                    traceback.print_exc()
                    break
            msg = '\n'.join(all_msg_out)
            for i in clear_list:
                msg = msg.replace(i, '')
            return msg
        except Exception as e:
            print(e)
            traceback.print_exc()
            self.restart()
            return '代码有问题，已清空缓存区，请你从头编写代码'

    def execute_interactive(self, code, verbose=False):
        shell_msg = self.kernel.execute_interactive(code)
        if shell_msg is queue.Empty:
            if verbose:
                print("Timeout waiting for shell message.")
        self.check_msg(shell_msg, verbose=verbose)

        return shell_msg

    def inspect(self, code, verbose=False):
        msg_id = self.kernel.inspect(code)
        shell_msg = self.kernel.get_shell_msg(timeout=30)
        if shell_msg is queue.Empty:
            if verbose:
                print("Timeout waiting for shell message.")
        self.check_msg(shell_msg, verbose=verbose)

        return shell_msg

    def get_error_msg(self, msg, verbose=False) -> str | None:
        if msg['content']['status'] == 'error':
            try:
                error_msg = msg['content']['traceback']
            except:
                try:
                    error_msg = msg['content']['traceback'][-1].strip()
                except:
                    error_msg = "Traceback Error"
            if verbose:
                print("Error: ", error_msg)
            return error_msg
        return None

    def check_msg(self, msg, verbose=False):
        status = msg['content']['status']
        if status == 'ok':
            if verbose:
                print("Execution succeeded.")
        elif status == 'error':
            for line in msg['content']['traceback']:
                if verbose:
                    print(line)

    def shutdown(self):
        # Shutdown the backend kernel
        self.kernel_manager.shutdown_kernel()
        print("Backend kernel shutdown.")
        # Shutdown the code kernel
        self.kernel.shutdown()
        print("Code kernel shutdown.")

    def restart(self):
        # Restart the backend kernel
        self.kernel_manager.restart_kernel()
        # print("Backend kernel restarted.")

    def interrupt(self):
        # Interrupt the backend kernel
        self.kernel_manager.interrupt_kernel()
        # print("Backend kernel interrupted.")

    def is_alive(self):
        return self.kernel.is_alive()


def run_code(python_str, code_kernel, iscode=False):
    if iscode:
        val = code_kernel.execute(python_str)
        print(val)
        return val
    # 使用正则表达式搜索代码块
    match = re.search(r'```python(.*?)```', python_str, re.DOTALL)

    if match:
        python_str_run = match.group(1)
        python_str_run = re.sub('-> (str|list|dict|int|float)\s*\n', '\n', python_str_run)
        val = code_kernel.execute(python_str_run)
        print(val)
        return val
    else:
        match = re.search(r'```json(.*?)```', python_str, re.DOTALL)
        if match:
            print('json结果并未保存到代码：',match.group(1))
        return '没有使用正则表达式搜索到python代码，请使用```python ```代码输出'




if __name__ == '__main__':
    ck = CodeKernel()
    res = run_code('print(123)',ck,iscode=True)

    print(res)