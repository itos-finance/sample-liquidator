from web3 import Web3
import json

def derive_portfolio_id(address, portfolio):
    # address is a hex string. Truncate derivation result to 8 bytes:
    port = int(address, 16) + (int(str(portfolio), 32) << 160)
    print("portId: %d", Web3.to_int(port))
    return Web3.to_int(port)

def get_abi(path):
    with open(path, 'r') as file:
        file_content = file.read()
    return json.loads(file_content)

if __name__ == "__main__":
    x = derive_portfolio_id('0x333', 0)
    print(x)