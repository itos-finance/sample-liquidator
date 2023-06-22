from web3 import Web3


class InstructionsLib:

    def __init__():
        pass

    def create_itos_swap_instruction(is_exact_out, tokenIn, tokenOut, amountOut, amountIn, tickSpacing):
        if(is_exact_out == False):
            opcode = Web3.to_bytes(3)
            # token is uint16. Give 2 bytes:
            tokenIn_bytes = Web3.to_bytes(int(tokenIn, 2))
            print(len(tokenIn_bytes))
            tokenOut_bytes = Web3.to_bytes(int(tokenOut, 2))
            amountOut_bytes = Web3.to_bytes(int(amountOut, 32))
            amountIn_bytes = Web3.to_bytes(int(amountIn, 16))
            tickSpacing_bytes = Web3.to_bytes(int(tickSpacing, 3))

            return [opcode, amountOut_bytes, amountIn_bytes, tickSpacing_bytes, tokenIn_bytes, tokenOut_bytes]