import tkinter as tk
from tkinter import ttk, font
import sv_ttk
from network.client import BlackjackClient
import platform
import re
import time

COUNTDOWN_RE = re.compile(r"^GAME_COUNTDOWN (\d+)$")
TURN_RE = re.compile(r"^TURN:\s+(.+)$")
STATE_RE = re.compile(r"^STATE:\s+(.+)$")
RESULT_RE = re.compile(r"^RESULT:\s+(.+?)\s+(WIN|LOSE|PUSH)$", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^RESULT_SUMMARY:")
EVENT_RE = re.compile(r"^EVENT:\s+(JOIN|LEAVE|JOIN_WAIT)\s+(.+)$")
ACTION_RE = re.compile(r"^ACTION:\s+(HIT|STAND|BUST)\s+([^\s]+)(?:\s+(.*))?$")
PING_RE = re.compile(r"^PING$")

class BlackjackGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Blackjack")
        self.geometry("880x600")

        self.client = BlackjackClient()
        self.q = []
        self.players = {}
        self.dealer = {"cards":"", "value":"", "hidden":True}
        self.turn = ""
        self.connected = False
        self._ping_start_ns = None

        if platform.system() == "Windows":
            sv_ttk.set_theme("dark")

        top = ttk.Frame(self); top.pack(fill="x", pady=4)
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="5555")
        self.name_var = tk.StringVar(value="Player")
        ttk.Entry(top, textvariable=self.host_var, width=12).pack(side="left")
        ttk.Entry(top, textvariable=self.port_var, width=6).pack(side="left", padx=4)
        ttk.Entry(top, textvariable=self.name_var, width=12).pack(side="left")
        self.btn_connect = ttk.Button(top, text="Connect", command=self.on_connect)
        self.btn_connect.pack(side="left", padx=4)
        self.btn_hit = ttk.Button(top, text="Hit", command=lambda: self.send("HIT"))
        self.btn_stand = ttk.Button(top, text="Stand", command=lambda: self.send("STAND"))
        self.btn_ping = ttk.Button(top, text="Ping", command=self.ping)
        self.btn_hit.pack(side="left"); self.btn_stand.pack(side="left"); self.btn_ping.pack(side="left")
        self.count_var = tk.StringVar()
        ttk.Label(top, textvariable=self.count_var, foreground="white").pack(side="right")

        mid = ttk.Frame(self); mid.pack(fill="both", expand=True, padx=8, pady=4)
        self.tree = ttk.Treeview(mid, columns=("Name","Cards","Value","Status", "Ping"), show="headings", height=14)
        for c in ("Name","Cards","Value","Status", "Ping"):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160 if c=="Cards" else 80, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        self.log = tk.Text(mid, width=40)
        self.log.pack(side="right", fill="both", expand=True)

        self.log.configure(font=("Menlo", 11))
        self.log.tag_config("header", foreground="#ffffff", background="#333333", font=("Menlo", 11, "bold"))
        self.log.tag_config("action", foreground="#0b6e99")
        self.log.tag_config("result_win", foreground="#008800", font=("Menlo", 11, "bold"))
        self.log.tag_config("result_lose", foreground="#aa0000", font=("Menlo", 11, "bold"))
        self.log.tag_config("result_push", foreground="#555555")
        self.log.tag_config("event", foreground="#6e4fa3")
        self.log.tag_config("countdown", foreground="#b8860b")
        self.log.tag_config("turn", foreground="#004488", font=("Menlo", 11, "italic"))
        self.log.tag_config("error", foreground="#ff0000", underline=1)


        self.after(100, self._pump)
        self._update_buttons()

    def ping(self):
        self._ping_start_ns = time.perf_counter_ns()
        self.send("PING")
        print("Ping sent")

    def on_connect(self):
        if self.connected: return
        self.client.connect(self.host_var.get(), int(self.port_var.get()), self.name_var.get(), self._on_message)
        self.connected = True
        self._update_buttons()

    def send(self, cmd):
        if not self.connected: return
        self.client.send(cmd.strip())

    def _on_message(self, text):
        for line in text.splitlines():
            self.q.append(line)

    def _pump(self):
        while self.q:
            self._handle_line(self.q.pop(0))
        self.after(100, self._pump)

    def _handle_line(self, line):
        m = COUNTDOWN_RE.match(line)
        if m:
            self.count_var.set(f"Starting in {m.group(1)}s")
            return
        if line == "GAME_START":
            self.count_var.set("")
            return
        tm = TURN_RE.match(line)
        if tm:
            self.turn = tm.group(1)
            self._rebuild()
            self._update_buttons()
            return
        sm = STATE_RE.match(line)
        if sm:
            self._update_state_line(line)
            return
        rm = RESULT_RE.match(line)
        if rm:
            self._log(line, "result_push")
            return
        if SUMMARY_RE.match(line):
            self._log(line, "header")
            return
        em = EVENT_RE.match(line)
        if em:
            self._log(line, "event")
            return
        am = ACTION_RE.match(line)
        if am:
            self._log(line, "action")
            return
        pm = PING_RE.match(line)
        if pm:
            print("Ping returned!")
            #Set ping value to timer
            if hasattr(self, "_ping_start_ns"):
                elapsed_ns = time.perf_counter_ns() - self._ping_start_ns
                self.ping_ms = round(elapsed_ns / 1_000_000)  # ns -> ms (float)
            else:
                self.ping_ms = ""  # no start time, edge case
            my_name = self.name_var.get()
            if my_name in self.players:
                self.players[my_name]["ping"] = self.ping_ms
            self._rebuild()
            return
        if line in ("ROUND_START","ROUND_END"):
            self._log(line, "header")
            if line == "ROUND_START":
                self.players = {}
                self.dealer = {"cards":"", "value":"", "hidden":True}
                self.turn = ""
                self._rebuild()
            return
        self._log(line, "header")

    def _update_state_line(self, line):
        body = line[len("STATE:"):].strip()
        parts = [p.strip() for p in body.split("|")]
        header = parts[0]
        cards = parts[1] if len(parts) > 1 else ""
        value_part = parts[2] if len(parts) > 2 else ""
        tokens = header.split()
        role = tokens[0].upper()
        if role == "PLAYER":
            name = " ".join(tokens[1:])
            val = ""
            if value_part.startswith("VALUE="):
                val = value_part.split("=",1)[1]
            self.players[name] = {"cards":cards, "value":val, "ping": ""}
        elif role == "DEALER":
            hidden = tokens[1].upper() == "HIDDEN"
            if hidden:
                self.dealer = {"cards":cards, "value":"", "hidden":True}
            else:
                val = ""
                if value_part.startswith("VALUE="):
                    val = value_part.split("=",1)[1]
                self.dealer = {"cards":cards, "value":val, "hidden":False}
        self._rebuild()

    def _rebuild(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        dealer_status = "Hidden" if self.dealer.get("hidden") else ""
        
        turn_mark = " ←" if self.turn == "Dealer" else ""
        self.tree.insert("", "end", values=("Dealer"+turn_mark, self.dealer["cards"], self.dealer["value"], dealer_status))
        for name in sorted(self.players.keys()):
            p = self.players[name]
            status = ""
            if p["value"] and int(p["value"]) > 21:
                status = "Bust"
            mark = " ←" if self.turn == name else ""
            print(self.players)
            ping = self.players[name]["ping"]
            self.tree.insert("", "end", values=(name + mark, p["cards"], p["value"], status, ping))

    def _update_buttons(self):
        my_name = self.name_var.get()
        my_turn = (self.turn == my_name)
        state_ok = self.connected and my_turn
        if state_ok:
            self.btn_hit.state(["!disabled"])
            self.btn_stand.state(["!disabled"])
            
        else:
            self.btn_hit.state(["disabled"])
            self.btn_stand.state(["disabled"])
        if self.connected:
            self.btn_ping.state(["!disabled"])
        else:
            self.btn_ping.state(["disabled"])

    def _log(self, line, font_tag):
        self.log.insert("end", f"{line}\n", font_tag)
        self.log.see("end")

def run_gui():
    app = BlackjackGUI()
    app.mainloop()

if __name__ == "__main__":
    run_gui()