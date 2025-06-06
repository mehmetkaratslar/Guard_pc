# guard_pc_app/core/firebase_init.py
import os
import firebase_admin
from firebase_admin import credentials

def initialize_firebase():
    if not firebase_admin._apps:
        json_path = os.path.join(os.path.dirname(__file__), '../serviceAccountKey.json')
        cred = credentials.Certificate(json_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'guard-12345.appspot.com'  # Burayı kendi bucket adınla değiştir
        })
