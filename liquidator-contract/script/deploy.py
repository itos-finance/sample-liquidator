import os
import subprocess
import json
from dotenv import load_dotenv

BASEDIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASEDIR, '.env'))

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    while True:
        output = process.stdout.readline().decode("utf-8")
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    return process.poll()

def export_environment_variables(data):
    for key, value in data.items():
        os.environ[key] = str(value)

def read_json_to_envir(json_file_path):
    try:
        with open(json_file_path, 'r') as file:
            json_data = json.load(file)
    except FileNotFoundError:
        print(f"File '{json_file_path}' not found.")
        exit(1)
    except json.JSONDecodeError as e:
        print("Error parsing JSON file:", e)
        exit(1)
    export_environment_variables(json_data)

FORK_URL = os.getenv('FORK_URL') or 'http://localhost:8545'
DEPLOYER_PUBLIC_KEY = os.getenv('DEPLOYER_PUBLIC_KEY')

# Define the commands to be executed:
commands = [
            f'forge script DeployLiqContract.s.sol:DeployLiqContractScript --fork-url {FORK_URL} -vvvvv --ffi --broadcast']

# pull deployment info into env
read_json_to_envir('../../../itos-deploy/script/core/deployment/combined.json')
#read_json_to_envir('deployment/deployment.json')

# iterate commands
for command in commands:
    run_command(command)


