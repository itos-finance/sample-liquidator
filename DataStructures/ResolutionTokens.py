from enum import Enum

# Data structure to keep track of tokens that we can use during the resolution
class ResolutionTokens:
    # tokens[0] is the preferred in token, meaning it's the most feasible to swap out of and to get a large value flash loan of.
    # Typically the liq token
    def __init__(self, tokens, amounts, ids):
        self.tokens = tokens
        self.amounts = amounts
        self.ids = ids

    # maintain list of tokens we may accumulate during the resolution. We want to swap out of these to the preferred in token
    # to repay the flash loan in endResolutionCB (the last instructions passed to the resolver)
    def add_resolution_token(self, token, amount, id):
        self.tokens.append(token)
        self.amounts.append(amount)
        self.ids.append(id)

    def getPreferredInToken(self):
        return (self.tokens[0], self.amounts[0], self.ids[0])

    def add_resolution_tokens(self, res_to_add):
        for i in range(0, len(res_to_add.tokens)):
            self.add_resolution_token(res_to_add.tokens[i], res_to_add.amounts[i], res_to_add.ids[i])

class TokenMap:
    def __init__(self, token, token_type):
        self.available_tokens[token] = token_type

class TokenType(Enum):
    LIQ_TOKEN = 0
    CORE_TOKEN = 1
    TAIL_TOKEN = 2