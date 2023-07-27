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
        address balancerAddr = address(0);//vm.envAddress("BALANCER_ADDR");
        address positionManagerAddr = vm.envAddress("diamond");
        address usdc = vm.envAddress("usdc");
        address weth = vm.envAddress("weth");
        vm.startBroadcast(deployerPrivateKey);
        Liquidator liq = new Liquidator(positionManagerAddr, balancerAddr);
        MintableERC20(usdc).mint(address(liq), 10000000000e18);
        MintableERC20(weth).mint(address(liq), 10000000000e18);
        vm.stopBroadcast();
        //string memory base = "";
        //vm.serializeAddress(base, "LIQUIDATOR", address(liq));
        //vm.writeJson(base, "./script/output/liquidator.json");
        console2.log("liquidator contract addr: %s", address(liq));
    }
}
