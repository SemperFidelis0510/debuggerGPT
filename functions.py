import json
import os
import sys
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

# Create a Mode object
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


async def analyze_folder(folder_path):
    file_dict = {}
    for root, dirs, files in os.walk(folder_path):
        file_dict[root] = files
    return file_dict


async def execute_command(command, env_name, shell):
    if env_name:
        command = f"conda run -n {env_name} {command}"
    try:
        # Write the command to the shell's stdin and flush to ensure it's sent
        shell.stdin.write((command + '\n').encode())
        shell.stdin.flush()

        # Read the output from the shell's stdout
        output = shell.stdout.readline().decode()

        # Keep reading lines from the shell's stdout until we reach an empty line
        while True:
            line = shell.stdout.readline().decode()
            if line == '':
                break
            output += line

        return quart.Response(response=json.dumps({"output": output}), status=200)
    except Exception as e:
        return quart.Response(response=json.dumps({"error": str(e)}), status=400)


async def run_script(script_path, env_name, args_str):
    command = f"conda run -n {env_name} python {script_path} {args_str}"  # Include the arguments in the command
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        processed_output = remove_ansi_escape_sequences(result.stdout)
        return quart.Response(response=json.dumps({"output": processed_output, "error": result.stderr}), status=200)
    except subprocess.CalledProcessError as e:
        return quart.Response(response=json.dumps({"error": e.stderr, "output": e.output, "stderr": str(e)}),
                              status=400)


async def get_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            content = f.read()
        return content
    else:
        return 404


async def edit_file(filename, fixes, method):
    start_line = end_line = 0
    if method == "replace" and len(fixes) != 1:
        return Response(response='Error: For "replace" method, only one fix should be provided', status=400)

    lines = []
    if method != "new" and os.path.exists(filename):
        with open(filename, 'r') as f:
            lines = f.readlines()
            if lines[-1][-1] != '\n':
                lines[-1] += '\n'

    for fix in fixes:
        if len(fix["lines"]) == 2:
            start_line, end_line = fix["lines"]
        elif len(fix["lines"]) == 1:
            start_line = end_line = fix["lines"][0]
        elif isinstance(fix["lines"], int):
            start_line = end_line = fix["lines"]

        new_code = fix["code"]
        if "indentation" in fix:
            indentation = fix["indentation"]
        else:
            indentation = ''
        indented_code = '\n'.join([indentation + line for line in new_code.split('\n')])

        if method == "replace":
            if end_line > len(lines):
                lines.extend(['\n'] * (end_line - len(lines)))
            lines[start_line - 1:end_line] = [indented_code + '\n']
        elif method == "insert":
            lines.insert(start_line - 1, indented_code + '\n')
        elif method == "new":
            lines = [indented_code + '\n']
        elif method == "append":
            lines.append(indented_code + '\n')


    with open(filename, 'w') as f:
        f.writelines(lines)

    if filename.endswith('.py'):
        format_file_in_place(Path(filename), fast=False, mode=mode)

    return Response(response='OK', status=200)


def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


class Instructor:
    def __init__(self):
        self.tutorials = {}
        self.tut_counter = {}
        self.passed = {}
        self.plan_stage = 0
        self.plan_depth = 5
        self.one_time = ['init']

        self.load_instructions()

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            return self.teach(args[0])
        else:
            return None

    def load_instructions(self):
        instructions_dir = 'ai_instructions'
        for filename in os.listdir(instructions_dir):
            if filename.endswith('.txt'):
                tutorial_name = filename[:-4]
                with open(os.path.join(instructions_dir, filename), 'r') as file:
                    instructions = file.read()
                self.tutorials[tutorial_name] = instructions
                self.passed[tutorial_name] = False
                self.tut_counter[tutorial_name] = 0

    def teach(self, subject):
        self.done(subject)
        if subject == 'plan':
            self.plan_stage += 1
            if self.plan_stage >= self.plan_depth:
                return ''
        return self.tutorials[subject]

    def done(self, subject):
        self.tut_counter[subject] += 1
        self.passed[subject] = True
        if (subject == 'edit_file') and (self.tut_counter[subject] >= 3):
            self.tut_counter[subject] = 0
            self.passed[subject] = False
