from datetime import date,time


datetime_str = "2024-04-18T04:00:00Z"
date_str = datetime_str.split('T')[0]

print(date_str)
print(date.today().isoformat())