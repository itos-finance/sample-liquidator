// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IVault.sol";
import "../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IFlashLoanRecipient.sol";
import { PositionManagerFacet } from "../lib/itos-position-manager/src/facets/PositionManagerFacet.sol";

struct LiquidationParams {
        uint256 portfolioId;
        address resolver;
        uint256[] calldata positionIds;
        bytes[] calldata instructions;
}

contract Liquidator is IFlashLoanRecipient {
    IVault private constant _vault; //= "0xBA12222222228d8Ba445958a75a0704d566BF2C8";
    address internal _pm_addr;
    LiquidationParams internal _params;
    uint256 internal _locked;

    /// @notice simple reentrancy guard
    modifier nonReentrant() {
        require(locked == 1, "REENTRANCY");
        locked = 2;
        _;
        locked = 1;
    }

    constructor(_pm, _balancer_addr) {
        _pm_addr = _pm;
        _vault = _balancer_addr;
        // init unlocked
        _locked = 1;
    }

    function liquidate(
        address[] memory flashLoanTokens,
        uint256[] memory flashLoanAmounts,
        bytes memory userFlashLoanData,
        uint256 portfolioId,
        address resolver,
        uint256[] calldata positionIds,
        bytes[] calldata instructions
    ) external nonReentrant{
        vault.flashLoan(this, tokens, amounts, userData);
    }


    function receiveFlashLoan(
        IERC20[] memory tokens,
        uint256[] memory amounts,
        uint256[] memory feeAmounts,
        bytes memory userData
    ) external override {
        require(msg.sender == vault);
        PositionManagerFacet(pm_addr).liquidate(
            arams.portfolioId,
            params.resolver,
            params.positionIds,
            params.instructions
        );
    }

}
