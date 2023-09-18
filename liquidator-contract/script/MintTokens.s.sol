// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Script.sol";
import { MockBalancerVault } from  "@Mocks/MockBalancerVault.sol";
import { MintableERC20 } from "../lib/itos-position-manager/lib/itos-resolver/test/TestLib/ERC20.u.sol";
import {MockERC20} from "../lib/itos-position-manager/test/mocks/MockERC20.sol";
contract MintTokens is Script {
    function setUp() public {}

    function run() public {
        address deployerAddr = vm.envAddress("DEPLOYER_PUBLIC_KEY");
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        uint256 amount = 25e18;
        address usdc = 0x3895AB9717aF8fdB8c4FcFCEDdb220a297df6c49;
        address weth = 0x1e1579056e96818Fd1B478223C0A8B9068A92641;

        vm.startBroadcast(deployerPrivateKey);
        MockERC20(usdc).mint(0x2a8F692ad09C0DaCf98F5738c2ab9A7A5ca3e26a, amount);
        MockERC20(weth).mint(0x2a8F692ad09C0DaCf98F5738c2ab9A7A5ca3e26a, amount);
        MockERC20(usdc).mint(0x997c622d9925Cd622f58bC8Bb2FcA1d7eFF54b39, 10e18);
        MockERC20(weth).mint(0x997c622d9925Cd622f58bC8Bb2FcA1d7eFF54b39, 10e18);

        vm.stopBroadcast();

    }
}
