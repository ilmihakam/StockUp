import config
import sqlite3
import pandas
import csv
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
from datetime import datetime, timedelta

symbols = []
stock_ids = {}

with open('stocks.csv') as f:
   reader = csv.reader(f)
   for line in reader:
    symbols.append(line[1])

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, base_url = config.ALPACA_API_URL)

cursor.execute("""
   SELECT * FROM stock
""")

stocks = cursor.fetchall()

for stock in stocks:
  symbol = stock['symbol']
  stock_ids[symbol] = stock['id']

for symbol in symbols:
  start_date = datetime(2024, 1, 3).date()
  end_date_range = datetime(2024, 5, 10).date()

  while start_date < end_date_range:
    end_date = start_date + timedelta(days=4)

    print(f"=== Fetching minute bars {start_date}-{end_date} for {symbol}")

    minute_data = api.get_bars(symbol, TimeFrame(1, TimeFrameUnit.Minute), "2024-01-03", "2024-05-10", adjustment='raw').df
    minute_data = minute_data.resample('1min').ffill()

    for index, row in minute_data.iterrows():
      
     cursor.execute("""
     INSERT INTO stock_minute_price (stock_id, datetime, open, high, low, close, volume)
     VALUES (?, ?, ?, ?, ?, ?, ?)            
     """, (stock_ids[symbol], index.tz_localize(None).isoformat(), row['open'], row['high'], row['low'], row['close'], row['volume']))

    start_date = start_date + timedelta(days=7)

connection.commit()