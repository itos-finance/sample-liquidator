
class Portfolio:
    def __init__(
            self,
            portfolio_id,
            collateral_USD,
            debt_USD,
            obligation_USD,
            utilization,
            tails,
            tail_credits,
            tail_debts,
            tail_delta_X_vars,
            utils
    ):
        self.portfolio_id = portfolio_id
        self.collateral_USD = collateral_USD
        self.debt_USD = debt_USD
        self.obligation_USD = obligation_USD
        self.utilization = utilization
        self.tails = []
        self.tail_credits = []
        self.tail_debts = []
        self.tail_delta_X_vars = []
        self.utils = []
        for i in range(0, len(tails)):
            self.tails.append(tails[i])
            self.tail_credits.append(tail_credits[i])
            self.tail_debts.append(tail_debts[i])
            self.tail_delta_X_vars.append(tail_delta_X_vars[i])
            self.utils.append(utils[i])

    def print_portfolio(self):
        print("PRINTING PORTFOLIO: ", self.portfolio_id)
        print(" COLLATERAL USD: ", self.collateral_USD)
        print(" DEBT USD: ", self.debt_USD)
        print(" Obligation USD: ", self.obligation_USD)