import json
class TestUtils:

    def get_bytecode(path):
        with open(path, 'r') as file:
            file_content = file.read()
        return json.loads(file_content)

    def get_abi(path):
        with open(path, 'r') as file:
            file_content = file.read()
        return json.loads(file_content)