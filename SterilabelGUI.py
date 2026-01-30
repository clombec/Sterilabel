import time
import traceback
import customtkinter as ctk
from PIL import Image, ImageTk
import queue
import os
import yaml

from SterilabelApp import SterilabelApp
from tkinter import filedialog, messagebox
import tkinter as tk

# --- Configuration globale ---
ctk.set_appearance_mode("dark")          # Mode sombre
ctk.set_default_color_theme("blue")      # Thème moderne


# -------------------------
# Configuration / Constants
# -------------------------
DEFAULT_CONFIG = {
    "WATCH_ROOT": "Z:/Temp",
    "DEFAULT_COPIES": 1
}

CONFIG_FILE = "config.yaml"

VERSION = "1.0" # App version

class SterilabelGUIApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sterilabel")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.iconbitmap(False, 'sterilabel.ico')
        
        self.event_queue = queue.Queue()
        self.frame_color = None
        self.current_image_path = None
        self.lines = []
        self.bmanualsearch = False
        self.read_config_yaml()

        self._build_topbar()
        self._build_ui()
        self.after(200, self._process_event_queue)

        # Initialize application
        self.app = SterilabelApp(self.configdata.get("WATCH_ROOT"), self.event_queue)

    # -------------------------
    # CONFIG FUNCTIONS
    # -------------------------
    def read_config_yaml(self):
        """
        Reads a YAML configuration file.
        Ensures missing default keys are added with default values.
        Returns a dictionary.
        """
        if not os.path.exists(CONFIG_FILE):
            self.configdata = DEFAULT_CONFIG.copy()
            # If file does not exist, create it with defaults
            self.write_config_yaml()
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.configdata = yaml.safe_load(f) or {}
        except Exception as e:
            raise RuntimeError(f"Error reading YAML file: {e}")

        # Ensure required defaults exist
        changed = False
        for key, value in DEFAULT_CONFIG.items():
            if key not in self.configdata:
                self.configdata[key] = value
                changed = True

        # If defaults were missing, update the file
        if changed:
            self.write_config_yaml()


    def write_config_yaml(self) -> None:
        """
        Writes a dictionary to the YAML configuration file.
        """
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.configdata, f, sort_keys=False, allow_unicode=True)
        except Exception as e:
            raise RuntimeError(f"Error writing YAML file: {e}")


    # -------------------------
    # Top bar (Menu button replaces menubar)
    # -------------------------
    def _build_topbar(self):
        topbar = ctk.CTkFrame(self, height=48, corner_radius=0)
        topbar.pack(side="top", fill="x")

        # Menu button
        self.menu_btn = ctk.CTkButton(topbar, text="☰ Menu", width=90, height=32, command=self._open_menu_window)
        self.menu_btn.pack(side="left", padx=12, pady=8)

        # Title centered
        title_lbl = ctk.CTkLabel(topbar, text="Sterilabel", font=ctk.CTkFont(size=18, weight="bold"))
        title_lbl.pack(side="right", pady=6, padx = 15)

    def _open_menu_window(self):
        # Create small non-modal Toplevel-like CTk window for menu actions
        win = ctk.CTkToplevel(self)
        win.title("Menu")
        win.geometry("300x180")
        win.transient(self)
        win.grab_set()  # modal-ish

        ctk.CTkLabel(win, text="Menu", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 6))
        ctk.CTkButton(win, text="Configuration", width=200, command=lambda: (win.destroy(), self._open_config_window())).pack(pady=6)
        ctk.CTkButton(win, text="Aide", width=200, command=lambda: (win.destroy(), self._open_about_window())).pack(pady=6)
        ctk.CTkButton(win, text="Fermer", width=200, fg_color="gray30", hover_color="gray40", command=win.destroy).pack(pady=(6, 12))

    # -------------------------
    # Config & About windows
    # -------------------------
    def _open_config_window(self):
        # Create popup window
        win = ctk.CTkToplevel(self)
        win.title("Config")
        win.geometry("600x220")
        win.transient(self)
        win.grab_set()

        # -------- TITLE --------
        title = ctk.CTkLabel(
            win,
            text="Configuration",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(12, 10))

        # -------- MAIN FRAME --------
        frame = ctk.CTkFrame(win)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        # ============= Dossier racine =============
        lbl_root = ctk.CTkLabel(frame, text="Dossier racine :")
        lbl_root.grid(row=0, column=0, padx=6, pady=10, sticky="w")

        root_var = ctk.StringVar(value=self.configdata.get("WATCH_ROOT"))
        entry_root = ctk.CTkEntry(frame, width=260, textvariable=root_var)
        entry_root.grid(row=0, column=1, padx=6, pady=10)

        # Browse button
        def browse_root():
            folder = filedialog.askdirectory(title="Choisir un dossier", initialdir=self.configdata.get("WATCH_ROOT"))
            if folder:
                root_var.set(folder)

        browse_btn = ctk.CTkButton(frame, text="Parcourir...", width=100, command=browse_root)
        browse_btn.grid(row=0, column=2, padx=6, pady=10)

        # ============= Nombre de copies =============
        lbl_copies = ctk.CTkLabel(frame, text="Nombre de copies par défaut :")
        lbl_copies.grid(row=1, column=0, padx=6, pady=10, sticky="w")

        copies_var = ctk.StringVar(value=str(self.configdata.get("DEFAULT_COPIES")))
        entry_copies = ctk.CTkEntry(frame, width=80, textvariable=copies_var, justify="center")
        entry_copies.grid(row=1, column=1, padx=6, pady=10, sticky="w")

        # Validate only integer input
        def validate_integer(value):
            return value == "" or value.isdigit()

        entry_copies.configure(validate="key", validatecommand=(entry_copies.register(validate_integer), "%P"))

        # -------- SAVE BUTTON --------
        def save():
            # Validate integer
            if not copies_var.get().isdigit():
                messagebox.showerror("Erreur", "Le nombre de copies doit être un entier.")
                return

            self.configdata["WATCH_ROOT"] = root_var.get().strip()
            self.configdata["DEFAULT_COPIES"] = int(copies_var.get())

            self.write_config_yaml()
            self.app.reload_watchdog(self.configdata.get("WATCH_ROOT"))
            win.destroy()

        save_btn = ctk.CTkButton(win, text="Enregistrer", width=160, command=save)
        save_btn.pack(pady=12)

    def _open_about_window(self):
        win = ctk.CTkToplevel(self)
        win.title("À propos de Sterilabel")
        win.geometry("420x420")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Sterilabel", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(12,6))

        version = VERSION
        desc = "\n".join([
            "Outil d'impression d'étiquettes pour paquets stérilisés.",
            "\n\nUtilisation : Le logiciel retrouve automatiquement les données enregistrées par l'autoclave à la fin du cycle et les affiche dans sa fenêtre principale.",
            "La date et l'heure de la mise à jour de l'étiquette est affichée sous l'image et permet de vérifier qu'il s'agit bien du dernier cycle effectué.",
            "Sélectionner le nombre d'étiquettes à imprimer puis cliquer sur imprimer. L'imprimante va imprimer le nombre d'étiquettes demandé.",
            "\n\nSi besoin d'imprimer une étiquette pour un cycle précédent, cliquer sur le bouton 'Recherche manuelle' et sélectionner le fichier .pro correspondant au cycle voulu.",
        ])

        ctk.CTkLabel(win, text=f"Version : {version}").pack(pady=6)
        ctk.CTkLabel(win, text=desc, wraplength=380, justify="center").pack(pady=10)
        ctk.CTkButton(win, text="Fermer", width=120, command=win.destroy).pack(pady=(10,16))

    def _build_ui(self):
        self.title("Sterilabel")
        self.geometry("700x700")

        # -------- CADRE VERT AUTOUR DE L'IMAGE --------
        self.image_frame = ctk.CTkFrame(
            self,
            border_width=15,            # épaisseur du cadre
            border_color=self.frame_color,      # couleur du cadre
            fg_color="transparent"     # pas de fond (facultatif)
        )
        self.image_frame.pack(pady=10, padx=10)

        # -------- IMAGE --------
        blank_image = Image.new("RGBA", (600, 240), (255, 255, 255, 0))
        image = ctk.CTkImage(
            light_image=blank_image,
            dark_image=blank_image,
            size=(600, 240)
        )

        self.image_label = ctk.CTkLabel(self.image_frame, image=image, text="")
        self.image_label.pack(padx=25, pady=25)

         # nb copies label
        self.labelinfo_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14))
        self.labelinfo_lbl.pack(pady=(0,10))

         # nb copies label
        copies_frame = ctk.CTkFrame(self)
        copies_frame.pack(pady=(10,0))
        
        copies_lbl = ctk.CTkLabel(copies_frame, text="Nombre de copies :", font=ctk.CTkFont(size=14))
        copies_lbl.pack(side="left", padx=(0, 10))
        
        self.copies_entry = ctk.CTkEntry(copies_frame, width=60, justify="center")
        self.copies_entry.insert(0, str(self.configdata.get("DEFAULT_COPIES")))
        self.copies_entry.pack(side="left")

        delbtn = ctk.CTkButton(
                    copies_frame,
                    text="DEL",
                    width=50,
                    command=self.delcopiesentry
                )
        delbtn.pack(side="left", padx=(10,0))
        
        # -------- 3×3 BUTTON GRID (1 to 9) --------
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(pady=5)

        # Create a 3×3 grid
        number = 0
        for row in range(2):
            for col in range(5):
                btn = ctk.CTkButton(
                    buttons_frame,
                    text=str(number),
                    width=50,
                    command=lambda n=number: self.set_copies(n)
                )
                btn.grid(row=row, column=col, padx=5, pady=5)
                number += 1

        # -------- BOUTON IMPRIMER --------
        self.print_button = ctk.CTkButton(
            self,
            text="Imprimer",
            width=250,
            height=40,
            command=self.print_action
        )
        self.print_button.pack(pady=20)

        # -------- BOUTON RECHERCHE MANUELLE --------
        self.manual_button = ctk.CTkButton(
            self,
            text="Recherche manuelle",
            width=150,
            command=self.on_manual_search,
            fg_color="#5f7294",
        )
        self.manual_button.pack(side="right", pady=10, padx=5)

    def delcopiesentry(self):
        self.copies_entry.delete(0, tk.END)

    def _redraw_border(self):        
        self.image_frame.configure(border_color=self.frame_color if self.frame_color else "transparent")

    def set_frame_color(self, color):
        if color in (None, ""):
            self.frame_color = None
        elif color.lower() in ("green", "red"):
            self.frame_color = color.lower()
        else:
            raise ValueError("Invalid color")
        self._redraw_border()

    def set_copies(self, number):
        self.copies_entry.insert(len(self.copies_entry.get()), str(number))

    def _process_event_queue(self):
        try:
            while not self.event_queue.empty():
                kind, str, str2 = self.event_queue.get_nowait()
                if kind == "created":
                    self.bmanualsearch = False
                    self.lines = self.app.parse_file(str)
                if kind == "frame_color":
                    self.set_frame_color(str)
                if kind == "show_image":
                    self.show_image(str, str2)
        except:
            traceback.print_exc()
        finally:
            self.after(200, self._process_event_queue)

    def show_image(self, path, str):
        try:
            image = Image.open(path)
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(240, 240))
            self.image_label.configure(image=ctk_image)
            if not self.bmanualsearch:
                self.labelinfo_lbl.configure(text=f"Chargé Automatiquement le : {time.strftime('%d/%m/%Y à %H:%M')} - {str}")
            else:
                self.labelinfo_lbl.configure(text=f"Chargé Manuellement le : {time.strftime('%d/%m/%Y à %H:%M')} - {str}")
        except Exception as e:
            print(f"Error loading image: {e}")
        self.current_image_path = path
    
    def on_manual_search(self):
        folder = self.app.watchfolder
        chosen = filedialog.askopenfilename(initialdir=folder, filetypes=[("PRO","*.PRO *.pro")])
        if chosen:
            self.bmanualsearch = True
            self.lines = self.app.parse_file(chosen, delay=0)

    def on_close(self):
        try:
            self.app.stop()
        except:
            pass
        self.destroy()

    def print_action(self):
        if self.current_image_path:
            self.app.print_action(self.lines, int(self.copies_entry.get()))

# --- Lancement ---
if __name__ == "__main__":
    app = SterilabelGUIApp()
    app.mainloop()
