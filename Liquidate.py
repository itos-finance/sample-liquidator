from ChainListener import get_provider
from web3 import Web3
from Utils import derive_portfolio_id
import struct

class Liquidator:
    def __init__(self, pm_contract_getter_abi, pm_contract_pm_abi, pm_contract_address, resolver_address):
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
        self.targetUtil = self.pm_getter_contract.functions.targetUtil().call()


    #to be called by a function that calls the api to get accounts and discovers one with unhealthy positions
    def liquidate_account(self, account, safeToken):
        print("liq")
        portfolios = self.pm_getter_contract.functions.getAllPortfolios(account).call()
        print(portfolios)
        for i in range(0, len(portfolios)):
            id = self.pm_getter_contract.functions.derivePortfolioId(account, i).call() #derive_portfolio_id(account, i)
            (collateral, debt, util) = self.pm_contract.functions.queryValuesUSD(id).call()
            print("debt: %d", debt)
            print("collateral: %d", collateral)

            if(util < self.maxUtil and util !=0):
                print("foundAcct")
                instructions = self.getInstructions(collateral, debt, safeToken)
                portfolio = self.pm_getter_contract.functions.getPortfolio(account, id).call()
                print("gotport")
                print(portfolio)
                self.pm_contract.functions.liquidate(id, self.resolver_address, portfolio, instructions).call()
        return "None"


    def getInstructions(self, collateral, debt, tokenOut):
        return [Web3.to_bytes(0x0)]

