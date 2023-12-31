import json
import os
import sys
import subprocess
from urllib.parse import unquote
import quart
from quart import request, Response
from quart_cors import cors
import re
import requests
import ast
import sounddevice as sd
import numpy as np
from google.cloud import speech
import pyttsx3
import traceback
from radon.complexity import cc_visit
from radon.metrics import h_visit
from pylint import epylint as lint
from memory import Memory

app = quart.Quart(__name__)
app = cors(app, allow_origin="https://chat.openai.com")
explained = {'code_analysis': False}
memory = Memory()


# todo: add plan JSON.
# todo: add instruction JSON. maybe divide over all endpoints
# todo: add init data to memory
# todo: refactor after code modification
# todo: analyze folder
# todo: add auth
# todo: automate plugin improvement
# todo: add plugin template
# todo: check through memory, the user prompts.
# todo: improve instructions
# todo: add 'file not found' response where needed
# todo: continuous shell


@app.post("/initialize")
async def initialize_plugin():
    request_data = await quart.request.get_json(force=True)
    env_name = request_data.get("env_name", "debuggerGPT")
    memory['environ'] = env_name
    memory['w_dir'] = os.getcwd()
    try:
        # Check if the specified conda environment exists
        envs = subprocess.check_output(['conda', 'env', 'list']).decode('utf-8')
        if env_name not in envs:
            # Create the specified conda environment
            subprocess.run(['conda', 'create', '-n', env_name, 'python=3.10'], check=True)
        with open('ai_instructions/init.txt', 'r') as file:
            instructions = {
                "message": "Initialization successful. The conda environment '" + env_name + "' is ready to use.",
                "instructions": file.read()
            }
        return quart.Response(response=json.dumps(instructions), status=200)
    except subprocess.CalledProcessError as e:
        return quart.Response(response=f'Error during initialization: {str(e)}', status=400)


@app.post("/speak")
async def speak():
    request_data = await quart.request.get_json(force=True)
    text = request_data.get("text", "")
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return quart.Response(response='OK', status=200)


@app.route("/memory", methods=["POST"])
async def remember():
    request_data = await request.get_json(force=True)
    key = request_data.get("key", "")
    value = request_data.get("value", "")
    alias = request_data.get("alias", False)
    nature = 'memory'
    if alias:
        nature = 'alias'
    memory.remember(key, value, nature=nature)
    return Response(response='OK', status=200)


@app.route("/memory/<key>", methods=["GET"])
async def recall(key):
    key = unquote(key)
    All = quart.request.args.get("all", "False").lower() == "true"
    if All:
        return Response(response=json.dumps({"value": memory.to_json()}), status=200)
    if key in memory:
        return Response(response=json.dumps({"value": memory[key]}), status=200)
    else:
        return Response(response='Key not found', status=400)


@app.post("/listen")
async def listen():
    # Record audio
    duration = 10  # seconds
    fs = 44100  # Sample rate
    channels = 1  # Number of channels
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=channels)
    sd.wait()  # Wait for the recording to finish

    # Transcribe audio to text
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=np.array(myrecording).tobytes())
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=fs,
        language_code="en-US",
    )
    response = client.recognize(config=config, audio=audio)

    # Extract the transcription and return it
    for result in response.results:
        return {"transcription": result.alternatives[0].transcript}


@app.get("/analysis/code")
async def analyze_code():
    try:
        code_path = quart.request.args.get("code_path", "")
        scope_level = int(quart.request.args.get("scope_level", "2"))
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
        if not explained['code_analysis']:
            with open('ai_instructions/code_analysis.txt', 'r') as file:
                instructions = file.read()
        else:
            instructions = ''
        return quart.Response(response=json.dumps({"analysis": code_analysis, "instructions": instructions}),
                              status=200)
    except Exception as e:
        tb_str = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
        print("".join(tb_str))  # Print the traceback
        return quart.Response(response=json.dumps({"error": str(e)}), status=400)


@app.post("/download_file")
async def download_file():
    request_data = await quart.request.get_json(force=True)
    url = request_data.get("url", "")
    local_path = request_data.get("local_path", "")
    filename = url.split("/")[-1]  # Extract the filename from the URL
    full_path = os.path.join(local_path, filename)  # Combine the local path with the filename
    response = requests.get(url)
    with open(full_path, 'wb') as f:
        f.write(response.content)
    return quart.Response(response='File downloaded successfully', status=200)


@app.get("/analysis/folder")
async def analyze_folder():
    try:
        folder_path = quart.request.args.get("folder_path", "")
        file_dict = {}
        for root, dirs, files in os.walk(folder_path):
            file_dict[root] = files
        memory.remember(folder_path, file_dict, nature='data')
        with open('ai_instructions/folder_analysis.txt', 'r') as file:
            instructions = file.read()
            instructions = instructions.replace('{folder_path}', os.path.basename(folder_path))
        return quart.Response(response=json.dumps({"analysis": file_dict, "instructions": instructions}), status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return quart.Response(response=json.dumps({"error": "".join(tb_str)}), status=400)


@app.post("/execute")
async def execute_command():
    request_data = await quart.request.get_json(force=True)
    command = request_data.get("command", "")
    env_name = request_data.get("env_name", None)
    if env_name:
        command = f"conda run -n {env_name} {command}"
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        return quart.Response(response=json.dumps({"output": result.stdout}), status=200)
    except subprocess.CalledProcessError as e:
        return quart.Response(response=json.dumps({"error": str(e), "output": e.output}), status=400)


@app.post("/run_script")
async def run_script():
    request_data = await quart.request.get_json(force=True)
    env_name = request_data.get("env_name", "debuggerGPT")  # Default to 'debuggerGPT' if not specified
    script_path = request_data.get("script_path", "")
    args = request_data.get("args", [])  # Get the arguments from the request data
    args_str = " ".join(args)  # Convert the list of arguments into a string
    command = f"conda run -n {env_name} python {script_path} {args_str}"  # Include the arguments in the command
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        processed_output = remove_ansi_escape_sequences(result.stdout)
        return quart.Response(response=json.dumps({"output": processed_output, "error": result.stderr}), status=200)
    except subprocess.CalledProcessError as e:
        return quart.Response(response=json.dumps({"error": e.stderr, "output": e.output, "stderr": str(e)}),
                              status=400)


@app.get("/files/<path:filename>")
async def get_file(filename):
    filename = unquote(filename)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            content = f.read()
        return quart.Response(response=json.dumps({"content": content}), status=200)
    else:
        return quart.Response(response='File not found', status=404)


@app.post("/files/<path:filename>")
async def edit_file(filename):
    try:
        request_data = await quart.request.get_json(force=True)
        filename = unquote(filename)
        fixes = request_data.get("fixes", [])
        method = request_data.get("method", "replace")

        if method == "replace" and len(fixes) != 1:
            return quart.Response(response='Error: For "replace" method, only one fix should be provided', status=400)

        lines = []
        if method != "new" and os.path.exists(filename):
            with open(filename, 'r') as f:
                lines = f.readlines()

        for fix in fixes:
            if len(fix["lines"]) == 2:
                start_line, end_line = fix["lines"]
            elif len(fix["lines"]) == 1:
                start_line = end_line = fix["lines"][0]

            new_code = fix["code"]
            indentation = fix["indentation"]
            indented_code = '\n'.join([indentation + line for line in new_code.split('\n')])

            if method == "replace":
                lines[start_line - 1:end_line] = [indented_code + '\n']
            elif method == "insert":
                lines.insert(start_line - 1, indented_code + '\n')
            elif method == "new":
                lines = [indented_code + '\n']

        with open(filename, 'w') as f:
            f.writelines(lines)

        if filename.endswith('.py'):
            subprocess.run(['black', filename], check=True)

        return quart.Response(response='OK', status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        return quart.Response(response="".join(tb_str), status=500)


@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')


@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("./.well-known/ai-plugin.json") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/json")


@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/yaml")


@app.after_request
async def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = 'https://chat.openai.com'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response


@app.route("/files/<path:filename>", methods=['OPTIONS'])
async def options_files(filename):
    response = quart.Response(response='', status=200)
    response.headers['Access-Control-Allow-Origin'] = "https://chat.openai.com"
    response.headers['Access-Control-Allow-Headers'] = 'content-type,openai-conversation-id,openai-ephemeral-user-id'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    return response


def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def main():
    app.run(debug=True, host="0.0.0.0", port=5003)


if __name__ == "__main__":
    main()
