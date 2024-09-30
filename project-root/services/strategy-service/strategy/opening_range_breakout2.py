import sys
import os 

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.join(current_dir, '..', '..', '..'))
sys.path.append(parent_dir)

import pandas
from datetime import date, datetime, time, timedelta

class OpeningRangeBreakout:

    def __init__(self, num_opening_bars):

        self.num_opening_bars = num_opening_bars
        self.opening_range_low = 0
        self.opening_range_high = 0
        self.opening_range = 0
        self.bought_today = False
        self.order = None

    def log(self, message):

        print(message)

    def on_order(self):
        raise NotImplementedError("This method should be overridden by the adapter.")

    def get_current_price(self):
        raise NotImplementedError("This method should be overriden by the adapter")
    
    def get_current_time(self):
        raise NotImplementedError("This method should be overriden by the adapter")

    def reset_opening_range(self):

        current_bar_datetime = self.data.num2date(self.data.datetime[0])
        previous_bar_datetime = self.data.num2date(self.data.datetime[-1])

        if current_bar_datetime.date() != previous_bar_datetime.date():
            self.opening_range_low = self.data.low[0]
            self.opening_range_high = self.data.high[0]
            self.bought_today = False

    def update_opening_range(self):

        current_bar_datetime = self.data.num2date(self.data.datetime[0])
        current_price = self.get_current_price()

        opening_range_start_time = time(9,30,0)
        dt = datetime.combine(date.today(), opening_range_start_time) + timedelta(minutes=self.p.num_opening_bars)
        opening_range_end_time = dt.time()

        if current_bar_datetime.time() >= opening_range_start_time \
            and current_bar_datetime.time() < opening_range_end_time:           
            self.opening_range_high = max(self.opening_range_high, current_price)
            self.opening_range_low = min(self.opening_range_low, current_price)
            self.opening_range = self.opening_range_high - self.opening_range_low
        
    def evaluate_trades(self):
        current_price = self.get_current_price()
        current_bar_datetime = self.data.num2date(self.data.datetime[0])

        if current_price > (self.opening_range_high + self.opening_range):
            self.execute_trade('sell')
                
        if current_price > self.opening_range_high and not self.bought_today:
            self.execute_trade('buy')
            self.bought_today = True

        if current_price < (self.opening_range_high - self.opening_range):
            self.execute_trade('sell')

        if current_bar_datetime.time() >= time(15, 45, 0):
            self.log("RUNNING OUT OF TIME - LIQUIDATING POSITION")
            self.execute_trade('sell')

    def execute_trade(self, side):
        raise NotImplementedError("This method should be overriden by the")