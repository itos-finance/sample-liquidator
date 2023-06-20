import os
from ChainListener import get_provider
from Utils import get_abi
from dotenv import load_dotenv
from web3 import Web3

# Class for setting up a mock position that can be liquidated for testing purposes.
class SetUp:
    def __init__(self, pocketbook_address, mock_pyth_address, pocketbook_abi, mock_pyth_abi):
        Web3.strict_bytes_type_checking = False
        self.provider = get_provider()
        self.pocketbook_address = pocketbook_address
        self.pocketbook_contract = self.provider.eth.contract(address = pocketbook_address, abi = pocketbook_abi)
        #self.mock_pyth_feed = self.provider.eth.contract(address = mock_pyth_address, abi = mock_pyth_abi)

    def deposit(self, recipient, portfolio, token, amount):
        #approve the pocketbook to deposit token
        token_contract = self.provider.eth.contract(address = token, abi = get_abi("./abis/ERC20.json"))
        private_key = os.getenv('DEPLOYER_PRIVATE_KEY')
        function_call = token_contract.functions.approve(self.pocketbook_address, amount).build_transaction({
            'from': recipient,
            'nonce': self.provider.eth.get_transaction_count(recipient),
            'gas': 2000000,
            'gasPrice': Web3.to_wei('50', 'gwei')
        })
        signed_txn = self.provider.eth.account.sign_transaction(function_call, private_key = private_key)
        self.provider.eth.send_raw_transaction(signed_txn.rawTransaction)
        # deposit the token
        (assetId, positionId) = self.pocketbook_contract.functions.deposit(recipient, portfolio, token, amount).call({'from': recipient})

        print("AssetId: %d", assetId)
        print("PositionId: %d", positionId)

        return (assetId, positionId)

    def makeUnhealthy(self, positionId, account):
        #weth_feed_id = bytearray(32)
        #weth_feed_id[:len("weth")] = b"weth"
        weth_feed_id = Web3.to_bytes("weth\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0".encode('utf-8'))
        print(len(weth_feed_id))
        print(weth_feed_id)
        print(Web3.strict_bytes_type_checking)
        # price went from 1e18 to 5e17 (halved)
        newPrice = Web3.to_int(hexstr=hex(500000000000000000))
        # timestamp is 1 on deploy. try 3?
        timestamp = 3
        priceFeedData = self.mock_pyth_feed.functions.createPriceFeedUpdateData(
            weth_feed_id,
            newPrice,
            1,
            -18,
            1,
            1,
            timestamp
        ).call()

        self.mock_pyth_feed.functions.updatePriceFeeds([priceFeedData]).call()