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

import logging
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import time
import uuid
import os
import json

class FirestoreManager:
    """Firestore veritabanı işlemlerini yöneten sınıf."""
    
    def __init__(self, db=None):
        """
        Args:
            db (google.cloud.firestore.Client, optional): Firestore client nesnesi
        """
        self._memory_storage = {
            "users": {}
        }  # Memory storage başta tanımlanıyor
        
        try:
            self.db = db or firestore.client()
            self.is_available = True
            logging.info("Firestore bağlantısı başarılı.")
        except Exception as e:
            logging.warning(f"Firestore başlatılamadı: {str(e)}")
            logging.info("Yerel dosya tabanlı veri saklama kullanılacak.")
            self.is_available = False
            self._load_local_data()

    def _get_local_data_path(self):
        """Yerel veri dosyasının yolunu döndürür."""
        data_dir = os.path.join(os.path.dirname(__file__), "local_data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "local_db.json")
    
    def _load_local_data(self):
        """Yerel veri dosyasından verileri yükler."""
        try:
            file_path = self._get_local_data_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._memory_storage = data
                    logging.info(f"Yerel veri dosyası yüklendi: {file_path}")
            else:
                logging.info("Yerel veri dosyası bulunamadı, yeni dosya oluşturulacak.")
                self._save_local_data()
        except Exception as e:
            logging.error(f"Yerel veri yüklenirken hata: {str(e)}")
            # Boş veri ile devam et
            self._memory_storage = {"users": {}}
    
    def _save_local_data(self):
        """Verileri yerel dosyaya kaydeder."""
        try:
            file_path = self._get_local_data_path()
            # Geçici dosyaya yaz, sonra taşı (atomic operation)
            temp_path = file_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._memory_storage, f, indent=2, ensure_ascii=False)
            
            # Geçici dosyayı asıl dosyaya taşı
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(temp_path, file_path)
            
            logging.info(f"Veriler yerel dosyaya kaydedildi: {file_path}")
        except Exception as e:
            logging.error(f"Veriler yerel dosyaya kaydedilirken hata: {str(e)}")

    def get_user_data(self, user_id):
        """Kullanıcı verilerini getirir."""
        if not user_id:
            logging.warning("get_user_data: user_id boş")
            return None
            
        if not self.is_available:
            user_data = self._memory_storage["users"].get(user_id, None)
            logging.info(f"Yerel depodan kullanıcı verisi alındı: {user_id}")
            return user_data
        
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                data = user_doc.to_dict()
                logging.info(f"Firestore'dan kullanıcı verisi alındı: {user_id}")
                return data
            else:
                logging.warning(f"Kullanıcı bulunamadı: {user_id}")
                return None
        except Exception as e:
            logging.error(f"Kullanıcı verileri getirilirken hata: {str(e)}")
            # Firestore hatası durumunda yerel depolamayı dene
            if hasattr(self, '_memory_storage'):
                return self._memory_storage["users"].get(user_id, None)
            return None

    def save_user_settings(self, user_id, settings):
        """Kullanıcı ayarlarını kaydeder."""
        if not user_id:
            logging.error("save_user_settings: user_id boş")
            return False
            
        if not settings:
            logging.error("save_user_settings: settings boş")
            return False
        
        # Yerel depolamaya her durumda kaydet (backup)
        try:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            if "settings" not in self._memory_storage["users"][user_id]:
                self._memory_storage["users"][user_id]["settings"] = {}
            
            self._memory_storage["users"][user_id]["settings"].update(settings)
            self._memory_storage["users"][user_id]["updated_at"] = time.time()
            self._save_local_data()
            logging.info(f"Kullanıcı ayarları yerel depoya kaydedildi: {user_id}")
        except Exception as e:
            logging.error(f"Yerel ayar kaydetme hatası: {e}")
        
        if not self.is_available:
            return True  # Yerel kayıt başarılı
        
        try:
            user_ref = self.db.collection("users").document(user_id)
            
            # Mevcut kullanıcı verisini al
            user_doc = user_ref.get()
            if user_doc.exists:
                # Mevcut ayarları güncelle
                current_data = user_doc.to_dict()
                current_settings = current_data.get("settings", {})
                current_settings.update(settings)
                
                update_data = {
                    "settings": current_settings,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
                user_ref.update(update_data)
            else:
                # Yeni kullanıcı oluştur
                new_data = {
                    "id": user_id,
                    "settings": settings,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
                user_ref.set(new_data)
            
            logging.info(f"Kullanıcı ayarları Firestore'a güncellendi: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Kullanıcı ayarları Firestore'a kaydedilirken hata: {str(e)}")
            return True  # Yerel kayıt başarılı olduğu için True döndür
    
    def save_fall_event(self, event_data):
        """
        Düşme olayını /fall_events/{eventId} yoluna kaydeder.

        Args:
            event_data (dict): Kaydedilecek olay verileri (id, user_id, image_url, vb.)

        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            # ID'nin olduğundan emin ol
            if "id" not in event_data:
                event_data["id"] = str(uuid.uuid4())
            
            # Zaman damgasının olduğundan emin ol
            if "timestamp" not in event_data:
                event_data["timestamp"] = time.time()
            
            # Oluşturulma zamanını ekle
            if "created_at" not in event_data:
                event_data["created_at"] = time.time()
            
            event_id = event_data["id"]
            user_id = event_data.get("user_id", "unknown")
            logging.info(f"Düşme olayı kaydediliyor: {event_id} - Kullanıcı: {user_id}")
            
            # Firestore uyumlu veri oluştur
            cleaned_data = {}
            for key, value in event_data.items():
                if key == "model_info":
                    # model_info'yu string'e çevir
                    cleaned_data[key] = str(value)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    cleaned_data[key] = value
                else:
                    # Diğer karmaşık nesneleri string'e çevir
                    cleaned_data[key] = str(value)
            
            if not self.is_available:
                # Yerel depolamada /users/{user_id}/events ve /users/{user_id}/fall_events'e kaydet
                if user_id not in self._memory_storage["users"]:
                    self._memory_storage["users"][user_id] = {"id": user_id}
                
                for collection_name in ["events", "fall_events"]:
                    if collection_name not in self._memory_storage["users"][user_id]:
                        self._memory_storage["users"][user_id][collection_name] = []
                    self._memory_storage["users"][user_id][collection_name].append(cleaned_data)
                
                self._save_local_data()
                logging.info(f"Düşme olayı yerel depoya kaydedildi: {event_id}")
                return True
            
            # Firestore'a /fall_events/{eventId} yoluna kaydet
            doc_ref = self.db.collection("fall_events").document(event_id)
            doc_ref.set(cleaned_data)
            logging.info(f"Düşme olayı Firestore'a kaydedildi: /fall_events/{event_id}")
            return True
            
        except Exception as e:
            logging.error(f"Düşme olayı kaydedilirken hata: {str(e)}")
            return False

    def get_fall_events(self, user_id, limit=50):
        """
        Kullanıcının düşme olaylarını getirir.
        Firestore'da /fall_events/'ten, yerel depoda /users/{user_id}/events ve /users/{user_id}/fall_events'ten çeker.
        """
        if not user_id:
            logging.warning("get_fall_events: user_id boş")
            return []
            
        logging.info(f"Düşme olayları getiriliyor - Kullanıcı: {user_id}, Limit: {limit}")
        
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                logging.warning(f"Kullanıcı bellekte bulunamadı: {user_id}")
                return []
            
            events = self._memory_storage["users"][user_id].get("events", [])
            if not events:
                events = self._memory_storage["users"][user_id].get("fall_events", [])
            
            sorted_events = sorted(
                events, 
                key=lambda e: e.get("timestamp", e.get("created_at", 0)), 
                reverse=True
            )
            logging.info(f"Yerel depodan {len(sorted_events[:limit])} düşme olayı getirildi")
            return sorted_events[:limit]
            
        try:
            query = self.db.collection("fall_events")\
                .where("user_id", "==", user_id)\
                .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                .limit(limit)
            
            events = []
            for doc in query.stream():
                event_data = doc.to_dict()
                if "id" not in event_data:
                    event_data["id"] = doc.id
                events.append(event_data)
            
            logging.info(f"Firestore'dan {len(events)} düşme olayı getirildi")
            return events
            
        except Exception as e:
            logging.error(f"Düşme olayları getirilirken hata: {str(e)}")
            return []
    
    def create_new_user(self, user_id, user_data):
        """Yeni kullanıcı oluşturur."""
        if not user_id:
            logging.error("create_new_user: user_id boş")
            return False
            
        base_data = {
            "id": user_id,
            "created_at": time.time(),
            "last_login": time.time(),
            "settings": {
                "email_notification": True,
                "sms_notification": False,
                "fcm_notification": True,
                "phone_number": "",
                "dark_mode": False,
                "auto_brightness": True,
                "brightness_adjustment": 0,
                "contrast_adjustment": 1.0,
                "fall_sensitivity": "medium",
                "selected_ai_model": "yolo11l-pose"
            }
        }
        final_data = {**base_data, **user_data}
        
        # Yerel depolamaya kaydet
        try:
            self._memory_storage["users"][user_id] = final_data
            self._save_local_data()
            logging.info(f"Yeni kullanıcı yerel depoya kaydedildi: {user_id}")
        except Exception as e:
            logging.error(f"Yerel kullanıcı kaydetme hatası: {e}")
        
        if not self.is_available:
            return True
            
        try:
            user_ref = self.db.collection("users").document(user_id)
            final_data["created_at"] = firestore.SERVER_TIMESTAMP
            final_data["last_login"] = firestore.SERVER_TIMESTAMP
            user_ref.set(final_data)
            logging.info(f"Yeni kullanıcı Firestore'a oluşturuldu: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Kullanıcı Firestore'a oluşturulurken hata: {str(e)}")
            return True  # Yerel kayıt başarılı
    
    def update_last_login(self, user_id):
        """Kullanıcının son giriş zamanını günceller."""
        if not user_id:
            logging.error("update_last_login: user_id boş")
            return False
            
        # Yerel depolamayı güncelle
        try:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            self._memory_storage["users"][user_id]["last_login"] = time.time()
            self._save_local_data()
            logging.info(f"Son giriş zamanı yerel depoda güncellendi: {user_id}")
        except Exception as e:
            logging.error(f"Yerel son giriş güncelleme hatası: {e}")
        
        if not self.is_available:
            return True
            
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.update({"last_login": firestore.SERVER_TIMESTAMP})
            logging.info(f"Son giriş zamanı Firestore'da güncellendi: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Son giriş zamanı güncellenirken hata: {str(e)}")
            return True  # Yerel güncelleme başarılı
    
    def update_user_data(self, user_id, user_data):
        """Kullanıcı bilgilerini günceller."""
        if not user_id:
            logging.error("update_user_data: user_id boş")
            return False
            
        if not user_data:
            logging.error("update_user_data: user_data boş")
            return False
        
        # Yerel depolamayı güncelle
        try:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            self._memory_storage["users"][user_id].update(user_data)
            self._memory_storage["users"][user_id]["updated_at"] = time.time()
            self._save_local_data()
            logging.info(f"Kullanıcı verileri yerel depoda güncellendi: {user_id}")
        except Exception as e:
            logging.error(f"Yerel kullanıcı güncelleme hatası: {e}")
        
        if not self.is_available:
            return True
            
        try:
            user_ref = self.db.collection("users").document(user_id)
            update_data = user_data.copy()
            update_data["updated_at"] = firestore.SERVER_TIMESTAMP
            user_ref.update(update_data)
            logging.info(f"Kullanıcı verileri Firestore'da güncellendi: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Kullanıcı verileri güncellenirken hata: {str(e)}")
            return True  # Yerel güncelleme başarılı
    
    def delete_fall_event(self, user_id, event_id):
        """Düşme olayını siler."""
        if not user_id or not event_id:
            logging.error("delete_fall_event: user_id veya event_id boş")
            return False
            
        # Yerel depolamadan sil
        try:
            if user_id in self._memory_storage["users"]:
                for collection_name in ["events", "fall_events"]:
                    if collection_name in self._memory_storage["users"][user_id]:
                        events = self._memory_storage["users"][user_id][collection_name]
                        self._memory_storage["users"][user_id][collection_name] = [
                            e for e in events if e.get("id") != event_id
                        ]
                self._save_local_data()
                logging.info(f"Düşme olayı yerel depodan silindi: {event_id}")
        except Exception as e:
            logging.error(f"Yerel olay silme hatası: {e}")
        
        if not self.is_available:
            return True
            
        try:
            doc_ref = self.db.collection("fall_events").document(event_id)
            doc_ref.delete()
            logging.info(f"Düşme olayı Firestore'dan silindi: /fall_events/{event_id}")
            return True
        except Exception as e:
            logging.error(f"Düşme olayı silinirken hata: {str(e)}")
            return True  # Yerel silme başarılı

    def test_connection(self):
        """Veritabanı bağlantısını test eder."""
        if not self.is_available:
            return {"status": "local", "message": "Yerel depolama aktif"}
        
        try:
            # Test collection'a basit bir yazma işlemi yap
            test_ref = self.db.collection("test").document("connection_test")
            test_ref.set({"timestamp": firestore.SERVER_TIMESTAMP, "test": True})
            test_ref.delete()  # Test verisini sil
            
            return {"status": "connected", "message": "Firestore bağlantısı başarılı"}
        except Exception as e:
            logging.error(f"Bağlantı testi hatası: {e}")
            return {"status": "error", "message": f"Bağlantı hatası: {str(e)}"}