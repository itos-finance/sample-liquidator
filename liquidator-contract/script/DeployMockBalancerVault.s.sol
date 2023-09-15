// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Script.sol";
import { MockBalancerVault } from  "@Mocks/MockBalancerVault.sol";
import { MintableERC20 } from "../lib/itos-position-manager/lib/itos-resolver/test/TestLib/ERC20.u.sol";

contract DeployMockBalancerVault is Script {
    function setUp() public {}

    function run() public {
        address deployerAddr = vm.envAddress("DEPLOYER_PUBLIC_KEY");
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        uint256 amount = 1e77;
        address usdc = vm.envAddress("USDC");
        address weth = vm.envAddress("WETH");
        // address luna = vm.envAddress("luna");
        // address tail0 = vm.envAddress("tail0");
        // address tail1 = vm.envAddress("tail1");

        vm.startBroadcast(deployerPrivateKey);
        MockBalancerVault vault = new MockBalancerVault();
        MintableERC20(usdc).mint(address(vault), amount);
        MintableERC20(weth).mint(address(vault), amount);
        // MintableERC20(luna).mint(address(vault), amount);
        // MintableERC20(tail0).mint(address(vault), amount);
        // MintableERC20(tail1).mint(address(vault), amount);
        vm.stopBroadcast();
        //string memory base = "";
        //vm.serializeAddress(base, "VAULT", address(vault));
        //vm.writeJson(base, "./script/deployment/deployment.json");
        console2.log("vault: %s", address(vault));
    }
}
