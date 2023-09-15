// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IVault.sol";
import "../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IFlashLoanRecipient.sol";
import { PortfolioLiquidationFacet } from "../lib/itos-position-manager/src/facets/PortfolioLiquidationFacet.sol";
import { MockERC20 } from "../lib/itos-position-manager/test/mocks/MockERC20.sol";
import {console2 as console, Script} from "forge-std/Script.sol";
import { MintableERC20 } from "../lib/itos-position-manager/lib/itos-resolver/test/TestLib/ERC20.u.sol";
import { IItosSwapRouter } from  "../lib/itos-position-manager/lib/itos-resolver/src/interfaces/IItosSwapRouter.sol";
import { I2sAMMFactory } from "../lib/itos-position-manager/lib/itos-resolver/lib/V4AMM/lib/interfaces/I2sAMMFactory.sol";

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
    address internal itosFactory;


    /// @notice simple reentrancy guard
    modifier nonReentrant() {
        require(locked == 1, "REENTRANCY");
        locked = 2;
        _;
        locked = 1;
    }

    constructor(address _pm, address _balancer_addr, address _itosRouter, address _itosFactory) {
        pm_addr = _pm;
        vault = IVault(_balancer_addr);
        itosRouter = _itosRouter;
        // init unlocked
        locked = 1;
        itosFactory = _itosFactory;
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


        IERC20[] memory flashLoanERCs = new IERC20[](flashLoanTokens.length);
        for (uint i = 0; i < flashLoanTokens.length; i++){
            flashLoanERCs[i] = IERC20(flashLoanTokens[i]);
        }

        bytes memory userFlashLoanData;

        for (uint i = 0 ; i < flashLoanERCs.length; i++){
            uint256 balance = flashLoanERCs[i].balanceOf(address(this));
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
            tokens[i].approve(params.resolver, amounts[i]);
        }
        PortfolioLiquidationFacet(pm_addr).liquidate(
            params.portfolioId,
            params.resolver,
            params.positionIds,
            params.instructions
        );
        // see what we got
        populateLeftoverBalances();

        for (uint i = 0 ; i < tokens.length; i++){
            int256 predictedBalanceAfterPayback = int256(tokens[i].balanceOf(address(this))) - int256(amounts[i]);
            if (predictedBalanceAfterPayback < 0){
                swapOutLeftovers(tokens[i], -predictedBalanceAfterPayback);
            }
            tokens[i].transfer(address(vault), amounts[i]);
            populateLeftoverBalances();
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
        uint256[] memory balanceBefore = new uint256[](amounts.length);
        // approve resolver to spend the specified amount of token
        for(uint i = 0; i < tokens.length; i++){
            MintableERC20(tokens[i]).mint(address(this), amounts[i]);
            balanceBefore[i] = MockERC20(tokens[i]).balanceOf(address(this));
            // approve the resolver to use that amount
            MockERC20(tokens[i]).approve(resolver, amounts[i]);
        }

        PortfolioLiquidationFacet(pm_addr).liquidate(
            portfolioId,
            resolver,
            positionIds,
            instructions
        );
        // flash loan can be paid back
        require(balanceBefore[0] <= MockERC20(tokens[0]).balanceOf(address(this)), "flash loan pbk");
    }

    /// @dev swaps out excess tokens not needed for the flash loan to the flash loan token. If we swap into more than what is needed to pay the flash loan,
    /// we add that excess balance to leftover balance list so it can also be used to help pay back flash loans
    function swapOutLeftovers(IERC20 tokenOut, int256 amountNeeded) internal {
        uint i = 0;
        while (amountNeeded > 0){
            populateLeftoverBalances();
            if (params.potentialLeftovers[i] != address(tokenOut) && params.leftoverBalances[i] != 0){
                IItosSwapRouter.ExactInputSingleParams memory swapParams = IItosSwapRouter.ExactInputSingleParams({
                    tokenIn: params.potentialLeftovers[i],
                    tokenOut: address(tokenOut),
                    tickSpacing: getTickSpacing(params.potentialLeftovers[i], address(tokenOut)),
                    recipient: address(this),
                    amountIn: params.leftoverBalances[i],
                    amountOutMinimum: 0,
                    deadline: block.timestamp + 25000,
                    sqrtPriceLimitX96: 0
                });

                IERC20(params.potentialLeftovers[i]).approve(itosRouter, params.leftoverBalances[i]);
                (, uint256 amountRecieved) = IItosSwapRouter(itosRouter).exactInputSingle(swapParams);
                amountNeeded -= int256(amountRecieved);
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
        for (uint i = 0; i < params.potentialLeftovers.length; i++){
            params.leftoverBalances[i] = IERC20(params.potentialLeftovers[i]).balanceOf(address(this));
        }
    }

    /// @dev fucntion top get the tick spacing for an itos pool that can be used to swap a token pair.
    /// This function can be called by the liquidator service when assembing instructions as well.
    /// Tests the most likely spacing (32) first, then checks the other possilbe spacing iof that pool
    /// doesn't exist
    function getTickSpacing(address tokenX, address tokenY) public returns (uint24 tickSpacing){
        address pool;
        tickSpacing = 32;
        pool = I2sAMMFactory(itosFactory).getPool(tokenX, tokenY, tickSpacing);
        if (pool == address(0)){
            tickSpacing = 8;
            pool = I2sAMMFactory(itosFactory).getPool(tokenX, tokenY, tickSpacing);
            if (pool == address(0)){
                revert("Pool for token pair doesn't exist");
            }
        }
    }


}
