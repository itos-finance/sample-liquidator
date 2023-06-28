from web3 import Web3
import struct



def create_itos_swap_instruction(is_exact_out, tokenIn, tokenOut, amountOut, amountIn, tickSpacing):
    if(is_exact_out == False):
        opcode = Web3.to_bytes(3)
        # token is uint16. Give 2 bytes:
        tokenIn_bytes = struct.pack('>H', tokenIn)#Web3.to_bytes(int(str(tokenIn), 2))
        print(len(tokenIn_bytes))
        tokenOut_bytes = struct.pack('>H', tokenOut)
        amountOut_bytes = Web3.to_bytes(int(str(amountOut), 32))
        amountIn_bytes = Web3.to_bytes(int(str(amountIn), 16))
        tickSpacing_bytes = struct.pack('>L', tickSpacing)[:3]
        format_str= 'ssssss'
        instruction = struct.pack(format_str,opcode, amountOut_bytes, amountIn_bytes, tickSpacing_bytes, tokenIn_bytes, tokenOut_bytes)
        print(Web3.to_bytes(instruction))
        return Web3.to_bytes(instruction)