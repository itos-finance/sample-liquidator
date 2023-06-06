#! /usr/bin/env python3
from flask import Flask, jsonify, request
import json
from flask_cors import CORS
import argparse
from web3 import Web3
import os
from Utils import get_abi, derive_portfolio_id
from TestLib.SetUp import SetUp
from dotenv import load_dotenv

from Liquidate import Liquidator
DEFAULT_CHAIN_URL = 'http://127.0.0.1:8545'

POCKETBOOK = Web3.to_checksum_address(0x809d550fca64d94Bd9F66E60752A544199cfAC3D)
MOCK_PYTH = Web3.to_checksum_address(0x3Aa5ebB10DC797CAC828524e59A333d0A371443c)
USDC = Web3.to_checksum_address(0x4ed7c70F96B99c776995fB64377f0d4aB3B0e1C1)
WETH = Web3.to_checksum_address('0x322813Fd9A801c5507c9de605d63CEA4f2CE6c44')

app = Flask(__name__)
CORS(app)


@app.route('/liquidate/<addr>/<safeToken>')
def liquidate(addr, safeToken):
    res = LIQUIDATOR.liquidate_account(addr, safeToken)
    return res


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Web3.to_checksum_address, help="Address of the PM contract")
    parser.add_argument("resolver", type=Web3.to_checksum_address, help="Address of the resolver contract")
    parser.add_argument("-p", "--port", default=4321, help="Port for flask")
    return parser.parse_args()



def main(args):
    load_dotenv()
    global LIQUIDATOR
    getter_abi = get_abi("./abis/GetterFacet.json")
    pm_abi = get_abi("./abis/PositionManagerFacet.json")
    pocketbook_abi = get_abi("./abis/Pocketbook.json")
    mock_pyth_abi = get_abi("./abis/MockPyth.json")
    setup = SetUp(POCKETBOOK, MOCK_PYTH, pocketbook_abi, mock_pyth_abi)
    account = os.getenv('DEPLOYER_PUBLIC_KEY')
    (assetId, positionId) = setup.deposit(account, 0, WETH, 50)
    #setup.makeUnhealthy(positionId, account)
    LIQUIDATOR = Liquidator(getter_abi, pm_abi, args.contract, args.resolver)
    app.run(host="localhost", port=args.port)



if __name__ == "__main__":
    args = parse_args()
    main(args)
