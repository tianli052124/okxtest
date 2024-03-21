import requests
from bs4 import BeautifulSoup
import pandas as pd

pd.set_option("display.max_rows", None)

# Send a GET request to the URL
url = "https://www.okx.com/cn/markets/arbitrage/funding-usdt"
response = requests.get(url)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the table element
    table = soup.find("table")

    if table:
        # Extract table headers
        headers = [header.text.strip() for header in table.find_all("th")]

        # Extract table rows
        rows = []
        for row in table.find_all("tr"):
            rows.append([cell.text.strip() for cell in row.find_all("td")])

        # Create a DataFrame
        df = pd.DataFrame(rows[1:], columns=headers)

        # Print the DataFrame
        # print(df)

    else:
        print("Table not found on the webpage.")

else:
    print("Failed to retrieve the webpage. Status code:", response.status_code)

print(df.sort_values(by=["持仓价值"], ascending=False))
