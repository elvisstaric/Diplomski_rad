import random
import math
from typing import Dict, Any

class WorkloadGenerator:
    
    def __init__(self, pattern: str, num_users: int, duration: int, pattern_config: Dict[str, Any] = None, 
                 user_model: str = "closed", arrival_rate: float = None, session_duration: float = None):
        self.pattern = pattern
        self.num_users = num_users
        self.duration = duration
        self.current_time = 0
        self.pattern_config = pattern_config or {}
        self.user_model = user_model
        self.arrival_rate = arrival_rate
        self.session_duration = session_duration
        
        self.spike_start_time = 0
        self.spike_active = False
        
    def get_next_delay(self):
        if self.pattern == "burst":
            if random.random() < 0.7:   
                return random.uniform(0.1, 0.5)
            else:
                return random.uniform(1.0, 3.0)
        
        elif self.pattern == "steady":
            return random.uniform(0.5, 1.5)
        
        elif self.pattern == "ramp_up":
            progress = self.current_time / self.duration
            base_delay = 2.0 - (progress * 1.5)
            return random.uniform(base_delay * 0.8, base_delay * 1.2)
        
        elif self.pattern == "daily_cycle":
            peak_hours = self.pattern_config.get("peak_hours", [9, 10, 11, 14, 15, 16])
            off_peak_multiplier = self.pattern_config.get("off_peak_multiplier", 0.3)
            base_delay = self.pattern_config.get("base_delay", 1.0)
            
            hour_in_day = (self.current_time / self.duration) * 24
            
            is_peak_hour = any(abs(hour_in_day - peak_hour) < 0.5 for peak_hour in peak_hours)
            
            if is_peak_hour:
              
                delay = base_delay * random.uniform(0.5, 1.0)
            else:
              
                delay = base_delay * off_peak_multiplier * random.uniform(1.0, 2.0)
            
            return delay
        
        elif self.pattern == "spike":
            spike_interval = self.pattern_config.get("spike_interval", 120)  
            spike_duration = self.pattern_config.get("spike_duration", 30)  
            spike_intensity = self.pattern_config.get("spike_intensity", 5.0)  
            base_delay = self.pattern_config.get("base_delay", 2.0)
            
            
            time_in_cycle = self.current_time % spike_interval
            
            if time_in_cycle < spike_duration:
                delay = base_delay / spike_intensity * random.uniform(0.1, 0.3)
            else:
                delay = base_delay * random.uniform(0.8, 1.5)
            
            return delay
            
        elif self.pattern == "gradual_ramp":
            start_delay = self.pattern_config.get("start_delay", 3.0)
            end_delay = self.pattern_config.get("end_delay", 0.5)
            ramp_steps = self.pattern_config.get("ramp_steps", 10)
           
            progress = self.current_time / self.duration
            step = int(progress * ramp_steps)
            step = min(step, ramp_steps - 1)

            
            step_progress = (step + 1) / ramp_steps
            current_delay = start_delay - (start_delay - end_delay) * step_progress
            
            
            delay = current_delay * random.uniform(0.7, 1.3)
            
            return delay
        
        else:
            return random.uniform(0.5, 2.0)
    
    
    def update_time(self, elapsed_time: float):
        self.current_time = elapsed_time
    
    def get_session_duration(self):
        if self.user_model == "open" and self.session_duration:
            max_session_duration = self.session_duration * 3 
            session_duration = random.expovariate(1.0 / self.session_duration)
            return min(session_duration, max_session_duration)
        return self.duration
