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
def pm_contract(eth_tester, w3):

    deploy_address = eth_tester.get_accounts()[0]

    pm_abi = get_abi("./abis/PositionManagerFacet.json")
    bytecode = get_bytecode(BYTECODE_BASE_PATH + "PositionManagerFacet.json")["bytecode"]

    # Create our contract class.
    PMContract = w3.eth.contract(abi=pm_abi, bytecode=bytecode)
    # issue a transaction to deploy the contract.
    tx_hash = PMContract.constructor().transact(
        {
            "from": deploy_address,
        }
    )
    # wait for the transaction to be mined
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)
    # instantiate and return an instance of our contract.
    return PMContract(tx_receipt.contractAddress)

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
def getter_facet_contract(eth_tester, w3):
    deploy_address = eth_tester.get_accounts()[0]

    abi = get_abi("./abis/GetterFacet.json")
    bytecode = get_bytecode(BYTECODE_BASE_PATH + "GetterFacet.json")["bytecode"]
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

def test_pm_make(pm_contract):
    val = pm_contract.caller.queryValuesNative(0)
    assert val == 0