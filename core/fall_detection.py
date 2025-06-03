# =======================================================================================
# 📄 Dosya Adı: fall_detection.py
# 📁 Konum: guard_pc_app/core/fall_detection.py
# 📌 Açıklama:
# YOLOv11 tabanlı gerçek zamanlı düşme algılama modülü.
# Güven eşiği optimize edildi, çerçeve kalitesi kontrolü güçlendirildi.
# Mobil uygulama için görüntüleme desteği korundu.
# 🔗 Bağlantılı Dosyalar:
# - config/settings.py: MODEL_PATH, FRAME_WIDTH, FRAME_HEIGHT
# - ui/app.py: Düşme algılama çağrısı
# - data/database.py: Olay kaydı
# - data/storage.py: Görüntü yükleme
# =======================================================================================

import torch
import numpy as np
import cv2
import logging
import os
import time
import pkg_resources
from config.settings import MODEL_PATH, FRAME_WIDTH, FRAME_HEIGHT

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
        if hasattr(FallDetector, '_instance') and FallDetector._instance is not None:
            raise RuntimeError("FallDetector zaten başlatılmış. get_instance() kullanın.")
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logging.info(f"YOLOv11 modeli şu cihazda çalışacak: {self.device}")
        
        self.model = None
        self.is_model_loaded = False
        self.class_names = None
        self.fall_class_index = None
        
        self.total_detections = 0
        self.total_inference_time = 0
        self.max_inference_time = 0
        self.min_inference_time = float('inf')
        self.last_log_time = time.time()
        self.last_process_time = 0
        self.process_interval = 0.5
        
        self.confidence_buffer = []
        self.buffer_size = 3  # Daha kararlı algılama için artırıldı
        
        self._load_model()
        FallDetector._instance = self

    def _load_model(self):
        """YOLOv11 modelini yükler."""
        try:
            logging.info(f"YOLOv11 model dosyası yükleniyor: {MODEL_PATH}")
            
            if not os.path.exists(MODEL_PATH):
                logging.error(f"Model dosyası bulunamadı: {MODEL_PATH}")
                return
            
            file_size = os.path.getsize(MODEL_PATH)
            if file_size < 1024:
                logging.error(f"Model dosyası çok küçük, muhtemelen bozuk: {file_size} bytes")
                return
            
            try:
                ultralytics_version = pkg_resources.get_distribution("ultralytics").version
                if ultralytics_version < "8.0.0":
                    logging.error(f"ultralytics sürümü eski: {ultralytics_version}. Lütfen 'pip install ultralytics>=8.0.0' ile güncelleyin.")
                    return
                logging.info(f"ultralytics sürümü: {ultralytics_version}")
            except Exception as e:
                logging.error(f"ultralytics sürüm kontrolü başarısız: {str(e)}. Lütfen 'pip install ultralytics' ile yükleyin.")
                return
            
            try:
                from ultralytics import YOLO
                
                self.model = YOLO(MODEL_PATH)
                self.model.to(self.device)
                
                if hasattr(self.model, 'names'):
                    self.class_names = self.model.names
                    logging.info(f"Model sınıf isimleri: {self.class_names}")
                    if isinstance(self.class_names, dict):
                        for idx, name in self.class_names.items():
                            if name.lower() == 'fall':
                                self.fall_class_index = idx
                                break
                    else:
                        for idx, name in enumerate(self.class_names):
                            if name.lower() == 'fall':
                                self.fall_class_index = idx
                                break
                    if self.fall_class_index is None:
                        logging.error("Modelde 'fall' sınıfı bulunamadı!")
                        return
                else:
                    logging.error("Model sınıf isimleri alınamadı!")
                    return
                
                dummy_frame = np.random.randint(0, 255, (416, 416, 3), dtype=np.uint8)
                with torch.no_grad():
                    results = self.model.predict(
                        dummy_frame,
                        verbose=False,
                        imgsz=416,
                        conf=0.5
                    )
                    if results is None or len(results) == 0:
                        logging.error("Warmup işlemi başarısız, model düzgün yüklenmedi.")
                        return
                
                logging.info(f"YOLOv11 modeli başarıyla yüklendi ve warmup tamamlandı: {MODEL_PATH}")
                self.is_model_loaded = True
                
            except ImportError:
                logging.error("ultralytics kütüphanesi bulunamadı. Lütfen 'pip install ultralytics' ile yükleyin.")
                return
            except Exception as e:
                logging.error(f"YOLOv11 model yükleme hatası: {str(e)}")
                return
                
        except Exception as e:
            logging.error(f"Model yüklenirken hata oluştu: {str(e)}")
            self.model = None
            self.is_model_loaded = False

    def reload_model(self):
        """Modeli yeniden yükler."""
        logging.info("YOLOv11 modeli yeniden yükleniyor...")
        self.model = None
        self.is_model_loaded = False
        self.fall_class_index = None
        self.class_names = None
        self._load_model()
        return self.is_model_loaded

    def detect_fall(self, frame):
        """
        YOLOv11 modelini kullanarak hızlı düşme algılama gerçekleştirir.

        Args:
            frame (numpy.ndarray): İşlenecek kare (BGR formatında)

        Returns:
            tuple: (is_fall, confidence) - Düşme algılandı mı ve olasılığı
        """
        if not self.is_model_loaded or self.model is None:
            logging.warning("YOLOv11 modeli yüklü değil, düşme algılama devre dışı.")
            return False, 0.0
        
        current_time = time.time()
        if current_time - self.last_process_time < self.process_interval:
            return False, 0.0
        
        self.last_process_time = current_time
        
        try:
            if frame is None or frame.size == 0:
                logging.warning("Geçersiz çerçeve alındı.")
                return False, 0.0
            
            # Çerçeve kalitesini kontrol et
            frame_mean = np.mean(frame)
            frame_std = np.std(frame)
            frame_sharpness = cv2.Laplacian(frame, cv2.CV_64F).var()
            logging.debug(f"Çerçeve istatistikleri: Ortalama={frame_mean:.2f}, Std={frame_std:.2f}, Netlik={frame_sharpness:.2f}")
            if frame_std < 15 or frame_sharpness < 50:
                logging.warning("Çerçeve düşük kontrastlı veya bulanık, kalite sorunlu olabilir.")
                return False, 0.0
            
            optimized_frame = cv2.resize(frame, (416, 416))
            start_time = time.time()
            
            with torch.no_grad():
                results = self.model.predict(
                    optimized_frame,
                    conf=0.6,  # Güven eşiği optimize edildi
                    verbose=False,
                    device=self.device,
                    imgsz=416,
                    half=False,
                    augment=False,
                    agnostic_nms=True,
                    max_det=10
                )
            
            is_fall, confidence = self._analyze_results(results)
            
            if is_fall:
                self.confidence_buffer.append(confidence)
                if len(self.confidence_buffer) > self.buffer_size:
                    self.confidence_buffer.pop(0)
                
                if len(self.confidence_buffer) >= self.buffer_size:
                    avg_confidence = sum(self.confidence_buffer) / len(self.confidence_buffer)
                    if avg_confidence > 0.6:  # Güven eşiği optimize edildi
                        final_confidence = avg_confidence
                        final_is_fall = True
                    else:
                        final_confidence = 0.0
                        final_is_fall = False
                else:
                    final_confidence = 0.0
                    final_is_fall = False
            else:
                self.confidence_buffer.clear()
                final_confidence = 0.0
                final_is_fall = False
            
            inference_time = time.time() - start_time
            self.total_detections += 1
            self.total_inference_time += inference_time
            self.max_inference_time = max(self.max_inference_time, inference_time)
            self.min_inference_time = min(self.min_inference_time, inference_time)
            
            if final_is_fall:
                logging.info(f"DÜŞME ALGILANDI! Güven: {final_confidence:.4f} (Süre: {inference_time*1000:.1f}ms)")
            else:
                logging.debug(f"Düşme algılanmadı: Güven: {final_confidence:.4f}")
            
            return final_is_fall, final_confidence
            
        except Exception as e:
            logging.error(f"Düşme algılanırken hata oluştu: {str(e)}")
            return False, 0.0

    def _preprocess_frame(self, frame):
        """
        Hızlı frame ön işleme.
        """
        try:
            if frame is None or frame.size == 0:
                logging.warning("Geçersiz frame alındı.")
                return None
            resized_frame = cv2.resize(frame, (416, 416))
            return resized_frame
        except Exception as e:
            logging.error(f"Frame ön işleme hatası: {str(e)}")
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
            
            result = results[0]
            if not hasattr(result, 'boxes') or result.boxes is None:
                return False, 0.0
            
            boxes = result.boxes
            max_fall_confidence = 0.0
            fall_detected = False
            
            for box in boxes:
                if hasattr(box, 'cls') and hasattr(box, 'conf'):
                    cls = int(box.cls.item())
                    conf = float(box.conf.item())
                    if cls == self.fall_class_index and conf > max_fall_confidence:
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
            processed_frame = self._preprocess_frame(frame)
            if processed_frame is None:
                return frame
            
            with torch.no_grad():
                results = self.model.predict(
                    processed_frame,
                    conf=0.3,
                    verbose=False,
                    device=self.device
                )
            
            annotated_frame = frame.copy()
            if results and len(results) > 0:
                result = results[0]
                if hasattr(result, 'boxes') and result.boxes is not None:
                    for box in result.boxes:
                        if hasattr(box, 'xyxy'):
                            x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]
                            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                            
                            h, w = frame.shape[:2]
                            x1 = int(x1 * w / FRAME_WIDTH)
                            y1 = int(y1 * h / FRAME_HEIGHT)
                            x2 = int(x2 * w / FRAME_WIDTH)
                            y2 = int(x2 * h / FRAME_HEIGHT)
                            
                            cls = int(box.cls.item())
                            conf = float(box.conf.item())
                            class_name = self.class_names[cls] if isinstance(self.class_names, list) and cls < len(self.class_names) else self.class_names.get(cls, f"Class {cls}")
                            color = (0, 0, 255) if cls == self.fall_class_index else (0, 255, 0)
                            thickness = 3 if cls == self.fall_class_index else 2
                            
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
                            label = f"{class_name}: {conf:.2f}"
                            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                            cv2.rectangle(annotated_frame, 
                                        (x1, y1 - label_size[1] - 10), 
                                        (x1 + label_size[0], y1), 
                                        color, -1)
                            cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return annotated_frame
            
        except Exception as e:
            logging.error(f"Görselleştirme oluşturulurken hata: {str(e)}")
            return frame
    
    def get_model_info(self):
        """Model bilgilerini döndürür."""
        try:
            info = {
                "model_loaded": self.is_model_loaded,
                "model_path": MODEL_PATH,
                "device": str(self.device),
                "confidence_threshold": 0.6,  # Sabit 0.6
                "frame_size": f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
                "class_names": self.class_names,
                "fall_class_index": self.fall_class_index,
                "total_detections": self.total_detections,
                "process_interval": self.process_interval
            }
            
            if self.total_detections > 0:
                info["avg_inference_time"] = f"{(self.total_inference_time / self.total_detections)*1000:.2f}ms"
                info["min_inference_time"] = f"{self.min_inference_time*1000:.2f}ms"
                info["max_inference_time"] = f"{self.max_inference_time*1000:.2f}ms"
            
            return info
        except Exception as e:
            logging.error(f"Model bilgileri alınırken hata: {str(e)}")
            return {"model_loaded": False, "error": str(e)}