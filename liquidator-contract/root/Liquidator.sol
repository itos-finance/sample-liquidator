// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IVault.sol";
import "../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IFlashLoanRecipient.sol";
import { PositionManagerFacet } from "../lib/itos-position-manager/src/facets/PositionManagerFacet.sol";
import { MockERC20 } from "../lib/itos-position-manager/test/mocks/MockERC20.sol";
import {console2 as console, Script} from "forge-std/Script.sol";
import { MintableERC20 } from "../lib/itos-position-manager/lib/itos-resolver/test/TestLib/ERC20.u.sol";
import { IItosSwapRouter } from  "../lib/itos-position-manager/lib/itos-resolver/src/interfaces/IItosSwapRouter.sol";

struct LiquidationParams {
    uint256 portfolioId;
    address resolver;
    uint256[] positionIds;
    bytes[] instructions;
    address[] potentialLeftovers;
    uint256[] leftoverBalances;
}

contract Liquidator is IFlashLoanRecipient {
    IVault internal vault; //= "0xBA12222222228d8Ba445958a75a0704d566BF2C8";
    address internal pm_addr;
    LiquidationParams internal params;
    uint256 internal locked;
    address internal itosRouter;


    /// @notice simple reentrancy guard
    modifier nonReentrant() {
        require(locked == 1, "REENTRANCY");
        locked = 2;
        _;
        locked = 1;
    }

    constructor(address _pm, address _balancer_addr, address _itosRouter) {
        pm_addr = _pm;
        vault = IVault(_balancer_addr);
        itosRouter = _itosRouter;
        // init unlocked
        locked = 1;
    }

    function liquidate(
        address[] memory flashLoanTokens,
        uint256[] memory flashLoanAmounts,
        address[] memory tokensInvolved,
        uint256 portfolioId,
        address resolver,
        uint256[] calldata positionIds,
        bytes[] calldata instructions
    ) external nonReentrant{
        params = LiquidationParams({
            portfolioId: portfolioId,
            resolver: resolver,
            positionIds: positionIds,
            instructions: instructions,
            // TODO: might be able to init these to a minimum size we know we'll have to save gas
            potentialLeftovers: tokensInvolved,
            leftoverBalances: new uint256[](tokensInvolved.length)
        });

        for (uint y = 0; y < tokensInvolved.length; y++){
            console.log("out token %d: %s", y, tokensInvolved[y]);
        }

        IERC20[] memory flashLoanERCs = new IERC20[](flashLoanTokens.length);
        for (uint i = 0; i < flashLoanTokens.length; i++){
            flashLoanERCs[i] = IERC20(flashLoanTokens[i]);
        }

        bytes memory userFlashLoanData;

        console.log("Getting flashLoan...");
        for (uint i = 0 ; i < flashLoanERCs.length; i++){
            uint256 balance = flashLoanERCs[i].balanceOf(address(this));
            console.log("%s balance in liq contract: %d", address(flashLoanERCs[i]), balance);
        }

        vault.flashLoan(this, flashLoanERCs, flashLoanAmounts, userFlashLoanData);


        delete params;
    }


    function receiveFlashLoan(
        IERC20[] memory tokens,
        uint256[] memory amounts,
        uint256[] memory feeAmounts,
        bytes memory userData
    ) external override {
        require(msg.sender == address(vault));
        for (uint i = 0 ; i < tokens.length; i++){
            uint256 balance = tokens[i].balanceOf(address(this));
            console.log("%s balance in liq contract after rec: %d", address(tokens[i]), balance);
            tokens[i].approve(params.resolver, amounts[i]);
        }
        PositionManagerFacet(pm_addr).liquidate(
            params.portfolioId,
            params.resolver,
            params.positionIds,
            params.instructions
        );
        console.log("lq. len toks: %d", tokens.length);

        // see what we got
        populateLeftoverBalances();

        for (uint i = 0 ; i < tokens.length; i++){
            console.log("balance of %s: %d", address(tokens[i]), tokens[i].balanceOf(address(this)));
            console.log("transferring %d of %s back to vault", amounts[i], address(tokens[i]));
            int256 predictedBalanceAfterPayback = int256(tokens[i].balanceOf(address(this))) - int256(amounts[i]);
            if (predictedBalanceAfterPayback < 0){
                console.log("   swapping %s, amt needed: %d", address(tokens[i]), uint256(-predictedBalanceAfterPayback));
                swapOutLeftovers(tokens[i], -predictedBalanceAfterPayback);
            }
            console.log("balance of %s before send: %d", address(tokens[i]), tokens[i].balanceOf(address(this)));
            tokens[i].transfer(address(vault), amounts[i]);
            populateLeftoverBalances();
            console.log("transferred");
        }
    }

    // liquidate without a flash loan
    function liquidateNoFlashLoan(
        uint256 portfolioId,
        address resolver,
        address[] memory tokens,
        uint256[] memory amounts,
        uint256[] calldata positionIds,
        bytes[] calldata instructions
    ) external nonReentrant {
        console.log("in liquidateNoFlashLoan");
        uint256[] memory balanceBefore = new uint256[](amounts.length);
        // approve resolver to spend the specified amount of token
        for(uint i = 0; i < tokens.length; i++){
            console.log("approving and minting %d of %s", amounts[i], tokens[i]);
            MintableERC20(tokens[i]).mint(address(this), amounts[i]);
            console.log("balance of %s: %d", tokens[i], MockERC20(tokens[i]).balanceOf(address(this)));
            balanceBefore[i] = MockERC20(tokens[i]).balanceOf(address(this));
            // approve the resolver to use that amount
            MockERC20(tokens[i]).approve(resolver, amounts[i]);
        }

        console.log("calling liq on the pm: %s", pm_addr);
        PositionManagerFacet(pm_addr).liquidate(
            portfolioId,
            resolver,
            positionIds,
            instructions
        );
        console.log("liquidated.gday");
        // flash loan can be paid back
        //require(balanceBefore[0] <= MockERC20(tokens[0]).balanceOf(address(this)), "flash loan pbk");
    }

    /// @dev swaps out excess tokens not needed for the flash loan to the flash loan token. If we swap into more than what is needed to pay the flash loan,
    /// we add that excess balance to leftover balance list so it can also be used to help pay back flash loans
    function swapOutLeftovers(IERC20 tokenOut, int256 amountNeeded) internal {
        console.log("==============================swapping leftovers for %s", address(tokenOut));
        console.log("leftovers:");
        for (uint c = 0; c < params.potentialLeftovers.length; c++){
            console.log("   %d leftover of %s", params.leftoverBalances[c], params.potentialLeftovers[c]);
            console.log("   actual balance of %s: %d", params.potentialLeftovers[c], IERC20(params.potentialLeftovers[c]).balanceOf(address(this)));
        }
        uint i = 0;
        while (amountNeeded > 0){
            populateLeftoverBalances();
            console.log("       idx: %d", i);
            console.log("       amtNeede: %d", uint256(amountNeeded));
            console.log("       balance of %s: %d", params.potentialLeftovers[i], IERC20(params.potentialLeftovers[i]).balanceOf(address(this)));
            if (params.potentialLeftovers[i] != address(tokenOut) && params.leftoverBalances[i] != 0){
                IItosSwapRouter.ExactInputSingleParams memory swapParams = IItosSwapRouter.ExactInputSingleParams({
                    tokenIn: params.potentialLeftovers[i],
                    tokenOut: address(tokenOut),
                    tickSpacing: getTickSpacing(params.potentialLeftovers[i], address(tokenOut)),
                    recipient: address(this),
                    amountIn: params.leftoverBalances[i],
                    amountOutMinimum: 0,
                    sqrtPriceLimitX96: 0
                });
                console.log("tokenIn: %s", params.potentialLeftovers[i]);
                console.log("BALANCE OF TOKENIN: %d", IERC20(params.potentialLeftovers[i]).balanceOf(address(this)));
                console.log("AMOUNT IN OF TOKIN: %d", params.leftoverBalances[i]);
                IERC20(params.potentialLeftovers[i]).approve(itosRouter, params.leftoverBalances[i]);
                uint256 amountRecieved = IItosSwapRouter(itosRouter).exactInputSingle(swapParams);
                console.log("amount rec of %s: %d", address(tokenOut), amountRecieved);
                amountNeeded -= int256(amountRecieved);
                console.log("amount needed: %d", uint256(amountNeeded));
            }
            i += 1;
            if (i >= params.potentialLeftovers.length && amountNeeded > 0){
                revert("Can't pay back flashloan");
            }
        }
    }

    /// @dev populates array of potential leftover token balances. Does a balance query for each token, so
    /// it's kind of expensive gas-wise. These balances are used to help pay back the flash loan
    function populateLeftoverBalances() internal {
        console.log("populatin");
        for (uint i = 0; i < params.potentialLeftovers.length; i++){
            params.leftoverBalances[i] = IERC20(params.potentialLeftovers[i]).balanceOf(address(this));
        }
    }

    /// @dev fucntion top get the tick spacing for an itos pool that can be uised to swap a token pair.
    /// TODO make factory call once we get the other pieces working. For now, just return 50.
    /// This function can be called by the liquidator service when assembing instructions as well
    function getTickSpacing(address tokenX, address tokenY) public returns (uint24 tickSpacing){
        // TODO hard coded val
        tickSpacing = 50;
    }


}
