def get_provider():
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
    assert w3.isConnected()
    return w3
