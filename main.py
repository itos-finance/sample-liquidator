#! /usr/bin/env python3
from flask import Flask, jsonify, request
import json
from flask_cors import CORS
import argparse
from web3 import Web3
import os
from lib.Utils import get_abi, derive_portfolio_id
from TestLib.SetUp import SetUp
from dotenv import load_dotenv

from Liquidate import Liquidator
DEFAULT_CHAIN_URL = 'https://polygon-mumbai.infura.io/v3/e87ed58087a24e5ab2a025a1669bfcad'

USDC = Web3.to_checksum_address('0x5FC8d32690cc91D4c39d9d3abcBD16989F875707')
WETH = Web3.to_checksum_address('0x0165878A594ca255338adfa4d48449f69242Eb8F')

app = Flask(__name__)
CORS(app)


@app.route('/liquidate/<addr>/<safeToken>')
def liquidate(addr, safeToken):
    res = LIQUIDATOR.liquidate_account(addr, safeToken)
    return res


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("pm_contract", type=Web3.to_checksum_address, help="Address of the PM contract")
    parser.add_argument("resolver", type=Web3.to_checksum_address, help="Address of the resolver contract")
    parser.add_argument("-p", "--port", default=4321, help="Port for flask")
    return parser.parse_args()



def main(args):
    load_dotenv()
    global LIQUIDATOR
    getter_abi = get_abi("./abis/GetterFacet.json")
    pm_abi = get_abi("./abis/PositionManagerFacet.json")
    pocketbook_abi = get_abi("./abis/PocketbookFacet.json")
    resolver_abi = get_abi("./abis/Resolver.json")
    account = os.getenv('DEPLOYER_PUBLIC_KEY')
    LIQUIDATOR = Liquidator(getter_abi, pm_abi, pocketbook_abi, resolver_abi, args.pm_contract, args.resolver)
    app.run(host="localhost", port=args.port)



if __name__ == "__main__":
    args = parse_args()
    main(args)
