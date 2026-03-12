import customtkinter as ctk
import requests
import os
import json
import threading
import pysrt
import deepl
from deep_translator import GoogleTranslator
from tkinter import filedialog, messagebox

# --- КОНФИГУРАЦИЯ ---
CONFIG_FILE = "config.json"

class UltimateSubPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BG Subtitles Ultimate Pro - Search & Multi-Translate")
        self.geometry("950x900")
        self.token = None
        self.config = self.load_config()

        # Основна навигация (Tabs)
        self.tabview = ctk.CTkTabview(self, width=900, height=800)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.tab_search = self.tabview.add("Търсене в OpenSubtitles")
        self.tab_deepl = self.tabview.add("DeepL (Високо качество)")
        self.tab_unlimited = self.tabview.add("Unlimited (Без лимит)")
        self.tab_settings = self.tabview.add("Настройки")

        self.setup_search_ui()
        self.setup_deepl_ui()
        self.setup_unlimited_ui()
        self.setup_settings_ui()
        
        self.status = ctk.CTkLabel(self, text="Готов за работа.", font=("Arial", 12))
        self.status.pack(side="bottom", pady=5)

    # --- ИНТЕРФЕЙС: НАСТРОЙКИ ---
    def setup_settings_ui(self):
        frame = self.tab_settings
        ctk.CTkLabel(frame, text="OpenSubtitles API Key:", font=("Arial", 13, "bold")).pack(pady=(20,0))
        self.api_entry = ctk.CTkEntry(frame, width=450)
        self.api_entry.insert(0, self.config.get("api_key", "NGxAYc5M0yS45SMPXQ9J6PpowPc8Nspy"))
        self.api_entry.pack(pady=5)

        ctk.CTkLabel(frame, text="DeepL API Key:", font=("Arial", 13, "bold")).pack(pady=(15,0))
        self.deepl_entry = ctk.CTkEntry(frame, width=450, placeholder_text="Въведи DeepL API Key")
        self.deepl_entry.insert(0, self.config.get("deepl_key", ""))
        self.deepl_entry.pack(pady=5)

        ctk.CTkLabel(frame, text="OpenSubtitles Потребител/Парола:", font=("Arial", 13, "bold")).pack(pady=(15,0))
        up = ctk.CTkFrame(frame, fg_color="transparent"); up.pack()
        self.user_entry = ctk.CTkEntry(up); self.user_entry.insert(0, self.config.get("username", "lukather")); self.user_entry.pack(side="left", padx=5)
        self.pass_entry = ctk.CTkEntry(up, show="*"); self.pass_entry.insert(0, self.config.get("password", "sL741203&O")); self.pass_entry.pack(side="left", padx=5)

        ctk.CTkButton(frame, text="ЗАПАЗИ НАСТРОЙКИТЕ", command=self.save_config, fg_color="#2fa572").pack(pady=30)

    # --- ИНТЕРФЕЙС: ТЪРСЕНЕ ---
    def setup_search_ui(self):
        frame = self.tab_search
        self.login_btn = ctk.CTkButton(frame, text="Вход в OpenSubtitles", command=self.login, fg_color="#34495e")
        self.login_btn.pack(pady=10)

        sf = ctk.CTkFrame(frame, fg_color="transparent"); sf.pack(pady=10)
        self.search_entry = ctk.CTkEntry(sf, width=500, placeholder_text="Име на филм..."); self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search())
        ctk.CTkButton(sf, text="ТЪРСИ", width=100, command=self.search).pack(side="left", padx=5)

        self.ltabs = ctk.CTkTabview(frame, width=850, height=400)
        self.ltabs.pack(pady=10)
        self.tab_bg = self.ltabs.add("БЪЛГАРСКИ 🇧🇬"); self.tab_en = self.ltabs.add("АНГЛИЙСКИ 🇺🇸")
        self.scroll_bg = ctk.CTkScrollableFrame(self.tab_bg, width=800, height=350); self.scroll_bg.pack(fill="both")
        self.scroll_en = ctk.CTkScrollableFrame(self.tab_en, width=800, height=350); self.scroll_en.pack(fill="both")
        
        self.selected_file_id = ctk.StringVar()
        af = ctk.CTkFrame(frame, fg_color="transparent"); af.pack(pady=15)
        self.btn_sync = ctk.CTkButton(af, text="СИНХРОНИЗИРАЙ С ВИДЕО", state="disabled", fg_color="#e67e22", command=lambda: self.download_logic("sync"))
        self.btn_sync.grid(row=0, column=0, padx=10)
        self.btn_fold = ctk.CTkButton(af, text="СВАЛИ В ПАПКА", state="disabled", fg_color="#3498db", command=lambda: self.download_logic("folder"))
        self.btn_fold.grid(row=0, column=1, padx=10)

    # --- ИНТЕРФЕЙС: DEEPL ---
    def setup_deepl_ui(self):
        frame = self.tab_deepl
        ctk.CTkLabel(frame, text="DeepL High-Quality Translator", font=("Arial", 18, "bold")).pack(pady=20)
        self.d_file_btn = ctk.CTkButton(frame, text="📁 Избери SRT", command=self.open_deepl_file).pack(pady=10)
        self.d_prog = ctk.CTkProgressBar(frame, width=500); self.d_prog.set(0); self.d_prog.pack(pady=20)
        self.d_status = ctk.CTkLabel(frame, text="Готовност"); self.d_status.pack()
        self.d_start = ctk.CTkButton(frame, text="СТАРТ DEEPL", state="disabled", fg_color="#2fa572", command=self.start_deepl_thread)
        self.d_start.pack(pady=20)

    # --- ИНТЕРФЕЙС: UNLIMITED (GOOGLE/META ENGINE) ---
    def setup_unlimited_ui(self):
        frame = self.tab_unlimited
        ctk.CTkLabel(frame, text="Unlimited Translator (No Limits)", font=("Arial", 18, "bold")).pack(pady=20)
        ctk.CTkButton(frame, text="📁 Избери SRT", command=self.open_unlimited_file).pack(pady=10)
        self.u_prog = ctk.CTkProgressBar(frame, width=500); self.u_prog.set(0); self.u_prog.pack(pady=20)
        self.u_status = ctk.CTkLabel(frame, text="Готовност"); self.u_status.pack()
        self.u_start = ctk.CTkButton(frame, text="СТАРТ БЕЗЛИМИТЕН ПРЕВОД", state="disabled", fg_color="#3498db", command=self.start_unlimited_thread)
        self.u_start.pack(pady=20)

    # --- ЛОГИКА: ФАЙЛОВЕ И ВХОД ---
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: return json.load(f)
            except: pass
        return {}

    def save_config(self):
        self.config = {"api_key": self.api_entry.get(), "deepl_key": self.deepl_entry.get(), "username": self.user_entry.get(), "password": self.pass_entry.get()}
        with open(CONFIG_FILE, "w") as f: json.dump(self.config, f)
        messagebox.showinfo("Успех", "Настройките са запазени!")

    def login(self):
        def t():
            h = {'Api-Key': self.api_entry.get(), 'Content-Type': 'application/json', 'User-Agent': 'SubApp v1.0'}
            try:
                r = requests.post("https://api.opensubtitles.com/api/v1/login", json={"username": self.user_entry.get(), "password": self.pass_entry.get()}, headers=h)
                if r.status_code == 200: 
                    self.token = r.json().get('token')
                    self.status.configure(text="✅ Успешен вход в OpenSubtitles!", text_color="green")
                else: self.status.configure(text=f"❌ Грешка при вход: {r.status_code}", text_color="red")
            except: self.status.configure(text="❌ Няма връзка.", text_color="red")
        threading.Thread(target=t, daemon=True).start()

    def search(self):
        movie = self.search_entry.get()
        if not movie: return
        for w in self.scroll_bg.winfo_children(): w.destroy()
        for w in self.scroll_en.winfo_children(): w.destroy()
        def t():
            h = {'Api-Key': self.api_entry.get(), 'User-Agent': 'SubApp v1.0'}
            try:
                r = requests.get("https://api.opensubtitles.com/api/v1/subtitles", headers=h, params={'query': movie, 'languages': 'bg,en'})
                data = r.json().get('data', [])
                for i in data:
                    attr = i['attributes']; lang = attr['language']; fid = attr['files'][0]['file_id']
                    target = self.scroll_bg if lang == 'bg' else self.scroll_en
                    ctk.CTkRadioButton(target, text=f"{attr['feature_details']['title']} | {attr['release']}", variable=self.selected_file_id, value=str(fid), command=self.en_btns).pack(anchor="w", pady=5, padx=10)
            except: pass
        threading.Thread(target=t, daemon=True).start()

    def en_btns(self): self.btn_sync.configure(state="normal"); self.btn_fold.configure(state="normal")

    def download_logic(self, mode):
        fid = self.selected_file_id.get()
        if not self.token: messagebox.showwarning("Вход", "Моля, логнете се първо!"); return
        if mode == "sync":
            path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mkv *.avi")])
            if not path: return
            tdir = os.path.dirname(path); tname = os.path.splitext(os.path.basename(path))[0] + ".srt"
        else:
            tdir = filedialog.askdirectory()
            if not tdir: return
            tname = None
        threading.Thread(target=self.dl, args=(fid, tdir, tname), daemon=True).start()

    def dl(self, fid, tdir, tname):
        h = {'Api-Key': self.api_entry.get(), 'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json', 'User-Agent': 'SubApp v1.0'}
        try:
            r = requests.post("https://api.opensubtitles.com/api/v1/download", json={"file_id": int(fid)}, headers=h)
            if r.status_code == 200:
                d = r.json(); res = requests.get(d.get('link'))
                fn = tname if tname else d.get('file_name')
                with open(os.path.join(tdir, fn), 'wb') as f: f.write(res.content)
                self.status.configure(text=f"✅ Свалено: {fn}", text_color="green")
                os.startfile(tdir)
        except: self.status.configure(text="❌ Грешка при сваляне.")

    # --- ЛОГИКА ПРЕВОД: DEEPL ---
    def open_deepl_file(self):
        self.dp = filedialog.askopenfilename(filetypes=[("SRT", "*.srt")])
        if self.dp: self.d_start.configure(state="normal"); self.d_status.configure(text=os.path.basename(self.dp))

    def start_deepl_thread(self): threading.Thread(target=self.run_deepl, daemon=True).start()

    def run_deepl(self):
        try:
            self.d_start.configure(state="disabled")
            t = deepl.Translator(self.deepl_entry.get())
            subs = pysrt.open(self.dp, encoding='utf-8')
            for i in range(0, len(subs), 50):
                batch = subs[i:i+50]; texts = [s.text for s in batch]
                res = t.translate_text(texts, target_lang="BG")
                for j, r in enumerate(res): subs[i+j].text = r.text
                self.d_prog.set((i+50)/len(subs)); self.d_status.configure(text=f"{i+50}/{len(subs)}")
            subs.save(self.dp.replace(".srt", "_DeepL_BG.srt"), encoding='utf-8')
            messagebox.showinfo("Успех", "DeepL преводът е готов!")
        except Exception as e: messagebox.showerror("Грешка", str(e))
        finally: self.d_start.configure(state="normal")

    # --- ЛОГИКА ПРЕВОД: UNLIMITED ---
    def open_unlimited_file(self):
        self.upath = filedialog.askopenfilename(filetypes=[("SRT", "*.srt")])
        if self.upath: self.u_start.configure(state="normal"); self.u_status.configure(text=os.path.basename(self.upath))

    def start_unlimited_thread(self): threading.Thread(target=self.run_unlimited, daemon=True).start()

    def run_unlimited(self):
        try:
            self.u_start.configure(state="disabled")
            translator = GoogleTranslator(source='en', target='bg')
            subs = pysrt.open(self.upath, encoding='utf-8')
            total = len(subs)
            
            # Рекламни фрази за премахване
            ads = ["subtitles by", "opensubtitles", "downloaded from", "support us", "translated by"]
            
            for i, sub in enumerate(subs):
                # Проверка за реклами
                if any(ad in sub.text.lower() for ad in ads):
                    sub.text = "" # Изтрива рекламния ред
                elif sub.text.strip():
                    sub.text = translator.translate(sub.text)
                
                if i % 10 == 0:
                    self.u_prog.set(i/total); self.u_status.configure(text=f"Напредък: {i}/{total}")
                    self.update_idletasks()
            
            out = self.upath.replace(".srt", "_Unlimited_BG.srt")
            subs.save(out, encoding='utf-8')
            messagebox.showinfo("Успех", "Безлимитният превод е готов!")
        except Exception as e: messagebox.showerror("Грешка", str(e))
        finally: self.u_start.configure(state="normal")

if __name__ == "__main__":
    app = UltimateSubPro()
    app.mainloop()

