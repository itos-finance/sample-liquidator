from web3 import Web3

class Record:
    def __init__(self, record):
        self.isSourcePocketbook = record[0]
        self.sourceAddress = Web3.to_checksum_address(record[1])
        self.tokens = []
        self.credits = []
        self.debts = []
        self.deltas = []
        #populate tokens, credits, debts and deltas. Should all be the same len
        for i in range(0, len(record[2])):
            self.tokens.append(Web3.to_checksum_address(record[2][i]))
            self.credits.append(record[3][i])
            self.debts.append(record[4][i])
            self.deltas.append(record[5][i])



