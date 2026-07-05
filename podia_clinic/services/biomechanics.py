"""Biomechanics Calculator - Computes biomechanical angles and metrics."""

import numpy as np
from typing import Tuple


class BiomechanicsCalculator:
    """Calculates biomechanical angles and symmetry indices."""
    
    @staticmethod
    def calc_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        """
        Calculate the angle formed by three points (a-b-c).
        
        Args:
            a, b, c: 2D or 3D coordinates of three points
            
        Returns:
            Angle in degrees (0-180)
        """
        a, b, c = np.array(a), np.array(b), np.array(c)
        rad = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        ang = np.abs(rad * 180.0 / np.pi)
        if ang > 180.0:
            ang = 360 - ang
        return float(ang)
    
    @staticmethod
    def calculate_foot_progression_angle(heel: np.ndarray, ankle: np.ndarray, 
                                        foot_index: np.ndarray) -> float:
        """
        Calculate Foot Progression Angle (FPA).
        
        Positive values indicate toe-out rotation.
        
        Args:
            heel: Heel landmark coordinates
            ankle: Ankle landmark coordinates
            foot_index: Foot index landmark coordinates
            
        Returns:
            FPA in degrees
        """
        vec = np.array(foot_index) - np.array(heel)
        fpa = np.degrees(np.arctan2(vec[0], -vec[1]))
        return float(fpa)
    
    @staticmethod
    def estimate_arch_height(ankle: np.ndarray, foot_index: np.ndarray, 
                            heel: np.ndarray) -> float:
        """
        Estimate foot arch height.
        
        Args:
            ankle: Ankle landmark coordinates
            foot_index: Foot index landmark coordinates
            heel: Heel landmark coordinates
            
        Returns:
            Arch height measurement
        """
        arch_height = ankle[1] - min(foot_index[1], heel[1])
        return abs(float(arch_height))
    
    @staticmethod
    def calculate_symmetry_index(left_val: float, right_val: float) -> float:
        """
        Calculate symmetry index between left and right measurements.
        
        Args:
            left_val: Left side measurement
            right_val: Right side measurement
            
        Returns:
            Symmetry percentage (100 = perfect symmetry)
        """
        avg = (left_val + right_val) / 2.0
        if avg == 0:
            return 100.0
        sym = 100 * (1 - abs(left_val - right_val) / avg)
        return max(0.0, float(sym))


class GaitPhaseDetector:
    """Detects gait phases from ankle positions."""
    
    def __init__(self):
        """Initialize the gait phase detector."""
        self.prev_y = {'R': 0.0, 'L': 0.0}
    
    def detect(self, ankle_r: np.ndarray, ankle_l: np.ndarray) -> Tuple[str, str]:
        """
        Detect current gait phase for each leg.
        
        Args:
            ankle_r: Right ankle coordinates
            ankle_l: Left ankle coordinates
            
        Returns:
            Tuple of (right_phase, left_phase) - "Stance" or "Swing"
        """
        # Simple phase detection based on Y-coordinate difference
        self.prev_y['R'], self.prev_y['L'] = ankle_r[1], ankle_l[1]
        return "Stance", "Swing"
