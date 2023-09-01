// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import { I2sAMMFactory } from "../../lib/itos-position-manager/lib/itos-resolver/lib/V4AMM/lib/interfaces/I2sAMMFactory.sol";
import { IBRConfig } from "../../lib/itos-position-manager/lib/itos-resolver/lib/V4AMM/lib/Borrow/Internal.sol";

contract MockFactory is I2sAMMFactory {

    function getPool(address tokenX, address tokenY, uint24 tickSpacing) public pure returns (address) {
        // we just use the router to swap in our setup so we can just safely return any nonzero address
        return address(1);
    }

    function createPool(
        address _tokenX,
        address _tokenY,
        uint24 tickSpacing
    ) external returns (address pool){
        return address(0);
    }

     function configureFees(
        uint256 _invAlphaX224,
        int128 _betaX96,
        uint128 _maxUtilX128
    ) external{}

    /// Configure the initial borrowing rates.
    function configureBorrowing(
        IBRConfig calldata ibrConfig,
        uint32 rateUpdateIntervalSecs
    ) external{}

    function owner() external view returns (address owner_){}
    function transferOwnership(address _newOwner) external{}
}