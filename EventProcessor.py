from web3 import Web3
import json
import eth_utils
from hexbytes import HexBytes
from Data import PoolRepresentation, PositionRepresentation

class Subscriber:
    def __init__(self, pool, endpoint):
        self.endpoint = endpoint
        self.position = PositionRepresentation(pool)

    def add_event(self, event_log):
        self.position.add_event(event_log)

class EventListener:
    def __init__(self, w3, contract_addr, contract_out_file):
        self.w3 = w3
        self.contract_addr = contract_addr
        self.reset_filter()
        with open(contract_out_file, "r") as fo:
            self.abi = json.load(fo)["abi"]
        self.contract_obj = w3.eth.contract(
            address=contract_addr,
            abi=self.abi
        )
        sqrt_priceX96 = self.contract_obj.functions.get_sqrt_price().call()
        price = (sqrt_priceX96 / (1 << 96)) ** 2
        self.pool = PoolRepresentation(price)

        self.event_abis = {e["name"]:e for e in self.abi if e['type'] == 'event'}
        self.topic_lookup = {HexBytes(eth_utils.event_abi_to_log_topic(v)):
                             k for k, v in self.event_abis.items()}
        self.subscribed_senders = {}

    def reset_filter(self):
        self.event_filter = self.w3.eth.filter({"address": self.contract_addr})

    def subscribe_sender(self, address, endpoint):
        self.subscribed_senders[Web3.toChecksumAddress(address)] = Subscriber(self.pool, endpoint)

    def pull_logs(self):
        new_entries = self.event_filter.get_new_entries()
        return new_entries

    def process_log(self, log):
        event_type = self.topic_lookup[log['topics'][0]]
        return self.contract_obj.events.__getattribute__(event_type)().processLog(log)

    def test_pull(self):
        res = []
        for l in self.pull_logs():
            res.append(self.process_log(l))
        return res

class LogListenerAndProcessor(EventListener):

    def __init__(self, w3, contract_addr, contract_out_file):
        super().__init__(w3, contract_addr, contract_out_file)
        self.last_entries = None

    def pull(self):
        new_entries = self.pull_logs()
        self.last_entries = new_entries
        for e in new_entries:
            log = self.process_log(e)
            self.pool.add_event(log)
            subscriber = self.subscribed_senders.get(Web3.toChecksumAddress(log.args.sender))
            if (subscriber is not None):
                subscriber.add_event(log)

    def produce(self):
        """ Creates a big dictionary of data this has collected """
        res = {}
        res["price"] = self.pool.get_price()
        res["liquidity"] = self.pool.get_liqs(0.01, 300, 20)
        res["subscriptions"] = {}
        for address, subscriber in self.subscribed_senders.items():
            sub_data = {}
            sub_data["fees"] = subscriber.position.get_fee_ranges()
            sub_data["value"] = subscriber.position.get_deltas_from(1, 300, 1)
            res["subscriptions"][address] = sub_data
        return res
