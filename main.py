import asyncio
import os
import re
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup

# No API key needed for this version

async def scrape_page(url, crawler, use_playwright=False):
    # Fetches HTML content of a given URL, optionally using Playwright
    print(f"  Fetching: {url} {'(using Playwright)' if use_playwright else ''}")
    try:
        result = await crawler.arun(url=url, use_playwright=use_playwright) 
        # Check if html content exists and is not empty
        if result and result.html:
            print(f"  Success fetching: {url}")
            return result.html
        else:
            print(f"  Failed fetching or empty content: {url}")
            return None
    except Exception as e:
        print(f"  Error during fetch for {url}: {e}")
        return None

async def extract_listing_links(html, base_url):
    # Extracts links that match the property listing pattern
    if not html:
        print("No HTML content to extract links from.")
        return set()
        
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    
    # Regex based on user feedback: /kibris/kiralik-emlak/...
    # Making it flexible for different locations/types ending in .html
    listing_pattern = re.compile(r'/kibris/(kiralik|satilik)-emlak/[\w-]+(?:/.*)?-\d+\.html')
    
    anchor_tags = soup.find_all('a', href=listing_pattern)
    print(f"Found {len(anchor_tags)} potential listing anchor tags using pattern.")
    
    for tag in anchor_tags:
        href = tag['href'].strip()
        absolute_url = urljoin(base_url, href) 
        # Final check for validity
        parsed_url = urlparse(absolute_url)
        if parsed_url.scheme in ['http', 'https'] and parsed_url.netloc == 'www.101evler.com':
            links.add(absolute_url)
            
    print(f"Extracted {len(links)} unique listing links.")
    return links

def get_listing_id_from_url(url):
    # Extract listing ID from URL
    match = re.search(r'-(\d+)\.html$', url)
    if match:
        return match.group(1)
    return None

def get_existing_listing_ids(output_dir):
    # Get list of listing IDs that are already scraped
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        return set()
    
    existing_ids = set()
    for filename in os.listdir(output_dir):
        if filename.endswith('.html'):
            # Extract ID from filename (e.g., 123456.html -> 123456)
            try:
                listing_id = filename.split('.')[0]
                if listing_id.isdigit():
                    existing_ids.add(listing_id)
            except:
                pass
    
    print(f"Found {len(existing_ids)} existing listing files in '{output_dir}'")
    return existing_ids

def get_existing_search_pages(pages_dir):
    # Get list of search pages that are already scraped
    if not os.path.exists(pages_dir):
        os.makedirs(pages_dir)
        return set()
    
    existing_pages = set()
    for filename in os.listdir(pages_dir):
        if filename.startswith('search_page_') and filename.endswith('.html'):
            try:
                # Extract page number from filename (e.g., search_page_1_playwright.html -> 1)
                page_num = int(filename.split('_')[2])
                existing_pages.add(page_num)
            except:
                pass
    
    print(f"Found {len(existing_pages)} existing search pages in '{pages_dir}'")
    return existing_pages

async def save_html_to_file(html_content, url, output_dir):
    # Saves HTML content to a file named after the listing ID
    if not html_content:
        print(f"  Skipping save for {url} due to empty content.")
        return
        
    # Extract a filename from the URL, e.g., the listing ID
    match = re.search(r'-(\d+)\.html$', url)
    if match:
        filename = f"{match.group(1)}.html"
    else:
        # Fallback filename if pattern doesn't match
        filename = os.path.basename(urlparse(url).path).replace('.html', '') + ".html"
        if not filename or filename == ".html": # Added check for empty filename
            filename = f"listing_{hash(url)}.html" # Use hash as last resort
            
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  Saved HTML for {url} to {filepath}")
    except Exception as e:
        print(f"  Error saving HTML for {url}: {e}")

async def save_search_page(html_content, page_num, pages_dir):
    # Saves search page HTML content to a file in the pages directory
    if not html_content:
        print(f"  Skipping save for search page {page_num} due to empty content.")
        return
        
    # Ensure pages directory exists
    if not os.path.exists(pages_dir):
        os.makedirs(pages_dir)
        
    filename = f"search_page_{page_num}_playwright.html"
    filepath = os.path.join(pages_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  Saved HTML for search page {page_num} to {filepath}")
    except Exception as e:
        print(f"  Error saving HTML for search page {page_num}: {e}")

async def main():
    base_search_url = "https://www.101evler.com/kibris/kiralik-daire/magusa"
    max_search_pages = 5 # Number of search result pages to scrape for links
    output_dir = "listings"
    pages_dir = "pages"
    all_listing_links = set()
    
    # Create pages directory if it doesn't exist
    if not os.path.exists(pages_dir):
        os.makedirs(pages_dir)
    
    # Get existing listing IDs before starting
    existing_listing_ids = get_existing_listing_ids(output_dir)
    print(f"Will skip {len(existing_listing_ids)} listings that are already saved.")
    
    # Get existing search pages before starting
    existing_search_pages = get_existing_search_pages(pages_dir)
    print(f"Will skip {len(existing_search_pages)} search pages that are already saved.")
    
    print(f"Starting link extraction from search pages...")

    async with AsyncWebCrawler(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
        }
    ) as crawler:
        
        # 1. Scrape search result pages using PLAYWRIGHT to gather listing links
        for page_num in range(1, max_search_pages + 1):
            search_page_url = f"{base_search_url}?&page={page_num}"
            print(f"\n--- Processing Search Page {page_num}/{max_search_pages} for links --- ")
            
            # Check if this search page already exists
            if page_num in existing_search_pages:
                print(f"Search page {page_num} already exists - loading from file")
                page_file = os.path.join(pages_dir, f"search_page_{page_num}_playwright.html")
                try:
                    with open(page_file, 'r', encoding='utf-8') as f:
                        html = f.read()
                    if html:
                        print(f"Loaded search page {page_num} from file")
                    else:
                        print(f"Empty file for search page {page_num}, will re-scrape")
                        html = None
                except Exception as e:
                    print(f"Error loading search page {page_num} from file: {e}")
                    html = None
            else:
                # Use Playwright for the search pages
                html = await scrape_page(search_page_url, crawler, use_playwright=True)
                # Save the search page
                if html:
                    await save_search_page(html, page_num, pages_dir)
            
            if html:
                base_for_relative = search_page_url.split('?')[0]
                links_on_page = await extract_listing_links(html, base_for_relative)
                all_listing_links.update(links_on_page)
                print(f"Total unique links found so far: {len(all_listing_links)}")
            else:
                print(f"Skipping search page {page_num} due to fetch error or empty content.")
            
            # Add a random component to the delay to make the scraping pattern less predictable
            # Only wait if we're fetching the next page (not on the last page)
            if page_num < max_search_pages and page_num not in existing_search_pages:
                random_delay = 4 + (page_num % 3)  # 4-6 seconds based on page number
                print(f"Waiting {random_delay} seconds before next search page...")
                await asyncio.sleep(random_delay)

        print(f"\nFound a total of {len(all_listing_links)} unique listing links.")
        
        if not all_listing_links:
            print("No listing links found. Exiting.")
            return
            
        # Filter out listings that are already scraped
        new_listing_links = []
        for url in all_listing_links:
            listing_id = get_listing_id_from_url(url)
            if listing_id in existing_listing_ids:
                print(f"Skipping listing {listing_id} - already scraped")
                continue
            new_listing_links.append(url)
            
        print(f"After filtering: {len(new_listing_links)} new listings to scrape (skipped {len(all_listing_links) - len(new_listing_links)} existing ones)")
            
        if not new_listing_links:
            print("No new listings to scrape. Exiting.")
            return
            
        # 2. Scrape each individual listing page (NO Playwright needed) and save its HTML
        print(f"\n--- Scraping individual listing pages ({len(new_listing_links)} links) --- ")
        tasks = []
        for listing_url in new_listing_links:
             tasks.append(scrape_and_save_listing(listing_url, crawler, output_dir))
             
        # Reduced batch size from 5 to 3
        batch_size = 3 
        
        # Create subdirectory for failed listings to retry later
        failed_dir = os.path.join(output_dir, "failed")
        if not os.path.exists(failed_dir):
            os.makedirs(failed_dir)
            
        for i in range(0, len(tasks), batch_size):
             batch = tasks[i:i+batch_size]
             print(f"\nProcessing batch {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size}...")
             
             # Gather results to check for failures
             results = await asyncio.gather(*batch, return_exceptions=True)
             
             # Check if any tasks failed and log them
             for j, result in enumerate(results):
                 if isinstance(result, Exception):
                     batch_index = i + j
                     if batch_index < len(new_listing_links):
                         failed_url = new_listing_links[batch_index]
                         print(f"⚠️ Failed to scrape {failed_url}: {result}")
                         # Log failed URL to retry later
                         with open(os.path.join(failed_dir, "failed_urls.txt"), "a") as f:
                             f.write(f"{failed_url}\n")
             
             if i + batch_size < len(tasks):
                 # Add a random component to the delay to make the scraping pattern less predictable
                 batch_delay = 8 + (i // batch_size % 5) # 8-12 seconds
                 print(f"Waiting {batch_delay} seconds before next batch...")
                 await asyncio.sleep(batch_delay)

    print("\n--- Scraping Complete --- ")
    print(f"Saved HTML content for individual listings in the '{output_dir}' folder.")
    print(f"Saved HTML content for search pages in the '{pages_dir}' folder.")
    
    # Print stats
    failed_urls = []
    if os.path.exists(os.path.join(failed_dir, "failed_urls.txt")):
        with open(os.path.join(failed_dir, "failed_urls.txt"), "r") as f:
            failed_urls = f.read().splitlines()
    
    print(f"Total links found: {len(all_listing_links)}")
    print(f"Previously scraped: {len(existing_listing_ids)}")
    print(f"New links to scrape: {len(new_listing_links)}")
    print(f"Successfully scraped: {len(new_listing_links) - len(failed_urls)}")
    print(f"Failed to scrape: {len(failed_urls)}")
    if failed_urls:
        print(f"Failed URLs are saved in: {os.path.join(failed_dir, 'failed_urls.txt')}")
    
async def scrape_and_save_listing(url, crawler, output_dir):
    # Scrape single listing page WITHOUT Playwright
    html_content = await scrape_page(url, crawler, use_playwright=False) 
    await save_html_to_file(html_content, url, output_dir)
    
    # Add a slight random variation to the delay (4-5 seconds)
    import random
    random_delay = 4 + random.random()
    await asyncio.sleep(random_delay)

if __name__ == "__main__":
    asyncio.run(main())