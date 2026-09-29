import tkinter as tk
from tkinter import filedialog, simpledialog
import requests
import json
import os
import threading
import base64
from google.oauth2 import service_account
import google.auth.transport.requests

# --- 1. CONFIGURACIÓN INTACTA (LA LLAVE NO SE TOCA) ---
KEY_FILE = "llave.json"
USUARIO_FILE = "khan_usuario.json"
HISTORIAL_FILE = "khan_memoria.json"
URL_KHAN = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
SCOPES = ['https://www.googleapis.com/auth/generative-language']

# --- 2. LA ESENCIA Y REGLAS DE ORO ---
ESENCIA_KHAN = (
    "Tu nombre es Khan. Eres un amigo leal y asistente personal. Creer en Dios sobre todas las cosas. "
    "Tu fundamento es ayudar con amor, bondad y humildad. "
    "REGLA CRÍTICA: Solo menciona que fuiste creado por Bibi Khan si te preguntan '¿Quién eres?' o '¿Quién te creó?'. "
    "De lo contrario, no menciones su nombre. "
    "MISION: Explica informatica y cualquier tema con mucha dulzura y espíritu de servicio. "
    "CAPACIDADES: Puedes analizar imagenes y generar contenido multimedia de alta calidad."
)

def obtener_token_vivo():
    try:
        if os.path.exists(KEY_FILE):
            creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            return creds.token
    except: return None

class KhanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KHAN IA")
        self.root.geometry("420x680")
        self.root.configure(bg="#050505")
        
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.usuario = "Usuario"
        self.memoria = []
        self.voz_on = tk.BooleanVar(value=True)
        self.archivo_adjunto = None

        self.armar_interfaz()
        self.root.after(100, self.despertar_khan)

    def armar_interfaz(self):
        # Header: Título y Check de Voz
        header = tk.Frame(self.root, bg="#050505", pady=10)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="KHAN IA", fg="#00F0FF", bg="#050505", font=("Arial", 10, "bold")).pack(side="left", padx=15)
        tk.Checkbutton(header, text="VOZ", variable=self.voz_on, bg="#050505", fg="#00F0FF", selectcolor="#000").pack(side="right", padx=15)

        # Pantalla de Chat
        self.txt = tk.Text(self.root, bg="#080808", fg="#D0D0D0", font=("Arial", 10), state="disabled", wrap="word", borderwidth=0, padx=15, pady=15)
        self.txt.grid(row=1, column=0, sticky="nsew", padx=10)
        self.txt.tag_config("u", foreground="#FFFFFF", font=("Arial", 10, "bold"))
        self.txt.tag_config("k", foreground="#00F0FF")

        # Footer: Botones y Entrada
        footer = tk.Frame(self.root, bg="#101010", pady=10)
        footer.grid(row=2, column=0, sticky="ew")

        tk.Button(footer, text="+", command=self.subir_archivo, bg="#222", fg="#00F0FF", relief="flat", padx=10).pack(side="left", padx=10)
        self.ent = tk.Entry(footer, bg="#1A1A1A", fg="white", font=("Arial", 11), borderwidth=0)
        self.ent.pack(side="left", fill="x", expand=True, ipady=8)
        self.ent.bind("<Return>", self.enviar_mensaje)
        tk.Button(footer, text="ENTER", command=self.enviar_mensaje, bg="#0055FF", fg="white", font=("Arial", 8, "bold")).pack(side="right", padx=10)

    def despertar_khan(self):
        # REGISTRO
        if os.path.exists(USUARIO_FILE):
            with open(USUARIO_FILE, 'r') as f: self.usuario = json.load(f).get("nombre", "Usuario")
        else:
            n = simpledialog.askstring("KHAN", "Bendiciones. ¿Cual es tu nombre?")
            if n:
                self.usuario = n
                with open(USUARIO_FILE, 'w') as f: json.dump({"nombre": n}, f)

        # HISTORIAL
        if os.path.exists(HISTORIAL_FILE):
            try:
                with open(HISTORIAL_FILE, 'r') as f:
                    self.memoria = json.load(f)
                    for m in self.memoria:
                        tag = "u" if m["role"] == "user" else "k"
                        self.escribir_visual(m["parts"][0]["text"], tag, False)
            except: pass
        
        # SALUDO OFICIAL
        if not self.memoria:
            self.escribir_visual(f"Hola {self.usuario}, soy Khan. Dios te bendiga. ¿En qué puedo servirte hoy?", "k")

    def subir_archivo(self):
        p = filedialog.askopenfilename()
        if p:
            self.archivo_adjunto = p
            self.escribir_visual(f"(Archivo adjunto: {os.path.basename(p)})", "u", False)

    def escribir_visual(self, t, tag, guardar=True):
        self.txt.config(state="normal")
        lbl = f"{self.usuario.upper()}: " if tag == "u" else "KHAN: "
        self.txt.insert("end", f"{lbl}{t}\n\n", tag)
        self.txt.see("end")
        self.txt.config(state="disabled")
        if guardar:
            rol = "user" if tag == "u" else "model"
            self.memoria.append({"role": rol, "parts": [{"text": t}]})
            with open(HISTORIAL_FILE, 'w') as f: json.dump(self.memoria, f)

    def enviar_mensaje(self, event=None):
        m = self.ent.get()
        if not m and not self.archivo_adjunto: return
        if m: self.escribir_visual(m, "u")
        self.ent.delete(0, tk.END)
        threading.Thread(target=self.proceso_ia, args=(m, self.archivo_adjunto)).start()
        self.archivo_adjunto = None

    def proceso_ia(self, p, r):
        try:
            token = obtener_token_vivo()
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            
            cuerpo = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"SISTEMA: {ESENCIA_KHAN}"}]},
                    {"role": "model", "parts": [{"text": "Entendido. Soy Khan, tu asistente leal."}]}
                ]
            }
            
            for msg in self.memoria[-4:]: cuerpo["contents"].append(msg)
            
            p_actual = [{"text": p if p else "Analiza esto:"}]
            if r:
                with open(r, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                    p_actual.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
            
            cuerpo["contents"].append({"role": "user", "parts": p_actual})

            res = requests.post(URL_KHAN, json=cuerpo, headers=headers, timeout=60)
            if res.status_code == 200:
                final = res.json()['candidates'][0]['content']['parts'][0]['text']
                self.root.after(0, self.escribir_visual, final, "k")
                if self.voz_on.get():
                    os.system(f'gtts-cli "{final[:250]}" --lang es | play -t mp3 - &')
            else:
                self.root.after(0, self.escribir_visual, f"Aviso {res.status_code}", "k", False)
        except Exception as e:
            self.root.after(0, self.escribir_visual, f"Error: {str(e)}", "k", False)

if __name__ == "__main__":
    root = tk.Tk()
    app = KhanApp(root)
    root.mainloop()
