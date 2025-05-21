# File: pc/core/fall_detection.py
# Açıklama: YOLOv11 tabanlı düşme algılama için modül

import torch
import numpy as np
import cv2
import logging
import os
import time
from config.settings import MODEL_PATH, CONFIDENCE_THRESHOLD, FRAME_WIDTH, FRAME_HEIGHT

class FallDetector:
    """YOLOv11 tabanlı düşme algılama sınıfı."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Singleton örneği döndürür."""
        if not hasattr(cls, '_instance') or cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Düşme algılama sınıfını başlatır.
        YOLOv11 modelini yükler ve çalışmaya hazır hale getirir.
        """
        # Singleton kontrolü
        if hasattr(FallDetector, '_instance') and FallDetector._instance is not None:
            raise RuntimeError("FallDetector zaten başlatılmış. get_instance() kullanın.")
            
        # Cihazı belirle (CUDA GPU veya CPU)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logging.info(f"YOLOv11 modeli şu cihazda çalışacak: {self.device}")
        
        # Model yükleme işlemi
        self.model = None
        self.is_model_loaded = False
        self._load_model()
        
        # Sınıf adları - YOLOv11 düşme algılama için
        self.class_names = ['normal', 'fall']
        
        # İstatistikler ve performans
        self.total_detections = 0
        self.total_inference_time = 0
        self.max_inference_time = 0
        self.min_inference_time = float('inf')
        self.last_log_time = time.time()
        self.last_process_time = 0
        self.process_interval = 5.0  # Her 5 saniyede bir işleme (değiştirildi)
        
        # FallDetector sınıfı singleton
        FallDetector._instance = self
    
    def _load_model(self):
        """YOLOv11 modelini yükler."""
        try:
            logging.info(f"YOLOv11 model dosyası yükleniyor: {MODEL_PATH}")
            
            # Model dosyasını kontrol et
            if not os.path.exists(MODEL_PATH):
                logging.error(f"Model dosyası bulunamadı: {MODEL_PATH}")
                return
            
            file_size = os.path.getsize(MODEL_PATH)
            if file_size < 1024:  # 1KB'den küçükse muhtemelen bozuk
                logging.error(f"Model dosyası çok küçük, muhtemelen bozuk: {file_size} bytes")
                return
            
            # YOLOv11 modelini yükle - Ultralytics kütüphanesi kullanılıyor
            try:
                # Import ultralytics - bu kütüphane yüklü olmalı
                import ultralytics
                from ultralytics import YOLO
                
                # YOLO model yükleme
                self.model = YOLO(MODEL_PATH)
                logging.info(f"YOLOv11 modeli başarıyla yüklendi: {MODEL_PATH}")
                
                # Başarılı yükleme
                self.is_model_loaded = True
                
            except ImportError:
                logging.error("Ultralytics kütüphanesi bulunamadı, lütfen 'pip install ultralytics' komutu ile yükleyin")
                return
            except Exception as e:
                logging.error(f"YOLOv11 model yükleme hatası: {str(e)}")
                
                # Fallback: Torch'un standart load metodunu dene
                try:
                    self.model = torch.load(MODEL_PATH, map_location=self.device)
                    self.is_model_loaded = True
                    logging.info(f"Model alternatif yöntemle yüklendi: {MODEL_PATH}")
                except Exception as e2:
                    logging.error(f"Alternatif yükleme de başarısız: {str(e2)}")
                    return
            
        except Exception as e:
            logging.error(f"Model yüklenirken hata oluştu: {str(e)}", exc_info=True)
            logging.warning("YOLOv11 modeli yüklenemedi! Düşme algılama devre dışı.")
            self.model = None
            self.is_model_loaded = False
    
    def reload_model(self):
        """Modeli yeniden yükler."""
        logging.info("YOLOv11 modeli yeniden yükleniyor...")
        self.model = None
        self.is_model_loaded = False
        self._load_model()
        return self.is_model_loaded
    
    def detect_fall(self, frame):
        """
        YOLOv11 modelini kullanarak düşme algılama gerçekleştirir.
        
        Args:
            frame (numpy.ndarray): İşlenecek kare
            
        Returns:
            tuple: (is_fall, confidence) - Düşme algılandı mı ve olasılığı
        """
        # Model yüklü değilse çıkış
        if not self.is_model_loaded or self.model is None:
            logging.warning("YOLOv11 modeli yüklü değil, düşme algılama devre dışı.")
            return False, 0.0
        
        # 5 saniyelik kontrol - işleme zamanı gelmemişse önceki sonucu döndür
        current_time = time.time()
        if current_time - self.last_process_time < self.process_interval:
            return False, 0.0  # İşleme zamanı gelmedi, düşme yok olarak döndür
            
        # İşleme zamanını güncelle
        self.last_process_time = current_time
        
        # İstatistikler için düzenli loglama
        now = time.time()
        if now - self.last_log_time > 3600:  # Saatte bir loglama
            if self.total_detections > 0:
                avg_time = self.total_inference_time / self.total_detections
                logging.info(f"YOLOv11 Performans istatistikleri: Toplam: {self.total_detections} algılama, "
                           f"Ortalama: {avg_time*1000:.2f}ms, "
                           f"Min: {self.min_inference_time*1000:.2f}ms, "
                           f"Max: {self.max_inference_time*1000:.2f}ms")
                self.total_detections = 0
                self.total_inference_time = 0
                self.max_inference_time = 0
                self.min_inference_time = float('inf')
            self.last_log_time = now
        
        try:
            # Frame boyutunu modelin beklediği boyuta yeniden boyutlandır (640x640)
            resized_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            
            # Başlangıç zamanı
            start_time = time.time()
            
            # YOLOv11 için kareyi işle
            results = self.model.predict(resized_frame, conf=CONFIDENCE_THRESHOLD)
            
            # YOLOv11 düşme algılama sonuçlarını çözümle
            fall_detected = False
            fall_confidence = 0.0
            
            # İlk sonuç grubunu al
            if results and len(results) > 0:
                # Kutuları al
                boxes = results[0].boxes
                
                # Her bir tespit için kontrol et
                for i, box in enumerate(boxes):
                    cls = int(box.cls.item())
                    conf = float(box.conf.item())
                    
                    # "fall" sınıfı (indeks 1) ve güven değerini kontrol et
                    if cls == 1:  # 1 = fall (düşme) sınıfı
                        if conf > fall_confidence:
                            fall_confidence = conf
                            fall_detected = True
            
            # Eşik değeriyle karşılaştır (eşiği settings.py'da tanımladığımız için burada tekrar kontrol etmeye gerek yok)
            is_fall = fall_detected
            
            # İstatistikleri güncelle
            inference_time = time.time() - start_time
            self.total_detections += 1
            self.total_inference_time += inference_time
            self.max_inference_time = max(self.max_inference_time, inference_time)
            self.min_inference_time = min(self.min_inference_time, inference_time)
            
            # Düşme algılandıysa logla
            if is_fall:
                logging.info(f"Düşme algılandı! Güven: {fall_confidence:.4f}")
            
            return is_fall, fall_confidence
            
        except Exception as e:
            logging.error(f"Düşme algılanırken hata oluştu: {str(e)}")
            return False, 0.0
    
    def get_heatmap(self, frame):
        """
        Aktivasyon ısı haritasını oluşturur (sağlık kontrolü için).
        YOLOv11 için özelleştirilmiş görselleştirme.
        
        Args:
            frame (numpy.ndarray): OpenCV formatında BGR kare

        Returns:
            numpy.ndarray: Tespit kutuları çizilmiş görüntü veya hata durumunda None
        """
        if not self.is_model_loaded or self.model is None:
            return None
            
        try:
            # Frame'i modele uygun boyuta getir
            resized_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            
            # YOLOv11 tespitlerini al
            results = self.model.predict(resized_frame, conf=0.3)  # Düşük güven eşiği ile göster
            
            # Kare kopyasını oluştur
            heatmap = resized_frame.copy()
            
            # Tespitleri çiz
            if results and len(results) > 0:
                # Her bir tespit için
                for box in results[0].boxes:
                    # Kutu koordinatlarını al
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Sınıf ve güven değerini al
                    cls = int(box.cls.item())
                    conf = float(box.conf.item())
                    
                    # Sınıf adını belirle
                    class_name = self.class_names[cls] if cls < len(self.class_names) else f"Sınıf {cls}"
                    
                    # Rengi belirle (düşme: kırmızı, normal: yeşil)
                    color = (0, 0, 255) if cls == 1 else (0, 255, 0)
                    
                    # Dikdörtgen çiz
                    cv2.rectangle(heatmap, (x1, y1), (x2, y2), color, 2)
                    
                    # Etiket ekle
                    label = f"{class_name}: {conf:.2f}"
                    cv2.putText(heatmap, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Orijinal frame boyutuna geri getir
            if frame.shape[:2] != (FRAME_HEIGHT, FRAME_WIDTH):
                heatmap = cv2.resize(heatmap, (frame.shape[1], frame.shape[0]))
                
            return heatmap
            
        except Exception as e:
            logging.error(f"Isı haritası oluşturulurken hata: {str(e)}")
            return None