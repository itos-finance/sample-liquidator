from web3 import Web3
import struct



def create_itos_swap_instruction(is_exact_out, tokenIn, tokenOut, amountOut, amountIn, tickSpacing):
    opcode = None
    if(is_exact_out == False):
        # itos swap exact in
        opcode = Web3.to_bytes(3)
    else:
        # itos swap exact out
        opcode = Web3.to_bytes(1)

    # token is uint16. Give 2 bytes:
    tokenIn_bytes = struct.pack('>H', tokenIn)
    tokenOut_bytes = struct.pack('>H', tokenOut)
    # amountOut is uint256
    amountOut_bytes = amountOut.to_bytes(32, byteorder='big')
    print("amtOut bytes: ",amountOut_bytes)
    # amountIn is uint128, gets 16 bytes
    amountIn_bytes = amountIn.to_bytes(16, byteorder='big')
    # uint24
    tickSpacing_bytes = struct.pack('>L', tickSpacing)[:3]
    # see https://docs.python.org/3/library/struct.html#format-characters

    instruction = opcode + amountOut_bytes + amountIn_bytes + tickSpacing_bytes + tokenIn_bytes + tokenOut_bytes
    print("instr: ", Web3.to_bytes(instruction))
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
    tokenIn_bytes = struct.pack('>H', tokenIn)
    print(len(tokenIn_bytes))
    tokenOut_bytes = struct.pack('>H', tokenOut)
    amountOut_bytes = amountOut.to_bytes(32, byteorder='big')
    amountIn_bytes = amountIn.to_bytes(16, byteorder='big')
    fee_bytes = struct.pack('>L', fee)[:3]
    format_str= 'ssssss'
    instruction = struct.pack(format_str, opcode, amountOut_bytes, amountIn_bytes, fee_bytes, tokenIn_bytes, tokenOut_bytes)
    print(Web3.to_bytes(instruction))
    return Web3.to_bytes(instruction)

def create_transferFrom_instruction(amount, token):
    opcode = Web3.to_bytes(5)
    amount_bytes = amount.to_bytes(32, byteorder='big')
    token_bytes = struct.pack('>H', token)
    format_str= 'sss'
    instruction = struct.pack(format_str, opcode, amount_bytes, token_bytes)
    print(Web3.to_bytes(instruction))
    return Web3.to_bytes(instruction)