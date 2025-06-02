# File: core/fall_detection.py
# Açıklama: YOLOv11 tabanlı gerçek zamanlı düşme algılama modülü

import torch
import numpy as np
import cv2
import logging
import os
import time
from config.settings import MODEL_PATH, CONFIDENCE_THRESHOLD, FRAME_WIDTH, FRAME_HEIGHT

class FallDetector:
    """YOLOv11 tabanlı gerçek zamanlı düşme algılama sınıfı."""
    
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
        self.process_interval = 3.0  # Her 3 saniyede bir işleme
        
        # Düşme algılama sonuçları için filtreler
        self.confidence_buffer = []
        self.buffer_size = 3  # Son 3 tespitin ortalamasını al
        
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
            if file_size < 1024:
                logging.error(f"Model dosyası çok küçük, muhtemelen bozuk: {file_size} bytes")
                return
            
            try:
                from ultralytics import YOLO
                
                # YOLO model yükleme
                self.model = YOLO(MODEL_PATH)
                self.model.to(self.device)
                
                # DÜZELTME: Doğru normalize edilmiş dummy input ile warmup
                dummy_frame = np.random.randint(0, 255, (416, 416, 3), dtype=np.uint8)
                
                # İlk warmup çalıştırması
                with torch.no_grad():
                    _ = self.model.predict(
                        dummy_frame, 
                        verbose=False,
                        imgsz=416,
                        conf=0.5
                    )
                
                logging.info(f"YOLOv11 modeli başarıyla yüklendi ve warmup tamamlandı: {MODEL_PATH}")
                self.is_model_loaded = True
                
            except ImportError:
                logging.error("Ultralytics kütüphanesi bulunamadı, lütfen 'pip install ultralytics' komutu ile yükleyin")
                return
            except Exception as e:
                logging.error(f"YOLOv11 model yükleme hatası: {str(e)}")
                return
            
        except Exception as e:
            logging.error(f"Model yüklenirken hata oluştu: {str(e)}", exc_info=True)
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
        YOLOv11 modelini kullanarak HIZLI düşme algılama gerçekleştirir.
        
        Args:
            frame (numpy.ndarray): İşlenecek kare (BGR formatında)
            
        Returns:
            tuple: (is_fall, confidence) - Düşme algılandı mı ve olasılığı
        """
        # Model yüklü değilse çıkış
        if not self.is_model_loaded or self.model is None:
            logging.warning("YOLOv11 modeli yüklü değil, düşme algılama devre dışı.")
            return False, 0.0
        
        # PERFORMANS OPTİMİZASYONU: 5 saniye yerine 2 saniye interval
        current_time = time.time()
        if current_time - self.last_process_time < 2.0:  # 2 saniyede bir işleme
            return False, 0.0
            
        # İşleme zamanını güncelle
        self.last_process_time = current_time
        
        try:
            # PERFORMANS OPTİMİZASYONU: Frame'i daha küçük boyuta indir
            # CPU için optimize edilmiş boyut: 416x416 yerine 640x640
            optimized_frame = cv2.resize(frame, (416, 416))
            
            # Başlangıç zamanı
            start_time = time.time()
            
            # YOLOv11 inference - PERFORMANS AYARLARI
            with torch.no_grad():
                results = self.model.predict(
                    optimized_frame, 
                    conf=CONFIDENCE_THRESHOLD,
                    verbose=False,
                    device=self.device,
                    imgsz=416,  # Küçük görüntü boyutu
                    half=False,  # CPU için half precision kapalı
                    augment=False,  # Augmentation kapalı
                    agnostic_nms=True,  # Hızlı NMS
                    max_det=10  # Maksimum 10 tespit (hız için)
                )
            
            # Sonuçları analiz et
            is_fall, confidence = self._analyze_results(results)
            
            # PERFORMANS OPTİMİZASYONU: Buffer boyutunu küçült
            buffer_size = 2  # 3 yerine 2
            
            # Güven değerini buffer'a ekle
            if is_fall:
                self.confidence_buffer.append(confidence)
                if len(self.confidence_buffer) > buffer_size:
                    self.confidence_buffer.pop(0)
                
                # Buffer doluysa ve ortalama güven yüksekse düşme algıla
                if len(self.confidence_buffer) >= buffer_size:
                    avg_confidence = sum(self.confidence_buffer) / len(self.confidence_buffer)
                    if avg_confidence > CONFIDENCE_THRESHOLD:
                        final_confidence = avg_confidence
                        final_is_fall = True
                    else:
                        final_confidence = 0.0
                        final_is_fall = False
                else:
                    final_confidence = 0.0
                    final_is_fall = False
            else:
                # Düşme algılanmadıysa buffer'ı temizle
                self.confidence_buffer.clear()
                final_confidence = 0.0
                final_is_fall = False
            
            # İstatistikleri güncelle
            inference_time = time.time() - start_time
            self.total_detections += 1
            self.total_inference_time += inference_time
            self.max_inference_time = max(self.max_inference_time, inference_time)
            self.min_inference_time = min(self.min_inference_time, inference_time)
            
            # Düşme algılandıysa logla
            if final_is_fall:
                logging.info(f"DÜŞME ALGILANDI! Güven: {final_confidence:.4f} (Süre: {inference_time*1000:.1f}ms)")
            
            return final_is_fall, final_confidence
            
        except Exception as e:
            logging.error(f"Düşme algılanırken hata oluştu: {str(e)}")
            return False, 0.0

    def _preprocess_frame(self, frame):
        """
        HIZLI frame preprocessing
        """
        try:
            if frame is None or frame.size == 0:
                return None
            
            # PERFORMANS: BGR'den RGB'ye dönüştürmeyi atla çünkü YOLOv11 otomatik yapıyor
            # rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Direkt resize et (YOLOv11 otomatik renk dönüşümü yapacak)
            resized_frame = cv2.resize(frame, (416, 416))  # Küçük boyut
            
            return resized_frame
            
        except Exception as e:
            logging.error(f"Frame preprocessing hatası: {str(e)}")
            return None




    def _analyze_results(self, results):
        """
        YOLOv11 sonuçlarını analiz eder.
        
        Args:
            results: YOLOv11 çıktısı
            
        Returns:
            tuple: (is_fall, confidence)
        """
        try:
            if not results or len(results) == 0:
                return False, 0.0
            
            # İlk sonuç grubunu al
            result = results[0]
            
            if not hasattr(result, 'boxes') or result.boxes is None:
                return False, 0.0
            
            boxes = result.boxes
            
            max_fall_confidence = 0.0
            fall_detected = False
            
            # Her bir tespit için kontrol et
            for box in boxes:
                if hasattr(box, 'cls') and hasattr(box, 'conf'):
                    cls = int(box.cls.item())
                    conf = float(box.conf.item())
                    
                    # "fall" sınıfı (indeks 1) kontrolü
                    if cls == 1 and conf > max_fall_confidence:  # 1 = fall sınıfı
                        max_fall_confidence = conf
                        fall_detected = True
            
            return fall_detected, max_fall_confidence
            
        except Exception as e:
            logging.error(f"Sonuç analizi hatası: {str(e)}")
            return False, 0.0
    
    def get_detection_visualization(self, frame):
        """
        Tespit sonuçlarını görüntü üzerinde gösterir.
        
        Args:
            frame (numpy.ndarray): İşlenecek kare
            
        Returns:
            numpy.ndarray: Tespit kutuları çizilmiş görüntü
        """
        if not self.is_model_loaded or self.model is None:
            return frame
            
        try:
            # Frame'i işle
            processed_frame = self._preprocess_frame(frame)
            if processed_frame is None:
                return frame
            
            # YOLOv11 tespitlerini al (düşük güven eşiği ile göster)
            with torch.no_grad():
                results = self.model.predict(
                    processed_frame, 
                    conf=0.3,  # Düşük güven eşiği ile göster
                    verbose=False,
                    device=self.device
                )
            
            # Orijinal frame kopyasını oluştur
            annotated_frame = frame.copy()
            
            # Tespitleri çiz
            if results and len(results) > 0:
                result = results[0]
                
                if hasattr(result, 'boxes') and result.boxes is not None:
                    for box in result.boxes:
                        # Kutu koordinatlarını al
                        if hasattr(box, 'xyxy'):
                            x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]
                            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                            
                            # Koordinatları orijinal frame boyutuna ölçekle
                            h, w = frame.shape[:2]
                            x1 = int(x1 * w / FRAME_WIDTH)
                            y1 = int(y1 * h / FRAME_HEIGHT)
                            x2 = int(x2 * w / FRAME_WIDTH)
                            y2 = int(y2 * h / FRAME_HEIGHT)
                            
                            # Sınıf ve güven değerini al
                            cls = int(box.cls.item())
                            conf = float(box.conf.item())
                            
                            # Sınıf adını belirle
                            class_name = self.class_names[cls] if cls < len(self.class_names) else f"Class {cls}"
                            
                            # Rengi belirle (düşme: kırmızı, normal: yeşil)
                            color = (0, 0, 255) if cls == 1 else (0, 255, 0)
                            thickness = 3 if cls == 1 else 2
                            
                            # Dikdörtgen çiz
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
                            
                            # Etiket ekle
                            label = f"{class_name}: {conf:.2f}"
                            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                            
                            # Etiket arka planı
                            cv2.rectangle(annotated_frame, 
                                        (x1, y1 - label_size[1] - 10), 
                                        (x1 + label_size[0], y1), 
                                        color, -1)
                            
                            # Etiket metni
                            cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return annotated_frame
            
        except Exception as e:
            logging.error(f"Görselleştirme oluşturulurken hata: {str(e)}")
            return frame
    
    def get_model_info(self):
        """Model bilgilerini döndürür."""
        info = {
            "model_loaded": self.is_model_loaded,
            "model_path": MODEL_PATH,
            "device": str(self.device),
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "frame_size": f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
            "class_names": self.class_names,
            "total_detections": self.total_detections,
            "process_interval": self.process_interval
        }
        
        if self.total_detections > 0:
            info["avg_inference_time"] = f"{(self.total_inference_time / self.total_detections)*1000:.2f}ms"
            info["min_inference_time"] = f"{self.min_inference_time*1000:.2f}ms"
            info["max_inference_time"] = f"{self.max_inference_time*1000:.2f}ms"
        
        return info