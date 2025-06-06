# =======================================================================================
# 📄 Dosya Adı: endpoints.py (ULTRA ENHANCED VERSION)
# 📁 Konum: guard_pc_app/api/endpoints.py
# 📌 Açıklama:
# Guard AI Ultra - YOLOv11 Pose Estimation için gelişmiş API endpoints
# Firebase Firestore entegrasyonu, gerçek zamanlı veri işleme
# =======================================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
import logging
import asyncio
import json
import cv2
import numpy as np
from datetime import datetime, timedelta
from enum import Enum
import uuid
import time
import base64
from io import BytesIO
from PIL import Image

# Firebase ve AI imports
try:
    from data.database import FirestoreManager
    from data.storage import StorageManager
    from core.fall_detection import FallDetector
    from core.camera import Camera
    from core.notification import NotificationManager
    from config.settings import FRAME_WIDTH, FRAME_HEIGHT
except ImportError as e:
    logging.warning(f"Bazı modüller yüklenemedi: {e}")

router = APIRouter(prefix="/api/v1", tags=["Guard AI Ultra API"])

# Enum'lar
class EventType(str, Enum):
    FALL_DETECTION = "fall_detection"
    PERSON_DETECTED = "person_detected"
    SYSTEM_ALERT = "system_alert"
    CAMERA_OFFLINE = "camera_offline"

class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PUSH = "push"
    WEBHOOK = "webhook"

class SystemStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"

# Pydantic Modeller
class FallEvent(BaseModel):
    id: str = Field(..., description="Unique event ID")
    user_id: str = Field(..., description="User ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence (0-1)")
    image_url: Optional[str] = Field(None, description="Event image URL")
    event_type: EventType = Field(EventType.FALL_DETECTION, description="Event type")
    camera_id: str = Field(..., description="Camera identifier")
    detection_method: str = Field("YOLOv11_Pose", description="Detection algorithm used")
    pose_analysis: Optional[Dict[str, Any]] = Field(None, description="Pose analysis data")
    location: Optional[Dict[str, float]] = Field(None, description="GPS coordinates")
    processed: bool = Field(False, description="Event processing status")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "evt_123456789",
                "user_id": "user_abc123",
                "timestamp": "2025-06-06T16:36:59Z",
                "confidence": 0.95,
                "camera_id": "camera_0",
                "detection_method": "YOLOv11_Pose",
                "pose_analysis": {
                    "valid_points": 15,
                    "stability": 0.8,
                    "tilt_angle": 78.5
                }
            }
        }

class UserSettings(BaseModel):
    user_id: str = Field(..., description="User ID")
    email_notification: bool = Field(True, description="Enable email notifications")
    sms_notification: bool = Field(False, description="Enable SMS notifications")
    telegram_notification: bool = Field(False, description="Enable Telegram notifications")
    push_notification: bool = Field(True, description="Enable push notifications")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID")
    notification_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum confidence for notifications")
    quiet_hours: Optional[Dict[str, str]] = Field(None, description="Quiet hours configuration")
    emergency_contacts: List[str] = Field(default_factory=list, description="Emergency contact list")
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if v and not v.startswith('+'):
            raise ValueError('Phone number must include country code')
        return v

class SystemInfo(BaseModel):
    version: str = Field(..., description="System version")
    status: SystemStatus = Field(..., description="System status")
    uptime: float = Field(..., description="System uptime in seconds")
    active_cameras: int = Field(..., description="Number of active cameras")
    ai_model_loaded: bool = Field(..., description="AI model status")
    detection_count: int = Field(..., description="Total detections today")
    fall_count: int = Field(..., description="Total falls detected today")
    last_detection: Optional[datetime] = Field(None, description="Last detection timestamp")

class CameraInfo(BaseModel):
    camera_id: str = Field(..., description="Camera identifier")
    name: str = Field(..., description="Camera name")
    status: str = Field(..., description="Camera status")
    fps: float = Field(..., description="Current FPS")
    resolution: str = Field(..., description="Camera resolution")
    backend: str = Field(..., description="Camera backend")
    last_frame_time: Optional[datetime] = Field(None, description="Last frame timestamp")

class DetectionStats(BaseModel):
    total_detections: int = Field(..., description="Total detections")
    fall_detections: int = Field(..., description="Fall detections")
    false_positives: int = Field(..., description="False positive count")
    accuracy: float = Field(..., description="Detection accuracy")
    avg_processing_time: float = Field(..., description="Average processing time")
    avg_fps: float = Field(..., description="Average FPS")

# Dependency injection
def get_firestore_manager():
    """Firestore manager dependency."""
    try:
        return FirestoreManager()
    except Exception as e:
        logging.error(f"Firestore manager oluşturulamadı: {e}")
        raise HTTPException(status_code=503, detail="Database service unavailable")

def get_storage_manager():
    """Storage manager dependency."""
    try:
        return StorageManager()
    except Exception as e:
        logging.error(f"Storage manager oluşturulamadı: {e}")
        raise HTTPException(status_code=503, detail="Storage service unavailable")

def get_fall_detector():
    """Fall detector dependency."""
    try:
        return FallDetector.get_instance()
    except Exception as e:
        logging.error(f"Fall detector alınamadı: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")

# Ana Endpoints
@router.get("/", response_model=Dict[str, str])
async def root():
    """API root endpoint."""
    return {
        "message": "Guard AI Ultra API v2.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "version": "2.0.0"
    }

@router.get("/health", response_model=Dict[str, Any])
async def health_check(db: FirestoreManager = Depends(get_firestore_manager)):
    """Sistem sağlık kontrolü."""
    try:
        # Database bağlantısı test
        db_status = "healthy"
        try:
            # Basit bir test sorgusu
            test_result = db.health_check() if hasattr(db, 'health_check') else True
            if not test_result:
                db_status = "unhealthy"
        except Exception:
            db_status = "error"
        
        # AI model durumu
        ai_status = "healthy"
        try:
            detector = FallDetector.get_instance()
            if not detector.is_model_loaded:
                ai_status = "unhealthy"
        except Exception:
            ai_status = "error"
        
        return {
            "status": "healthy" if db_status == "healthy" and ai_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": db_status,
                "ai_model": ai_status,
                "api": "healthy"
            },
            "uptime": time.time() - (getattr(health_check, 'start_time', time.time()))
        }
    except Exception as e:
        logging.error(f"Health check hatası: {e}")
        raise HTTPException(status_code=503, detail="Health check failed")

# Event Endpoints
@router.get("/events/{user_id}", response_model=List[FallEvent])
async def get_events(
    user_id: str,
    limit: int = Query(50, le=100, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    db: FirestoreManager = Depends(get_firestore_manager)
):
    """Kullanıcının düşme olaylarını getirir."""
    try:
        # Firestore'dan olayları getir
        filters = {"user_id": user_id}
        if event_type:
            filters["event_type"] = event_type.value
        if start_date:
            filters["timestamp_gte"] = start_date
        if end_date:
            filters["timestamp_lte"] = end_date
        
        events = db.get_fall_events(
            user_id=user_id,
            limit=limit,
            offset=offset,
            filters=filters
        )
        
        return [FallEvent(**event) for event in events]
        
    except Exception as e:
        logging.error(f"Events getirme hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve events")

@router.post("/events/", response_model=FallEvent)
async def create_event(
    event: FallEvent,
    background_tasks: BackgroundTasks,
    db: FirestoreManager = Depends(get_firestore_manager)
):
    """Yeni bir düşme olayı kaydeder."""
    try:
        # Event ID generate et
        if not event.id:
            event.id = f"evt_{uuid.uuid4().hex[:12]}"
        
        # Firestore'a kaydet
        event_data = event.dict()
        event_data["timestamp"] = event.timestamp.isoformat()
        
        result = db.save_fall_event(event_data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to save event")
        
        # Arka planda bildirim gönder
        background_tasks.add_task(send_notification_async, event)
        
        logging.info(f"Yeni düşme olayı kaydedildi: {event.id}")
        return event
        
    except Exception as e:
        logging.error(f"Event kaydetme hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to create event")

@router.get("/events/{user_id}/{event_id}", response_model=FallEvent)
async def get_event(
    user_id: str,
    event_id: str,
    db: FirestoreManager = Depends(get_firestore_manager)
):
    """Belirli bir olayın detaylarını getirir."""
    try:
        event_data = db.get_fall_event(user_id, event_id)
        if not event_data:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return FallEvent(**event_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Event getirme hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve event")

@router.delete("/events/{user_id}/{event_id}")
async def delete_event(
    user_id: str,
    event_id: str,
    db: FirestoreManager = Depends(get_firestore_manager)
):
    """Belirli bir olayı siler."""
    try:
        result = db.delete_fall_event(user_id, event_id)
        if not result:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {"message": "Event deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Event silme hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete event")

# Settings Endpoints
@router.get("/settings/{user_id}", response_model=UserSettings)
async def get_settings(
    user_id: str,
    db: FirestoreManager = Depends(get_firestore_manager)
):
    """Kullanıcı ayarlarını getirir."""
    try:
        user_data = db.get_user_data(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        settings = user_data.get("settings", {})
        settings["user_id"] = user_id
        
        return UserSettings(**settings)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Settings getirme hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")

@router.post("/settings/", response_model=UserSettings)
async def update_settings(
    settings: UserSettings,
    db: FirestoreManager = Depends(get_firestore_manager)
):
    """Kullanıcı ayarlarını günceller."""
    try:
        settings_data = settings.dict()
        user_id = settings_data.pop("user_id")
        
        result = db.save_user_settings(user_id, settings_data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update settings")
        
        logging.info(f"Kullanıcı ayarları güncellendi: {user_id}")
        return settings
        
    except Exception as e:
        logging.error(f"Settings güncelleme hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

# System Information Endpoints
@router.get("/system/info", response_model=SystemInfo)
async def get_system_info(detector: FallDetector = Depends(get_fall_detector)):
    """Sistem bilgilerini getirir."""
    try:
        model_info = detector.get_enhanced_model_info()
        detection_summary = detector.get_detection_summary()
        
        return SystemInfo(
            version="2.0.0",
            status=SystemStatus.ACTIVE if model_info["model_loaded"] else SystemStatus.ERROR,
            uptime=model_info["uptime"],
            active_cameras=detection_summary["active_tracks"],
            ai_model_loaded=model_info["model_loaded"],
            detection_count=detection_summary["total_detections"],
            fall_count=detection_summary["fall_detections"],
            last_detection=datetime.utcnow() if detection_summary["total_detections"] > 0 else None
        )
        
    except Exception as e:
        logging.error(f"System info hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system info")

@router.get("/system/stats", response_model=DetectionStats)
async def get_detection_stats(detector: FallDetector = Depends(get_fall_detector)):
    """Algılama istatistiklerini getirir."""
    try:
        summary = detector.get_detection_summary()
        performance = detector._get_performance_metrics()
        
        return DetectionStats(
            total_detections=summary["total_detections"],
            fall_detections=summary["fall_detections"],
            false_positives=detector.detection_stats.get("false_positives", 0),
            accuracy=performance["detection_accuracy"],
            avg_processing_time=performance["avg_processing_time"],
            avg_fps=performance["fps"]
        )
        
    except Exception as e:
        logging.error(f"Detection stats hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve detection stats")

@router.get("/cameras/", response_model=List[CameraInfo])
async def get_cameras():
    """Aktif kameraların listesini getirir."""
    try:
        available_cameras = Camera.get_available_cameras()
        
        camera_list = []
        for cam_info in available_cameras:
            camera_list.append(CameraInfo(
                camera_id=f"camera_{cam_info['index']}",
                name=cam_info['name'],
                status="active" if cam_info['working'] else "inactive",
                fps=cam_info.get('fps', 0),
                resolution=cam_info['resolution'],
                backend=cam_info['backend_name'],
                last_frame_time=datetime.utcnow()
            ))
        
        return camera_list
        
    except Exception as e:
        logging.error(f"Camera listesi hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve camera list")

@router.get("/cameras/{camera_id}/status", response_model=CameraInfo)
async def get_camera_status(camera_id: str):
    """Belirli bir kameranın durumunu getirir."""
    try:
        # Camera ID'den index çıkar
        camera_index = int(camera_id.split("_")[-1])
        
        # Kamera durumunu kontrol et
        camera = Camera(camera_index)
        status = camera.get_camera_status()
        
        return CameraInfo(
            camera_id=camera_id,
            name=f"Camera {camera_index}",
            status=status["connection"],
            fps=status["fps"],
            resolution=f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
            backend=status["backend_name"],
            last_frame_time=datetime.fromtimestamp(status["last_frame_time"]) if status["last_frame_time"] > 0 else None
        )
        
    except Exception as e:
        logging.error(f"Camera status hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve camera status")

# Real-time Endpoints
@router.get("/stream/events")
async def stream_events(user_id: str):
    """Gerçek zamanlı olay akışı (Server-Sent Events)."""
    async def event_generator():
        while True:
            # Burada gerçek zamanlı olayları dinleyecek kod olacak
            # Şimdilik sahte veri gönderiyoruz
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(30)  # 30 saniyede bir heartbeat
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@router.post("/test/fall-detection")
async def test_fall_detection(
    background_tasks: BackgroundTasks,
    user_id: str,
    confidence: float = Query(0.95, ge=0.0, le=1.0),
    detector: FallDetector = Depends(get_fall_detector)
):
    """Test amaçlı düşme algılama simülasyonu."""
    try:
        # Test event oluştur
        test_event = FallEvent(
            id=f"test_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            confidence=confidence,
            camera_id="test_camera",
            detection_method="YOLOv11_Test",
            event_type=EventType.FALL_DETECTION,
            pose_analysis={
                "valid_points": 15,
                "stability": 0.8,
                "tilt_angle": 85.0
            }
        )
        
        # Arka planda bildirim gönder
        background_tasks.add_task(send_notification_async, test_event)
        
        logging.info(f"Test düşme algılama simülasyonu: {test_event.id}")
        return {"message": "Test fall detection triggered", "event": test_event}
        
    except Exception as e:
        logging.error(f"Test fall detection hatası: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger test detection")

# Yardımcı fonksiyonlar
async def send_notification_async(event: FallEvent):
    """Arka planda bildirim gönderir."""
    try:
        # NotificationManager ile bildirim gönder
        # Bu fonksiyon asenkron olarak çalışacak
        logging.info(f"Bildirim gönderiliyor: {event.id}")
        # Burada gerçek bildirim gönderme kodu olacak
        
    except Exception as e:
        logging.error(f"Bildirim gönderme hatası: {e}")

# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Startup event
@router.on_event("startup")
async def startup_event():
    """API başlatma eventi."""
    logging.info("Guard AI Ultra API başlatıldı")
    # Başlangıç zamanını kaydet
    setattr(health_check, 'start_time', time.time())

@router.on_event("shutdown")
async def shutdown_event():
    """API kapatma eventi."""
    logging.info("Guard AI Ultra API kapatılıyor")