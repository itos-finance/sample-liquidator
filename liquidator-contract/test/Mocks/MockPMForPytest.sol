// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;
import { MockERC20 } from "../../lib/itos-position-manager/test/mocks/MockERC20.sol";
import { console2 as console, Script } from "forge-std/Script.sol";
import { PortfolioData } from "../../lib/itos-position-manager/src/facets/PositionManagerFacet.sol";
import { Position, PositionSource } from "../../lib/itos-position-manager/src/Position.sol";
import { Record } from "../../lib/itos-position-manager/src/Record.sol";
import { PositionType } from "../../lib/itos-position-manager/src/PositionType.sol";

contract MockPMForPytest {

    uint256 constant MAX_PORTFOLIOS = 16;
     // user => portfolioNum => positionid
    mapping(address => uint256[][]) internal portfolios;
    // portfolioID => PortfolioData
    mapping(uint256 => PortfolioData) internal portfolioDatas;
    // positionId => Position
    mapping(uint256 => Position) internal positions;
    // assetId => Record
    mapping(uint256 => Record) internal records;
    // portfolioID => positionIds
    mapping(uint256 => uint256[]) internal portfolioPositions;
    // positionId => portfolioId
    mapping(uint256 => uint256) internal assignments;

    struct LocalVars {
        uint256  _maxUtil;
        address  liqToken;
        uint256  _targetUtil;
        uint256  _liquidationBonus;

        // incremented with every add
        uint256  nextPositionId;
        uint256  nextAssetId;
        // fields used by the test script:
        bytes[]  instructionsRecieved;
        address[]  tokensInvolved;
        uint256[]  amountsToTake;
        uint256[]  amountsToReturn;
    }

    struct MockPortfolioParams{
        address user;
        uint8 portNum;
        uint256 collateralUSD;
        uint256 debtUSD;
        uint256 obligationUSD;
        uint256 utilization;
        address[] tails;
        uint256[] tailCredits;
        uint256[] tailDebts;
        uint256[] tailDeltaXVars;
        uint256[] utils;
    }

    LocalVars internal vars;

    constructor(
        uint256 maxUtilIn,
        address liqTokenIn,
        uint256 targetUtilIn,
        uint256 liquidationBonusIn
    ) {
        vars._maxUtil = maxUtilIn;
        vars.liqToken = liqTokenIn;
        vars._targetUtil = targetUtilIn;
        vars._liquidationBonus = liquidationBonusIn;
        vars.nextPositionId = 0;
        vars.nextAssetId = 0;
    }

    // set up mock portfolio
    function setupMockPortfolio(
       MockPortfolioParams memory params
    ) public returns (uint256 portfolioID){
        portfolioID = derive(params.user, params.portNum);
        PortfolioData memory portData = PortfolioData({
            collateralUSD: params.collateralUSD,
            debtUSD: params.debtUSD,
            obligationUSD: params.obligationUSD,
            utilization: params.utilization,
            tails: params.tails,
            tailCredits: params.tailCredits,
            tailDebts: params.tailDebts,
            tailDeltaXVars: params.tailDeltaXVars,
            utils : params.utils
        });

        portfolioDatas[portfolioID] = portData;
        // init all portfolios to empty arrays
        for (uint i = 0; i < MAX_PORTFOLIOS; i++){
            portfolios[params.user][i] = new uint256[](0);
        }
        portfolioPositions[portfolioID] = new uint256[](0);

    }

    function addMockPosition(
        uint256 positionSource,
        uint256 positionType,
        address sourceAddress,
        address owner,
        uint8 portfolio
    ) public {
        uint256 positionId = vars.nextPositionId;
        vars.nextPositionId ++;
        uint256 portfolioId = derive(owner, portfolio);
        portfolios[owner][portfolio].push(positionId);
        Position memory position = Position({
            source: positionSource == 0 ? PositionSource.AMM : PositionSource.Pocketbook,
            positionType: positionType == 0 ? PositionType.Credit : PositionType.Debt,
            assetId: vars.nextAssetId,
            sourceAddress: sourceAddress,
            owner: owner
        });
        positions[positionId] = position;
        portfolioPositions[portfolioId].push(positionId);
        vars.nextAssetId ++;
        assignments[positionId] = portfolioId;

    }

    function makeRecord(
        uint256 assetId,
        uint256 positionSource,
        address sourceAddress,
        address[] memory tokens,
        uint256[] memory credits,
        uint256[] memory debts,
        uint256[] memory deltas
    ) public {
        Record memory record = Record({
           source: positionSource == 0 ? PositionSource.AMM : PositionSource.Pocketbook,
            sourceAddress: sourceAddress,
           tokens: tokens,
            credits: credits,
            debts: debts,
            deltas: deltas
        });
        records[assetId] = record;
    }

    // TODO need to transfer from the liquidatior but can't use the instructions
    function liquidate(
        uint256 portfolioId,
        address resolver,
        uint256[] calldata positionIds,
        bytes[] calldata instructions
    ) external {
        vars.instructionsRecieved = instructions;
        // To simulate the liquidator spending the flashloan, just take tokens from it
        address[] memory flashLoanedTokens = abi.decode(instructions[0], (address[]));
        for (uint i = 0; i < vars.amountsToTake.length; i++){
            MockERC20(flashLoanedTokens[i]).transferFrom(msg.sender, address(this), vars.amountsToTake[i]);
        }
    }

    function maxUtil() external view returns (uint256) {
        return vars._maxUtil;
    }

    function defaultToken() external view returns (address){
        return vars.liqToken;
    }

    function targetUtil() external view returns (uint256){
        return vars._targetUtil;
    }

    function liquidationBonus() external view returns (uint256){
        return vars._liquidationBonus;
    }

    // function getAllPortfolios(address user) external view returns (uint256[][] memory) {
    //     return portfolios[user];
    // }

    function getPortfolio(address user, uint8 portfolio) external view returns (uint256[] memory) {
        return portfolios[user][portfolio];
    }

    function getPosition(uint256 positionId) external view returns (uint256 portfolioId, Position memory position) {
        position = positions[positionId];
        portfolioId = assignments[positionId];

    }

    function queryValuesUSD(uint256 portfolioID) public returns (PortfolioData memory portfolio){
        return portfolioDatas[portfolioID];
    }

    function queryValuesNative(uint256 portfolioId) public returns (Record[] memory){
        uint256[] memory positionIds = portfolioPositions[portfolioId];
        Record[] memory recs = new Record[](positionIds.length);
        for (uint i = 0; i < positionIds.length; i++){
            (, Position memory pos) = this.getPosition(positionIds[i]);
            recs[i] = queryValue(pos.assetId);
        }
        return recs;
    }

    function queryValue(uint256 assetId) public view returns (Record memory record) {
        return records[assetId];
    }

    /**
     * @notice Derives a portfolioId from a user address and portfolio number (0-255)
     * @param self The address of the user
     * @param portfolio The portfolio number
     * @return portfolioId The portfolioId
     */
    function derive(address self, uint8 portfolio) internal pure returns (uint256) {
        return uint256(uint160(self)) + (uint256(portfolio) << 160);
    }

    // to be called by the test script. Returns the instructions that were sent to the liquidator
    function getInstructionsRecieved() public returns (bytes[] memory){
        return vars.instructionsRecieved;
    }

    function setTokensAndAmountsToTakeOrReturn(address[] memory tokens, uint256[] memory amounts) public {

    }


}