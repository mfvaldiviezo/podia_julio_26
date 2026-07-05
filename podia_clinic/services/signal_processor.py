"""Signal Processor - Handles signal filtering and smoothing."""

import numpy as np
from collections import deque
from typing import Dict


class SignalProcessor:
    """Processes biomechanical signals with filtering and outlier detection."""
    
    def __init__(self, window_size: int = 5, outlier_threshold: float = 2.5):
        """
        Initialize the signal processor.
        
        Args:
            window_size: Window size for moving average
            outlier_threshold: Standard deviations for outlier detection
        """
        self.history: Dict[str, deque] = {}
        self.window_size = window_size
        self.outlier_threshold = outlier_threshold
    
    def get_moving_average(self, name: str, val: float, window: int = None) -> float:
        """
        Calculate moving average for a signal.
        
        Args:
            name: Signal identifier
            val: Current value
            window: Window size (overrides default if provided)
            
        Returns:
            Smoothed value
        """
        if window is None:
            window = self.window_size
            
        if name not in self.history:
            self.history[name] = deque(maxlen=window)
        
        self.history[name].append(val)
        return float(np.average(self.history[name]))
    
    def detect_outliers(self, values: np.ndarray) -> list:
        """
        Detect outliers using Median Absolute Deviation.
        
        Args:
            values: Array of values to check
            threshold: Override threshold if provided
            
        Returns:
            List of boolean flags indicating outliers
        """
        if len(values) < 3:
            return [False] * len(values)
        
        median = np.median(values)
        diff = np.abs(values - median)
        med_abs_deviation = np.median(diff)
        
        if med_abs_deviation == 0:
            return [False] * len(values)
        
        modified_z_scores = 0.6745 * diff / med_abs_deviation
        return (modified_z_scores > self.outlier_threshold).tolist()
    
    def kalman_filter_1d(self, measurement: float, name: str) -> float:
        """
        Apply simplified Kalman-like filtering (exponential moving average).
        
        Args:
            measurement: Current measurement
            name: Signal identifier
            
        Returns:
            Filtered value
        """
        return self.get_moving_average(name, measurement)
    
    def reset(self, name: str = None) -> None:
        """
        Reset signal history.
        
        Args:
            name: Specific signal to reset, or None to reset all
        """
        if name:
            if name in self.history:
                del self.history[name]
        else:
            self.history.clear()
