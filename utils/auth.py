# File: utils/auth.py
# Amac: Firebase kimlik doğrulama işlemlerini (e-posta/şifre ve Google ile giriş dahil) yürütür.
# Kullanildigi yerler: ui/login.py icin kullanici girisi, kayit olma ve Google auth akışı

import logging
import requests
import pyrebase
from typing import Dict, Tuple, Optional
import threading
from threading import Timer
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import socket
import webbrowser
import os
from dotenv import load_dotenv
import re
import json
from datetime import datetime, timedelta

# Ortam değişkenlerini yükle
load_dotenv()

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('auth')

class CallbackHandler(BaseHTTPRequestHandler):
    """Google OAuth callback için HTTP handler."""
    
    def do_GET(self):
        # URL'den kod parametresini çıkar
        path_parts = self.path.split('?', 1)
        if len(path_parts) > 1:
            query = path_parts[1]
            params = urllib.parse.parse_qs(query)
            self.server.auth_code = params.get("code", [None])[0]
            self.server.error = params.get("error", [None])[0]
        else:
            self.server.auth_code = None
            self.server.error = None

        # HTTP yanıtı gönder
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        # Sonuç durumunu belirle
        if self.server.auth_code:
            success = True
            message = "Kimlik doğrulama başarılı!"
            sub_message = "Guard uygulamasına geri dönebilirsiniz."
            icon = "✓"
            icon_class = "success-icon"
        elif self.server.error:
            success = False
            message = "Kimlik Doğrulama İptal Edildi!"
            sub_message = f"Hata: {self.server.error}"
            icon = "✗"
            icon_class = "error-icon"
        else:
            success = False
            message = "Kimlik Doğrulama Başarısız!"
            sub_message = "Bilinmeyen bir hata oluştu."
            icon = "✗"
            icon_class = "error-icon"

        # HTML içeriği oluştur
        html_content = self._generate_response_html(
            success=success,
            message=message,
            sub_message=sub_message,
            icon=icon,
            icon_class=icon_class
        )

        self.wfile.write(html_content.encode('utf-8'))

    def _generate_response_html(self, success: bool, message: str, sub_message: str, 
                               icon: str, icon_class: str) -> str:
        """Yanıt HTML'ini oluşturur."""
        
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guard Uygulaması - Kimlik Doğrulama</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            background-size: 400% 400%;
            animation: gradientShift 8s ease infinite;
            overflow: hidden;
            position: relative;
        }}

        body::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="50" cy="50" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            pointer-events: none;
        }}

        .floating-shapes {{
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: 1;
        }}

        .shape {{
            position: absolute;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            animation: float 6s ease-in-out infinite;
        }}

        .shape:nth-child(1) {{
            width: 80px;
            height: 80px;
            top: 20%;
            left: 10%;
            animation-delay: 0s;
        }}

        .shape:nth-child(2) {{
            width: 120px;
            height: 120px;
            top: 60%;
            right: 15%;
            animation-delay: 2s;
        }}

        .shape:nth-child(3) {{
            width: 60px;
            height: 60px;
            bottom: 20%;
            left: 20%;
            animation-delay: 4s;
        }}

        .container {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 480px;
            width: 90%;
            padding: 50px 40px;
            border-radius: 24px;
            box-shadow: 
                0 25px 50px rgba(0, 0, 0, 0.15),
                0 0 0 1px rgba(255, 255, 255, 0.1);
            text-align: center;
            animation: slideInUp 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            position: relative;
            z-index: 2;
            overflow: hidden;
        }}

        .container::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
            background-size: 200% 100%;
            animation: shimmer 3s ease infinite;
        }}

        .icon-wrapper {{
            position: relative;
            display: inline-block;
            margin-bottom: 30px;
        }}

        .icon {{
            font-size: 90px;
            animation: iconPulse 2s ease-in-out infinite;
            position: relative;
            z-index: 1;
        }}

        .icon-bg {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 140px;
            height: 140px;
            border-radius: 50%;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            animation: pulse 2s ease-in-out infinite;
        }}

        .success-icon {{ 
            color: #10b981; 
            text-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
        }}
        
        .error-icon {{ 
            color: #ef4444; 
            text-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
        }}

        h2 {{
            color: #1f2937;
            font-size: 32px;
            margin-bottom: 16px;
            font-weight: 600;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }}

        p {{
            color: #6b7280;
            font-size: 18px;
            margin-bottom: 24px;
            line-height: 1.6;
            font-weight: 400;
        }}

        .progress-bar {{
            width: 100%;
            height: 4px;
            background: rgba(107, 114, 128, 0.2);
            border-radius: 2px;
            margin: 30px 0 20px;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 2px;
            animation: progressFill 4s ease-out;
        }}

        .close-text {{
            font-size: 15px;
            color: #9ca3af;
            margin-top: 20px;
            font-weight: 500;
            animation: fadeInUp 1s ease-out 1s both;
        }}

        .countdown {{
            display: inline-block;
            min-width: 20px;
            font-weight: 600;
            color: #667eea;
        }}

        @keyframes gradientShift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}

        @keyframes slideInUp {{
            0% {{ 
                opacity: 0; 
                transform: translateY(60px) scale(0.95); 
            }}
            100% {{ 
                opacity: 1; 
                transform: translateY(0) scale(1); 
            }}
        }}

        @keyframes iconPulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
        }}

        @keyframes pulse {{
            0%, 100% {{ transform: translate(-50%, -50%) scale(1); opacity: 0.5; }}
            50% {{ transform: translate(-50%, -50%) scale(1.1); opacity: 0.8; }}
        }}

        @keyframes fadeInUp {{
            0% {{ 
                opacity: 0; 
                transform: translateY(20px); 
            }}
            100% {{ 
                opacity: 1; 
                transform: translateY(0); 
            }}
        }}

        @keyframes shimmer {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}

        @keyframes progressFill {{
            0% {{ width: 0%; }}
            100% {{ width: 100%; }}
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
            50% {{ transform: translateY(-20px) rotate(180deg); }}
        }}

        @media (max-width: 480px) {{
            .container {{
                padding: 40px 30px;
                margin: 20px;
            }}
            
            h2 {{
                font-size: 28px;
            }}
            
            .icon {{
                font-size: 70px;
            }}
            
            .icon-bg {{
                width: 120px;
                height: 120px;
            }}
        }}
    </style>
</head>
<body>
    <div class="floating-shapes">
        <div class="shape"></div>
        <div class="shape"></div>
        <div class="shape"></div>
    </div>

    <div class="container">
        <div class="icon-wrapper">
            <div class="icon-bg"></div>
            <div class="{icon_class} icon">{icon}</div>
        </div>
        
        <h2>{message}</h2>
        <p>{sub_message}</p>
        
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
        
        <p class="close-text">
            Bu pencere <span class="countdown" id="countdown">4</span> saniye içinde otomatik olarak kapanacak
        </p>
    </div>

    <script>
        // Geri sayım işlevi
        let seconds = 4;
        const countdownElement = document.getElementById('countdown');
        
        const timer = setInterval(function() {{
            seconds--;
            if (countdownElement) {{
                countdownElement.textContent = seconds;
            }}
            
            if (seconds <= 0) {{
                clearInterval(timer);
                window.close();
            }}
        }}, 1000);

        // Klavye kısayolu - ESC ile pencereyi kapatma
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                window.close();
            }}
        }});
    </script>
</body>
</html>"""

    def log_message(self, format, *args):
        """Log mesajlarını bastır"""
        pass

class FirebaseAuth:
    """Firebase kimlik doğrulama işlemlerini yöneten sınıf."""

    def __init__(self, firebase_config: Dict):
        try:
            self.config = firebase_config
            self.firebase = pyrebase.initialize_app(firebase_config)
            self.auth = self.firebase.auth()
            self.current_user: Optional[Dict] = None
            self.token_expiry: Optional[datetime] = None
            self._token_refresh_timer: Optional[Timer] = None
            self.callback_server = None
            logging.info("Firebase Authentication başlatıldı.")
            self._start_token_refresh_timer()
        except Exception as e:
            logging.error(f"Firebase başlatma hatası: {str(e)}", exc_info=True)
            raise

    def _start_token_refresh_timer(self):
        """Token yenileme işlemini otomatik olarak arka planda yürütür."""
        if self._token_refresh_timer:
            self._token_refresh_timer.cancel()

        # Token yenileme işlemi her 50 dakikada bir çalışacak
        self._token_refresh_timer = Timer(50 * 60, self._auto_refresh_token)
        self._token_refresh_timer.daemon = True
        self._token_refresh_timer.start()

    def _auto_refresh_token(self):
        """Token'ı otomatik olarak yeniler."""
        if self.is_logged_in() and self.refresh_auth_token():
            logging.info("Token otomatik olarak yenilendi.")
            self._start_token_refresh_timer()  # Timer'ı yeniden başlat

    def sign_in_with_email_password(self, email: str, password: str) -> Dict:
        """E-posta/şifre ile giriş yapar."""
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            account_info = self.auth.get_account_info(user['idToken'])
            user_info = user.copy()
            if 'users' in account_info and account_info['users']:
                user_info.update(account_info['users'][0])
            self.current_user = user_info
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logging.info(f"Kullanıcı giriş yaptı: {user_info.get('email', '-')}")
            self._start_token_refresh_timer()
            return user_info
        except Exception as e:
            raise Exception(self._format_error_message(e))

    def create_user_with_email_password(self, email: str, password: str) -> Dict:
        """Yeni kullanıcı oluşturur."""
        try:
            user = self.auth.create_user_with_email_and_password(email, password)
            account_info = self.auth.get_account_info(user['idToken'])
            user_info = user.copy()
            if 'users' in account_info and account_info['users']:
                user_info.update(account_info['users'][0])
            self.current_user = user_info
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logging.info(f"Yeni kullanıcı oluşturuldu: {user_info.get('email', '-')}")
            self._start_token_refresh_timer()
            return user_info
        except Exception as e:
            raise Exception(self._format_error_message(e))

    def update_profile(self, display_name: Optional[str] = None, photo_url: Optional[str] = None, phone_number: Optional[str] = None) -> bool:
        """Kullanıcı adını, foto URL'sini ve telefon numarasını günceller."""
        if not self.current_user:
            raise Exception("Profil güncelleme için giriş yapılmamış.")
        update_data = {}
        if display_name:
            update_data['displayName'] = display_name
        if photo_url:
            update_data['photoUrl'] = photo_url
        if not update_data:
            return True

        self.auth.update_profile(self.current_user['idToken'], **update_data)
        self.current_user.update(update_data)

        # Telefon numarası güncelleme
        if phone_number:
            self.current_user['phoneNumber'] = phone_number

        return True

    def sign_out(self) -> bool:
        """Çıkış yapar."""
        self.current_user = None
        self.token_expiry = None
        if self._token_refresh_timer:
            self._token_refresh_timer.cancel()
        if self.callback_server:
            try:
                self.callback_server.server_close()
            except:
                pass
        logging.info("Kullanıcı çıkış yaptı.")
        return True

    def get_current_user(self) -> Optional[Dict]:
        return self.current_user

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def sign_in_with_google(self) -> Tuple[str, str]:
        """Google OAuth ile giriş işlemini başlatır."""
        try:
            # Dinamik port seçimi
            port = self._find_available_port(3000)
            redirect_uri = f"http://localhost:{port}"

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            if not client_id:
                raise Exception("GOOGLE_CLIENT_ID ortam değişkeni bulunamadı.")

            # OAuth URL'si oluştur
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope=email%20profile&"
                f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
                f"access_type=offline&"
                f"prompt=select_account"
            )

            # HTTP sunucusunu başlat
            self.callback_server = HTTPServer(("localhost", port), CallbackHandler)
            self.callback_server.auth_code = None
            self.callback_server.error = None

            # Sunucuyu ayrı thread'de çalıştır
            server_thread = threading.Thread(target=self.callback_server.handle_request, daemon=True)
            server_thread.start()

            # Tarayıcıyı aç
            webbrowser.open(auth_url)
            logging.info(f"Google kimlik doğrulama URL'si açıldı: {auth_url}")

            # Kullanıcının yanıtını bekle (maksimum 120 saniye)
            start_time = time.time()
            timeout = 120  # 2 dakika
            
            while (self.callback_server.auth_code is None and 
                   self.callback_server.error is None and 
                   time.time() - start_time < timeout):
                time.sleep(0.5)

            # Sunucu thread'inin bitmesini bekle
            server_thread.join(timeout=5)

            if self.callback_server.error:
                raise Exception(f"Google giriş hatası: {self.callback_server.error}")
            elif self.callback_server.auth_code:
                return auth_url, self.callback_server.auth_code
            else:
                raise Exception("Google giriş zaman aşımına uğradı veya iptal edildi.")

        except Exception as e:
            logging.error(f"Google giriş başlatılırken hata: {str(e)}")
            raise Exception(f"Google giriş hatası: {str(e)}")
        finally:
            # Sunucuyu temizle
            if self.callback_server:
                try:
                    self.callback_server.server_close()
                except:
                    pass
                self.callback_server = None

    def complete_google_sign_in(self, request_token: str, auth_code: str) -> Dict:
        """Google yetkilendirme kodunu kullanarak Firebase'e giriş yapar."""
        try:
            if not auth_code:
                raise Exception("Yetkilendirme kodu bulunamadı.")

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                raise Exception("Google OAuth yapılandırması eksik.")

            # Port dinamik olarak ayarla
            port = self._find_available_port(3000)
            redirect_uri = f"http://localhost:{port}"

            # Google'dan access token al
            logging.info("Google'dan access token alınıyor...")
            token_response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": auth_code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                },
                timeout=30
            )
            
            if not token_response.ok:
                logging.error(f"Token alma hatası: {token_response.status_code} - {token_response.text}")
                raise Exception(f"Google token alınamadı: {token_response.status_code}")

            tokens = token_response.json()
            id_token = tokens.get("id_token")
            access_token = tokens.get("access_token")

            if not id_token:
                raise Exception("Google ID token bulunamadı.")

            logging.info("Firebase'e Google ile giriş yapılıyor...")
            
            # Firebase'e Google ile giriş yap
            firebase_response = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={self.config['apiKey']}",
                json={
                    "postBody": f"id_token={id_token}&providerId=google.com",
                    "requestUri": redirect_uri,
                    "returnIdpCredential": True,
                    "returnSecureToken": True
                },
                timeout=30
            )

            if not firebase_response.ok:
                logging.error(f"Firebase giriş hatası: {firebase_response.status_code} - {firebase_response.text}")
                raise Exception(f"Firebase Google girişi başarısız: {firebase_response.status_code}")

            user_data = firebase_response.json()
            
            # Kullanıcı bilgilerini al
            account_info = self.auth.get_account_info(user_data['idToken'])
            user_info = user_data.copy()
            
            if 'users' in account_info and account_info['users']:
                user_info.update(account_info['users'][0])

            # Google'dan ek kullanıcı bilgileri al
            if access_token:
                try:
                    user_info_response = requests.get(
                        f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}",
                        timeout=10
                    )
                    if user_info_response.ok:
                        google_user_info = user_info_response.json()
                        # Google'dan gelen bilgileri ekle
                        if 'name' in google_user_info and not user_info.get('displayName'):
                            user_info['displayName'] = google_user_info['name']
                        if 'picture' in google_user_info and not user_info.get('photoUrl'):
                            user_info['photoUrl'] = google_user_info['picture']
                except Exception as e:
                    logging.warning(f"Google kullanıcı bilgileri alınırken hata: {e}")

            # Oturum bilgilerini ayarla
            self.current_user = user_info
            self.token_expiry = datetime.now() + timedelta(hours=1)
            
            logging.info(f"Google ile giriş başarılı: {user_info.get('email', 'Bilinmeyen')}")
            self._start_token_refresh_timer()

            return user_info

        except Exception as e:
            logging.error(f"Google giriş tamamlanırken hata: {str(e)}")
            raise Exception(f"Google giriş tamamlanamadı: {str(e)}")

    def send_password_reset_email(self, email: str) -> bool:
        """Şifre sıfırlama e-postası gönderir."""
        try:
            self.auth.send_password_reset_email(email)
            logging.info(f"Şifre sıfırlama e-postası gönderildi: {email}")
            return True
        except Exception as e:
            error_msg = self._format_error_message(e)
            logging.error(f"Şifre sıfırlama e-postası gönderilirken hata: {error_msg}")
            raise Exception(error_msg)

    def refresh_auth_token(self) -> bool:
        """JWT token'ını yeniler."""
        try:
            if not self.current_user:
                return False

            user = self.auth.refresh(self.current_user['refreshToken'])
            self.current_user['idToken'] = user['idToken']
            self.current_user['refreshToken'] = user['refreshToken']
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logging.info(f"Token yenilendi: {self.current_user.get('email', '-')}")
            return True
        except Exception as e:
            logging.error(f"Token yenileme hatası: {str(e)}")
            return False

    def _find_available_port(self, start_port: int) -> int:
        """Boş bir port bulur."""
        port = start_port
        max_attempts = 100
        
        for _ in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                port += 1
        
        raise Exception(f"Boş port bulunamadı ({start_port}-{start_port + max_attempts})")

    def _format_error_message(self, error: Exception) -> str:
        """Firebase API hatalarını okunabilir mesaja çevirir."""
        error_str = str(error)
        
        # Yaygın Firebase hataları
        error_mappings = {
            "INVALID_EMAIL": "Geçersiz e-posta adresi.",
            "EMAIL_NOT_FOUND": "Bu e-posta adresi kayıtlı değil.",
            "INVALID_PASSWORD": "Yanlış şifre.",
            "INVALID_LOGIN_CREDENTIALS": "E-posta veya şifre hatalı.",
            "EMAIL_EXISTS": "Bu e-posta zaten kullanılıyor.",
            "WEAK_PASSWORD": "Şifre en az 6 karakter olmalı.",
            "TOO_MANY_ATTEMPTS": "Çok fazla hatalı giriş denemesi. Lütfen bir süre bekleyin.",
            "USER_DISABLED": "Bu kullanıcı hesabı devre dışı bırakılmış.",
            "INVALID_ID_TOKEN": "Geçersiz kimlik token'ı. Lütfen tekrar giriş yapın.",
            "TOKEN_EXPIRED": "Oturum süresi doldu. Lütfen tekrar giriş yapın."
        }
        
        for error_code, user_message in error_mappings.items():
            if error_code in error_str:
                return user_message
                
        return f"Bir hata oluştu: {error_str}"

        self.wfile.write(html_content.encode('utf-8'))

    def log_message(self, format, *args):
        """Log mesajlarını bastır"""
        pass

class FirebaseAuth:
    """Firebase kimlik doğrulama işlemlerini yöneten sınıf."""

    def __init__(self, firebase_config: Dict):
        try:
            self.config = firebase_config
            self.firebase = pyrebase.initialize_app(firebase_config)
            self.auth = self.firebase.auth()
            self.current_user: Optional[Dict] = None
            self.token_expiry: Optional[datetime] = None
            self._token_refresh_timer: Optional[Timer] = None
            self.callback_server = None
            logging.info("Firebase Authentication başlatıldı.")
            self._start_token_refresh_timer()
        except Exception as e:
            logging.error(f"Firebase başlatma hatası: {str(e)}", exc_info=True)
            raise

    def _start_token_refresh_timer(self):
        """Token yenileme işlemini otomatik olarak arka planda yürütür."""
        if self._token_refresh_timer:
            self._token_refresh_timer.cancel()

        # Token yenileme işlemi her 50 dakikada bir çalışacak
        self._token_refresh_timer = Timer(50 * 60, self._auto_refresh_token)
        self._token_refresh_timer.daemon = True
        self._token_refresh_timer.start()

    def _auto_refresh_token(self):
        """Token'ı otomatik olarak yeniler."""
        if self.is_logged_in() and self.refresh_auth_token():
            logging.info("Token otomatik olarak yenilendi.")
            self._start_token_refresh_timer()  # Timer'ı yeniden başlat

    def sign_in_with_email_password(self, email: str, password: str) -> Dict:
        """E-posta/şifre ile giriş yapar."""
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            account_info = self.auth.get_account_info(user['idToken'])
            user_info = user.copy()
            if 'users' in account_info and account_info['users']:
                user_info.update(account_info['users'][0])
            self.current_user = user_info
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logging.info(f"Kullanıcı giriş yaptı: {user_info.get('email', '-')}")
            self._start_token_refresh_timer()
            return user_info
        except Exception as e:
            raise Exception(self._format_error_message(e))

    def create_user_with_email_password(self, email: str, password: str) -> Dict:
        """Yeni kullanıcı oluşturur."""
        try:
            user = self.auth.create_user_with_email_and_password(email, password)
            account_info = self.auth.get_account_info(user['idToken'])
            user_info = user.copy()
            if 'users' in account_info and account_info['users']:
                user_info.update(account_info['users'][0])
            self.current_user = user_info
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logging.info(f"Yeni kullanıcı oluşturuldu: {user_info.get('email', '-')}")
            self._start_token_refresh_timer()
            return user_info
        except Exception as e:
            raise Exception(self._format_error_message(e))

    def update_profile(self, display_name: Optional[str] = None, photo_url: Optional[str] = None, phone_number: Optional[str] = None) -> bool:
        """Kullanıcı adını, foto URL'sini ve telefon numarasını günceller."""
        if not self.current_user:
            raise Exception("Profil güncelleme için giriş yapılmamış.")
        update_data = {}
        if display_name:
            update_data['displayName'] = display_name
        if photo_url:
            update_data['photoUrl'] = photo_url
        if not update_data:
            return True

        self.auth.update_profile(self.current_user['idToken'], **update_data)
        self.current_user.update(update_data)

        # Telefon numarası güncelleme
        if phone_number:
            self.current_user['phoneNumber'] = phone_number

        return True

    def sign_out(self) -> bool:
        """Çıkış yapar."""
        self.current_user = None
        self.token_expiry = None
        if self._token_refresh_timer:
            self._token_refresh_timer.cancel()
        if self.callback_server:
            try:
                self.callback_server.server_close()
            except:
                pass
        logging.info("Kullanıcı çıkış yaptı.")
        return True

    def get_current_user(self) -> Optional[Dict]:
        return self.current_user

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def sign_in_with_google(self) -> Tuple[str, str]:
        """Google OAuth ile giriş işlemini başlatır."""
        try:
            # Dinamik port seçimi
            port = self._find_available_port(3000)
            redirect_uri = f"http://localhost:{port}"

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            if not client_id:
                raise Exception("GOOGLE_CLIENT_ID ortam değişkeni bulunamadı.")

            # OAuth URL'si oluştur
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope=email%20profile&"
                f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
                f"access_type=offline&"
                f"prompt=select_account"
            )

            # HTTP sunucusunu başlat
            self.callback_server = HTTPServer(("localhost", port), CallbackHandler)
            self.callback_server.auth_code = None
            self.callback_server.error = None

            # Sunucuyu ayrı thread'de çalıştır
            server_thread = threading.Thread(target=self.callback_server.handle_request, daemon=True)
            server_thread.start()

            # Tarayıcıyı aç
            webbrowser.open(auth_url)
            logging.info(f"Google kimlik doğrulama URL'si açıldı: {auth_url}")

            # Kullanıcının yanıtını bekle (maksimum 120 saniye)
            start_time = time.time()
            timeout = 120  # 2 dakika
            
            while (self.callback_server.auth_code is None and 
                   self.callback_server.error is None and 
                   time.time() - start_time < timeout):
                time.sleep(0.5)

            # Sunucu thread'inin bitmesini bekle
            server_thread.join(timeout=5)

            if self.callback_server.error:
                raise Exception(f"Google giriş hatası: {self.callback_server.error}")
            elif self.callback_server.auth_code:
                return auth_url, self.callback_server.auth_code
            else:
                raise Exception("Google giriş zaman aşımına uğradı veya iptal edildi.")

        except Exception as e:
            logging.error(f"Google giriş başlatılırken hata: {str(e)}")
            raise Exception(f"Google giriş hatası: {str(e)}")
        finally:
            # Sunucuyu temizle
            if self.callback_server:
                try:
                    self.callback_server.server_close()
                except:
                    pass
                self.callback_server = None

    def complete_google_sign_in(self, request_token: str, auth_code: str) -> Dict:
        """Google yetkilendirme kodunu kullanarak Firebase'e giriş yapar."""
        try:
            if not auth_code:
                raise Exception("Yetkilendirme kodu bulunamadı.")

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                raise Exception("Google OAuth yapılandırması eksik.")

            # Port dinamik olarak ayarla
            port = self._find_available_port(3000)
            redirect_uri = f"http://localhost:{port}"

            # Google'dan access token al
            logging.info("Google'dan access token alınıyor...")
            token_response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": auth_code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                },
                timeout=30
            )
            
            if not token_response.ok:
                logging.error(f"Token alma hatası: {token_response.status_code} - {token_response.text}")
                raise Exception(f"Google token alınamadı: {token_response.status_code}")

            tokens = token_response.json()
            id_token = tokens.get("id_token")
            access_token = tokens.get("access_token")

            if not id_token:
                raise Exception("Google ID token bulunamadı.")

            logging.info("Firebase'e Google ile giriş yapılıyor...")
            
            # Firebase'e Google ile giriş yap
            firebase_response = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={self.config['apiKey']}",
                json={
                    "postBody": f"id_token={id_token}&providerId=google.com",
                    "requestUri": redirect_uri,
                    "returnIdpCredential": True,
                    "returnSecureToken": True
                },
                timeout=30
            )

            if not firebase_response.ok:
                logging.error(f"Firebase giriş hatası: {firebase_response.status_code} - {firebase_response.text}")
                raise Exception(f"Firebase Google girişi başarısız: {firebase_response.status_code}")

            user_data = firebase_response.json()
            
            # Kullanıcı bilgilerini al
            account_info = self.auth.get_account_info(user_data['idToken'])
            user_info = user_data.copy()
            
            if 'users' in account_info and account_info['users']:
                user_info.update(account_info['users'][0])

            # Google'dan ek kullanıcı bilgileri al
            if access_token:
                try:
                    user_info_response = requests.get(
                        f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}",
                        timeout=10
                    )
                    if user_info_response.ok:
                        google_user_info = user_info_response.json()
                        # Google'dan gelen bilgileri ekle
                        if 'name' in google_user_info and not user_info.get('displayName'):
                            user_info['displayName'] = google_user_info['name']
                        if 'picture' in google_user_info and not user_info.get('photoUrl'):
                            user_info['photoUrl'] = google_user_info['picture']
                except Exception as e:
                    logging.warning(f"Google kullanıcı bilgileri alınırken hata: {e}")

            # Oturum bilgilerini ayarla
            self.current_user = user_info
            self.token_expiry = datetime.now() + timedelta(hours=1)
            
            logging.info(f"Google ile giriş başarılı: {user_info.get('email', 'Bilinmeyen')}")
            self._start_token_refresh_timer()

            return user_info

        except Exception as e:
            logging.error(f"Google giriş tamamlanırken hata: {str(e)}")
            raise Exception(f"Google giriş tamamlanamadı: {str(e)}")

    def send_password_reset_email(self, email: str) -> bool:
        """Şifre sıfırlama e-postası gönderir."""
        try:
            self.auth.send_password_reset_email(email)
            logging.info(f"Şifre sıfırlama e-postası gönderildi: {email}")
            return True
        except Exception as e:
            error_msg = self._format_error_message(e)
            logging.error(f"Şifre sıfırlama e-postası gönderilirken hata: {error_msg}")
            raise Exception(error_msg)

    def refresh_auth_token(self) -> bool:
        """JWT token'ını yeniler."""
        try:
            if not self.current_user:
                return False

            user = self.auth.refresh(self.current_user['refreshToken'])
            self.current_user['idToken'] = user['idToken']
            self.current_user['refreshToken'] = user['refreshToken']
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logging.info(f"Token yenilendi: {self.current_user.get('email', '-')}")
            return True
        except Exception as e:
            logging.error(f"Token yenileme hatası: {str(e)}")
            return False

    def _find_available_port(self, start_port: int) -> int:
        """Boş bir port bulur."""
        port = start_port
        max_attempts = 100
        
        for _ in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                port += 1
        
        raise Exception(f"Boş port bulunamadı ({start_port}-{start_port + max_attempts})")

    def _format_error_message(self, error: Exception) -> str:
        """Firebase API hatalarını okunabilir mesaja çevirir."""
        error_str = str(error)
        
        # Yaygın Firebase hataları
        error_mappings = {
            "INVALID_EMAIL": "Geçersiz e-posta adresi.",
            "EMAIL_NOT_FOUND": "Bu e-posta adresi kayıtlı değil.",
            "INVALID_PASSWORD": "Yanlış şifre.",
            "INVALID_LOGIN_CREDENTIALS": "E-posta veya şifre hatalı.",
            "EMAIL_EXISTS": "Bu e-posta zaten kullanılıyor.",
            "WEAK_PASSWORD": "Şifre en az 6 karakter olmalı.",
            "TOO_MANY_ATTEMPTS": "Çok fazla hatalı giriş denemesi. Lütfen bir süre bekleyin.",
            "USER_DISABLED": "Bu kullanıcı hesabı devre dışı bırakılmış.",
            "INVALID_ID_TOKEN": "Geçersiz kimlik token'ı. Lütfen tekrar giriş yapın.",
            "TOKEN_EXPIRED": "Oturum süresi doldu. Lütfen tekrar giriş yapın."
        }
        
        for error_code, user_message in error_mappings.items():
            if error_code in error_str:
                return user_message
                
        return f"Bir hata oluştu: {error_str}"