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
        address balancerAddr =  0x2a8F692ad09C0DaCf98F5738c2ab9A7A5ca3e26a;
        address positionManagerAddr = 0x26055d2bFd7de6c653b79E3b43B8F59D3f5b38a1;//vm.envAddress("DIAMOND");
        //address usdc = vm.envAddress("USDC");
        //address weth = vm.envAddress("WETH");
        address router = 0x6822bFe69df8F2c857edd8b1f224Fb5805FbFBB6; //vm.envAddress("ROUTER");
        address factory = 0xb2f0D984330C3B3F947523bD919437A303Fa7f81;//vm.envAddress("FACTORY");
        vm.startBroadcast(deployerPrivateKey);
        Liquidator liq = new Liquidator(positionManagerAddr, balancerAddr, router, factory);

        vm.stopBroadcast();
        // string memory base = "";
        // vm.serializeAddress(base, "LIQUIDATOR", address(liq));
        // vm.writeJson(base, "./script/deployment/deployment.json");
        console2.log("liquidator contract addr: %s", address(liq));
    }
}
