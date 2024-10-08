import sqlite3, config
import alpaca_trade_api as tradeapi

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row 

cursor = connection.cursor()

cursor.execute("""
        SELECT symbol, name FROM stock
""")

rows = cursor.fetchall()
symbols = [row['symbol'] for row in rows]

api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, base_url = config.ALPACA_API_URL)
assets = api.list_assets()

for asset in assets:
    try:
        if asset.status == 'active' and asset.tradable and '/' not in asset.symbol and asset.symbol not in symbols:
         print(f"Added a new stock {asset.symbol} {asset.name}")
         cursor.execute("INSERT INTO stock (symbol, name, exchange, shortable) VALUES (?,?,?,?)", (asset.symbol, asset.name, asset.exchange, asset.shortable))
    except Exception as e:
        print(asset.symbol)
        print(e)

connection.commit()