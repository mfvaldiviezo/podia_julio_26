"""Clinic State Manager - Manages application state and session data."""

import json
import os
import threading
from collections import deque
from typing import Any, Dict, Optional

from ..config import Config


class ClinicStateManager:
    """Manages the clinic's operational state, including session data and ML buffers."""
    
    def __init__(self):
        self.lock = threading.RLock()
        self.session_data = deque(maxlen=50000)
        self.ml_features_buffer = deque(maxlen=2000)
        self.ml_labels_buffer = deque(maxlen=2000)
        self.current_live_angles: Dict[str, float] = {}
        self.current_fps: float = 0.0
        self.session_active: bool = False
        self.system_status_msg: str = "Esperando feed clínico..."
        
        # Configuration file paths
        self.config_db = Config.CONFIG_DB_PATH
        self.buffers_db = Config.ML_BUFFERS_PATH
        
        # Clinical measurement ranges
        self.clinical_ranges = Config.CLINICAL_RANGES.copy()
        
        # Session state
        self.current_patient_id: Optional[str] = None
        self.test_mode: Optional[Dict[str, Any]] = None
        
        # Load persisted state
        self.load_state()
    
    def load_state(self) -> None:
        """Load state from persistent storage."""
        # Load ML buffers
        if os.path.exists(self.buffers_db):
            try:
                with open(self.buffers_db, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.ml_features_buffer = deque(data.get('features', []), maxlen=2000)
                    self.ml_labels_buffer = deque(data.get('labels', []), maxlen=2000)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load ML buffers: {e}")
        
        # Load clinical ranges configuration
        if os.path.exists(self.config_db):
            try:
                with open(self.config_db, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    loaded_ranges = data.get('ranges', {})
                    if loaded_ranges:
                        self.clinical_ranges.update(loaded_ranges)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config: {e}")
    
    def save_state(self) -> None:
        """Save current state to persistent storage."""
        with self.lock:
            try:
                # Save ML buffers
                with open(self.buffers_db, 'w', encoding='utf-8') as f:
                    json.dump({
                        'features': list(self.ml_features_buffer),
                        'labels': list(self.ml_labels_buffer)
                    }, f)
                
                # Save clinical ranges configuration
                with open(self.config_db, 'w', encoding='utf-8') as f:
                    json.dump({'ranges': self.clinical_ranges}, f)
                    
            except Exception as e:
                print(f"Error saving state: {e}")
    
    def set_active_session(self, active: bool) -> None:
        """Set session active state."""
        with self.lock:
            self.session_active = active
    
    def update_live_angles(self, angles: Dict[str, float]) -> None:
        """Update current live angle measurements."""
        with self.lock:
            self.current_live_angles = angles
    
    def get_live_angles(self) -> Dict[str, float]:
        """Get current live angle measurements."""
        with self.lock:
            return self.current_live_angles.copy()
    
    def add_ml_sample(self, features: list, label: int) -> None:
        """Add a sample to the ML training buffers."""
        with self.lock:
            self.ml_features_buffer.append(features)
            self.ml_labels_buffer.append(label)
    
    def get_ml_buffers(self) -> tuple:
        """Get copies of ML feature and label buffers."""
        with self.lock:
            return list(self.ml_features_buffer).copy(), list(self.ml_labels_buffer).copy()
