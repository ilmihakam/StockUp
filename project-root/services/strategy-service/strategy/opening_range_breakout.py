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
import datetime as date


#Database and Network connection setup
context = ssl.create_default_context()

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
   SELECT id from strategy WHERE name = 'opening_range_breakout'               
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
  end_minute_bar = f"{target_date} 14:00+01:00"

else:
   start_minute_bar = f"{target_date} 13:00:00+00:00"
   end_minute_bar = f"{target_date} 14:00+00:00"

orders = api.list_orders(status='all',limit=500, after=f"{target_date}T13:30:00Z")
existing_order_symbols = [order.symbol for order in orders if order.status != 'canceled']

messages = []


for symbol in symbols:
   minute_bars = api.get_bars(symbol, TimeFrame(1, TimeFrameUnit.Minute), "2024-04-24", "2024-05-10", adjustment='raw').df

   opening_range_mask = (minute_bars.index >= start_minute_bar) & (minute_bars.index < end_minute_bar)
   opening_range_bars = minute_bars.loc[opening_range_mask]

   opening_range_low = opening_range_bars['low'].min() 
   opening_range_high = opening_range_bars['high'].max()
   opening_range = opening_range_high - opening_range_low

   after_opening_range_mask = minute_bars.index >= end_minute_bar 
   after_opening_range_bars = minute_bars.loc[after_opening_range_mask]

   after_opening_range_breakout = after_opening_range_bars[after_opening_range_bars['close'] > opening_range_high]

   if not after_opening_range_breakout.empty:
    if symbol not in existing_order_symbols:
      limit_price = after_opening_range_breakout.iloc[0]['close']

      messages.append(f"placing order for {symbol} at {limit_price}, closed above {opening_range_high}\n\n{after_opening_range_breakout.iloc[0]}\n\n")

      print(f"placing order for {symbol} at {limit_price}, closed above {opening_range_high} at {after_opening_range_breakout.iloc[0]}")

      min_price_increment = 0.05
      rounded_limit_price = round(limit_price / min_price_increment) * min_price_increment
      rounded_take_profit_price = round((limit_price + opening_range) / min_price_increment) * min_price_increment
      rounded_stop_loss_price = round((limit_price - opening_range) / min_price_increment) * min_price_increment

      if not (limit_price == limit_price + opening_range and limit_price == limit_price - opening_range):
       api.submit_order(
         symbol=symbol,
         side='buy',
         type='limit',
         qty=calculate_quantity(limit_price),
         time_in_force='day',
         order_class='bracket',
         limit_price=rounded_limit_price,
         take_profit=dict(
            limit_price= rounded_take_profit_price,
         ),
         stop_loss=dict(
            stop_price= rounded_stop_loss_price,
         )
       )
    else:
      print(f"Already an order for {symbol}, skipping")





with smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT, context=context) as server:
  server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)

  email_message = f"Subject: Trade Notifications for {target_date}\n\n"
  email_message += "\n".join(messages)

  server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_ADDRESS, email_message)
  server.sendmail(config.EMAIL_ADDRESS, config.SMS_EMAIL, email_message)