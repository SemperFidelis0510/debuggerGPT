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
import time
import openai

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


async def read_output(stream, output_list):
    while True:
        line = await stream.readline()
        if not line:
            break
        output_list.append(line.decode().rstrip())


async def execute_command(command, env_name=None):
    if env_name is not None:
        command = f"conda activate {env_name} && {command}"

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

    stdout_lines = stdout.split('\r\n')[4:]
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

    with open(filename, 'w') as f:
        f.writelines(lines)

    if filename.endswith('.py'):
        format_file_in_place(Path(filename), fast=False, mode=mode)

    with open(filename, 'r') as f:
        new_content = f.read()

    return Response(response=json.dumps({"content": new_content}), status=200)


def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    ansi_escape = ansi_escape.sub('', text)
    ansi_escape.replace('\n', '')
    ansi_escape.replace('\r', '')
    return ansi_escape


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


class Code:
    def __init__(self, code='', output=None, error=None, path=None):
        self.code = code
        self.code_lines = code.split('\n')
        self.output = output
        self.error = error
        self.fixes = []
        self.path = ''
        self.debug_model = 'gpt-4'

        if path is not None:
            self.from_file(path)

    def to_json(self):
        return {
            'code': self.code,
            'output': self.output,
            'error': self.error
        }

    def load(self, path):
        with open(path, 'r') as file:
            self.code = file.read()
            lines = file.readline()

        i = 0
        for line in lines:
            i += 1
            self.code_lines[i] = line.replace('\n', '')

    @staticmethod
    def from_json(json_obj):
        return Code(json_obj['code'], json_obj['output'], json_obj['error'])

    def fix(self, lines, new_code):
        new_code = new_code.split('\n')
        if len(lines) == 1:
            lines = [lines[0], lines[0]]
        elif len(lines) == 0:
            if new_code == '':
                print('No fix is needed')
                return
            else:
                print('A new code was given, but instructions of where to put it are missing.')
                return
        j = 0
        for i in range(lines[0] - 1, lines[1]):
            self.code_lines[i] = new_code[j]
            j += 1
        self.compile_code()

    def compile_code(self):
        self.code = '\n'.join(self.code_lines)

    def debug(self):
        input_json = self.to_json()
        prompt = f"""
        You are a code debugger. Here is the code, its output, and the error it produced:

        {json.dumps(input_json, indent=4)}

        Please identify the lines that need to be changed and suggest the new code to fix the issue. 
        Return your response in the following JSON format:

        {{
            "lines": [start_line, end_line],
            "new_code": "the new code",
            "align": number of idents at the beginning of this code snippet
        }}

        Note to yourself:
        - If there is only one line to be changed, the value on the key "lines", will be as [change_line, change_line], i.e both elements of the list will be the same single line.
        - Add nothing else to you response, send only the JSON.
        - The content of this prompt might be divided into a few parts, and be sent in a sequence. 
        Therefore, you should not send any response back, until you receive the total prompt. To know when the prompt is complete,
        expect the total content of this complete prompt to end with only the JSON with keys {{'code','output','error'}}.
        """

        prompt_parts = [prompt[i:i + 4097] for i in range(0, len(prompt), 4097)]
        responses = []
        for part in prompt_parts:
            response = openai.ChatCompletion.create(
                model=self.debug_model,
                messages=[
                    {"role": "system",
                     "content": "You are an experienced Python coder. You want to help the user debug his codes."},
                    {"role": "user",
                     "content": part}
                ]
            )
            responses.append(response['choices'][0]['message']['content'])

        content = ''.join(responses)

        try:
            # Use a regex to extract the JSON object from the response
            match = re.search(r'\{\s*"lines":\s*\[.*],\s*"new_code":\s*".*"\s*}', content, re.DOTALL)
            if match:
                json_str = match.group(0)
                response_json = json.loads(json_str)
            else:
                print("No JSON object found in the response.")
                response_json = {'lines': [], 'new_code': ''}
        except json.JSONDecodeError:
            print("The content could not be parsed as JSON.")
            response_json = {'lines': [], 'new_code': ''}

        self.fix(response_json["lines"], response_json["new_code"])

    def to_file(self):
        path = self.path
        # Rename the old file if it exists
        if os.path.exists(path):
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            os.rename(path, f"{path}_{timestamp}")

        with open(path, "w") as f:
            for line in self.code:
                f.write(line)

    def from_file(self, path):
        self.path = path
        # Read the code from the file
        with open(self.path, 'r') as f:
            self.code = f.read()

    def run(self, env_name, args=''):
        args = args.split(' ')
        try:
            # Run the Python file in the specified conda environment
            result = subprocess.run(['conda', 'run', '-n', env_name, 'python', self.path] + args,
                                    capture_output=True,
                                    text=True)
            self.output = result.stdout
            self.error = result.stderr
        except Exception as e:
            self.output = ''
            self.error = str(e)
