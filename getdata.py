import requests
from bs4 import BeautifulSoup
import pandas as pd
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


# Define a function to convert values
def convert_value(value):
    value = value.replace(',', '')
    if '亿' in value:
        return float(value.replace('亿', '')) * 10000
    elif '万' in value:
        return float(value.replace('万', ''))
    elif '%' in value:
        return float(value.replace('%',''))
    else:
        return value

# Convert Dataframe value
df = df.map(convert_value)

#Sort by market value
df = df.sort_values('持仓价值',ascending=False)

df = df.head(50)

arbitrageset = df['币种'].tolist()
print(df)
print(arbitrageset)