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

        # tails needing liquidation. We must clear this at the end of each liquidation
        self.markedForLiq = []

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
             portfolio_tailUtils) = self.pm_contract.functions.queryValuesUSD(portfolio_id).call()
            if(portfolio_debt > 0 or portfolio_collateral > 0 or len(portfolio_tailCredits) > 0):
                print("     debt: ", portfolio_debt)
                print("     req: ", portfolio_obligation)
                print("     collateral: ", portfolio_collateral)
                print("     util: ", portfolio_util)
                print("     tails: ", portfolio_tails)
                print("     tailDebts: ", portfolio_tailDebts)
                print("     tailCredits: ", portfolio_tailCredits)
                print("     utils: ", portfolio_tailUtils)

            # mark tails for liquidation
            self.populateMarkedForLiq(portfolio_tails, portfolio_tailUtils)

            # is it eligible for liquidation?
            if(((portfolio_util >= self.maxUtil and portfolio_util != 0))
               or (portfolio_collateral > 0 and (portfolio_debt / portfolio_collateral >= self.maxUtil))
               or len(self.markedForLiq) > 0
            ):
                print("     Found portfolio to liquidate: ", portfolio_id)
                # get positions in the portfolio
                positions = self.pm_getter_contract.functions.getPortfolio(account, i).call()
                print("     Positions in portfolio:")
                print("     ", positions)
                resolution_tokens = ResolutionTokens([self.liqToken], [portfolio_collateral], [self.get_token_id_from_address(self.liqToken)])
                # how do we liquidate?
                (close_instructions, additional_resTokens) = self.getInstructions(
                    portfolio_id,
                    portfolio_collateral,
                    portfolio_debt,
                    resolution_tokens,
                    positions,
                    portfolio_util,
                    portfolio_tailUtils
                )
                resolution_tokens.add_resolution_tokens(additional_resTokens)
                print("ciLen: ", len(close_instructions))
                print("CLOSE_INSTRUCTIONS: ", close_instructions)
                pos_to_liq = []
                for x in range(0, len(positions)):
                    pos_to_liq.append(Web3.to_int(positions[x]))
                # call liquidate
                print("resolver: ", self.resolver_address)
                # get tokens to flash loan

                # flash loan 10x the collateral amount to safely have enough TODO param the multiple so user can adjust if fail
                resolution_tokens.amounts[0] = resolution_tokens.amounts[0] * 10

                self.liquidator_contract.functions.liquidateNoFlashLoan(
                    portfolio_id,
                    self.resolver_address,
                    resolution_tokens.tokens,
                    resolution_tokens.amounts,
                    positions,
                    close_instructions
                ).call()

        self.markedForLiq.clear()
        return "Healthy"

    def getInstructions(self, portfolio_id, portfolio_collateral, portfolio_debt, resolution_tokens, positions, portfolio_util):
        instructions = []
        # NOOP for startResolution
        instructions.append(InstructionsLib.NOOP)
        # calculate how much to liquidate
        (debt_to_liquidate, collateral_to_liquidate) = self.calcCreditAndDebtTargets(portfolio_debt, portfolio_collateral, portfolio_util)
        records = self.get_records(portfolio_id)
        self.print_records(records, portfolio_id)
        print("     Collateral to Liq: " , collateral_to_liquidate)
        print("positions: ", positions)
        # loop through the records to determine what we need to pay back
        for record in records:
            #position = self.get_position(position_id)
            if (collateral_to_liquidate == portfolio_collateral):
                if(record.isSourcePocketbook):
                    ix = None
                    print("source is pb")
                    # Deposit. We liq the whole portfolio here so we close this.
                    # We can do a NOOP here since this ix won't be passed to the resolver
                    instructions.append(InstructionsLib.NOOP)
                else:
                    print("source is amm")
                    # source is the AMM. If we have debt to pay in this token, do an exact output swap from any deposit balances we have
                    ix = None
                    for tokenIdx in range(0, len(record.tokens)):
                        if record.debts[tokenIdx] > 0:
                            # if token has debt at it's index that's the fee amt and it must be paid back with the other token in the record.
                            # we add in that amount extra of that token to account for the fee.
                            paybackTokenIdx = 1 if tokenIdx == 0 else 0
                            token_out_id = self.get_token_id_from_address(record.tokens[paybackTokenIdx])
                            (_, balance, tokenId) = resolution_tokens.getPreferredInToken()
                            # TODO We hard code tickSpacing to 50 here. Need to account for different spacings
                            print("swap instruction")
                            # Passing in amountOut 0 tells the resolver to swap into whatever xDelta/yDelta the taker provides.
                            ix1 = InstructionsLib.create_itos_swap_instruction(True, tokenId, token_out_id, 0, balance, 50)
                            ix = InstructionsLib.merge_instructions(ix, ix1)
                        else:
                            ix = InstructionsLib.NOOP
                            print("instr: ", ix)
                    instructions.append(ix)
            else:
                print("partial liq")
                # TODO: add liquidation if only part of the portfolio needs to be liquidated
        # instead of a noop, we may need to get rid of the tails and pay back the flash loan.
        instructions.append(InstructionsLib.NOOP)
        return instructions, resolution_tokens

    # based on LiquidateLib:initLiquidation() in the pm
    def calcCreditAndDebtTargets(self, debt, collateral, portfolio_util):
        collateral_target, debt_target = (0,0)
        if (portfolio_util < self.maxUtil):
            # just liq tails
            collateral_target, debt_target = (0,0)
        elif (portfolio_util >= self.maxUtil and debt == 0):
            # case where no debt has accrued to a position, but the obligation has put it liquidation range.
            # In this case, we liquidate zero debt and base the liquidation bonus on the collateral value.
            collateral_target, debt_target = (0, self.liq_bonus_formula(collateral))
        elif (portfolio_util > self.BASEX128):
            bonus_USD = debt + self.liq_bonus_formula(debt)
            if (bonus_USD > collateral):
                bonus_USD = collateral
            # if the portfolio is over 100% utilized, liquidate the entire debt and collateral
            (debt_target, collateral_target) = (debt, bonus_USD)
        else:
            # liquidate based on the liquidation formula
            (debt_target, collateral_target) = self.liquidationFormula(debt, collateral)
        return debt_target, collateral_target

    # Calculate how much needs to be liquidated. This calculation is based off of LiquidateLib:liquidationFormula() in the position manager
    def liquidationFormula(self, debt, collateral):
        debt_target = 0
        credit_target = 0
        if(debt > collateral):
            debt_target = debt
            credit_target = collateral
        else: #debt / collateral >= maxUtil
            util = debt / collateral
            debt_target = (debt * (util - self.targetUtil)) / ( self.BASEX128 - ((self.targetUtil * self.liquidationBonus) / self.BASEX128) )
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
        print("__________________________________")
        print("POSITION: ", position_id)
        print("rawPos: ", position)
        position_with_values = Position(portfolio_id, position, assetValue)
        print("ID: ", position_id)
        print("portfolio: ", position_with_values.portfolio_id)
        print("     isPocketbook: ", position_with_values.isSourcePocketbook)
        print("     isDebt: ", position_with_values.isPositionDebt)
        print("     tokens: ", position_with_values.tokens)
        print("     deltas: ", position_with_values.deltas)
        print("     credits: ", position_with_values.credits)
        print("     debts: ", position_with_values.debts)
        print("ASSET VALUE: ")
        print(assetValue)
        print("_____________________________________")
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
                    print("         debts: ?")

                print("         deltas ", records[i].deltas[j])

    # populate list of tails needing liquidation
    def populateMarkedForLiq(self, tails, tail_utils):
        for i in range(0, len(tails)):
            if(tail_utils[i] > self.maxUtil):
                self.markedForLiq.append(tails[i])