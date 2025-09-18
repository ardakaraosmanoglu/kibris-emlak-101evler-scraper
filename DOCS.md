# 101evler Scraper Kullanım Kılavuzu

## Otomatik Sayfa Sayısı Tespiti

Scraper artık toplam sayfa sayısını ve toplam ilan sayısını otomatik olarak tespit ediyor:

1. İlk arama sayfası çekildiğinde, iki farklı yöntem ile bilgileri toplar:
   - Site tarafından kullanılan API'ye istek yaparak (JavaScript'in yaptığı gibi)
   - HTML içeriğini analiz ederek (sayfa numarası, sayfa seçici, toplam sonuç sayısı)

2. Toplam sayfa sayısını tespit ettiğinde, ekrana bilgi mesajı yazdırır:
   ```
   Toplam ilan: 230
   Toplam sayfa: 8
   Otomatik tespit edilen maksimum sayfa: 8
   ```

3. Tespit edilen sayfa sayısı, arama işleminde maksimum değer olarak kullanılır.

4. Eğer belirli bir sayfada hiç ilan bulunamazsa (son sayfaya ulaşılmışsa), scraper işlemini otomatik olarak sonlandırır.

## Komut Satırı Parametreleri

### `--max-pages` Parametresi

Ayrıca kullanıcı, komut satırı parametresi ile maksimum sayfa sayısını manuel olarak belirleyebilir:

```bash
python main.py --max-pages 5
```

Bu komut, otomatik tespit edilen sayfa sayısını görmezden gelip, maksimum 5 sayfa tarayacaktır. Böylece:

1. Tüm sayfaları taramak istemediğinizde
2. Tespit algoritmasına güvenmediğinizde
3. Sadece belirli sayıda sayfayı test etmek istediğinizde

manuel kontrol sağlayabilirsiniz.

## Cloudflare ve Engellenme Tespiti

Script, HTML içerisinde aşağıdaki durumlarda engellenme tespit ettiğinde otomatik olarak 10 dakika bekleme moduna geçer ve sonra devam eder:

- "Sorry, you have been blocked" mesajı
- "You are unable to access" mesajı
- Cloudflare CAPTCHA sayfası

Engellenme tespit edildiğinde:

1. Ekrana şu mesaj yazdırılır:
   ```
   !!! Erişim engellendi. 10 dakika bekleniyor ve tekrar denenecek... !!!
   ```

2. Script 10 dakika bekler (cooldown süresi).

3. Bekleme süresi sonunda şu mesaj görünür ve işlem devam eder:
   ```
   10 dakika bekleme süresi doldu. Tekrar deneniyor...
   ```

4. Eğer ikinci denemede de erişim engeli tespit edilirse, script durur.

Bu özellik, geçici IP yasaklarının veya rate-limit engellemelerinin geçmesini bekleyerek tarama işleminin otomatik olarak devam etmesini sağlar.

## Örnek Kullanım

```bash
# Tam otomatik mod - toplam sayfa sayısını tespit eder
python main.py

# Maksimum sayfa sayısını manuel belirle
python main.py --max-pages 10

# Sonuçları CSV'ye dönüştür
python extract_data.py
``` 