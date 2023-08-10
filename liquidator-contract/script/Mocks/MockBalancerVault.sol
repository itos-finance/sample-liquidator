// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "../../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IVault.sol";
import "../../lib/balancer-v2-monorepo/pkg/interfaces/contracts/vault/IFlashLoanRecipient.sol";
import "../../lib/balancer-v2-monorepo/pkg/interfaces/contracts/solidity-utils/helpers/BalancerErrors.sol";
//import "../../lib/balancer-v2-monorepo/pkg/vault/contracts/Fees.sol";

contract MockBalancerVault is IVault {
    error NotImplemented();
     // Flash Loans

    /**
     * @dev Performs a 'flash loan', sending tokens to `recipient`, executing the `receiveFlashLoan` hook on it,
     * and then reverting unless the tokens plus a proportional protocol fee have been returned.
     *
     * The `tokens` and `amounts` arrays must have the same length, and each entry in these indicates the loan amount
     * for each token contract. `tokens` must be sorted in ascending order.
     *
     * The 'userData' field is ignored by the Vault, and forwarded as-is to `recipient` as part of the
     * `receiveFlashLoan` call.
     *
     * Emits `FlashLoan` events.
     */

    function flashLoan(
        IFlashLoanRecipient recipient,
        IERC20[] memory tokens,
        uint256[] memory amounts,
        bytes memory userData
    ) external{
        uint256[] memory feeAmounts = new uint256[](tokens.length);
        uint256[] memory preLoanBalances = new uint256[](tokens.length);

        // Used to ensure `tokens` is sorted in ascending order, which ensures token uniqueness.
        IERC20 previousToken = IERC20(address(0));

        for (uint256 i = 0; i < tokens.length; ++i) {
            IERC20 token = tokens[i];
            uint256 amount = amounts[i];

            _require(token > previousToken, token == IERC20(address(0)) ? Errors.ZERO_TOKEN : Errors.UNSORTED_TOKENS);
            previousToken = token;

            preLoanBalances[i] = token.balanceOf(address(this));
            feeAmounts[i] = _calculateFlashLoanFeeAmount(amount);

            _require(preLoanBalances[i] >= amount, Errors.INSUFFICIENT_FLASH_LOAN_BALANCE);
            token.transfer(address(recipient), amount);
        }

        recipient.receiveFlashLoan(tokens, amounts, feeAmounts, userData);

        for (uint256 i = 0; i < tokens.length; ++i) {
            IERC20 token = tokens[i];
            uint256 preLoanBalance = preLoanBalances[i];

            // Checking for loan repayment first (without accounting for fees) makes for simpler debugging, and results
            // in more accurate revert reasons if the flash loan protocol fee percentage is zero.
            uint256 postLoanBalance = token.balanceOf(address(this));
            _require(postLoanBalance >= preLoanBalance, Errors.INVALID_POST_LOAN_BALANCE);

            // No need for checked arithmetic since we know the loan was fully repaid.
            uint256 receivedFeeAmount = postLoanBalance - preLoanBalance;
            _require(receivedFeeAmount >= feeAmounts[i], Errors.INSUFFICIENT_FLASH_LOAN_FEE_AMOUNT);

            _payFeeAmount(token, receivedFeeAmount);
            emit FlashLoan(recipient, token, amounts[i], receivedFeeAmount);
        }
    }

    function _calculateFlashLoanFeeAmount(uint256 amount) internal returns (uint256){
        return 0;
    }

    function _payFeeAmount(IERC20 token, uint256 receivedFeeAmount) internal {

    }

    // solhint-disable
    function getAuthorizer() external view returns (IAuthorizer){
        revert NotImplemented();
    }

    function setAuthorizer(IAuthorizer newAuthorizer) external {
        revert NotImplemented();
    }


    function hasApprovedRelayer(address user, address relayer) external view returns (bool){
        revert NotImplemented();
    }


    function setRelayerApproval(
        address sender,
        address relayer,
        bool approved
    ) external{
        revert NotImplemented();
    }



    function getInternalBalance(address user, IERC20[] memory tokens) external view returns (uint256[] memory){
        revert NotImplemented();
    }


    function manageUserBalance(UserBalanceOp[] memory ops) external payable{
        revert NotImplemented();
    }


    function registerPool(PoolSpecialization specialization) external returns (bytes32){
        revert NotImplemented();
    }



    function getPool(bytes32 poolId) external view returns (address, PoolSpecialization){
        revert NotImplemented();
    }


    function registerTokens(
        bytes32 poolId,
        IERC20[] memory tokens,
        address[] memory assetManagers
    ) external{
        revert NotImplemented();
    }


    function deregisterTokens(bytes32 poolId, IERC20[] memory tokens) external{
        revert NotImplemented();
    }

    function getPoolTokenInfo(bytes32 poolId, IERC20 token)
        external
        view
        returns (
            uint256 cash,
            uint256 managed,
            uint256 lastChangeBlock,
            address assetManager
        ){
        revert NotImplemented();
    }


    function getPoolTokens(bytes32 poolId)
        external
        view
        returns (
            IERC20[] memory tokens,
            uint256[] memory balances,
            uint256 lastChangeBlock
        ){
        revert NotImplemented();
    }


    function joinPool(
        bytes32 poolId,
        address sender,
        address recipient,
        JoinPoolRequest memory request
    ) external payable{
        revert NotImplemented();
    }



    function exitPool(
        bytes32 poolId,
        address sender,
        address payable recipient,
        ExitPoolRequest memory request
    ) external{
        revert NotImplemented();
    }

    function swap(
        SingleSwap memory singleSwap,
        FundManagement memory funds,
        uint256 limit,
        uint256 deadline
    ) external payable returns (uint256){
        revert NotImplemented();
    }


    function batchSwap(
        SwapKind kind,
        BatchSwapStep[] memory swaps,
        IAsset[] memory assets,
        FundManagement memory funds,
        int256[] memory limits,
        uint256 deadline
    ) external payable returns (int256[] memory){
        revert NotImplemented();
    }



    function queryBatchSwap(
        SwapKind kind,
        BatchSwapStep[] memory swaps,
        IAsset[] memory assets,
        FundManagement memory funds
    ) external returns (int256[] memory assetDeltas){
        revert NotImplemented();
    }


    function managePoolBalance(PoolBalanceOp[] memory ops) external{
        revert NotImplemented();
    }


    function getProtocolFeesCollector() external view returns (IProtocolFeesCollector){
        revert NotImplemented();
    }


    function setPaused(bool paused) external{
        revert NotImplemented();
    }

    function WETH() external view returns (IWETH){
        revert NotImplemented();
    }

    function getActionId(bytes4 selector) external view returns (bytes32){
        revert NotImplemented();
    }
    function getDomainSeparator() external view returns (bytes32){
        revert NotImplemented();
    }
    function getNextNonce(address user) external view returns (uint256){
        revert NotImplemented();
    }

    function getPausedState() external
        view
        returns (
            bool paused,
            uint256 pauseWindowEndTime,
            uint256 bufferPeriodEndTime
        ){
        revert NotImplemented();
    }


}
