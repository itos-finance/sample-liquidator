// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Script.sol";
import {Liquidator} from "../root/Liquidator.sol";
import { MintableERC20 } from "../lib/itos-position-manager/lib/itos-resolver/test/TestLib/ERC20.u.sol";

contract DeployLiqContractScript is Script {
    function setUp() public {}

    function run() public {
        address deployerAddr = vm.envAddress("DEPLOYER_PUBLIC_KEY");
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address balancerAddr = 0x5Ab2232a0c296f0ae6D73140bFeFc4316970224F;
        address positionManagerAddr = vm.envAddress("diamond");
        address usdc = vm.envAddress("usdc");
        address weth = vm.envAddress("weth");
        address router = vm.envAddress("router");
        vm.startBroadcast(deployerPrivateKey);
        Liquidator liq = new Liquidator(positionManagerAddr, balancerAddr, router);

        vm.stopBroadcast();
        // string memory base = "";
        // vm.serializeAddress(base, "LIQUIDATOR", address(liq));
        // vm.writeJson(base, "./script/deployment/deployment.json");
        console2.log("liquidator contract addr: %s", address(liq));
    }
}
// 400000000000001000000
// 150155943834583101222050520
// 2000000400000000000001001000
// 4000000400000000000001001000