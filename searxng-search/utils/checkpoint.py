import os
import json
from datetime import datetime

class CheckpointManager:
    def __init__(self, base_archive_dir="archive/search_staging"):
        self.base_dir = base_archive_dir

    def _get_topic_dir(self, topic, date_str):
        """
        Constructs path: archive/search_staging/YYYY/MM/DD/query-topic/
        date_str should be YYYY-MM-DD
        """
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # Fallback to today if format is wrong
            dt = datetime.now()
            
        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        day = dt.strftime("%d")
        
        # Sanitize topic for filesystem
        safe_topic = topic.lower().replace(" ", "_").replace("/", "_").replace(" ", "_")
        
        return os.path.join(self.base_dir, year, month, day, safe_topic)

    def initialize_session(self, topic, date_str):
        path = self._get_topic_dir(topic, date_str)
        os.makedirs(path, exist_ok=True)
        return path

    def save_checkpoint(self, topic, date_str, stage_num, data):
        path = self._get_topic_dir(topic, date_str)
        filename = f"{stage_num:02d}_stage.json"
        full_path = os.path.join(path, filename)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return full_path

    def load_checkpoint(self, topic, date_str, stage_num):
        path = self._get_topic_dir(topic, date_str)
        filename = f"{stage_num:02d}_stage.json"
        full_path = os.path.join(path, filename)
        
        if not os.path.exists(full_path):
            return None
            
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_last_completed_stage(self, topic, date_str):
        path = self._get_topic_dir(topic, date_str)
        if not os.path.exists(path):
            return 0
            
        files = os.listdir(path)
        stage_nums = []
        for f in files:
            if f.startswith(tuple(f"{i:02d}_stage.json" for i in range(1, 6))):
                try:
                    stage_nums.append(int(f.split('_')[0]))
                except (ValueError, IndexError):
                    continue
        
        return max(stage_nums) if stage_nums else 0
