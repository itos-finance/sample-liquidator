import pytest
import json

import pytest_asyncio

from web3 import (
    EthereumTesterProvider,
    Web3,
)
from web3.eth import (
    AsyncEth,
)
from web3.providers.eth_tester.main import (
    AsyncEthereumTesterProvider,
)
BASEX128 = 1 << 128
def get_bytecode(path):
    with open(path, 'r') as file:
        file_content = file.read()
    return json.loads(file_content)

def get_abi(path):
    with open(path, 'r') as file:
        file_content = file.read()
    return json.loads(file_content)

BYTECODE_BASE_PATH = "./Tests/bytecode/"

@pytest.fixture
def tester_provider():
    return EthereumTesterProvider()


@pytest.fixture
def eth_tester(tester_provider):
    return tester_provider.ethereum_tester


@pytest.fixture
def w3(tester_provider):
    return Web3(tester_provider)



@pytest.fixture
def resolver_contract(eth_tester, w3):
    deploy_address = eth_tester.get_accounts()[0]

    abi = get_abi("./abis/Resolver.json")
    bytecode = get_bytecode(BYTECODE_BASE_PATH + "Resolver.json")["bytecode"]
    ResolverContract = w3.eth.contract(abi=abi, bytecode=bytecode)
    # issue a transaction to deploy the contract.
    tx_hash = ResolverContract.constructor().transact(
        {
            "from": deploy_address,
        }
    )
    # wait for the transaction to be mined
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)
    # instantiate and return an instance of our contract.
    return ResolverContract(tx_receipt.contractAddress)

@pytest.fixture
def mock_pm_contract(eth_tester, w3):
    deploy_address = eth_tester.get_accounts()[0]
    maxUtil = int((75 * BASEX128) / 100)
    targetUtil = int((7 * BASEX128) / 10)
    liqBonus =int((5 * BASEX128) / 100 + BASEX128)
    liqToken = Web3.to_checksum_address("0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0")
    abi = get_abi("./Tests/abis/MockPM.json")
    bytecode = get_bytecode(BYTECODE_BASE_PATH + "MockPM.json")["bytecode"]
    PMContract = w3.eth.contract(abi=abi, bytecode=bytecode)
    # issue a transaction to deploy the contract.
    tx_hash = PMContract.constructor(maxUtil, liqToken, targetUtil, liqBonus).transact(
        {
            "from": deploy_address,
        }
    )
    # wait for the transaction to be mined
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)
    # instantiate and return an instance of our contract.
    return PMContract(tx_receipt.contractAddress)

def test_simple_liq(eth_tester, mock_pm_contract):
    deploy_address = eth_tester.get_accounts()[0]
    util = int((80 * BASEX128) / 100)

    tx_hash = mock_pm_contract.caller.setupMockPortfolio([deploy_address, 0, 1000000000, 1100000000, 200, 1, util], [],[],[],[],[]).transact(
        {
            "from":  w3.eth.accounts[1]
        }
    )

    tx_reciept = w3.eth.wait_for_transaction_receipt(tx_hash, 180)

    print(tx_reciept.portfolio_id)