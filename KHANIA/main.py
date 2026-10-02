import os
import json
import threading
import base64
import requests

from google.oauth2 import service_account
import google.auth.transport.requests

# --- IMPORTACIONES DE KIVY PARA INTERFAZ FUTURISTA ---
import kivy
kivy.require('2.1.0')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle

# --- RUTA ABSOLUTA DINÁMICA (EVITA CIERRES EN ANDROID) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(BASE_DIR, filename)

# --- 1. CONFIGURACIÓN INTACTA (LA LLAVE NO SE TOCA) ---
KEY_FILE = get_path("llave.json")
USUARIO_FILE = get_path("khan_usuario.json")
HISTORIAL_FILE = get_path("khan_memoria.json")
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
    except Exception as e:
        print(f"Error Token: {e}")
        return None

# --- COMPONENTES GRÁFICOS FUTURISTAS ---
class CyberPanel(BoxLayout):
    """Panel contenedor con estética Ciberpunk / Sci-Fi HUD"""
    def __init__(self, bg_color=(0.04, 0.06, 0.1, 0.95), border_color=(0, 0.95, 1, 0.8), **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
            Color(*self.border_color)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 8), width=1.2)

class KhanApp(App):
    def build(self):
        self.title = "KHAN IA // SYSTEM OS"
        Window.clearcolor = (0.02, 0.03, 0.05, 1) # Fondo Espacial Profundo

        self.usuario = "Usuario"
        self.memoria = []
        self.voz_on = True
        self.archivo_adjunto = None

        # Root principal
        self.root_layout = BoxLayout(orientation='vertical', padding=12, spacing=10)

        # 1. HEADER FUTURISTA
        header_panel = CyberPanel(
            orientation='horizontal',
            size_hint_y=None,
            height=60,
            padding=[15, 5],
            bg_color=(0.06, 0.09, 0.15, 0.9),
            border_color=(0, 0.95, 1, 0.6)
        )
        
        title_label = Label(
            text="[b][color=#00F0FF]KHAN IA[/color][/b] [color=#7000FF]// SYSTEM v3.5[/color]",
            markup=True,
            font_size='18sp',
            halign='left',
            valign='middle'
        )
        title_label.bind(size=title_label.setter('text_size'))

        voice_box = BoxLayout(orientation='horizontal', size_hint_x=None, width=120, spacing=5)
        voice_lbl = Label(text="[color=#00F0FF][b]VOZ[/b][/color]", markup=True, font_size='14sp')
        self.chk_voz = CheckBox(active=True, color=(0, 0.95, 1, 1))
        self.chk_voz.bind(active=self.toggle_voz)
        voice_box.add_widget(voice_lbl)
        voice_box.add_widget(self.chk_voz)

        header_panel.add_widget(title_label)
        header_panel.add_widget(voice_box)
        self.root_layout.add_widget(header_panel)

        # 2. PANTALLA DE CHAT CIBERNÉTICA
        chat_panel = CyberPanel(
            orientation='vertical',
            padding=10,
            bg_color=(0.03, 0.04, 0.08, 0.95),
            border_color=(0, 0.95, 1, 0.3)
        )

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.txt_label = Label(
            text="",
            markup=True,
            size_hint_y=None,
            text_size=(Window.width - 60, None),
            halign='left',
            valign='top',
            font_size='15sp',
            line_height=1.2
        )
        self.txt_label.bind(texture_size=self._update_chat_height)
        self.scroll.add_widget(self.txt_label)
        chat_panel.add_widget(self.scroll)
        self.root_layout.add_widget(chat_panel)

        # 3. FOOTER: ENTRADA Y BOTONES CIBERNÉTICOS
        footer_panel = CyberPanel(
            orientation='horizontal',
            size_hint_y=None,
            height=65,
            padding=8,
            spacing=8,
            bg_color=(0.06, 0.09, 0.15, 0.9),
            border_color=(0.4, 0, 1, 0.6)
        )

        # Botón Subir Archivo (+)
        self.btn_subir = Button(
            text="[b]+[/b]",
            markup=True,
            size_hint_x=None,
            width=50,
            background_normal='',
            background_color=(0.1, 0.15, 0.25, 1),
            color=(0, 0.95, 1, 1),
            font_size='22sp'
        )
        self.btn_subir.bind(on_release=lambda x: self.subir_archivo())

        # Campo de Entrada de Texto
        self.ent = TextInput(
            hint_text="Escribe un comando o mensaje...",
            hint_text_color=(0.4, 0.5, 0.6, 1),
            multiline=False,
            background_normal='',
            background_color=(0.02, 0.04, 0.08, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0, 0.95, 1, 1),
            font_size='15sp',
            padding=[10, 12, 10, 10]
        )
        self.ent.bind(on_text_validate=lambda x: self.enviar_mensaje())

        # Botón Enviar (ENTER)
        self.btn_enviar = Button(
            text="[b]ENTER[/b]",
            markup=True,
            size_hint_x=None,
            width=90,
            background_normal='',
            background_color=(0.26, 0, 0.8, 1),
            color=(1, 1, 1, 1),
            font_size='13sp'
        )
        self.btn_enviar.bind(on_release=lambda x: self.enviar_mensaje())

        footer_panel.add_widget(self.btn_subir)
        footer_panel.add_widget(self.ent)
        footer_panel.add_widget(self.btn_enviar)
        self.root_layout.add_widget(footer_panel)

        Clock.schedule_once(lambda dt: self.despertar_khan(), 0.2)
        return self.root_layout

    def _update_chat_height(self, instance, value):
        instance.height = instance.texture_size[1]
        instance.text_size = (self.scroll.width - 20, None)
        self.scroll.scroll_y = 0

    def toggle_voz(self, checkbox, value):
        self.voz_on = value

    def despertar_khan(self):
        # REGISTRO CON POPUP FUTURISTA SI NO EXISTE EL USUARIO
        if os.path.exists(USUARIO_FILE):
            try:
                with open(USUARIO_FILE, 'r', encoding='utf-8') as f:
                    self.usuario = json.load(f).get("nombre", "Usuario")
                self.cargar_historial_y_saludo()
            except Exception as e:
                self.pedir_nombre_popup()
        else:
            self.pedir_nombre_popup()

    def pedir_nombre_popup(self):
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        lbl = Label(
            text="[color=#00F0FF][b]SISTEMA KHAN IA[/b][/color]\nBendiciones. ¿Cuál es tu nombre?",
            markup=True,
            halign='center'
        )
        name_input = TextInput(
            multiline=False,
            hint_text="Tu nombre...",
            background_color=(0.05, 0.08, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0, 0.95, 1, 1)
        )
        btn = Button(
            text="GUARDAR EN MEMORIA",
            background_color=(0, 0.6, 1, 1),
            color=(1, 1, 1, 1)
        )

        content.add_widget(lbl)
        content.add_widget(name_input)
        content.add_widget(btn)

        popup = Popup(
            title="INICIALIZACIÓN DE USUARIO",
            content=content,
            size_hint=(0.85, 0.4),
            auto_dismiss=False,
            title_color=(0, 0.95, 1, 1),
            separator_color=(0.4, 0, 1, 1)
        )

        def guardar_nombre(instance):
            n = name_input.text.strip()
            if n:
                self.usuario = n
                with open(USUARIO_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"nombre": n}, f)
                popup.dismiss()
                self.cargar_historial_y_saludo()

        btn.bind(on_release=guardar_nombre)
        popup.open()

    def cargar_historial_y_saludo(self):
        # HISTORIAL
        if os.path.exists(HISTORIAL_FILE):
            try:
                with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                    self.memoria = json.load(f)
                    for m in self.memoria:
                        tag = "u" if m["role"] == "user" else "k"
                        self.escribir_visual(m["parts"][0]["text"], tag, False)
            except Exception as e:
                print(f"Error cargando historial: {e}")

        # SALUDO OFICIAL
        if not self.memoria:
            self.escribir_visual(f"Hola {self.usuario}, soy Khan. Dios te bendiga. ¿En qué puedo servirte hoy?", "k")

    def subir_archivo(self):
        # SELECTOR CIBERNÉTICO DE ARCHIVOS CON KIVY
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        filechooser = FileChooserListView(path=BASE_DIR)
        
        btn_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_select = Button(text="SELECCIONAR", background_color=(0, 0.8, 1, 1))
        btn_cancel = Button(text="CANCELAR", background_color=(0.8, 0.2, 0.2, 1))
        
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_select)

        content.add_widget(filechooser)
        content.add_widget(btn_layout)

        popup = Popup(
            title="ADJUNTAR ARCHIVO MULTIMEDIA",
            content=content,
            size_hint=(0.9, 0.8),
            title_color=(0, 0.95, 1, 1),
            separator_color=(0, 0.95, 1, 1)
        )

        def seleccionar(instance):
            if filechooser.selection:
                p = filechooser.selection[0]
                self.archivo_adjunto = p
                self.escribir_visual(f"(Archivo adjunto: {os.path.basename(p)})", "u", False)
            popup.dismiss()

        btn_select.bind(on_release=seleccionar)
        btn_cancel.bind(on_release=lambda x: popup.dismiss())
        popup.open()

    def escribir_visual(self, t, tag, guardar=True):
        # FORMATEO DE TEXTO CIBERNÉTICO
        if tag == "u":
            header_str = f"[b][color=#FF007A]{self.usuario.upper()} //[/color][/b] "
        else:
            header_str = f"[b][color=#00F0FF]KHAN //[/color][/b] "

        nuevo_texto = f"{header_str}{t}\n\n"
        self.txt_label.text += nuevo_texto

        if guardar:
            rol = "user" if tag == "u" else "model"
            self.memoria.append({"role": rol, "parts": [{"text": t}]})
            try:
                with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.memoria, f)
            except Exception as e:
                print(f"Error al guardar memoria: {e}")

    def enviar_mensaje(self, event=None):
        m = self.ent.text.strip()
        if not m and not self.archivo_adjunto:
            return
        
        if m:
            self.escribir_visual(m, "u")
        
        self.ent.text = ""
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

            for msg in self.memoria[-4:]:
                cuerpo["contents"].append(msg)

            p_actual = [{"text": p if p else "Analiza esto:"}]
            if r:
                try:
                    with open(r, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode("utf-8")
                        p_actual.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
                except Exception as file_err:
                    print(f"Error cargando imagen: {file_err}")

            cuerpo["contents"].append({"role": "user", "parts": p_actual})

            res = requests.post(URL_KHAN, json=cuerpo, headers=headers, timeout=60)
            if res.status_code == 200:
                final = res.json()['candidates'][0]['content']['parts'][0]['text']
                Clock.schedule_once(lambda dt: self.escribir_visual(final, "k"), 0)
                
                if self.voz_on:
                    try:
                        os.system(f'gtts-cli "{final[:250]}" --lang es | play -t mp3 - &')
                    except:
                        pass
            else:
                Clock.schedule_once(lambda dt: self.escribir_visual(f"Aviso {res.status_code}", "k", False), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.escribir_visual(f"Error: {str(e)}", "k", False), 0)

if __name__ == "__main__":
    KhanApp().run()
