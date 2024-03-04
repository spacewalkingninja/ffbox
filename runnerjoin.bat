@echo off
set "script_dir=%~dp0"

set pyenv=<%script_dir%\envpath.txt

set /p conda_path=<%script_dir%\condapath.txt

set SKIP_VENV=1
call %conda_path% activate %script_dir%\env 

if not defined PYTHON (set PYTHON=%pyenv%)

if "%~1"=="" (
    echo Usage: %0 --model_req [path_to_model_req_yaml] --model_res_url [path_to_model_res_json]
    exit /b 1
)

::Call the Python script with provided arguments
call %pyenv% %script_dir%\join.py %*
SET exit_code = %ERRORLEVEL%
call %conda_path% deactivate
if %exit_code% 1 echo Exit code is one  & exit 1
if %exit_code% 0 echo Exit code is zero & exit 0
GOTO:EOF