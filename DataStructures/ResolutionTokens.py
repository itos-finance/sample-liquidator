# Data structure to keep track of tokens that we can use during the resolution
class ResolutionTokens:
    def __init__(self, tokens, amounts, ids):
        self.tokens = tokens
        self.amounts = amounts
        self.ids = ids

    def add_resolution_token(self, token, amount, id):
        self.tokens.append(token)
        self.amounts.append(amount)
        self.ids.append(id)

    def getAvailableToken(self):
        return (self.tokens[0], self.amounts[0], self.ids[0])

    def add_resolution_tokens(self, res_to_add):
        for i in range(0, len(res_to_add.tokens)):
            self.add_resolution_token(res_to_add.tokens[i], res_to_add.amounts[i], res_to_add.ids[i])