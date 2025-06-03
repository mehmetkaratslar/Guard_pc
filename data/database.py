# =======================================================================================
# 📄 Dosya Adı: database.py
# 📁 Konum: guard_pc_app/data/database.py
# 📌 Açıklama:
# Firestore tabanlı kullanıcı ve düşme olayı yönetimi.
# save_fall_event, /fall_events/{eventId} yoluna kaydeder.
# Yerel depolamada /users/{user_id}/events ve /users/{user_id}/fall_events korunur.
# Mobil uygulama için erişim optimize edildi.
# 🔗 Bağlantılı Dosyalar:
# - config/settings.py: Firestore bağlantı ve uygulama ayarları
# - ui/app.py: Firestore’a olay kaydı
# - config/firebase_config.py: Firebase yapılandırma
# - core/notification.py: Olay sonrası bildirim tetikler
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
        try:
            self.db = db or firestore.client()
            self.is_available = True
            logging.info("Firestore bağlantısı başarılı.")
        except Exception as e:
            logging.warning(f"Firestore başlatılamadı: {str(e)}")
            logging.info("Yerel dosya tabanlı veri saklama kullanılacak.")
            self.is_available = False
            self._memory_storage = {
                "users": {}
            }
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
    
    def _save_local_data(self):
        """Verileri yerel dosyaya kaydeder."""
        try:
            file_path = self._get_local_data_path()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._memory_storage, f, indent=2, ensure_ascii=False)
            logging.info(f"Veriler yerel dosyaya kaydedildi: {file_path}")
        except Exception as e:
            logging.error(f"Veriler yerel dosyaya kaydedilirken hata: {str(e)}")

    def get_user_data(self, user_id):
        """Kullanıcı verilerini getirir."""
        if not self.is_available:
            user_data = self._memory_storage["users"].get(user_id, None)
            logging.info(f"Yerel depodan kullanıcı verisi alındı: {user_id}")
            return user_data
        
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                return user_doc.to_dict()
            else:
                logging.warning(f"Kullanıcı bulunamadı: {user_id}")
                return None
        except Exception as e:
            logging.error(f"Kullanıcı verileri getirilirken hata: {str(e)}")
            return None

    def save_user_settings(self, user_id, settings):
        """Kullanıcı ayarlarını kaydeder."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {}
            if "settings" not in self._memory_storage["users"][user_id]:
                self._memory_storage["users"][user_id]["settings"] = {}
            self._memory_storage["users"][user_id]["settings"].update(settings)
            self._memory_storage["users"][user_id]["updated_at"] = time.time()
            self._save_local_data()
            logging.info(f"Kullanıcı ayarları yerel depoya kaydedildi: {user_id}")
            return True
        
        try:
            user_ref = self.db.collection("users").document(user_id)
            settings["updated_at"] = firestore.SERVER_TIMESTAMP
            user_ref.set({"settings": settings}, merge=True)
            logging.info(f"Kullanıcı ayarları güncellendi: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Kullanıcı ayarları kaydedilirken hata: {str(e)}")
            return False
    
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
            
            if not self.is_available:
                # Yerel depolamada /users/{user_id}/events ve /users/{user_id}/fall_events’e kaydet
                if user_id not in self._memory_storage["users"]:
                    self._memory_storage["users"][user_id] = {"id": user_id}
                
                for collection_name in ["events", "fall_events"]:
                    if collection_name not in self._memory_storage["users"][user_id]:
                        self._memory_storage["users"][user_id][collection_name] = []
                    self._memory_storage["users"][user_id][collection_name].append(event_data)
                
                self._save_local_data()
                logging.info(f"Düşme olayı yerel depoya kaydedildi: {event_id}")
                return True
            
            # Firestore’a /fall_events/{eventId} yoluna kaydet
            doc_ref = self.db.collection("fall_events").document(event_id)
            doc_ref.set(event_data)
            logging.info(f"Düşme olayı Firestore’a kaydedildi: /fall_events/{event_id}")
            return True
            
        except Exception as e:
            logging.error(f"Düşme olayı kaydedilirken hata: {str(e)}")
            return False

    def get_fall_events(self, user_id, limit=50):
        """
        Kullanıcının düşme olaylarını getirir.
        Firestore’da /fall_events/’ten, yerel depoda /users/{user_id}/events ve /users/{user_id}/fall_events’ten çeker.
        """
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
            # Firestore’dan /fall_events/’ten çek, user_id ile filtrele
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
            
            logging.info(f"Firestore’dan {len(events)} düşme olayı getirildi")
            return events
            
        except Exception as e:
            logging.error(f"Düşme olayları getirilirken hata: {str(e)}")
            return []
    
    def create_new_user(self, user_id, user_data):
        """Yeni kullanıcı oluşturur."""
        base_data = {
            "id": user_id,
            "created_at": time.time(),
            "last_login": time.time(),
            "settings": {
                "email_notification": True,
                "sms_notification": False,
                "telegram_notification": False,
                "phone_number": "",
                "telegram_chat_id": ""
            }
        }
        user_data = {**base_data, **user_data}
        
        if not self.is_available:
            self._memory_storage["users"][user_id] = user_data
            self._save_local_data()
            logging.info(f"Yeni kullanıcı yerel depoya kaydedildi: {user_id}")
            return True
            
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.set(user_data)
            logging.info(f"Yeni kullanıcı oluşturuldu: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Kullanıcı oluşturulurken hata: {str(e)}")
            return False
    
    def update_last_login(self, user_id):
        """Kullanıcının son giriş zamanını günceller."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            self._memory_storage["users"][user_id]["last_login"] = time.time()
            self._save_local_data()
            logging.info(f"Son giriş zamanı yerel depoda güncellendi: {user_id}")
            return True
            
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.update({"last_login": firestore.SERVER_TIMESTAMP})
            return True
        except Exception as e:
            logging.error(f"Son giriş zamanı güncellenirken hata: {str(e)}")
            return False
    
    def update_user_data(self, user_id, user_data):
        """Kullanıcı bilgilerini günceller."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            self._memory_storage["users"][user_id].update(user_data)
            self._memory_storage["users"][user_id]["updated_at"] = time.time()
            self._save_local_data()
            logging.info(f"Kullanıcı verileri yerel depoda güncellendi: {user_id}")
            return True
            
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_data["updated_at"] = firestore.SERVER_TIMESTAMP
            user_ref.update(user_data)
            logging.info(f"Kullanıcı verileri güncellendi: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Kullanıcı verileri güncellenirken hata: {str(e)}")
            return False
    
    def delete_fall_event(self, user_id, event_id):
        """Düşme olayını siler."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                return False
            for collection_name in ["events", "fall_events"]:
                if collection_name in self._memory_storage["users"][user_id]:
                    events = self._memory_storage["users"][user_id][collection_name]
                    self._memory_storage["users"][user_id][collection_name] = [
                        e for e in events if e.get("id") != event_id
                    ]
            self._save_local_data()
            logging.info(f"Düşme olayı yerel depodan silindi: {event_id}")
            return True
            
        try:
            # Firestore’dan /fall_events/{eventId}’yi sil
            doc_ref = self.db.collection("fall_events").document(event_id)
            doc_ref.delete()
            logging.info(f"Düşme olayı Firestore’dan silindi: /fall_events/{event_id}")
            return True
        except Exception as e:
            logging.error(f"Düşme olayı silinirken hata: {str(e)}")
            return False