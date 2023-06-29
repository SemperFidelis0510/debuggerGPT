@echo off

REM Initialize the plugin
curl -X POST http://localhost:5003/initialize -H "Content-Type: application/json" -d "{\"env_name\": \"debuggerGPT\"}"

REM Remember a value in memory
curl -X POST http://localhost:5003/memory -H "Content-Type: application/json" -d "{\"key\": \"test\", \"value\": \"Hello, World!\"}"

REM Recall a value from memory
 curl -X GET http://localhost:5003/memory/test

REM Execute a shell command
curl -X POST http://localhost:5003/execute -H "Content-Type: application/json" -d "{\"command\": \"echo Hello, World!\", \"env_name\": \"debuggerGPT\"}"

REM Run a Python script
curl -X POST http://localhost:5003/run_script -H "Content-Type: application/json" -d "{\"script_path\": \"codes\\\\trial.py\", \"env_name\": \"debuggerGPT\"}"

REM Analyze a Python code file
curl -X GET "http://localhost:5003/analysis/code?code_path=codes\\\\trial.py&scope_level=2"

REM Download a file
curl -X POST http://localhost:5003/download_file -H "Content-Type: application/json" -d "{\"url\": \"https://illustoon.com/photo/5462.png\", \"local_path\": \"codes\"}"

REM Get a file's content
curl -X GET http://localhost:5003/files/codes\\\\SR2.py

REM Edit a file
curl -X POST http://localhost:5003/files/codes\\\\trial.py -H "Content-Type: application/json" -d "{\"fixes\": [{\"lines\": [1, 1], \"code\": \"print('Hello, World!')\", \"indentation\": \"\"}], \"method\": \"subs\"}"

REM Analyze a folder
curl -X GET "http://localhost:5003/analysis/folder?folder_path=debuggerGPT"

@echo on

pause
