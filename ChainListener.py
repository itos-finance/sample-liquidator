from web3 import Web3
import os
from dotenv import load_dotenv

def get_provider():
    load_dotenv()
    url = os.getenv('FORK_URL')
    w3 = Web3(Web3.HTTPProvider(url))
    assert w3.is_connected()
    return w3
