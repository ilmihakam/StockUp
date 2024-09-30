from alpaca_trade_api.rest import REST, TimeFrame
from datetime import date, datetime
import alpaca_trade_api as tradeapi
import tulipy, numpy
import sqlite3
import config

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row 

cursor = connection.cursor()

cursor.execute("""
        SELECT id, symbol, name FROM stock
""")

rows = cursor.fetchall()

symbols = []
stock_dict = {}
for row in rows:
    symbol = row['symbol']
    symbols.append(symbol)
    stock_dict[symbol] = row['id']

api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, base_url = config.ALPACA_API_URL)

chunk_size = 200


for i in range(0, len(symbols), chunk_size):
    symbol_chunk = symbols[i:i+chunk_size]

    barsets = api.get_bars(symbol_chunk, TimeFrame.Day, "2024-01-01")._raw
    
    for bar in barsets:

        symbol = bar["S"]
        datetime_isoformat = bar["t"]
        date_str = datetime_isoformat.split('T')[0]

        recent_closes = [bar["c"] for bar in barsets if bar["S"] == symbol]
        

        if len(recent_closes) >= 50 and "2024-05-10" == date_str:
          sma_20 = tulipy.sma(numpy.array(recent_closes), period=20)[-1]
          sma_50 = tulipy.sma(numpy.array(recent_closes), period=50)[-1]
          rsi_14 = tulipy.sma(numpy.array(recent_closes), period=14)[-1]
        else:
            sma_20, sma_50, rsi_14 = None, None, None

        print(f"processing symbol {symbol}")
    
        stock_id = stock_dict[bar["S"]]

        cursor.execute("""
        INSERT INTO stock_price (stock_id, date, open, high, low, close, volume, sma_20, sma_50, rsi_14)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (stock_id, date_str, bar["o"], bar["h"], bar["l"], bar["c"], bar["v"], sma_20, sma_50, rsi_14))

connection.commit()