# Python Code Debugger Plugin

## Description
This plugin allows ChatGPT to debug Python code files, manage Python environments, and manipulate files on your computer. It can retrieve and modify files, execute shell commands, create new Python environments, and run Python scripts within specific environments.

## Installation
1. Clone this repository to your local machine.
2. Navigate to the cloned repository in your terminal.
3. Install the required Python packages by running `pip install -r requirements.txt`.
4. Start the server by running `python main.py`.

## Usage
Before using the plugin, you need to initialize it by sending a POST request to the `/initialize` endpoint. This ensures that the conda environment 'debuggerGPT' is set up for running scripts.

Here are the main capabilities of the plugin:

1. **Execute Shell Commands**: You can execute a shell command by sending a POST request to the `/execute` endpoint with the command as a string in the request body. If you want to run the command in a specific environment, include the 'env_name' in your request.

2. **Run Python Scripts**: You can run a Python script in a specific environment by sending a POST request to the `/run_script` endpoint with the path to the script and the name of the environment in the request body.

3. **Modify Files**: You can modify a file by sending a POST request to the `/files/{filename}` endpoint with the new content of the file in the request body.

4. **Install Python Packages**: You can install Python packages in a specific environment by sending a POST request to the `/install_packages` endpoint with the name of the environment and a list of packages in the request body.

5. **Debug Code**: To debug a code, run the code, examine the output and error messages, decide how to fix the code, and then use the 'modify a file' command to update the code. Repeat this process until the code runs without errors.
