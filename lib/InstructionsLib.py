from web3 import Web3
import struct



def create_itos_swap_instruction(is_exact_out, tokenIn, tokenOut, amountOut, amountIn, tickSpacing):
    opcode = None
    if(is_exact_out == False):
        # itos swap exact in
        opcode = Web3.to_bytes(3)
    else:
        # itos swap exact in
        opcode = Web3.to_bytes(1)

    # token is uint16. Give 2 bytes:
    tokenIn_bytes = struct.pack('>H', tokenIn) #Web3.to_bytes(int(str(tokenIn), 2))
    print(len(tokenIn_bytes))
    tokenOut_bytes = struct.pack('>H', tokenOut)
    # amountOut is uint256
    amountOut_bytes = Web3.to_bytes(int(str(amountOut), 32))
    # amountIn is uint128
    amountIn_bytes = Web3.to_bytes(int(str(amountIn), 16))
    # uint24
    tickSpacing_bytes = struct.pack('>L', tickSpacing)[:3]
    # see https://docs.python.org/3/library/struct.html#format-characters
    format_str= 'ssssss'
    instruction = struct.pack(format_str, opcode, amountOut_bytes, amountIn_bytes, tickSpacing_bytes, tokenIn_bytes, tokenOut_bytes)
    print(Web3.to_bytes(instruction))
    return Web3.to_bytes(instruction)

def create_uniswap_instruction(is_exact_out, tokenIn, tokenOut, amountOut, amountIn, fee):
    opcode = None
    if(is_exact_out == False):
        # uniswap exact in
        opcode = Web3.to_bytes(4)
    else:
        # uniswap exact out
        opcode = Web3.to_bytes(2)

    # token is uint16. Give 2 bytes:
    tokenIn_bytes = struct.pack('>H', tokenIn) #Web3.to_bytes(int(str(tokenIn), 2))
    print(len(tokenIn_bytes))
    tokenOut_bytes = struct.pack('>H', tokenOut)
    amountOut_bytes = Web3.to_bytes(int(str(amountOut), 32))
    amountIn_bytes = Web3.to_bytes(int(str(amountIn), 16))
    fee_bytes = struct.pack('>L', fee)[:3]
    format_str= 'ssssss'
    instruction = struct.pack(format_str, opcode, amountOut_bytes, amountIn_bytes, fee_bytes, tokenIn_bytes, tokenOut_bytes)
    print(Web3.to_bytes(instruction))
    return Web3.to_bytes(instruction)

def create_transferFrom_instruction(amount, token):
    opcode = Web3.to_bytes(5)
    amount_bytes = Web3.to_bytes(int(str(amount), 32))
    token_bytes = struct.pack('>H', token)
    format_str= 'sss'
    instruction = struct.pack(format_str, opcode, amount_bytes, token_bytes)
    print(Web3.to_bytes(instruction))
    return Web3.to_bytes(instruction)