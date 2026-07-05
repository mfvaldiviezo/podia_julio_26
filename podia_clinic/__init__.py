"""
AsistIA V5 - PodiaAI Clinic
Sistema profesional de análisis biomecánico y monitoreo de postura podológica.
"""

from .config import Config
from .models.state_manager import ClinicStateManager
from .models.patient_manager import PatientManager
from .services.voice_engine import VoiceEngine
from .services.signal_processor import SignalProcessor
from .services.biomechanics import BiomechanicsCalculator, GaitPhaseDetector
from .services.ml_classifier import GaitMLClassifier
from .services.video_processor import VideoProcessor
from .routes.main_routes import init_routes
from .routes.test_routes import create_test_routes
from .utils.logging_setup import setup_logging


def create_app():
    """Application factory for Flask app."""
    from flask import Flask
    
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE
    
    # Setup logging
    app_log = setup_logging()
    
    # Initialize global services
    state = ClinicStateManager()
    voice = VoiceEngine()
    processor = SignalProcessor()
    ml_engine = GaitMLClassifier()
    
    # Register main routes
    init_routes(app, state, voice, processor, ml_engine, app_log)
    
    # Register test routes
    create_test_routes(app, state, app_log)
    
    return app, app_log


if __name__ == '__main__':
    app, app_log = create_app()
    app.run(host='127.0.0.1', port=5001, debug=False)
