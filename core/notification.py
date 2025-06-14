# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: notification.py (GELİŞMİŞ BİLDİRİM SİSTEMİ)
# Konum: guard_pc_app/core/notification.py
# Açıklama:
# Bu sınıf, Guard AI uygulamasında düşme olayları tespit edildiğinde kullanıcıya 
# çeşitli iletişim kanalları üzerinden bilgilendirme göndermek için kullanılır.
#
# Desteklenen Bildirim Kanalları:
# - E-posta (SMTP ile)
# - SMS (Twilio API veya benzeri)
# - Telegram mesajı (Telegram Bot API)
# - Mobil Push Bildirimi (Firebase Cloud Messaging - FCM)

# === ÖZELLİKLER ===
# - Çoklu bildirim kanalı desteği
# - Asenkron kuyruk sistemi (Queue)
# - Bildirim geçmişi saklama
# - Kullanıcı ayarlarına göre bildirim tercihleri
# - Test bildirimleri için özel mod
# - Hata durumunda fallback mekanizması (örn. SMS başarısızsa e-posta gönderimi)

# === BAŞLICA MODÜLLER VE KULLANIM AMACI ===
# - smtplib / email: SMTP üzerinden e-posta gönderimi
# - telepot: Telegram botu ile mesajlaşma
# - requests: REST API çağrıları (Twilio, Telegram)
# - firebase_admin.messaging: Firebase Cloud Messaging (FCM) entegrasyonu
# - threading: Asenkron işlem yönetimi
# - queue: Bildirim kuyruğu yönetimi
# - logging: Hata ve işlem kayıtları tutma

# === SINIFLAR ===
# - NotificationManager: Birden fazla kanalda bildirim gönderen ana sınıf

# === TEMEL FONKSİYONLAR ===
# - __init__: Gerekli servisleri başlatır (SMTP, Telegram, Twilio, FCM)
# - send_notifications: Belirtilen düşme olayı için tüm aktif kanallara bildirim gönderir
# - _send_email_notification: E-posta bildirimi gönderir
# - _send_sms_notification: SMS bildirimi gönderir
# - _send_telegram_notification: Telegram mesajı gönderir
# - _send_fcm_notification: FCM push bildirimi gönderir
# - update_user_data: Kullanıcı ayarlarını günceller
# - _start_queue_processor: Bildirim kuyruğunu işleyen thread'i başlatır
# - _process_notification_queue: Bekleyen bildirimleri sırayla işler

# === BİLDİRİM İÇERİKLERİ ===
# - Düşme zamanı (timestamp)
# - Güvenilirlik oranı (confidence score)
# - Ekran görüntüsü bağlantısı (image_url)
# - Olay ID'si (event_id)
# - Test bildirimi mi? (test=True/False)

# === GÖRSEL DESTEK ===
# - Ekran görüntüsünü gömülü olarak e-postaya ekler
# - Telegram'a fotoğraf olarak gönderir
# - FCM ile URL olarak paylaşır

# === HATA YÖNETİMİ ===
# - Her kanal için hata kontrolü yapılır
# - Gönderim başarısız olursa loglanır
# - Fallback sistemleri devreye girer

# === LOGGING ===
# - Tüm işlemler log dosyasına yazılır (guard_ai_v3.log)
# - Log formatı: Tarih/Zaman [Seviye] Mesaj

# === TEST AMAÇLI KULLANIM ===
# - `if __name__ == "__main__":` bloğu ile bağımsız çalıştırılabilir
# - Mock verilerle test bildirimleri gönderilebilir

# === NOTLAR ===
# - Bu dosya, app.py, dashboard.py ve database.py ile entegre çalışır
# - Ortam değişkenleri (.env) üzerinden gizli anahtarlar alınır (SMTP, Twilio, Telegram Token vb.)
# - Kuyruk sistemi sayesinde yüksek sayıda bildirimde performans düşmez
# =======================================================================================

import logging
import smtplib
import requests
import threading
import json
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from config.settings import EMAIL_SUBJECT, EMAIL_FROM, SMS_MESSAGE, TELEGRAM_MESSAGE
import telepot
from dotenv import load_dotenv
from queue import Queue, Empty
from firebase_admin import messaging   # FCM için şart

# Ortam değişkenlerini yükle
load_dotenv()

class NotificationManager:
    """Farklı kanallarda bildirim gönderen sınıf."""
    
    _instance = None
    _init_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, user_data=None):
        """Singleton örneği döndürür, varsa user_data günceller."""
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls(user_data)
            elif user_data:
                cls._instance.update_user_data(user_data)
        return cls._instance
    
    def __init__(self, user_data=None):
        """
        Args:
            user_data (dict): Kullanıcı verisi ve bildirim tercihleri
        """
        # Singleton kontrolü
        if NotificationManager._instance is not None:
            raise RuntimeError("NotificationManager zaten başlatılmış. get_instance() kullanın.")
            
        # Kullanıcı verisi yoksa boş bir sözlük kullan
        self.user_data = user_data if user_data else {}
        self.telegram_bot = None
        
        # Bildirim kuyruğu ve işleyici thread'i
        self.notification_queue = Queue()
        self.queue_thread = None
        self.queue_running = False
        
        # Bildirim kanalları durumu
        self.channel_status = {
        "email": {"available": False, "last_error": None, "last_success": None},
        "sms": {"available": False, "last_error": None, "last_success": None},
        "telegram": {"available": False, "last_error": None, "last_success": None},
        "fcm": {"available": False, "last_error": None, "last_success": None}  # <-- FCM EKLE!
        }

        
        # Telegram botu varsa başlat
        self._init_telegram()
        
        # Email SMTP ayarlarını kontrol et
        self._validate_email_settings()
        
        # SMS API ayarlarını kontrol et
        self._validate_sms_settings()
        
        # Bildirim kuyruğu işleyicisini başlat
        self._start_queue_processor()
    
    def update_user_data(self, user_data):
        """Kullanıcı verisini günceller."""
        if user_data:
            self.user_data = user_data
            logging.info("Bildirim yöneticisi kullanıcı verisi güncellendi.")
    
    def _init_telegram(self):
        """Telegram botunu başlatır."""
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            try:
                self.telegram_bot = telepot.Bot(telegram_token)
                # Basit bağlantı testi
                bot_info = self.telegram_bot.getMe()
                self.channel_status["telegram"]["available"] = True
                logging.info(f"Telegram botu başlatıldı: {bot_info['username']}")
            except Exception as e:
                self.channel_status["telegram"]["available"] = False
                self.channel_status["telegram"]["last_error"] = str(e)
                logging.error(f"Telegram botu başlatılamadı: {str(e)}")
    
    def _validate_email_settings(self):
        """E-posta ayarlarını kontrol eder."""
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        
        if not (smtp_user and smtp_pass):
            self.channel_status["email"]["available"] = False
            self.channel_status["email"]["last_error"] = "SMTP kimlik bilgileri ayarlanmamış."
            logging.warning("SMTP kimlik bilgileri ayarlanmamış.")
            return
        
        try:
            # SMTP sunucusuna bağlantıyı test et
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.quit()
            
            self.channel_status["email"]["available"] = True
            logging.info("SMTP sunucusuna bağlantı başarılı.")
        except Exception as e:
            self.channel_status["email"]["available"] = False
            self.channel_status["email"]["last_error"] = str(e)
            logging.error(f"SMTP sunucusuna bağlantı başarısız: {str(e)}")
    
    def _validate_sms_settings(self):
        """SMS ayarlarını kontrol eder."""
        twilio_sid = os.getenv("TWILIO_SID")
        twilio_token = os.getenv("TWILIO_TOKEN")
        twilio_from = os.getenv("TWILIO_PHONE")
        
        if not (twilio_sid and twilio_token and twilio_from):
            self.channel_status["sms"]["available"] = False
            self.channel_status["sms"]["last_error"] = "Twilio kimlik bilgileri ayarlanmamış."
            logging.warning("Twilio kimlik bilgileri ayarlanmamış.")
            return
        
        # Twilio API'sini test et - tam bir test için kredi gerektiğinden sadece credentials kontrolü yap
        self.channel_status["sms"]["available"] = True
        logging.info("Twilio kimlik bilgileri mevcut.")
    
    def _start_queue_processor(self):
        """Bildirim kuyruğu işleyicisini başlatır."""
        if self.queue_thread and self.queue_thread.is_alive():
            return
            
        self.queue_running = True
        self.queue_thread = threading.Thread(target=self._process_notification_queue)
        self.queue_thread.daemon = True
        self.queue_thread.start()
        logging.info("Bildirim kuyruğu işleyicisi başlatıldı.")
    
    def _process_notification_queue(self):
        """Bildirim kuyruğunu işleyen thread fonksiyonu."""
        while self.queue_running:
            try:
                # Kuyruktan bildirim al (bloklamadan)
                try:
                    notification = self.notification_queue.get(block=True, timeout=1.0)
                except Empty:
                    continue
                
                # Bildirim tipine göre işle
                notification_type = notification.get("type", "unknown")
                
                if notification_type == "email":
                    self._send_email_notification(notification)
                elif notification_type == "sms":
                    self._send_sms_notification(notification)
                elif notification_type == "telegram":
                    self._send_telegram_notification(notification)
                
                # İşleme tamamlandı
                self.notification_queue.task_done()
                
            except Exception as e:
                logging.error(f"Bildirim kuyruğu işlenirken hata: {str(e)}")
                time.sleep(1.0)  # Hata durumunda kısa bir bekleyiş
    
    def _send_fcm_notification(self, notification):
        try:
            event_data = notification.get("event_data", {})
            event_id = event_data.get("id")
            confidence = event_data.get("confidence", 0.0)
            image_url = event_data.get("image_url")
            user_id = self.user_data.get("id") or self.user_data.get("user_id")

            logging.debug(f"FCM bildirimi için veriler: user_id={user_id}, event_id={event_id}, image_url={image_url}")

            if not user_id:
                logging.error("FCM bildirimi gönderilemedi: Kullanıcı ID bulunamadı.")
                return False

            # image_url opsiyonel olabilir
            if not image_url:
                logging.warning("FCM bildirimi: image_url eksik, görüntüsüz bildirim gönderiliyor.")
                image_url = ""  # Boş string olarak ayarla

            fcm_token = self.user_data.get("fcmToken")
            if not fcm_token:
                logging.error("FCM bildirimi gönderilemedi: FCM token bulunamadı.")
                return False

            logging.debug(f"FCM token: {fcm_token}")

            # FCM bildirimi gönder
            message = messaging.Message(
                notification=messaging.Notification(
                    title='🚨 DÜŞME ALGILANDI!',
                    body=f'Düşme olayı tespit edildi. Olasılık: {confidence:.2f}',
                ),
                data={
                    'type': 'fall_detection',
                    'event_id': str(event_id),
                    'image_url': str(image_url),
                    'probability': str(confidence),
                },
                token=fcm_token,
            )

            # --- EK LOG ve HATA AYIKLAMA ---
            logging.info(f"FCM mesajı gönderiliyor... Token: {fcm_token}, event_id: {event_id}")

            response = messaging.send(message)
            self.channel_status["fcm"]["available"] = True
            self.channel_status["fcm"]["last_success"] = time.time()
            logging.info(f"FCM bildirimi başarıyla gönderildi! Yanıt: {response}")
            return True

        except Exception as e:
            self.channel_status["fcm"]["last_error"] = str(e)
            self.channel_status["fcm"]["available"] = False
            logging.error(f"FCM bildirimi gönderilirken hata: {str(e)}")
            return False

    def send_notifications(self, event_data, screenshot=None):
        """
        DÜZELTME: Asenkron bildirim sistemi - sistem donmasını önler
        Tüm bildirimler background thread'lerde çalışır.
        """
        try:
            # DÜZELTME: Hızlı validation - minimum CPU kullanımı
            if not self.user_data:
                logging.error("Kullanıcı verileri eksik - bildirim atlandı!")
                return False

            event_id = event_data.get('id', 'unknown')
            logging.info(f"🚀 Async notification started: {event_id}")
            
            # DÜZELTME: Background notification processing
            threading.Thread(target=self._async_notification_processing, 
                           args=(event_data.copy(), screenshot.copy() if screenshot is not None else None),
                           daemon=True).start()
            
            # DÜZELTME: Hemen True döndür - UI thread'i bloklamaz
            return True
            
        except Exception as e:
            logging.error(f"❌ Notification dispatch error: {e}")
            return False

    def _async_notification_processing(self, event_data, screenshot):
        """DÜZELTME: Asenkron bildirim işleme - UI thread'i bloklamaz."""
        try:
            event_id = event_data.get('id', 'unknown')
            logging.info(f"🔄 Async notification processing: {event_id}")
            
            # Aktif kanalları belirle
            active_channels = self._get_active_channels()
            
            if not active_channels:
                logging.warning(f"⚠️ No active channels for: {event_id}")
                return False

            # Her kanal için ayrı thread başlat
            notification_threads = []
            
            for channel in active_channels:
                thread = threading.Thread(
                    target=self._send_channel_notification,
                    args=(channel, event_data, screenshot),
                    daemon=True
                )
                thread.start()
                notification_threads.append(thread)
            
            # DÜZELTME: Thread'leri beklemez - hızlı response
            logging.info(f"✅ {len(notification_threads)} notification threads started for: {event_id}")
            
        except Exception as e:
            logging.error(f"❌ Async notification processing error: {e}")

    def _get_active_channels(self):
        """DÜZELTME: Hızlı kanal belirleme."""
        active_channels = []
        
        try:
            # FCM check
            if (self.user_data.get("fcm_notification", True) and 
                self.user_data.get("fcmToken")):
                active_channels.append("fcm")
            
            # Email check
            if (self.user_data.get("email_notification", True) and 
                (self.user_data.get("email") or os.getenv("SMTP_USER"))):
                active_channels.append("email")
            
            # SMS check
            if (self.user_data.get("sms_notification", False) and 
                self.user_data.get("settings", {}).get("phone_number")):
                active_channels.append("sms")
            
            # Telegram check
            if (self.user_data.get("telegram_notification", False) and 
                self.user_data.get("telegram_chat_id")):
                active_channels.append("telegram")
                
        except Exception as e:
            logging.error(f"❌ Channel detection error: {e}")
        
        return active_channels

    def _send_channel_notification(self, channel, event_data, screenshot):
        """DÜZELTME: Tek kanal için asenkron bildirim gönderimi."""
        try:
            event_id = event_data.get('id', 'unknown')
            start_time = time.time()
            
            notification = {
                "type": channel,
                "event_data": event_data,
                "screenshot": screenshot,
                "timestamp": time.time()
            }
            
            success = False
            
            # Kanal tipine göre gönder
            if channel == "fcm":
                success = self._send_fcm_notification(notification)
            elif channel == "email":
                success = self._send_email_notification(notification)
            elif channel == "sms":
                success = self._send_sms_notification(notification)
            elif channel == "telegram":
                success = self._send_telegram_notification(notification)
            
            processing_time = time.time() - start_time
            status = "✅ success" if success else "❌ failed"
            
            logging.info(f"{status} {channel} notification: {event_id} ({processing_time:.2f}s)")
            
        except Exception as e:
            logging.error(f"❌ {channel} notification error: {e}")

    def _send_email_notification(self, notification):
        """E-posta bildirimi kuyruğunu işler.
        
        Args:
            notification (dict): Bildirim verisi
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        event_data = notification.get("event_data", {})
        screenshot = notification.get("screenshot")
        
        # E-posta alıcısını belirle
        to_email = notification.get("to_email")
        if not to_email:
            to_email = self.user_data.get("email")
            if not to_email and "settings" in self.user_data:
                to_email = self.user_data["settings"].get("email")
            
            if not to_email:
                to_email = os.getenv("SMTP_USER")
                
        if not to_email:
            logging.error("E-posta bildirimi gönderilemedi: Alıcı e-posta adresi bulunamadı.")
            return False
            
        # E-posta gönder
        logging.info(f"E-posta bildirimi gönderiliyor: {to_email}")
        result = self.send_email(to_email, event_data, screenshot)
        
        if result:
            self.channel_status["email"]["last_success"] = time.time()
            logging.info(f"E-posta bildirimi başarıyla gönderildi: {to_email}")
        else:
            # E-posta gönderilemedi, alternatif kanala geç
            if self.channel_status["telegram"]["available"] and self.user_data.get("telegram_chat_id"):
                logging.info("E-posta gönderilemedi, Telegram'a geçiliyor...")
                self._send_telegram_notification({
                    "event_data": event_data,
                    "screenshot": screenshot,
                    "fallback": True
                })
                
        return result

    def _send_sms_notification(self, notification):
        """SMS bildirimi kuyruğunu işler.
        
        Args:
            notification (dict): Bildirim verisi
        """
        event_data = notification.get("event_data", {})
        phone_number = self.user_data.get("phone_number")
        
        if not phone_number:
            logging.error("SMS bildirimi gönderilemedi: Telefon numarası bulunamadı.")
            return
            
        # SMS gönder
        result = self.send_sms(phone_number, event_data)
        
        if result:
            self.channel_status["sms"]["last_success"] = time.time()
            logging.info(f"SMS bildirimi başarıyla gönderildi: {phone_number}")
        else:
            # SMS gönderilemedi, alternatif kanala geç
            if self.channel_status["email"]["available"] and self.user_data.get("email"):
                logging.info("SMS gönderilemedi, e-posta'ya geçiliyor...")
                self._send_email_notification({
                    "event_data": event_data,
                    "fallback": True
                })
    
    def _send_telegram_notification(self, notification):
        """Telegram bildirimi kuyruğunu işler.
        
        Args:
            notification (dict): Bildirim verisi
        """
        event_data = notification.get("event_data", {})
        screenshot = notification.get("screenshot")
        chat_id = self.user_data.get("telegram_chat_id")
        
        if not chat_id:
            logging.error("Telegram bildirimi gönderilemedi: Chat ID bulunamadı.")
            return
            
        # Telegram mesajı gönder
        result = self.send_telegram(chat_id, event_data, screenshot)
        
        if result:
            self.channel_status["telegram"]["last_success"] = time.time()
            logging.info(f"Telegram bildirimi başarıyla gönderildi: {chat_id}")
        else:
            # Telegram gönderilemedi, alternatif kanala geç
            is_fallback = notification.get("fallback", False)
            if not is_fallback and self.channel_status["email"]["available"] and \
               (self.user_data.get("email") or os.getenv("SMTP_USER")):
                logging.info("Telegram gönderilemedi, e-posta'ya geçiliyor...")
                self._send_email_notification({
                    "event_data": event_data,
                    "screenshot": screenshot,
                    "fallback": True
                })
    
    def send_email(self, to_email, event_data, screenshot=None):
        """E-posta bildirimi gönderir.
        
        Args:
            to_email (str): Alıcı e-posta adresi
            event_data (dict): Olay bilgileri
            screenshot (numpy.ndarray, optional): Olay anındaki ekran görüntüsü
        
        Returns:
            bool: Gönderim başarılı ise True, değilse False
        """
        try:
            # SMTP sunucu ayarları
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASS")
            
            if not (smtp_user and smtp_pass):
                logging.error("SMTP kimlik bilgileri ayarlanmamış.")
                return False
            
            # E-posta mesajı oluştur
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = EMAIL_SUBJECT
            
            # Timestamp veya şimdi
            timestamp = event_data.get("timestamp", time.time())
            if isinstance(timestamp, str):
                try:
                    timestamp = float(timestamp)
                except:
                    timestamp = time.time()
            
            # Tarih biçimlendirme
            date_time = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(timestamp))
            
            # Test bildirimi mi?
            is_test = event_data.get("test", False)
            test_label = "[TEST] " if is_test else ""
            
            # Olasılık değeri
            confidence = event_data.get("confidence", 0.0)
            if hasattr(confidence, "item"):  # NumPy değerlerini normal Python tiplerine dönüştür
                confidence = float(confidence)
            
            # Mesaj içeriği
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #d9534f;">{test_label}Guard Düşme Algılama Sistemi - UYARI!</h2>
                    <p>Merhaba,</p>
                    <p>Sistemimiz <strong>{date_time}</strong> tarihinde bir düşme algıladı.</p>
                    <p>Düşme olasılığı: <strong>%{confidence * 100:.2f}</strong></p>
                    <p style="background-color: #f2dede; padding: 10px; border-radius: 5px; border-left: 4px solid #d9534f;">
                        <strong>⚠️ Dikkat:</strong> Lütfen durumu kontrol edin ve gerekirse acil yardım çağırın.
                    </p>
                    <hr style="border: 1px solid #eee;">
                    <p style="font-size: 12px; color: #777;">
                        <i>Not: Bu e-posta otomatik olarak gönderilmiştir. Yanlış bildirim aldıysanız, 
                        lütfen Guard uygulamasındaki ayarlarınızı kontrol edin.</i>
                    </p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_content, 'html'))
            
            # Ekran görüntüsü varsa ekle
            if screenshot is not None:
                try:
                    import cv2
                    _, img_encoded = cv2.imencode('.jpg', screenshot)
                    img_bytes = img_encoded.tobytes()
                    
                    img_attachment = MIMEImage(img_bytes)
                    img_attachment.add_header('Content-Disposition', 'attachment', filename='fall_detected.jpg')
                    msg.attach(img_attachment)
                except Exception as e:
                    logging.warning(f"Ekran görüntüsü e-postaya eklenirken hata: {str(e)}")
            
            # E-postayı gönder
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            self.channel_status["email"]["last_error"] = str(e)
            self.channel_status["email"]["available"] = False
            logging.error(f"E-posta gönderilirken hata oluştu: {str(e)}")
            return False
    
    def send_sms(self, phone_number, event_data):
        """SMS bildirimi gönderir.
        
        Args:
            phone_number (str): Alıcı telefon numarası
            event_data (dict): Olay bilgileri
            
        Returns:
            bool: Gönderim başarılı ise True, değilse False
        """
        try:
            # SMS API ayarları (örnek olarak Twilio)
            twilio_sid = os.getenv("TWILIO_SID")
            twilio_token = os.getenv("TWILIO_TOKEN")
            twilio_from = os.getenv("TWILIO_PHONE")
            
            if not (twilio_sid and twilio_token and twilio_from):
                logging.error("Twilio kimlik bilgileri ayarlanmamış.")
                return False
            
            # Test bildirimi mi?
            is_test = event_data.get("test", False)
            test_label = "[TEST] " if is_test else ""
            
            # Olasılık değeri
            confidence = event_data.get("confidence", 0.0)
            if hasattr(confidence, "item"):
                confidence = float(confidence)
            
            # Mesaj içeriği - kısa ve net ol
            message = f"{test_label}{SMS_MESSAGE} Düşme olasılığı: %{confidence * 100:.0f}"
            
            # SMS gönder
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            data = {
                "From": twilio_from,
                "To": phone_number,
                "Body": message
            }
            
            response = requests.post(
                url,
                data=data,
                auth=(twilio_sid, twilio_token)
            )
            
            if response.status_code == 201:
                return True
            else:
                self.channel_status["sms"]["last_error"] = f"HTTP {response.status_code}: {response.text}"
                logging.error(f"SMS gönderilemedi. Durum kodu: {response.status_code}, Yanıt: {response.text}")
                return False
            
        except Exception as e:
            self.channel_status["sms"]["last_error"] = str(e)
            self.channel_status["sms"]["available"] = False
            logging.error(f"SMS gönderilirken hata oluştu: {str(e)}")
            return False
    
    def send_telegram(self, chat_id, event_data, screenshot=None):
        """Telegram bildirimi gönderir.
        
        Args:
            chat_id (str): Alıcı Telegram sohbet ID'si
            event_data (dict): Olay bilgileri
            screenshot (numpy.ndarray, optional): Olay anındaki ekran görüntüsü
            
        Returns:
            bool: Gönderim başarılı ise True, değilse False
        """
        try:
            if not self.telegram_bot:
                logging.error("Telegram botu başlatılmamış.")
                return False
            
            # Test bildirimi mi?
            is_test = event_data.get("test", False)
            test_label = "[TEST] " if is_test else ""
            
            # Olasılık değeri
            confidence = event_data.get("confidence", 0.0)
            if hasattr(confidence, "item"):
                confidence = float(confidence)
            
            # Zaman damgası
            timestamp = event_data.get("timestamp", time.time())
            if isinstance(timestamp, str):
                try:
                    timestamp = float(timestamp)
                except:
                    timestamp = time.time()
            
            # Tarih biçimlendirme
            date_time = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(timestamp))
            
            # Mesaj içeriği - Markdown formatında
            message = f"{test_label}*GUARD DÜŞME ALGILAMA UYARISI!*\n\n" \
                     f"⏰ *Zaman:* {date_time}\n" \
                     f"📊 *Düşme Olasılığı:* %{confidence * 100:.2f}\n\n" \
                     f"⚠️ Lütfen durumu kontrol edin ve gerekirse acil yardım çağırın."
            
            # Mesajı gönder
            self.telegram_bot.sendMessage(chat_id, message, parse_mode="Markdown")
            
            # Ekran görüntüsü varsa gönder
            if screenshot is not None:
                try:
                    import cv2
                    import io
                    
                    # Ekran görüntüsüne zaman damgası ekle
                    img_with_timestamp = screenshot.copy()
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.putText(
                        img_with_timestamp, 
                        date_time, 
                        (10, 30), 
                        font, 
                        0.7, 
                        (255, 255, 255), 
                        2, 
                        cv2.LINE_AA
                    )
                    
                    _, img_encoded = cv2.imencode('.jpg', img_with_timestamp)
                    img_bytes = io.BytesIO(img_encoded.tobytes())
                    img_bytes.name = 'fall_detected.jpg'
                    
                    self.telegram_bot.sendPhoto(chat_id, img_bytes)
                except Exception as e:
                    logging.warning(f"Ekran görüntüsü Telegram'a gönderilirken hata: {str(e)}")
            
            return True
            
        except Exception as e:
            self.channel_status["telegram"]["last_error"] = str(e)
            self.channel_status["telegram"]["available"] = False
            logging.error(f"Telegram bildirimi gönderilirken hata oluştu: {str(e)}")
            return False
    
    def get_notification_status(self):
        """Bildirim kanallarının durumunu döndürür."""
        return {
            "channels": self.channel_status,
            "queue_size": self.notification_queue.qsize(),
            "user_preferences": {
                "email": self.user_data.get("email_notification", True),
                "sms": self.user_data.get("sms_notification", False),
                "telegram": self.user_data.get("telegram_notification", False)
            }
        }
    
    def _record_notification_status(self, event_id, channels):
        """Bildirim durumunu veritabanına kaydeder (istatistik için).
        
        Args:
            event_id (str): Olay ID'si
            channels (list): Kullanılan bildirim kanalları
        """
        try:
            if not event_id:
                return
            
            # Bildirim kanallarını dizge olarak birleştir
            channels_str = ", ".join(channels)
            
            # Bildirimin gönderildiği zamanı al
            timestamp = time.time()
            
            # Bildirim verilerini oluştur
            notification_data = {
                "event_id": event_id,
                "channels": channels,
                "channels_str": channels_str,  # Firestore sorgularında kolaylık için
                "timestamp": timestamp,
                "status": "sent"  # Durumu 'sent' olarak işaretliyoruz
            }
            
            # Kullanıcı verilerine erişmek için
            user_id = None
            if self.user_data and "localId" in self.user_data:
                user_id = self.user_data["localId"]
            elif self.user_data and "user_id" in self.user_data:
                user_id = self.user_data["user_id"]
            
            # Kullanıcı ID'si yoksa kayıt yapma
            if not user_id:
                return
            
            # Veritabanı referansı
            from firebase_admin import firestore
            db = firestore.client()
            
            # Bildirim kaydını ekle
            notification_ref = db.collection(f"users/{user_id}/notifications").document()
            notification_ref.set(notification_data)
            
            # Ayrıca olay kaydına da bildirim bilgisini ekle
            import datetime
            date_string = datetime.datetime.fromtimestamp(timestamp).strftime("%Y%m")
            event_ref = db.collection(f"users/{user_id}/events/{date_string}/falls").document(event_id)
            
            # Notification_sent alanını güncelle
            event_ref.update({
                "notification_sent": True,
                "notification_channels": channels,
                "notification_time": timestamp
            })
            
            logging.info(f"Bildirim durumu kaydedildi: {event_id}, kanallar: {channels_str}")
            
        except Exception as e:
            logging.error(f"Bildirim durumu kaydedilirken hata: {str(e)}")