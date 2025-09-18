# Configuration file for 101evler.com scraper
# Easily change regions, property types, and other parameters here

# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================

# Region/City Configuration
# Available cities: iskele, magusa, lefkosa, girne, gazimagusa, esentepe, etc.
CITY = "iskele"

# Property Type Configuration
PROPERTY_TYPES = {
    "satilik-villa": {
        "url_path": "satilik-villa",
        "property_type": 3,
        "property_subtype": [4]
    },
    "satilik-ev": {
        "url_path": "satilik-ev",
        "property_type": 1,
        "property_subtype": [1]
    },
    "satilik-daire": {
        "url_path": "satilik-daire",
        "property_type": 1,
        "property_subtype": [2]
    },
    "kiralik-villa": {
        "url_path": "kiralik-villa",
        "property_type": 3,
        "property_subtype": [4]
    },
    "kiralik-daire": {
        "url_path": "kiralik-daire",
        "property_type": 1,
        "property_subtype": [2]
    }
}

# Currently selected property type
PROPERTY_TYPE = "satilik-villa"

# Sale/Rent type (R for sale, L for rent)
SALE_TYPE = "R"

# Sort parameter (mr = most recent, pa = price ascending, pd = price descending, etc.)
SORT_PARAM = "mr"

# ============================================================================
# URL CONFIGURATION
# ============================================================================

# Base domain
BASE_DOMAIN = "https://www.101evler.com"

# API endpoint for getting total count
API_URL = "https://www.101evler.com/ac/arama-sonucu"

# ============================================================================
# DIRECTORY CONFIGURATION
# ============================================================================

# Output directories
OUTPUT_DIR = "listings"
PAGES_DIR = "pages"
FAILED_DIR = "failed"

# ============================================================================
# SCRAPING BEHAVIOR CONFIGURATION
# ============================================================================

# Batch processing
BATCH_SIZE = 3

# Timing configuration (in seconds)
TIMING = {
    "listing_delay_min": 1.2,
    "listing_delay_max": 1.7,
    "batch_delay_min": 0.8,
    "batch_delay_max": 1.2,
    "search_page_delay_base": 1.2,
    "search_page_delay_variation": 0.9,  # 1.2 + (page % 3) * 0.3
    "cooldown_minutes": 3
}

# ============================================================================
# WEB SCRAPING CONFIGURATION
# ============================================================================

# Headers for web requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
}

# API headers
API_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*"
}

# Block detection phrases
BLOCK_PHRASES = [
    "Sorry, you have been blocked",
    "You are unable to access",
    'data-translate="block_headline"',
    'data-translate="unable_to_access"'
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_base_search_url():
    """Generate base search URL based on current configuration"""
    property_config = PROPERTY_TYPES[PROPERTY_TYPE]
    return f"{BASE_DOMAIN}/kibris/{property_config['url_path']}/{CITY}"

def get_search_url_with_page(page=1):
    """Generate complete search URL with page and sort parameters"""
    base_url = get_base_search_url()
    return f"{base_url}?page={page}&sort={SORT_PARAM}"

def get_api_params(page=1):
    """Generate API parameters based on current configuration"""
    property_config = PROPERTY_TYPES[PROPERTY_TYPE]

    # Build property subtype parameter
    subtype_params = []
    for i, subtype in enumerate(property_config['property_subtype']):
        subtype_params.append(f"property_subtype%5B{i}%5D={subtype}")

    subtype_string = "&".join(subtype_params)

    return f"page={page}&s_r={SALE_TYPE}&property_type={property_config['property_type']}&city={CITY}&{subtype_string}"

def get_listing_pattern():
    """Get regex pattern for listing links based on property type"""
    # Site uses /kibris/satilik-emlak/ for all listing URLs, not the specific property type
    return r'/kibris/satilik-emlak/[\w-]+-\d+\.html'

# ============================================================================
# REGION PRESETS
# ============================================================================

# Quick configuration presets for different regions
REGION_PRESETS = {
    "iskele_villa": {
        "CITY": "iskele",
        "PROPERTY_TYPE": "satilik-villa",
        "SALE_TYPE": "R",
        "SORT_PARAM": "mr"
    },
    "magusa_villa": {
        "CITY": "magusa",
        "PROPERTY_TYPE": "satilik-villa",
        "SALE_TYPE": "R",
        "SORT_PARAM": "mr"
    },
    "lefkosa_daire": {
        "CITY": "lefkosa",
        "PROPERTY_TYPE": "satilik-daire",
        "SALE_TYPE": "R",
        "SORT_PARAM": "mr"
    },
    "girne_villa": {
        "CITY": "girne",
        "PROPERTY_TYPE": "satilik-villa",
        "SALE_TYPE": "R",
        "SORT_PARAM": "mr"
    },
    "gazimagusa_ev": {
        "CITY": "gazimagusa",
        "PROPERTY_TYPE": "satilik-ev",
        "SALE_TYPE": "R",
        "SORT_PARAM": "mr"
    }
}

def apply_preset(preset_name):
    """Apply a region preset configuration"""
    global CITY, PROPERTY_TYPE, SALE_TYPE, SORT_PARAM

    if preset_name in REGION_PRESETS:
        preset = REGION_PRESETS[preset_name]
        CITY = preset["CITY"]
        PROPERTY_TYPE = preset["PROPERTY_TYPE"]
        SALE_TYPE = preset["SALE_TYPE"]
        SORT_PARAM = preset["SORT_PARAM"]
        print(f"Applied preset '{preset_name}': {CITY} - {PROPERTY_TYPE} - sort: {SORT_PARAM}")
    else:
        print(f"Preset '{preset_name}' not found. Available presets: {list(REGION_PRESETS.keys())}")

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config():
    """Validate current configuration"""
    errors = []

    if PROPERTY_TYPE not in PROPERTY_TYPES:
        errors.append(f"Invalid PROPERTY_TYPE: {PROPERTY_TYPE}. Available: {list(PROPERTY_TYPES.keys())}")

    if SALE_TYPE not in ["R", "L"]:
        errors.append(f"Invalid SALE_TYPE: {SALE_TYPE}. Must be 'R' (sale) or 'L' (rent)")

    if not CITY:
        errors.append("CITY cannot be empty")

    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return False

    return True

# ============================================================================
# DISPLAY CURRENT CONFIGURATION
# ============================================================================

def show_config():
    """Display current configuration"""
    print("=== CURRENT CONFIGURATION ===")
    print(f"City: {CITY}")
    print(f"Property Type: {PROPERTY_TYPE}")
    print(f"Sale Type: {'Sale' if SALE_TYPE == 'R' else 'Rent'}")
    print(f"Sort: {SORT_PARAM}")
    print(f"Base URL: {get_base_search_url()}")
    print(f"Search URL: {get_search_url_with_page(1)}")
    print(f"API Params: {get_api_params()}")
    print(f"Output Dir: {OUTPUT_DIR}")
    print(f"Batch Size: {BATCH_SIZE}")
    print("=============================")