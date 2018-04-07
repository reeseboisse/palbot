import datetime
from datetime import timedelta
import json
import urllib.request, urllib.parse


def stock (self, e):
    url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={}&apikey={}"
    if " " in e.input or "," in e.input:
        e.output = "I can only do a single stock symvol such as: AAPL"
    else:
        url = url.format(urllib.parse.quote(e.input), self.botconfig['APIkeys']['alphavantage'])
        response = urllib.request.urlopen(url)
        response = json.loads(response.read().decode('utf-8'))
        today = datetime.date.today().strftime("%Y-%m-%d")
        yesterday = (datetime.date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        symbol = response['Meta Data']["2. Symbol"]
        data = response['Time Series (Daily)']

        closed = False
        if today not in data:
           closed = True
           today = yesterday
           yesterday = (datetime.date.today() - timedelta(days=2)).strftime("%Y-%m-%d")

        current = float(data[today]['4. close'])
        close = float(data[yesterday]['4. close'])

        change = current - close
        perc = (change / current) * 100

        if not closed:
            e.output = "{} : {} || Today's Change: {:.2f} ({:.2f}%)".format(symbol, current, change, perc)
        else:
            e.output = "{} : {} || Yesterday's Change: {:.2f} ({:.2f}%) || MARKET CLOSED".format(symbol, current, change, perc)
          
        

stock.command = "!stock"

# http://query1.finance.yahoo.com/v7/finance/quote?symbols=msft
