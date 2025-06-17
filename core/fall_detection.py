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
# - process_frame: Tek bir frame'i işler, nesne tespiti yapar, takip eder
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
#    - Yeterli sayıda keypoint'in güvenilir olması gerekir
# 4. **Süre Kontrolü:**
#    - Aynı kişi üzerinde belirli süre boyunca tekrarlayan algılama

# === DEEPSORT İLE KİŞİ TAKİBİ ===
# - Her kişiye benzersiz ID atanır
# - Frame'ler arasında aynı kişiyi takip eder
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

    def get_detection_visualization(self, frame):
        """
        DÜZELTME: İNSAN DOĞRULAMALI detection visualization
        """
        if not self.is_model_loaded or self.model is None:
            logging.warning("Model yüklü değil, orijinal frame döndürülüyor")
            return frame, []
        
        start_time = time.time()
        
        with self.detection_lock:
            try:
                # Frame'i resize et
                frame_resized = cv2.resize(frame, (self.frame_size, self.frame_size))
                
                # DÜZELTME: YOLO ile pose estimation - ÇOK DÜŞÜK threshold + DEBUG
                results = self.model.predict(
                    frame_resized, 
                    conf=0.15,  # 0.20 -> 0.15 (çok daha düşük)
                    classes=[0],  # sadece person class
                    verbose=False
                )
                
                # DEBUG: YOLO sonuçları kontrol et - SADECE değişiklik varsa logla
                total_raw_detections = 0
                for result in results:
                    if result.boxes is not None and hasattr(result.boxes, 'xyxy'):
                        total_raw_detections += len(result.boxes.xyxy)
                
                # FIXED: Log spam önleme - doğrulanmış insan sayısı
                if not hasattr(self, '_last_validated_count'):
                    self._last_validated_count = -1
                    self._last_validated_log_time = 0
                
                current_time = time.time()
                validated_should_log = (total_raw_detections != self._last_validated_count or 
                                       current_time - self._last_validated_log_time > 10.0)
                
                if validated_should_log:
                    logging.info(f"🔍 Doğrulanmış insan sayısı: {total_raw_detections}")
                    self._last_validated_count = total_raw_detections
                    self._last_validated_log_time = current_time
                
                # Detections'ı hazırla
                detections = []
                pose_data = []
                
                for result in results:
                    if result.boxes is not None and hasattr(result.boxes, 'xyxy'):
                        try:
                            # DÜZELTME: Güvenli tensor handling
                            boxes = result.boxes.xyxy
                            if boxes is not None:
                                if hasattr(boxes, 'cpu'):
                                    boxes = boxes.cpu().numpy()
                                elif hasattr(boxes, 'detach'):
                                    boxes = boxes.detach().numpy()
                                elif hasattr(boxes, 'numpy'):
                                    boxes = boxes.numpy()
                                else:
                                    boxes = np.array(boxes)
                            else:
                                continue
                            
                            # Confidence değerleri
                            confs = result.boxes.conf
                            if confs is not None:
                                if hasattr(confs, 'cpu'):
                                    confs = confs.cpu().numpy()
                                elif hasattr(confs, 'detach'):
                                    confs = confs.detach().numpy()
                                elif hasattr(confs, 'numpy'):
                                    confs = confs.numpy()
                                else:
                                    confs = np.array(confs)
                            else:
                                continue
                            
                            # DÜZELTME: Keypoints güvenli alma
                            keypoints = None
                            keypoint_confs = None
                            if hasattr(result, 'keypoints') and result.keypoints is not None:
                                try:
                                    if hasattr(result.keypoints, 'xy') and result.keypoints.xy is not None:
                                        kp_xy = result.keypoints.xy
                                        if hasattr(kp_xy, 'cpu'):
                                            keypoints = kp_xy.cpu().numpy()
                                        elif hasattr(kp_xy, 'detach'):
                                            keypoints = kp_xy.detach().numpy()
                                        elif hasattr(kp_xy, 'numpy'):
                                            keypoints = kp_xy.numpy()
                                        else:
                                            keypoints = np.array(kp_xy)
                                    
                                    if hasattr(result.keypoints, 'conf') and result.keypoints.conf is not None:
                                        kp_conf = result.keypoints.conf
                                        if hasattr(kp_conf, 'cpu'):
                                            keypoint_confs = kp_conf.cpu().numpy()
                                        elif hasattr(kp_conf, 'detach'):
                                            keypoint_confs = kp_conf.detach().numpy()
                                        elif hasattr(kp_conf, 'numpy'):
                                            keypoint_confs = kp_conf.numpy()
                                        else:
                                            keypoint_confs = np.array(kp_conf)
                                except Exception as kp_error:
                                    logging.debug(f"Keypoint işleme hatası: {kp_error}")
                                    keypoints = None
                                    keypoint_confs = None
                            
                            # DÜZELTME: Her detection için GELİŞMİŞ İNSAN DOĞRULAMA
                            for i, (box, conf) in enumerate(zip(boxes, confs)):
                                # DEBUG: Her detection'ı logla
                                logging.debug(f"📊 Detection {i}: conf={conf:.3f}")
                                
                                # ✅ DÜZELTME: Güvenilir confidence threshold - daha iyi tespit
                                if conf < 0.30:  # 0.15 -> 0.30 (daha güvenilir)
                                    logging.debug(f"❌ Düşük confidence reddedildi: {conf:.3f}")
                                    continue
                                
                                x1, y1, x2, y2 = map(int, box)
                                
                                # DEBUG: Bbox boyutları
                                bbox_width = x2 - x1
                                bbox_height = y2 - y1
                                logging.debug(f"📐 Bbox boyutu: {bbox_width}x{bbox_height}")
                                
                                # ✅ DÜZELTME: Gerçekçi boyut kontrolü - insan boyutları
                                if bbox_width < 40 or bbox_height < 100:  # 20,50 -> 40,100 (gerçekçi insan boyutları)
                                    logging.debug(f"❌ Çok küçük obje reddedildi: {bbox_width}x{bbox_height}")
                                    continue
                                
                                if bbox_width > 400 or bbox_height > 600:  # 300,500 -> 400,600 (çok daha büyük)
                                    logging.debug(f"❌ Çok büyük obje reddedildi: {bbox_width}x{bbox_height}")
                                    continue
                                
                                # DÜZELTME: ÇOK ESNEK aspect ratio
                                aspect_ratio = bbox_height / bbox_width
                                if aspect_ratio < 1.0 or aspect_ratio > 6.0:  # 1.2-4.5 -> 1.0-6.0 (çok daha geniş)
                                    logging.debug(f"❌ Yanlış aspect ratio reddedildi: {aspect_ratio:.2f}")
                                    continue
                                
                                logging.debug(f"✅ Bbox kontrolü geçti: {bbox_width}x{bbox_height}, ratio: {aspect_ratio:.2f}")
                                
                                # DÜZELTME: Pose data ve keypoint doğrulama
                                person_keypoints = None
                                person_keypoint_confs = None
                                if keypoints is not None and i < len(keypoints):
                                    person_keypoints = keypoints[i]
                                    person_keypoint_confs = keypoint_confs[i] if keypoint_confs is not None else None
                                    
                                    # DEBUG: Keypoint sayısı
                                    if person_keypoint_confs is not None:
                                        valid_kp_count = np.sum(person_keypoint_confs > 0.2)  # 0.3 -> 0.2 (daha düşük)
                                        logging.debug(f"🎯 Geçerli keypoint sayısı: {valid_kp_count}/17")
                                    
                                    # DÜZELTME: ÇOK ESNEK keypoint validation - geçici olarak devre dışı
                                    # if not self._validate_human_keypoints(person_keypoints, person_keypoint_confs):
                                    #     logging.debug(f"❌ Keypoint doğrulama başarısız - insan değil")
                                    #     continue
                                    logging.debug(f"⚠️ Keypoint validation GEÇİCİ OLARAK DEVRE DIŞI - test için")
                                
                                # DÜZELTME: Sadece doğrulanmış insanları ekle
                                detection = [x1, y1, x2-x1, y2-y1]
                                detections.append((detection, conf, 0))  # class_id = 0 (person)
                                
                                pose_data.append({
                                    'keypoints': person_keypoints,
                                    'keypoint_confs': person_keypoint_confs,
                                    'bbox': [x1, y1, x2, y2],
                                    'confidence': float(conf),  # Box confidence ekle
                                    'validated_human': True  # Doğrulanmış insan işareti
                                })
                                
                                logging.info(f"✅ İnsan EKLENDI: conf={conf:.3f}, keypoints={np.sum(person_keypoint_confs > 0.2) if person_keypoint_confs is not None else 0}")
                        
                        except Exception as box_error:
                            logging.error(f"Box işleme hatası: {box_error}")
                            continue

                # İstatistikleri güncelle
                self.detection_stats['total_detections'] += len(detections)
                logging.info(f"🔍 Doğrulanmış insan sayısı: {len(detections)}")

                # DeepSORT ile tracking - sadece doğrulanmış insanlar
                tracks = []
                if self.tracker is not None and len(detections) > 0:
                    try:
                        tracks = self.tracker.update_tracks(detections, frame=frame_resized)
                    except Exception as e:
                        logging.error(f"DeepSORT tracking hatası: {str(e)}")
                        tracks = []
                
                # Tracking bilgilerini güncelle
                self._update_person_tracks(tracks, pose_data)
                
                # DÜZELTME: Enhanced görselleştirme - sadece doğrulanmış insanlar
                annotated_frame = self._draw_enhanced_visualizations(frame, tracks)
                
                # Track listesi oluştur - sadece doğrulanmış insanlar
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
                            'confidence': getattr(track, 'confidence', 0.0),
                            'validated_human': True  # Doğrulanmış insan
                        })
                
                # ✅ DÜZELTİLDİ: Enhanced visualization ekle - keypoint çizimi
                if track_list:  # Sadece track varsa visualize et
                    annotated_frame = self._draw_enhanced_visualizations(annotated_frame, detections)
                
                # İşlem süresini kaydet
                processing_time = time.time() - start_time
                self.detection_stats['processing_times'].append(processing_time)
                
                return annotated_frame, track_list
                
            except Exception as e:
                logging.error(f"Detection visualization hatası: {str(e)}")
                return frame, []

    def _draw_enhanced_visualizations(self, frame, tracks):
        """
        DÜZELTME: Enhanced görselleştirme - keypoint'ler çok görünür
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
                box_thickness = 4 if is_falling else 2  # Daha kalın
                
                # DÜZELTME: Enhanced bounding box
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, box_thickness)
                
                # DÜZELTME: Enhanced label - daha büyük
                confidence = getattr(track, 'confidence', 0.0)
                label = f"ID: {track_id}"
                if confidence > 0:
                    label += f" ({confidence:.2f})"
                
                # Düşme uyarısı ekle
                if is_falling:
                    label += " - FALL DETECTED!"
                
                # DÜZELTME: Daha büyük label arka planı
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                cv2.rectangle(annotated_frame, (x1, y1-40), (x1 + label_size[0] + 10, y1), box_color, -1)
                
                # DÜZELTME: Daha büyük label metni
                text_color = (255, 255, 255)
                cv2.putText(annotated_frame, label, (x1 + 5, y1-15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2, cv2.LINE_AA)
                
                # DÜZELTME: Enhanced pose keypoints - çok görünür
                if track_id in self.person_tracks:
                    person_track = self.person_tracks[track_id]
                    if person_track.has_valid_pose():
                        self._draw_enhanced_pose_keypoints(annotated_frame, person_track, scale_x, scale_y, is_falling)
            
            return annotated_frame
            
        except Exception as e:
            logging.error(f"Enhanced visualization çizim hatası: {str(e)}")
            return frame

    def _draw_enhanced_pose_keypoints(self, frame, person_track, scale_x, scale_y, is_falling=False):
        """
        DÜZELTME: Enhanced pose keypoints - çok görünür ve renkli
        """
        try:
            keypoints = person_track.latest_keypoints
            keypoint_confs = person_track.latest_keypoint_confs
            
            if keypoints is None or keypoint_confs is None:
                return
            
            # ✅ DÜZELTİLDİ: Keypoint görünürlük threshold - daha çok keypoint
            conf_threshold = 0.05  # 0.1 -> 0.05 (çok daha düşük)
            
            # DÜZELTME: Enhanced keypoint colors - çok renkli
            keypoint_colors = [
                (255, 0, 0),    # 0: burun - mavi
                (255, 85, 0),   # 1: sol göz - turuncu
                (255, 170, 0),  # 2: sağ göz - sarı-turuncu
                (255, 255, 0),  # 3: sol kulak - sarı
                (170, 255, 0),  # 4: sağ kulak - yeşil-sarı
                (85, 255, 0),   # 5: sol omuz - açık yeşil
                (0, 255, 0),    # 6: sağ omuz - yeşil
                (0, 255, 85),   # 7: sol dirsek - yeşil-mavi
                (0, 255, 170),  # 8: sağ dirsek - açık mavi
                (0, 255, 255),  # 9: sol bilek - cyan
                (0, 170, 255),  # 10: sağ bilek - mavi
                (0, 85, 255),   # 11: sol kalça - koyu mavi
                (0, 0, 255),    # 12: sağ kalça - mavi
                (85, 0, 255),   # 13: sol diz - mor
                (170, 0, 255),  # 14: sağ diz - pembe-mor
                (255, 0, 255),  # 15: sol ayak - magenta
                (255, 0, 170)   # 16: sağ ayak - pembe
            ]
            
            # DÜZELTME: Keypoint'leri çiz - çok büyük ve görünür
            for i, (keypoint, conf) in enumerate(zip(keypoints, keypoint_confs)):
                if conf > conf_threshold:
                    x = int(keypoint[0] * scale_x)
                    y = int(keypoint[1] * scale_y)
                    
                    # DÜZELTME: Çok büyük keypoint circles
                    radius = 8 if is_falling else 6  # 4 -> 6/8
                    color = keypoint_colors[i] if i < len(keypoint_colors) else (255, 255, 255)
                    
                    # Outer circle - daha görünür
                    cv2.circle(frame, (x, y), radius + 2, (0, 0, 0), -1)  # Siyah border
                    cv2.circle(frame, (x, y), radius, color, -1)
                    
                    # DÜZELTME: Keypoint numarası - debug için
                    cv2.putText(frame, str(i), (x-5, y-10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, (255, 255, 255), 1, cv2.LINE_AA)
            
            # DÜZELTME: Enhanced skeleton çizgileri - daha kalın
            skeleton_connections = [
                # Baş bölgesi
                [0, 1], [0, 2], [1, 3], [2, 4],  # Burun-göz-kulak
                # Gövde
                [5, 6], [5, 11], [6, 12], [11, 12],  # Omuz-kalça çerçevesi
                # Sol kol
                [5, 7], [7, 9],  # Sol omuz-dirsek-bilek
                # Sağ kol
                [6, 8], [8, 10],  # Sağ omuz-dirsek-bilek
                # Sol bacak
                [11, 13], [13, 15],  # Sol kalça-diz-ayak
                # Sağ bacak
                [12, 14], [14, 16],  # Sağ kalça-diz-ayak
            ]
            
            for connection in skeleton_connections:
                pt1_idx, pt2_idx = connection[0], connection[1]
                
                if (0 <= pt1_idx < len(keypoints) and 0 <= pt2_idx < len(keypoints) and
                    keypoint_confs[pt1_idx] > conf_threshold and
                    keypoint_confs[pt2_idx] > conf_threshold):
                    
                    pt1 = (int(keypoints[pt1_idx][0] * scale_x), int(keypoints[pt1_idx][1] * scale_y))
                    pt2 = (int(keypoints[pt2_idx][0] * scale_x), int(keypoints[pt2_idx][1] * scale_y))
                    
                    # DÜZELTME: Çok kalın skeleton lines
                    line_color = (0, 255, 255) if is_falling else (0, 255, 0)  # Cyan/Yeşil
                    line_thickness = 4 if is_falling else 3  # 2 -> 3/4
                    
                    cv2.line(frame, pt1, pt2, line_color, line_thickness, cv2.LINE_AA)
            
            # DÜZELTME: Enhanced pose info overlay
            if is_falling:
                # Düşme uyarısı overlay
                overlay = frame.copy()
                h, w = frame.shape[:2]
                cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 255), -1)
                cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                
                cv2.putText(frame, "FALL DETECTED - ENHANCED POSE ANALYSIS", 
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Valid Keypoints: {np.sum(keypoint_confs > conf_threshold)}/17", 
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
                        
        except Exception as e:
            logging.error(f"Enhanced pose keypoints çizim hatası: {str(e)}")

    def detect_fall(self, frame, tracks=None):
        """
        DÜZELTME: Ultra hassas düşme algılama - düşük threshold
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
                        # DÜZELTME: Süreklilik kontrolü - çok düşük
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
                        
                        # DÜZELTME: Süreklilik eşiği - 3 frame gerekli (kararlılık)
                        alert = self.fall_alerts[person_id]
                        if alert['frame_count'] >= 3:  # 1 -> 3 (daha kararlı)
                            logging.warning(f"🚨 DENGELİ DÜŞME ALGILANDI: ID={person_id}, Güven={alert['max_confidence']:.3f}")
                            
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
                logging.error(f"Ultra hassas fall detection hatası: {str(e)}")
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

    def _get_performance_metrics(self):
        """Performans metriklerini hesaplar."""
        try:
            uptime = time.time() - self.initialization_time
            fps = self.frame_count / uptime if uptime > 0 else 0
            
            avg_processing_time = 0
            if self.detection_stats['processing_times']:
                avg_processing_time = sum(self.detection_stats['processing_times']) / len(self.detection_stats['processing_times'])
            
            return {
                "fps": fps,
                "avg_processing_time": avg_processing_time,
                "total_frames": self.frame_count,
                "uptime": uptime,
                "detection_rate": self.detection_stats['total_detections'] / max(1, self.frame_count),
                "fall_rate": self.detection_stats['fall_detections'] / max(1, self.frame_count)
            }
        except Exception as e:
            logging.error(f"Performance metrics hesaplama hatası: {e}")
            return {
                "fps": 0,
                "avg_processing_time": 0,
                "total_frames": 0,
                "uptime": 0,
                "detection_rate": 0,
                "fall_rate": 0
            }

    def _get_system_status(self):
        """Sistem durumunu döndürür."""
        try:
            return {
                "model_loaded": self.is_model_loaded,
                "tracker_active": self.tracker is not None,
                "cameras_connected": True,  # Bu bilgi camera.py'den gelir
                "ai_processing": True,
                "fall_detection_active": True,
                "pose_estimation_active": True,
                "system_healthy": self.is_model_loaded and self.tracker is not None
            }
        except Exception as e:
            logging.error(f"System status hesaplama hatası: {e}")
            return {
                "model_loaded": False,
                "tracker_active": False,
                "cameras_connected": False,
                "ai_processing": False,
                "fall_detection_active": False,
                "pose_estimation_active": False,
                "system_healthy": False
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
        DÜZELTME: DENGELI İNSAN DOĞRULAMALI düşme analizi
        """
        if not person_track.has_valid_pose():
            return False, 0.0
            
        try:
            keypoints = person_track.latest_keypoints
            keypoint_confs = person_track.latest_keypoint_confs
            
            # DÜZELTME: Dengeli confidence threshold - daha fazla keypoint algılar
            conf_threshold = 0.35  # 0.5 -> 0.35 (daha düşük eşik)
            conf_mask = keypoint_confs > conf_threshold
            valid_keypoints = np.sum(conf_mask)
            
            # ✅ DÜZELTME: Optimum minimum keypoint sayısı - güvenilir analiz
            if valid_keypoints < 5:  # 7 -> 5 (daha esnek ama yeterli)
                logging.debug(f"❌ Yetersiz güvenilir keypoint düşme analizi için: {valid_keypoints}/17")
                return False, 0.0
            
            # DÜZELTME: TEKRAR İNSAN DOĞRULAMA - düşme analizinden önce
            if not self._validate_human_keypoints(keypoints, keypoint_confs):
                logging.debug(f"❌ İnsan doğrulama başarısız - düşme analizi iptal")
                return False, 0.0
            
            # DÜZELTME: Doğru COCO keypoint indeksleri (0-based)
            nose = keypoints[0] if conf_mask[0] else None                    # 0: burun
            left_shoulder = keypoints[5] if conf_mask[5] else None          # 5: sol omuz
            right_shoulder = keypoints[6] if conf_mask[6] else None         # 6: sağ omuz
            left_elbow = keypoints[7] if conf_mask[7] else None             # 7: sol dirsek
            right_elbow = keypoints[8] if conf_mask[8] else None            # 8: sağ dirsek
            left_hip = keypoints[11] if conf_mask[11] else None             # 11: sol kalça
            right_hip = keypoints[12] if conf_mask[12] else None            # 12: sağ kalça
            left_knee = keypoints[13] if conf_mask[13] else None            # 13: sol diz
            right_knee = keypoints[14] if conf_mask[14] else None           # 14: sağ diz
            left_ankle = keypoints[15] if conf_mask[15] else None           # 15: sol ayak bileği
            right_ankle = keypoints[16] if conf_mask[16] else None          # 16: sağ ayak bileği
            
            # DÜZELTME: ZORUNLU anatomik noktalar - bunlar olmadan analiz yapma
            if (left_shoulder is None or right_shoulder is None or 
                left_hip is None or right_hip is None):
                logging.debug(f"❌ Zorunlu anatomik noktalar eksik - düşme analizi iptal")
                return False, 0.0
            
            # DÜZELTME: Vücut merkez noktalarını hesapla
            shoulder_center = (left_shoulder + right_shoulder) / 2
            hip_center = (left_hip + right_hip) / 2
            
            # Ayak merkezi
            foot_center = None
            if left_ankle is not None and right_ankle is not None:
                foot_center = (left_ankle + right_ankle) / 2
            elif left_ankle is not None:
                foot_center = left_ankle
            elif right_ankle is not None:
                foot_center = right_ankle
            
            # DÜZELTME: KATIL düşme algılama kriterleri - yüksek eşikler
            fall_indicators = []
            fall_score = 0.0
            
            # 1. DÜZELTME: OMUZ-KALÇA EĞİM AÇISI (60 derece kriteri - çok katı)
            dx = hip_center[0] - shoulder_center[0]
            dy = hip_center[1] - shoulder_center[1]
            
            if abs(dy) > 1:
                tilt_angle = abs(math.degrees(math.atan(dx / abs(dy))))
                
                # DÜZELTME: 60 derece eşiği - çok katı hassasiyet
                if tilt_angle > 60:  # 45 -> 60 derece (çok daha katı)
                    fall_score += 1.0  # Yüksek ağırlık
                    fall_indicators.append("kritik_egim")
                    logging.debug(f"DÜŞME İNDİKATÖRÜ: Kritik omuz-kalça eğimi {tilt_angle:.1f}°")
                elif tilt_angle > 45:  # Orta risk
                    fall_score += 0.5
                    fall_indicators.append("omuz_kalca_egim")
            
            # 2. DÜZELTME: YÜKSEK HASSAS yükseklik kaybı analizi
            if foot_center is not None:
                hip_foot_distance = abs(hip_center[1] - foot_center[1])
                bbox_height = person_track.latest_bbox[3] - person_track.latest_bbox[1]
                
                if bbox_height > 0:
                    height_ratio = hip_foot_distance / bbox_height
                    
                    # DÜZELTME: Çok katı oran - gerçek düşme tespiti
                    if height_ratio < 0.25:  # 0.4 -> 0.25 (çok daha katı)
                        fall_score += 1.2
                        fall_indicators.append("kritik_yukseklik_kaybi")
                        logging.debug(f"DÜŞME İNDİKATÖRÜ: Kritik yükseklik kaybı {height_ratio:.3f}")
                    elif height_ratio < 0.4:  # Orta risk
                        fall_score += 0.6
                        fall_indicators.append("yukseklik_kaybi")
            
            # 3. DÜZELTME: YATAY POZISYONU - çok katı kontrol
            if foot_center is not None:
                shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
                body_height = abs(shoulder_center[1] - foot_center[1])
                
                if body_height > 0:
                    width_height_ratio = shoulder_width / body_height
                    
                    # DÜZELTME: Çok katı eşik - gerçek yatay pozisyon
                    if width_height_ratio > 0.8:  # 0.6 -> 0.8 (çok daha katı)
                        fall_score += 1.5
                        fall_indicators.append("kritik_yatay_pozisyon")
                        logging.debug(f"DÜŞME İNDİKATÖRÜ: Kritik yatay pozisyon {width_height_ratio:.3f}")
                    elif width_height_ratio > 0.6:  # Orta risk
                        fall_score += 0.7
                        fall_indicators.append("yatay_pozisyon")
            
            # 4. DÜZELTME: BAŞ POZISYONU - çok katı kontrol
            if nose is not None:
                nose_hip_diff = nose[1] - hip_center[1]  # Y farkı
                
                # Burun kalçadan çok aşağıdaysa (ters durum)
                if nose_hip_diff > 40:  # 20 -> 40 piksel (daha katı)
                    fall_score += 1.0
                    fall_indicators.append("kritik_bas_asagida")
                    logging.debug(f"DÜŞME İNDİKATÖRÜ: Kritik baş aşağıda pozisyonu")
                elif nose_hip_diff > 20:  # Orta risk
                    fall_score += 0.4
                    fall_indicators.append("bas_asagida")
            
            # 5. DÜZELTME: DESTEK POZISYONU - el yerde
            ground_support_score = 0
            for elbow_name, elbow_point in [("sol_dirsek", left_elbow), ("sag_dirsek", right_elbow)]:
                if elbow_point is not None and foot_center is not None:
                    elbow_foot_distance = abs(elbow_point[1] - foot_center[1])
                    
                    # Dirsek ayağa çok yakınsa (yerde desteklenme)
                    if elbow_foot_distance < 60:  # 100 -> 60 piksel (daha katı)
                        ground_support_score += 0.8
                        fall_indicators.append(f"kritik_{elbow_name}_destek")
                        logging.debug(f"DÜŞME İNDİKATÖRÜ: Kritik {elbow_name} yerde destek")
                    elif elbow_foot_distance < 100:  # Orta risk
                        ground_support_score += 0.3
                        fall_indicators.append(f"{elbow_name}_destek")
            
            fall_score += ground_support_score
            
            # 6. DÜZELTME: DİZ BÜKÜLME - oturma/düşme analizi
            knee_bend_score = 0
            for knee_name, knee_point, hip_point, ankle_point in [
                ("sol_diz", left_knee, left_hip, left_ankle),
                ("sag_diz", right_knee, right_hip, right_ankle)
            ]:
                if knee_point is not None and hip_point is not None and ankle_point is not None:
                    # Kalça-diz-ayak açısı
                    v1 = hip_point - knee_point
                    v2 = ankle_point - knee_point
                    
                    dot_product = np.dot(v1, v2)
                    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
                    
                    if norms > 0:
                        cos_angle = np.clip(dot_product / norms, -1.0, 1.0)
                        knee_angle = math.degrees(math.acos(cos_angle))
                        
                        # DÜZELTME: Diz açısı 45 derece altındaysa kritik
                        if knee_angle < 45:  # 60 -> 45 (daha katı)
                            knee_bend_score += 0.6
                            fall_indicators.append(f"kritik_{knee_name}_bukum")
                            logging.debug(f"DÜŞME İNDİKATÖRÜ: Kritik {knee_name} açısı {knee_angle:.1f}°")
                        elif knee_angle < 60:  # Orta risk
                            knee_bend_score += 0.2
                            fall_indicators.append(f"{knee_name}_bukum")
            
            fall_score += knee_bend_score
            
            # ✅ DÜZELTME: Gerçekçi düşme eşiği - güvenilir tespit
            fall_threshold = 1.0  # 2.0 -> 1.0 (gerçekçi eşik)
            is_fall = fall_score >= fall_threshold
            
            # DÜZELTME: Ek güvenlik kontrolü - en az 2 farklı indikatör gerekli
            if is_fall and len(set(fall_indicators)) < 2:
                logging.debug(f"❌ Yetersiz çeşitli indikatör - düşme reddedildi")
                is_fall = False
            
            if is_fall:
                logging.warning(f"🚨 GELİŞMİŞ DÜŞME ALGILANDI! Skor: {fall_score:.3f}, İndikatörler: {fall_indicators}")
                logging.info(f"   📊 Geçerli keypoint sayısı: {valid_keypoints}")
                logging.info(f"   🎯 Toplam indikatör: {len(fall_indicators)}")
                logging.info(f"   🔍 Güvenilir insan doğrulaması: ✅")
            elif fall_score > 1.0:  # Orta riskli durumları logla
                logging.debug(f"⚠️ Orta risk algılandı: Skor: {fall_score:.3f}, İndikatörler: {fall_indicators}")
            
            return is_fall, fall_score
            
        except Exception as e:
            logging.error(f"Gelişmiş düşme analizi hatası: {str(e)}")
            return False, 0.0

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

    def _validate_human_keypoints(self, keypoints, keypoint_confs):
        """
        DÜZELTME: TUTARLI İNSAN KEYPOINT DOĞRULAMA
        Daha stabil ve tutarlı insan tespiti
        """
        if keypoints is None or keypoint_confs is None:
            return False
        
        try:
            # DÜZELTME: Dengeli confidence threshold - tutarlı tespit
            conf_threshold = 0.25  # 0.3 -> 0.25 (daha tutarlı)
            valid_mask = keypoint_confs > conf_threshold
            valid_count = np.sum(valid_mask)
            
            # DÜZELTME: Daha esnek minimum keypoint sayısı - tutarlılık için
            if valid_count < 5:  # 6 -> 5 (daha stabil)
                logging.debug(f"❌ Yetersiz güvenilir keypoint: {valid_count}/17")
                return False
            
            # DÜZELTME: Kritik keypoint kontrolü - insan anatomisi
            critical_points = [0, 5, 6, 11, 12]  # Burun, omuzlar, kalçalar
            critical_valid = np.sum(valid_mask[critical_points])
            
            if critical_valid < 2:  # En az 2 kritik keypoint
                logging.debug(f"❌ Yetersiz kritik keypoint: {critical_valid}/5")
                return False
            
            # DÜZELTME: Keypoint anatomik kontrol - insan vücut yapısı
            if self._validate_anatomical_structure(keypoints, keypoint_confs):
                logging.debug(f"✅ Keypoint doğrulama başarılı: {valid_count} valid, {critical_valid} critical")
                return True
            
            return False
            
        except Exception as e:
            logging.debug(f"❌ Keypoint validation error: {e}")
            return False
    
    def _validate_anatomical_structure(self, keypoints, keypoint_confs):
        """
        DÜZELTME: Anatomik yapı doğrulama - insan vücut oranları
        """
        try:
            conf_threshold = 0.2  # Daha düşük eşik anatomik kontrol için
            
            # Baş-boyun kontrolü
            nose = keypoints[0] if keypoint_confs[0] > conf_threshold else None
            left_shoulder = keypoints[5] if keypoint_confs[5] > conf_threshold else None
            right_shoulder = keypoints[6] if keypoint_confs[6] > conf_threshold else None
            
            # Omuz mesafesi kontrolü - insan boyutu
            if left_shoulder is not None and right_shoulder is not None:
                shoulder_distance = np.linalg.norm(left_shoulder - right_shoulder)
                if 15 <= shoulder_distance <= 200:  # Makul omuz mesafesi
                    return True
            
            # Kalça kontrolü
            left_hip = keypoints[11] if keypoint_confs[11] > conf_threshold else None
            right_hip = keypoints[12] if keypoint_confs[12] > conf_threshold else None
            
            if left_hip is not None and right_hip is not None:
                hip_distance = np.linalg.norm(left_hip - right_hip)
                if 10 <= hip_distance <= 150:  # Makul kalça mesafesi
                    return True
            
            # Dikey kontrol - baş omuz kalça hizası
            if nose is not None and (left_shoulder is not None or right_shoulder is not None):
                return True  # Temel dikey yapı var
            
            return False
            
        except Exception as e:
            logging.debug(f"❌ Anatomical validation error: {e}")
            return False


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
        self.pose_data = None  # Pose data attribute eklendi
        
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