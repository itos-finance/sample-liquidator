from ChainListener import get_provider
from web3 import Web3
from lib.Utils import derive_portfolio_id
import struct
from lib.Errors import TokenNotInRegistry
import lib.InstructionsLib as InstructionsLib

class Liquidator:
    #X128 val used in calculation
    BASEX128 = 1 << 128
    # when token isn't in the registry, it returns the max uint16 value as an error code
    NOT_IN_REGISTRY_CODE = 65535

    def __init__(
            self,
            pm_contract_getter_abi,
            pm_contract_pm_abi,
            pocketbook_contract_abi,
            resolver_contract_abi,
            pm_contract_address,
            resolver_address
        ):
        provider = get_provider()

        self.resolver_address = resolver_address
        # get the position manager contract facets. We need a separate contract object per facet since they have
        # unique abis:
        self.pm_getter_contract = provider.eth.contract(address = pm_contract_address, abi = pm_contract_getter_abi)
        self.pm_contract = provider.eth.contract(address = pm_contract_address, abi = pm_contract_pm_abi)
        self.pocketbook_contract = provider.eth.contract(address = pm_contract_address, abi = pocketbook_contract_abi)
        self.resolver_contract = provider.eth.contract(address = resolver_address, abi = resolver_contract_abi)

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
            portfolio_id = derive_portfolio_id(account, i)

            #get status of position
            (portfolio_collateral, portfolio_debt, portfolio_req, portfolio_util, portfolio_tails, portfolio_tailDebts, portfolio_tailCredits, portfolio_utils) = self.pm_contract.functions.queryValuesUSD(portfolio_id).call()
            print("     debt: ", portfolio_debt)
            print("     req: ", portfolio_req)
            print("     collateral: ", portfolio_collateral)
            print("     util: ", portfolio_util)
            print("     tails: ", portfolio_tails)
            print("     tailDebts: ", portfolio_tailDebts)
            print("     tailCredits: ", portfolio_tailCredits)
            print("     utils: ", portfolio_utils)

            # is it eligible for liquidation?
            if(((portfolio_util >= self.maxUtil and portfolio_util != 0)) or (portfolio_collateral > 0 and (portfolio_debt / portfolio_collateral >= self.maxUtil))):
                print("     found portfolio to liquidate: ", portfolio_id)
                # get positions in the portfolio
                positions = self.pm_getter_contract.functions.getPortfolio(account, i).call()
                print("     Positions in portfolio:")
                print("     ", positions)
                # how do we liquidate?
                instructions = self.getInstructions(portfolio_id, portfolio_collateral, portfolio_debt, self.liqToken, positions)

                pos_to_liq = []
                for x in range(0, len(positions)):
                    pos_to_liq.append(Web3.to_int(positions[x]))
                # call liquidate
                self.pm_contract.functions.liquidate(portfolio_id, self.resolver_address, positions, [Web3.to_bytes(0x0),instructions,Web3.to_bytes(0x0),Web3.to_bytes(0x0)]).call()

        return "Healthy"

    def getInstructions(self, portfolio_id, portfolio_collateral, portfolio_debt, tokenOut, positions):
        instructions = []
        valueToLiquidate = self.calcCreditAndDebtTargets(portfolio_debt, portfolio_collateral)
        print("valToLiq: " , valueToLiquidate)
        # get the tokens and amounts in the portfolio:
        for position_id in positions:
            (source, pos_type, assetId, sourceAddress, owner) = self.pm_getter_contract.functions.getPosition(position_id).call()
            (source, sourceAddress, tokens, credits, debts, deltas) = self.pocketbook_contract.functions.queryValue(assetId).call()
            print("ID: ", position_id)
            print("     tokens: ", tokens)
            print("     deltas: ", deltas)
            print("     credits: ", credits)
            print("     debts: ", debts)
            if (valueToLiquidate[1] == portfolio_collateral):
                # liquidate the whole portfolio
                for tokenIndex in range(0, len(tokens)):
                    token_in_id = self.get_token_id_from_address(tokens[tokenIndex])
                    token_out_id = self.get_token_id_from_address(tokenOut)
                    if token_in_id is None or token_out_id is None:
                        raise TokenNotInRegistry()
                    return InstructionsLib.create_itos_swap_instruction(False, token_in_id, token_out_id, 0, credits[tokenIndex], 50)

        return [Web3.to_bytes(0x0),Web3.to_bytes(0x0),Web3.to_bytes(0x0),Web3.to_bytes(0x0)]

    # Calculate how much needs to be liquidated. This calculation is based off of LiquidateLib:liquidationFormula() in the position manager
    def calcCreditAndDebtTargets(self, debt, collateral):
        debt_target = 0
        credit_target = 0
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

    # get a the token id given the address of the token and an index to start searching at
    def get_token_id_from_address(self, token_address):
        id = self.resolver_contract.functions.get_token_id_from_address(token_address).call()
        if (id == self.NOT_IN_REGISTRY_CODE):
            return None
        else:
            return id
