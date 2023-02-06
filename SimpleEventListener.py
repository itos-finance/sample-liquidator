#! /usr/bin/env python3
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request
from flask_cors import CORS
import argparse
from web3 import Web3
import time

from Plot import Plotter
from EventProcessor import LogListenerAndProcessor

DEFAULT_OUT_FILE = "/Users/terence/Dev/Solidity/Itos/Mock2sAMM/out/2sAMM.sol/Alpha2sAMM.json"
DEFAULT_CHAIN_URL = 'http://127.0.0.1:8545'
LLP = None

def get_subscriber_fees():
    subscriber.position.get_fee_ranges()

app = Flask(__name__)
CORS(app)

@app.route("/data")
def data():
    result = LLP.produce()
    response = jsonify(result)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route("/subscribe/<addr>")
def subscribe(addr):
    LLP.subscribe_sender(addr, "test")
    return f"{addr} was subscribed to!"

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Web3.toChecksumAddress, help="Which contract to subscribe to events for.")
    parser.add_argument("--out_file", default=DEFAULT_OUT_FILE, help="The foundry output file for our contract.")
    parser.add_argument("--chain_url", default=DEFAULT_CHAIN_URL, help="The web3 http provider we'll use.")
    parser.add_argument("--local", action="store_true", help="Don't host any data. Just fetch and plot locally.")
    parser.add_argument("--sub", type=Web3.toChecksumAddress, help="Wallet address to subscribe to. Non-local runs can initiate a subscription later.")
    parser.add_argument("-p", "--port", default=4321, help="Port for flask")
    parser.add_argument("-t", "--time", default=3, help="Chain polling interval in seconds")
    return parser.parse_args()

def main(args):
    global LLP
    w3 = Web3(Web3.HTTPProvider(args.chain_url))
    assert w3.isConnected()
    LLP = LogListenerAndProcessor(w3, args.contract, args.out_file)

    if (args.sub):
        LLP.subscribe_sender(args.sub, "test")

    # pull from the chain every 2 seconds
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(LLP.pull, 'interval', seconds=3)
    sched.start()

    if args.local:
        # poll and plot
        plotter = Plotter(LLP)
        while True:
            plotter.plot()
            time.sleep(args.time)
    else:
        app.run(host="localhost", port=args.port)



if __name__ == "__main__":
    args = parse_args()
    main(args)
