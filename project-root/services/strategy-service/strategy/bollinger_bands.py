import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.append(parent_dir)

from shared import config
from shared.timezone import is_dst
from shared.helpers import calculate_quantity

from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
import sqlite3
import alpaca_trade_api as tradeapi
import smtplib, ssl
import tulipy, numpy
import datetime as date

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
   SELECT id from strategy WHERE name = 'bollinger_bands'               
""")

strategy_id = cursor.fetchone()['id']

cursor.execute("""
   SELECT symbol, name
   FROM stock 
   JOIN stock_strategy ON stock_strategy.stock_id = stock.id
   WHERE stock_strategy.strategy_id = ?
""", (strategy_id,))

stocks = cursor.fetchall()
symbols = [stock['symbol'] for stock in stocks]

api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, base_url = config.ALPACA_API_URL)

target_date = "2024-05-10"

if is_dst():
  start_minute_bar = f"{target_date} 13:00:00+01:00"
  end_minute_bar = f"{target_date} 21:00+01:00"

else:
   start_minute_bar = f"{target_date} 13:00:00+00:00"
   end_minute_bar = f"{target_date} 21:00+00:00"

orders = api.list_orders(status='all',limit=500, after=f"{target_date}T13:30:00Z")
existing_order_symbols = [order.symbol for order in orders if order.status != 'canceled']

messages = []

for symbol in symbols:
   minute_bars = api.get_bars(symbol, TimeFrame(1, TimeFrameUnit.Minute), "2024-04-24", "2024-05-10", adjustment='raw').df

   market_open_mask = (minute_bars.index >= start_minute_bar) & (minute_bars.index < end_minute_bar)
   market_open_bars = minute_bars.loc[market_open_mask]

   if len(market_open_bars) >= 20:
      closes = market_open_bars.close.values
      lower, middle, upper = tulipy.bbands(closes, 20, 2)

      current_candle = market_open_bars.iloc[-1]
      previous_candle = market_open_bars.iloc[-2]

      if current_candle.close > lower[-1] and current_candle.close > lower[-2]:
         print(f"{symbol} closed above bollinger band")
         print(current_candle)

      if symbol not in existing_order_symbols:
       limit_price = current_candle.close

       candle_range = current_candle.high - current_candle.low

       print(f"selling short {symbol} at {limit_price}")

       min_price_increment = 0.05
       rounded_limit_price = round(limit_price / min_price_increment) * min_price_increment
       rounded_take_profit_price = round((limit_price + candle_range) / min_price_increment) * min_price_increment
       rounded_stop_loss_price = round((limit_price - candle_range) / min_price_increment) * min_price_increment

       try:
        api.submit_order(
        symbol=symbol,
        side='sell',
        type='limit',
        qty=calculate_quantity(limit_price),
        time_in_force='day',
        order_class='bracket',
        limit_price=rounded_limit_price,
        take_profit=dict(
            limit_price= limit_price + (candle_range * 3),
        ),
        stop_loss=dict(
            stop_price= previous_candle.low,
        ))
        
       except Exception as e:
        print(f"could not submit order {e}")
      else:
       print(f"Already an order for {symbol}, skipping")
    
   #after_opening_range_mask = minute_bars.index >= end_minute_bar 
   #after_opening_range_bars = minute_bars.loc[after_opening_range_mask]

   #after_opening_range_breakout = after_opening_range_bars[after_opening_range_bars['close'] > opening_range_high]