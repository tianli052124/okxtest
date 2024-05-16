import requests
from bs4 import BeautifulSoup
import pandas as pd


def convert_value(value):
    value = value.replace(",", "")
    if "亿" in value:
        return float(value.replace("亿", "")) * 10000
    elif "万" in value:
        return float(value.replace("万", ""))
    elif "%" in value:
        return float(value.replace("%", ""))
    else:
        return value


def scrape_arbitrage_data():
    url = "https://www.okx.com/cn/markets/arbitrage/funding-usdt"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for unsuccessful requests

        soup = BeautifulSoup(response.content, "html.parser")

        table = soup.find("table")

        if table:
            headers = [header.text.strip() for header in table.find_all("th")]
            data_rows = []
            for row in table.find_all("tr"):
                data_rows.append([convert_value(cell.text.strip()) for cell in row.find_all("td")])

            df = pd.DataFrame(data_rows[1:], columns=headers)
            df = df.sort_values("持仓价值", ascending=False)
            return df.head(50)["币种"].tolist()
        else:
            print("Table not found on the webpage.")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to retrieve webpage. {e}")
        return []


if __name__ == "__main__":
    arbitrageset = scrape_arbitrage_data()
    if arbitrageset:
        print(f"Top 50 Crypto for Arbitrage: {arbitrageset}")
    else:
        print("No data retrieved from webpage.")
