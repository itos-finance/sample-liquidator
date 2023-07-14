#! /usr/bin/env python3
from flask import Flask, jsonify, request
import json
from flask_cors import CORS
import argparse
from web3 import Web3
import os
from lib.Utils import get_abi, derive_portfolio_id
from dotenv import load_dotenv

from Liquidate import Liquidator

app = Flask(__name__)
CORS(app)


@app.route('/liquidate/<addr>')
def liquidate(addr):
    res = LIQUIDATOR.liquidate_account(addr)
    return res


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("pm_contract", type=Web3.to_checksum_address, help="Address of the PM contract")
    parser.add_argument("resolver", type=Web3.to_checksum_address, help="Address of the resolver contract")
    parser.add_argument("liquidator", type=Web3.to_checksum_address, help="Address of the liquidator contract")
    parser.add_argument("-p", "--port", default=4321, help="Port for flask")
    return parser.parse_args()



def main(args):
    load_dotenv()
    global LIQUIDATOR
    getter_abi = get_abi("./abis/GetterFacet.json")
    pm_abi = get_abi("./abis/PositionManagerFacet.json")
    pocketbook_abi = get_abi("./abis/PocketbookFacet.json")
    resolver_abi = get_abi("./abis/Resolver.json")
    liquidator_abi = get_abi("./abis/Liquidator.json")
    account = os.getenv('DEPLOYER_PUBLIC_KEY')
    LIQUIDATOR = Liquidator(getter_abi, pm_abi, pocketbook_abi, resolver_abi, liquidator_abi, args.pm_contract, args.resolver, args.liquidator)
    app.run(host="localhost", port=args.port)



if __name__ == "__main__":
    args = parse_args()
    main(args)
