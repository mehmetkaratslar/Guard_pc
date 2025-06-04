# =======================================================================================
# 📄 Dosya Adı: fall_detection.py
# 📁 Konum: guard_pc_app/core/fall_detection.py
# 📌 Açıklama:
# YOLOv11 tabanlı insan takibi ve düşme algılama sistemi.
# DeepSORT ile insan takibi yaparak her kişiye bir ID atar.
# Pose estimation ile düşme olaylarını algılar.
# Kamera görüntüsüne takip ID'leri ve kareler çizer.
#
# Özellikler:
# - YOLOv11 pose estimation (yolo11l-pose.pt) ile insan tespiti
# - DeepSORT ile gerçek zamanlı insan takibi
# - Düşme algılama: Pelvis ve baş pozisyonlarına dayalı
# - Görüntü görselleştirme: Takip ID'leri ve kareler
#
# 🔗 Bağlantılı Dosyalar:
# - ui/dashboard.py: UI entegrasyonu
# - config/settings.py: Model yolu ve ayarlar
# - utils/logger.py: Loglama
# =======================================================================================

import cv2
import numpy as np
import logging
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from config.settings import MODEL_PATH, CONFIDENCE_THRESHOLD, FRAME_WIDTH
import ultralytics

class FallDetector:
    """
    YOLOv11 ve DeepSORT kullanarak insan takibi ve düşme algılama sistemi.
    Singleton pattern ile tek bir örnek oluşturulur.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        """Singleton örneğini döndürür."""
        # Eğer örnek yoksa, yeni bir örnek oluştur
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """FallDetector başlatıcı fonksiyonu."""
        # Singleton kontrolü
        if FallDetector._instance is not None:
            raise Exception("Bu sınıf singleton! get_instance() kullanın.")
        # YOLO modelini yükle
        try:
            self.model = YOLO(MODEL_PATH)
            logging.info(f"YOLOv11 modeli başarıyla yüklendi: {MODEL_PATH}")
        except Exception as e:
            logging.error(f"YOLO model yüklenirken hata: {str(e)}")
            raise
        # DeepSORT tracker'ı başlat
        try:
            self.tracker = DeepSort(
                max_age=30, n_init=3, max_iou_distance=0.7,
                embedder=None, max_cosine_distance=0.3  # Varsayılan embedder
            )
            logging.info("DeepSORT tracker başarıyla başlatıldı.")
        except Exception as e:
            logging.error(f"DeepSORT tracker başlatılırken hata: {str(e)}", exc_info=True)
            raise
        # Ayarlar
        self.conf_threshold = CONFIDENCE_THRESHOLD
        self.frame_size = FRAME_WIDTH
        # Düşme algılama için önceki pozisyonları sakla
        self.previous_positions = {}
        # Çerçeve sayacı
        self.frame_count = 0
        self.process_interval = 0.1  # Her 0.1 saniyede bir işleme

    def get_model_info(self):
        """
        YOLOv11 modelinin bilgilerini döndürür.

        Returns:
            dict: Model sürümü, adı ve yapılandırma bilgileri.
        """
        try:
            model_info = {
                "model_name": "YOLOv11",
                "model_version": ultralytics.__version__,
                "model_path": MODEL_PATH,
                "confidence_threshold": self.conf_threshold,
                "frame_size": self.frame_size
            }
            logging.debug(f"Model bilgisi alındı: {model_info}")
            return model_info
        except Exception as e:
            logging.error(f"Model bilgisi alınırken hata: {str(e)}")
            return {}

    def get_detection_visualization(self, frame):
        """
        İnsan takibi yapar ve görüntüyü görselleştirir.

        Args:
            frame (np.ndarray): Giriş kamera görüntüsü (BGR)

        Returns:
            tuple: (Görselleştirilmiş çerçeve, takip listesi)
        """
        try:
            # Çerçeveyi yeniden boyutlandır
            frame_resized = cv2.resize(frame, (self.frame_size, self.frame_size))
            # YOLO ile insan tespiti
            results = self.model.predict(
                frame_resized, conf=self.conf_threshold, classes=[0], verbose=False
            )
            # Tespitleri al
            detections = []
            for result in results:
                boxes = result.boxes.xyxy.cpu().numpy()  # Bounding box'lar
                confs = result.boxes.conf.cpu().numpy()  # Güven skorları
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = map(int, box)
                    conf = float(confs[i])
                    detections.append(([x1, y1, x2 - x1, y2 - y1], conf, 0))
            # DeepSORT ile takip
            tracks = self.tracker.update_tracks(detections, frame=frame_resized)
            # Orijinal çerçeve boyutlarına ölçeklendirme faktörleri
            scale_x = frame.shape[1] / self.frame_size
            scale_y = frame.shape[0] / self.frame_size
            # Görselleştirme
            annotated_frame = frame.copy()
            track_list = []
            for track in tracks:
                if not track.is_confirmed():
                    continue
                track_id = track.track_id
                bbox = track.to_ltrb()
                x1, y1, x2, y2 = map(int, [bbox[0] * scale_x, bbox[1] * scale_y,
                                         bbox[2] * scale_x, bbox[3] * scale_y])
                # Kare çiz
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                # Takip ID'sini yaz
                cv2.putText(
                    annotated_frame, f"ID: {track_id}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2
                )
                track_list.append({
                    'track_id': track_id,
                    'bbox': [x1, y1, x2, y2]
                })
                logging.debug(f"Takip ID: {track_id}, Bbox: ({x1},{y1}) to ({x2},{y2})")
            return annotated_frame, track_list
        except Exception as e:
            logging.error(f"Görselleştirme sırasında hata: {str(e)}", exc_info=True)
            return frame, []

    def detect_fall(self, frame, tracks=None):
        """
        Düşme olayını algılar.

        Args:
            frame (np.ndarray): Giriş kamera görüntüsü (BGR)
            tracks (list, optional): Takip edilen kişilerin listesi. Varsa sağlanır, yoksa hesaplanır.

        Returns:
            tuple: (Düşme durumu, güven skoru, takip ID'si)
        """
        try:
            # Tracks sağlanmadıysa, get_detection_visualization ile al
            if tracks is None:
                _, tracks = self.get_detection_visualization(frame)
            # Çerçeve sayacı
            self.frame_count += 1
            # Düşme algılama için her n çerçevede bir kontrol
            if self.frame_count * self.process_interval < 1:
                return False, 0.0, None
            self.frame_count = 0
            # Çerçeveyi yeniden boyutlandır
            frame_resized = cv2.resize(frame, (self.frame_size, self.frame_size))
            # YOLO ile pose estimation
            results = self.model.predict(
                frame_resized, conf=self.conf_threshold, classes=[0], verbose=False
            )
            # Düşme algılama
            for result in results:
                if not result.keypoints:
                    continue
                keypoints = result.keypoints.xy.cpu().numpy()
                for i, kps in enumerate(keypoints):
                    if len(kps) < 17:  # Standart 17 anahtar nokta
                        continue
                    # Pelvis (12: sağ kalça, 11: sol kalça) ve baş (0: burun)
                    pelvis_x = (kps[11][0] + kps[12][0]) / 2
                    pelvis_y = (kps[11][1] + kps[12][1]) / 2
                    head_x, head_y = kps[0]
                    # Düşme kriteri: Pelvis başa göre çok aşağıda
                    height_ratio = (pelvis_y - head_y) / (frame_resized.shape[0])
                    if height_ratio > 0.7:  # Eşik
                        confidence = min(0.9, height_ratio * 1.2)
                        # En yakın track ID'sini bul
                        track_id = None
                        min_distance = float('inf')
                        cx, cy = pelvis_x * (frame.shape[1] / self.frame_size), pelvis_y * (frame.shape[0] / self.frame_size)
                        for track in tracks:
                            tx1, ty1, tx2, ty2 = track['bbox']
                            tcx = (tx1 + tx2) / 2
                            tcy = (ty1 + ty2) / 2
                            distance = np.sqrt((tcx - cx) ** 2 + (tcy - cy) ** 2)
                            if distance < min_distance:
                                min_distance = distance
                                track_id = track['track_id']
                        if track_id is not None:
                            logging.info(f"Düşme algılandı: ID={track_id}, Güven={confidence:.2f}")
                            return True, confidence, track_id
            return False, 0.0, None
        except Exception as e:
            logging.error(f"Düşme algılama sırasında hata: {str(e)}", exc_info=True)
            return False, 0.0, None

    def cleanup(self):
        """Kaynakları temizler."""
        try:
            self.tracker.delete_all_tracks()
            logging.info("DeepSORT tracker kaynakları temizlendi.")
        except Exception as e:
            logging.error(f"Tracker temizlenirken hata: {str(e)}")