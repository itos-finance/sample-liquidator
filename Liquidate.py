from ChainListener import get_provider
from web3 import Web3
from Utils import derive_portfolio_id
import struct

class Liquidator:

    #X128 val used in calculation
    BASEX128 = 1 << 128

    def __init__(self, pm_contract_getter_abi, pm_contract_pm_abi, pm_contract_address, resolver_address,):
        provider = get_provider()
        self.pm_contract_getter_abi = pm_contract_getter_abi
        self.pm_contract_pm_abi = pm_contract_pm_abi
        self.pm_contract_address = pm_contract_address
        self.resolver_address = resolver_address
        # get the position manager contract facets. We need a separate contract object per facet since they have
        # unique abis:
        self.pm_getter_contract = provider.eth.contract(address=self.pm_contract_address, abi=self.pm_contract_getter_abi)
        self.pm_contract = provider.eth.contract(address=self.pm_contract_address, abi=self.pm_contract_pm_abi)

        # get the util values from getter facet and set them:
        self.maxUtil = self.pm_getter_contract.functions.maxUtil().call()
        self.liqToken = self.pm_getter_contract.functions.fallbackToken().call()
        self.targetUtil = self.pm_getter_contract.functions.targetUtil().call()
        self.liquidationBonus = self.pm_getter_contract.functions.liquidationBonus().call()



    #to be called by a function that calls the api to get accounts and discovers one with unhealthy positions
    def liquidate_account(self, account, safeToken):
        print("liq")
        portfolios = self.pm_getter_contract.functions.getAllPortfolios(account).call()
        print(portfolios)

        for i in range(0, len(portfolios)):

            # get position id
            id = derive_portfolio_id(account, i)

            #get status of position
            (collateral, debt, req, util, tails, tailDebts, tailCredits, utils) = self.pm_contract.functions.queryValuesUSD(id).call()
            print("     debt: ", debt)
            print("     req: ", req)
            print("     collateral: ", collateral)
            print("     util: ", util)
            print("     tails: ", tails)
            print("     tailDebts: ", tailDebts)
            print("     tailCredits: ", tailCredits)
            print("     utils: ", utils)

            # is it eligible for liquidation?
            if(util >= self.maxUtil and util != 0):
                print("     found portfolio to liquidate: ", id)

                # how do we liquidate?
                instructions = self.getInstructions(id, collateral, debt, self.liqToken)

                # get list of positions to liquidate
                positions = self.pm_getter_contract.functions.getPortfolio(account, id).call()
                print("     Positions in portfolio:")
                print("     ", positions)

                # call liquidate
                self.pm_contract.functions.liquidate(id, self.resolver_address, positions, instructions).call()

        return "Healthy"


    def getInstructions(self, id, collateral, debt, tokenOut):
        # get the tokens and amounts in the portfolio:
        (_, assetId, _, _ ) = self.pm_getter_contract.functions.getPosition(id)
        (_, _, tokens, amounts) = self.pocketbook_contract.functions.queryValue(assetId)
        print(tokens)
        print(amounts)

        #how much do we need to liquidate?
        valueToLiquidate = self.calcCreditAndDebtTargets(debt, collateral)

        index = 0
        # loop through tokens in position until the instruction execution would either return the position to the targetUtil or run out of tokens
        #while(collateral/debt > self.targetUtil or index >= len(tokens)):

        return [Web3.to_bytes(0x0)]

    def calcCreditAndDebtTargets(self, debt, collateral):
        debt_target, credit_target
        if(debt > collateral):
            debt_target = debt
            credit_target = collateral
        else: #debt / collateral >= maxUtil
            util = debt / collateral
            debt_target = (debt * (util - self.targetUtil)) / ( self.BASEX128 - ((self.targetUtil * self.liquidationBonus)/ self.BASEX128) )
            if debt_target > self.BASEX128:
                debt_target = self.BASEX128
            credit_target = debt_target + ((debt_target * self.liquidationBonus) / self.BASEX128)
        return (debt_target, credit_target)
