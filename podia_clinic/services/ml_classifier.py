"""Machine Learning Classifier for gait pattern classification."""

import os
from typing import Tuple, Optional

try:
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class GaitMLClassifier:
    """Random Forest classifier for gait pattern analysis."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize the ML classifier.
        
        Args:
            model_path: Path to saved model file
        """
        self.model = None
        self.model_path = model_path or 'logs/gait_model.pkl'
        self.classes = {
            1: "Marcha Normativa",
            2: "Pronación Dinámica",
            3: "Supinación / Arco Elevado",
            4: "Asimetría Significativa",
            5: "Patrón Compensatorio"
        }
        
        # Try to load existing model
        if os.path.exists(self.model_path) and ML_AVAILABLE:
            try:
                self.model = joblib.load(self.model_path)
            except Exception as e:
                print(f"Warning: Failed to load ML model: {e}")
    
    def train_from_buffers(self, features: list, labels: list) -> Tuple[bool, str]:
        """
        Train the classifier from buffered data.
        
        Args:
            features: List of feature vectors
            labels: List of corresponding labels
            
        Returns:
            Tuple of (success, message)
        """
        if not ML_AVAILABLE:
            return False, "Machine learning libraries not available"
        
        if len(features) < 15 or len(set(labels)) < 2:
            return False, "Insufficient data or lack of bi-modal classes"
        
        try:
            self.model = RandomForestClassifier(
                n_estimators=100,
                class_weight='balanced',
                random_state=42
            )
            self.model.fit(features, labels)
            joblib.dump(self.model, self.model_path)
            return True, "Model successfully trained and saved"
            
        except Exception as e:
            return False, str(e)
    
    def predict(self, feature_vector: list) -> Tuple[str, float]:
        """
        Predict gait pattern from feature vector.
        
        Args:
            feature_vector: 11-element feature array
            
        Returns:
            Tuple of (classification_label, confidence_percentage)
        """
        if not self.model:
            return "Sin IA Clasificadora", 0.0
        
        try:
            pred = self.model.predict([feature_vector])[0]
            prob = max(self.model.predict_proba([feature_vector])[0]) * 100
            return self.classes.get(pred, "Desconocido"), float(prob)
        except Exception as e:
            print(f"ML prediction error: {e}")
            return "Error Inferencial", 0.0
    
    def is_available(self) -> bool:
        """Check if ML model is loaded and ready."""
        return self.model is not None and ML_AVAILABLE
