
class Position:
    def __init__(self, portfolio_id, position, assetValue):
        self.portfolio_id = portfolio_id
        source = position[0] # 0 if source is AMM, 1 if source is pocketbook
        positionType = position[1]  # 0 if credit position, 1 if debt position
        self.assetId = position[2]
        self.sourceAddress = position[3]
        self.owner = position[4]

        self.isSourcePocketbook = True if source == 1 else False
        self.isPositionDebt = True if positionType == 1 else False
        # 4 lists, tokens[i] credits are credits[i], debts are debts[i], etc:
        self.tokens = assetValue[2]
        self.credits = assetValue[3]
        self.debts = assetValue[4]
        self.deltas = assetValue[5]