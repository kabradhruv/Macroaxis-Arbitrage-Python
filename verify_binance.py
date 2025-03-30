from binance import Client
from decimal import Decimal, getcontext, ROUND_DOWN

# Set high precision (28 digits is usually safe for these operations)
getcontext().prec = 28

api_key = ""
api_secret = ""

client = Client(api_key, api_secret)

def verify_triangular_opportunity(sequence, starting_amount=100):
    """
    Given a triangular sequence (e.g., "USDT -> ACH -> BTC -> USDT")
    and a starting amount in USDT, this function uses live Binance prices
    to simulate the trade sequence and verify if the arbitrage opportunity
    is still present.
    
    Trade Sequence:
      1. Buy ACH with USDT from the ACHUSDT pair (use ask price).
      2. Sell ACH for BTC from the ACHBTC pair (use bid price).
      3. Sell BTC for USDT from the BTCUSDT pair (use bid price).
    
    Returns:
      A tuple (final_usdt, arbitrage_ratio) where:
         final_usdt = USDT amount after executing the sequence.
         arbitrage_ratio = final_usdt / starting_amount.
      Returns (None, None) if an error occurs.
    """
    try:
        # Parse the sequence. Expected format: "USDT -> ACH -> BTC -> USDT"
        parts = [p.strip().upper() for p in sequence.split("->")]
        if len(parts) != 4 or parts[0] != parts[-1]:
            print("Invalid sequence format. Must be like 'USDT -> ACH -> BTC -> USDT'")
            return None, None
        
        start, mid, end, final = parts  # e.g., start="USDT", mid="ACH", end="BTC", final="USDT"
        
        # Convert starting_amount to Decimal
        starting_amount_dec = Decimal(str(starting_amount))
        
        # Leg 1: Buy ACH with USDT using pair "ACHUSDT" (ask price)
        mid_start = f"{mid}{start}"
        ticker1 = client.get_orderbook_ticker(symbol=mid_start)
        ask_price_ach_usdt = Decimal(ticker1["askPrice"])
        if ask_price_ach_usdt <= 0:
            print("Invalid ask price for ACHUSDT.")
            return None, None
        ach_amount = starting_amount_dec / ask_price_ach_usdt
        
        # Leg 2: Sell ACH for BTC using pair "ACHBTC" (bid price)
        mid_end = f"{mid}{end}"
        ticker2 = client.get_orderbook_ticker(symbol=mid_end)
        bid_price_ach_btc = Decimal(ticker2["bidPrice"])
        if bid_price_ach_btc <= 0:
            print(f"Invalid bid price for {mid_end}.")
            return None, None
        btc_amount = ach_amount * bid_price_ach_btc
        
        # Leg 3: Sell BTC for USDT using pair "BTCUSDT" (bid price)
        end_start = f"{end}{start}"
        ticker3 = client.get_orderbook_ticker(symbol=end_start)
        bid_price_btc_usdt = Decimal(ticker3["bidPrice"])
        if bid_price_btc_usdt <= 0:
            print(f"Invalid bid price for {end_start}.")
            return None, None
        final_usdt = btc_amount * bid_price_btc_usdt
        
        arbitrage_ratio = final_usdt / starting_amount_dec
        
        # Prepare a Decimal format for 8 decimal places.
        fmt = Decimal('0.00000001')
        
        # Always print the detailed breakdown (you can later change this conditional)
        print(f"1st Pair - {mid_start} and price is - {ask_price_ach_usdt.quantize(fmt)}")
        print(f"2nd Pair - {mid_end} and price is - {bid_price_ach_btc.quantize(fmt)}")
        print(f"3rd Pair - {end_start} and price is - {bid_price_btc_usdt.quantize(fmt)}")
        print(f"--- Verification for sequence: {sequence} ---")
        print(f"Starting with {starting_amount_dec} {start}")
        print(f"Leg 1: Buy {mid} using {start}: {starting_amount_dec} / {ask_price_ach_usdt.quantize(fmt)} = {ach_amount.quantize(fmt)} {mid}")
        print(f"Leg 2: Sell {mid} for {end}: {ach_amount.quantize(fmt)} * {bid_price_ach_btc.quantize(fmt)} = {btc_amount.quantize(fmt)} {end}")
        print(f"Leg 3: Sell {end} for {start}: {btc_amount.quantize(fmt)} * {bid_price_btc_usdt.quantize(fmt)} = {final_usdt.quantize(fmt)} {start}")
        print(f"Arbitrage Ratio: {arbitrage_ratio.quantize(Decimal('0.0001'))}")
        
        return final_usdt, arbitrage_ratio
    
    except Exception as e:
        print(f"Error verifying triangular opportunity for sequence '{sequence}': {e}")
        return None, None

# Example usage:
if __name__ == "__main__":
    # sequence = "USDT -> ONE -> BTC -> USDT"
    sequence = "USDT -> GALA -> BTC -> USDT"
    final_usdt, arb_ratio = verify_triangular_opportunity(sequence, starting_amount=100)
    if final_usdt is not None:
        if arb_ratio > 1:
            print("Arbitrage opportunity confirmed!")
        else:
            print("No arbitrage opportunity found on Binance.")
