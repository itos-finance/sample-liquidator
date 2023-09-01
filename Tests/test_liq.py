import pytest
import json
import pytest_asyncio

from Liquidate import Liquidate

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

############### CONTRACTS ################

@pytest.fixture
def mock_pm(eth_tester, w3):
    deploy_address = eth_tester.get_accounts()[0]
    maxUtil = int((75 * BASEX128) / 100)
    targetUtil = int((7 * BASEX128) / 10)
    liqBonus = int((5 * BASEX128) / 100 + BASEX128)
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
    return PMContract(tx_receipt.contractAddress), tx_receipt.contractAddress


def liquidator_contract(eth_tester, w3, pm_addr):
    deploy_address = eth_tester.get_accounts()[0]

    abi = get_abi("./Tests/abis/MockLiquidator.json")
    bytecode = get_bytecode(BYTECODE_BASE_PATH + "MockLiquidator.json")["bytecode"]
    LiquidatorContract = w3.eth.contract(abi=abi, bytecode=bytecode)
    # issue a transaction to deploy the contract.
    tx_hash = LiquidatorContract.constructor(pm_addr).transact(
        {
            "from": deploy_address,
        }
    )
    # wait for the transaction to be mined
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)
    print("liqctrctaddr: ", tx_receipt.contractAddress)
    # instantiate and return an instance of our contract.
    return LiquidatorContract(tx_receipt.contractAddress), tx_receipt.contractAddress

def resolver_contract(eth_tester, w3, pm_addr):
    deploy_address = eth_tester.get_accounts()[0]
    zero_addr = w3.to_checksum_address("0x0000000000000000000000000000000000000000")
    mock_amm_init_hash = Web3.to_bytes(hexstr = "0x1234567891234567890123456789012012345678912345678901234567890120")
    print(len(mock_amm_init_hash))
    print(mock_amm_init_hash)
    abi = get_abi("./abis/Resolver.json")
    bytecode = get_bytecode(BYTECODE_BASE_PATH + "Resolver.json")["bytecode"]
    ResolverContract = w3.eth.contract(abi=abi, bytecode=bytecode)
    # issue a transaction to deploy the contract.
    tx_hash = ResolverContract.constructor(zero_addr, zero_addr, zero_addr, zero_addr, pm_addr, mock_amm_init_hash).transact(
        {
            "from": deploy_address,
        }
    )
    # wait for the transaction to be mined
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)

    # instantiate and return an instance of our contract.
    return ResolverContract(tx_receipt.contractAddress), tx_receipt.contractAddress

############### SETUP HELPERS ##############################

def register_token(ResolverContract, token):
    ResolverContract.functions.addTokenToRegistry(token).transact()

def get_liquidator(w3, mock_pm_addr, resolver_addr, liq_contract_addr):
    getter_abi = get_abi("./abis/GetterFacet.json")
    pm_abi = get_abi("./abis/PositionManagerFacet.json")
    pocketbook_abi = get_abi("./abis/PocketbookFacet.json")
    resolver_abi = get_abi("./abis/Resolver.json")
    liquidator_abi = get_abi("./Tests/abis/MockLiquidator.json")
    liq = Liquidate.Liquidator(
        getter_abi,
        pm_abi,
        pocketbook_abi,
        resolver_abi,
        liquidator_abi,
        mock_pm_addr,
        resolver_addr,
        liq_contract_addr,
        w3
    )
    return liq

def get_simple_liq_setup(w3, eth_tester, mock_pm):
    (mock_pm_contract, mock_pm_addr) = mock_pm
    deploy_address = eth_tester.get_accounts()[0]
    tok0 = w3.to_checksum_address("0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0")
    tok1 = w3.to_checksum_address("0x0000000000000000000000000000000000000007")
    tx_hash = mock_pm_contract.functions.setupLiquidatablePortfolio(deploy_address, tok0, tok1).transact(
        {
            "from": w3.eth.accounts[1],
        }
    )
    w3.eth.wait_for_transaction_receipt(tx_hash, 180)
    #.setupMockPortfolio([deploy_address, 0, 1000000000, 1100000000, 200, 1, util], [],[],[],[],[])
    ports = mock_pm_contract.caller.getAllPortfolios(deploy_address)
    (ResolverContract, resolver_addr) = resolver_contract(eth_tester, w3, mock_pm_addr)
    register_token(ResolverContract, tok0)
    register_token(ResolverContract, tok1)
    (Liquidator_contract_obj, liq_contract) = liquidator_contract(eth_tester, w3, mock_pm_addr)
    Liquidator_contract_obj.functions.setPm(mock_pm_addr).transact()
    liq = get_liquidator(w3, mock_pm_addr, resolver_addr, liq_contract)
    return liq, mock_pm_contract


################ TESTS ######################################

def test_simple_total_liq(w3, eth_tester, mock_pm):
    deploy_address = eth_tester.get_accounts()[0]
    flashloan_scalar = 10
    simple_mode = True
    liquidator, mock_pm_contract = get_simple_liq_setup(w3, eth_tester, mock_pm)
    liquidator.liquidate_account(deploy_address, flashloan_scalar, simple_mode)
    instructions = mock_pm_contract.caller.getInstructionsRecieved2D()
    assert(instructions[0] == Web3.to_bytes(0))
    # scalar * credits + debts
    amount = 10 * (1000000000000000000 + 1100000000000000000)
    print(amount.to_bytes(32, byteorder='big'))
    print(len(instructions[1]))
    assert(int.from_bytes(instructions[1][1:33], byteorder='big') == amount)

def test_simple_partial_liq(w3, eth_tester, mock_pm):
    deploy_address = eth_tester.get_accounts()[0]
    flashloan_scalar = 10
    simple_mode = True
    liquidator, mock_pm_contract = get_simple_liq_setup(w3, eth_tester, mock_pm)
    liquidator.liquidate_account(deploy_address, flashloan_scalar, simple_mode)
    instructions = mock_pm_contract.caller.getInstructionsRecieved2D()
    assert(instructions[0] == Web3.to_bytes(0))
    # scalar * credits + debts
    amount = 10 * (1000000000000000000 + 1100000000000000000)
    print(amount.to_bytes(32, byteorder='big'))
    print(len(instructions[1]))
    assert(int.from_bytes(instructions[1][1:33], byteorder='big') == amount)



if __name__ == '__main__':
    pass
