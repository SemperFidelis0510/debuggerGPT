import json
import os
import subprocess
import quart
from quart import Response
import re
import requests
import ast
from radon.complexity import cc_visit
from radon.metrics import h_visit
from pylint import epylint as lint
import shutil
from pathlib import Path
from black import format_file_in_place, Mode, TargetVersion

mode = Mode(
    target_versions={TargetVersion.PY38},
    line_length=88,
    string_normalization=True,
    experimental_string_processing=False,
)


async def initialize_plugin(env_name):
    envs = subprocess.check_output(['conda', 'env', 'list']).decode('utf-8')
    if env_name not in envs:
        subprocess.run(['conda', 'create', '-n', env_name, 'python=3.10'], check=True)


async def create_plugin(destination_path='codes'):
    if destination_path == 'codes':
        destination_path = os.path.join(os.getcwd(), 'codes')
    template_path = os.path.join(os.getcwd(), 'templates/gpt_plugin')

    if not os.path.exists(destination_path):
        os.makedirs(destination_path)
    if not os.path.exists(os.path.join(destination_path, 'main.py')):
        for filename in os.listdir(template_path):
            src_file = os.path.join(template_path, filename)
            dst_file = os.path.join(destination_path, filename)
            if os.path.isfile(src_file):
                shutil.copy(src_file, dst_file)
    return destination_path


async def analyze_code(code_path, scope_level):
    with open(code_path, 'r') as f:
        code = f.read()
    tree = ast.parse(code)
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    dependencies = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    code_analysis = {
        'length': len(code.split('\n')),
        'functions': functions,
        'code': code,
        'dep': dependencies
    }
    if scope_level > 1:
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        comments = [node.s for node in ast.walk(tree) if isinstance(node, ast.Str)]
        code_analysis.update({
            'classes': classes,
            'comments': comments,
        })
    if scope_level > 2:
        (pylint_stdout, pylint_stderr) = lint.py_run(code_path, return_std=True)
        pylint_output = pylint_stdout.getvalue()
        cyclomatic_complexity = cc_visit(code)
        halstead_metrics = h_visit(code)
        code_analysis.update({
            'pylint_output': pylint_output,
            'cyclomatic_complexity': cyclomatic_complexity,
            'halstead_metrics': halstead_metrics,
        })

    return code_analysis


async def download_file(url, local_path):
    if os.path.isdir(local_path):
        filename = url.split('/')[-1]
        full_path = os.path.join(local_path, filename)
    else:
        full_path = local_path
    response = requests.get(url)
    with open(full_path, 'wb') as f:
        f.write(response.content)
    return Response(response='File downloaded successfully', status=200)


async def analyze_folder(folder_path, depth=None):
    file_dict = {}
    current_depth = folder_path.count(os.sep)
    for root, dirs, files in os.walk(folder_path):
        if depth and (root.count(os.sep) - current_depth >= depth):
            dirs[:] = []  # Don't recurse any deeper
        file_dict[root] = files
    return file_dict


async def read_output(stream, output_list):
    while True:
        line = await stream.readline()
        if not line:
            break
        output_list.append(line.decode().rstrip())


async def execute_command(command, env_name=None):
    if env_name is not None:
        python_path = f"C:\\Users\\Bar\\.conda\\envs\\{env_name}\\python.exe"
        command = command.replace("python", python_path)

    shell_process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Get the output and error from the command
    stdout, stderr = shell_process.communicate()

    # Decode the output and error from bytes to strings
    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')

    stdout_lines = stdout.split('\r\n')  # Include all lines of output
    stderr_lines = stderr.split('\r\n')

    if stderr:
        return Response(response=json.dumps({"error": stderr_lines, "output": stdout_lines}), status=400)
    return Response(response=json.dumps({"output": stdout_lines}), status=200)


async def get_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            raw_content = f.readlines()

        content = {0: ''}
        i = 1
        for line in raw_content:
            content[i] = line.replace('\n', '')
            i += 1

        return content
    else:
        return 404


async def edit_file(filename, fixes, erase=False):
    dir_name = os.path.dirname(filename)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    if erase:
        lines = []
    elif os.path.exists(filename):
        with open(filename, 'r') as f:
            lines = f.readlines()
            if lines and lines[-1][-1] != '\n':
                lines[-1] += '\n'
    else:
        return Response(response='Error: File does not exist', status=400)

    for fix in fixes:
        start_line = fix["start_line"]
        end_line = fix.get("end_line", None)
        new_code = fix["new_code"]
        replace = fix.get("replace", False)

        indentation = fix.get("indentation", '')
        indented_code = '\n'.join([indentation + line for line in new_code.split('\n')])

        if replace:
            if start_line > len(lines):
                lines.extend(['\n'] * (start_line - len(lines)))
            if end_line is not None and end_line < len(lines):
                lines = lines[:start_line - 1] + [indented_code + '\n'] + lines[end_line:]
            else:
                lines[start_line - 1] = indented_code + '\n'
        else:
            lines.insert(start_line - 1, indented_code + '\n')

    with open(filename, 'w') as f:
        f.writelines(lines)

    if filename.endswith('.py'):
        format_file_in_place(Path(filename), fast=False, mode=mode)

    new_content = {0: ''}
    i = 1
    with open(filename, 'r') as f:
        new_content0 = f.readlines()
    for line in new_content0:
        new_content[i] = line.replace('\n', '')
        i += 1

    return Response(response=json.dumps({"content": new_content}), status=200)


def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    ansi_escape = ansi_escape.sub('', text)
    ansi_escape.replace('\n', '')
    ansi_escape.replace('\r', '')
    return ansi_escape
