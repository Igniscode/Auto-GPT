"""Execute code in a Docker container"""
import os
import subprocess
import pathlib
import venv

from pathlib import Path

import docker
from docker.errors import ImageNotFound

from autogpt.commands.command import command
from autogpt.config import Config
from autogpt.logs import logger

CFG = Config()


@command("execute_python_file", "Execute Python File", '"filename": "<filename>"')
def execute_python_file(filename: str) -> str:
    """Execute a Python file in a Venv and return the output

    Args:
        filename (str): The name of the file to execute

    Returns:
        str: The output of the file
    """
    logger.info(f"Executing file '{filename}'")

    if not filename.endswith(".py"):
        return "Error: Invalid file type. Only .py files are allowed."

    if not os.path.isfile(filename):
        return f"Error: File '{filename}' does not exist."

    if we_are_running_in_a_docker_container():
        result = subprocess.run(
            f"python {filename}", capture_output=True, encoding="utf8", shell=True
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"

    try:
        # Set the desired virtual environment directory
        venv_dir = f"{CFG.workspace_path}/venv"
        if pathlib.Path(venv_dir).exists():
            print("Virtual environment already exists.")
        else:
            # Create the virtual environment
            venv.create(venv_dir, with_pip=True)
            print("Virtual environment created.")

        # Define the path to the Python interpreter within the virtual environment
        venv_python = f"{venv_dir}/Scripts/python.exe"

        filepath = Path(filename)

        script_process = subprocess.Popen([venv_python, filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        script_stdout, script_stderr = script_process.communicate()

        # Wait for the script to complete
        script_process.wait()

        # Capture the script output and append it to the logs
        if script_stdout:
            logs += "Script Output:\n" + script_stdout.decode("utf-8") + "\n"
        if script_stderr:
            logs += "Script Error:\n" + script_stderr.decode("utf-8") + "\n"

        return logs

    except Exception as e:
        return f"Error: {str(e)}"


@command(
    "execute_shell",
    "Execute Shell Command, non-interactive commands only",
    '"command_line": "<command_line>"',
    CFG.execute_local_commands,
    "You are not allowed to run local shell commands. To execute"
    " shell commands, EXECUTE_LOCAL_COMMANDS must be set to 'True' "
    "in your config. Do not attempt to bypass the restriction.",
)
def execute_shell(command_line: str) -> str:
    """Execute a shell command and return the output

    Args:
        command_line (str): The command line to execute

    Returns:
        str: The output of the command
    """

    current_dir = Path.cwd()
    # Change dir into workspace if necessary
    if not current_dir.is_relative_to(CFG.workspace_path):
        os.chdir(CFG.workspace_path)

    logger.info(
        f"Executing command '{command_line}' in working directory '{os.getcwd()}'"
    )

    result = subprocess.run(command_line, capture_output=True, shell=True)
    output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    # Change back to whatever the prior working dir was

    os.chdir(current_dir)
    return output


@command(
    "execute_shell_popen",
    "Execute Shell Command, non-interactive commands only",
    '"command_line": "<command_line>"',
    CFG.execute_local_commands,
    "You are not allowed to run local shell commands. To execute"
    " shell commands, EXECUTE_LOCAL_COMMANDS must be set to 'True' "
    "in your config. Do not attempt to bypass the restriction.",
)
def execute_shell_popen(command_line) -> str:
    """Execute a shell command with Popen and returns an english description
    of the event and the process id

    Args:
        command_line (str): The command line to execute

    Returns:
        str: Description of the fact that the process started and its id
    """

    current_dir = os.getcwd()
    # Change dir into workspace if necessary
    if CFG.workspace_path not in current_dir:
        os.chdir(CFG.workspace_path)

    logger.info(
        f"Executing command '{command_line}' in working directory '{os.getcwd()}'"
    )

    do_not_show_output = subprocess.DEVNULL
    process = subprocess.Popen(
        command_line, shell=True, stdout=do_not_show_output, stderr=do_not_show_output
    )

    # Change back to whatever the prior working dir was

    os.chdir(current_dir)

    return f"Subprocess started with PID:'{str(process.pid)}'"


def we_are_running_in_a_docker_container() -> bool:
    """Check if we are running in a Docker container

    Returns:
        bool: True if we are running in a Docker container, False otherwise
    """
    return os.path.exists("/.dockerenv")
