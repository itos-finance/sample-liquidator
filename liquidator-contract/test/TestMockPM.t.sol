// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import { LiquidationParams, Liquidator } from "../root/Liquidator.sol";
import { MockBalancerVault } from "@Mocks/MockBalancerVault.sol";
import { MockFactory } from "@Mocks/MockFactory.sol";
import { MockSwapRouter } from "@Mocks/MockSwapRouter.sol";
import { MockPMForPytest, MockPortfolioParams } from "@Mocks/MockPMForPytest.sol";
import { MockERC20 } from "../lib/itos-position-manager/test/mocks/MockERC20.sol";
import { Position, PositionSource } from "../lib/itos-position-manager/src/Position.sol";
import { Record } from "../lib/itos-position-manager/src/Record.sol";



/// Got to make some tests for the mock pm to make sure it's working correctly. It's a little big to be untested
contract MockPMTest is Test {
    Liquidator liquidator;
    MockPMForPytest pm;
    MockBalancerVault balancer;
    MockSwapRouter router;
    MockFactory factory;
    MockERC20 usdc;
    MockERC20 weth;
    MockERC20 tok0;
    MockERC20 tok1;
    address user;
    uint256 BASEX128 = 1 << 128;

    function setUp() public {
        uint256 mintAmount = 1e77;
        router = new MockSwapRouter(100);
        uint256 maxUtil = (75 * BASEX128) / 100;
        uint256 targetUtil = (7 * BASEX128) / 10;
        uint256 liqBonus = (5 * BASEX128) / 100 + BASEX128;
        balancer = new MockBalancerVault();
        factory = new MockFactory();
        liquidator = new Liquidator(address(pm), address(balancer), address(router), address(factory));
        usdc = new MockERC20("USDC", "USDC", 6);
        weth = new MockERC20("WETH", "WETH", 18);
        tok0 = new MockERC20("tok0", "tok0", 18);
        tok1 = new MockERC20("tok1", "tok1", 18);
        pm = new MockPMForPytest(maxUtil, address(usdc), targetUtil, liqBonus);
        usdc.mint(address(balancer), mintAmount);
        weth.mint(address(balancer), mintAmount);
        tok0.mint(address(balancer), mintAmount);
        tok1.mint(address(balancer), mintAmount);
        user = address(0x123);
    }

    function addLiquidatablePortfolio() internal returns (uint256 portfolioID){
        MockPortfolioParams memory params = MockPortfolioParams({
            user: user,
            portNum: 0,
            collateralUSD: 1e18,
            debtUSD: 11e17,
            obligationUSD: 1e18,
            utilization: ((110 * BASEX128) / 100)
        });
        address[] memory tails = new address[](0);
        uint256[] memory tailCredits = new uint256[](0);
        uint256[] memory tailDebts = new uint256[](0);
        uint256[] memory tailDeltaXVars = new uint256[](0);
        uint256[] memory utils = new uint256[](0);
        portfolioID = pm.setupMockPortfolio(params, tails, tailCredits, tailDebts, tailDeltaXVars, utils);
    }

    function testSetupPortfolio() public {
        addLiquidatablePortfolio();
        uint256[][] memory ports = pm.getAllPortfolios(user);
        assertTrue(ports.length > 0);
    }

    function testAddMockPosition() public {
        uint256 portfolioID = addLiquidatablePortfolio();
        (uint256 positionId, ) = pm.addMockPosition(0, 0, address(1), user, 0);
        (uint256 posPortId, Position memory pos) = pm.getPosition(positionId);
        pm.getAllPortfolios(user);
        assertTrue(portfolioID == posPortId);
    }

    function testAddRecordToPosition() public {
        uint256 portfolioId = addLiquidatablePortfolio();
        (uint256 positionId, uint256 assetId)= pm.addMockPosition(0, 0, address(1), user, 0);
        address[] memory tokens = new address[](2);
        tokens[0] = address(usdc);
        tokens[1] = address(weth);
        uint256[] memory credits = new uint256[](2);
        credits[0] = 1e18;
        credits[1] = 0;
        uint256[] memory debts = new uint256[](2);
        debts[0] = 11e17;
        debts[1] = 0;
        uint256[] memory deltas = new uint256[](2);
        deltas[0] = 11e17;
        deltas[1] = 0;
        pm.makeRecord(assetId, 0, address(1), tokens, credits, debts, deltas);
        Record[] memory records = pm.queryValuesNative(portfolioId);
        assertTrue(records.length == 1);
    }

    function testSetupLiquadatablePortfolioHelper() public {
        uint256 portfolioId = pm.setupLiquidatablePortfolio(user, address(usdc), address(weth));
        Record[] memory records = pm.queryValuesNative(portfolioId);
        assertTrue(records.length == 1);
    }

    function testLiquidate() public {
        uint256 portfolioId = pm.setupLiquidatablePortfolio(user, address(usdc), address(weth));
        bytes[] memory instructions = new bytes[](3);
        instructions[0] = new bytes(1);
        instructions[0][0] = bytes1(uint8(0));
        instructions[1] = new bytes(5);
        instructions[1][0] = bytes1(uint8(5));
        instructions[1][4] = bytes1(uint8(1));
        instructions[2] = new bytes(1);
        instructions[2][0] = bytes1(uint8(0));
        uint256[] memory positionIds = new uint256[](1);
        positionIds[0] = 0;
        pm.liquidate(portfolioId, address(0), positionIds, instructions);
        uint256 leng = pm.getRecievedInstructionLength();
        bytes memory instructionsRecieved = pm.getInstructionsRecieved();
        bytes[] memory unflattened = new bytes[](leng);
        uint iter = 0;
        for (uint i = 0; i < instructionsRecieved.length; i++){
            if (instructionsRecieved[i] == bytes1("|")){
                iter += 1;
            } else {
                unflattened[iter] = pm.mergeBytes(unflattened[iter], abi.encodePacked(instructionsRecieved[i]));
            }
        }
        assertTrue(uint8(unflattened[0][0]) == 0);
        assertTrue(uint8(unflattened[1][0]) == 5);
        assertTrue(unflattened[2][0] == 0);
    }
}