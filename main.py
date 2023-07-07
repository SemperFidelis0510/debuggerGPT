from quart import Quart, request, Response
from quart_cors import cors
import functions
import traceback
from memory import Memory
from urllib.parse import unquote
import json
import os
import sys
import subprocess
import quart

app = Quart(__name__)
app = cors(app, allow_origin="https://chat.openai.com")
explained = {'code_analysis': False, 'plan': False, 'init': False}
memory = Memory()
instructor = functions.Instructor()
ok = Response(response='OK', status=200)
shell_process = None


@app.post("/initialize")
async def initialize():
    global shell_process
    request_data = await request.get_json(force=True)
    try:
        env_name = request_data.get("env_name", "debuggerGPT")
        memory['environ'] = env_name
        memory['w_dir'] = os.getcwd()
        if shell_process is None:
            shell_process = subprocess.Popen(['cmd.exe'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

        await functions.initialize_plugin(env_name)

        response = {
            "message": "Initialization successful. The conda environment '" + env_name + "' is ready to use.",
            "guidelines": instructor('init')
        }
        return Response(response=json.dumps(response), status=200)
    except subprocess.CalledProcessError as e:
        error_response = {
            "error": str(e)
        }
        return Response(response=json.dumps(error_response), status=400, mimetype='application/json')


@app.get("/files/<path:filename>")
async def get_file(filename):
    try:
        content = await functions.get_file(filename)
        if content == 404:
            return Response(response='File not found', status=404)
        else:
            return Response(response=json.dumps({"content": content}), status=200, mimetype='application/json')
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500, mimetype='text/plain')


@app.post("/files/<path:filename>")
async def edit_file(filename):
    # if not instructor.passed('edit_file'):
    #     return Response(response=instructor('edit_file'), status=200)
    try:
        request_data = await request.get_json(force=True)
        fixes = request_data.get("fixes", [])
        method = request_data.get("method", "replace")
        return await functions.edit_file(filename, fixes, method)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.post("/execute")
async def execute_command():
    try:
        request_data = await request.get_json(force=True)
        command = request_data.get("command", "")
        env_name = request_data.get("env_name", None)
        return await functions.execute_command(command, env_name, shell_process)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.route("/memory", methods=["POST"])
async def remember():
    try:
        request_data = await request.get_json(force=True)
        key = request_data.get("key", "")
        value = request_data.get("value", "")
        nature = request_data.get("nature", 'memory')
        nature = 'memory'
        memory.remember(key, value, nature=nature)
        return Response(response='OK', status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.route("/memory/<key>", methods=["GET"])
async def recall(key):
    try:
        All = request.args.get("all", "False").lower() == "true"
        if All:
            return Response(response=json.dumps({"value": memory.to_json()}), status=200)
        if key in memory:
            return Response(response=json.dumps({"value": memory[key]}), status=200)
        else:
            return Response(response='Key not found', status=400)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.get("/analysis/folder")
async def analyze_folder():
    try:
        folder_path = request.args.get("folder_path", "")
        file_dict = await functions.analyze_folder(folder_path)
        folder_path = os.path.basename(folder_path)
        memory.remember(folder_path, file_dict, nature='data')
        guidelines = instructor('folder_analysis')
        response = {"analysis": file_dict,
                    "guidelines": guidelines.replace('{folder_path}', os.path.basename(folder_path))}
        return Response(response=json.dumps(response), status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.get("/analysis/code")
async def analyze_code():
    try:
        code_path = request.args.get("code_path", "")
        scope_level = int(request.args.get("scope_level", "2"))
        code_analysis = await functions.analyze_code(code_path, scope_level)
        return Response(response=json.dumps({"analysis": code_analysis, "guidelines": instructor('code_analysis')}),
                        status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.post('/download_file')
async def download_file():
    try:
        request_data = await request.get_json(force=True)
        url = request_data.get('url', '')
        local_path = request_data.get('local_path', '')
        return await functions.download_file(url, local_path)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.post("/run_script")
async def run_script():
    try:
        request_data = await request.get_json(force=True)
        env_name = request_data.get("env_name", "debuggerGPT")
        script_path = request_data.get("script_path", "")
        args_str = request_data.get("args_str", "")

        return await functions.run_script(script_path, env_name, args_str)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.post('/create_plugin')
async def create_plugin():
    guidelines = None
    try:
        request_data = await request.get_json(force=True)
        destination_path = request_data.get('path', 'codes')
        if not instructor.passed('plugins'):
            guidelines = instructor('plugins')
            destination_path = await functions.create_plugin(destination_path)
            guidelines.replace('{destination_path}', destination_path)
        else:
            guidelines = instructor('plugins')
        return Response(response=json.dumps({'guidelines': guidelines}),
                        status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')


@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("./.well-known/ai-plugin.json") as f:
        text = f.read()
        return Response(text, mimetype="text/json")


@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return Response(text, mimetype="text/yaml")


@app.after_request
async def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = 'https://chat.openai.com'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response


@app.route("/files/<path:filename>", methods=['OPTIONS'])
async def options_files(filename):
    response = Response(response='', status=200)
    response.headers['Access-Control-Allow-Origin'] = "https://chat.openai.com"
    response.headers['Access-Control-Allow-Headers'] = 'content-type,openai-conversation-id,openai-ephemeral-user-id'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    return response


def main():
    app.run(debug=True, host="0.0.0.0", port=5003)


if __name__ == "__main__":
    main()
