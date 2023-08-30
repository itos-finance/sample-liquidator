// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Script.sol";
import { MockPMForPytest } from "@Mocks/MockPMForPytest.sol";
import { MockLiquidator } from "@Mocks/MockLiquidatorContract.sol";
import { MockResolver } from "@Mocks/MockResolver.sol";

/// @dev an easy way to get the linked bytecode needed for pytest unit test is to deploy the contract. Bytecode will be under
/// run-latest.json
contract GenerateBytecodeForPytest is Script {

    function setUp() public {}

    function run() public {
        uint256 BASEX128 = 1 << 128;
        address deployerAddr = vm.envAddress("DEPLOYER_PUBLIC_KEY");
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address liqToken = vm.envAddress("usdc");
        vm.startBroadcast(deployerPrivateKey);
        // values copied from pm's DiamondInit.sol
        uint256 maxUtil = (75 * BASEX128) / 100;
        uint256 targetUtil = (7 * BASEX128) / 10;
        uint256 liqBonus = (5 * BASEX128) / 100 + BASEX128;
        MockPMForPytest mock = new MockPMForPytest(maxUtil, liqToken, targetUtil, liqBonus);
        MockLiquidator liq = new MockLiquidator(address(mock));
        MockResolver resolver = new MockResolver();
        vm.stopBroadcast();
    }
}