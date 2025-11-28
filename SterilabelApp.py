import os
import re
import tempfile
import threading
import datetime
from tkinter import messagebox
from dateutil.relativedelta import relativedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import PrintLabel

class SterilabelApp:
    def __init__(self, watch_root, event_queue):
        self.watch_root = watch_root
        self.event_queue = event_queue
        self.observer = None
        self._start_observer()

    # -------------------------
    # Watchdog
    # -------------------------
    def _start_observer(self):
        self.watchfolder = current_mm_yyyy_folder(self.watch_root)
        if not os.path.exists(self.watchfolder):
            self.watchfolder = self.watch_root
        handler = PROFileHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(handler, self.watchfolder, recursive=False)
        if self.watchfolder != self.watch_root:
            self.observer.schedule(handler, self.watch_root, recursive=False)
        thread = threading.Thread(target=self.observer.start, daemon=True)
        thread.start()

    def parse_file(self, path, delay=2):
        parsed = self._try_parse_with_retries(path, delay=delay)
        if parsed:
            parsed["_source_path"] = path
            self._handle_parsed_pro(parsed)

    def _try_parse_with_retries(self, path, retries=5, delay=2):
        import time
        for _ in range(retries):
            try:
                time.sleep(delay)
                return self.parse_pro_file(path)
            except:
                time.sleep(delay)
        return None

    def _handle_parsed_pro(self, p):
        self.set_frame_color("green" if p.get("success") else "red")

        dt = datetime.datetime.strptime(p.get("date"), "%d.%m.%Y")
        expiration = dt + relativedelta(months=3)
        lines = [
            f"MELAG 44 B+  {p.get('serial_number')}",
            f"{dt.strftime('%d/%m/%Y')} - Exp: {expiration.strftime('%d/%m/%Y')}",
            f"Charges: {p.get('charges_jour')} / Total: {p.get('total')}",
            f"ID: {p.get('chargement_id')}"
        ]
        barcode = f"3{p.get('filename')}"

        tmp = os.path.join(tempfile.gettempdir(), "etiquette_label.png")
        PrintLabel.generate_label(tmp, lines, barcode)
        self.show_image(tmp, p.get("success_message"))


    def parse_pro_file(self,filepath):
        result = {
            "filename": os.path.splitext(os.path.basename(filepath))[0],
            "date": None,
            "charges_jour": None,
            "total": None,
            "chargement_id": None,
            "success": False,
            "success_message" : None,
            "serial_number": None
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = [ln.rstrip("\n\r") for ln in f]
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="latin-1") as f:
                lines = [ln.rstrip("\n\r") for ln in f]

        for raw in lines:
            line = raw.strip()
            if line.startswith("25") and "Date" in line:
                m = re.search(r"Date[:\s]*([\d\./-]+.*)$", line)
                if m:
                    result["date"] = m.group(1).strip()

            if line.startswith("30") and "Charges/Jour" in line:
                m = re.search(r"Charges\/Jour[:\s]*([0-9]+)\s+Total[:\s]*([0-9]+)", line)
                if m:
                    result["charges_jour"] = m.group(1)
                    result["total"] = m.group(2)

            if line.startswith("34") and "Chargement ID" in line:
                m = re.search(r"Chargement ID[:\s]*(.*)$", line)
                if m:
                    val = m.group(1).strip()
                    result["chargement_id"] = "-" if val.lower().startswith("désactiv") else val

            if line.startswith("40"):
                if re.search(r"terminé avec succès$", line.lower(), flags=re.IGNORECASE) or re.search(r"test réussi$", line, flags=re.IGNORECASE):
                    result["success"] = True
                    result["success_message"] = line[3:]

            if line.startswith("80") and ("N°" in line or "Série" in line or "Serie" in line):
                m = re.search(r"N.?\s*de\s*S[ée]rie[:\s]*(.+)$", line, flags=re.IGNORECASE)
                if not m:
                    m = re.search(r":\s*(\S.+)$", line)
                if m:
                    result["serial_number"] = m.group(1).strip()

        return result
    
    def set_frame_color(self, color):
        self.event_queue.put(("frame_color", color, ""))

    def show_image(self, path, str):
        self.event_queue.put(("show_image", path, str))

    def print_action(self, img_path, copies):
        if not os.path.exists(img_path):
            messagebox.showerror("Print error", "Image non trouvée")
            return
        
        try:
            for _ in range(copies):
                PrintLabel.print_image(img_path)
        except Exception as e:
            messagebox.showerror("Erreur d'impression", str(e))

    def reload_watchdog(self, watch_root):
        try:
            self.observer.stop()
        except:
            pass
        self.watch_root = watch_root
        self._start_observer()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=2)
        
# -------------------------
# Watchdog
# -------------------------
class PROFileHandler(FileSystemEventHandler):
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pro"):
            self.event_queue.put(("created", event.src_path, ""))

#    def on_moved(self, event):
#        if not event.is_directory and event.dest_path.lower().endswith(".pro"):
#            self.event_queue.put(("created", event.dest_path))

# -------------------------
# Helpers
# -------------------------
def current_mm_yyyy_folder(root, when=None):
    when = when or datetime.datetime.now()
    return os.path.join(root, f"{when.month:02d}_{when.year}")
