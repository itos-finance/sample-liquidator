// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;
import { MockERC20 } from "../../lib/itos-position-manager/test/mocks/MockERC20.sol";
import {console2 as console, Script} from "forge-std/Script.sol";

contract MockPM {

    // To simplify the test setup, we mock that the pm does the transfers the resolver would, with simpler instructions
    function liquidate(
        uint256 portfolioId,
        address resolver,
        uint256[] calldata positionIds,
        bytes[] calldata instructions
    ) external {
        // To simulate the liquidator spending the flashloan, just take tokens from it
        address[] memory flashLoanedTokens = abi.decode(instructions[0], (address[]));
        uint256[] memory amountsToTake = abi.decode(instructions[1], (uint256[]));
        for (uint i = 0; i < amountsToTake.length; i++){
            MockERC20(flashLoanedTokens[i]).transferFrom(msg.sender, address(this), amountsToTake[i]);
        }
    }


}