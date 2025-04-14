import requests
from bs4 import BeautifulSoup
import csv
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
base_url = "http://books.toscrape.com/catalogue/"
csv_file = 'books_data_with_links.csv'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
max_pages = 10
max_workers = 5
EXCHANGE_API_URL = "https://v6.exchangerate-api.com/v6/9e0416b186915f9f3bc9363c/latest/GBP"

def get_live_exchange_rate():
    """Get current GBP to INR rate"""
    try:
        response = requests.get(EXCHANGE_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data['result'] == 'success':
            return data['conversion_rates']['INR']
    except Exception as e:
        print(f"Exchange API error: {e}")
    return 100  # Fallback rate

def clean_price(price_text):
    """Remove £ symbol and any special characters"""
    return price_text.replace('£', '').replace('Â', '').strip()

def convert_to_rupees(price_text, rate):
    """Convert cleaned GBP price to INR"""
    try:
        price_gbp = float(clean_price(price_text))
        return f"₹{price_gbp * rate:,.2f}"
    except:
        return "N/A"

def scrape_page(page, exchange_rate):
    try:
        url = f"{base_url}page-{page}.html"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        books = soup.select('article.product_pod')
        
        page_books = []
        for book in books:
            try:
                # Extract and clean data
                title = book.h3.a['title'] if book.h3 and book.h3.a else "No title"
                price_gbp = book.select_one('p.price_color').get_text(strip=True)
                cleaned_gbp = f"£{clean_price(price_gbp)}"
                price_inr = convert_to_rupees(price_gbp, exchange_rate)
                book_link = base_url + book.h3.a['href'] if book.h3 and book.h3.a else "N/A"
                
                page_books.append({
                    'Title': title,
                    'Price (£)': cleaned_gbp,
                    'Price (₹)': price_inr,
                    'Availability': book.select_one('p.instock').get_text(strip=True) if book.select_one('p.instock') else "N/A",
                    'Rating': book.p['class'][1] if book.p and 'class' in book.p.attrs else "No rating",
                    'Book Link': book_link,
                    'Page': page
                })
            except Exception as e:
                print(f"Book error (Page {page}): {e}")
                continue
        
        return page_books
    
    except Exception as e:
        print(f"Page {page} failed: {e}")
        return []

def main():
    start_time = time.time()
    
    # Get live exchange rate
    print("Fetching current exchange rate...")
    exchange_rate = get_live_exchange_rate()
    print(f"Current rate: £1 = ₹{exchange_rate:.2f}")
    
    # Scrape pages
    print(f"\nScraping {max_pages} pages...")
    all_books = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(scrape_page, page, exchange_rate) for page in range(1, max_pages + 1)]
        for future in futures:
            all_books.extend(future.result())
    
    # Save results
    with open(csv_file, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['Title', 'Price (£)', 'Price (₹)', 'Availability', 'Rating', 'Book Link', 'Page']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_books)
    
    # Verification
    if all_books:
        sample = all_books[0]
        print("\nSample Verification:")
        print(f"Title: {sample['Title']}")
        print(f"Price: {sample['Price (£)']} | {sample['Price (₹)']}")
        print(f"Link: {sample['Book Link']}")
        print(f"Calculation: {clean_price(sample['Price (£)'])} × {exchange_rate:.2f} = {sample['Price (₹)']}")
    
    print(f"\nDone! Scraped {len(all_books)} books in {time.time() - start_time:.2f}s")
    print(f"Data saved to: {csv_file}")

if __name__ == "__main__":
    main()