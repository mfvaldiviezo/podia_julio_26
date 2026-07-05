"""Video Processor - Handles video capture and frame processing."""

import cv2
import mediapipe as mp
import os
import time
from typing import Generator, Optional, Tuple, Any


class VideoProcessor:
    """Processes video streams for biomechanical analysis."""
    
    def __init__(self):
        """Initialize the video processor with MediaPipe Pose."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            model_complexity=1,
            smooth_landmarks=True
        )
    
    @staticmethod
    def open_camera(source: int) -> Optional[cv2.VideoCapture]:
        """
        Attempt to open a camera source with retries.
        
        Args:
            source: Camera index (integer)
            
        Returns:
            VideoCapture object or None if failed
        """
        cap = None
        tries = 0
        while tries < 5:
            cap = cv2.VideoCapture(source)
            if cap and cap.isOpened():
                return cap
            tries += 1
            time.sleep(1)
        
        if cap:
            cap.release()
        return None
    
    @staticmethod
    def open_video_file(path: str) -> Optional[cv2.VideoCapture]:
        """
        Open a video file.
        
        Args:
            path: Path to video file
            
        Returns:
            VideoCapture object or None if failed
        """
        if not os.path.exists(path):
            return None
        
        cap = cv2.VideoCapture(path)
        if cap and cap.isOpened():
            return cap
        
        cap.release()
        return None
    
    def process_frame(self, frame: np.ndarray, biomech, processor, state, voice, logger):
        """
        Process a single video frame for biomechanical analysis.
        
        Args:
            frame: Input video frame (BGR format)
            biomech: BiomechanicsCalculator instance
            processor: SignalProcessor instance
            state: ClinicStateManager instance
            voice: VoiceEngine instance
            logger: Logger instance
            
        Returns:
            Tuple of (processed_image, angles_dict, feature_vector, alert_text)
        """
        # Convert to RGB for MediaPipe
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        current_angles = {}
        feature_vector = None
        pron_text = None
        metrics_display = []
        
        if results.pose_landmarks:
            lms = results.pose_landmarks.landmark
            
            # Validate critical landmarks visibility
            critical_indices = [23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
            critical_vis = [lms[i].visibility for i in critical_indices]
            min_critical_vis = min(critical_vis)
            
            if min_critical_vis < 0.6:
                logger.warning(f"Insufficient visibility ({min_critical_vis:.2f}). Incorrect framing.")
                cv2.putText(image, "🚫 ENCUADRE INCORRECTO - Muestre pies/tobillos", 
                           (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                return image, {}, None, None
            
            # Draw landmarks
            mp.solutions.drawing_utils.draw_landmarks(
                image, results.pose_landmarks, 
                mp.solutions.pose.POSE_CONNECTIONS,
                mp.solutions.drawing_utils.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=1),
                mp.solutions.drawing_utils.DrawingSpec(color=(255, 50, 50), thickness=2, circle_radius=1)
            )
            
            # Extract landmark coordinates
            def get_cp(lm):
                return [lm.x, lm.y]
            
            try:
                # Calculate angles using biomechanics calculator
                r_an = get_cp(lms[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value])
                r_ft = get_cp(lms[self.mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value])
                r_he = get_cp(lms[self.mp_pose.PoseLandmark.RIGHT_HEEL.value])
                l_sh = get_cp(lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value])
                l_hp = get_cp(lms[self.mp_pose.PoseLandmark.LEFT_HIP.value])
                l_kn = get_cp(lms[self.mp_pose.PoseLandmark.LEFT_KNEE.value])
                l_an = get_cp(lms[self.mp_pose.PoseLandmark.LEFT_ANKLE.value])
                l_ft = get_cp(lms[self.mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value])
                l_he = get_cp(lms[self.mp_pose.PoseLandmark.LEFT_HEEL.value])
                r_sh = get_cp(lms[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value])
                r_hp = get_cp(lms[self.mp_pose.PoseLandmark.RIGHT_HIP.value])
                r_kn = get_cp(lms[self.mp_pose.PoseLandmark.RIGHT_KNEE.value])
                
                # Apply filtering to angle measurements
                r_knee_ang = processor.kalman_filter_1d(biomech.calc_angle(r_hp, r_kn, r_an), 'rk')
                l_knee_ang = processor.kalman_filter_1d(biomech.calc_angle(l_hp, l_kn, l_an), 'lk')
                r_ankle_ang = processor.kalman_filter_1d(biomech.calc_angle(r_kn, r_an, r_ft), 'ra')
                l_ankle_ang = processor.kalman_filter_1d(biomech.calc_angle(l_kn, l_an, l_ft), 'la')
                r_hip_ang = processor.kalman_filter_1d(biomech.calc_angle(r_sh, r_hp, r_kn), 'rh')
                l_hip_ang = processor.kalman_filter_1d(biomech.calc_angle(l_sh, l_hp, l_kn), 'lh')
                r_fpa = processor.kalman_filter_1d(biomech.calculate_foot_progression_angle(r_he, r_an, r_ft), 'rfpa')
                l_fpa = processor.kalman_filter_1d(biomech.calculate_foot_progression_angle(l_he, l_an, l_ft), 'lfpa')
                r_arch = biomech.estimate_arch_height(r_an, r_ft, r_he)
                l_arch = biomech.estimate_arch_height(l_an, l_ft, l_he)
                symmetry = biomech.calculate_symmetry_index(l_knee_ang, r_knee_ang)
                
                current_angles = {
                    'r_ankle': r_ankle_ang, 
                    'l_ankle': l_ankle_ang,
                    'r_knee': r_knee_ang, 
                    'l_knee': l_knee_ang, 
                    'symmetry': symmetry
                }
                
                feature_vector = [
                    r_ankle_ang, l_ankle_ang, r_knee_ang, l_knee_ang,
                    r_hip_ang, l_hip_ang, r_fpa, l_fpa, r_arch, l_arch, symmetry
                ]
                
                # Check against clinical ranges
                c_rng = state.clinical_ranges
                def in_range(val, key):
                    return c_rng[key]['min'] <= val <= c_rng[key]['max']
                
                t_d_ok = in_range(r_ankle_ang, 'ankle_dorsiflexion')
                metrics_display.append(f"Tobillo D: {r_ankle_ang:.1f}   [{'OK' if t_d_ok else 'WR'}]")
                metrics_display.append(f"Tobillo I: {l_ankle_ang:.1f}   [{'OK' if in_range(l_ankle_ang, 'ankle_dorsiflexion') else 'WR'}]")
                metrics_display.append(f"Rodilla D: {r_knee_ang:.1f}   [{'OK' if in_range(r_knee_ang, 'knee_flexion') else 'WR'}]")
                metrics_display.append(f"Rodilla I: {l_knee_ang:.1f}   [{'OK' if in_range(l_knee_ang, 'knee_flexion') else 'WR'}]")
                metrics_display.append(f"FPA Der  : {r_fpa:+.1f}     [{'OK' if in_range(r_fpa, 'foot_progression_angle') else 'WR'}]")
                
                # Generate alerts
                if r_fpa > 15 and not t_d_ok:
                    pron_text = "PRONACION Dinamica Detectada"
                    voice.alert("Extrema Pronación Visualizada", "high")
                elif symmetry < 85:
                    pron_text = f"ASIMETRIA MARCH: {symmetry:.0f}%"
                
                # Draw metrics overlay
                cv2.rectangle(image, (10, 10), 
                            (330, 20 + len(metrics_display)*25 + (30 if pron_text else 0)), 
                            (245, 245, 245), -1)
                cv2.putText(image, "METRICAS BIOMECANICAS:", (20, 30), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.6, (50, 50, 50), 1)
                for i, m in enumerate(metrics_display):
                    col = (0, 150, 0) if 'OK' in m else (0, 0, 200)
                    cv2.putText(image, m, (20, 55 + i*25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
                if pron_text:
                    yp = 55 + len(metrics_display)*25
                    cv2.rectangle(image, (15, yp-5), (320, yp+20), (0, 200, 255), -1)
                    cv2.putText(image, f"! {pron_text} !", (20, yp+12), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                    
            except Exception as e:
                logger.warning(f"Error calculating angles: {e}")
                current_angles = {}
                feature_vector = None
        
        return image, current_angles, feature_vector, pron_text
    
    def generate_frames(self, source: Any, biomech, processor, state, voice, logger) -> Generator[bytes, None, None]:
        """
        Generate processed frames from a video source.
        
        Args:
            source: Camera index or video file path
            biomech: BiomechanicsCalculator instance
            processor: SignalProcessor instance
            state: ClinicStateManager instance
            voice: VoiceEngine instance
            logger: Logger instance
            
        Yields:
            JPEG-encoded frames
        """
        # Open video source
        if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
            cap = self.open_camera(int(source))
        else:
            cap = self.open_video_file(str(source))
        
        if not cap:
            logger.error(f"Failed to open video source: {source}")
            return
        
        logger.info(f"Successfully opened video source: {source}")
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                processed, _, _, _ = self.process_frame(
                    frame, biomech, processor, state, voice, logger
                )
                
                # Encode as JPEG
                _, buffer = cv2.imencode('.jpg', processed)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
        finally:
            cap.release()
    
    def release(self):
        """Release MediaPipe resources."""
        self.pose.close()
