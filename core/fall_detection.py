# =======================================================================================
# 📄 Dosya Adı: fall_detection.py (ULTRA ENHANCED FALL DETECTION)
# 📁 Konum: core/fall_detection.py
# 📌 Açıklama:
# Ultra gelişmiş düşme algılama - hassas algoritmalar, çoklu kontrol
# Anatomik analiz, hareket takibi, temporal analiz
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
from config.settings import MODEL_PATH, CONFIDENCE_THRESHOLD, FRAME_WIDTH
import winsound

class UltraFallDetector:
    """Ultra gelişmiş düşme algılama sistemi - anatomik analiz tabanlı."""
    
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, model_path=None, confidence_threshold=None, frame_width=None):
        """Thread-safe singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_path, confidence_threshold, frame_width)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Singleton instance sıfırla."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance.cleanup()
                except:
                    pass
                cls._instance = None

    def __init__(self, model_path=None, confidence_threshold=None, frame_width=None):
        """Ultra enhanced fall detector başlatıcı."""
        if UltraFallDetector._instance is not None:
            raise Exception("Bu sınıf singleton! get_instance() kullanın.")
        
        # Parametreler
        self.model_path = model_path or MODEL_PATH
        self.conf_threshold = confidence_threshold or CONFIDENCE_THRESHOLD
        self.frame_size = frame_width or FRAME_WIDTH
        
        # Model bilgileri
        self.model_version = "YOLOv11-Ultra"
        self.detector_version = "4.0"
        self.initialization_time = time.time()
        
                    # ULTRA ENHANCED FALL DETECTION PARAMETERS
        self.fall_detection_config = {
            # Ana anatomik eşikler
            'head_hip_ratio_threshold': 0.75,      # Baş-kalça oranı (kritik)
            'shoulder_hip_angle_threshold': 35,     # Omuz-kalça açısı (derece)
            'body_tilt_threshold': 40,              # Vücut eğimi (derece)
            'vertical_speed_threshold': 150,        # Dikey hız (pixel/frame)
            
            # Gelişmiş kontroller
            'knee_bend_threshold': 45,              # Diz bükülme açısı
            'arm_position_threshold': 30,           # Kol pozisyon değişimi
            'center_of_mass_shift': 0.3,           # Ağırlık merkezi kayması
            'pose_stability_threshold': 0.4,       # Pose kararlılığı
            
            # Temporal analiz
            'continuity_frames': 8,                # Süreklilik kontrol frame sayısı
            'velocity_analysis_frames': 5,         # Hız analizi frame sayısı
            'acceleration_threshold': 200,         # İvme eşiği (pixel/frame²)
            'fall_duration_min': 0.5,             # Minimum düşme süresi (saniye)
            'fall_duration_max': 3.0,             # Maksimum düşme süresi (saniye)
            
            # Kalite kontrolleri
            'min_keypoints': 12,                   # Minimum keypoint sayısı
            'min_keypoint_confidence': 0.4,       # Minimum keypoint güveni
            'min_person_height': 80,              # Minimum kişi yüksekliği (pixel)
            'max_person_height': 400,             # Maksimum kişi yüksekliği (pixel)
            
            # Çoklu düşme tipleri için ağırlıklar
            'fall_type_weights': {
                'forward_fall': {
                    'weight': 0.35,
                    'head_forward_threshold': 50,
                    'torso_angle_threshold': 45
                },
                'backward_fall': {
                    'weight': 0.25,
                    'head_backward_threshold': 40,
                    'spine_curve_threshold': 35
                },
                'side_fall': {
                    'weight': 0.30,
                    'lateral_displacement': 0.4,
                    'shoulder_imbalance': 40
                },
                'collapse_fall': {
                    'weight': 0.10,
                    'sudden_height_loss': 0.6,
                    'leg_collapse_angle': 60
                }
            }
        }
        
        # YOLO modeli yükle
        try:
            self.model = YOLO(self.model_path)
            self.is_model_loaded = True
            logging.info(f"Ultra YOLOv11 Pose modeli yüklendi: {self.model_path}")
        except Exception as e:
            logging.error(f"YOLO model yükleme hatası: {str(e)}")
            self.is_model_loaded = False
            self.model = None

        # DeepSORT tracker
        try:
            self.tracker = DeepSort(
                max_age=40,              # Daha uzun tracking
                n_init=3,                # Hızlı başlatma
                max_iou_distance=0.7,
                max_cosine_distance=0.4,
                nn_budget=150            # Daha büyük budget
            )
            logging.info("Ultra DeepSORT tracker başlatıldı")
        except Exception as e:
            logging.error(f"DeepSORT tracker hatası: {str(e)}")
            self.tracker = None

        # COCO pose keypoints (17 nokta) - anatomik mapping
        self.keypoint_anatomy = {
            'head': [0, 1, 2, 3, 4],           # Burun, gözler, kulaklar
            'torso': [5, 6, 11, 12],           # Omuzlar, kalçalar
            'arms': [5, 6, 7, 8, 9, 10],       # Omuz-dirsek-bilek
            'legs': [11, 12, 13, 14, 15, 16],  # Kalça-diz-ayak bileği
            'spine': [0, 5, 6, 11, 12],        # Omurga hattı
            'balance_points': [5, 6, 11, 12]   # Denge noktaları
        }
        
        # Tracking verileri
        self.person_tracks = {}          # {track_id: UltraPerson}
        self.fall_alerts = {}            # {track_id: fall_analysis}
        self.temporal_history = {}       # {track_id: pose_history}
        
        # Performans ve istatistikler
        self.frame_count = 0
        self.detection_stats = {
            'total_detections': 0,
            'fall_detections': 0,
            'false_positives': 0,
            'true_positives': 0,
            'processing_times': deque(maxlen=100),
            'session_start': time.time(),
            'fall_type_stats': defaultdict(int)
        }
        
        # Thread güvenliği
        self.detection_lock = threading.Lock()
        
        logging.info("Ultra Fall Detector başarıyla başlatıldı!")

    def get_enhanced_model_info(self):
        """Gelişmiş model bilgileri."""
        device_type = "cpu"
        if self.model is not None:
            try:
                device_type = "cuda" if self.model.device.type == "cuda" else "cpu"
            except:
                device_type = "cpu"
        
        return {
            "model_name": "Ultra YOLOv11 Pose",
            "model_path": self.model_path,
            "model_loaded": self.is_model_loaded,
            "confidence_threshold": self.conf_threshold,
            "frame_size": self.frame_size,
            "device": device_type,
            "detector_version": self.detector_version,
            "keypoints_count": 17,
            "tracker_available": self.tracker is not None,
            "fall_detection_config": self.fall_detection_config.copy(),
            "supported_fall_types": list(self.fall_detection_config['fall_type_weights'].keys()),
            "anatomic_mapping": self.keypoint_anatomy.copy(),
            "performance_stats": self.detection_stats.copy()
        }

    def get_detection_visualization(self, frame):
        """Ultra enhanced detection ve görselleştirme."""
        if not self.is_model_loaded or self.model is None:
            logging.warning("Model yüklü değil")
            return frame, []
        
        start_time = time.time()
        
        with self.detection_lock:
            try:
                # Frame preprocessing
                processed_frame = self._preprocess_frame(frame)
                
                # YOLO inference
                results = self.model.predict(
                    processed_frame, 
                    conf=self.conf_threshold, 
                    classes=[0],  # Sadece person
                    verbose=False,
                    imgsz=self.frame_size
                )
                
                # Detections ve pose data
                detections, pose_data = self._extract_detections_and_poses(results)
                
                # DeepSORT tracking
                tracks = []
                if self.tracker is not None and len(detections) > 0:
                    try:
                        tracks = self.tracker.update_tracks(detections, frame=processed_frame)
                    except Exception as e:
                        logging.error(f"Tracking hatası: {str(e)}")
                
                # Person tracking güncelle
                self._update_ultra_person_tracks(tracks, pose_data)
                
                # Ultra enhanced görselleştirme
                annotated_frame = self._draw_ultra_visualizations(frame, tracks)
                
                # Track listesi oluştur
                track_list = self._create_enhanced_track_list(tracks)
                
                # Performance stats
                processing_time = time.time() - start_time
                self.detection_stats['processing_times'].append(processing_time)
                self.detection_stats['total_detections'] += len(detections)
                
                return annotated_frame, track_list
                
            except Exception as e:
                logging.error(f"Detection visualization hatası: {str(e)}")
                return frame, []

    def detect_enhanced_fall(self, frame, tracks=None):
        """Ultra enhanced düşme algılama."""
        if not self.is_model_loaded or self.model is None:
            return False, 0.0, None, None
        
        with self.detection_lock:
            try:
                self.frame_count += 1
                current_time = time.time()
                
                # Tracks yoksa detection'dan al
                if tracks is None:
                    _, tracks = self.get_detection_visualization(frame)
                
                # Her kişi için ultra enhanced fall analizi
                for person_id, ultra_person in self.person_tracks.items():
                    if not ultra_person.has_sufficient_data():
                        continue
                    
                    # ULTRA FALL ANALYSIS
                    fall_analysis = self._ultra_fall_analysis(ultra_person, current_time)
                    
                    if fall_analysis['is_fall']:
                        # Temporal validation
                        if self._validate_fall_temporally(person_id, fall_analysis):
                            
                            # Fall type classification
                            fall_type = self._classify_fall_type(fall_analysis)
                            
                            # Final confidence calculation
                            final_confidence = self._calculate_final_confidence(fall_analysis, fall_type)
                            
                            if final_confidence > 0.7:  # Yüksek güven eşiği
                                logging.warning(f"🚨 ULTRA FALL DETECTED! ID={person_id}, Type={fall_type}, Confidence={final_confidence:.3f}")
                                
                                # İstatistik güncelle
                                self.detection_stats['fall_detections'] += 1
                                self.detection_stats['fall_type_stats'][fall_type] += 1
                                
                                # Alert sistemi
                                self._trigger_fall_alert(person_id, fall_analysis, fall_type)
                                
                                # Analysis result oluştur
                                analysis_result = UltraFallAnalysisResult(
                                    is_fall=True,
                                    confidence=final_confidence,
                                    fall_score=fall_analysis['total_score'],
                                    fall_type=fall_type,
                                    keypoint_quality=fall_analysis['keypoint_quality'],
                                    pose_stability=fall_analysis['pose_stability'],
                                    risk_factors=fall_analysis['risk_factors'],
                                    anatomic_analysis=fall_analysis['anatomic_scores'],
                                    temporal_analysis=fall_analysis['temporal_scores'],
                                    timestamp=current_time
                                )
                                
                                return True, final_confidence, person_id, analysis_result
                
                return False, 0.0, None, None
                
            except Exception as e:
                logging.error(f"Enhanced fall detection hatası: {str(e)}")
                return False, 0.0, None, None

    def _preprocess_frame(self, frame):
        """Frame ön işleme - performans optimizasyonu."""
        try:
            # Resize if needed
            h, w = frame.shape[:2]
            if w != self.frame_size or h != self.frame_size:
                frame = cv2.resize(frame, (self.frame_size, self.frame_size), interpolation=cv2.INTER_LINEAR)
            
            # Normalize
            frame = cv2.convertScaleAbs(frame, alpha=1.0, beta=0)
            
            return frame
        except Exception as e:
            logging.error(f"Frame preprocessing hatası: {e}")
            return frame

    def _extract_detections_and_poses(self, results):
        """YOLO sonuçlarından detection ve pose verilerini çıkar."""
        detections = []
        pose_data = []
        
        try:
            for result in results:
                if result.boxes is not None and hasattr(result.boxes, 'xyxy'):
                    boxes = self._safe_tensor_to_numpy(result.boxes.xyxy)
                    confs = self._safe_tensor_to_numpy(result.boxes.conf)
                    
                    # Keypoints
                    keypoints = None
                    keypoint_confs = None
                    if hasattr(result, 'keypoints') and result.keypoints is not None:
                        try:
                            if hasattr(result.keypoints, 'xy'):
                                keypoints = self._safe_tensor_to_numpy(result.keypoints.xy)
                            if hasattr(result.keypoints, 'conf'):
                                keypoint_confs = self._safe_tensor_to_numpy(result.keypoints.conf)
                        except Exception as kp_error:
                            logging.debug(f"Keypoint extraction hatası: {kp_error}")
                    
                    # Her detection için işle
                    for i, (box, conf) in enumerate(zip(boxes, confs)):
                        if conf < self.conf_threshold:
                            continue
                            
                        x1, y1, x2, y2 = map(int, box)
                        
                        # Person height validation
                        person_height = y2 - y1
                        if (person_height < self.fall_detection_config['min_person_height'] or 
                            person_height > self.fall_detection_config['max_person_height']):
                            continue
                        
                        # Detection format: [x, y, w, h]
                        detection = [x1, y1, x2-x1, y2-y1]
                        detections.append((detection, conf, 0))
                        
                        # Pose data
                        person_keypoints = keypoints[i] if keypoints is not None and i < len(keypoints) else None
                        person_keypoint_confs = keypoint_confs[i] if keypoint_confs is not None and i < len(keypoint_confs) else None
                        
                        pose_data.append({
                            'keypoints': person_keypoints,
                            'keypoint_confs': person_keypoint_confs,
                            'bbox': [x1, y1, x2, y2],
                            'person_height': person_height
                        })
        
        except Exception as e:
            logging.error(f"Detection extraction hatası: {e}")
        
        return detections, pose_data

    def _safe_tensor_to_numpy(self, tensor):
        """Tensor'ı güvenli şekilde numpy'ye çevir."""
        try:
            if tensor is None:
                return None
            if hasattr(tensor, 'cpu'):
                return tensor.cpu().numpy()
            elif hasattr(tensor, 'numpy'):
                return tensor.numpy()
            else:
                return np.array(tensor)
        except Exception as e:
            logging.debug(f"Tensor conversion hatası: {e}")
            return None

    def _update_ultra_person_tracks(self, tracks, pose_data):
        """Ultra person tracking güncelle."""
        try:
            current_track_ids = set()
            
            for i, track in enumerate(tracks):
                if not hasattr(track, 'is_confirmed') or not track.is_confirmed():
                    continue
                    
                track_id = track.track_id
                current_track_ids.add(track_id)
                
                # Pose data al
                person_pose = pose_data[i] if i < len(pose_data) else None
                
                if track_id not in self.person_tracks:
                    self.person_tracks[track_id] = UltraPerson(track_id)
                    self.temporal_history[track_id] = deque(maxlen=30)
                
                # Ultra person güncelle
                self.person_tracks[track_id].update(track, person_pose)
                
                # Temporal history güncelle
                if person_pose and person_pose.get('keypoints') is not None:
                    self.temporal_history[track_id].append({
                        'timestamp': time.time(),
                        'keypoints': person_pose['keypoints'].copy(),
                        'keypoint_confs': person_pose.get('keypoint_confs'),
                        'bbox': person_pose.get('bbox')
                    })
            
            # Inactive tracks temizle
            inactive_tracks = set(self.person_tracks.keys()) - current_track_ids
            for track_id in inactive_tracks:
                del self.person_tracks[track_id]
                if track_id in self.fall_alerts:
                    del self.fall_alerts[track_id]
                if track_id in self.temporal_history:
                    del self.temporal_history[track_id]
                    
        except Exception as e:
            logging.error(f"Ultra person tracks güncelleme hatası: {str(e)}")

    def _ultra_fall_analysis(self, ultra_person, current_time):
        """Ultra enhanced fall analysis."""
        try:
            keypoints = ultra_person.latest_keypoints
            keypoint_confs = ultra_person.latest_keypoint_confs
            bbox = ultra_person.latest_bbox
            
            # Keypoint quality check
            valid_keypoints = np.sum(keypoint_confs > self.fall_detection_config['min_keypoint_confidence'])
            keypoint_quality = valid_keypoints / 17.0
            
            if valid_keypoints < self.fall_detection_config['min_keypoints']:
                return {'is_fall': False, 'reason': 'insufficient_keypoints'}
            
            # Anatomik analiz
            anatomic_scores = self._analyze_anatomic_features(keypoints, keypoint_confs, bbox)
            
            # Temporal analiz
            temporal_scores = self._analyze_temporal_features(ultra_person.track_id, keypoints)
            
            # Pose stability analizi
            pose_stability = self._calculate_pose_stability(ultra_person.track_id)
            
            # Risk faktörleri
            risk_factors = []
            total_score = 0.0
            
            # 1. HEAD-HIP RATIO ANALYSIS (En kritik)
            head_hip_score = anatomic_scores.get('head_hip_ratio_score', 0)
            if head_hip_score > 0.6:
                risk_factors.append('critical_head_hip_ratio')
                total_score += head_hip_score * 0.25
            
            # 2. BODY TILT ANALYSIS
            body_tilt_score = anatomic_scores.get('body_tilt_score', 0)
            if body_tilt_score > 0.5:
                risk_factors.append('excessive_body_tilt')
                total_score += body_tilt_score * 0.20
            
            # 3. SHOULDER-HIP ALIGNMENT
            shoulder_hip_score = anatomic_scores.get('shoulder_hip_score', 0)
            if shoulder_hip_score > 0.4:
                risk_factors.append('shoulder_hip_misalignment')
                total_score += shoulder_hip_score * 0.15
            
            # 4. VERTICAL VELOCITY
            velocity_score = temporal_scores.get('vertical_velocity_score', 0)
            if velocity_score > 0.5:
                risk_factors.append('high_vertical_velocity')
                total_score += velocity_score * 0.15
            
            # 5. ACCELERATION ANALYSIS
            acceleration_score = temporal_scores.get('acceleration_score', 0)
            if acceleration_score > 0.4:
                risk_factors.append('sudden_acceleration')
                total_score += acceleration_score * 0.10
            
            # 6. LIMB POSITION ANALYSIS
            limb_score = anatomic_scores.get('limb_position_score', 0)
            if limb_score > 0.3:
                risk_factors.append('abnormal_limb_position')
                total_score += limb_score * 0.10
            
            # 7. CENTER OF MASS SHIFT
            com_score = anatomic_scores.get('center_of_mass_score', 0)
            if com_score > 0.3:
                risk_factors.append('center_of_mass_shift')
                total_score += com_score * 0.05
            
            # Fall decision
            is_fall = (total_score > 0.65 and 
                      len(risk_factors) >= 3 and
                      keypoint_quality > 0.6 and
                      pose_stability < 0.7)
            
            return {
                'is_fall': is_fall,
                'total_score': total_score,
                'keypoint_quality': keypoint_quality,
                'pose_stability': pose_stability,
                'risk_factors': risk_factors,
                'anatomic_scores': anatomic_scores,
                'temporal_scores': temporal_scores,
                'analysis_timestamp': current_time
            }
            
        except Exception as e:
            logging.error(f"Ultra fall analysis hatası: {e}")
            return {'is_fall': False, 'reason': 'analysis_error'}

    def _analyze_anatomic_features(self, keypoints, keypoint_confs, bbox):
        """Anatomik özellik analizi."""
        try:
            scores = {}
            
            # Key points
            nose = keypoints[0] if keypoint_confs[0] > 0.3 else None
            left_shoulder = keypoints[5] if keypoint_confs[5] > 0.3 else None
            right_shoulder = keypoints[6] if keypoint_confs[6] > 0.3 else None
            left_hip = keypoints[11] if keypoint_confs[11] > 0.3 else None
            right_hip = keypoints[12] if keypoint_confs[12] > 0.3 else None
            left_knee = keypoints[13] if keypoint_confs[13] > 0.3 else None
            right_knee = keypoints[14] if keypoint_confs[14] > 0.3 else None
            
            # 1. HEAD-HIP RATIO (Kritik)
            if nose is not None and left_hip is not None and right_hip is not None:
                hip_center = (left_hip + right_hip) / 2
                head_hip_distance = abs(nose[1] - hip_center[1])
                bbox_height = bbox[3] - bbox[1]
                
                if bbox_height > 0:
                    head_hip_ratio = head_hip_distance / bbox_height
                    threshold = self.fall_detection_config['head_hip_ratio_threshold']
                    scores['head_hip_ratio_score'] = max(0, (threshold - head_hip_ratio) / threshold)
                else:
                    scores['head_hip_ratio_score'] = 0
            else:
                scores['head_hip_ratio_score'] = 0
            
            # 2. BODY TILT ANALYSIS
            if (left_shoulder is not None and right_shoulder is not None and 
                left_hip is not None and right_hip is not None):
                
                shoulder_center = (left_shoulder + right_shoulder) / 2
                hip_center = (left_hip + right_hip) / 2
                
                # Spine tilt angle
                dx = hip_center[0] - shoulder_center[0]
                dy = hip_center[1] - shoulder_center[1]
                
                if dy != 0:
                    tilt_angle = abs(math.degrees(math.atan(dx / dy)))
                    threshold = self.fall_detection_config['body_tilt_threshold']
                    scores['body_tilt_score'] = min(1.0, max(0, (tilt_angle - threshold/2) / threshold))
                else:
                    scores['body_tilt_score'] = 1.0  # Horizontal = fall
            else:
                scores['body_tilt_score'] = 0
            
            # 3. SHOULDER-HIP ALIGNMENT
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
                
                alignment_diff = abs(shoulder_angle - hip_angle)
                threshold = self.fall_detection_config['shoulder_hip_angle_threshold']
                scores['shoulder_hip_score'] = min(1.0, max(0, (alignment_diff - threshold/2) / threshold))
            else:
                scores['shoulder_hip_score'] = 0
            
            # 4. LIMB POSITION ANALYSIS
            limb_abnormality = 0
            limb_count = 0
            
            # Knee position analysis
            if left_knee is not None and left_hip is not None:
                knee_hip_distance = np.linalg.norm(left_knee - left_hip)
                if knee_hip_distance < 30:  # Çok yakın = çömelme/düşme
                    limb_abnormality += 1
                limb_count += 1
            
            if right_knee is not None and right_hip is not None:
                knee_hip_distance = np.linalg.norm(right_knee - right_hip)
                if knee_hip_distance < 30:
                    limb_abnormality += 1
                limb_count += 1
            
            scores['limb_position_score'] = limb_abnormality / max(1, limb_count)
            
            # 5. CENTER OF MASS ANALYSIS
            if (left_shoulder is not None and right_shoulder is not None and 
                left_hip is not None and right_hip is not None):
                
                upper_com = (left_shoulder + right_shoulder) / 2
                lower_com = (left_hip + right_hip) / 2
                
                com_shift = abs(upper_com[0] - lower_com[0])
                bbox_width = bbox[2] - bbox[0]
                
                if bbox_width > 0:
                    com_ratio = com_shift / bbox_width
                    threshold = self.fall_detection_config['center_of_mass_shift']
                    scores['center_of_mass_score'] = min(1.0, max(0, com_ratio / threshold))
                else:
                    scores['center_of_mass_score'] = 0
            else:
                scores['center_of_mass_score'] = 0
            
            return scores
            
        except Exception as e:
            logging.error(f"Anatomic analysis hatası: {e}")
            return {}

    def _analyze_temporal_features(self, track_id, current_keypoints):
        """Temporal feature analysis."""
        try:
            scores = {}
            
            if track_id not in self.temporal_history or len(self.temporal_history[track_id]) < 3:
                return scores
            
            history = list(self.temporal_history[track_id])
            
            # Calculate velocities and accelerations
            velocities = []
            accelerations = []
            
            for i in range(len(history) - 1):
                if (history[i]['keypoints'] is not None and 
                    history[i+1]['keypoints'] is not None):
                    
                    # Time difference
                    dt = history[i+1]['timestamp'] - history[i]['timestamp']
                    if dt <= 0:
                        continue
                    
                    # Center of mass velocity
                    com1 = self._calculate_center_of_mass(history[i]['keypoints'], history[i]['keypoint_confs'])
                    com2 = self._calculate_center_of_mass(history[i+1]['keypoints'], history[i+1]['keypoint_confs'])
                    
                    if com1 is not None and com2 is not None:
                        velocity = np.linalg.norm(com2 - com1) / dt
                        velocities.append(velocity)
                        
                        # Vertical velocity
                        vertical_velocity = abs(com2[1] - com1[1]) / dt
                        
                        # Acceleration
                        if len(velocities) >= 2:
                            acceleration = abs(velocities[-1] - velocities[-2]) / dt
                            accelerations.append(acceleration)
            
            # Vertical velocity score
            if velocities:
                max_velocity = max(velocities)
                threshold = self.fall_detection_config['vertical_speed_threshold']
                scores['vertical_velocity_score'] = min(1.0, max(0, max_velocity / threshold))
            else:
                scores['vertical_velocity_score'] = 0
            
            # Acceleration score
            if accelerations:
                max_acceleration = max(accelerations)
                threshold = self.fall_detection_config['acceleration_threshold']
                scores['acceleration_score'] = min(1.0, max(0, max_acceleration / threshold))
            else:
                scores['acceleration_score'] = 0
            
            return scores
            
        except Exception as e:
            logging.error(f"Temporal analysis hatası: {e}")
            return {}

    def _calculate_center_of_mass(self, keypoints, keypoint_confs):
        """Ağırlık merkezi hesapla."""
        try:
            if keypoints is None or keypoint_confs is None:
                return None
            
            # Ana vücut noktaları
            main_points = [5, 6, 11, 12]  # Omuzlar ve kalçalar
            valid_points = []
            
            for idx in main_points:
                if idx < len(keypoints) and keypoint_confs[idx] > 0.3:
                    valid_points.append(keypoints[idx])
            
            if len(valid_points) >= 2:
                return np.mean(valid_points, axis=0)
            else:
                return None
                
        except Exception as e:
            logging.debug(f"Center of mass hesaplama hatası: {e}")
            return None

    def _calculate_pose_stability(self, track_id):
        """Pose kararlılığı hesapla."""
        try:
            if track_id not in self.temporal_history or len(self.temporal_history[track_id]) < 5:
                return 1.0  # Yeterli veri yok
            
            history = list(self.temporal_history[track_id])[-5:]  # Son 5 frame
            
            # Keypoint position variances
            position_variances = []
            
            for kp_idx in range(17):  # 17 keypoints
                positions = []
                for frame_data in history:
                    if (frame_data['keypoints'] is not None and 
                        frame_data['keypoint_confs'] is not None and
                        kp_idx < len(frame_data['keypoint_confs']) and
                        frame_data['keypoint_confs'][kp_idx] > 0.3):
                        positions.append(frame_data['keypoints'][kp_idx])
                
                if len(positions) >= 3:
                    positions = np.array(positions)
                    variance = np.var(positions, axis=0)
                    position_variances.append(np.mean(variance))
            
            if position_variances:
                avg_variance = np.mean(position_variances)
                # Normalize variance to stability score (0-1)
                stability = 1.0 / (1.0 + avg_variance / 100.0)
                return max(0.0, min(1.0, stability))
            else:
                return 1.0
                
        except Exception as e:
            logging.debug(f"Pose stability hesaplama hatası: {e}")
            return 1.0

    def _validate_fall_temporally(self, person_id, fall_analysis):
        """Temporal fall validation."""
        try:
            current_time = time.time()
            
            if person_id not in self.fall_alerts:
                self.fall_alerts[person_id] = {
                    'start_time': current_time,
                    'frame_count': 1,
                    'max_confidence': fall_analysis['total_score'],
                    'fall_sequence': [fall_analysis]
                }
                return False  # İlk frame, henüz validate etme
            
            alert = self.fall_alerts[person_id]
            alert['frame_count'] += 1
            alert['max_confidence'] = max(alert['max_confidence'], fall_analysis['total_score'])
            alert['fall_sequence'].append(fall_analysis)
            
            # Duration check
            duration = current_time - alert['start_time']
            min_duration = self.fall_detection_config['fall_duration_min']
            max_duration = self.fall_detection_config['fall_duration_max']
            
            if duration < min_duration:
                return False
            
            if duration > max_duration:
                # Reset if too long
                del self.fall_alerts[person_id]
                return False
            
            # Continuity check
            required_frames = self.fall_detection_config['continuity_frames']
            if alert['frame_count'] >= required_frames:
                # Check sequence consistency
                recent_scores = [seq['total_score'] for seq in alert['fall_sequence'][-required_frames:]]
                if all(score > 0.5 for score in recent_scores):
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Temporal validation hatası: {e}")
            return False

    def _classify_fall_type(self, fall_analysis):
        """Düşme tipini sınıflandır."""
        try:
            anatomic = fall_analysis.get('anatomic_scores', {})
            temporal = fall_analysis.get('temporal_scores', {})
            
            # Fall type scores
            type_scores = {}
            
            # Forward fall
            head_hip_score = anatomic.get('head_hip_ratio_score', 0)
            body_tilt_score = anatomic.get('body_tilt_score', 0)
            type_scores['forward_fall'] = (head_hip_score * 0.6 + body_tilt_score * 0.4)
            
            # Backward fall  
            shoulder_hip_score = anatomic.get('shoulder_hip_score', 0)
            com_score = anatomic.get('center_of_mass_score', 0)
            type_scores['backward_fall'] = (shoulder_hip_score * 0.5 + com_score * 0.5)
            
            # Side fall
            com_score = anatomic.get('center_of_mass_score', 0)
            limb_score = anatomic.get('limb_position_score', 0)
            type_scores['side_fall'] = (com_score * 0.7 + limb_score * 0.3)
            
            # Collapse fall
            velocity_score = temporal.get('vertical_velocity_score', 0)
            acceleration_score = temporal.get('acceleration_score', 0)
            type_scores['collapse_fall'] = (velocity_score * 0.6 + acceleration_score * 0.4)
            
            # En yüksek skorlu tipi döndür
            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                return best_type
            else:
                return 'unknown_fall'
                
        except Exception as e:
            logging.error(f"Fall type classification hatası: {e}")
            return 'unknown_fall'

    def _calculate_final_confidence(self, fall_analysis, fall_type):
        """Final güven skoru hesapla."""
        try:
            base_score = fall_analysis['total_score']
            keypoint_quality = fall_analysis['keypoint_quality']
            pose_stability = fall_analysis['pose_stability']
            
            # Type weight
            type_weights = self.fall_detection_config['fall_type_weights']
            type_weight = type_weights.get(fall_type, {}).get('weight', 0.5)
            
            # Quality factors
            quality_factor = (keypoint_quality * 0.4 + (1 - pose_stability) * 0.6)
            
            # Final confidence
            final_confidence = base_score * type_weight * quality_factor
            
            return max(0.0, min(1.0, final_confidence))
            
        except Exception as e:
            logging.error(f"Final confidence hesaplama hatası: {e}")
            return 0.0

    def _trigger_fall_alert(self, person_id, fall_analysis, fall_type):
        """Düşme uyarısı tetikle."""
        try:
            # Ses uyarısı
            threading.Thread(target=self._play_enhanced_fall_alert, daemon=True).start()
            
            # Alert kaydı
            alert_data = {
                'person_id': person_id,
                'fall_type': fall_type,
                'confidence': fall_analysis['total_score'],
                'timestamp': time.time(),
                'risk_factors': fall_analysis['risk_factors'],
                'keypoint_quality': fall_analysis['keypoint_quality']
            }
            
            logging.info(f"🚨 FALL ALERT TRIGGERED: {alert_data}")
            
        except Exception as e:
            logging.error(f"Fall alert trigger hatası: {e}")

    def _play_enhanced_fall_alert(self):
        """Gelişmiş ses uyarısı."""
        try:
            # Windows sistem sesi
            for _ in range(3):  # 3 kez çal
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                time.sleep(0.3)
        except Exception as e:
            logging.warning(f"Ses uyarısı hatası: {e}")

    def _draw_ultra_visualizations(self, frame, tracks):
        """Ultra enhanced görselleştirme."""
        try:
            annotated_frame = frame.copy()
            
            # Frame boyut oranları
            scale_x = frame.shape[1] / self.frame_size
            scale_y = frame.shape[0] / self.frame_size
            
            for track in tracks:
                if not hasattr(track, 'is_confirmed') or not track.is_confirmed():
                    continue
                
                track_id = track.track_id
                bbox = track.to_ltrb()
                
                # Bbox ölçeklendir
                x1 = int(bbox[0] * scale_x)
                y1 = int(bbox[1] * scale_y)
                x2 = int(bbox[2] * scale_x)
                y2 = int(bbox[3] * scale_y)
                
                # Fall status kontrolü
                is_falling = track_id in self.fall_alerts
                
                # Renk seçimi
                if is_falling:
                    box_color = (0, 0, 255)  # Kırmızı
                    text_color = (255, 255, 255)
                    thickness = 4
                else:
                    box_color = (0, 255, 0)  # Yeşil
                    text_color = (255, 255, 255)
                    thickness = 2
                
                # Bounding box çiz
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, thickness)
                
                # Enhanced label
                confidence = getattr(track, 'confidence', 0.0)
                label = f"ID: {track_id}"
                
                if is_falling:
                    alert = self.fall_alerts[track_id]
                    fall_conf = alert.get('max_confidence', 0.0)
                    label = f"ID: {track_id} - FALL! ({fall_conf:.2f})"
                
                # Label background
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                cv2.rectangle(annotated_frame, (x1, y1-40), (x1 + label_size[0] + 10, y1), box_color, -1)
                
                # Label text
                cv2.putText(annotated_frame, label, (x1+5, y1-15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
                
                # Enhanced pose visualization
                if track_id in self.person_tracks:
                    ultra_person = self.person_tracks[track_id]
                    if ultra_person.has_valid_pose():
                        self._draw_enhanced_pose(annotated_frame, ultra_person, scale_x, scale_y, is_falling)
            
            # Performance stats overlay
            self._draw_performance_overlay(annotated_frame)
            
            return annotated_frame
            
        except Exception as e:
            logging.error(f"Ultra visualization hatası: {e}")
            return frame

    def _draw_enhanced_pose(self, frame, ultra_person, scale_x, scale_y, is_falling):
        """Enhanced pose çizimi."""
        try:
            keypoints = ultra_person.latest_keypoints
            keypoint_confs = ultra_person.latest_keypoint_confs
            
            if keypoints is None or keypoint_confs is None:
                return
            
            # Renk seçimi
            if is_falling:
                point_color = (0, 0, 255)  # Kırmızı
                line_color = (255, 0, 0)   # Mavi
            else:
                point_color = (0, 255, 255)  # Sarı
                line_color = (0, 255, 0)     # Yeşil
            
            # COCO skeleton connections
            skeleton = [
                [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],
                [6, 12], [7, 13], [6, 7], [6, 8], [7, 9],
                [8, 10], [9, 11], [6, 5], [5, 7], [1, 2],
                [0, 1], [0, 2], [1, 3], [2, 4]
            ]
            
            # Keypoints çiz
            for i, (keypoint, conf) in enumerate(zip(keypoints, keypoint_confs)):
                if conf > self.fall_detection_config['min_keypoint_confidence']:
                    x = int(keypoint[0] * scale_x)
                    y = int(keypoint[1] * scale_y)
                    
                    # Kritik noktaları vurgula
                    if i in [0, 5, 6, 11, 12]:  # Baş, omuzlar, kalçalar
                        radius = 6
                        thickness = -1
                    else:
                        radius = 4
                        thickness = -1
                    
                    cv2.circle(frame, (x, y), radius, point_color, thickness)
            
            # Skeleton çizgileri
            for connection in skeleton:
                pt1_idx, pt2_idx = connection[0] - 1, connection[1] - 1
                
                if (0 <= pt1_idx < len(keypoints) and 0 <= pt2_idx < len(keypoints) and
                    keypoint_confs[pt1_idx] > 0.3 and keypoint_confs[pt2_idx] > 0.3):
                    
                    pt1 = (int(keypoints[pt1_idx][0] * scale_x), int(keypoints[pt1_idx][1] * scale_y))
                    pt2 = (int(keypoints[pt2_idx][0] * scale_x), int(keypoints[pt2_idx][1] * scale_y))
                    
                    thickness = 3 if is_falling else 2
                    cv2.line(frame, pt1, pt2, line_color, thickness)
                    
        except Exception as e:
            logging.error(f"Enhanced pose çizim hatası: {e}")

    def _draw_performance_overlay(self, frame):
        """Performans overlay çiz."""
        try:
            h, w = frame.shape[:2]
            
            # Performance stats
            processing_times = list(self.detection_stats['processing_times'])
            if processing_times:
                avg_time = np.mean(processing_times)
                fps = 1.0 / avg_time if avg_time > 0 else 0
            else:
                fps = 0
            
            # Overlay background
            overlay_height = 80
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, overlay_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            # Stats text
            stats_text = [
                f"Ultra FallDetector v{self.detector_version}",
                f"FPS: {fps:.1f} | Tracks: {len(self.person_tracks)} | Falls: {self.detection_stats['fall_detections']}"
            ]
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            for i, text in enumerate(stats_text):
                y_pos = 20 + i * 25
                cv2.putText(frame, text, (10, y_pos), font, 0.6, (0, 255, 255), 2)
                
        except Exception as e:
            logging.debug(f"Performance overlay hatası: {e}")

    def _create_enhanced_track_list(self, tracks):
        """Enhanced track listesi oluştur."""
        try:
            track_list = []
            
            for track in tracks:
                if hasattr(track, 'is_confirmed') and track.is_confirmed():
                    track_id = track.track_id
                    bbox = track.to_ltrb()
                    
                    # Additional data
                    is_falling = track_id in self.fall_alerts
                    fall_confidence = 0.0
                    fall_type = 'none'
                    
                    if is_falling:
                        alert = self.fall_alerts[track_id]
                        fall_confidence = alert.get('max_confidence', 0.0)
                        # Get fall type from last sequence
                        if alert.get('fall_sequence'):
                            last_analysis = alert['fall_sequence'][-1]
                            fall_type = self._classify_fall_type(last_analysis)
                    
                    track_info = {
                        'track_id': track_id,
                        'bbox': bbox.tolist(),
                        'confidence': getattr(track, 'confidence', 0.0),
                        'is_falling': is_falling,
                        'fall_confidence': fall_confidence,
                        'fall_type': fall_type,
                        'has_pose': track_id in self.person_tracks and self.person_tracks[track_id].has_valid_pose()
                    }
                    
                    track_list.append(track_info)
            
            return track_list
            
        except Exception as e:
            logging.error(f"Enhanced track list oluşturma hatası: {e}")
            return []

    def get_detection_summary(self):
        """Enhanced detection summary."""
        uptime = time.time() - self.initialization_time
        
        processing_times = list(self.detection_stats['processing_times'])
        avg_fps = 0
        if processing_times:
            avg_time = np.mean(processing_times)
            avg_fps = 1.0 / avg_time if avg_time > 0 else 0
        
        return {
            "detector_version": self.detector_version,
            "session_uptime": uptime,
            "total_frames": self.frame_count,
            "total_detections": self.detection_stats['total_detections'],
            "fall_detections": self.detection_stats['fall_detections'],
            "active_tracks": len(self.person_tracks),
            "active_alerts": len(self.fall_alerts),
            "avg_fps": avg_fps,
            "model_status": "loaded" if self.is_model_loaded else "error",
            "tracker_status": "active" if self.tracker else "disabled",
            "fall_type_distribution": dict(self.detection_stats['fall_type_stats']),
            "detection_accuracy": self._calculate_detection_accuracy()
        }

    def _calculate_detection_accuracy(self):
        """Detection accuracy hesapla."""
        total = self.detection_stats['fall_detections'] + self.detection_stats['false_positives']
        if total == 0:
            return 1.0
        
        true_positives = self.detection_stats['fall_detections']
        accuracy = true_positives / total
        return max(0.0, min(1.0, accuracy))

    def cleanup(self):
        """Enhanced cleanup."""
        try:
            if self.tracker is not None:
                self.tracker.delete_all_tracks()
            
            self.person_tracks.clear()
            self.fall_alerts.clear()
            self.temporal_history.clear()
            
            logging.info("Ultra FallDetector cleanup tamamlandı")
        except Exception as e:
            logging.error(f"Cleanup hatası: {e}")


class UltraPerson:
    """Ultra enhanced person tracking class."""
    
    def __init__(self, track_id):
        self.track_id = track_id
        self.latest_bbox = None
        self.latest_keypoints = None
        self.latest_keypoint_confs = None
        self.pose_history = deque(maxlen=15)
        self.update_time = time.time()
        self.person_height = 0
        
    def update(self, track, pose_data):
        """Update person data."""
        self.latest_bbox = track.to_ltrb()
        self.update_time = time.time()
        
        if pose_data and pose_data.get('keypoints') is not None:
            self.latest_keypoints = pose_data['keypoints']
            self.latest_keypoint_confs = pose_data.get('keypoint_confs')
            self.person_height = pose_data.get('person_height', 0)
            
            # Add to history
            self.pose_history.append({
                'keypoints': self.latest_keypoints.copy(),
                'keypoint_confs': self.latest_keypoint_confs.copy() if self.latest_keypoint_confs is not None else None,
                'timestamp': self.update_time,
                'bbox': self.latest_bbox.copy()
            })
    
    def has_valid_pose(self):
        """Check if has valid pose data."""
        return (self.latest_keypoints is not None and 
                self.latest_keypoint_confs is not None and
                len(self.latest_keypoints) >= 17)
    
    def has_sufficient_data(self):
        """Check if has sufficient data for analysis."""
        return (self.has_valid_pose() and 
                len(self.pose_history) >= 3 and
                self.person_height > 50)


class UltraFallAnalysisResult:
    """Ultra enhanced fall analysis result."""
    
    def __init__(self, is_fall, confidence, fall_score, fall_type, keypoint_quality, 
                 pose_stability, risk_factors, anatomic_analysis, temporal_analysis, timestamp):
        self.is_fall = is_fall
        self.confidence = confidence
        self.fall_score = fall_score
        self.fall_type = fall_type
        self.keypoint_quality = keypoint_quality
        self.pose_stability = pose_stability
        self.risk_factors = risk_factors
        self.anatomic_analysis = anatomic_analysis
        self.temporal_analysis = temporal_analysis
        self.timestamp = timestamp
        
        # Enhanced analysis details
        self.analysis_details = {
            'anatomic_scores': anatomic_analysis,
            'temporal_scores': temporal_analysis,
            'risk_assessment': self._assess_risk_level(),
            'fall_severity': self._calculate_fall_severity(),
            'recommended_action': self._get_recommended_action()
        }
    
    def _assess_risk_level(self):
        """Risk seviyesi değerlendir."""
        if self.confidence > 0.9:
            return 'CRITICAL'
        elif self.confidence > 0.7:
            return 'HIGH'
        elif self.confidence > 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _calculate_fall_severity(self):
        """Düşme şiddeti hesapla."""
        severity_score = (self.fall_score * 0.4 + 
                         self.confidence * 0.4 + 
                         (1 - self.pose_stability) * 0.2)
        
        if severity_score > 0.8:
            return 'SEVERE'
        elif severity_score > 0.6:
            return 'MODERATE'
        else:
            return 'MILD'
    
    def _get_recommended_action(self):
        """Önerilen eylem."""
        if self.confidence > 0.8:
            return 'IMMEDIATE_RESPONSE_REQUIRED'
        elif self.confidence > 0.6:
            return 'CHECK_PERSON_STATUS'
        else:
            return 'MONITOR_SITUATION'


# Backward compatibility
FallDetector = UltraFallDetector


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    detector = UltraFallDetector.get_instance()
    print("Ultra Fall Detector test edildi!")
    print(f"Model info: {detector.get_enhanced_model_info()}")