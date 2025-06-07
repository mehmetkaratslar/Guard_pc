# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: database.py (FIRESTORE VE YEREL DEPOLAMA YÖNETİMİ)
# Konum: guard_pc_app/data/database.py
# Açıklama:
# Uygulamanın veritabanı işlemlerini yöneten FirestoreManager sınıfını içerir.
# Kullanıcı ayarlarını, düşme olaylarını hem yerel olarak hem de Firebase Firestore üzerinde saklar.
#
# Sistem çevrimdışıyken bile kullanıcı verilerini yönetmeye olanak sağlar.
# Gerçek zamanlı senkronizasyon ile birden fazla cihaz arasında uyum sağlar.

# === ÖZELLİKLER ===
# - Firebase Firestore bağlantısı
# - Yerel JSON tabanlı veri yedekleme desteği
# - Kullanıcı oluşturma ve ayarları yönetme
# - Düşme olaylarını kaydetme/silme
# - Bağlantı kontrolü (çevrimdışı/çevrimiçi durumu)

# === BAŞLICA MODÜLLER VE KULLANIM AMACI ===
# - logging: Hata ve işlem kayıtları tutma
# - firebase_admin.firestore: Firebase Firestore erişimi
# - datetime / time: Zaman damgası üretimi
# - uuid: Olay ID'leri üretmek
# - os / json: Yerel JSON dosya yönetimi

# === SINIFLAR ===
# - FirestoreManager: Firestore ve yerel depolama işlemleri için ana sınıf

# === TEMEL FONKSİYONLAR ===
# - __init__: Firebase Admin SDK'yı başlatır, Firestore bağlantısını kurar
# - get_fall_events: Belirli bir kullanıcının düşme olaylarını çeker
# - create_new_user: Yeni kullanıcı oluşturur ve varsayılan ayarları atar
# - save_user_settings: Kullanıcı ayarlarını yerel ve/veya uzak veritabanında günceller
# - delete_fall_event: Belirli bir düşme olayını siler
# - test_connection: Firestore bağlantısını test eder

# === VERİ DEPOLAMA MEKANİZMALARI ===
# 1. FIRESTORE:
#    - Ana veritabanı olarak kullanılır
#    - Gerçek zamanlı senkronizasyon
#    - Çoklu cihaz desteği
#    - Güvenli kullanıcı kimliği ile erişim
# 2. YEREL DEPOLAMA:
#    - JSON formatında saklanır
#    - Offline modda kullanılabilir
#    - Otomatik yedekleme mekanizması

# === VERİ YAPILARI ===
# Kullanıcı Verisi:
# {
#     "id": "user123",
#     "created_at": 1712345678,
#     "last_login": 1712345678,
#     "settings": {
#         "email_notification": True,
#         "sms_notification": False,
#         ...
#     }
# }

# Düşme Olayı:
# {
#     "id": "event123",
#     "timestamp": 1712345678,
#     "camera_id": "cam1",
#     "confidence": 0.95,
#     "image_url": "https://firebasestorage.googleapis.com/..." 
# }

# === YEREL DEPOLAMA DOSYA YAPISI ===
# - /users/{user_id}/settings.json: Kullanıcı ayarları
# - /users/{user_id}/events/: Düşme olayları klasörü
# - /users/{user_id}/fall_events.json: Tüm düşme olaylarının listesi

# === FIRESTORE VERİTABANI YAPISI ===
# Koleksiyonlar:
# - users: Kullanıcı bilgileri
# - fall_events: Düşme olayları koleksiyonu
# - settings: Kullanıcı ayarları alt koleksiyonu

# === ÇEVRİMDIŞI DESTEK ===
# - Eğer internet yoksa yerel JSON dosyasına yazma yapılır
# - İnternet tekrar bağlandığında yerel veriler Firestore'a senkronize edilir

# === HATA YÖNETİMİ ===
# - Tüm işlemlerde try-except bloklarıyla hatalar loglanır
# - Kullanıcıya anlamlı mesajlar gösterilir
# - Bağlantı hatası durumunda uyarı verilir

# === LOGGING ===
# - Tüm işlemler log dosyasına yazılır (guard_ai_v3.log)
# - Log formatı: Tarih/Zaman [Seviye] Mesaj

# === TEST AMAÇLI KULLANIM ===
# - `if __name__ == "__main__":` bloğu ile bağımsız çalıştırılabilir
# - Mock DB veya test ortamı ile çalıştırılabilir

# === NOTLAR ===
# - Bu dosya, app.py ve dashboard.py ile entegre çalışır
# - Firebase kimlik doğrulaması zorunludur
# - Yerel depolama sadece geçici çözümler içindir
# =======================================================================================


import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import types

class FirestoreManager:
    """🔥 Gelişmiş Firestore Veritabanı Yöneticisi - Tam Özellikli"""

    def __init__(self):
        """Firestore bağlantısını başlatır."""
        self.db = None
        self.bucket = None
        
        # 🆕 MEMORY STORAGE - Kullanıcı verisi kalıcılığı için
        self._memory_storage = {}
        self._user_cache = {}
        self._settings_cache = {}
        
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Firebase'i başlatır."""
        try:
            if not firebase_admin._apps:
                # Firebase config - gerçek config ile değiştirin
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": "guard-12345",
                    "private_key_id": "your_private_key_id",
                    "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
                    "client_email": "firebase-adminsdk-xyz@guard-12345.iam.gserviceaccount.com",
                    "client_id": "your_client_id",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xyz%40guard-12345.iam.gserviceaccount.com"
                })
                
                firebase_admin.initialize_app(cred, {
                    'storageBucket': 'guard-12345.firebasestorage.app'
                })
            
            self.db = firestore.client()
            self.bucket = storage.bucket()
            logging.info("✅ Firebase başlatıldı")
            
        except Exception as e:
            logging.error(f"❌ Firebase başlatma hatası: {e}")
            self.db = None
            self.bucket = None

    # 🔧 SAFE CONVERSION METHODS
    def _safe_timestamp_convert(self, timestamp_value):
        """🔧 Güvenli timestamp dönüştürme"""
        try:
            if timestamp_value is None:
                return time.time()
            
            if hasattr(timestamp_value, 'timestamp'):
                return timestamp_value.timestamp()
            elif isinstance(timestamp_value, datetime):
                return timestamp_value.timestamp()
            elif hasattr(timestamp_value, 'seconds'):
                return float(timestamp_value.seconds) + float(timestamp_value.nanoseconds) / 1e9
            elif isinstance(timestamp_value, str):
                try:
                    dt = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                    return dt.timestamp()
                except:
                    return float(timestamp_value)
            elif isinstance(timestamp_value, (int, float)):
                return float(timestamp_value)
            else:
                logging.warning(f"⚠️ Bilinmeyen timestamp formatı: {type(timestamp_value)}")
                return time.time()
                
        except Exception as e:
            logging.error(f"❌ Timestamp dönüştürme hatası: {e}")
            return time.time()

    # 🆕 NEW USER METHODS
    def create_new_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """🆕 Yeni kullanıcı oluşturur"""
        try:
            if not user_id:
                logging.error("❌ User ID boş olamaz")
                return False
            
            default_user_data = {
                'user_id': user_id,
                'email': user_data.get('email', ''),
                'displayName': user_data.get('displayName', user_data.get('email', '').split('@')[0]),
                'photoURL': user_data.get('photoURL', ''),
                'emailVerified': user_data.get('emailVerified', False),
                'phoneNumber': user_data.get('phoneNumber', ''),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'last_login': firestore.SERVER_TIMESTAMP,
                'login_count': 1,
                'provider': user_data.get('provider', 'email'),
                
                'settings': {
                    'email_notification': True,
                    'fcm_notification': True,
                    'sms_notification': False,
                    'phone_number': '',
                    'dark_mode': True,
                    'auto_brightness': True,
                    'brightness_adjustment': 0,
                    'contrast_adjustment': 1.0,
                    'fall_sensitivity': 'medium',
                    'selected_ai_model': 'yolo11n-pose',
                    'language': 'tr',
                    'timezone': 'Europe/Istanbul'
                },
                
                'profile': {
                    'age': user_data.get('age'),
                    'gender': user_data.get('gender'),
                    'emergency_contacts': [],
                    'medical_conditions': [],
                    'preferences': {}
                },
                
                'system': {
                    'app_version': '1.0.0',
                    'platform': 'Windows',
                    'device_info': {},
                    'last_sync': firestore.SERVER_TIMESTAMP
                }
            }
            
            final_user_data = {**default_user_data, **user_data}
            
            # Memory cache'e kaydet
            self._user_cache[user_id] = final_user_data.copy()
            self._settings_cache[user_id] = final_user_data['settings'].copy()
            self._memory_storage[f"user_{user_id}"] = final_user_data.copy()
            self._memory_storage[f"settings_{user_id}"] = final_user_data['settings'].copy()
            
            if not self.db:
                logging.warning("⚠️ Firestore bağlantısı yok, sadece yerel cache'e kaydedildi")
                return True
            
            user_ref = self.db.collection('users').document(user_id)
            user_ref.set(final_user_data)
            
            logging.info(f"✅ Yeni kullanıcı oluşturuldu: {user_id} - {final_user_data.get('email', '')}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Yeni kullanıcı oluşturma hatası: {e}")
            return False

    def check_user_exists(self, user_id: str) -> bool:
        """🔍 Kullanıcının var olup olmadığını kontrol eder"""
        try:
            if user_id in self._user_cache:
                return True
            
            if not self.db:
                return f"user_{user_id}" in self._memory_storage
            
            user_ref = self.db.collection('users').document(user_id)
            doc = user_ref.get()
            
            exists = doc.exists
            logging.info(f"🔍 Kullanıcı kontrol: {user_id} - {'Var' if exists else 'Yok'}")
            return exists
            
        except Exception as e:
            logging.error(f"❌ Kullanıcı kontrol hatası: {e}")
            return False

    def update_login_count(self, user_id: str) -> bool:
        """📊 Kullanıcı giriş sayısını günceller"""
        try:
            if not self.db:
                if user_id in self._user_cache:
                    current_count = self._user_cache[user_id].get('login_count', 0)
                    self._user_cache[user_id]['login_count'] = current_count + 1
                    self._memory_storage[f"user_{user_id}"] = self._user_cache[user_id].copy()
                return True
            
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                'login_count': firestore.Increment(1),
                'last_login': firestore.SERVER_TIMESTAMP,
                'last_login_timestamp': time.time()
            })
            
            logging.info(f"✅ Giriş sayısı güncellendi: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Giriş sayısı güncelleme hatası: {e}")
            return False

    # 🔧 EXISTING METHODS - UPDATED
    def update_user_data(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """🔧 Kullanıcı verilerini günceller"""
        try:
            if user_id not in self._user_cache:
                self._user_cache[user_id] = {}
            
            self._user_cache[user_id].update(user_data)
            self._memory_storage[f"user_{user_id}"] = self._user_cache[user_id].copy()
            
            if not self.db:
                logging.warning("⚠️ Firestore bağlantısı yok, sadece yerel cache güncellendi")
                return True
            
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                **user_data,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logging.info(f"✅ Kullanıcı verileri güncellendi: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Kullanıcı güncelleme hatası: {e}")
            return False

    def save_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """🔧 Kullanıcı ayarlarını kaydeder"""
        try:
            self._settings_cache[user_id] = settings.copy()
            self._memory_storage[f"settings_{user_id}"] = settings.copy()
            
            if not self.db:
                logging.warning("⚠️ Firestore bağlantısı yok, sadece yerel cache güncellendi")
                return True
            
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                'settings': settings,
                'settings_updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logging.info(f"✅ Kullanıcı ayarları güncellendi: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Ayar kaydetme hatası: {e}")
            return False

    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """🔧 Kullanıcı verilerini alır"""
        try:
            if user_id in self._user_cache:
                cached_data = self._user_cache[user_id].copy()
                if user_id in self._settings_cache:
                    cached_data['settings'] = self._settings_cache[user_id]
                return cached_data
            
            if not self.db:
                user_data = self._memory_storage.get(f"user_{user_id}")
                settings_data = self._memory_storage.get(f"settings_{user_id}")
                
                if user_data:
                    if settings_data:
                        user_data['settings'] = settings_data
                    return user_data
                return None
            
            user_ref = self.db.collection('users').document(user_id)
            doc = user_ref.get()
            
            if doc.exists:
                user_data = doc.to_dict()
                
                self._user_cache[user_id] = user_data.copy()
                if 'settings' in user_data:
                    self._settings_cache[user_id] = user_data['settings']
                
                logging.info(f"✅ Firestore'dan kullanıcı verisi alındı: {user_id}")
                return user_data
            else:
                logging.warning(f"⚠️ Kullanıcı verisi bulunamadı: {user_id}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Kullanıcı verisi alma hatası: {e}")
            return self._user_cache.get(user_id)

    def get_fall_events(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """🔧 Düşme olaylarını alır"""
        try:
            if not self.db:
                logging.warning("⚠️ Firestore bağlantısı yok, boş liste döndürülüyor")
                return []
            
            events_ref = self.db.collection('fall_events').where('user_id', '==', user_id)
            events_query = events_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            
            events = []
            docs = events_query.stream()
            
            for doc in docs:
                try:
                    event_data = doc.to_dict()
                    event_data['id'] = doc.id
                    
                    if 'timestamp' in event_data:
                        event_data['timestamp'] = self._safe_timestamp_convert(event_data['timestamp'])
                    
                    if 'confidence' in event_data:
                        try:
                            event_data['confidence'] = float(event_data['confidence'])
                        except (ValueError, TypeError):
                            event_data['confidence'] = 0.0
                    
                    for field in ['track_id']:
                        if field in event_data and event_data[field] is not None:
                            try:
                                event_data[field] = int(event_data[field])
                            except (ValueError, TypeError):
                                event_data[field] = 0
                    
                    events.append(event_data)
                    
                except Exception as e:
                    logging.error(f"❌ Event parsing hatası: {e} - Event: {doc.id}")
                    continue
            
            logging.info(f"✅ Firestore'dan {len(events)} düşme olayı getirildi")
            return events
            
        except Exception as e:
            logging.error(f"❌ Düşme olayları alma hatası: {e}")
            return []

    def delete_fall_event(self, user_id: str, event_id: str) -> bool:
        """🗑️ Düşme olayını siler"""
        try:
            if not self.db:
                return False
            
            event_ref = self.db.collection('fall_events').document(event_id)
            event_doc = event_ref.get()
            
            if not event_doc.exists:
                logging.warning(f"⚠️ Silinecek event bulunamadı: {event_id}")
                return False
            
            event_data = event_doc.to_dict()
            if event_data.get('user_id') != user_id:
                logging.warning(f"⚠️ Event kullanıcıya ait değil: {event_id}")
                return False
            
            event_ref.delete()
            
            if 'image_url' in event_data:
                try:
                    self._delete_image_from_storage(event_data['image_url'])
                except Exception as e:
                    logging.warning(f"⚠️ Resim silme hatası: {e}")
            
            logging.info(f"✅ Event silindi: {event_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Event silme hatası: {e}")
            return False

    def update_last_login(self, user_id: str) -> bool:
        """⏰ Son giriş zamanını günceller"""
        try:
            login_time = time.time()
            self._memory_storage[f"last_login_{user_id}"] = login_time
            
            if not self.db:
                logging.warning("⚠️ Firestore bağlantısı yok, sadece yerel cache güncellendi")
                return True
            
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                'last_login': firestore.SERVER_TIMESTAMP,
                'last_login_timestamp': login_time
            })
            
            logging.info(f"✅ Son giriş zamanı Firestore'da güncellendi: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Son giriş güncelleme hatası: {e}")
            return False

    def clear_user_cache(self, user_id: str = None):
        """🧹 Kullanıcı cache'ini temizler"""
        try:
            if user_id:
                self._user_cache.pop(user_id, None)
                self._settings_cache.pop(user_id, None)
                
                keys_to_remove = [key for key in self._memory_storage.keys() if user_id in key]
                for key in keys_to_remove:
                    self._memory_storage.pop(key, None)
                    
                logging.info(f"✅ Kullanıcı cache temizlendi: {user_id}")
            else:
                self._user_cache.clear()
                self._settings_cache.clear()
                self._memory_storage.clear()
                logging.info("✅ Tüm cache temizlendi")
                
        except Exception as e:
            logging.error(f"❌ Cache temizleme hatası: {e}")

    def _delete_image_from_storage(self, image_url: str):
        """🗑️ Storage'dan resmi siler"""
        try:
            if not self.bucket or not image_url:
                return
            
            if 'firebasestorage.googleapis.com' in image_url:
                import urllib.parse
                parsed = urllib.parse.urlparse(image_url)
                path_parts = parsed.path.split('/')
                
                if len(path_parts) >= 4 and path_parts[2] == 'o':
                    blob_path = urllib.parse.unquote(path_parts[3])
                    blob = self.bucket.blob(blob_path)
                    blob.delete()
                    logging.info(f"✅ Storage'dan resim silindi: {blob_path}")
            
        except Exception as e:
            logging.error(f"❌ Storage resim silme hatası: {e}")

# Singleton instance
_firestore_manager_instance = None

def get_firestore_manager():
    """Singleton FirestoreManager instance döndürür."""
    global _firestore_manager_instance
    if _firestore_manager_instance is None:
        _firestore_manager_instance = FirestoreManager()
    return _firestore_manager_instance