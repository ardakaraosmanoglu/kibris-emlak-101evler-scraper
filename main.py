import asyncio
import os
import re
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
import sys
import time  # cooldown için
import random
import config

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
    
    # Regex for property listing pattern based on config
    listing_pattern = re.compile(config.get_listing_pattern())
    
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

def check_blocked_html(html):
    if not html:
        return False
    block_phrases = config.BLOCK_PHRASES
    for phrase in block_phrases:
        if phrase in html:
            return True
    return False

def handle_access_blocked():
    """Erişim engellendiğinde yapılacak işlemler: konfigurasyon süresince bekle ve tekrar dene"""
    cooldown_minutes = config.TIMING['cooldown_minutes']
    print(f"!!! Erişim engellendi. {cooldown_minutes} dakika bekleniyor ve tekrar denenecek... !!!")
    # 3 dakika bekle
    time.sleep(cooldown_minutes * 60)
    print(f"{cooldown_minutes} dakika bekleme süresi doldu. Tekrar deneniyor...")
    return

def extract_total_counts(html):
    import re
    total_listings = None
    total_pages = None
    
    # 1. Sayfa numarasını HTML'den direkt tespit etmeye çalış
    match = re.search(r'<span id="page_number">(\d+)</span>', html)
    if match and match.group(1) != "1":  # Eğer "1" değilse JavaScript tarafından güncellenmiş demektir
        total_pages = int(match.group(1))
        print(f"HTML'den toplam sayfa sayısı: {total_pages}")
    
    # 2. Toplam ilan sayısını bul (count_label)
    match = re.search(r'([\d\.]+)\s*Sonuç Bulundu', html)
    if match:
        try:
            total_listings = int(match.group(1).replace('.', ''))
            print(f"HTML'den toplam ilan sayısı: {total_listings}")
            # Toplam sayfa sayısını hesapla (JavaScript'in yaptığı gibi)
            if total_listings is not None and total_pages is None:
                total_pages = max(1, (total_listings + 29) // 30)  # Math.ceil(count/30) eşdeğeri
                print(f"Toplam ilan sayısından hesaplanan sayfa sayısı: {total_pages}")
        except:
            pass
    
    # 3. Pagination select options'dan tespit et
    if total_pages is None:
        options = re.findall(r'<option[^>]*value="[^"]*[?&]page=(\d+)[^"]*"[^>]*>(\d+)</option>', html)
        if options:
            try:
                highest_page = max([int(page[0]) for page in options])
                if highest_page > 1:  # En az 2 varsa JavaScript çalışmış demektir
                    total_pages = highest_page
                    print(f"Pagination options'dan tespit edilen sayfa sayısı: {total_pages}")
            except:
                pass
    
    # 4. next/son sayfa butonunda URL'den tespit et
    if total_pages is None:
        match = re.search(r'<a[^>]*href="[^"]*[?&]page=(\d+)[^"]*"[^>]*>.*?Son.*?</a>', html)
        if match:
            try:
                total_pages = int(match.group(1))
                print(f"Son sayfa butonundan tespit edilen sayfa sayısı: {total_pages}")
            except:
                pass
    
    # 5. Sayfadaki ilanları say ve bundan tahmin et (fallback)
    if total_listings is None:
        items_count = len(re.findall(r'class="ilanitem(cardorange|basic)"', html))
        # İlan sayısı ile sayfa başına ilan sayısını hesapla
        if items_count > 0:
            total_listings = items_count  # Bu sadece ilk sayfadaki ilan sayısı
            print(f"Sayfada tespit edilen ilan sayısı: {items_count}")
    
    # 6. Tahmin: Sayfada hiç ilan yoksa ve total_pages hala null ise 1 sayfadır
    if total_listings == 0 and total_pages is None:
        total_pages = 1
        print("Sayfada hiç ilan yok, 1 sayfa olduğu varsayılıyor.")
    
    # Güvenlik: varsayılan değerler
    if total_pages is None:
        total_pages = 30  # Varsayılan değer
        print(f"Toplam sayfa sayısı tespit edilemedi, varsayılan: {total_pages}")
    
    return total_listings, total_pages

async def extract_total_counts_from_api(crawler, base_url):
    """JavaScript'in yaptığı gibi API'ye istek yaparak toplam ilan sayısını almaya çalışır"""
    try:
        api_url = config.API_URL
        # API parametreleri: konfigürasyondan alınır
        params = config.get_api_params(page=1)
        headers = config.API_HEADERS.copy()
        headers["Referer"] = base_url
        
        print("API'den toplam ilan sayısını almaya çalışılıyor...")
        response = await crawler.arun(
            url=api_url, 
            method="POST",
            headers=headers,
            data=params
        )
        
        if response and response.html:
            total_listings_str = response.html
            try:
                total_listings = int(total_listings_str)
                total_pages = max(1, (total_listings + 29) // 30)  # Math.ceil(count/30) eşdeğeri
                print(f"API'den alınan toplam ilan sayısı: {total_listings}")
                print(f"API'den hesaplanan toplam sayfa sayısı: {total_pages}")
                return total_listings, total_pages
            except:
                print(f"API yanıtı sayıya dönüştürülemedi: {total_listings_str}")
        else:
            print("API'den yanıt alınamadı")
    except Exception as e:
        print(f"API isteği sırasında hata: {e}")
        
    return None, None

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-pages', type=int, default=None, help='Maksimum çekilecek sayfa sayısı')
    args = parser.parse_args()
    # base_search_url konfigürasyondan alınır
    base_search_url = config.get_base_search_url()
    output_dir = config.OUTPUT_DIR
    pages_dir = config.PAGES_DIR
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
        headers=config.HEADERS
    ) as crawler:
        
        # 1. Scrape search result pages using PLAYWRIGHT to gather listing links
        first_page_num = 1
        search_page_url = config.get_search_url_with_page(first_page_num)
        html = await scrape_page(search_page_url, crawler, use_playwright=True)
        if check_blocked_html(html):
            handle_access_blocked()
            # Tekrar ilk sayfayı çek
            html = await scrape_page(search_page_url, crawler, use_playwright=True)
            if check_blocked_html(html):
                print("!!! Erişim engellendi. Script durduruluyor. !!!")
                exit(1)  # İkinci denemede de engellenirse sonlandır
        if not html:
            print("İlk arama sayfası çekilemedi. Script duruyor.")
            return
        
        # Önce API'den toplam sayıları almayı dene
        total_listings_api, total_pages_api = await extract_total_counts_from_api(crawler, search_page_url)
        
        # Sonra HTML'den tespit et
        total_listings_html, total_pages_html = extract_total_counts(html)
        
        # API'den ve HTML'den alınan değerleri önceliklendirme
        total_listings = total_listings_api if total_listings_api else total_listings_html
        total_pages = total_pages_api if total_pages_api else total_pages_html
        
        if total_listings:
            print(f"Toplam ilan: {total_listings}")
        if total_pages:
            print(f"Toplam sayfa: {total_pages}")
            
        # Kullanıcı override etmediyse otomatik max_search_pages belirle
        if args.max_pages:
            max_search_pages = args.max_pages
            print(f"Kullanıcı tarafından belirlenen maksimum sayfa: {max_search_pages}")
        elif total_pages:
            max_search_pages = total_pages
            print(f"Otomatik tespit edilen maksimum sayfa: {max_search_pages}")
        else:
            max_search_pages = 30
            print(f"Sayfa sayısı tespit edilemedi, varsayılan: {max_search_pages}")
        
        # İlk sayfa kaydedilsin
        await save_search_page(html, first_page_num, pages_dir)
        base_for_relative = search_page_url.split('?')[0]
        links_on_page = await extract_listing_links(html, base_for_relative)
        all_listing_links.update(links_on_page)
        print(f"Total unique links found so far: {len(all_listing_links)}")
        
        # Kalan sayfalar için döngü
        for page_num in range(2, max_search_pages + 1):
            search_page_url = config.get_search_url_with_page(page_num)
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
                if check_blocked_html(html):
                    handle_access_blocked()
                    # Tekrar aynı sayfayı çek
                    html = await scrape_page(search_page_url, crawler, use_playwright=True)
                    if check_blocked_html(html):
                        print("!!! Erişim engellendi. Script durduruluyor. !!!")
                        exit(1)  # İkinci denemede de engellenirse sonlandır
                    if not html:
                        print(f"Sayfa {page_num} tekrar çekilemedi. Sonraki sayfaya geçiliyor.")
                        continue
                base_for_relative = search_page_url.split('?')[0]
                links_on_page = await extract_listing_links(html, base_for_relative)
                all_listing_links.update(links_on_page)
                print(f"Total unique links found so far: {len(all_listing_links)}")
                # Eğer hiç ilan yoksa, bu muhtemelen son sayfa, döngüyü kır
                if not links_on_page:
                    print(f"Sayfa {page_num} boş, muhtemelen son sayfa. Tarama durduruluyor.")
                    break
            else:
                print(f"Skipping search page {page_num} due to fetch error or empty content.")
            
            # Add a random component to the delay to make the scraping pattern less predictable
            # Only wait if we're fetching the next page (not on the last page)
            if page_num < max_search_pages and page_num not in existing_search_pages:
                random_delay = config.TIMING['search_page_delay_base'] + (page_num % 3) * 0.3
                print(f"Waiting {random_delay:.1f} seconds before next search page...")
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
             
        # Batch size konfigürasyondan alınır
        batch_size = config.BATCH_SIZE 
        
        # Create subdirectory for failed listings to retry later
        failed_dir = os.path.join(output_dir, config.FAILED_DIR)
        if not os.path.exists(failed_dir):
            os.makedirs(failed_dir)
            
        # Start time for batch processing estimation
        import datetime
        batch_start_time = time.time()
        total_batches = (len(tasks) + batch_size - 1) // batch_size
            
        for i in range(0, len(tasks), batch_size):
             batch = tasks[i:i+batch_size]
             current_batch = i//batch_size + 1
             print(f"\nProcessing batch {current_batch}/{total_batches}...")
             
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
             
             # Calculate and display estimated finish time
             elapsed_time = time.time() - batch_start_time
             if current_batch > 0:
                 avg_time_per_batch = elapsed_time / current_batch
                 remaining_batches = total_batches - current_batch
                 estimated_remaining_time = remaining_batches * avg_time_per_batch
                 
                 # Add estimated delay time for remaining batches
                 if remaining_batches > 0:
                     estimated_delay_time = remaining_batches * 1  # Average delay of 1 second
                     estimated_remaining_time += estimated_delay_time
                 
                 finish_time = datetime.datetime.now() + datetime.timedelta(seconds=estimated_remaining_time)
                 
                 print(f"📊 Progress: {current_batch}/{total_batches} batches completed")
                 print(f"⏱️  Elapsed: {elapsed_time/60:.1f} minutes")
                 print(f"🎯 Estimated finish: {finish_time.strftime('%H:%M:%S')} (in {estimated_remaining_time/60:.1f} minutes)")
             
             if i + batch_size < len(tasks):
                 # Konfigürasyondan batch delay
                 batch_delay = config.TIMING['batch_delay_min'] + random.random() * (config.TIMING['batch_delay_max'] - config.TIMING['batch_delay_min'])
                 print(f"Waiting {batch_delay:.1f} seconds before next batch...")
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
    if check_blocked_html(html_content):
        handle_access_blocked()
        # Tekrar dene
        html_content = await scrape_page(url, crawler, use_playwright=False)
        if check_blocked_html(html_content):
            print("!!! Erişim engellendi. Script durduruluyor. !!!")
            exit(1)  # İkinci denemede de engellenirse sonlandır
    await save_html_to_file(html_content, url, output_dir)
    # Add a slight random variation to the delay based on config
    random_delay = config.TIMING['listing_delay_min'] + random.random() * (config.TIMING['listing_delay_max'] - config.TIMING['listing_delay_min'])
    await asyncio.sleep(random_delay)

if __name__ == "__main__":
    asyncio.run(main())