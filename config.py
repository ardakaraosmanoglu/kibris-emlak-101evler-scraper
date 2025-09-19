# 101evler.com Scraper Ayarları
# Bu dosyayı düzenleyerek farklı şehir ve emlak türlerini tarayabilirsiniz

# =============================================================================
# ANA AYARLAR - Bunları değiştirin
# =============================================================================

# Şehir seçimi
CITY = "iskele"  # Seçenekler: iskele, magusa, lefkosa, girne, gazimagusa

# Emlak türü seçimi
PROPERTY_TYPE = "satilik-villa"  # Seçenekler: satilik-villa, satilik-daire, satilik-ev, kiralik-villa, kiralik-daire

# Sıralama türü
SORT = "mr"  # mr=en yeni, pa=fiyat artan, pd=fiyat azalan

# Kaç sayfa taranacak? (None = tümü, sayı = maksimum sayfa)
MAX_PAGES = None

# =============================================================================
# HIZLI AYARLAR - Örnekler
# =============================================================================

# Farklı bölgeler için hazır ayarlar:
QUICK_CONFIGS = {
    "iskele_villa": {
        "CITY": "iskele",
        "PROPERTY_TYPE": "satilik-villa"
    },
    "magusa_villa": {
        "CITY": "magusa",
        "PROPERTY_TYPE": "satilik-villa"
    },
    "lefkosa_daire": {
        "CITY": "lefkosa",
        "PROPERTY_TYPE": "satilik-daire"
    },
    "girne_villa": {
        "CITY": "girne",
        "PROPERTY_TYPE": "satilik-villa"
    }
}

# =============================================================================
# GELİŞMİŞ AYARLAR - Sadece gerekirse değiştirin
# =============================================================================

# Dosya klasörleri
OUTPUT_DIR = "listings"
PAGES_DIR = "pages"

# İndirme hızı (1-5 arası, 3 önerilen)
BATCH_SIZE = 3

# Bekleme süreleri (saniye)
DELAY_BETWEEN_REQUESTS = 1.5
DELAY_BETWEEN_BATCHES = 1.0

# =============================================================================
# SİSTEM AYARLARI - Değiştirmeyin
# =============================================================================

# Emlak türü kodları
PROPERTY_CONFIGS = {
    "satilik-villa": {"type": 3, "subtype": [4], "sale": "R"},
    "satilik-ev": {"type": 1, "subtype": [1], "sale": "R"},
    "satilik-daire": {"type": 1, "subtype": [2], "sale": "R"},
    "kiralik-villa": {"type": 3, "subtype": [4], "sale": "L"},
    "kiralik-daire": {"type": 1, "subtype": [2], "sale": "L"}
}

# Site ayarları
BASE_DOMAIN = "https://www.101evler.com"
API_URL = "https://www.101evler.com/ac/arama-sonucu"

# Tarayıcı ayarları
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

API_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*"
}

# Engellenme tespiti
BLOCK_PHRASES = [
    "Sorry, you have been blocked",
    "You are unable to access",
    'data-translate="block_headline"',
    'data-translate="unable_to_access"'
]

# =============================================================================
# FONKSİYONLAR - Sistem tarafından kullanılır
# =============================================================================

def get_base_search_url():
    """Ana arama URL'sini oluşturur"""
    return f"{BASE_DOMAIN}/kibris/{PROPERTY_TYPE}/{CITY}"

def get_search_url_with_page(page=1):
    """Sayfa numarası ile tam URL oluşturur"""
    base_url = get_base_search_url()
    return f"{base_url}?page={page}&sort={SORT}"

def get_api_params(page=1):
    """API parametrelerini oluşturur"""
    config = PROPERTY_CONFIGS[PROPERTY_TYPE]
    subtype_params = []
    for i, subtype in enumerate(config['subtype']):
        subtype_params.append(f"property_subtype%5B{i}%5D={subtype}")
    subtype_string = "&".join(subtype_params)
    return f"page={page}&s_r={config['sale']}&property_type={config['type']}&city={CITY}&{subtype_string}"

def get_listing_pattern():
    """İlan linklerini bulmak için pattern"""
    return r'/kibris/satilik-emlak/[\w-]+-\d+\.html'

def apply_quick_config(config_name):
    """Hızlı ayar uygular"""
    global CITY, PROPERTY_TYPE

    if config_name in QUICK_CONFIGS:
        config = QUICK_CONFIGS[config_name]
        CITY = config["CITY"]
        PROPERTY_TYPE = config["PROPERTY_TYPE"]
        print(f"✓ {config_name} ayarı uygulandı: {CITY} - {PROPERTY_TYPE}")
        return True
    else:
        print(f"❌ '{config_name}' bulunamadı. Mevcut ayarlar: {list(QUICK_CONFIGS.keys())}")
        return False

def show_config():
    """Mevcut ayarları gösterir"""
    print("\n=== MEVCUT AYARLAR ===")
    print(f"📍 Şehir: {CITY}")
    print(f"🏠 Emlak Türü: {PROPERTY_TYPE}")
    print(f"🔄 Sıralama: {SORT}")
    print(f"📊 Maksimum Sayfa: {MAX_PAGES or 'Sınırsız'}")
    print(f"🌐 Arama URL: {get_search_url_with_page(1)}")
    print(f"📁 Kayıt Klasörü: {OUTPUT_DIR}")
    print("====================\n")

def show_help():
    """Kullanım talimatlarını gösterir"""
    print("""
=== 101evler.com Scraper Kullanım Kılavuzu ===

1. TEL AYARLAR:
   - CITY: Taranacak şehir (iskele, magusa, lefkosa, girne, gazimagusa)
   - PROPERTY_TYPE: Emlak türü (satilik-villa, satilik-daire, kiralik-villa, vb.)
   - SORT: Sıralama (mr=en yeni, pa=fiyat artan, pd=fiyat azalan)
   - MAX_PAGES: Kaç sayfa (None=tümü, 10=maksimum 10 sayfa)

2. HIZLI KULLANIM:
   import config
   config.apply_quick_config("lefkosa_daire")  # Lefkoşa daireler için
   config.show_config()                        # Ayarları göster

3. ÇALIŞTIRMA:
   python main.py                              # Tüm sayfalar
   python main.py --max-pages 5                # Sadece 5 sayfa

Daha fazla bilgi için README.md dosyasını okuyun.
""")

# İlk çalıştırmada mevcut ayarları göster
if __name__ == "__main__":
    show_help()
    show_config()