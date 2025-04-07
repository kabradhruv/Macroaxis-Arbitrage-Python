import aiohttp
import asyncio
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import sys
from verify_binance import verify_triangular_opportunity

# Set the profit threshold (in percent, e.g., 1 means 1%)
PROFIT_THRESHOLD_MACROAXIS = 1 # For Macroaxis
PROFIT_THRESHOLD_FOR_BINANCE = 1

# Use WindowsSelectorEventLoopPolicy on Windows to work with aiodns.
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Custom headers to simulate a real browser request
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.93 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/"
}

CONCURRENCY_LIMIT = 50  # Adjust this to a lower number if needed
MAX_RETRIES = 3         # Number of retries per URL
REQUEST_TIMEOUT = 10    # Timeout per request in seconds


def verify_from_binance(sequence):
    final_usdt, arb_ratio = verify_triangular_opportunity(sequence, starting_amount=100 , PROFIT_THRESHOLD_VEIRFY = PROFIT_THRESHOLD_FOR_BINANCE)

def load_urls_from_csv(csv_file):
    """Load URLs from a CSV file."""
    urls = []
    try:
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    urls.append(row[0].strip())
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return urls

def extract_opportunities(html, threshold):
    """
    Parse the HTML and extract arbitrage opportunities from rows that 
    start with USDT. Returns a list of tuples:
      (sequence_string, profit_ratio)
    where sequence_string is like "USDT -> BTC -> ALT -> USDT".
    """
    soup = BeautifulSoup(html, "html.parser")
    opportunities = []

    container = soup.find("div", class_="esgTile p-l-10 p-r-10")
    if not container:
        print("No container found.")
        return opportunities

    table = container.find("table", class_="table")
    if not table:
        print("No table found.")
        return opportunities

    rows = table.find_all("tr")
    if len(rows) < 2:
        print("Not enough rows found.")
        return opportunities

    # Skip the header row (assumed to be the first row)
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue  # Skip row if structure is unexpected

        try:
            # Extract start and buy currencies from cells:
            start_currency = cells[0].find("span", class_="p-5").get_text(strip=True)
            buy1 = cells[1].find("span", class_="p-5").get_text(strip=True)
            buy2 = cells[3].find("span", class_="p-5").get_text(strip=True)
            buy3 = cells[5].find("span", class_="p-5").get_text(strip=True)
        except AttributeError:
            continue  # Skip if any cell doesn't have expected structure

        # Only consider sequences starting with "USDT"
        if start_currency.upper() != "USDT":
            continue

        sequence = f"{start_currency} -> {buy1} -> {buy2} -> {buy3}"

        # Extract profit ratio from the 7th cell (index 6)
        profit_td = cells[6]
        profit_div = profit_td.find("div", class_="esgTile p-l-10 p-r-10")
        if not profit_div:
            continue

        profit_text = profit_div.get_text(separator=" ", strip=True)
        try:
            profit_value = float(profit_text.split()[0])
        except (ValueError, IndexError):
            continue

        if profit_value > threshold:
            opportunities.append((sequence, profit_value))

    return opportunities

async def fetch(session, url):
    """
    Fetch the content of the URL asynchronously with retry logic.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT) as response:
                if response.status != 200:
                    print(f"Failed to retrieve URL {url} (Status: {response.status}) on attempt {attempt}")
                    await asyncio.sleep(0.5)  # short delay before retrying
                    continue
                return await response.text()
        except Exception as e:
            print(f"Error fetching {url} on attempt {attempt}: {e}")
            await asyncio.sleep(0.5)
    return None

async def scrape_and_find(sem, session, url):
    """
    Scrape the provided URL, extract opportunities,
    and print those with a profit ratio above the threshold.
    Only opportunities starting with 'USDT' are reported.
    """
    async with sem:
        html = await fetch(session, url)
    if html is None:
        return

    opportunities = extract_opportunities(html, PROFIT_THRESHOLD_MACROAXIS)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if opportunities:
        for seq, profit in opportunities:
            print(f"{timestamp} | Opportunity: {seq} | Profit Ratio: {profit:.2f}% | url: {url}")
            verify_from_binance(seq)

async def main():
    csv_file = "usdt_url_list.csv"  # Replace with your CSV file path
    urls = load_urls_from_csv(csv_file)
    if not urls:
        print("No URLs loaded from CSV.")
        return

    print(f"Loaded {len(urls)} URLs. Starting asynchronous scraping (USDT sequences only)...")
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [scrape_and_find(sem, session, url) for url in urls]
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
