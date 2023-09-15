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
        address balancerAddr =  0x2B0d36FACD61B71CC05ab8F3D2355ec3631C0dd5;

        address positionManagerAddr = vm.envAddress("DIAMOND");
        address usdc = vm.envAddress("USDC");
        address weth = vm.envAddress("WETH");
        address router = vm.envAddress("ROUTER");
        address factory = vm.envAddress("FACTORY");
        vm.startBroadcast(deployerPrivateKey);
        Liquidator liq = new Liquidator(positionManagerAddr, balancerAddr, router, factory);

        vm.stopBroadcast();
        // string memory base = "";
        // vm.serializeAddress(base, "LIQUIDATOR", address(liq));
        // vm.writeJson(base, "./script/deployment/deployment.json");
        console2.log("liquidator contract addr: %s", address(liq));
    }
}
