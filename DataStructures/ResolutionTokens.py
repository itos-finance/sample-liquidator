
# Data structure to keep track of tokens that we can use during the resolution
class ResolutionTokens:
    # the first token added is the preferred in token, meaning it's the most feasible to swap out of and to get a large value flash loan of.
    # Typically the liq token
    def __init__(self, token_addr, amount, id):
        self.tokens = []
        res_token = ResolutionToken(token_addr, amount, id)
        self.tokens.append(res_token)
        self.preferredInToken = res_token
        # when get_token_addresses_and_balances_sorted is called, tokens gets sorted in place.
        # sorted flag saves us from calling sort on a sorted list
        self.sorted = True

    # maintain list of tokens we may accumulate during the resolution. We want to swap out of these to the preferred in token
    # to repay the flash loan in endResolutionCB (the last instructions passed to the resolver)
    def add_resolution_token(self, token_addr, amount, id):
        # if token is already in list, increment its amount. Else append. Preserves that tokens[0] is liq token
        idx = self.get_resolution_token_index(token_addr)
        if(idx is not None):
            self.tokens[idx].amount += amount
            return
        self.tokens.append(ResolutionToken(token_addr, amount, id))
        self.sorted = False

    def getPreferredInToken(self):
        return self.preferredInToken

    def add_resolution_tokens(self, res_to_add):
        for i in range(0, len(res_to_add.tokens)):
            self.add_resolution_token(res_to_add.tokens[i].token_addr, res_to_add.tokens[i].amount, res_to_add.tokens[i].id)

    def getAddress(self, res_token):
        return res_token.token_addr

    def get_token_addresses_and_balances_sorted(self):
        if self.tokens is None:
            return []
        if self.sorted is False:
            self.tokens.sort(key=self.getAddress)
        addresses, amounts = [],[]
        for tok in self.tokens:
            addresses.append(tok.token_addr)
            amounts.append(tok.amount)
        self.sorted = True
        return addresses, amounts

    def get_resolution_token_index(self, address):
        for i in range (0, len(self.tokens)):
            if (self.tokens[i].token_addr == address):
                return i
        return None

class ResolutionToken:
    def __init__(self, token_addr, amount, id):
        self.token_addr = token_addr
        self.amount = amount
        self.id = id