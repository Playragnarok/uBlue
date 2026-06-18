import webview
import requests
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class TradingAppAPI:
    def __init__(self):
        self.app_dir = os.path.expanduser("~/Documents/uBlue")
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)
            
        self.profile_file = os.path.join(self.app_dir, "prompt_profiles.json")
        self.config_file = os.path.join(self.app_dir, "config.json")
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.profile_file):
            # โครงสร้างใหม่ แยก System Prompt และ User Prompt ออกจากกันอย่างชัดเจน
            default_profiles = {
                "scalping_gold": {
                    "model": "qwen2.5:7b", 
                    "system_prompt": "คุณคือ AI ผู้ช่วยเทรดเดอร์ Forex ระดับมืออาชีพ หน้าที่ของคุณคือวิเคราะห์ข้อมูลตลาด แจ้งเทรนด์หลัก และบอกจุด Entry, SL, TP เท่านั้น ห้ามร่ายยาว ห้ามอธิบายทฤษฎี ให้ตอบเป็น Bullet Points ที่สั้นและกระชับที่สุด",
                    "user_prompt": "ช่วยวิเคราะห์จังหวะ Scalping สำหรับ XAUUSD ทันทีโดยดูจาก Action ของราคาและแท่งเทียนล่าสุด..."
                }
            }
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(default_profiles, f, ensure_ascii=False, indent=4)
                
        if not os.path.exists(self.config_file):
            default_config = {"ip": "", "port": "5001", "timeframe": "M15", "symbols": ["XAUUSD", "EURUSD"], "last_symbol": "XAUUSD"}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)

    def get_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}

    def save_config(self, key, value):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f: config = json.load(f)
            config[key] = value
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except: return False

    def check_ollama_status(self):
        try:
            res = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            return True if res.status_code == 200 else False
        except: return False

    def get_ollama_models(self):
        try:
            res = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            if res.status_code == 200: return [m["name"] for m in res.json().get("models", [])]
            return []
        except: return []

    def get_all_profiles(self):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f: return list(json.load(f).keys())
        except: return []

    def load_profile(self, profile_name):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f: return json.load(f).get(profile_name, {})
        except: return {}

    def save_profile(self, profile_name, model, system_prompt, user_prompt):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f: profiles = json.load(f)
            profiles[profile_name] = {"model": model, "system_prompt": system_prompt, "user_prompt": user_prompt}
            with open(self.profile_file, 'w', encoding='utf-8') as f: json.dump(profiles, f, ensure_ascii=False, indent=4)
            return True
        except: return False

    def delete_profile(self, profile_name):
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f: profiles = json.load(f)
            if profile_name in profiles:
                del profiles[profile_name]
                with open(self.profile_file, 'w', encoding='utf-8') as f: json.dump(profiles, f, ensure_ascii=False, indent=4)
                return True
            return False
        except: return False

    # อัปเกรดระบบดึงคำตอบผ่าน /api/chat เพื่อแยกบทบาทและควบคุมวินัยโมเดลอย่างเด็ดขาด
    def analyze_market(self, model, system_prompt, user_prompt):
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2, # ลดค่าความสุ่ม เพื่อให้ตอบตรงตามกรอบระเบียบวินัย
                "top_p": 0.9
            }
        }
        try:
            response = requests.post("http://127.0.0.1:11434/api/chat", json=payload)
            result = response.json()
            content = result.get("message", {}).get("content", "ไม่สามารถดึงข้อความจาก AI ได้")
            return {"status": "success", "response": content}
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    api = TradingAppAPI()
    html_file_path = resource_path('index.html')
    
    window = webview.create_window(
        title=' ', # เคาะเว้นวรรค 1 ที เพื่อให้ปุ่มปิด ย่อขยายของระบบ Mac ทำงานสมบูรณ์แบบ
        url=html_file_path, 
        js_api=api,
        width=1280,
        height=850,
        background_color='#111827'
    )
    
    # ปิดโหมด Debug เพื่อเข้าสู่สภาวะ Production แก้อาการทับซ้อนพื้นที่ปุ่มปิด/ย่อขยายของ Mac หายขาด 100%
    webview.start(http_server=True, debug=False)
