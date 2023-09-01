// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import { IItosSwapRouter } from  "../../lib/itos-position-manager/lib/itos-resolver/src/interfaces/IItosSwapRouter.sol";
import { MockERC20 } from "../../lib/itos-position-manager/test/mocks/MockERC20.sol";

contract MockSwapRouter is IItosSwapRouter {

    // toggling this amount is useful for changing how profitable a liquidation is
    uint256 internal _returnFactor;

    /// @param returnFactor used to scale the amount of tokenOut to return in an exact in swap. A value of 100 will yield 100%
    /// of the amountIn value being returned in tokenOut (1:1 swap). amountOut = returnFactor * amountIn / 100
    constructor(uint256 returnFactor) {
        _returnFactor = returnFactor;
    }

    function calculateAmountToReturn(uint256 amountIn) internal returns (uint256 amountOut){
        amountOut = _returnFactor * amountIn / 100;
    }

    function setReturnFactor(uint256 newFactor) external {
        _returnFactor = newFactor;
    }

    function exactOutputSingle(ExactOutputSingleParams memory params) external payable returns (uint256 amountOut){
        uint256 amountIn = params.amountInMaximum > params.amountOut ? params.amountOut : params.amountInMaximum;
        MockERC20(params.tokenIn).transferFrom(msg.sender, address(this), amountIn);
        MockERC20(params.tokenOut).mint(params.recipient, params.amountOut);
        return params.amountOut;
    }

    function exactInputSingle(ExactInputSingleParams memory params) external payable returns (uint256 amountOut){
        uint256 calculatedReturnAmount = calculateAmountToReturn(params.amountIn);
        amountOut = params.amountOutMinimum > params.amountIn ? params.amountOutMinimum : calculatedReturnAmount;
        MockERC20(params.tokenIn).transferFrom(msg.sender, address(this), params.amountIn);
        MockERC20(params.tokenOut).mint(params.recipient, amountOut);
        return amountOut;
    }
}