// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import { MockPMForPytest, MockPortfolioParams } from "@Mocks/MockPMForPytest.sol";
import { console2 as console, Script } from "forge-std/Script.sol";
contract MockLiquidator {

    address internal mockPm;

    constructor(address _mockPm) {
        mockPm = _mockPm;
    }

    event Liq(address pm);

    function setPm(address newPm) public {
        mockPm = newPm;
    }

    function liquidate(
        address[] memory flashLoanTokens,
        uint256[] memory flashLoanAmounts,
        address[] memory tokensInvolved,
        uint256 portfolioId,
        address resolver,
        uint256[] calldata positionIds,
        bytes[] calldata instructions
    ) external  {
        //console.log("mockPM: %s", address(mockPm));
        emit Liq(mockPm);
        MockPMForPytest(mockPm).liquidate(portfolioId, resolver, positionIds, instructions);
    }
    // returns hard coded val
    function getTickSpacing(address tokenX, address tokenY) public returns (uint24 tickSpacing){
        tickSpacing = 32;
    }
}