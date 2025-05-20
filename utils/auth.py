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
    def __init__(self, *args, **kwargs):
        self.auth_result = kwargs.pop('auth_result', {'success': True, 'email': None, 'error': None})
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        # URL'den kod parametresini çıkar
        path_parts = self.path.split('?', 1)
        if len(path_parts) > 1:
            query = path_parts[1]
            self.server.auth_code = urllib.parse.parse_qs(query).get("code", [None])[0]
        else:
            self.server.auth_code = None

        # Dinamik HTML içeriği
        success = self.auth_result.get('success', True)
        email = self.auth_result.get('email', None)
        error = self.auth_result.get('error', None)

        if success and email:
            message = f"Kimlik doğrulama başarılı! ({email})"
            sub_message = "Guard uygulamasına geri dönebilirsiniz."
        else:
            message = "Kimlik Doğrulama Başarısız!"
            sub_message = error if error else "Bir hata oluştu. Lütfen tekrar deneyin."

        html_content = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <title>Guard Uygulaması - Kimlik Doğrulama</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #e0f7fa 0%, #80deea 100%);
                    overflow: hidden;
                }}
                .container {{
                    background: white;
                    max-width: 450px;
                    width: 90%;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
                    text-align: center;
                    animation: fadeIn 1s ease-in-out;
                }}
                .icon {{
                    font-size: 80px;
                    margin-bottom: 20px;
                    animation: bounce 1s ease-in-out;
                }}
                .success-icon {{ color: #00c853; }}
                .error-icon {{ color: #d32f2f; }}
                h2 {{
                    color: #0288d1;
                    font-size: 28px;
                    margin-bottom: 15px;
                    font-weight: 600;
                }}
                p {{
                    color: #555;
                    font-size: 16px;
                    margin-bottom: 20px;
                    line-height: 1.5;
                }}
                .close-text {{
                    font-size: 14px;
                    color: #888;
                    margin-top: 20px;
                    animation: fadeInText 1.5s ease-in-out;
                }}
                @keyframes fadeIn {{
                    0% {{ opacity: 0; transform: translateY(20px); }}
                    100% {{ opacity: 1; transform: translateY(0); }}
                }}
                @keyframes bounce {{
                    0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
                    40% {{ transform: translateY(-30px); }}
                    60% {{ transform: translateY(-15px); }}
                }}
                @keyframes fadeInText {{
                    0% {{ opacity: 0; }}
                    100% {{ opacity: 1; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="{ 'success-icon' if success else 'error-icon' } icon">{ '✓' if success else '✗' }</div>
                <h2>{ message }</h2>
                <p>{ sub_message }</p>
                <p class="close-text">Pencere otomatik olarak kapanıyor...</p>
            </div>
            <script>
                setTimeout(function() {{
                    window.close();
                }}, 3000);
            </script>
        </body>
        </html>
        """

        self.wfile.write(html_content.encode('ascii', 'ignore'))

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
            logging.info("Firebase Authentication başlatıldı.")
            self._start_token_refresh_timer()
        except Exception as e:
            logging.error(f"Firebase başlatma hatası: {str(e)}", exc_info=True)
            raise

    def _start_token_refresh_timer(self):
        """Token yenileme işlemini otomatik olarak arka planda yürütür."""
        if self._token_refresh_timer:
            self._token_refresh_timer.cancel()

        # Token yenileme işlemi her 50 dakikada bir çalışacak (Firebase token'ları genelde 1 saat geçerli)
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
            self.token_expiry = datetime.now() + timedelta(hours=1)  # Token süresi 1 saat
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

        # Telefon numarası güncelleme (API destek vermediği için sadece yerel kullanıcı nesnesini güncelliyoruz)
        if phone_number:
            self.current_user['phoneNumber'] = phone_number

        return True

    def sign_out(self) -> bool:
        """Çıkış yapar."""
        self.current_user = None
        self.token_expiry = None
        if self._token_refresh_timer:
            self._token_refresh_timer.cancel()
        logging.info("Kullanıcı çıkış yaptı.")
        return True

    def get_current_user(self) -> Optional[Dict]:
        return self.current_user

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def sign_in_with_google(self) -> Tuple[str, str]:
        """Tarayıcı ile Google yetkilendirme işlemini başlatır."""
        try:
            # Dinamik port seçimi
            port = self._find_available_port(3000)
            redirect_uri = f"http://localhost:{port}"

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            if not client_id:
                raise Exception("GOOGLE_CLIENT_ID ortam değişkeni bulunamadı.")

            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope=email%20profile&"
                f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
                f"access_type=offline"
            )

            server = HTTPServer(("localhost", port), lambda *args, **kwargs: CallbackHandler(
                *args, auth_result={'success': True}, **kwargs
            ))
            server.auth_code = None
            threading.Thread(target=server.handle_request, daemon=True).start()

            # Tarayıcıyı aç
            webbrowser.open(auth_url)
            logging.info(f"Google kimlik doğrulama URL'si açıldı: {auth_url}")

            start_time = time.time()
            while server.auth_code is None and time.time() - start_time < 60:
                time.sleep(0.1)

            if server.auth_code:
                return auth_url, server.auth_code
            else:
                raise Exception("Google giriş zaman aşımına uğradı.")

        except Exception as e:
            raise Exception(f"Google giriş hatası: {str(e)}")

    def complete_google_sign_in(self, request_token: str, auth_code: str) -> Dict:
        """Google yetkilendirme tamamlanır ve Firebase'e login olunur."""
        try:
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            redirect_uri = f"http://localhost:3000"

            # Google'dan token al
            token_resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": auth_code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            token_resp.raise_for_status()
            tokens = token_resp.json()
            id_token = tokens.get("id_token")

            if not id_token:
                raise Exception("Google ID token alınamadı.")

            firebase_resp = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={self.config['apiKey']}",
                json={
                    "postBody": f"id_token={id_token}&providerId=google.com",
                    "requestUri": redirect_uri,
                    "returnIdpCredential": True,
                    "returnSecureToken": True
                }
            )
            firebase_resp.raise_for_status()
            user = firebase_resp.json()

            account_info = self.auth.get_account_info(user['idToken'])
            user_info = user.copy()
            if 'users' in account_info and account_info['users']:
                user_info.update(account_info['users'][0])
            self.current_user = user_info
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logging.info(f"Google ile giriş başarılı: {user_info.get('email', '-')}")
            self._start_token_refresh_timer()

            # CallbackHandler'a dinamik içerik gönder
            port = 3000
            server = HTTPServer(("localhost", port), lambda *args, **kwargs: CallbackHandler(
                *args, auth_result={'success': True, 'email': user_info.get('email', None)}, **kwargs
            ))
            server.handle_request()

            return user_info

        except Exception as e:
            logging.error(f"Google giriş tamamlanamadı: {str(e)}")
            # Hata durumunda kullanıcıya bilgi ver
            port = 3000
            server = HTTPServer(("localhost", port), lambda *args, **kwargs: CallbackHandler(
                *args, auth_result={'success': False, 'error': str(e)}, **kwargs
            ))
            server.handle_request()
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
        """JWT token'ını yeniler ve hataları ele alır."""
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
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except OSError:
                    port += 1
                    if port > start_port + 1000:  # Maksimum 1000 port denenir
                        raise Exception("Boş bir port bulunamadı.")

    def _format_error_message(self, error: Exception) -> str:
        """Firebase API hatalarını okunabilir mesaja çevirir."""
        error_str = str(error)
        if "INVALID_EMAIL" in error_str:
            return "Geçersiz e-posta adresi."
        elif "EMAIL_NOT_FOUND" in error_str:
            return "Bu e-posta adresi kayıtlı değil."
        elif "INVALID_PASSWORD" in error_str:
            return "Yanlış şifre."
        elif "EMAIL_EXISTS" in error_str:
            return "Bu e-posta zaten kullanılıyor."
        elif "WEAK_PASSWORD" in error_str:
            return "Şifre en az 6 karakter olmalı."
        elif "TOO_MANY_ATTEMPTS" in error_str:
            return "Çok fazla hatalı giriş denemesi. Lütfen bir süre bekleyin."
        elif "USER_DISABLED" in error_str:
            return "Bu kullanıcı hesabı devre dışı bırakılmış."
        elif "INVALID_ID_TOKEN" in error_str:
            return "Geçersiz kimlik token'ı. Lütfen tekrar giriş yapın."
        elif "TOKEN_EXPIRED" in error_str:
            return "Oturum süresi doldu. Lütfen tekrar giriş yapın."
        return f"Bir hata oluştu: {error_str}"