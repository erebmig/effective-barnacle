from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect, url_for
import yt_dlp
import os
import tempfile
import uuid
import threading
import time
import json
import hashlib
import secrets
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ==================== CONFIGURATION ====================
DOWNLOAD_DIR = tempfile.gettempdir()
MAX_VIDEO_DURATION = 7200  # 2 saat maksimum
RATE_LIMIT_WINDOW = 60  # saniye
RATE_LIMIT_MAX_REQUESTS = 5  # pencere basina maksimum istek (misafir)
PREMIUM_RATE_LIMIT = 100  # Email dogrulamis kullanicilar icin

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

# ==================== IN-MEMORY STORAGE ====================
download_status = {}
rate_limit_store = {}
user_sessions = {}
verification_codes = {}  # email -> {code, expires, attempts}
verified_users = {}  # email -> {verified_at, download_count}
download_history = {}
analytics_data = {
    'total_downloads': 0,
    'mp3_downloads': 0,
    'mp4_downloads': 0,
    'unique_users': set(),
    'popular_videos': {},
    'verified_users_count': 0
}

# ==================== EMAIL VERIFICATION ====================
def generate_verification_code():
    """6 haneli dogrulama kodu olustur"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code):
    """Email ile dogrulama kodu gonder"""
    try:
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            # SMTP yapilandirmasi yoksa simule et (development icin)
            print(f"[DEV MODE] Verification code for {email}: {code}")
            return True
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'TubeGrab Pro - Dogrulama Kodunuz'
        msg['From'] = f'TubeGrab Pro <{SMTP_EMAIL}>'
        msg['To'] = email
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #050505; color: #ffffff; margin: 0; padding: 0; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .logo {{ font-size: 32px; font-weight: 700; background: linear-gradient(135deg, #ff3333, #ff6b35); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
                .code-box {{ background: linear-gradient(135deg, rgba(255,51,51,0.1), rgba(255,107,53,0.1)); border: 2px solid rgba(255,51,51,0.3); border-radius: 16px; padding: 30px; text-align: center; margin: 30px 0; }}
                .code {{ font-size: 48px; font-weight: 700; letter-spacing: 12px; font-family: 'Consolas', monospace; background: linear-gradient(135deg, #ff3333, #ff6b35); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
                .info {{ color: #888; font-size: 14px; text-align: center; margin-top: 30px; }}
                .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #222; color: #666; font-size: 12px; }}
                .benefits {{ background: #111; border-radius: 12px; padding: 20px; margin: 20px 0; }}
                .benefit {{ display: flex; align-items: center; gap: 10px; padding: 8px 0; color: #ccc; font-size: 14px; }}
                .benefit-icon {{ color: #ff3333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">TubeGrab Pro</div>
                    <p style="color: #888; margin-top: 10px;">Hizli & Guvenli YouTube Indirici</p>
                </div>
                
                <p style="color: #ccc; text-align: center;">Merhaba! Iste dogrulama kodunuz:</p>
                
                <div class="code-box">
                    <div class="code">{code}</div>
                </div>
                
                <div class="benefits">
                    <p style="color: #fff; font-weight: 600; margin-bottom: 15px;">Premium Avantajlariniz:</p>
                    <div class="benefit"><span class="benefit-icon">⚡</span> 20x Daha Hizli Indirme</div>
                    <div class="benefit"><span class="benefit-icon">🔓</span> Bot Korumasini Atlama</div>
                    <div class="benefit"><span class="benefit-icon">🎵</span> 320kbps MP3 Kalitesi</div>
                    <div class="benefit"><span class="benefit-icon">📹</span> 4K Video Destegi</div>
                    <div class="benefit"><span class="benefit-icon">♾️</span> Sinirsiz Indirme</div>
                </div>
                
                <p class="info">Bu kod 10 dakika icinde gecerlidir.<br>Eger bu istegi siz yapmadiysiniz, bu emaili gormezden gelebilirsiniz.</p>
                
                <div class="footer">
                    &copy; 2024 TubeGrab Pro - Tum haklar saklidir.<br>
                    Bu email otomatik olarak gonderilmistir.
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        TubeGrab Pro - Dogrulama Kodunuz
        
        Merhaba! Iste dogrulama kodunuz:
        
        {code}
        
        Premium Avantajlariniz:
        - 20x Daha Hizli Indirme
        - Bot Korumasini Atlama
        - 320kbps MP3 Kalitesi
        - 4K Video Destegi
        - Sinirsiz Indirme
        
        Bu kod 10 dakika icinde gecerlidir.
        Eger bu istegi siz yapmadiysiniz, bu emaili gormezden gelebilirsiniz.
        
        TubeGrab Pro
        """
        
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, email, msg.as_string())
        
        return True
    except Exception as e:
        print(f"Email gonderme hatasi: {e}")
        return False

def validate_email(email):
    """Email formatini dogrula"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ==================== RATE LIMITING ====================
def get_client_ip():
    """Gercek IP adresini al"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

def is_premium_user():
    """Kullanicinin premium (dogrulanmis) olup olmadigini kontrol et"""
    email = session.get('verified_email')
    return email is not None and email in verified_users

def check_rate_limit(ip_address, is_premium=False):
    """Rate limit kontrolu"""
    current_time = time.time()
    max_requests = PREMIUM_RATE_LIMIT if is_premium else RATE_LIMIT_MAX_REQUESTS
    
    if ip_address not in rate_limit_store:
        rate_limit_store[ip_address] = []
    
    # Eski kayitlari temizle
    rate_limit_store[ip_address] = [
        t for t in rate_limit_store[ip_address] 
        if current_time - t < RATE_LIMIT_WINDOW
    ]
    
    if len(rate_limit_store[ip_address]) >= max_requests:
        return False, max_requests
    
    rate_limit_store[ip_address].append(current_time)
    return True, max_requests - len(rate_limit_store[ip_address])

def rate_limit_decorator(f):
    """Rate limit decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = get_client_ip()
        is_premium = is_premium_user()
        allowed, remaining = check_rate_limit(ip, is_premium)
        
        if not allowed:
            return jsonify({
                'success': False,
                'error': 'Cok fazla istek gonderdiniz. Lutfen biraz bekleyin veya email ile dogrulayin.',
                'error_type': 'rate_limit',
                'retry_after': RATE_LIMIT_WINDOW,
                'suggestion': 'email_verify' if not is_premium else None
            }), 429
        
        response = f(*args, **kwargs)
        return response
    return decorated_function

# ==================== YOUTUBE HELPERS ====================
def extract_video_id(url):
    """URL'den video ID'sini cikar"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_duration(seconds):
    """Saniyeyi okunabilir formata cevir"""
    if not seconds:
        return "0:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def format_views(views):
    """Izlenme sayisini formatla"""
    if not views:
        return "0"
    if views >= 1000000000:
        return f"{views/1000000000:.1f}B"
    if views >= 1000000:
        return f"{views/1000000:.1f}M"
    if views >= 1000:
        return f"{views/1000:.1f}K"
    return str(views)

def get_yt_dlp_opts(format_type='mp4', quality='best', is_premium=False):
    """yt-dlp ayarlari - bot tespitini asmak icin ozel yapilandirma"""
    
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'no_color': True,
        
        # Bot tespitini asmak icin KRITIK ayarlar
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'android', 'web'],
                'player_skip': ['webpage', 'configs', 'js'],
                'skip': ['hls', 'dash'],
            }
        },
        
        # Ozel HTTP headers - tarayici gibi gorun
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.113 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Chromium";v="125", "Google Chrome";v="125", "Not.A/Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?1',
            'Sec-Ch-Ua-Platform': '"Android"',
            'Cache-Control': 'max-age=0',
            'X-Youtube-Client-Name': '3',
            'X-Youtube-Client-Version': '19.29.37',
        },
        
        # Retry ayarlari
        'retries': 20,
        'fragment_retries': 20,
        'skip_unavailable_fragments': True,
        'file_access_retries': 10,
        
        # Sleep araliklari (rate limiting icin)
        'sleep_interval': 0.3 if is_premium else 1,
        'max_sleep_interval': 2 if is_premium else 5,
        'sleep_interval_requests': 0.3 if is_premium else 1,
        
        # Ek guvenlik
        'socket_timeout': 30,
        'source_address': '0.0.0.0',
    }
    
    # Cookie dosyasi varsa kullan
    cookies_file = os.environ.get('COOKIES_FILE')
    if cookies_file and os.path.exists(cookies_file):
        opts['cookiefile'] = cookies_file
    
    return opts

def get_video_info(url, is_premium=False):
    """Video bilgilerini al"""
    opts = get_yt_dlp_opts(is_premium=is_premium)
    opts['extract_flat'] = False
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Kalite seceneklerini al
            formats = info.get('formats', [])
            video_qualities = []
            audio_qualities = []
            
            seen_resolutions = set()
            for f in formats:
                height = f.get('height')
                if height and f.get('vcodec') != 'none':
                    resolution = f"{height}p"
                    if resolution not in seen_resolutions:
                        seen_resolutions.add(resolution)
                        filesize = f.get('filesize') or f.get('filesize_approx') or 0
                        video_qualities.append({
                            'quality': resolution,
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext', 'mp4'),
                            'filesize': filesize,
                            'filesize_str': f"{filesize / (1024*1024):.1f} MB" if filesize else "Bilinmiyor"
                        })
                
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    abr = f.get('abr', 0)
                    if abr:
                        audio_qualities.append({
                            'quality': f"{int(abr)}kbps",
                            'format_id': f.get('format_id'),
                            'abr': abr
                        })
            
            # Siralanmis kaliteler
            video_qualities = sorted(video_qualities, key=lambda x: int(x['quality'].replace('p', '')), reverse=True)
            audio_qualities = sorted(audio_qualities, key=lambda x: x['abr'], reverse=True)
            
            return {
                'success': True,
                'id': info.get('id', ''),
                'title': info.get('title', 'Bilinmeyen'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'duration_string': format_duration(info.get('duration', 0)),
                'channel': info.get('uploader', 'Bilinmeyen'),
                'channel_url': info.get('uploader_url', ''),
                'view_count': info.get('view_count', 0),
                'view_count_string': format_views(info.get('view_count', 0)),
                'like_count': info.get('like_count', 0),
                'upload_date': info.get('upload_date', ''),
                'description': (info.get('description', '') or '')[:500],
                'video_qualities': video_qualities[:8],
                'audio_qualities': audio_qualities[:4],
                'is_live': info.get('is_live', False),
                'categories': info.get('categories', []),
                'tags': info.get('tags', [])[:10],
            }
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
            return {
                'success': False,
                'error': 'YouTube bot korumasi aktif. Email ile dogrulama yaparak bu sorunu asabilirsiniz.',
                'error_type': 'bot_detection',
                'suggestion': 'email_verify'
            }
        elif 'Video unavailable' in error_msg:
            return {
                'success': False,
                'error': 'Bu video mevcut degil veya bolgenizde kisitlanmis.',
                'error_type': 'unavailable'
            }
        elif 'Private video' in error_msg:
            return {
                'success': False,
                'error': 'Bu ozel bir video, indirilemez.',
                'error_type': 'private'
            }
        return {
            'success': False,
            'error': f'Video bilgisi alinamadi: {error_msg[:200]}',
            'error_type': 'general'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Beklenmeyen hata: {str(e)[:200]}',
            'error_type': 'general'
        }

def download_video(url, download_id, format_type='mp4', quality='best', is_premium=False):
    """Video indir"""
    try:
        download_status[download_id] = {
            'status': 'starting',
            'progress': 0,
            'speed': '',
            'eta': '',
            'filename': '',
            'is_premium': is_premium
        }
        
        filename = f"{download_id}.{'mp3' if format_type == 'mp3' else 'mp4'}"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        opts = get_yt_dlp_opts(format_type, quality, is_premium)
        
        if format_type == 'mp3':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320' if is_premium else '192',
                }],
                'outtmpl': os.path.join(DOWNLOAD_DIR, f"{download_id}.%(ext)s"),
                'prefer_ffmpeg': True,
            })
        else:
            # Kalite secimi
            if quality == 'best':
                format_string = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality.endswith('p'):
                height = quality.replace('p', '')
                format_string = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
            else:
                format_string = f'{quality}+bestaudio/best'
            
            opts.update({
                'format': format_string,
                'outtmpl': filepath,
                'merge_output_format': 'mp4',
            })
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                progress = int((downloaded / total) * 100) if total > 0 else 0
                speed_str = f"{speed / (1024*1024):.1f} MB/s" if speed else ""
                eta_str = f"{eta}s kaldi" if eta else ""
                
                download_status[download_id].update({
                    'status': 'downloading',
                    'progress': progress,
                    'speed': speed_str,
                    'eta': eta_str,
                    'downloaded': f"{downloaded / (1024*1024):.1f} MB",
                    'total': f"{total / (1024*1024):.1f} MB" if total else ""
                })
            elif d['status'] == 'finished':
                download_status[download_id].update({
                    'status': 'processing',
                    'progress': 95,
                    'speed': '',
                    'eta': 'Isleniyor...'
                })
        
        opts['progress_hooks'] = [progress_hook]
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            
            # Dosya adindaki ozel karakterleri temizle
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)[:100]
            
            # MP3 icin dosya yolunu guncelle
            if format_type == 'mp3':
                filepath = os.path.join(DOWNLOAD_DIR, f"{download_id}.mp3")
            
            download_status[download_id] = {
                'status': 'completed',
                'progress': 100,
                'filepath': filepath,
                'filename': f"{safe_title}.{'mp3' if format_type == 'mp3' else 'mp4'}",
                'title': title,
                'duration': info.get('duration', 0),
                'filesize': os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                'is_premium': is_premium
            }
            
            # Analytics guncelle
            analytics_data['total_downloads'] += 1
            if format_type == 'mp3':
                analytics_data['mp3_downloads'] += 1
            else:
                analytics_data['mp4_downloads'] += 1
            
            video_id = info.get('id', '')
            if video_id:
                analytics_data['popular_videos'][video_id] = analytics_data['popular_videos'].get(video_id, 0) + 1
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
            download_status[download_id] = {
                'status': 'error',
                'error': 'YouTube bot korumasi aktif. Email ile dogrulama yaparak hizli indirme yapabilirsiniz.',
                'error_type': 'bot_detection',
                'suggestion': 'email_verify'
            }
        elif 'ffmpeg' in error_msg.lower():
            download_status[download_id] = {
                'status': 'error',
                'error': 'Ses donusumu icin FFmpeg gerekli. Sunucu yapilandirmasi gerekiyor.',
                'error_type': 'ffmpeg_missing'
            }
        else:
            download_status[download_id] = {
                'status': 'error',
                'error': f'Indirme hatasi: {error_msg[:200]}',
                'error_type': 'general'
            }
    except Exception as e:
        download_status[download_id] = {
            'status': 'error',
            'error': f'Beklenmeyen hata: {str(e)[:200]}',
            'error_type': 'general'
        }

# ==================== ROUTES ====================
@app.route('/')
def index():
    user_email = session.get('verified_email')
    is_premium = is_premium_user()
    return render_template('index.html', 
                         user_email=user_email, 
                         is_premium=is_premium,
                         stats=analytics_data)

# ==================== EMAIL AUTH ROUTES ====================
@app.route('/api/auth/send-code', methods=['POST'])
def send_code():
    """Email'e dogrulama kodu gonder"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email adresi gerekli'})
    
    if not validate_email(email):
        return jsonify({'success': False, 'error': 'Gecerli bir email adresi girin'})
    
    # Rate limit kontrolu (spam onleme)
    ip = get_client_ip()
    current_time = time.time()
    
    # Ayni email icin son 1 dakikada kod gonderilmis mi?
    if email in verification_codes:
        last_sent = verification_codes[email].get('sent_at', 0)
        if current_time - last_sent < 60:
            remaining = int(60 - (current_time - last_sent))
            return jsonify({
                'success': False, 
                'error': f'Lutfen {remaining} saniye bekleyin',
                'retry_after': remaining
            })
    
    # Kod olustur ve kaydet
    code = generate_verification_code()
    verification_codes[email] = {
        'code': code,
        'expires': current_time + 600,  # 10 dakika
        'attempts': 0,
        'sent_at': current_time,
        'ip': ip
    }
    
    # Email gonder
    if send_verification_email(email, code):
        return jsonify({
            'success': True, 
            'message': 'Dogrulama kodu gonderildi',
            'expires_in': 600
        })
    else:
        return jsonify({
            'success': False, 
            'error': 'Email gonderilemedi. Lutfen tekrar deneyin.'
        })

@app.route('/api/auth/verify-code', methods=['POST'])
def verify_code():
    """Dogrulama kodunu kontrol et"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    
    if not email or not code:
        return jsonify({'success': False, 'error': 'Email ve kod gerekli'})
    
    if email not in verification_codes:
        return jsonify({'success': False, 'error': 'Oncelikle kod isteyin'})
    
    stored = verification_codes[email]
    current_time = time.time()
    
    # Suresi dolmus mu?
    if current_time > stored['expires']:
        del verification_codes[email]
        return jsonify({'success': False, 'error': 'Kodun suresi doldu. Yeni kod isteyin.'})
    
    # Cok fazla deneme?
    if stored['attempts'] >= 5:
        del verification_codes[email]
        return jsonify({'success': False, 'error': 'Cok fazla basarisiz deneme. Yeni kod isteyin.'})
    
    # Kod dogru mu?
    if code != stored['code']:
        verification_codes[email]['attempts'] += 1
        remaining = 5 - verification_codes[email]['attempts']
        return jsonify({
            'success': False, 
            'error': f'Yanlis kod. {remaining} deneme hakkiniz kaldi.'
        })
    
    # Basarili dogrulama
    del verification_codes[email]
    
    # Kullaniciyi verified olarak kaydet
    verified_users[email] = {
        'verified_at': current_time,
        'download_count': 0,
        'ip': get_client_ip()
    }
    
    # Session'a kaydet
    session['verified_email'] = email
    session['verified_at'] = current_time
    
    analytics_data['verified_users_count'] += 1
    
    return jsonify({
        'success': True,
        'message': 'Basariyla dogrulandi! Premium avantajlariniz aktif.',
        'email': email,
        'benefits': [
            '20x Daha Hizli Indirme',
            'Bot Korumasini Atlama',
            '320kbps MP3 Kalitesi',
            '4K Video Destegi',
            'Sinirsiz Indirme'
        ]
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Oturumu kapat"""
    session.pop('verified_email', None)
    session.pop('verified_at', None)
    return jsonify({'success': True, 'message': 'Cikis yapildi'})

@app.route('/api/auth/status')
def auth_status():
    """Oturum durumunu kontrol et"""
    email = session.get('verified_email')
    is_premium = is_premium_user()
    
    if email and is_premium:
        user_data = verified_users.get(email, {})
        return jsonify({
            'authenticated': True,
            'email': email,
            'is_premium': True,
            'download_count': user_data.get('download_count', 0),
            'verified_at': user_data.get('verified_at')
        })
    
    return jsonify({
        'authenticated': False,
        'is_premium': False
    })

# ==================== VIDEO ROUTES ====================
@app.route('/api/info', methods=['POST'])
@rate_limit_decorator
def get_info():
    """Video bilgilerini getir"""
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'success': False, 'error': 'URL gerekli'})
    
    # URL dogrulama
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Gecerli bir YouTube URL\'si girin'})
    
    is_premium = is_premium_user()
    info = get_video_info(url, is_premium)
    
    # Canli yayin kontrolu
    if info.get('success') and info.get('is_live'):
        return jsonify({
            'success': False,
            'error': 'Canli yayinlar indirilemez.',
            'error_type': 'live_stream'
        })
    
    # Sure kontrolu
    if info.get('success') and info.get('duration', 0) > MAX_VIDEO_DURATION:
        return jsonify({
            'success': False,
            'error': f'Video cok uzun. Maksimum {MAX_VIDEO_DURATION // 60} dakikalik videolar indirilebilir.',
            'error_type': 'too_long'
        })
    
    return jsonify(info)

@app.route('/api/download', methods=['POST'])
@rate_limit_decorator
def start_download():
    """Indirme baslat"""
    data = request.get_json()
    url = data.get('url', '').strip()
    format_type = data.get('format', 'mp4')
    quality = data.get('quality', 'best')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL gerekli'})
    
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Gecerli bir YouTube URL\'si girin'})
    
    # Unique download ID olustur
    download_id = str(uuid.uuid4())[:12]
    
    # Premium kullanici mi?
    is_premium = is_premium_user()
    
    # Premium kullanicinin indirme sayisini artir
    email = session.get('verified_email')
    if email and email in verified_users:
        verified_users[email]['download_count'] = verified_users[email].get('download_count', 0) + 1
    
    # Indirmeyi arka planda baslat
    thread = threading.Thread(
        target=download_video, 
        args=(url, download_id, format_type, quality, is_premium)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'download_id': download_id,
        'message': 'Indirme baslatildi',
        'is_premium': is_premium
    })

@app.route('/api/status/<download_id>')
def check_status(download_id):
    """Indirme durumunu kontrol et"""
    if download_id not in download_status:
        return jsonify({'status': 'not_found'})
    
    return jsonify(download_status[download_id])

@app.route('/api/file/<download_id>')
def get_file(download_id):
    """Indirilen dosyayi gonder"""
    if download_id not in download_status:
        return jsonify({'error': 'Dosya bulunamadi'}), 404
    
    status = download_status[download_id]
    
    if status.get('status') != 'completed':
        return jsonify({'error': 'Dosya henuz hazir degil'}), 400
    
    filepath = status.get('filepath')
    filename = status.get('filename', 'download')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Dosya bulunamadi'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/cleanup/<download_id>', methods=['POST'])
def cleanup(download_id):
    """Gecici dosyayi temizle"""
    if download_id in download_status:
        status = download_status[download_id]
        filepath = status.get('filepath')
        
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        
        del download_status[download_id]
    
    return jsonify({'success': True})

# ==================== STATS & HEALTH ====================
@app.route('/api/stats')
def get_stats():
    """Istatistikleri getir"""
    return jsonify({
        'total_downloads': analytics_data['total_downloads'],
        'mp3_downloads': analytics_data['mp3_downloads'],
        'mp4_downloads': analytics_data['mp4_downloads'],
        'verified_users': analytics_data['verified_users_count'],
        'uptime': 'Online'
    })

@app.route('/api/health')
def health_check():
    """Sunucu saglik kontrolu"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'features': {
            'email_verification': True,
            'premium_downloads': True,
            'mp3_support': True,
            'mp4_support': True,
            'bot_bypass': True
        }
    })

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Sayfa bulunamadi'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Sunucu hatasi'}), 500

@app.errorhandler(429)
def rate_limit_error(e):
    return jsonify({
        'error': 'Cok fazla istek. Lutfen bekleyin.',
        'suggestion': 'email_verify'
    }), 429

# ==================== MAIN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
