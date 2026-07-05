"""Configuration constants for the application."""

import os


class Config:
    """Application configuration settings."""
    
    # Directory structure
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
    PATIENTS_FOLDER = os.path.join(BASE_DIR, 'patients')
    LOGS_FOLDER = os.path.join(BASE_DIR, 'logs')
    
    # Ensure directories exist
    for directory in [UPLOAD_FOLDER, REPORTS_FOLDER, PATIENTS_FOLDER, LOGS_FOLDER]:
        os.makedirs(directory, exist_ok=True)
    
    # File upload limits
    MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200MB
    
    # Authentication credentials (should be moved to environment variables)
    AUTH_USERNAME = 'admin'
    AUTH_PASSWORD = 'clinic2026'
    
    # Clinical ranges for biomechanical analysis
    CLINICAL_RANGES = {
        'ankle_dorsiflexion': {'min': 70, 'max': 180, 'unit': '°'},
        'knee_flexion': {'min': 150, 'max': 180, 'unit': '°'},
        'hip_extension': {'min': 150, 'max': 180, 'unit': '°'},
        'foot_progression_angle': {'min': -15, 'max': 15, 'unit': '°'}
    }
    
    # ML model settings
    ML_MODEL_PATH = os.path.join(LOGS_FOLDER, 'gait_model.pkl')
    ML_BUFFERS_PATH = os.path.join(BASE_DIR, 'ml_buffers_backup.json')
    CONFIG_DB_PATH = os.path.join(BASE_DIR, 'config_clinic.json')
    
    # Logging settings
    LOG_FILE = os.path.join(LOGS_FOLDER, 'podia_ai_clinic.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_LEVEL = 'INFO'
    
    # Voice engine settings
    VOICE_RATE = 140
    VOICE_COOLDOWN_NORMAL = 5.0  # seconds
    
    # Signal processing settings
    SIGNAL_WINDOW_SIZE = 5
    OUTLIER_THRESHOLD = 2.5
    
    # Gait classification labels
    GAIT_CLASSES = {
        1: "Marcha Normativa",
        2: "Pronación Dinámica",
        3: "Supinación / Arco Elevado",
        4: "Asimetría Significativa",
        5: "Patrón Compensatorio"
    }
