// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import { LiquidationParams, Liquidator } from "../root/Liquidator.sol";
import { MockBalancerVault } from "./Mocks/MockBalancerVault.sol";
import { MockPM } from "./Mocks/MockPM.sol";
import { MockSwapRouter } from "./Mocks/MockSwapRouter.sol";
import { MockERC20 } from "../lib/itos-position-manager/test/mocks/MockERC20.sol";
import { MockFactory } from "./Mocks/MockFactory.sol";

contract LiquidatorProxy {
    function liquidateExt(
        address[] memory flashLoanTokens,
        uint256[] memory flashLoanAmounts,
        address[] memory tokensInvolved,
        uint256 portfolioId,
        address resolver,
        uint256[] calldata positionIds,
        bytes[] calldata instructions,
        address liquidator
    ) external {
        Liquidator(liquidator).liquidate(
            flashLoanTokens,
            flashLoanAmounts,
            tokensInvolved,
            portfolioId,
            resolver,
            positionIds,
            instructions
        );
    }
}

contract LiqTest is Test {

    Liquidator liquidator;
    MockPM pm;
    MockBalancerVault balancer;
    LiquidatorProxy liqProxy;
    MockSwapRouter router;
    MockFactory factory;
    MockERC20 usdc;
    MockERC20 weth;
    MockERC20 tok0;
    MockERC20 tok1;

    function setUp() public {
        uint256 mintAmount = 1e77;
        router = new MockSwapRouter(100);
        pm = new MockPM();
        balancer = new MockBalancerVault();
        factory = new MockFactory();
        liquidator = new Liquidator(address(pm), address(balancer), address(router), address(factory));
        liqProxy = new LiquidatorProxy();
        usdc = new MockERC20("USDC", "USDC", 6);
        weth = new MockERC20("WETH", "WETH", 18);
        tok0 = new MockERC20("tok0", "tok0", 18);
        tok1 = new MockERC20("tok1", "tok1", 18);
        usdc.mint(address(balancer), mintAmount);
        weth.mint(address(balancer), mintAmount);
        tok0.mint(address(balancer), mintAmount);
        tok1.mint(address(balancer), mintAmount);

    }

    function testProfitableLiquidation() public {
        // liquidator got back some usdc, a tiny bit of weth, but a decent amount of tok0 and tok1 from the resolution
        usdc.mint(address(liquidator), 5e17);
        weth.mint(address(liquidator), 7);
        tok0.mint(address(liquidator), 5e18);
        tok1.mint(address(liquidator), 5e18);
        // liquidator flashLoaned some usdc and weth
        address[] memory flashLoanTokens = new address[](2);
        // balancer wants tokens in 123abc order:
       (address tokenA, address tokenB) = address(usdc) > address(weth) ? (address(weth), address(usdc)) : (address(usdc), address(weth));
        flashLoanTokens[0] =  tokenA;
        flashLoanTokens[1] = tokenB;
        uint256[] memory flashLoanAmounts = new uint256[](2);
        flashLoanAmounts[0] = uint256(1e18);
        flashLoanAmounts[1] = uint256(1e18);
        address[] memory tokensInvolved = new address[](2);
        tokensInvolved[0] = address(tok0);
        tokensInvolved[1] = address(tok1);
        // placeholder vals not used by the mocks
        uint256 portId = 0;
        // pass the resolver to be the MockPm so it can tranfer away the flash loan
        address resolver = address(pm);
        uint256[] memory posIds = new uint256[](2);
        posIds[0] = 0;
        posIds[1] = 1;
        bytes[] memory instr = new bytes[](2);
        instr[0] = abi.encode(flashLoanTokens);
        instr[1] = abi.encode(flashLoanAmounts);
        // call liquidate
        liqProxy.liquidateExt(flashLoanTokens, flashLoanAmounts, tokensInvolved, portId, resolver, posIds, instr, address(liquidator));
        // if this doesn't revert we're good
    }

    function testUnProfitableLiquidation() public {
        // liquidator barely got anything back from the liquidation
        usdc.mint(address(liqProxy), 1);
        weth.mint(address(liqProxy), 7);
        tok0.mint(address(liqProxy), 500);
        tok1.mint(address(liqProxy), 89);
        // liquidator flashLoaned some usdc and weth
        address[] memory flashLoanTokens = new address[](2);
        (address tokenA, address tokenB) = address(usdc) > address(weth) ? (address(weth), address(usdc)) : (address(usdc), address(weth));
        flashLoanTokens[0] =  tokenA;
        flashLoanTokens[1] = tokenB;
        uint256[] memory flashLoanAmounts = new uint256[](2);
        flashLoanAmounts[0] = 1e18;
        flashLoanAmounts[1] = 1e18;
        address[] memory tokensInvolved = new address[](2);
        tokensInvolved[0] = address(tok0);
        tokensInvolved[1] = address(tok1);
        // placeholder vals not used by the mocks
        uint256 portId = 0;
        // pass the resolver to be the MockPm so it can tranfer away the flash loan
        address resolver = address(pm);
        uint256[] memory posIds = new uint256[](2);
        posIds[0] = 0;
        posIds[1] = 1;
        bytes[] memory instr = new bytes[](2);
        instr[0] = abi.encode(flashLoanTokens);
        instr[1] = abi.encode(flashLoanAmounts);
        // call liquidate, should revert:
        vm.expectRevert("Can't pay back flashloan");
        liqProxy.liquidateExt(flashLoanTokens, flashLoanAmounts, tokensInvolved, portId, resolver, posIds, instr, address(liquidator));
    }

    function testProfitableLiquidationAllOneToken() public {
        // liquidator got back no usdc, no weth, just tok0
        tok0.mint(address(liquidator), 9e18);
        // liquidator flashLoaned some usdc and weth
        address[] memory flashLoanTokens = new address[](2);
        (address tokenA, address tokenB) = address(usdc) > address(weth) ? (address(weth), address(usdc)) : (address(usdc), address(weth));
        flashLoanTokens[0] =  tokenA;
        flashLoanTokens[1] = tokenB;
        uint256[] memory flashLoanAmounts = new uint256[](2);
        flashLoanAmounts[0] = uint256(1e18);
        flashLoanAmounts[1] = uint256(1e18);
        address[] memory tokensInvolved = new address[](3);
        tokensInvolved[0] = address(tok0);
        tokensInvolved[1] = flashLoanTokens[0];
        tokensInvolved[2] = flashLoanTokens[1];
        // placeholder vals not used by the mocks
        uint256 portId = 0;
        // pass the resolver to be the MockPm so it can tranfer away the flash loan
        address resolver = address(pm);
        uint256[] memory posIds = new uint256[](2);
        posIds[0] = 0;
        posIds[1] = 1;
        bytes[] memory instr = new bytes[](2);
        instr[0] = abi.encode(flashLoanTokens);
        instr[1] = abi.encode(flashLoanAmounts);
        // call liquidate
        liqProxy.liquidateExt(flashLoanTokens, flashLoanAmounts, tokensInvolved, portId, resolver, posIds, instr, address(liquidator));
        // if this doesn't revert we're good
    }
}
