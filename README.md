# 101evler.com Scraper and Data Extractor

This project scrapes property listing data from 101evler.com (specifically for Northern Cyprus) and extracts the details into a structured CSV file.

## Features

*   Scrapes listing URLs from search result pages.
*   Uses Playwright for search pages to handle dynamic content.
*   Saves individual listing pages as HTML files.
*   Avoids re-scraping already saved listings and search pages.
*   Extracts detailed information from saved HTML listing pages using BeautifulSoup.
*   Handles potential errors during scraping and extraction.
*   Calculates approximate monthly rent in TL (based on a 14x multiplier and current exchange rates from the Turkish Central Bank).
*   Outputs extracted data to a CSV file (`property_details.csv`).
*   Includes continuous run mode for `extract_data.py`.

## Prerequisites

*   Python 3.8+
*   pip (Python package installer)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers:**
    The `crawl4ai` library uses Playwright. You might need to install its browser binaries the first time:
    ```bash
    playwright install
    ```

## Usage

### 1. Scraping Listings (`main.py`)

This script crawls the search result pages to find listing URLs and then scrapes each listing's HTML content.

*   **Configuration:**
    *   Open `main.py`.
    *   Modify `base_search_url`: Change the path (e.g., `/magusa`, `/girne`, `/lefkosa`) to target different areas or property types (e.g., `kiralik-daire`, `satilik-villa`). The base should look like `https://www.101evler.com/kibris/<listing_type>/<area>`.
    *   Modify `max_search_pages`: Set the number of search result pages you want to scrape for links.
    *   You can also adjust the `output_dir` (default: `listings`) and `pages_dir` (default: `pages`) if needed.
*   **Run the scraper:**
    ```bash
    python main.py
    ```
    The script will:
    *   Fetch search result pages (using Playwright) up to `max_search_pages`.
    *   Save search page HTML to the `pages/` directory.
    *   Extract listing URLs from these pages.
    *   Fetch individual listing pages (without Playwright).
    *   Save listing HTML to the `listings/` directory.
    *   Skip already downloaded search pages and listings.
    *   Log progress and delays to the console.
    *   Failed listing URLs are saved to `listings/failed/failed_urls.txt` for potential retries.

### 2. Extracting Data (`extract_data.py`)

This script parses the saved HTML files in the `listings/` directory and extracts property details into a CSV file.

*   **Run the extractor:**
    ```bash
    python extract_data.py
    ```
    The script will:
    *   Read all `.html` files from the `listings/` directory.
    *   Skip listings already present in the output CSV.
    *   Parse HTML using BeautifulSoup to extract details like price, location, features, dates, agency, etc.
    *   Fetch current TRY exchange rates for price conversion.
    *   Calculate an estimated 14x monthly rent in TL (`price_tl_14x`).
    *   Append the extracted data to `property_details.csv`.
    *   Update existing TL prices in the CSV based on current exchange rates.
*   **Continuous Mode:**
    To run the extractor periodically (e.g., if the scraper runs in the background or via cron):
    ```bash
    python extract_data.py --continuous [INTERVAL_MINUTES] [MAX_RUNS]
    ```
    *   `INTERVAL_MINUTES`: Wait time in minutes between runs (default: 30).
    *   `MAX_RUNS`: Maximum number of times to run (default: 10).

## Output

*   **`listings/`**: Directory containing the raw HTML of individual property listings.
*   **`pages/`**: Directory containing the raw HTML of search result pages.
*   **`property_details.csv`**: CSV file containing the extracted and structured property data.

## Dependencies

See `requirements.txt`. 