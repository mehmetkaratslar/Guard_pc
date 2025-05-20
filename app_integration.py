# File: app_integration.py
# Description: Geliştirilen özellikleri ana uygulamaya entegre eder

import logging
import os
import sys

# Özel modülleri içe aktarın
from utils.password_reset_handler import PasswordResetHandler
from utils.user_settings_manager import UserSettingsManager
from ui.enhanced_settings import EnhancedSettingsFrame

def entegre_et(app):
    """
    Geliştirilen özellikleri ana uygulamaya entegre eder.
    
    Args:
        app (GuardApp): Ana uygulama örneği
    """
    try:
        logging.info("Gelişmiş özellikler entegre ediliyor...")
        
        # Orijinal show_settings metodunu yedekle
        original_show_settings = app.show_settings
        
        # show_settings metodunu geliştir
        def enhanced_show_settings():
            """Gelişmiş ayarlar ekranını gösterir."""
            # Önce orijinal metodu çağır
            original_show_settings()
            
            # Şimdi geliştirmeleri uygula
            if hasattr(app, "settings_frame"):
                try:
                    # EnhancedSettingsFrame örneği oluştur
                    enhanced_settings = EnhancedSettingsFrame(
                        app.settings_frame,
                        app.current_user,
                        app.auth,
                        app.db_manager
                    )
                    
                    # Referansı sakla
                    app.enhanced_settings = enhanced_settings
                    
                    logging.info("Gelişmiş ayarlar ekranı başarıyla uygulandı.")
                except Exception as e:
                    logging.error(f"Gelişmiş ayarlar ekranı uygulanırken hata: {str(e)}")
        
        # Metodu geliştirilen versiyonla değiştir
        app.show_settings = enhanced_show_settings
        
        # Kullanıcı ayarları yöneticisini oluştur ve global olarak sakla
        app.settings_manager = UserSettingsManager(app.auth, app.db_manager)
        
        # Şifre sıfırlama işleyicisini oluştur ve global olarak sakla
        app.password_handler = PasswordResetHandler(app.auth)
        
        logging.info("Gelişmiş özellikler başarıyla entegre edildi.")
        return True
        
    except Exception as e:
        logging.error(f"Özellik entegrasyonu sırasında hata: {str(e)}")
        return False