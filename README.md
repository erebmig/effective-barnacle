# TubeGrab Pro - YouTube MP3 & MP4 Indirici

Profesyonel, hizli ve guvenli YouTube video indirme araci. Email dogrulama ile bot kontrolunu atlayin ve premium avantajlardan yararlanin.

## Ozellikler

- **MP3 Indirme** - 320kbps yuksek kalite ses
- **MP4 Indirme** - 4K'ya kadar video kalitesi
- **Email Dogrulama** - Hizli indirme icin email ile giris
- **Bot Korumasi Atlatma** - Android client + ozel headers
- **Rate Limiting** - DDoS korumasi
- **Progress Tracking** - Gercek zamanli ilerleme
- **Modern Arayuz** - Koyu tema, mobil uyumlu

## Premium Avantajlar (Email ile Giris)

- 20x Daha Hizli Indirme
- YouTube Bot Korumasini Atlama
- 320kbps MP3 Kalitesi
- 4K Video Destegi
- Sinirsiz Indirme Hakki

## Hizli Baslangic

### Yerel Gelistirme

```bash
# Repository'yi klonla
git clone https://github.com/KULLANICI_ADI/tubegrab-pro.git
cd tubegrab-pro

# Virtual environment olustur
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya: venv\Scripts\activate  # Windows

# Bagimliliklari yukle
pip install -r requirements.txt

# FFmpeg yukle (MP3 donusumu icin)
# Ubuntu/Debian: sudo apt install ffmpeg
# Mac: brew install ffmpeg
# Windows: https://ffmpeg.org/download.html

# Uygulamayi calistir
python app.py
```

### Environment Variables

```bash
# Zorunlu
SECRET_KEY=your-secret-key-here

# Email Gonderimi (Gmail icin)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Cookie dosyasi (opsiyonel - bot bypass icin)
COOKIES_FILE=cookies.txt

# Debug modu
FLASK_DEBUG=false
```

## Gmail SMTP Kurulumu

Email dogrulama ozelligi icin Gmail SMTP ayarlari:

1. **Gmail Hesabiniza Gidin**
2. **Google Hesap Ayarlari** > **Guvenlik**
3. **2 Adimli Dogrulama** acik olmali
4. **Uygulama Sifreleri** > Yeni uygulama sifresi olusturun
5. "Mail" ve "Diger (ozel ad)" secin
6. Olusturulan 16 karakterlik sifreyi `SMTP_PASSWORD` olarak kullanin

```bash
# Render Environment Variables
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=darkheavenemi@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # Uygulama sifresi
```

## Render Deployment

### Otomatik (render.yaml)

1. GitHub'a push edin
2. Render Dashboard'da "New" > "Blueprint" secin
3. Repository'yi baglayin
4. Environment Variables ekleyin
5. Otomatik deploy edilir

### Manuel

1. Render Dashboard > "New" > "Web Service"
2. Repository'yi baglayin
3. Ayarlar:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Environment Variables ekleyin:
   - `SECRET_KEY`
   - `SMTP_SERVER`
   - `SMTP_PORT`
   - `SMTP_EMAIL`
   - `SMTP_PASSWORD`

## API Endpoints

### Public Endpoints

| Endpoint | Method | Aciklama |
|----------|--------|----------|
| `/` | GET | Ana sayfa |
| `/api/health` | GET | Sunucu sagligi |
| `/api/stats` | GET | Indirme istatistikleri |

### Video Endpoints

| Endpoint | Method | Aciklama |
|----------|--------|----------|
| `/api/info` | POST | Video bilgilerini getir |
| `/api/download` | POST | Indirme baslat |
| `/api/status/<id>` | GET | Indirme durumu |
| `/api/file/<id>` | GET | Dosyayi indir |
| `/api/cleanup/<id>` | POST | Gecici dosyayi sil |

### Auth Endpoints (Email Dogrulama)

| Endpoint | Method | Aciklama |
|----------|--------|----------|
| `/api/auth/send-code` | POST | Dogrulama kodu gonder |
| `/api/auth/verify-code` | POST | Kodu dogrula |
| `/api/auth/logout` | POST | Cikis yap |
| `/api/auth/status` | GET | Giris durumu |

### Request/Response Ornekleri

#### Kod Gonder
```bash
curl -X POST https://your-app.onrender.com/api/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"email": "kullanici@email.com"}'

# Response
{
  "success": true,
  "message": "Dogrulama kodu gonderildi",
  "expires_in": 600
}
```

#### Kodu Dogrula
```bash
curl -X POST https://your-app.onrender.com/api/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"email": "kullanici@email.com", "code": "123456"}'

# Response
{
  "success": true,
  "message": "Basariyla dogrulandi!",
  "email": "kullanici@email.com",
  "benefits": ["20x Daha Hizli Indirme", ...]
}
```

#### Video Bilgisi
```bash
curl -X POST https://your-app.onrender.com/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

#### Indirme Baslat
```bash
curl -X POST https://your-app.onrender.com/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "format": "mp3", "quality": "best"}'
```

## Bot Tespiti Cozumu

YouTube bot korumasi aktif oldugunda su yontemler kullanilir:

### 1. Android Player Client (Varsayilan)
```python
'extractor_args': {
    'youtube': {
        'player_client': ['android_creator', 'android', 'web'],
    }
}
```

### 2. Ozel HTTP Headers
Chrome Android tarayici gibi gorunmek icin kapsamli header seti.

### 3. Email Dogrulama (Onerilen)
Premium kullanicilar icin hizli indirme ve bot bypass.

### 4. Cookie Kullanimi
```bash
# Cookie export
yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com"

# Environment variable
export COOKIES_FILE=cookies.txt
```

## Proje Yapisi

```
tubegrab-pro/
├── app.py              # Flask uygulamasi (870+ satir)
├── templates/
│   └── index.html      # Ana sayfa (2200+ satir)
├── requirements.txt    # Python bagimliliklari
├── Procfile           # Render/Heroku icin
├── render.yaml        # Render deployment config
├── runtime.txt        # Python versiyonu
├── .gitignore
└── README.md
```

## Rate Limiting

- **Misafir kullanicilar:** 5 istek / dakika
- **Email ile giris:** 100 istek / dakika
- **Maksimum video suresi:** 2 saat
- **Kod gonderme limiti:** 60 saniye bekleme

## Guvenlik

- Session bazli kimlik dogrulama
- Rate limiting
- Input validation
- Email dogrulama (6 haneli kod, 10 dakika gecerli, 5 deneme hakki)
- Gecici dosya temizleme
- SSL/TLS (Render tarafindan)

## Telif Hakki Uyarisi

Bu platform yalnizca kisisel kullanim amaclidir. Indirilen icerikler tamamen kullanicinin sorumluluğundadir. Telif hakki ile korunan iceriklerin izinsiz indirilmesi ve dagitilmasi yasalara aykiridir. Kullanici, indirdigi iceriklerin yasal kullanimini saglamakla yukumludur. TubeGrab Pro, kullanicilarin eylemlerinden sorumlu degildir ve hicbir video icerigini sunucularinda depolamaz.

## Lisans

MIT License

## Katkida Bulunma

Pull request'ler memnuniyetle karsilanir. Buyuk degisiklikler icin lutfen once bir issue acin.

---

**TubeGrab Pro** - Profesyonel YouTube Indirme Araci
