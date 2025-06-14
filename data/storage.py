# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: storage.py (FIREBASE STORAGE VE YEREL GÖRSEL DEPOLAMA)
# Konum: guard_pc_app/data/storage.py
# Açıklama:
# Bu sınıf, Guard AI uygulamasında düşme olayları sırasında alınan ekran görüntülerinin 
# Firebase Cloud Storage ve yerel disk üzerinde saklanması, alınması ve silinmesi işlemlerini yönetir.
#
# Uygulama çevrimdışıyken bile görüntüleri geçici olarak yerel olarak saklayabilir,
# internet bağlantısı tekrar sağlandığında buluta senkronize edebilir.

# === ÖZELLİKLER ===
# - Firebase Storage entegrasyonu (görüntü yükleme/indirme)
# - Yerel disk desteği (çevrimdışı işlemeye izin verir)
# - Görüntü URL oluşturma (signed URL veya yerel yol)
# - Ekran görüntüsünü listeleme/silme işlemleri
# - Bağlantı testi (Storage erişilebilirliği kontrolü)

# === BAŞLICA MODÜLLER VE KULLANIM AMACI ===
# - logging: Hata ve işlem kayıtları tutma
# - firebase_admin.storage: Firebase Storage erişimi
# - cv2 (OpenCV): Görüntü işleme ve JPEG formatına dönüştürme
# - numpy: Görsel verilerin manipülasyonu
# - os / tempfile: Yerel dosya yönetimi
# - datetime: Signed URL süresi için zaman damgası

# === SINIFLAR ===
# - ScreenshotStorageManager: Firebase Storage ve yerel depolama işlemleri için ana sınıf

# === TEMEL FONKSİYONLAR ===
# - save_screenshot: Düşme anında alınan ekran görüntüsünü kaydeder (yerel ya da uzak)
# - get_screenshot_url: Belirli bir düşme olayının ekran görüntüsünün URL'sini döndürür
# - download_screenshot: Görüntüyü indirip OpenCV formatında döner
# - list_all_screenshots: Kullanıcının tüm ekran görüntülerini listeler
# - delete_screenshot: Belirli bir ekran görüntüsünü siler
# - test_connection: Firebase Storage bağlantısını test eder

# === VERİ DEPOLAMA MEKANİZMALARI ===
# 1. FIREBASE STORAGE:
#    - Ana depolama alanı
#    - Gerçek zamanlı erişim
#    - Birden fazla cihaz arasında senkronizasyon
#    - Signed URL ile güvenli erişim
# 2. YEREL DEPOLAMA:
#    - Çevrimdışı modda kullanılabilir
#    - Geçici yedekleme mekanizması
#    - Otomatik senkronizasyon destekli

# === GÖRSEL İŞLEME ===
# - Görüntü OpenCV ile işlenir (JPEG formatında sıkıştırılır)
# - Yerel olarak `user_id/event_id.jpg` şeklinde saklanır
# - Firebase Storage'a `screenshots/{user_id}/{event_id}.jpg` yoluyla yüklenir

# === URL ÜRETİMİ ===
# - Firebase Storage için signed URL üretir (365 gün geçerli)
# - Yerel dosyalar için `file://` protokolü kullanılır

# === BAĞIMSIZ ÇALIŞMA DESTEĞİ ===
# - Eğer internet yoksa yerel dosyaya yazma yapılır
# - İnternet tekrar bağlandığında yerel veriler Firebase'e senkronize edilir

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
# - Bu dosya, app.py, dashboard.py ve database.py ile entegre çalışır
# - Firebase kimlik doğrulaması zorunludur
# - Yerel depolama sadece geçici çözümler içindir
# =======================================================================================
import logging
import firebase_admin
from firebase_admin import storage
import cv2
import numpy as np
import os
import uuid
import tempfile
import time
import io
from PIL import Image

class StorageManager:
    """Firebase Storage işlemlerini yöneten sınıf."""
    
    def __init__(self, bucket=None):
        """
        Args:
            bucket (google.cloud.storage.bucket.Bucket, optional): Firebase Storage bucket nesnesi
        """
        # Yerel depolama dizini her durumda oluştur
        self.local_storage_dir = os.path.join(os.path.dirname(__file__), "local_storage")
        os.makedirs(self.local_storage_dir, exist_ok=True)
        
        try:
            self.bucket = bucket or storage.bucket()
            self.is_available = True
            logging.info("Firebase Storage bağlantısı başarılı.")
        except Exception as e:
            logging.warning(f"Firebase Storage başlatılamadı: {str(e)}")
            logging.info("Yerel dosya depolama kullanılacak.")
            self.is_available = False
            
    def upload_screenshot(self, image_data, user_id, event_id):
        """
        Ekran görüntüsünü yükler.
        
        Args:
            image_data: PIL Image veya bytes
            user_id (str): Kullanıcı ID
            event_id (str): Olay ID
            
        Returns:
            str: Yüklenen dosyanın URL'i veya None
        """
        try:
            # DÜZELTME: Farklı image formatlarını destekle
            if hasattr(image_data, 'save'):
                # PIL Image
                img = image_data
            elif hasattr(image_data, 'shape'):
                # DÜZELTME: NumPy array desteği eklendi
                import numpy as np
                if len(image_data.shape) == 3:
                    # BGR to RGB conversion (OpenCV format)
                    image_rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(image_rgb.astype(np.uint8))
                else:
                    img = Image.fromarray(image_data.astype(np.uint8))
                logging.debug(f"NumPy array converted to PIL Image: {image_data.shape}")
            elif isinstance(image_data, bytes):
                # Bytes ise PIL Image'a çevir
                img = Image.open(io.BytesIO(image_data))
            else:
                logging.error(f"Desteklenmeyen image_data türü: {type(image_data)}")
                return None
            
            # Görüntüyü optimize et (max 1280x720)
            max_size = (1280, 720)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # JPEG olarak kaydet (kalite: 75)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=75, optimize=True)
            img_bytes = img_bytes.getvalue()
            
            # Dosya boyutunu logla
            size_mb = len(img_bytes) / (1024 * 1024)
            logging.info(f"Optimize edilmiş görüntü boyutu: {size_mb:.2f} MB")
            
            # Dosya adı
            filename = f"{event_id}.jpg"
            
            # Firebase Storage'a yükle
            if self.is_available:
                try:
                    url = self._upload_firebase(img_bytes, user_id, filename)
                    if url:
                        return url
                except Exception as e:
                    logging.error(f"Firebase Storage hatası: {e}")
                    # Firebase başarısız olursa yerel depolamaya geç
            
            # Yerel depolamaya kaydet (yedek olarak)
            return self._upload_local(img_bytes, user_id, filename)
            
        except Exception as e:
            logging.error(f"Screenshot upload hatası: {str(e)}")
            return None
    
    def _upload_local(self, img_bytes, user_id, filename):
        """Yerel depolamaya kaydet."""
        try:
            user_dir = os.path.join(self.local_storage_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            local_path = os.path.join(user_dir, filename)
            
            # Byte dizisinden yükle
            with open(local_path, 'wb') as f:
                f.write(img_bytes)
            
            logging.info(f"Ekran görüntüsü yerel depolamaya kaydedildi: {local_path}")
            return f"file://{os.path.abspath(local_path)}"
                
        except Exception as e:
            logging.error(f"Yerel depolama hatası: {str(e)}")
            return None
    
    def _upload_firebase(self, img_bytes, user_id, filename):
        """Firebase Storage'a yükle."""
        try:
            destination_path = f"fall_events/{user_id}/{filename}"
            blob = self.bucket.blob(destination_path)

            # Access token üret
            import uuid as uuid_lib
            access_token = str(uuid_lib.uuid4())

            # Metadata'yı güncelle (var olan metadata üzerine ekle)
            existing_metadata = blob.metadata or {}
            existing_metadata.update({
                'user_id': user_id,
                'event_id': filename.replace('.jpg', ''),
                'upload_time': str(int(time.time())),
                'content_type': 'image/jpeg',
                'firebaseStorageDownloadTokens': access_token,
            })
            blob.metadata = existing_metadata

            # Byte dizisinden yükle
            blob.upload_from_string(img_bytes, content_type='image/jpeg')
            blob.patch()  # Metadata'yı kaydet

            logging.info(f"Blob metadata: {blob.metadata}")

            bucket_name = self.bucket.name
            public_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{destination_path.replace('/', '%2F')}?alt=media&token={access_token}"

            logging.info(f"Ekran görüntüsü Firebase Storage'a yüklendi: {destination_path}")
            return public_url

        except Exception as e:
            logging.error(f"Firebase Storage yükleme hatası: {str(e)}", exc_info=True)
            return None

    def delete_screenshot(self, user_id, event_id):
        """Ekran görüntüsünü Firebase Storage'dan veya yerel depolamadan siler.
        
        Args:
            user_id (str): Kullanıcı ID'si
            event_id (str): Olay ID'si
            
        Returns:
            bool: İşlem başarılı ise True, değilse False
        """
        try:
            if not user_id or not event_id:
                logging.error("delete_screenshot: user_id veya event_id boş")
                return False
                
            success = True
            
            # Yerel depolamadan sil
            try:
                local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logging.info(f"Ekran görüntüsü yerel depolamadan silindi: {local_path}")
            except Exception as e:
                logging.error(f"Yerel silme hatası: {e}")
                success = False
            
            if not self.is_available:
                return success
            
            # Firebase Storage'dan sil
            try:
                blob_path = f"fall_events/{user_id}/{event_id}.jpg"
                blob = self.bucket.blob(blob_path)
                
                if blob.exists():
                    blob.delete()
                    logging.info(f"Ekran görüntüsü Firebase'den silindi: {blob_path}")
                else:
                    logging.warning(f"Silinecek ekran görüntüsü Firebase'de bulunamadı: {blob_path}")
            except Exception as e:
                logging.error(f"Firebase silme hatası: {e}")
                success = False
            
            return success
                
        except Exception as e:
            logging.error(f"Ekran görüntüsü silinirken hata oluştu: {str(e)}")
            return False
    
    def get_screenshot_url(self, user_id, event_id):
        """Ekran görüntüsünün URL'sini döndürür.
        
        Args:
            user_id (str): Kullanıcı ID'si
            event_id (str): Olay ID'si
            
        Returns:
            str: Görüntünün URL'si, hata durumunda None
        """
        try:
            if not user_id or not event_id:
                logging.error("get_screenshot_url: user_id veya event_id boş")
                return None
                
            # Önce yerel dosyaya bak
            local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
            if os.path.exists(local_path):
                return f"file://{os.path.abspath(local_path)}"
            
            if not self.is_available:
                logging.warning(f"Görüntü bulunamadı: {local_path}")
                return None
            
            # Firebase Storage'da ara
            blob_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                # Metadata'dan token'ı al
                blob.reload()
                if blob.metadata and 'firebaseStorageDownloadTokens' in blob.metadata:
                    token = blob.metadata['firebaseStorageDownloadTokens']
                    bucket_name = self.bucket.name
                    return f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{blob_path.replace('/', '%2F')}?alt=media&token={token}"
                else:
                    # Signed URL oluştur
                    from datetime import timedelta
                    url = blob.generate_signed_url(
                        version="v4",
                        expiration=timedelta(days=365),
                        method="GET"
                    )
                    return url
            else:
                logging.warning(f"Görüntü Firebase'de bulunamadı: {blob_path}")
                return None
                
        except Exception as e:
            logging.error(f"Görüntü URL'si alınırken hata oluştu: {str(e)}")
            return None
    
    def download_screenshot(self, user_id, event_id):
        """Ekran görüntüsünü indirir ve bir numpy dizisi olarak döndürür.
        
        Args:
            user_id (str): Kullanıcı ID'si
            event_id (str): Olay ID'si
            
        Returns:
            numpy.ndarray: Görüntü, hata durumunda None
        """
        try:
            if not user_id or not event_id:
                logging.error("download_screenshot: user_id veya event_id boş")
                return None
                
            # Önce yerel dosyayı dene
            local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
            if os.path.exists(local_path):
                img = cv2.imread(local_path)
                if img is not None:
                    return img
            
            if not self.is_available:
                logging.warning(f"İndirilecek görüntü bulunamadı: {local_path}")
                return None
            
            # Firebase Storage'dan indir
            blob_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                # Görüntüyü byte dizisi olarak indir
                img_bytes = blob.download_as_bytes()
                
                # Byte dizisini numpy array'e dönüştür
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                return img
            else:
                logging.warning(f"İndirilecek görüntü Firebase'de bulunamadı: {blob_path}")
                return None
                
        except Exception as e:
            logging.error(f"Görüntü indirilirken hata oluştu: {str(e)}")
            return None
    
    def list_all_screenshots(self, user_id):
        """Kullanıcının tüm ekran görüntülerini listeler.
        
        Args:
            user_id (str): Kullanıcı ID'si
            
        Returns:
            list: event_id'lerin listesi
        """
        try:
            if not user_id:
                logging.error("list_all_screenshots: user_id boş")
                return []
                
            event_ids = set()
            
            # Yerel dosyaları listele
            user_dir = os.path.join(self.local_storage_dir, user_id)
            if os.path.exists(user_dir):
                files = os.listdir(user_dir)
                local_ids = [f.replace('.jpg', '') for f in files if f.endswith('.jpg')]
                event_ids.update(local_ids)
            
            if not self.is_available:
                return list(event_ids)
            
            # Firebase Storage'dan liste al
            try:
                prefix = f"fall_events/{user_id}/"
                blobs = self.bucket.list_blobs(prefix=prefix)
                
                for blob in blobs:
                    filename = os.path.basename(blob.name)
                    if filename.endswith('.jpg'):
                        event_id = filename.replace('.jpg', '')
                        event_ids.add(event_id)
            except Exception as e:
                logging.error(f"Firebase listeleme hatası: {e}")
            
            return list(event_ids)
                
        except Exception as e:
            logging.error(f"Ekran görüntüleri listelenirken hata oluştu: {str(e)}")
            return []

    def test_connection(self):
        """Storage bağlantısını test eder."""
        if not self.is_available:
            return {"status": "local", "message": "Yerel depolama aktif"}
        
        try:
            # Test dosyası yükle
            test_data = b"test data"
            test_blob = self.bucket.blob("test/connection_test.txt")
            test_blob.upload_from_string(test_data, content_type='text/plain')
            
            # Test dosyasını sil
            test_blob.delete()
            
            return {"status": "connected", "message": "Firebase Storage bağlantısı başarılı"}
        except Exception as e:
            logging.error(f"Storage bağlantı testi hatası: {e}")
            return {"status": "error", "message": f"Bağlantı hatası: {str(e)}"}