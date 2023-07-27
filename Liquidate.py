from ChainListener import get_provider
from DataStructures.Position import Position
from DataStructures.Record import Record
from DataStructures.ResolutionTokens import ResolutionTokens
from web3 import Web3
from lib.Utils import derive_portfolio_id
from lib.Errors import TokenNotInResolverRegistry
import lib.InstructionsLib as InstructionsLib

class Liquidator:
    #X128 val used in calculation
    BASEX128 = 1 << 128
    # when token isn't in the registry, the resolver returns the max uint16 value as an error code
    NOT_IN_REGISTRY_CODE = 65535

    def __init__(
            self,
            pm_contract_getter_abi,
            pm_contract_pm_abi,
            pocketbook_contract_abi,
            resolver_contract_abi,
            liquidator_contract_abi,
            pm_contract_address,
            resolver_address,
            liquidator_address
        ):
        provider = get_provider()

        self.resolver_address = resolver_address
        # get the position manager contract facets. We need a separate contract object per facet since they have
        # unique abis:
        self.pm_getter_contract = provider.eth.contract(address = pm_contract_address, abi = pm_contract_getter_abi)
        self.pm_contract = provider.eth.contract(address = pm_contract_address, abi = pm_contract_pm_abi)
        self.pocketbook_contract = provider.eth.contract(address = pm_contract_address, abi = pocketbook_contract_abi)
        self.resolver_contract = provider.eth.contract(address = resolver_address, abi = resolver_contract_abi)
        self.liquidator_contract = provider.eth.contract(address = liquidator_address, abi = liquidator_contract_abi)

        # get the static pm config values from getter facet and set them:
        self.maxUtil = self.pm_getter_contract.functions.maxUtil().call()
        self.liqToken = self.pm_getter_contract.functions.defaultToken().call()
        self.targetUtil = self.pm_getter_contract.functions.targetUtil().call()
        self.liquidationBonus = self.pm_getter_contract.functions.liquidationBonus().call()

    #to be called by a function that calls the api to get accounts and discovers one with a liquidate-able portfolio
    def liquidate_account(self, account):
        print("Looking for liquidate-able portfolio on account...")
        portfolios = self.pm_getter_contract.functions.getAllPortfolios(account).call()
        print(portfolios)

        for i in range(0, len(portfolios)):

            # get position id
            portfolio_id = derive_portfolio_id(account, i)

            #get status of position
            (portfolio_collateral,
             portfolio_debt,
             portfolio_obligation,
             portfolio_util,
             portfolio_tails,
             portfolio_tailCredits,
             portfolio_tailDebts,
             _,
             portfolio_utils) = self.pm_contract.functions.queryValuesUSD(portfolio_id).call()
            if(portfolio_debt > 0 or portfolio_collateral > 0 or len(portfolio_tailCredits) > 0):
                print("     debt: ", portfolio_debt)
                print("     req: ", portfolio_obligation)
                print("     collateral: ", portfolio_collateral)
                print("     util: ", portfolio_util)
                print("     tails: ", portfolio_tails)
                print("     tailDebts: ", portfolio_tailDebts)
                print("     tailCredits: ", portfolio_tailCredits)
                print("     utils: ", portfolio_utils)


            # is it eligible for liquidation?
            if(((portfolio_util >= self.maxUtil and portfolio_util != 0)) or (portfolio_collateral > 0 and (portfolio_debt / portfolio_collateral >= self.maxUtil))):
                print("     Found portfolio to liquidate: ", portfolio_id)
                # get positions in the portfolio
                positions = self.pm_getter_contract.functions.getPortfolio(account, i).call()
                print("     Positions in portfolio:")
                print("     ", positions)
                resolution_tokens = ResolutionTokens([self.liqToken], [portfolio_collateral], [self.get_token_id_from_address(self.liqToken)])
                # how do we liquidate?
                (close_instructions, additional_resTokens) = self.getInstructions(portfolio_id, portfolio_collateral, portfolio_debt, resolution_tokens, positions)
                resolution_tokens.add_resolution_tokens(additional_resTokens)
                print("ciLen: ", len(close_instructions))
                print("CLOSE_INSTRUCTIONS: ", close_instructions)
                pos_to_liq = []
                for x in range(0, len(positions)):
                    pos_to_liq.append(Web3.to_int(positions[x]))
                # call liquidate
                print("resolver: ", self.resolver_address)
                # get tokens to flash loan

                # flash loan 10x the debt amount to safely have enough
                amounts = list(map(lambda x: x * 10, resolution_tokens.amounts))

                self.liquidator_contract.functions.liquidateNoFlashLoan(
                    portfolio_id,
                    self.resolver_address,
                    resolution_tokens.tokens,
                    amounts,
                    positions,
                    close_instructions
                ).call()

        return "Healthy"

    def getInstructions(self, portfolio_id, portfolio_collateral, portfolio_debt, resolution_tokens, positions):
        instructions = []
        # NOOP for startResolution
        instructions.append(Web3.to_bytes(0x0))
        # calculate how much to liquidate
        (debt_to_liquidate, collateral_to_liquidate) = self.calcCreditAndDebtTargets(portfolio_debt, portfolio_collateral)
        records = self.get_records(portfolio_id)
        self.print_records(records, portfolio_id)
        print("     Collateral to Liq: " , collateral_to_liquidate)
        # get the tokens and amounts in the portfolio:
        for position_id in positions:
            print("POSITION: ", position_id)
            position = self.get_position(position_id)
            if (collateral_to_liquidate == portfolio_collateral):
                if(position.isSourcePocketbook):
                    ix = None
                    print("source is pb")
                    # Deposit. We liq the whole portfolio here so we close this.
                    # just transferFrom this amount of this position's token from the liquidator to the resolver
                    for tokenIdx in range(0, len(position.tokens)):
                        token_in_id = self.get_token_id_from_address(position.tokens[tokenIdx])
                        amount = position.credits[tokenIdx]
                        ix1 = InstructionsLib.create_transferFrom_instruction(amount, token_in_id)
                        print("ix: transfer")
                        ix = InstructionsLib.merge_instructions(ix, ix1)
                        resolution_tokens.add_resolution_token(position.tokens[tokenIdx], amount, token_in_id)
                    instructions.append(ix)
                else:
                    print("source is amm")
                    # source is the AMM. If we have debt to pay in this token, do an exact output swap from any deposit balances we have
                    ix = None
                    for tokenIdx in range(0, len(position.tokens)):
                        if position.debts[tokenIdx] > 0:
                            token_out_id = self.get_token_id_from_address(position.tokens[tokenIdx])
                            debt = position.debts[tokenIdx]
                            (_, balance, tokenId) = resolution_tokens.getAvailableToken()
                            # TODO We hard code tickSpacing to 50 here. Need to account for different spacings
                            # TODO might not be enough still. May have to add in another transferFrom before swaps
                            # For now, assuming tokens_available[0] should cover it
                            print("swapm instructuion")
                            ix1 = InstructionsLib.create_itos_swap_instruction(True, tokenId, token_out_id, debt, balance, 50)
                            ix = InstructionsLib.merge_instructions(ix, ix1)
                        else:
                            print("transfer instr")
                            token_in_id = self.get_token_id_from_address(position.tokens[tokenIdx])
                            amount = position.credits[tokenIdx]
                            ix1 = InstructionsLib.create_transferFrom_instruction(amount, token_in_id)
                            print("instr: transfer amt ",  amount)
                            print("tokID: ", token_in_id)
                            ix = InstructionsLib.merge_instructions(ix, ix1)
                            print("instr: ", ix)
                            resolution_tokens.add_resolution_token(position.tokens[tokenIdx], amount, token_in_id)
                    instructions.append(ix)
            else:
                print("partial liq")
                # TODO: add liquidation if only part of the portfolio needs to be liquidated
        instructions.append(Web3.to_bytes(0x0))
        return instructions, resolution_tokens

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

    # get a the token id from the resolver given the address of the token
    def get_token_id_from_address(self, token_address):
        id = self.resolver_contract.functions.getTokenIdFromAddress(token_address).call()
        if (id == self.NOT_IN_REGISTRY_CODE):
            raise TokenNotInResolverRegistry()
        else:
            return id

    # get a list of Records given a portfolio id
    def get_records(self, portfolio_id):
        records = self.pm_contract.functions.queryValuesNative(portfolio_id).call()
        recordList = []
        for record in records:
            recordList.append(Record(record))
        return recordList

    # get a Position given its id
    def get_position(self, position_id):
        (portfolio_id, position) = self.pm_getter_contract.functions.getPosition(position_id).call()
        assetValue = self.pocketbook_contract.functions.queryValue(position[2]).call()
        position_with_values = Position(portfolio_id, position, assetValue)
        print("ID: ", position_id)
        print("     isPocketbook: ", position_with_values.isSourcePocketbook)
        print("     isDebt: ", position_with_values.isPositionDebt)
        print("     tokens: ", position_with_values.tokens)
        print("     deltas: ", position_with_values.deltas)
        print("     credits: ", position_with_values.credits)
        print("     debts: ", position_with_values.debts)
        return position_with_values

    def print_records(self, records, portfolio_id):
        print("Logging Records for Portfolio: ", portfolio_id)
        for i in range( 0, len(records)):
            print("     Record ", i)
            hasDebts = len(records[i].debts) > 0
            for j in range(0, len(records[i].tokens)):
                print("         token: ", records[i].tokens[j])
                print("         credits: ", records[i].credits[j])
                if (hasDebts):
                    print("         debts: ", records[i].debts[j])
                else:
                    print("         debts: 0")

                print("         deltas ", records[i].deltas[j])

