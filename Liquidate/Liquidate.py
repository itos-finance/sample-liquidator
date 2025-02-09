from DataStructures.Position import Position
from DataStructures.Record import Record
from DataStructures.ResolutionTokens import ResolutionTokens
from DataStructures.Portfolio import Portfolio
from web3 import Web3
from lib.Utils import derive_portfolio_id
from lib.Errors import TokenNotInResolverRegistry
import lib.InstructionsLib as InstructionsLib
from functools import reduce
import traceback

class Liquidator:
    #X128 val used in calculation
    BASEX128 = 1 << 128
    # when token isn't in the registry, the resolver returns the max uint16 value as an error code
    NOT_IN_REGISTRY_CODE = 65535
    MAX_UINT128 = 340282366920938463463374607431768211455
    # default amount to flashloan. Multiplied by user-supplied flashloan_scalar which can be adjusted if it ends up not being enough
    DEFAULT_IN = 1e18

    def __init__(
            self,
            pm_contract_getter_abi,
            pm_contract_pm_abi,
            pocketbook_contract_abi,
            resolver_contract_abi,
            liquidator_contract_abi,
            pm_contract_address,
            resolver_address,
            liquidator_address,
            provider
        ):

        self.resolver_address = resolver_address
        # get the position manager contract facets. We need a separate contract object per facet since they have
        # unique abis:
        self.pm_getter_contract = provider.eth.contract(address = pm_contract_address, abi = pm_contract_getter_abi)
        self.pm_contract = provider.eth.contract(address = pm_contract_address, abi = pm_contract_pm_abi)
        self.pocketbook_contract = provider.eth.contract(address = pm_contract_address, abi = pocketbook_contract_abi)
        self.resolver_contract = provider.eth.contract(address = resolver_address, abi = resolver_contract_abi)
        self.liquidator_contract = provider.eth.contract(address = liquidator_address, abi = liquidator_contract_abi)
        print("liq addr in liquidate py: ", liquidator_address)

        # get the static pm config values from getter facet and set them:
        self.maxUtil = self.pm_getter_contract.functions.maxUtil().call()
        self.liqToken = self.pm_getter_contract.functions.defaultToken().call()
        self.targetUtil = self.pm_getter_contract.functions.targetUtil().call()
        self.liquidationBonus = self.pm_getter_contract.functions.liquidationBonus().call()

        # tails needing liquidation. We must clear this at the end of each liquidation
        self.markedForLiq = []
        self.provider = provider

    # to be called by a function that calls the api to get accounts and discovers one with a liquidate-able portfolio
    def liquidate_account(self, account, flashloan_scalar, simple_mode):
        print("Looking for liquidate-able portfolio on account...")
        portfolios = self.pm_getter_contract.functions.getAllPortfolios(account).call()
        print(portfolios)
        result = "Healthy"
        for i in range(0, len(portfolios)):
            if len(portfolios[i]) > 0:
                try:
                    portfolio_id = derive_portfolio_id(account, i)
                    needs_liq, portfolio = self.is_portfolio_liquidatable(portfolio_id)
                    if (needs_liq):
                        result = self.liquidate_portfolio(portfolio_id, i, account, portfolio, flashloan_scalar, simple_mode)
                except Exception as e:
                    print("CAUGHT EXCEPTION DURING EXECUTION: ", e)
                    print(traceback.format_exc())
        return result

    def is_portfolio_liquidatable(self, portfolio_id):
        # get status of portfolio:
        (portfolio_collateral,
        portfolio_debt,
        portfolio_obligation,
        portfolio_util,
        portfolio_tails,
        portfolio_tailCredits,
        portfolio_tailDebts,
        portfolio_tail_delta_X_vars,
        portfolio_tailUtils) = self.pm_contract.functions.queryValuesUSD(portfolio_id).call()

        # populate portfolio object
        portfolio = Portfolio(
            portfolio_id,
            portfolio_collateral,
            portfolio_debt,
            portfolio_obligation,
            portfolio_util,
            portfolio_tails,
            portfolio_tailCredits,
            portfolio_tailDebts,
            portfolio_tail_delta_X_vars,
            portfolio_tailUtils
        )
        # print if interesting:
        if(portfolio_debt > 0 or portfolio_collateral > 0 or len(portfolio_tailCredits) > 0):
            print("     debt: ", portfolio_debt)
            print("     req: ", portfolio_obligation)
            print("     collateral: ", portfolio_collateral)
            print("     util: ", portfolio_util)
            print("     tails: ", portfolio_tails)
            print("     tailDebts: ", portfolio_tailDebts)
            print("     tailCredits: ", portfolio_tailCredits)
            print("     utils: ", portfolio_tailUtils)

        # populate tails
        if (len(portfolio_tails) > 0):
            # mark tails for liquidation if there are tails. This gets cleared if nothing gets liquidated
            self.populateMarkedForLiq(portfolio_tails, portfolio_tailUtils)


        # is it eligible for liquidation?
        if (((portfolio_util >= self.maxUtil and portfolio_util != 0))
            or (portfolio_collateral > 0 and (portfolio_debt / portfolio_collateral >= self.maxUtil))
            or len(self.markedForLiq) > 0
        ):
            return True, portfolio
        else:
            return False, None

    def liquidate_portfolio(self, portfolio_id, i, account, portfolio, flashloan_scalar, simple_mode):
        print("     Found portfolio to liquidate: ", portfolio_id)
        # get positions in the portfolio
        positions = self.pm_getter_contract.functions.getPortfolio(account, i).call()

        print("     Positions in portfolio:")
        print("     ", positions)
        # use the entire portfolio collateral value as the base amount of the liq token to flash loan.
        resolution_tokens = ResolutionTokens(self.liqToken, portfolio.collateral_USD, self.get_token_id_from_address(self.liqToken))
        # keep track of out tokens
        tokens_involved = []
        # how do we liquidate?
        (close_instructions, additional_resTokens, pos_to_liq, additional_tokens_involved) = self.get_liquidation_instructions(
            portfolio_id,
            portfolio,
            positions,
            resolution_tokens,
            simple_mode,
            flashloan_scalar,
            tokens_involved
        )
        resolution_tokens.add_resolution_tokens(additional_resTokens)
        tokens_involved += additional_tokens_involved
        print("ciLen: ", len(close_instructions))
        print("CLOSE_INSTRUCTIONS: ", close_instructions)

        print("resolver: ", self.resolver_address)
        # balancer wants the tokens sorted
        sorted_resolution_token_addresses, sorted_resolution_token_amounts = resolution_tokens.get_token_addresses_and_balances_sorted()
        print("sorted")
        print(" calling liq...")
        # call liquidate
        try:
            self.liquidator_contract.functions.liquidate(
                sorted_resolution_token_addresses,
                sorted_resolution_token_amounts,
                tokens_involved,
                portfolio_id,
                self.resolver_address,
                pos_to_liq,
                close_instructions
            ).transact()
        except Exception as e:
            print("CAUGHT EXCEPTION DURING Liq EXECUTION: ", e)
            logs = self.liquidator_contract.events.Liq().get_logs()
            print("logs: ", logs)

        print("liqqed")
        self.markedForLiq.clear()
        return "LIQUIDATED PORTFOLIO: " + str(portfolio_id)

    def get_liquidation_instructions(self, portfolio_id, portfolio, positions, resolution_tokens, simple_mode, flashloan_scalar, tokens_involved):
        instructions = []
        # NOOP for startResolution
        instructions.append(InstructionsLib.NOOP)
        # calculate how much to liquidate
        (debt_to_liquidate, collateral_to_liquidate) = self.calcCreditAndDebtTargets(
            portfolio.debt_USD,
            portfolio.collateral_USD,
            portfolio.utilization
        )
        print("Collateral to Liq: " , collateral_to_liquidate)
        print("positions: ", positions)
        records = self.get_records(portfolio_id)
        self.print_records(records, portfolio_id)
        positions_to_close = []
        # lambda to sum credits. We use this to overestimate the amount of token ot transfer from the liquidator
        sum = lambda lst : reduce(lambda x, y: x + y, lst)

        if (collateral_to_liquidate >= portfolio.collateral_USD):
            print("Total Liq")
            positions_to_close = positions
            i = 0
            # loop through the records to determine what we need to pay back
            for record in records:
                # positions_to_close[i] corresponds to records[i]
                position_to_close = self.get_position(positions_to_close[i])
                position_credits = sum(position_to_close.credits)
                instructions, resolution_tokens, tokens_involved = self.get_instructions_for_position(
                    record,
                    resolution_tokens,
                    instructions,
                    position_credits,
                    simple_mode,
                    flashloan_scalar,
                    tokens_involved
                )
                i += 1
        else:
            print("Partial Liq")
            collateral_liquidated = 0
            iter = 0
            while (collateral_liquidated < collateral_to_liquidate and iter < len(positions)):
                record = records[iter]
                position_to_close = self.get_position(positions[iter])
                position_credits = sum(position_to_close.credits)
                instructions, resolution_tokens, tokens_involved = self.get_instructions_for_position(
                    record,
                    resolution_tokens,
                    instructions,
                    position_credits,
                    simple_mode,
                    flashloan_scalar,
                    tokens_involved
                )
                positions_to_close.append(positions[iter])
                for tokenIdx in range(0, len(position_to_close.tokens)):
                    collateral_liquidated += position_to_close.credits[tokenIdx]
                    if (collateral_liquidated >= collateral_to_liquidate):
                        break
                iter += 1
        # NOOP for endResolution
        instructions.append(InstructionsLib.NOOP)
        return instructions, resolution_tokens, positions_to_close, tokens_involved



    def get_instructions_for_position(self, record, resolution_tokens, instructions, position_credits, simple_mode, flashloan_scalar, tokens_involved):
        if (record.isSourcePocketbook):
            ix = None
            print("source is pocketbook")
            # Deposit. We just close this.
            # We can do a NOOP here since this ix won't be passed to the resolver
            instructions.append(InstructionsLib.NOOP)
        elif (not simple_mode):
            # source is the AMM. If we have debt to pay in this token, do an exact output swap from the token that's returned from the takerClose
            # to the token required to pay back the taker. Due to fees, this may not be enough, so we flash loan some of that token and transfer
            # it to the resolver.
            print("source is amm")
            ix = None
            # taker puts need repayment in token X
            debtTokenIdx = 1
            paybackTokenIdx = 0

            payback_token = record.tokens[paybackTokenIdx]
            debt_token = record.tokens[debtTokenIdx]
            token_out_id = self.get_token_id_from_address(debt_token)
            token_in_id = self.get_token_id_from_address(payback_token)
            transfer_amount = 0
            print("liq token: )", self.liqToken)
            print("payback toke: ", payback_token)
            print("debt token: ", debt_token)
            # if the token swapped out of is the liq token, transfer some more of it from the liquidator to the resolver so the pm can
            # get what it needs in endResolution. Then, we add that amount to resolution_tokens so we flashloan enough. It might make sense to just save this transfer
            # instruction for the endResolution, but we can save gas and just do a bigger transfer here. We use the total position credits to over-estimate how much the pm
            # needs back in endResolution
            if (debt_token == self.liqToken):
                transfer_amount = flashloan_scalar * (position_credits + record.debts[debtTokenIdx])
                resolution_tokens.add_resolution_token(payback_token, transfer_amount, token_in_id)
            else:
                transfer_amount = flashloan_scalar * (position_credits + record.debts[debtTokenIdx])
                resolution_tokens.add_resolution_token(payback_token, transfer_amount, token_in_id)
            tokens_involved = self.add_out_token(tokens_involved, debt_token)
            tokens_involved = self.add_out_token(tokens_involved, payback_token)
            ix1 = InstructionsLib.create_transferFrom_instruction(transfer_amount, token_in_id)
            ix = InstructionsLib.merge_instructions(ix, ix1)
            # We don't know exactly how much tokenIn it will take to swap to the exact out amount we need, but it will be about what we get back from the taker (except fees).
            # To safely have enough in all cases, we pass in the max uint128 value
            ix1 = InstructionsLib.create_itos_swap_instruction(True, token_in_id, token_out_id, 0, self.MAX_UINT128, 50) # TODO tickspacing hardcoded
            ix = InstructionsLib.merge_instructions(ix, ix1)

            print("instr: ", ix)
            instructions.append(ix)
        else:
            # simple mode. go crazy with flash loans
            ix = None
            tails = False

            # If the record has a tail token, we likely won't be able to flashloan the token. Instead,
            # we flashloan more liqToken and swap into the tail to pay any tail debts
            if (record.tokens[0] in self.markedForLiq):
                tails = True
                token_in_id = self.preferredInToken.id
                token_out_id = self.get_token_id_from_address(record.tokens[0])
                # transfer in and then exact in the typical base flashloan amount
                amount = flashloan_scalar * (position_credits + record.debts[0])
                ix1 = InstructionsLib.create_transferFrom_instruction(amount, token_in_id)
                ix = InstructionsLib.merge_instructions(ix, ix1)
                ix1 = InstructionsLib.create_itos_swap_instruction(False, token_in_id, token_out_id, 0, amount, 50) # TODO tickspacing hardcoded
                ix = InstructionsLib.merge_instructions(ix, ix1)
                resolution_tokens.add_resolution_token(self.preferredInToken.token_addr, amount, self.preferredInToken.id)

            if (record.tokens[1] in self.markedForLiq):
                tails = True
                token_in_id = self.preferredInToken.id
                token_out_id = self.get_token_id_from_address(record.tokens[1])
                # transfer in and then exact in swap the typical base flashloan amount into the tail token
                amount = flashloan_scalar * (position_credits + record.debts[1])
                ix1 = InstructionsLib.create_transferFrom_instruction(amount, token_in_id)
                ix = InstructionsLib.merge_instructions(ix, ix1)
                ix1 = InstructionsLib.create_itos_swap_instruction(False, token_in_id, token_out_id, 0, amount, 50) # TODO tickspacing hardcoded
                ix = InstructionsLib.merge_instructions(ix, ix1)
                # keep track of the amount needed for flash loan
                resolution_tokens.add_resolution_token(self.preferredInToken.token_addr, amount, self.preferredInToken.id)
                # keep track of the out token so it can be used to help pay back the flash loan if left over

            if (tails is False):
                print("no tails")
                # easiest case where we flash loan all the tokens that might be needed
                transfer_amount = flashloan_scalar * (position_credits + record.debts[0])
                token_id = self.get_token_id_from_address(record.tokens[0])
                ix1 = InstructionsLib.create_transferFrom_instruction(transfer_amount, token_id)
                ix = InstructionsLib.merge_instructions(ix, ix1)
                resolution_tokens.add_resolution_token(record.tokens[0], transfer_amount, token_id)
                transfer_amount = flashloan_scalar * (position_credits + record.debts[1])
                token_id = self.get_token_id_from_address(record.tokens[1])
                ix1 = InstructionsLib.create_transferFrom_instruction(transfer_amount, token_id)
                ix = InstructionsLib.merge_instructions(ix, ix1)
                resolution_tokens.add_resolution_token(record.tokens[1], transfer_amount, token_id)
                instructions.append(ix)
            # add all the tokens we touch to a list to pass to the liq contract. this helps with the flash loan payback process
            tokens_involved = self.add_out_token(tokens_involved, record.tokens[0])
            tokens_involved = self.add_out_token(tokens_involved, record.tokens[1])

        return instructions, resolution_tokens, tokens_involved


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

    def liq_bonus_formula(self, base):
        # round up
        if ((base * (self.liquidationBonus - self.BASEX128) % self.BASEX128) != 0):
            return ((base * (self.liquidationBonus - self.BASEX128)) / self.BASEX128) + 1
        else:
            return (base * (self.liquidationBonus - self.BASEX128)) / self.BASEX128

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

    # get a Position given its id.
    def get_position(self, position_id):
        (portfolio_id, position) = self.pm_getter_contract.functions.getPosition(position_id).call()
        assetValue = self.pocketbook_contract.functions.queryValue(position[2]).call()
        print("__________________________________")
        print("POSITION: ", position_id)
        print("rawPos: ", position)
        position_with_values = Position(portfolio_id, position_id, position, assetValue)
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

    # print records
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

    def add_out_token(self, tokens_involved, token_to_add):
        if (token_to_add not in tokens_involved):
            print("adding OUT token: ", token_to_add)
            tokens_involved.append(token_to_add)

        return tokens_involved