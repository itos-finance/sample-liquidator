// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;


contract MockResolver{
     // The max amount of tokens in the registry is the max uint16 - 1
    uint16 internal constant MAX_TOKENS = 65534;
    // The max uint16 is reserved to be the return value when a token isn't in the registry
    uint16 internal constant NOT_IN_REGISTRY_CODE = 65535;
    uint16 numTokens;
    mapping(uint16 => address) registry;
    mapping(address => uint16) indexOf;
    mapping(address => bool) inserted;

    function addToRegistry(address token) internal returns (uint16 index) {
        require(numTokens <= MAX_TOKENS, "Max tokens reached");
        // registry starts indexing at 0
        registry[numTokens] = token;
        inserted[token] = true;
        indexOf[token] = numTokens;
        index = numTokens;
        numTokens += 1;
    }

    function getTokenIdFromAddress(address token) public view returns (uint16 id){
        if(inserted[token]){
            return indexOf[token];
        } else {
            return NOT_IN_REGISTRY_CODE;
        }
    }

     function addTokenToRegistry(address token) external {
        addToRegistry(token);
    }

}