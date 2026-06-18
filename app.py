import webview
import requests
import json
import os
import sys
import warnings

# ปิดการแจ้งเตือนของ urllib3 ที่ไม่จำเป็นบน Mac
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

def resource_path(relative_path):
    """ จัดการ Path ให้ทำงานได้ทั้งตอนรัน .py และตอนเป็น .app """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class TradingAppAPI:
    def __init__(self):
        # สร้างโฟลเดอร์สำหรับเก็บค่าไฟล์ตั้งค่าต่างๆ ในเครื่อง Mac
        self.app_dir = os.path.expanduser("~/Documents/uBlue")
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)
            
        self.profile_file = os.path.join(self.app_dir, "prompt_profiles.json")
        self.config_file = os.path.join(self.app_dir, "config.json")
        self._init_files()

    def _init_files(self):
        # บันทึกและสแตนบายไฟล์ JSON สำหรับใช้งาน
        if not os.path.exists(self.profile_file):
            default_profiles = {
                "scalping_gold": {"model": "qwen2.5:7b", "prompt": "วิเคราะห์จังหวะ Scalping สำหรับ XAUUSD ทันทีโดยดูจาก Action ของราคาและแท่งเทียนล่าสุด..."}
            }
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(default_profiles, f, ensure_ascii=False, indent=4)
                
        if not os.path.exists(self.config_file):
            default_config = {
                "ip": "", "port": "5001", "timeframe": "M15", 
                "symbols": ["XAUUSD", "EURUSD"], "last_symbol": "XAUUSD"
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)

    # --- ระบบจัดการไฟล์ตั้งค่า (Config) ---
    def get_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def save_config(self, key, value):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            config[key] = value
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    # --- ระบบเชื่อมต่อและตรวจสอบ Ollama Local ---
    def check_ollama_status(self):
        try:
            res = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            return True if res.status_code == 200 else False
        except:
            return False

    def get_ollama_models(self):
        try:
            res = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            if res.status_code == 200:
                return [m["name"] for m in res.json().get("models", [])]
            return []
        except:
            return []

    # --- ระบบโปรไฟล์พรมอมต์ (Prompt Profiles) ---
    def get_all_profiles(self):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f:
                return list(json.load(f).keys())
        except:
            return []

    def load_profile(self, profile_name):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f:
                return json.load(f).get(profile_name, {})
        except:
            return {}

    def save_profile(self, profile_name, model, prompt_text):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f:
                profiles = json.load(f)
            profiles[profile_name] = {"model": model, "prompt": prompt_text}
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def delete_profile(self, profile_name):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f:
                profiles = json.load(f)
            if profile_name in profiles:
                del profiles[profile_name]
                with open(self.profile_file, 'w', encoding='utf-8') as f:
                    json.dump(profiles, f, ensure_ascii=False, indent=4)
                return True
            return False
        except:
            return False

    def analyze_market(self, model, prompt_text):
        payload = {"model": model, "prompt": prompt_text, "stream": False}
        try:
            response = requests.post("http://127.0.0.1:11434/api/generate", json=payload)
            return {"status": "success", "response": response.json().get("response")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    # เรียกใช้ชื่อคลาส TradingAppAPI ให้ตรงกับคำสั่งของโครงสร้างเก่าที่คุณต้องการ
    api = TradingAppAPI()
    html_file_path = resource_path('index.html')
    
    # ดึงชุดคำสั่งดั้งเดิมที่ทำให้เปิดใช้เมนูไฟจราจรของ Mac ได้ปกติกลับมาทำงานร่วมกับระบบใหม่
    window = webview.create_window(
        title='uBlue AI LLM Helper',
        url=html_file_path, 
        js_api=api,
        width=1280,
        height=850,
        background_color='#111827'
    )
    
# ปิดโหมด debug หรือลบคำว่า debug ออกไปเลยครับ
    webview.start(http_server=True, debug=False)