# guard_pc_app/data/storage.py (Güncellenmiş ve Düzeltilmiş)
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

class StorageManager:
    """Firebase Storage işlemlerini yöneten sınıf."""
    
    def __init__(self, bucket=None):
        """
        Args:
            bucket (google.cloud.storage.bucket.Bucket, optional): Firebase Storage bucket nesnesi
        """
        try:
            self.bucket = bucket or storage.bucket()
            self.is_available = True
            logging.info("Firebase Storage bağlantısı başarılı.")
        except Exception as e:
            logging.warning(f"Firebase Storage başlatılamadı: {str(e)}")
            logging.info("Yerel dosya depolama kullanılacak.")
            self.is_available = False
            
            # Yerel depolama dizini oluştur
            self.local_storage_dir = os.path.join(os.path.dirname(__file__), "local_storage")
            os.makedirs(self.local_storage_dir, exist_ok=True)
    
    def upload_screenshot(self, user_id, image, event_id=None):
        """Ekran görüntüsünü Firebase Storage'a veya yerel depolamaya yükler.
        
        Args:
            user_id (str): Kullanıcı ID'si
            image (numpy.ndarray): Yüklenecek görüntü (OpenCV formatında)
            event_id (str, optional): Olay ID'si
            
        Returns:
            str: Yüklenen dosyanın URL'si/yolu, hata durumunda None
        """
        try:
            if event_id is None:
                event_id = str(uuid.uuid4())
                
            logging.info(f"Ekran görüntüsü yükleniyor - User: {user_id}, Event: {event_id}")
            
            if not self.is_available:
                # Yerel depolamaya kaydet
                return self._upload_local(user_id, image, event_id)
            
            # Firebase Storage'a yükle
            return self._upload_firebase(user_id, image, event_id)
                
        except Exception as e:
            logging.error(f"Ekran görüntüsü yüklenirken hata oluştu: {str(e)}", exc_info=True)
            return None
    
    def _upload_local(self, user_id, image, event_id):
        """Yerel depolamaya kaydet."""
        try:
            user_dir = os.path.join(self.local_storage_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            local_path = os.path.join(user_dir, f"{event_id}.jpg")
            
            # OpenCV görüntüsünü JPEG olarak kaydet
            success = cv2.imwrite(local_path, image, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            if success:
                logging.info(f"Ekran görüntüsü yerel depolamaya kaydedildi: {local_path}")
                return f"file://{os.path.abspath(local_path)}"
            else:
                logging.error("Görüntü yerel depolamaya kaydedilemedi")
                return None
                
        except Exception as e:
            logging.error(f"Yerel depolama hatası: {str(e)}")
            return None
    
    def _upload_firebase(self, user_id, image, event_id):
        """Firebase Storage'a yükle."""
        try:
            # Görüntüyü JPEG formatında byte dizisine dönüştür
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 90]
            success, img_encoded = cv2.imencode('.jpg', image, encode_param)
            
            if not success:
                logging.error("Görüntü encode edilemedi")
                return None
            
            img_bytes = img_encoded.tobytes()
            
            # Firebase Storage yolu
            destination_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(destination_path)
            
            # Metadata ekle
            blob.metadata = {
                'user_id': user_id,
                'event_id': event_id,
                'upload_time': str(int(time.time())),
                'content_type': 'image/jpeg'
            }
            
            # Byte dizisinden yükle
            blob.upload_from_string(
                img_bytes,
                content_type='image/jpeg'
            )
            
            # Access token oluştur (görüntünün tarayıcıda görüntülenebilmesi için)
            try:
                import uuid as uuid_lib
                access_token = str(uuid_lib.uuid4())
                blob.metadata = blob.metadata or {}
                blob.metadata['firebaseStorageDownloadTokens'] = access_token
                blob.patch()
                
                # Public URL oluştur
                project_id = firebase_admin._apps['[DEFAULT]']._project_id
                bucket_name = self.bucket.name
                public_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{destination_path.replace('/', '%2F')}?alt=media&token={access_token}"
                
                logging.info(f"Ekran görüntüsü Firebase Storage'a yüklendi: {destination_path}")
                return public_url
                
            except Exception as token_error:
                logging.warning(f"Access token oluşturulamadı: {str(token_error)}")
                
                # Fallback: signed URL oluştur
                try:
                    from datetime import timedelta
                    url = blob.generate_signed_url(
                        version="v4",
                        expiration=timedelta(days=365),  # 1 yıl geçerli
                        method="GET"
                    )
                    logging.info(f"Signed URL oluşturuldu: {destination_path}")
                    return url
                except Exception as signed_error:
                    logging.error(f"Signed URL oluşturulamadı: {str(signed_error)}")
                    # En son çare olarak public URL
                    return f"https://storage.googleapis.com/{self.bucket.name}/{destination_path}"
            
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
            if not self.is_available:
                # Yerel depolamadan sil
                local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logging.info(f"Ekran görüntüsü yerel depolamadan silindi: {local_path}")
                    return True
                else:
                    logging.warning(f"Silinecek ekran görüntüsü bulunamadı: {local_path}")
                    return False
            
            blob_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                blob.delete()
                logging.info(f"Ekran görüntüsü silindi: {blob_path}")
                return True
            else:
                logging.warning(f"Silinecek ekran görüntüsü bulunamadı: {blob_path}")
                return False
                
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
            if not self.is_available:
                # Yerel dosya yolunu döndür
                local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
                if os.path.exists(local_path):
                    return f"file://{os.path.abspath(local_path)}"
                else:
                    logging.warning(f"Görüntü bulunamadı: {local_path}")
                    return None
            
            blob_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                # Metadata'dan token'ı al
                blob.reload()
                if blob.metadata and 'firebaseStorageDownloadTokens' in blob.metadata:
                    token = blob.metadata['firebaseStorageDownloadTokens']
                    project_id = firebase_admin._apps['[DEFAULT]']._project_id
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
                logging.warning(f"Görüntü bulunamadı: {blob_path}")
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
            if not self.is_available:
                # Yerel dosyayı oku
                local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
                if os.path.exists(local_path):
                    img = cv2.imread(local_path)
                    return img
                else:
                    logging.warning(f"İndirilecek görüntü bulunamadı: {local_path}")
                    return None
            
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
                logging.warning(f"İndirilecek görüntü bulunamadı: {blob_path}")
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
            if not self.is_available:
                # Yerel dosyaları listele
                user_dir = os.path.join(self.local_storage_dir, user_id)
                if not os.path.exists(user_dir):
                    return []
                
                files = os.listdir(user_dir)
                event_ids = [f.replace('.jpg', '') for f in files if f.endswith('.jpg')]
                return event_ids
            
            # Storage'dan liste al
            prefix = f"fall_events/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            event_ids = []
            for blob in blobs:
                filename = os.path.basename(blob.name)
                if filename.endswith('.jpg'):
                    event_id = filename.replace('.jpg', '')
                    event_ids.append(event_id)
            
            return event_ids
                
        except Exception as e:
            logging.error(f"Ekran görüntüleri listelenirken hata oluştu: {str(e)}")
            return []