from quart import Quart, request
from quart_cors import cors
from functions import *
import classes
import traceback
from memory import Memory
import json
import os
import subprocess
import quart
from fastapi import HTTPException
import logging

app = Quart(__name__)
app = cors(app, allow_origin=["https://chat.openai.com", "192.168.1.233", "192.168.1.113"])
explained = {'code_analysis': False, 'plan': False, 'init': False}
memory = Memory()
instructor = classes.Instructor()
logger = logging.getLogger(__name__)


# todo: add info to init
# todo: add constants to memory
# todo: add permissions for files
# todo: probe for standard folders
# todo: update guides


@app.get("/files/<path:filename>")
async def get_file_route(filename: str):
    try:
        request_data = await request.get_json(force=True)
        num_lines = request_data.get("num_lines", 250)
        start_line = request_data.get("start_line", 0)
        content = await get_file(filename, num_lines, start_line)
        if content == 404:
            return Response(response='File not found', status=404)
        else:
            return Response(response=json.dumps({"content": content}), status=200, mimetype='application/json')
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500, mimetype='text/plain')


@app.post("/files/<path:filename>")
async def write_file_route(filename):
    try:
        request_data = await request.get_json(force=True)
        fixes = request_data.get("fixes", [])
        erase = request_data.get("erase", False)
        for fix in fixes:
            if "end_line" in fix:
                fix["end_line"] = int(fix["end_line"])
        return await write_file(filename, fixes, erase)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.put("/files/<path:filename>")
async def download_file_route(filename):
    try:
        request_data = await request.get_json(force=True)
        url = request_data.get('url', '')
        local_path = os.path.join(request_data.get('local_path', ''), filename)
        return await download_file(url, local_path)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.post("/execute")
async def execute_command_route():
    try:
        request_data = await request.get_json(force=True)
        command = request_data.get("command", "")
        env_name = request_data.get("env_name", None)

        # Input validation
        if not command or not isinstance(command, str):
            raise HTTPException(status_code=400, detail="Invalid command")
        if env_name is not None and not isinstance(env_name, str):
            raise HTTPException(status_code=400, detail="Invalid environment name")

        return await execute_command(command, env_name)
    except HTTPException as e:
        # Return user-friendly error messages
        return Response(response=e.detail, status=e.status_code)
    except Exception as e:
        # Log the error
        logger.error(f"An error occurred while executing the command: {e}")
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        logger.debug("".join(tb_str))  # Log the traceback at the debug level

        # Return a generic error message
        return Response(
            response="An error occurred while executing the command. Please check the logs for more details.",
            status=500)


@app.route("/memory/<key>", methods=["GET"])
async def recall_route(key):
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


@app.route("/memory/<key>", methods=["POST"])
async def remember_route(key):
    try:
        request_data = await request.get_json(force=True)
        value = request_data.get("value", "")
        nature = 'memory'
        memory.remember(key, value, nature=nature)
        return Response(response='OK', status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.get("/analysis/folder")
async def analyze_folder_route():
    try:
        folder_path = request.args.get("folder_path", "")
        depth = request.args.get("depth", None)  # Get the depth parameter from the request
        if depth is not None:
            depth = int(depth)  # Convert the depth to an integer if it is not None
        file_dict = await analyze_folder(folder_path, depth)  # Pass the depth to the analyze_folder function
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
async def analyze_code_route():
    try:
        code_path = request.args.get("code_path", "")
        scope_level = int(request.args.get("scope_level", "2"))
        code_analysis = await analyze_code(code_path, scope_level)
        return Response(response=json.dumps({"analysis": code_analysis, "guidelines": instructor('code_analysis')}),
                        status=200)
    except Exception as e:
        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        print("".join(tb_str))
        return Response(response="".join(tb_str), status=500)


@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')


@app.route("/.well-known/ai-plugin.json", methods=['GET', 'POST', 'OPTIONS'])
async def options_manifest():
    if request.method == 'OPTIONS':
        print("OPTIONS request received for /.well-known/ai-plugin.json")
        print(f"Request headers: {request.headers}")
        response = Response(response='', status=204)
    elif request.method == 'GET':
        with open("./.well-known/ai-plugin.json") as f:
            text = f.read()
            response = Response(text, mimetype="text/json")
    else:
        response = Response(response='', status=200)

    # List of allowed origins
    allowed_origins = ["https://chat.openai.com", "http://192.168.1.233", "http://192.168.1.113"]

    # Get the Origin header of the incoming request
    origin = request.headers.get('Origin')

    # If the Origin is in the list of allowed origins, set the Access-Control-Allow-Origin header
    # to the value of the Origin header
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = "https://chat.openai.com"

    response.headers['Access-Control-Allow-Headers'] = 'content-type,openai-conversation-id,openai-ephemeral-user-id'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    return response


@app.get("/openapi.yaml")
async def openapi_spec():
    with open("openapi.yaml") as f:
        text = f.read()
        return Response(text, mimetype="text/yaml")


@app.after_request
async def after_request(response):
    if response is not None:
        response.headers['Access-Control-Allow-Origin'] = 'https://chat.openai.com'
        response.headers['Access-Control-Allow-Headers'] = '*'
        response.headers['Access-Control-Allow-Methods'] = '*'
    return response


@app.route("/files/<path:filename>", methods=['OPTIONS'])
async def options_file_route(filename):
    print(f"OPTIONS request received for /files/{filename}")
    print(f"Request headers: {request.headers}")
    response = Response(response='', status=200)
    response.headers['Access-Control-Allow-Origin'] = "https://chat.openai.com"
    response.headers['Access-Control-Allow-Headers'] = 'content-type,openai-conversation-id,openai-ephemeral-user-id'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    return response


@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
async def handle_request():
    if request.method == 'OPTIONS':
        print(f"OPTIONS request received. Headers: {dict(request.headers)}")
    return '', 200


def main():
    app.run(debug=True, host="0.0.0.0", port=5003)


if __name__ == "__main__":
    main()
