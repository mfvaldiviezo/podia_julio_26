"""Patient Manager - Handles patient data operations."""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import Config


class PatientManager:
    """Manages patient records and data persistence."""
    
    @staticmethod
    def create_patient(data: Dict[str, Any]) -> str:
        """
        Create a new patient record.
        
        Args:
            data: Dictionary containing patient information
            
        Returns:
            Patient ID
        """
        pid = str(uuid.uuid4())[:8]
        patient_data = {
            'id': pid,
            'name': data.get('name', 'Anónimo'),
            'age': int(data.get('age', 0)) if data.get('age') else 0,
            'sex': data.get('sex', 'U'),
            'clinical_notes': data.get('clinical_notes', data.get('notes', '')),
            'foot_type': data.get('foot_type', 'Normal'),
            'created_at': datetime.now().isoformat()
        }
        
        path = os.path.join(Config.PATIENTS_FOLDER, f"{pid}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(patient_data, f, ensure_ascii=False, indent=2)
        
        return pid
    
    @staticmethod
    def get_patient(pid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve patient data by ID.
        
        Args:
            pid: Patient ID
            
        Returns:
            Patient data dictionary or None if not found
        """
        path = os.path.join(Config.PATIENTS_FOLDER, f"{pid}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    @staticmethod
    def list_patients() -> list:
        """List all patients in the system."""
        patients = []
        if os.path.exists(Config.PATIENTS_FOLDER):
            for filename in os.listdir(Config.PATIENTS_FOLDER):
                if filename.endswith('.json'):
                    path = os.path.join(Config.PATIENTS_FOLDER, filename)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            patients.append(json.load(f))
                    except (json.JSONDecodeError, IOError):
                        continue
        return patients
    
    @staticmethod
    def delete_patient(pid: str) -> bool:
        """
        Delete a patient record.
        
        Args:
            pid: Patient ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        path = os.path.join(Config.PATIENTS_FOLDER, f"{pid}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except OSError:
                return False
        return False
    
    @staticmethod
    def update_patient(pid: str, updates: Dict[str, Any]) -> bool:
        """
        Update patient information.
        
        Args:
            pid: Patient ID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        patient = PatientManager.get_patient(pid)
        if not patient:
            return False
        
        # Update allowed fields
        allowed_fields = ['name', 'age', 'sex', 'clinical_notes', 'foot_type']
        for field in allowed_fields:
            if field in updates:
                if field == 'age' and updates.get('age'):
                    patient[field] = int(updates['age'])
                else:
                    patient[field] = updates[field]
        
        path = os.path.join(Config.PATIENTS_FOLDER, f"{pid}.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(patient, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False
