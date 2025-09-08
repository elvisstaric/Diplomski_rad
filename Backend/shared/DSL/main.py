import re
import json
from typing import List, Dict, Any

def parse_dsl(dsl_script: str) -> Dict[str, Any]:
    if not dsl_script or not dsl_script.strip():
        return {
            "num_users": 1,
            "test_duration": 60,
            "workload_pattern": "steady",
            "steps": [],
            "user_journey": []
        }
    
    steps = []
    user_journey = []
    num_users = 1
    test_duration = 60
    workload_pattern = "steady"
    pattern_config = {}
    current_journey_step = None

    
    lines = dsl_script.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        if line.startswith("users:"):
            try:
                num_users = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                num_users = 1
        elif line.startswith("duration:"):
            try:
                test_duration = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                test_duration = 60
        elif line.startswith("pattern:"):
            pattern_value = line.split(":")[1].strip()
            if pattern_value in ["burst", "steady", "ramp_up", "daily_cycle", "spike", "gradual_ramp"]:
                workload_pattern = pattern_value
        elif line.startswith("peak_hours:"):
            try:
                hours_str = line.split(":", 1)[1].strip()
                pattern_config["peak_hours"] = [int(h.strip()) for h in hours_str.split(",")]
            except (ValueError, IndexError):
                pattern_config["peak_hours"] = [9, 10, 11, 14, 15, 16]
        elif line.startswith("off_peak_multiplier:"):
            try:
                pattern_config["off_peak_multiplier"] = float(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["off_peak_multiplier"] = 0.3
        elif line.startswith("base_delay:"):
            try:
                pattern_config["base_delay"] = float(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["base_delay"] = 1.0
        elif line.startswith("spike_interval:"):
            try:
                pattern_config["spike_interval"] = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["spike_interval"] = 120
        elif line.startswith("spike_duration:"):
            try:
                pattern_config["spike_duration"] = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["spike_duration"] = 30
        elif line.startswith("spike_intensity:"):
            try:
                pattern_config["spike_intensity"] = float(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["spike_intensity"] = 5.0
        elif line.startswith("start_delay:"):
            try:
                pattern_config["start_delay"] = float(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["start_delay"] = 3.0
        elif line.startswith("end_delay:"):
            try:
                pattern_config["end_delay"] = float(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["end_delay"] = 0.5
        elif line.startswith("ramp_steps:"):
            try:
                pattern_config["ramp_steps"] = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pattern_config["ramp_steps"] = 10
        elif line.startswith("journey:"):
            journey_name = line.split(":", 1)[1].strip()
            current_journey_step = {
                "name": journey_name,
                "steps": [],
                "repeat": 1,
                "condition": None
            }
            user_journey.append(current_journey_step)
        elif line.startswith("repeat:"):
            if current_journey_step:
                try:
                    repeat_count = int(line.split(":")[1].strip())
                    current_journey_step["repeat"] = repeat_count
                except (ValueError, IndexError):
                    current_journey_step["repeat"] = 1
        elif line.startswith("if:"):
            if current_journey_step:
                condition = line.split(":", 1)[1].strip()
                current_journey_step["condition"] = condition
        elif line.startswith("end"):
            current_journey_step = None
        elif line.startswith("-"):
            match = re.match(r"-\s*(\w+)\s+([^\s{]+)\s*(\{.*\})?", line)
            if match:
                method = match.group(1).upper()
                path = match.group(2)
                payload_str = match.group(3)
                
                payload = None
                if payload_str:
                    try:
                        payload = json.loads(payload_str)
                    except json.JSONDecodeError:
                        print(f"Warning: Invalid JSON payload: {payload_str}")
                
                step = {
                    "method": method,
                    "path": path,
                    "payload": payload
                }
                
                steps.append(step)
                
                if current_journey_step:
                    current_journey_step["steps"].append(step)
            else:
                print(f"Warning: Invalid step format: {line}")

    return {
        "num_users": num_users,
        "test_duration": test_duration,
        "workload_pattern": workload_pattern,
        "pattern_config": pattern_config,
        "steps": steps,
        "user_journey": user_journey
    }