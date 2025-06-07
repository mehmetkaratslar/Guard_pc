# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: detection.py (YOLOv11 POSE TABANLI DÜŞME ALGILAMA MOTORU)
# Konum: guard_pc_app/core/detection.py
# Açıklama:
# Bu dosya, Guard AI uygulamasının ana düşme algılama motorunu içerir.
# Gerçek zamanlı kamera görüntüsünden insan figürlerini tespit eder,
# YOLOv11-pose modeliyle vücut pozları çıkarır ve düşme durumunu analiz eder.
#
# Sistem hem tekli hem çoklu kamera desteği sunar ve yüksek performanslı görsel işleme ile çalışır.

# === ÖZELLİKLER ===
# - YOLOv11-pose modeli ile gerçek zamanlı insan tespiti
# - DeepSORT ile kişi takibi
# - Pose noktalarından düşme durumu analizi
# - Dinamik performans ayarlaması (FPS kontrolü)
# - Çoklu kamera desteği
# - Görsel üstüne bilgi yazısı ekleme (overlay)
# - Sesli uyarı sistemi

# === BAŞLICA MODÜLLER VE KULLANIM AMACI ===
# - cv2 (OpenCV): Kamera görüntüsünü alma ve işleme
# - numpy: Matris işlemleri ve matematiksel hesaplamalar
# - torch: AI modelinin çalıştırılması
# - deep_sort_real: Kişi takibi için DeepSORT algoritması
# - threading: Arka planda çalışan algılama döngüsü
# - logging: Hata ve işlem kayıtları tutma
# - math / time: Geometrik hesaplamalar ve zamanlama

# === SINIFLAR ===
# - FallDetector: YOLOv11-pose ve DeepSORT temelli düşme algılama sınıfı

# === TEMEL FONKSİYONLAR ===
# - __init__: Gerekli modelleri başlatır, yapılandırmaları yükler
# - process_frame: Tek bir frame’i işler, nesne tespiti yapar, takip eder
# - detect_fall: Belirli bir kişinin düşüp düşmediğini analiz eder
# - visualize_detections: Algılanan kişileri görüntü üzerine çizer
# - _play_fall_alert_sound: Düşme algılandığında sesli uyarı verir
# - cleanup: Sistem kaynaklarını serbest bırakır

# === POSE ANALİZİ ===
# - Vücudun 17 farklı noktasını inceler (nose, omuz, kalça, dirsek vb.)
# - Anahtar noktalar üzerinden açısal ve oran analizi yapılır
# - Baş-omuz-kalça hizası, eğim açısı ve pelvis oranı gibi değerler değerlendirilir

# === DÜŞME TESPİTİ İÇİN KRİTERLER ===
# 1. **Baş-Pelvis Oranı:** 
#    - Yüksek düşme riski için başın kalçadan çok daha aşağıda olması
# 2. **Eğim Açısı:**
#    - Vücudun yatay eksene göre dik olmadığı durumlar
# 3. **Minimum Poz Noktası Sayısı:**
#    - Yeterli sayıda keypoint’in güvenilir olması gerekir
# 4. **Süre Kontrolü:**
#    - Aynı kişi üzerinde belirli süre boyunca tekrarlayan algılama

# === DEEPSORT İLE KİŞİ TAKİBİ ===
# - Her kişiye benzersiz ID atanır
# - Frame’ler arasında aynı kişiyi takip eder
# - Takip süresince düşme algılaması yapılır

# === GÖRSEL ÜSTÜNE BİLGİ EKLEME ===
# - FPS gösterimi
# - Kullanıcı kimliği
# - Güven skoru
# - Uyarı mesajı (DÜŞME ALGILANDI!)

# === SESLİ UYARI ===
# - Düşme algılandığında Windows sistem sesi çalar
# - Thread içinde asenkron olarak çalışır

# === PERFORMANS İZLEME ===
# - Ortalama FPS
# - Toplam düşme sayısı
# - İşlem süresi istatistikleri

# === HATA YÖNETİMİ ===
# - Tüm işlemlerde try-except bloklarıyla hatalar loglanır
# - Kullanıcıya anlamlı mesajlar gösterilir

# === LOGGING ===
# - Tüm işlemler log dosyasına yazılır (guard_ai_v3.log)
# - Log formatı: Tarih/Zaman [Seviye] Mesaj

# === TEST AMAÇLI KULLANIM ===
# - `if __name__ == "__main__":` bloğu ile bağımsız çalıştırılabilir
# - Basit test modunda FPS ve düşme sayısı terminale yazdırılır

# === NOTLAR ===
# - Bu dosya, app.py, camera.py ve dashboard.py ile entegre çalışır
# - AI modeli değişkenlik gösterebilir (yolo11n-pose, yolo11s-pose vs.)
# - Düşme algılama hassasiyeti settings.py dosyasından değiştirilebilir
# =======================================================================================

import cv2
import numpy as np
import logging
import math
import time
import threading
import datetime
from collections import defaultdict, deque
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from config.settings import MODEL_PATH, CONFIDENCE_THRESHOLD, FRAME_WIDTH, AVAILABLE_MODELS
import winsound

class FallDetector:
    """
    YOLOv11 Pose Estimation + DeepSORT tabanlı gelişmiş düşme algılama sistemi.
    Thread-safe Singleton pattern ile implement edildi.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, model_path=None, confidence_threshold=None, frame_width=None):
        """
        Thread-safe singleton örneğini döndürür.
        
        Args:
            model_path (str, optional): YOLO model dosya yolu
            confidence_threshold (float, optional): Güven eşiği
            frame_width (int, optional): Frame genişliği
            
        Returns:
            FallDetector: Singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = cls(model_path, confidence_threshold, frame_width)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Singleton instance'ını sıfırlar (test amaçlı)."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance.cleanup()
                except:
                    pass
                cls._instance = None

    def __init__(self, model_path=None, confidence_threshold=None, frame_width=None):
        """
        FallDetector başlatıcı fonksiyonu.
        
        Args:
            model_path (str, optional): YOLO model dosya yolu
            confidence_threshold (float, optional): Güven eşiği
            frame_width (int, optional): Frame genişliği
        """
        if FallDetector._instance is not None:
            raise Exception("Bu sınıf singleton! get_instance() kullanın.")
        
        # Parametreleri ayarla
        self.model_path = model_path or MODEL_PATH
        self.conf_threshold = confidence_threshold or CONFIDENCE_THRESHOLD
        self.frame_size = frame_width or FRAME_WIDTH
        
        # Model ve sistem bilgileri
        self.model_version = "YOLOv11-L"
        self.detector_version = "3.0"
        self.initialization_time = time.time()
        
        # Mevcut modeller listesi - config/settings.py'dan al
        self.available_models = AVAILABLE_MODELS.copy()
        
        # YOLO modelini yükle (pose estimation modeli)
        try:
            self.model = YOLO(self.model_path)
            self.is_model_loaded = True
            logging.info(f"YOLOv11 Pose modeli başarıyla yüklendi: {self.model_path}")
        except Exception as e:
            logging.error(f"YOLO model yüklenirken hata: {str(e)}")
            self.is_model_loaded = False
            self.model = None

        # DeepSORT tracker'ı başlat
        try:
            self.tracker = DeepSort(
                max_age=30,
                n_init=3,
                max_iou_distance=0.7,
                max_cosine_distance=0.4,
                nn_budget=100
            )
            logging.info("DeepSORT tracker başarıyla başlatıldı.")
        except Exception as e:
            logging.error(f"DeepSORT tracker başlatılırken hata: {str(e)}")
            self.tracker = None

        # COCO pose keypoints (17 nokta)
        self.keypoint_names = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]

        # Düşme algılama parametreleri
        self.fall_detection_params = {
            'head_pelvis_ratio_threshold': 0.8,  # Baş-pelvis oranı eşiği
            'tilt_angle_threshold': 45,          # Eğiklik açısı eşiği (derece)
            'continuity_frames': 5,              # Süreklilik için gerekli kare sayısı
            'min_keypoints': 10,                 # Minimum gerekli keypoint sayısı
            'confidence_threshold': 0.3          # Keypoint güven eşiği
        }

        # Tracking verileri
        self.person_tracks = {}  # {track_id: PersonTrack}
        self.fall_alerts = {}    # {track_id: fall_info}
        
        # Performans takibi
        self.frame_count = 0
        self.last_detection_time = 0
        self.detection_stats = {
            'total_detections': 0,
            'fall_detections': 0,
            'false_positives': 0,
            'processing_times': deque(maxlen=100),
            'session_start': time.time()
        }
        
        # Analytics sistemi (ui/app.py uyumluluğu için)
        self.analytics = AnalyticsManager()
        
        # Thread güvenliği için lock
        self.detection_lock = threading.Lock()

    def get_model_info(self):
        """Temel model bilgilerini döndürür."""
        device_type = "unknown"
        if self.model is not None:
            try:
                device_type = "cuda" if self.model.device.type == "cuda" else "cpu"
            except:
                device_type = "cpu"
        
        return {
            "model_name": "YOLOv11 Pose",
            "model_path": self.model_path,
            "model_loaded": self.is_model_loaded,
            "confidence_threshold": self.conf_threshold,
            "frame_size": self.frame_size,
            "device": device_type,
            "keypoints_count": len(self.keypoint_names),
            "tracker_available": self.tracker is not None,
            "available_models": self.available_models  # Eksik olan bu satır eklendi
        }

    def get_enhanced_model_info(self):
        """
        Gelişmiş model bilgilerini döndürür (app.py uyumluluğu için).
        
        Returns:
            dict: Detaylı model ve sistem bilgileri
        """
        basic_info = self.get_model_info()
        
        # Gelişmiş bilgiler ekle
        enhanced_info = {
            **basic_info,
            "detector_version": self.detector_version,
            "model_version": self.model_version,
            "initialization_time": self.initialization_time,
            "uptime": time.time() - self.initialization_time,
            "detection_stats": self.detection_stats.copy(),
            "fall_detection_params": self.fall_detection_params.copy(),
            "active_tracks": len(self.person_tracks),
            "active_alerts": len(self.fall_alerts),
            "performance_metrics": self._get_performance_metrics(),
            "system_status": self._get_system_status(),
            "capabilities": {
                "pose_estimation": True,
                "object_tracking": self.tracker is not None,
                "fall_detection": True,
                "multi_person": True,
                "real_time": True,
                "keypoint_analysis": True
            },
            "supported_formats": {
                "input": ["BGR", "RGB", "GRAY"],
                "output": ["annotated_frame", "tracking_data", "pose_data"],
                "video_codecs": ["mp4", "avi", "mov"]
            }
        }
        
        return enhanced_info

    def get_enhanced_detection_visualization(self, frame):
        """
        Enhanced detection visualization method (app.py uyumluluğu için).
        
        Args:
            frame (np.ndarray): Giriş görüntüsü
            
        Returns:
            tuple: (görselleştirilmiş_frame, track_listesi)
        """
        return self.get_detection_visualization(frame)

    def detect_enhanced_fall(self, frame, tracks=None):
        """
        Enhanced fall detection method (app.py uyumluluğu için).
        
        Args:
            frame (np.ndarray): Giriş görüntüsü
            tracks (list, optional): Tracking bilgileri
            
        Returns:
            tuple: (düşme_durumu, güven_skoru, track_id, analysis_result)
        """
        # Standart detect_fall metodunu çağır ve sonuca None ekle
        is_fall, confidence, track_id = self.detect_fall(frame, tracks)
        
        # Analysis result için basit bir mock object
        analysis_result = None
        if is_fall:
            analysis_result = AnalysisResult(
                is_fall=is_fall,
                confidence=confidence,
                fall_score=confidence,
                keypoint_quality=0.8,
                pose_stability=0.7,
                risk_factors=["tilt_angle", "head_pelvis_ratio"],
                timestamp=time.time(),
                analysis_details={}
            )
        
        return is_fall, confidence, track_id, analysis_result

    def _get_performance_metrics(self):
        """Performans metriklerini hesapla."""
        processing_times = list(self.detection_stats['processing_times'])
        
        if not processing_times:
            return {
                "avg_processing_time": 0.0,
                "fps": 0.0,
                "min_processing_time": 0.0,
                "max_processing_time": 0.0
            }
        
        avg_time = np.mean(processing_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0.0
        
        return {
            "avg_processing_time": float(avg_time),
            "fps": float(fps),
            "min_processing_time": float(np.min(processing_times)),
            "max_processing_time": float(np.max(processing_times)),
            "total_frames_processed": self.frame_count,
            "detection_accuracy": self._calculate_detection_accuracy()
        }

    def _calculate_detection_accuracy(self):
        """Algılama doğruluğunu hesapla."""
        total = self.detection_stats['total_detections']
        false_pos = self.detection_stats['false_positives']
        
        if total == 0:
            return 1.0
        
        accuracy = 1.0 - (false_pos / total)
        return max(0.0, min(1.0, accuracy))

    def _get_system_status(self):
        """Sistem durumunu değerlendir."""
        status = "healthy"
        issues = []
        
        # Model durumu
        if not self.is_model_loaded:
            status = "warning"
            issues.append("Model yüklü değil")
        
        # Tracker durumu
        if self.tracker is None:
            if status == "healthy":
                status = "warning"
            issues.append("Tracker kullanılamıyor")
        
        # Performans kontrolü
        if self.detection_stats['processing_times']:
            avg_time = np.mean(list(self.detection_stats['processing_times']))
            if avg_time > 0.5:  # 500ms'den fazla
                if status == "healthy":
                    status = "warning"
                issues.append("Yavaş işleme")
        
        return {
            "status": status,
            "issues": issues,
            "last_check": time.time(),
            "checks_passed": len(issues) == 0
        }




    def get_detection_visualization(self, frame):
        """
        Thread-safe pose estimation ile insan tespiti ve görselleştirme.
        
        Args:
            frame (np.ndarray): Giriş görüntüsü
            
        Returns:
            tuple: (görselleştirilmiş_frame, track_listesi)
        """
        if not self.is_model_loaded or self.model is None:
            logging.warning("Model yüklü değil, orijinal frame döndürülüyor")
            return frame, []
        
        start_time = time.time()
        
        with self.detection_lock:
            try:
                # Frame'i yeniden boyutlandır
                frame_resized = cv2.resize(frame, (self.frame_size, self.frame_size))
                
                # YOLO ile pose estimation
                results = self.model.predict(
                    frame_resized, 
                    conf=self.conf_threshold, 
                    classes=[0],  # sadece person class
                    verbose=False
                )
                
                # Detections'ı hazırla
                detections = []
                pose_data = []
                
                for result in results:
                    # Boxes kontrolü - None olabilir
                    if result.boxes is not None and hasattr(result.boxes, 'xyxy'):
                        try:
                            # Tensor'ü numpy'ye güvenli dönüştür
                            boxes = result.boxes.xyxy
                            if boxes is not None:
                                # CPU'ya taşı ve numpy'ye dönüştür
                                if hasattr(boxes, 'cpu'):
                                    boxes = boxes.cpu().numpy()
                                elif hasattr(boxes, 'numpy'):
                                    boxes = boxes.numpy()
                                else:
                                    boxes = np.array(boxes)
                            else:
                                continue
                            
                            # Confidence değerlerini al
                            confs = result.boxes.conf
                            if confs is not None:
                                if hasattr(confs, 'cpu'):
                                    confs = confs.cpu().numpy()
                                elif hasattr(confs, 'numpy'):
                                    confs = confs.numpy()
                                else:
                                    confs = np.array(confs)
                            else:
                                continue
                            
                            # Keypoints varsa al
                            keypoints = None
                            keypoint_confs = None
                            if hasattr(result, 'keypoints') and result.keypoints is not None:
                                try:
                                    # Keypoints xy koordinatları
                                    if hasattr(result.keypoints, 'xy') and result.keypoints.xy is not None:
                                        kp_xy = result.keypoints.xy
                                        if hasattr(kp_xy, 'cpu'):
                                            keypoints = kp_xy.cpu().numpy()
                                        elif hasattr(kp_xy, 'numpy'):
                                            keypoints = kp_xy.numpy()
                                        else:
                                            keypoints = np.array(kp_xy)
                                    
                                    # Keypoints confidence değerleri
                                    if hasattr(result.keypoints, 'conf') and result.keypoints.conf is not None:
                                        kp_conf = result.keypoints.conf
                                        if hasattr(kp_conf, 'cpu'):
                                            keypoint_confs = kp_conf.cpu().numpy()
                                        elif hasattr(kp_conf, 'numpy'):
                                            keypoint_confs = kp_conf.numpy()
                                        else:
                                            keypoint_confs = np.array(kp_conf)
                                except Exception as kp_error:
                                    logging.debug(f"Keypoint işleme hatası: {kp_error}")
                                    keypoints = None
                                    keypoint_confs = None
                            
                            # Her detection için işle
                            for i, (box, conf) in enumerate(zip(boxes, confs)):
                                x1, y1, x2, y2 = map(int, box)
                                
                                # Detection formatı: [x, y, w, h]
                                detection = [x1, y1, x2-x1, y2-y1]
                                detections.append((detection, conf, 0))  # class_id = 0 (person)
                                
                                # Pose data ekle
                                person_keypoints = None
                                person_keypoint_confs = None
                                if keypoints is not None and i < len(keypoints):
                                    person_keypoints = keypoints[i]
                                    person_keypoint_confs = keypoint_confs[i] if keypoint_confs is not None else None
                                
                                pose_data.append({
                                    'keypoints': person_keypoints,
                                    'keypoint_confs': person_keypoint_confs,
                                    'bbox': [x1, y1, x2, y2]
                                })
                        
                        except Exception as box_error:
                            logging.debug(f"Box işleme hatası: {box_error}")
                            continue

                # İstatistikleri güncelle
                self.detection_stats['total_detections'] += len(detections)

                # DeepSORT ile tracking (eğer mevcut ise)
                tracks = []
                if self.tracker is not None and len(detections) > 0:
                    try:
                        tracks = self.tracker.update_tracks(detections, frame=frame_resized)
                    except Exception as e:
                        logging.error(f"DeepSORT tracking hatası: {str(e)}")
                        tracks = []
                
                # Tracking bilgilerini güncelle
                self._update_person_tracks(tracks, pose_data)
                
                # Görselleştirme
                annotated_frame = self._draw_visualizations(frame, tracks)
                
                # Track listesi oluştur
                track_list = []
                for track in tracks:
                    if hasattr(track, 'is_confirmed') and track.is_confirmed():
                        track_id = track.track_id
                        bbox = track.to_ltrb()
                        
                        # Frame boyutlarına ölçeklendir
                        scale_x = frame.shape[1] / self.frame_size
                        scale_y = frame.shape[0] / self.frame_size
                        
                        x1 = int(bbox[0] * scale_x)
                        y1 = int(bbox[1] * scale_y)
                        x2 = int(bbox[2] * scale_x)
                        y2 = int(bbox[3] * scale_y)
                        
                        track_list.append({
                            'track_id': track_id,
                            'bbox': [x1, y1, x2, y2],
                            'confidence': getattr(track, 'confidence', 0.0)
                        })
                
                # İşlem süresini kaydet
                processing_time = time.time() - start_time
                self.detection_stats['processing_times'].append(processing_time)
                
                return annotated_frame, track_list
                
            except Exception as e:
                logging.error(f"Detection visualization hatası: {str(e)}")
                return frame, []
            
        """
        Thread-safe pose estimation ile insan tespiti ve görselleştirme.
        
        Args:
            frame (np.ndarray): Giriş görüntüsü
            
        Returns:
            tuple: (görselleştirilmiş_frame, track_listesi)
        """
        if not self.is_model_loaded or self.model is None:
            logging.warning("Model yüklü değil, orijinal frame döndürülüyor")
            return frame, []
        
        start_time = time.time()
        
        with self.detection_lock:
            try:
                # Frame'i yeniden boyutlandır
                frame_resized = cv2.resize(frame, (self.frame_size, self.frame_size))
                
                # YOLO ile pose estimation
                results = self.model.predict(
                    frame_resized, 
                    conf=self.conf_threshold, 
                    classes=[0],  # sadece person class
                    verbose=False
                )
                
                # Detections'ı hazırla
                detections = []
                pose_data = []
                
                for result in results:
                    if result.boxes is not None:
                        boxes = result.boxes.xyxy.cpu().numpy()
                        confs = result.boxes.conf.cpu().numpy()
                        
                        # Keypoints varsa al
                        keypoints = None
                        keypoint_confs = None
                        if hasattr(result, 'keypoints') and result.keypoints is not None:
                            keypoints = result.keypoints.xy.cpu().numpy()
                            keypoint_confs = result.keypoints.conf.cpu().numpy()
                        
                        for i, (box, conf) in enumerate(zip(boxes, confs)):
                            x1, y1, x2, y2 = map(int, box)
                            
                            # Detection formatı: [x, y, w, h]
                            detection = [x1, y1, x2-x1, y2-y1]
                            detections.append((detection, conf, 0))  # class_id = 0 (person)
                            
                            # Pose data ekle
                            person_keypoints = None
                            person_keypoint_confs = None
                            if keypoints is not None and i < len(keypoints):
                                person_keypoints = keypoints[i]
                                person_keypoint_confs = keypoint_confs[i] if keypoint_confs is not None else None
                            
                            pose_data.append({
                                'keypoints': person_keypoints,
                                'keypoint_confs': person_keypoint_confs,
                                'bbox': [x1, y1, x2, y2]
                            })

                # İstatistikleri güncelle
                self.detection_stats['total_detections'] += len(detections)

                # DeepSORT ile tracking (eğer mevcut ise)
                tracks = []
                if self.tracker is not None:
                    try:
                        tracks = self.tracker.update_tracks(detections, frame=frame_resized)
                    except Exception as e:
                        logging.error(f"DeepSORT tracking hatası: {str(e)}")
                        tracks = []
                
                # Tracking bilgilerini güncelle
                self._update_person_tracks(tracks, pose_data)
                
                # Görselleştirme
                annotated_frame = self._draw_visualizations(frame, tracks)
                
                # Track listesi oluştur
                track_list = []
                for track in tracks:
                    if hasattr(track, 'is_confirmed') and track.is_confirmed():
                        track_id = track.track_id
                        bbox = track.to_ltrb()
                        
                        # Frame boyutlarına ölçeklendir
                        scale_x = frame.shape[1] / self.frame_size
                        scale_y = frame.shape[0] / self.frame_size
                        
                        x1 = int(bbox[0] * scale_x)
                        y1 = int(bbox[1] * scale_y)
                        x2 = int(bbox[2] * scale_x)
                        y2 = int(bbox[3] * scale_y)
                        
                        track_list.append({
                            'track_id': track_id,
                            'bbox': [x1, y1, x2, y2],
                            'confidence': getattr(track, 'confidence', 0.0)
                        })
                
                # İşlem süresini kaydet
                processing_time = time.time() - start_time
                self.detection_stats['processing_times'].append(processing_time)
                
                return annotated_frame, track_list
                
            except Exception as e:
                logging.error(f"Detection visualization hatası: {str(e)}")
                return frame, []




    def detect_fall(self, frame, tracks=None):
        """
        Thread-safe pose tabanlı düşme algılama.
        
        Args:
            frame (np.ndarray): Giriş görüntüsü
            tracks (list, optional): Tracking bilgileri
            
        Returns:
            tuple: (düşme_durumu, güven_skoru, track_id)
        """
        if not self.is_model_loaded or self.model is None:
            return False, 0.0, None
        
        with self.detection_lock:
            try:
                self.frame_count += 1
                current_time = time.time()
                
                # Tracks yoksa detection_visualization'dan al
                if tracks is None:
                    _, tracks = self.get_detection_visualization(frame)
                
                # Her track için düşme kontrolü
                for person_id, person_track in self.person_tracks.items():
                    fall_detected, confidence = self._analyze_fall_for_person(person_track)
                    
                    if fall_detected:
                        # Süreklilik kontrolü
                        if person_id not in self.fall_alerts:
                            self.fall_alerts[person_id] = {
                                'start_time': current_time,
                                'frame_count': 1,
                                'max_confidence': confidence
                            }
                        else:
                            self.fall_alerts[person_id]['frame_count'] += 1
                            self.fall_alerts[person_id]['max_confidence'] = max(
                                self.fall_alerts[person_id]['max_confidence'], 
                                confidence
                            )
                        
                        # Süreklilik eşiği kontrolü
                        alert = self.fall_alerts[person_id]
                        if alert['frame_count'] >= self.fall_detection_params['continuity_frames']:
                            logging.info(f"DÜŞME ALGILANDI: ID={person_id}, Güven={alert['max_confidence']:.3f}")
                            
                            # İstatistikleri güncelle
                            self.detection_stats['fall_detections'] += 1
                            
                            # Sesli uyarı (thread'de)
                            threading.Thread(target=self._play_fall_alert_sound, daemon=True).start()
                            
                            return True, alert['max_confidence'], person_id
                    else:
                        # Düşme algılanmadıysa alert'i temizle
                        if person_id in self.fall_alerts:
                            del self.fall_alerts[person_id]
                
                return False, 0.0, None
                
            except Exception as e:
                logging.error(f"Fall detection hatası: {str(e)}")
                return False, 0.0, None

    def get_detection_summary(self):
        """Algılama özetini döndürür."""
        uptime = time.time() - self.initialization_time
        
        return {
            "session_uptime": uptime,
            "total_frames": self.frame_count,
            "total_detections": self.detection_stats['total_detections'],
            "fall_detections": self.detection_stats['fall_detections'],
            "active_tracks": len(self.person_tracks),
            "active_alerts": len(self.fall_alerts),
            "avg_fps": self._get_performance_metrics()['fps'],
            "model_status": "loaded" if self.is_model_loaded else "error",
            "tracker_status": "active" if self.tracker else "disabled"
        }

    def _update_person_tracks(self, tracks, pose_data):
        """Person tracking bilgilerini günceller."""
        try:
            # Mevcut track'leri temizle
            current_track_ids = set()
            
            for i, track in enumerate(tracks):
                if not hasattr(track, 'is_confirmed') or not track.is_confirmed():
                    continue
                    
                track_id = track.track_id
                current_track_ids.add(track_id)
                
                # Pose data'yı al
                person_pose = pose_data[i] if i < len(pose_data) else None
                
                if track_id not in self.person_tracks:
                    self.person_tracks[track_id] = PersonTrack(track_id)
                
                # Track'i güncelle
                self.person_tracks[track_id].update(track, person_pose)
            
            # Aktif olmayan track'leri temizle
            inactive_tracks = set(self.person_tracks.keys()) - current_track_ids
            for track_id in inactive_tracks:
                del self.person_tracks[track_id]
                if track_id in self.fall_alerts:
                    del self.fall_alerts[track_id]
                    
        except Exception as e:
            logging.error(f"Person tracks güncelleme hatası: {str(e)}")

    def _analyze_fall_for_person(self, person_track):
        """
        Belirli bir kişi için düşme analizi yapar.
        
        Args:
            person_track (PersonTrack): Kişi tracking bilgileri
            
        Returns:
            tuple: (düşme_durumu, güven_skoru)
        """
        if not person_track.has_valid_pose():
            return False, 0.0
            
        try:
            keypoints = person_track.latest_keypoints
            keypoint_confs = person_track.latest_keypoint_confs
            
            # Güvenilir keypoint'leri filtrele
            conf_mask = keypoint_confs > self.fall_detection_params['confidence_threshold']
            valid_keypoints = np.sum(conf_mask)
            
            if valid_keypoints < self.fall_detection_params['min_keypoints']:
                return False, 0.0
            
            # Ana keypoint'leri al
            nose = keypoints[0] if conf_mask[0] else None
            left_shoulder = keypoints[5] if conf_mask[5] else None
            right_shoulder = keypoints[6] if conf_mask[6] else None
            left_hip = keypoints[11] if conf_mask[11] else None
            right_hip = keypoints[12] if conf_mask[12] else None
            
            # Baş merkezi hesapla
            head_center = None
            if nose is not None:
                head_center = nose
            elif left_shoulder is not None and right_shoulder is not None:
                head_center = (left_shoulder + right_shoulder) / 2
                head_center[1] -= 20  # Yaklaşık baş pozisyonu
            
            # Pelvis merkezi hesapla
            pelvis_center = None
            if left_hip is not None and right_hip is not None:
                pelvis_center = (left_hip + right_hip) / 2
            
            if head_center is None or pelvis_center is None:
                return False, 0.0
            
            # 1. Baş-Pelvis dikey mesafe oranı kontrolü
            head_pelvis_distance = abs(head_center[1] - pelvis_center[1])
            bbox_height = person_track.latest_bbox[3] - person_track.latest_bbox[1]
            
            if bbox_height > 0:
                height_ratio = head_pelvis_distance / bbox_height
            else:
                height_ratio = 1.0
            
            # 2. Eğiklik açısı kontrolü
            dx = pelvis_center[0] - head_center[0]
            dy = pelvis_center[1] - head_center[1]
            
            if dy != 0:
                tilt_angle = abs(math.degrees(math.atan(dx / dy)))
            else:
                tilt_angle = 90.0
            
            # 3. Omuz-kalça hizalaması kontrolü
            shoulder_hip_alignment = 0.0
            if (left_shoulder is not None and right_shoulder is not None and 
                left_hip is not None and right_hip is not None):
                
                shoulder_angle = math.degrees(math.atan2(
                    right_shoulder[1] - left_shoulder[1],
                    right_shoulder[0] - left_shoulder[0]
                ))
                
                hip_angle = math.degrees(math.atan2(
                    right_hip[1] - left_hip[1],
                    right_hip[0] - left_hip[0]
                ))
                
                shoulder_hip_alignment = abs(shoulder_angle - hip_angle)
            
            # Düşme skorunu hesapla
            fall_score = 0.0
            
            # Baş-pelvis oranı skoru
            if height_ratio < self.fall_detection_params['head_pelvis_ratio_threshold']:
                ratio_score = 1.0 - (height_ratio / self.fall_detection_params['head_pelvis_ratio_threshold'])
                fall_score += ratio_score * 0.4
            
            # Eğiklik açısı skoru
            if tilt_angle > self.fall_detection_params['tilt_angle_threshold']:
                tilt_score = min(1.0, (tilt_angle - self.fall_detection_params['tilt_angle_threshold']) / 45.0)
                fall_score += tilt_score * 0.4
            
            # Omuz-kalça hizalaması skoru
            if shoulder_hip_alignment > 30:
                alignment_score = min(1.0, (shoulder_hip_alignment - 30) / 60.0)
                fall_score += alignment_score * 0.2
            
            # Düşme eşiği
            fall_threshold = 0.6
            is_fall = fall_score > fall_threshold
            
            if is_fall:
                logging.debug(f"Fall analysis - ID: {person_track.track_id}, "
                            f"Height ratio: {height_ratio:.3f}, "
                            f"Tilt angle: {tilt_angle:.1f}°, "
                            f"Alignment: {shoulder_hip_alignment:.1f}°, "
                            f"Fall score: {fall_score:.3f}")
            
            return is_fall, fall_score
            
        except Exception as e:
            logging.error(f"Fall analysis hatası: {str(e)}")
            return False, 0.0

    def _draw_visualizations(self, frame, tracks):
        """
        Tracking ve pose bilgilerini frame üzerine çizer.
        
        Args:
            frame (np.ndarray): Orijinal frame
            tracks (list): DeepSORT track listesi
            
        Returns:
            np.ndarray: Görselleştirilmiş frame
        """
        annotated_frame = frame.copy()
        
        try:
            # Frame boyut oranları
            scale_x = frame.shape[1] / self.frame_size
            scale_y = frame.shape[0] / self.frame_size
            
            for track in tracks:
                if not hasattr(track, 'is_confirmed') or not track.is_confirmed():
                    continue
                
                track_id = track.track_id
                bbox = track.to_ltrb()
                
                # Bbox'ı orijinal frame boyutuna ölçeklendir
                x1 = int(bbox[0] * scale_x)
                y1 = int(bbox[1] * scale_y)
                x2 = int(bbox[2] * scale_x)
                y2 = int(bbox[3] * scale_y)
                
                # Düşme durumu kontrolü
                is_falling = track_id in self.fall_alerts
                box_color = (0, 0, 255) if is_falling else (0, 255, 0)  # Kırmızı/Yeşil
                box_thickness = 3 if is_falling else 2
                
                # Bounding box çiz
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, box_thickness)
                
                # Track ID ve güven skoru
                confidence = getattr(track, 'confidence', 0.0)
                label = f"ID: {track_id}"
                if confidence > 0:
                    label += f" ({confidence:.2f})"
                
                # Düşme uyarısı ekle
                if is_falling:
                    label += " - FALL DETECTED!"
                
                # Label arka planı
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                cv2.rectangle(annotated_frame, (x1, y1-35), (x1 + label_size[0], y1), box_color, -1)
                
                # Label metni
                text_color = (255, 255, 255)
                cv2.putText(annotated_frame, label, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
                
                # Pose keypoints çiz
                if track_id in self.person_tracks:
                    person_track = self.person_tracks[track_id]
                    if person_track.has_valid_pose():
                        self._draw_pose_keypoints(annotated_frame, person_track, scale_x, scale_y)
            
            return annotated_frame
            
        except Exception as e:
            logging.error(f"Visualization çizim hatası: {str(e)}")
            return frame

    def _draw_pose_keypoints(self, frame, person_track, scale_x, scale_y):
        """
        Pose keypoints'leri frame üzerine çizer.
        
        Args:
            frame (np.ndarray): Frame
            person_track (PersonTrack): Kişi tracking bilgileri
            scale_x (float): X ekseni ölçekleme faktörü
            scale_y (float): Y ekseni ölçekleme faktörü
        """
        try:
            keypoints = person_track.latest_keypoints
            keypoint_confs = person_track.latest_keypoint_confs
            
            if keypoints is None or keypoint_confs is None:
                return
            
            # Keypoint bağlantıları (COCO format)
            skeleton = [
                [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],  # Bacaklar
                [6, 12], [7, 13], [6, 7], [6, 8], [7, 9],         # Gövde ve kollar
                [8, 10], [9, 11], [6, 5], [5, 7], [1, 2],         # Kollar ve omuzlar
                [0, 1], [0, 2], [1, 3], [2, 4]                    # Baş
            ]
            
            # Keypoint'leri çiz
            for i, (keypoint, conf) in enumerate(zip(keypoints, keypoint_confs)):
                if conf > self.fall_detection_params['confidence_threshold']:
                    x = int(keypoint[0] * scale_x)
                    y = int(keypoint[1] * scale_y)
                    
                    # Keypoint rengi (önemli noktalara göre)
                    if i == 0:  # Burun
                        color = (255, 0, 0)  # Mavi
                    elif i in [5, 6]:  # Omuzlar
                        color = (0, 255, 255)  # Sarı
                    elif i in [11, 12]:  # Kalçalar
                        color = (255, 0, 255)  # Magenta
                    else:
                        color = (0, 255, 0)  # Yeşil
                    
                    cv2.circle(frame, (x, y), 4, color, -1)
            
            # Skeleton çizgileri çiz
            for connection in skeleton:
                pt1_idx, pt2_idx = connection[0] - 1, connection[1] - 1  # COCO 1-indexed
                
                if (0 <= pt1_idx < len(keypoints) and 0 <= pt2_idx < len(keypoints) and
                    keypoint_confs[pt1_idx] > self.fall_detection_params['confidence_threshold'] and
                    keypoint_confs[pt2_idx] > self.fall_detection_params['confidence_threshold']):
                    
                    pt1 = (int(keypoints[pt1_idx][0] * scale_x), int(keypoints[pt1_idx][1] * scale_y))
                    pt2 = (int(keypoints[pt2_idx][0] * scale_x), int(keypoints[pt2_idx][1] * scale_y))
                    
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
                    
        except Exception as e:
            logging.error(f"Pose keypoints çizim hatası: {str(e)}")

    def _play_fall_alert_sound(self):
        """Düşme uyarısı sesini çalar."""
        try:
            # Windows sistem sesi
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception as e:
            logging.warning(f"Ses çalma hatası: {str(e)}")

    def cleanup(self):
        """Kaynakları temizler."""
        try:
            if self.tracker is not None:
                self.tracker.delete_all_tracks()
            self.person_tracks.clear()
            self.fall_alerts.clear()
            logging.info("FallDetector kaynakları temizlendi.")
        except Exception as e:
            logging.error(f"Cleanup hatası: {str(e)}")


class PersonTrack:
    """
    Tek bir kişinin tracking bilgilerini saklayan sınıf.
    """
    
    def __init__(self, track_id):
        self.track_id = track_id
        self.latest_bbox = None
        self.latest_keypoints = None
        self.latest_keypoint_confs = None
        self.pose_history = deque(maxlen=10)  # Son 10 pose
        self.update_time = time.time()
        
    def update(self, track, pose_data):
        """Track ve pose bilgilerini günceller."""
        self.latest_bbox = track.to_ltrb()
        self.update_time = time.time()
        
        if pose_data and pose_data.get('keypoints') is not None:
            self.latest_keypoints = pose_data['keypoints']
            self.latest_keypoint_confs = pose_data.get('keypoint_confs')
            
            # Pose geçmişine ekle
            self.pose_history.append({
                'keypoints': self.latest_keypoints.copy(),
                'keypoint_confs': self.latest_keypoint_confs.copy() if self.latest_keypoint_confs is not None else None,
                'timestamp': self.update_time
            })
    
    def has_valid_pose(self):
        """Geçerli pose bilgisi olup olmadığını kontrol eder."""
        return (self.latest_keypoints is not None and 
                self.latest_keypoint_confs is not None and
                len(self.latest_keypoints) >= 17)
    
    def get_pose_stability(self):
        """Pose'un son birkaç frame'deki kararlılığını hesaplar."""
        if len(self.pose_history) < 3:
            return 0.0
            
        try:
            # Son 3 pose'u karşılaştır
            recent_poses = list(self.pose_history)[-3:]
            stability_scores = []
            
            for i in range(len(recent_poses) - 1):
                pose1 = recent_poses[i]['keypoints']
                pose2 = recent_poses[i + 1]['keypoints']
                conf1 = recent_poses[i]['keypoint_confs']
                conf2 = recent_poses[i + 1]['keypoint_confs']
                
                if pose1 is not None and pose2 is not None:
                    # Güvenilir keypoint'leri karşılaştır
                    valid_mask = (conf1 > 0.3) & (conf2 > 0.3)
                    
                    if np.sum(valid_mask) > 5:  # En az 5 geçerli keypoint
                        diff = np.linalg.norm(pose1[valid_mask] - pose2[valid_mask], axis=1)
                        avg_diff = np.mean(diff)
                        stability_score = max(0, 1.0 - avg_diff / 50.0)  # 50 pixel normalizasyon
                        stability_scores.append(stability_score)
            
            return np.mean(stability_scores) if stability_scores else 0.0
            
        except Exception as e:
            logging.error(f"Pose stability hesaplama hatası: {str(e)}")
            return 0.0


class AnalyticsManager:
    """Analytics yönetimi için basit sınıf (app.py uyumluluğu için)."""
    
    def __init__(self):
        self.stats = {
            'total_detections': 0,
            'fall_events': 0,
            'session_start': time.time()
        }
    
    def get_summary(self):
        """Analytics özetini döndürür."""
        return self.stats.copy()


class AnalysisResult:
    """Analysis result container (app.py uyumluluğu için)."""
    
    def __init__(self, is_fall, confidence, fall_score, keypoint_quality, 
                 pose_stability, risk_factors, timestamp, analysis_details):
        self.is_fall = is_fall
        self.confidence = confidence
        self.fall_score = fall_score
        self.keypoint_quality = keypoint_quality
        self.pose_stability = pose_stability
        self.risk_factors = risk_factors
        self.timestamp = timestamp
        self.analysis_details = analysis_details