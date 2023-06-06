from web3 import Web3
import json

def derive_portfolio_id(address, portfolio):
        # address is a hex string. Truncate derivation result to 8 bytes:
        print("portId: %d", int(Web3.to_bytes(int(address, 16) + (portfolio << 160))[-1]))
        return int(Web3.to_bytes(int(address, 16) + (portfolio << 160))[-1])

def get_abi(path):
    with open(path, 'r') as file:
        file_content = file.read()
    return json.loads(file_content)