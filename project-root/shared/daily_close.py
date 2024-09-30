import alpaca_trade_api as tradeapi
import config

api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, base_url = config.ALPACA_API_URL)

response = api.close_all_positions()

print(response)