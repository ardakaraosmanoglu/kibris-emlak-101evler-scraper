import os
import json
import asyncio
import pandas as pd
# Remove AsyncOpenAI import since we're not using it anymore
# from openai import AsyncOpenAI
from tqdm.asyncio import tqdm
import csv
from pathlib import Path
import shutil
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
import sys
import time

# Configuration
HTML_FOLDER = 'listings'
OUTPUT_FILE = 'property_details.csv'
TEMP_FOLDER = 'temp'  # Temporary folder for JSON files
MAX_CONCURRENT = 3
EXCHANGE_RATES_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"

# Remove OpenRouter API setup
# API_KEY = "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"
# MODEL = "llama3-70b-8192"

# Remove client initialization
# client = AsyncOpenAI(
#     base_url="https://api.groq.com/openai/v1",
#     api_key=API_KEY
# )

# Fetch exchange rates from Turkish Central Bank
def fetch_exchange_rates():
    try:
        print("Fetching current exchange rates from Turkish Central Bank...")
        response = requests.get(EXCHANGE_RATES_URL)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        
        # Create dictionary to store exchange rates
        rates = {}
        
        # Extract rates for common currencies
        for currency in root.findall("./Currency"):
            currency_code = currency.get("Kod")
            
            # Look for buying rate (Forexbuying)
            forex_buying = currency.find("ForexBuying")
            if forex_buying is not None and forex_buying.text:
                # Convert comma to dot and convert to float
                rate = float(forex_buying.text.replace(',', '.'))
                rates[currency_code] = rate
        
        print(f"Successfully fetched exchange rates for {len(rates)} currencies")
        return rates
    except Exception as e:
        print(f"Error fetching exchange rates: {e}")
        # Return default rates for common currencies as fallback
        return {
            "USD": 37.8646,
            "EUR": 41.8133,
            "GBP": 48.7317
        }

# Get property ID from filename
def get_property_id_from_filename(filename):
    # Extract numeric ID from the filename (e.g., 123456.html -> 123456)
    match = re.match(r'(\d+)\.html', filename)
    if match:
        return match.group(1)
    return None

# Load existing property IDs from the CSV file
def load_existing_property_ids():
    existing_ids = set()
    
    if not os.path.exists(OUTPUT_FILE):
        return existing_ids
    
    try:
        # Read the CSV file with pandas for better handling
        df = pd.read_csv(OUTPUT_FILE)
        
        # Check if property_id column exists
        if 'property_id' in df.columns:
            # Convert all property IDs to strings for consistent comparison
            property_ids = df['property_id'].astype(str).tolist()
            existing_ids.update(property_ids)
            
            # Extra check for property IDs in source_file column
            if 'source_file' in df.columns:
                for source_file in df['source_file']:
                    if isinstance(source_file, str) and source_file.endswith('.html'):
                        file_id = get_property_id_from_filename(source_file)
                        if file_id:
                            existing_ids.add(file_id)
    
    except Exception as e:
        print(f"Error loading existing property IDs: {e}")
        # If there's an error, try a direct CSV reading approach as fallback
        try:
            with open(OUTPUT_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'property_id' in row and row['property_id']:
                        # Make sure it's a string for consistent comparison
                        existing_ids.add(str(row['property_id']))
        except Exception as inner_e:
            print(f"Fallback method also failed: {inner_e}")
    
    print(f"Loaded {len(existing_ids)} existing property IDs from CSV")
    return existing_ids

# Setup directories
def setup_directories():
    # Create output directory if it doesn't exist
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
        print(f"Created temporary directory: {TEMP_FOLDER}")
    else:
        # Clean any existing temp files
        for file in os.listdir(TEMP_FOLDER):
            os.remove(os.path.join(TEMP_FOLDER, file))
        print(f"Cleaned existing temporary directory: {TEMP_FOLDER}")

# Setup CSV file with headers if it doesn't exist
def setup_csv_file():
    csv_path = Path(OUTPUT_FILE)
    if not csv_path.exists():
        # Create with headers
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Define headers based on our expected JSON structure
            headers = [
                'source_file', 'property_id', 'title', 'price', 'currency', 
                'listing_type', 'property_type', 'property_subtype', 'room_count',
                'district', 'city', 'country', 'agency_name', 
                'url', 'description', 'listing_date', 'update_date', 
                'title_deed_type', 'min_rental_period', 'payment_interval', 'exchange_option',
                'price_tl_14x', 'image_links', 'phone_numbers', 'whatsapp_numbers'
            ]
            writer.writerow(headers)
        print(f"Created new CSV file: {OUTPUT_FILE}")
    else:
        print(f"CSV file already exists: {OUTPUT_FILE}")
        try:
            # Read the current CSV
            df = pd.read_csv(OUTPUT_FILE)
            
            # Check if we need to remove columns
            columns_to_remove = ['area_m2', 'floor', 'furnished', 'has_elevator', 'image_count', 'pros_cons', 'agent_id', 'user_id', 'pros', 'cons', 'error']
            columns_removed = False
            
            for col in columns_to_remove:
                if col in df.columns:
                    df = df.drop(col, axis=1)
                    columns_removed = True
            
            # Check if we need to add new columns
            new_columns = ['title_deed_type', 'min_rental_period', 'payment_interval', 'exchange_option', 'image_links', 'phone_numbers', 'whatsapp_numbers']
            columns_added = False
            
            for col in new_columns:
                if col not in df.columns:
                    df[col] = None
                    columns_added = True
            
            # Save the updated CSV if any changes were made
            if columns_removed or columns_added:
                # Create a backup of the original file
                backup_file = f"{OUTPUT_FILE}.bak"
                shutil.copy2(OUTPUT_FILE, backup_file)
                print(f"Created backup of original CSV at: {backup_file}")
                
                # Write the updated DataFrame to the CSV
                df.to_csv(OUTPUT_FILE, index=False)
                
                if columns_removed:
                    print(f"Removed columns from CSV: {', '.join(columns_to_remove)}")
                if columns_added:
                    print(f"Added new columns to CSV: {', '.join(new_columns)}")
        except Exception as e:
            print(f"Error updating CSV columns: {e}")

# Calculate price in TL with 14x multiplier
def calculate_tl_price(price, currency, exchange_rates):
    if price is None or currency is None:
        return None
    
    # Determine currency ISO code
    currency_code = currency
    if currency == "£":
        currency_code = "GBP"
    elif currency == "$":
        currency_code = "USD"
    elif currency == "€":
        currency_code = "EUR"
    elif currency == "₺":
        currency_code = "TRY"
    
    # Get exchange rate
    if currency_code == "TRY":
        rate = 1.0  # No conversion needed
    elif currency_code in exchange_rates:
        rate = exchange_rates[currency_code]
    else:
        print(f"Exchange rate not found for {currency_code}, using 1.0")
        rate = 1.0
    
    # Calculate 14x monthly price in TL
    try:
        price_value = float(price)
        return round(price_value * 14 * rate, 2)
    except:
        return None

# Extract image URLs from HTML content
def extract_image_urls(soup):
    image_urls = set()
    
    # Method 1: Extract from main gallery (splide__slide)
    main_gallery = soup.find('div', class_='splide mainGallerySplide')
    if main_gallery:
        slides = main_gallery.find_all('li', class_='splide__slide')
        for slide in slides:
            # Look for regular src attributes
            img = slide.find('img')
            if img:
                if img.get('src') and 'property' in img.get('src'):
                    image_urls.add(img.get('src'))
                # Also check for lazy loaded images
                if img.get('data-splide-lazy') and 'property' in img.get('data-splide-lazy'):
                    image_urls.add(img.get('data-splide-lazy'))
    
    # Method 2: Extract from fancybox gallery links (full size)
    fancybox_links = soup.find_all('a', attrs={'data-fancybox': 'gallery-mobile'})
    for link in fancybox_links:
        if link.get('href') and 'property' in link.get('href'):
            image_urls.add(link.get('href'))
    
    # Method 3: Extract from meta tags (og:image)
    og_images = soup.find_all('meta', property='og:image')
    for og_img in og_images:
        if og_img.get('content') and 'property' in og_img.get('content'):
            image_urls.add(og_img.get('content'))
    
    # Convert set to list for easier handling
    return list(image_urls)

# Extract phone numbers from HTML content
def extract_phone_numbers(soup):
    phone_numbers = set()
    
    # Method 1: Extract from tel: links
    tel_links = soup.find_all('a', href=lambda href: href and href.startswith('tel:'))
    for link in tel_links:
        href = link.get('href', '')
        # Extract number from tel: link
        number = href.replace('tel:', '').strip()
        if number and (number.startswith('+') or number.isdigit()):
            phone_numbers.add(number)
            print(f"Found phone number from tel link: {number}")
    
    # Method 2: Extract from showphone JavaScript function calls
    onclick_elements = soup.find_all(attrs={'onclick': lambda v: v and 'showphone' in v})
    for elem in onclick_elements:
        onclick = elem.get('onclick', '')
        # Look for showphone(this, '+905xxxxxxxx', 'id') pattern
        match = re.search(r"showphone\s*\([^,]+,\s*['\"]([^'\"]+)['\"]", onclick)
        if match:
            number = match.group(1).strip()
            if number and (number.startswith('+') or number.isdigit()):
                phone_numbers.add(number)
                print(f"Found phone number from showphone function: {number}")
    
    # Method 3: Extract from text in specific elements
    phone_divs = soup.find_all(['div', 'span'], class_=['propDetailPhone', 'text-block-80'])
    for div in phone_divs:
        text = div.get_text(strip=True)
        # Look for phone number patterns in text
        matches = re.findall(r'(?:\+90|0)(?:5\d{2})\s*\d{3}\s*\d{2}\s*\d{2}', text)
        for match in matches:
            phone_numbers.add(match.replace(' ', ''))
            print(f"Found phone number from text: {match}")
    
    # Convert set to list for easier handling
    return list(phone_numbers)

# Extract WhatsApp numbers from HTML content
def extract_whatsapp_numbers(soup):
    whatsapp_numbers = set()
    
    # Extract from wa.me links
    wa_links = soup.find_all('a', href=lambda href: href and 'wa.me/' in href)
    for link in wa_links:
        href = link.get('href', '')
        # Extract number from wa.me link (https://wa.me/905xxxxxxxx?text=...)
        match = re.search(r'wa\.me/(\d+)', href)
        if match:
            number = match.group(1).strip()
            if number.startswith('90'):
                number = '+' + number
            elif not number.startswith('+'):
                number = '+90' + number
            whatsapp_numbers.add(number)
            print(f"Found WhatsApp number: {number}")
    
    # Convert set to list for easier handling
    return list(whatsapp_numbers)

# Add a single result to the CSV file
def append_to_csv(result, exchange_rates):
    try:
        # Calculate TL price with 14x multiplier if price and currency are available
        if "price" in result and "currency" in result and result["price"] is not None and result["currency"] is not None:
            result["price_tl_14x"] = calculate_tl_price(result["price"], result["currency"], exchange_rates)
        else:
            result["price_tl_14x"] = None
        
        # Read existing CSV headers to ensure we write data in the correct order
        if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader)  # Get the first row which contains headers
        else:
            # Define headers based on our expected JSON structure if file doesn't exist
            headers = [
                'source_file', 'property_id', 'title', 'price', 'currency', 
                'listing_type', 'property_type', 'property_subtype', 'room_count',
                'district', 'city', 'country', 'agency_name', 
                'url', 'description', 'listing_date', 'update_date', 
                'title_deed_type', 'min_rental_period', 'payment_interval', 'exchange_option',
                'price_tl_14x', 'image_links', 'phone_numbers', 'whatsapp_numbers'
            ]
        
        # Prepare row data in the same order as headers
        row_data = []
        for header in headers:
            if header in result:
                row_data.append(result[header])
            else:
                row_data.append(None)  # Use None for missing fields
        
        # Write to CSV
        with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # If this is the first entry, write headers
            if not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0:
                writer.writerow(headers)
            writer.writerow(row_data)
        
        print(f"Added data from {result.get('source_file')} to CSV")
        return True
    except Exception as e:
        print(f"Error adding to CSV: {e}")
        return False

async def extract_details(html_file):
    # Read HTML file
    file_path = os.path.join(HTML_FOLDER, html_file)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        print(f"Error reading {html_file}: {e}")
        return None
        
    # Initialize all fields we want to extract directly from HTML
    listing_date = None
    update_date = None
    location = None
    district = None
    city = None
    property_id = None
    property_type = None
    property_subtype = None
    listing_type = None
    price = None
    currency = None
    area_m2 = None
    min_rental_period = None
    payment_interval = None
    title_deed_type = None
    exchange_option = None
    room_count = None
    floor = None
    total_floors = None
    agency_name = None
    url = None
    description = None
    title = None
    image_links = None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract image URLs from HTML
        image_urls = extract_image_urls(soup)
        if image_urls:
            # Store image links as a comma-separated string
            image_links = ','.join(image_urls)
            print(f"Found {len(image_urls)} image links")
        
        # Extract Title from various places
        # Method 1: Main visible heading on the page (most reliable)
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.get_text(strip=True)
            print(f"Found title from h1 tag: {title}")
        
        # Method 2: Look for div with class text-block-135 which often contains the title
        if not title:
            title_div = soup.find('div', class_='text-block-135')
            if title_div:
                title = title_div.get_text(strip=True)
                print(f"Found title from text-block-135 div: {title}")
        
        # Method 3: Use og:title meta tag
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content')
                print(f"Found title from og:title meta tag: {title}")
        
        # Method 4: Use title tag from head section, but clean it
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                # Title tag often has format: "Title - Price - Listing Number | Website"
                full_title = title_tag.get_text(strip=True)
                # Extract the part before the first " - "
                parts = full_title.split(' - ')
                if parts:
                    title = parts[0].strip()
                    print(f"Found title from title tag: {title}")
        
        # Extract URL from meta tags (most reliable method)
        url_meta = soup.find('meta', property='og:url')
        if url_meta and url_meta.get('content'):
            url = url_meta.get('content')
            print(f"Found URL from meta tag: {url}")
        
        # Extract agency_name from various places
        # First check dataLayer in scripts (no longer extracting agent_id or user_id)
        scripts = soup.find_all('script')
        
        # Extract agency_name from contact card
        agency_divs = soup.find_all(['div', 'a'], class_=['text-block-157', 'text-block-204'])
        for div in agency_divs:
            text = div.get_text(strip=True)
            if text and len(text) > 3 and not text.startswith('+') and not re.match(r'^\d+$', text):
                agency_name = text
                print(f"Found agency_name: {agency_name}")
                break
        
        # Extract description from main content area
        description_div = soup.find('div', class_='div-block-361', style='line-break:anywhere')
        if description_div:
            # Look for description in paragraphs or divs with class f-s-16
            desc_elements = description_div.find_all(['p', 'div'], class_='f-s-16')
            if desc_elements:
                description = ' '.join([elem.get_text(strip=True) for elem in desc_elements])
            else:
                # If no specific elements found, use all text
                description = description_div.get_text(strip=True)
            
            print(f"Found description (truncated): {description[:50]}...")
        
        # If no description found, try meta description
        if not description:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content')
                print(f"Found description from meta (truncated): {description[:50]}...")
        
        # Look for all info in the "Hızlı Bakış" section
        hizli_bakis_div = soup.find('div', id='hizli-bakis')
        if hizli_bakis_div:
            print(f"Found Hızlı Bakış section in {html_file}")
            # Find all rows in the quick look section
            zebra_rows_divs = hizli_bakis_div.find_all('div', class_='zebra-rows')
            
            # Process all rows from all zebra-rows divs
            all_rows = []
            for zebra_div in zebra_rows_divs:
                rows = zebra_div.find_all('div', class_='text-block-141')
                all_rows.extend(rows)
            
            for row in all_rows:
                # Find the label (left column)
                label_div = row.find('div', class_='col-5')
                # Find the value (right column)
                value_div = row.find('div', class_='col-7')
                
                if not label_div or not value_div:
                    continue
                    
                label_text = label_div.get_text(strip=True)
                
                # Extract value, first checking for <strong> tag inside
                strong_tag = value_div.find('strong')
                if strong_tag:
                    value_text = strong_tag.get_text(strip=True)
                else:
                    value_text = value_div.get_text(strip=True)
                
                # Extract various fields based on label
                if "İlan No" in label_text and value_text:
                    # Remove '#' if present
                    property_id = value_text.replace('#', '').strip()
                    print(f"Found property ID from Hızlı Bakış: {property_id}")
                
                elif "Konum" in label_text and value_text:
                    location = value_text
                    print(f"Found location from Hızlı Bakış: {location}")
                    # Try to split location into district and city
                    parts = location.split(',')
                    if len(parts) >= 2:
                        district = parts[0].strip()
                        city = parts[1].strip()
                    else:
                        parts = location.split('/')
                        if len(parts) >= 2:
                            district = parts[0].strip()
                            city = parts[1].strip()
                
                elif "Emlak Türü" in label_text and value_text:
                    # This often has format like "Konut / Daire"
                    parts = value_text.split('/')
                    if len(parts) >= 2:
                        property_type = parts[0].strip()
                        property_subtype = parts[1].strip()
                    else:
                        property_type = value_text
                    print(f"Found property type: {property_type}, subtype: {property_subtype}")
                
                elif "Durumu" in label_text and value_text:
                    if "Kiralık" in value_text:
                        listing_type = "Rent"
                    elif "Satılık" in value_text:
                        listing_type = "Sale"
                    print(f"Found listing type: {listing_type}")
                
                elif "Fiyat" in label_text and value_text:
                    # Price often has format like "$580 (~ 22,291 TL)"
                    # First, try to extract the price and currency symbol
                    price_match = re.match(r'([£$€₺])\s*([0-9,.]+)', value_text)
                    if price_match:
                        currency_symbol = price_match.group(1)
                        price_value = price_match.group(2).replace(',', '')
                        
                        # Convert currency symbol to ISO code
                        if currency_symbol == '£':
                            currency = 'GBP'
                        elif currency_symbol == '$':
                            currency = 'USD'
                        elif currency_symbol == '€':
                            currency = 'EUR'
                        elif currency_symbol == '₺':
                            currency = 'TRY'
                        
                        price = float(price_value) if price_value else None
                        print(f"Found price: {price} {currency}")
                
                elif "Tapu Türü" in label_text and value_text:
                    title_deed_type = value_text
                    print(f"Found title deed type: {title_deed_type}")
                
                elif "Metrekare" in label_text and value_text:
                    # Extract just the number from "85 m²"
                    area_match = re.match(r'([0-9,.]+)\s*m²', value_text)
                    if area_match:
                        area_m2 = int(area_match.group(1).replace(',', ''))
                    print(f"Found area: {area_m2} m²")
                
                elif "Takas" in label_text and value_text:
                    exchange_option = value_text
                    print(f"Found exchange option: {exchange_option}")
                
                elif "İlan Tarihi" in label_text and value_text:
                    listing_date = value_text
                    print(f"Found listing date from Hızlı Bakış: {listing_date}")
                
                elif "Güncelleme Tarihi" in label_text and value_text:
                    update_date = value_text
                    print(f"Found update date from Hızlı Bakış: {update_date}")
                
                elif "En Az Kiralama" in label_text and value_text:
                    min_rental_period = value_text
                    print(f"Found minimum rental period: {min_rental_period}")
                
                elif "Kira Ödeme Aralığı" in label_text and value_text:
                    payment_interval = value_text
                    print(f"Found payment interval: {payment_interval}")
                    
                elif "Oda Sayısı" in label_text and value_text:
                    room_count = value_text
                    print(f"Found room count from Hızlı Bakış: {room_count}")
        
        # Look in the Property Details (Konut Detayları) section for floor info and room count if not found earlier
        konut_detaylari_div = soup.find('div', id='konut-detaylari')
        if konut_detaylari_div:
            print(f"Found Konut Detayları section in {html_file}")
            detail_rows = konut_detaylari_div.find_all('div', class_='text-block-141')
            
            for row in detail_rows:
                # Find the label (left column)
                label_div = row.find('div', class_='col-5')
                # Find the value (right column)
                value_div = row.find('div', class_='col-7')
                
                if not label_div or not value_div:
                    continue
                    
                label_text = label_div.get_text(strip=True)
                
                # Extract value, first checking for <strong> tag inside
                strong_tag = value_div.find('strong')
                if strong_tag:
                    value_text = strong_tag.get_text(strip=True)
                else:
                    value_text = value_div.get_text(strip=True)
                
                # Extract floor information
                if "Bulunduğu Kat" in label_text and value_text:
                    try:
                        # If it's a number, keep it as is
                        floor = int(value_text.strip())
                    except ValueError:
                        # Otherwise, keep the text (e.g., "Giriş Katı", "Çatı Katı")
                        floor = value_text.strip()
                    print(f"Found floor: {floor}")
                
                elif "Kat Sayısı" in label_text and value_text:
                    try:
                        total_floors = int(value_text.strip())
                    except ValueError:
                        total_floors = value_text.strip()
                    print(f"Found total floors: {total_floors}")
                
                # Extract room count if not found in Hızlı Bakış
                elif "Oda Sayısı" in label_text and value_text and not room_count:
                    room_count = value_text
                    print(f"Found room count from Konut Detayları: {room_count}")
        
        # If we still don't have room count, check the summary icons at the top
        if not room_count:
            room_count_divs = soup.find_all('div', class_='text-block-138')
            for div in room_count_divs:
                text = div.get_text(strip=True)
                # Look for common room count patterns like 1+1, 2+1, etc.
                match = re.search(r'(\d+\+\d+)', text)
                if match:
                    room_count = match.group(1)
                    print(f"Found room count from icons: {room_count}")
                    break
        
        # If we don't have floor info yet but have total_floors, combine them for the floor field
        if floor is not None and total_floors is not None:
            floor = f"{floor} / {total_floors}"
            print(f"Combined floor info: {floor}")
        
        # If we couldn't find dates in the primary structure, try alternative locations
        if not listing_date or not update_date:
            # Try looking in h-zl-bak-sright class
            right_div = soup.find('div', class_='h-zl-bak-sright')
            if right_div:
                rows = right_div.find_all('div', class_='text-block-141')
                
                for row in rows:
                    label_div = row.find('div', class_='col-5')
                    value_div = row.find('div', class_='col-7')
                    
                    if label_div and value_div:
                        label_text = label_div.get_text(strip=True)
                        value_text = value_div.get_text(strip=True)
                        
                        if "İlan Tarihi" in label_text and value_text and not listing_date:
                            listing_date = value_text
                            print(f"Found listing date from alternative HTML: {listing_date}")
                        
                        if "Güncelleme Tarihi" in label_text and value_text and not update_date:
                            update_date = value_text
                            print(f"Found update date from alternative HTML: {update_date}")
                            
                        if "Konum" in label_text and value_text and not location:
                            location = value_text
                            print(f"Found location from alternative HTML: {location}")
                            # Try to split location into district and city
                            parts = location.split('/')
                            if len(parts) >= 2:
                                district = parts[0].strip()
                                city = parts[1].strip()
                            else:
                                parts = location.split(',')
                                if len(parts) >= 2:
                                    district = parts[0].strip()
                                    city = parts[1].strip()
        
        # Additional fallback: Try to find dates using text search
        if not listing_date or not update_date:
            # Common patterns to look for dates
            listing_date_pattern = re.compile(r'İlan\s+Tarihi\s*:?\s*(\d{2}/\d{2}/\d{4})', re.IGNORECASE)
            update_date_pattern = re.compile(r'Güncelleme\s+Tarihi\s*:?\s*(\d{2}/\d{2}/\d{4})', re.IGNORECASE)
            
            # Look for listing date
            if not listing_date:
                text = soup.get_text()
                listing_match = listing_date_pattern.search(text)
                if listing_match:
                    listing_date = listing_match.group(1)
                    print(f"Found listing date via regex: {listing_date}")
            
            # Look for update date
            if not update_date:
                if not 'text' in locals():
                    text = soup.get_text()
                update_match = update_date_pattern.search(text)
                if update_match:
                    update_date = update_match.group(1)
                    print(f"Found update date via regex: {update_date}")
        
        # Extract phone numbers
        phone_numbers = extract_phone_numbers(soup)
        phone_numbers_str = ','.join(phone_numbers) if phone_numbers else None
        
        # Extract WhatsApp numbers
        whatsapp_numbers = extract_whatsapp_numbers(soup)
        whatsapp_numbers_str = ','.join(whatsapp_numbers) if whatsapp_numbers else None
        
        # Check if we have the minimal required data for a listing
        has_basic_data = bool(property_id and (listing_type or property_type))
        has_price_data = bool(price and currency)
        has_location_data = bool(district or city)
        
        # Now add the extracted property information
        result = {
            "source_file": html_file,
            "property_id": property_id,
            "title": title,
            "price": price,
            "currency": currency,
            "listing_type": listing_type,
            "property_type": property_type,
            "property_subtype": property_subtype,
            "room_count": room_count,
            "district": district,
            "city": city,
            "country": "Northern Cyprus",
            "agency_name": agency_name,
            "url": url,
            "description": description,
            "listing_date": listing_date,
            "update_date": update_date,
            "title_deed_type": title_deed_type,
            "min_rental_period": min_rental_period,
            "payment_interval": payment_interval,
            "exchange_option": exchange_option,
            "image_links": image_links,
            "phone_numbers": phone_numbers_str,
            "whatsapp_numbers": whatsapp_numbers_str
        }
        
        return result
        
    except Exception as e:
        print(f"Error processing {html_file}: {e}")
        return {
            "source_file": html_file,
            "property_id": property_id,
            "title": title,
            "price": price,
            "currency": currency,
            "listing_type": listing_type,
            "property_type": property_type,
            "property_subtype": property_subtype,
            "room_count": room_count,
            "district": district,
            "city": city,
            "country": "Northern Cyprus",
            "agency_name": agency_name,
            "url": url,
            "description": description,
            "listing_date": listing_date,
            "update_date": update_date,
            "title_deed_type": title_deed_type,
            "min_rental_period": min_rental_period,
            "payment_interval": payment_interval,
            "exchange_option": exchange_option,
            "image_links": image_links,
            "phone_numbers": phone_numbers_str if 'phone_numbers_str' in locals() else None,
            "whatsapp_numbers": whatsapp_numbers_str if 'whatsapp_numbers_str' in locals() else None
        }

# Main function to process files
async def main():
    print(f"Starting property extraction on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Setup necessary directories
        setup_directories()
        
        # Setup CSV file with headers if needed
        setup_csv_file()
        
        # Fetch and parse exchange rates
        exchange_rates = fetch_exchange_rates()
        
        # Load existing property IDs from CSV
        existing_ids = load_existing_property_ids()
        print(f"Found {len(existing_ids)} existing property IDs in CSV")
        
        # Find all HTML files to process
        html_files = [f for f in os.listdir(HTML_FOLDER) if f.endswith('.html')]
        print(f"Found {len(html_files)} HTML files to process")
        
        # Filter out files that have already been processed
        new_files = []
        for html_file in html_files:
            property_id = get_property_id_from_filename(html_file)
            # Double check both the property_id and the filename itself
            if property_id in existing_ids or html_file.replace('.html', '') in existing_ids:
                print(f"Skipping {html_file} - already exists in CSV")
            else:
                new_files.append(html_file)
        
        print(f"Processing {len(new_files)} new HTML files...")
        
        # Update prices in TL for existing entries
        if existing_ids:
            try:
                # Read the CSV file
                df = pd.read_csv(OUTPUT_FILE)
                
                # Update price_tl_14x column if price and currency are not null
                if 'price' in df.columns and 'currency' in df.columns and 'price_tl_14x' in df.columns:
                    count_updated = 0
                    for idx, row in df.iterrows():
                        if pd.notna(row['price']) and pd.notna(row['currency']):
                            tl_price = calculate_tl_price(row['price'], row['currency'], exchange_rates)
                            if tl_price is not None and (pd.isna(row['price_tl_14x']) or row['price_tl_14x'] != tl_price):
                                df.at[idx, 'price_tl_14x'] = tl_price
                                count_updated += 1
                
                    if count_updated > 0:
                        # Save the updated DataFrame back to the CSV file
                        df.to_csv(OUTPUT_FILE, index=False)
                        print(f"Updated TL prices for {count_updated} existing entries")
            except Exception as e:
                print(f"Error updating existing TL prices: {e}")
        
        if not new_files:
            print("No new files to process")
            return len(html_files), 0, len(existing_ids)
        
        # Process files concurrently with a limit on concurrency
        print(f"Processing {len(new_files)} new HTML files...")
        
        # Setup progress bar
        pbar = tqdm(total=len(new_files), desc="Extracting property details")
        
        # Track successful and failed extractions
        successful = []
        failed = []
        
        # Process in batches to limit memory usage
        batch_size = min(MAX_CONCURRENT * 10, len(new_files))
        for i in range(0, len(new_files), batch_size):
            batch = new_files[i:i + batch_size]
            
            # Create tasks for batch
            tasks = [extract_details(html_file) for html_file in batch]
            
            # Process batch concurrently
            results = await asyncio.gather(*tasks)
            
            # Process results
            for result in results:
                if result is None:
                    pbar.update(1)
                    continue
                    
                source_file = result.get('source_file')
                if source_file:
                    # Save to CSV
                    if append_to_csv(result, exchange_rates):
                        successful.append(source_file)
                    else:
                        failed.append(source_file)
                        print(f"Failed to add data from {source_file} to CSV")
                
                pbar.update(1)
        
        pbar.close()
        
        # Print summary
        print(f"\nExtraction Summary:")
        print(f"- Successfully processed: {len(successful)} files")
        print(f"- Failed: {len(failed)} files")
        print(f"- Skipped (already processed): {len(existing_ids)} files")
        print(f"- Total files: {len(html_files)} files")
        
        return len(html_files), len(successful), len(existing_ids)
    
    except KeyboardInterrupt:
        print("\nExtraction interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"Extraction process completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Function to restart extraction at intervals
async def restart_extraction(interval_minutes=30, max_runs=10):
    run_count = 0
    while run_count < max_runs:
        print(f"\n--- Starting extraction run {run_count + 1} of {max_runs} ---")
        total, successful, skipped = await main()
        
        run_count += 1
        if run_count >= max_runs:
            print(f"Completed {max_runs} extraction runs. Exiting.")
            break
            
        # Don't wait if there were no files or all files were skipped
        if total == 0 or (successful == 0 and skipped == total):
            print(f"No new files to process. Skipping wait and proceeding to next run.")
            continue
            
        print(f"Waiting {interval_minutes} minutes before next extraction run...")
        await asyncio.sleep(interval_minutes * 60)

# Run the script
if __name__ == "__main__":
    print(f"Starting property extraction on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Check for command-line arguments
        if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
            # Get interval in minutes (default 30)
            interval = 30
            if len(sys.argv) > 2:
                try:
                    interval = int(sys.argv[2])
                except ValueError:
                    print(f"Invalid interval: {sys.argv[2]}. Using default: 30 minutes.")
            
            # Get max runs (default 10)
            max_runs = 10
            if len(sys.argv) > 3:
                try:
                    max_runs = int(sys.argv[3])
                except ValueError:
                    print(f"Invalid max runs: {sys.argv[3]}. Using default: 10 runs.")
            
            print(f"Running in continuous mode with {interval} minute intervals, maximum {max_runs} runs.")
            asyncio.run(restart_extraction(interval, max_runs))
        else:
            asyncio.run(main())
            
    except KeyboardInterrupt:
        print("\nExtraction interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"Extraction process completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 