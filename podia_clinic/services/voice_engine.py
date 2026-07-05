"""Voice Engine - Text-to-speech service for clinical alerts."""

import queue
import threading
import time
from typing import Optional

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


class VoiceEngine:
    """Provides text-to-speech functionality for clinical feedback."""
    
    def __init__(self, rate: int = 140, cooldown: float = 5.0):
        """
        Initialize the voice engine.
        
        Args:
            rate: Speech rate in words per minute
            cooldown: Minimum seconds between normal priority messages
        """
        self.queue = queue.PriorityQueue()
        self.last_played = 0.0
        self.engine: Optional[Any] = None
        self.cooldown = cooldown
        
        # Start worker thread
        self._start_worker(rate)
    
    def _start_worker(self, rate: int) -> None:
        """Start the TTS worker thread."""
        def worker():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                
                if TTS_AVAILABLE:
                    self.engine = pyttsx3.init()
                    self.engine.setProperty('rate', rate)
                else:
                    print("Warning: pyttsx3 not available. Voice alerts disabled.")
                    return
                    
            except Exception as e:
                print(f"Warning: TTS initialization failed: {e}. System will operate without audio.")
                self.engine = None
                return
            
            while True:
                priority, _, msg = self.queue.get()
                if msg is None:
                    break
                    
                if self.engine:
                    try:
                        self.engine.say(msg)
                        self.engine.runAndWait()
                    except Exception as e:
                        print(f"TTS error: {e}")
                        
                self.queue.task_done()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def alert(self, msg: str, priority: str = 'normal') -> None:
        """
        Queue a voice alert.
        
        Args:
            msg: Message to speak
            priority: 'high' or 'normal' (high priority skips cooldown)
        """
        now = time.time()
        pri_num = 1 if priority == 'high' else 2
        
        # Debounce/cooldown to prevent saturation
        if priority == 'normal' and now - self.last_played < self.cooldown:
            return
            
        self.last_played = now
        self.queue.put((pri_num, now, msg))
    
    def stop(self) -> None:
        """Stop the voice engine gracefully."""
        self.queue.put((0, time.time(), None))
