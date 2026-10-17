"""The main window (Phase 4 of the spec).

The window never applies a rule itself. It asks the Game to step forward, redraws the board,
and listens to the game's events (Observer pattern) to fill the log.
"""
import tkinter as tk
from tkinter import ttk

from ..ai import make_strategy
from ..ai.simulator import simulate
from ..engine import EventType, Game
from ..model import Board
from .assets import Assets
from .board_view import BoardView
from .program_panel import ProgramPanel

PLAYER_TYPES = {"Perceptron AI": "ai", "Random": "random", "Human": "human"}
LOGGED = {EventType.TURN_STARTED, EventType.CARD_PLAYED, EventType.PUSHED, EventType.ELIMINATED,
          EventType.CHECKPOINT, EventType.FINISHED, EventType.BONUS_PICKED, EventType.SHIELD_USED,
          EventType.JUMPED, EventType.DAMAGED, EventType.REPAIRED, EventType.CONVEYORS,
          EventType.GAME_WON, EventType.GAME_DRAW}


class RoboRallyApp(tk.Tk):
    def __init__(self, map_path: str):
        super().__init__()
        self.title("Robo Rally - mini version")
        self.resizable(False, False)
        self.board = Board.from_file(map_path)
        self.assets = Assets()
        self.game = None
        self.running = False
        self.after_id = None
        self.ghost = None

        self.board_view = BoardView(self, self.assets)
        self.board_view.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        side = ttk.Frame(self, padding=(0, 10, 10, 10))
        side.grid(row=0, column=1, sticky="ns")
        self._build_setup(side)
        self._build_controls(side)
        self.turn_label = ttk.Label(side, text="", font=("Segoe UI", 10, "bold"))
        self.turn_label.pack(anchor="w", pady=(8, 0))
        self.program_panel = ProgramPanel(side, self.on_program_change, self.on_program_confirm)
        self.tabs = ttk.Notebook(side)
        self.tabs.pack(fill="both", expand=True, pady=(8, 0))
        self._build_status(self.tabs)
        self._build_log(self.tabs)
        self.new_game()

    # ------------------------------------------------------------------ layout
    def _build_setup(self, parent):
        box = ttk.LabelFrame(parent, text="New game", padding=8)
        box.pack(fill="x")
        self.team_vars = {}
        for row, (team, default) in enumerate([(1, "Human"), (2, "Perceptron AI")]):
            ttk.Label(box, text=f"Team {team} ({'blue' if team == 1 else 'red'})").grid(row=row, column=0, sticky="w")
            var = tk.StringVar(value=default)
            ttk.Combobox(box, textvariable=var, values=list(PLAYER_TYPES), state="readonly", width=14).grid(
                row=row, column=1, padx=6, pady=2)
            self.team_vars[team] = var
        ttk.Label(box, text="Seed").grid(row=2, column=0, sticky="w")
        self.seed_var = tk.StringVar(value="")
        ttk.Entry(box, textvariable=self.seed_var, width=8).grid(row=2, column=1, sticky="w", padx=6)
        ttk.Button(box, text="Start", command=self.new_game).grid(row=0, column=2, rowspan=3, padx=(6, 0))

    def _build_controls(self, parent):
        box = ttk.LabelFrame(parent, text="Play", padding=8)
        box.pack(fill="x", pady=(8, 0))
        ttk.Button(box, text="Step", command=self.step_once).grid(row=0, column=0)
        ttk.Button(box, text="Play turn", command=self.play_turn).grid(row=0, column=1, padx=4)
        self.run_button = ttk.Button(box, text="Auto ▶", command=self.toggle_run)
        self.run_button.grid(row=0, column=2)
        ttk.Label(box, text="Speed").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.speed = tk.IntVar(value=250)
        ttk.Scale(box, from_=800, to=20, variable=self.speed, orient="horizontal", length=180).grid(
            row=1, column=1, columnspan=2, sticky="we", pady=(6, 0))

    def _build_status(self, tabs):
        box = ttk.Frame(tabs, padding=6)
        tabs.add(box, text="Robots")
        columns = ("robot", "pos", "next", "state", "bonus")
        self.table = ttk.Treeview(box, columns=columns, show="headings", height=4)
        for col, text, width in zip(columns, ("Robot", "Cell", "Next CP", "State", "Bonuses"),
                                    (62, 52, 58, 70, 78)):
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="center")
        self.table.pack(fill="x")

    def _build_log(self, tabs):
        box = ttk.Frame(tabs, padding=6)
        tabs.add(box, text="What happened")
        self.log = tk.Text(box, width=46, height=6, font=("Consolas", 9), state="disabled", wrap="word")
        scroll = ttk.Scrollbar(box, command=self.log.yview)
        self.log.config(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ------------------------------------------------------------------ game control
    def new_game(self):
        self.stop()
        seed = int(self.seed_var.get()) if self.seed_var.get().strip().isdigit() else None
        strategies = {team: make_strategy(PLAYER_TYPES[var.get()]) for team, var in self.team_vars.items()}
        self.game = Game(self.board, strategies, seed=seed)
        self.game.bus.subscribe(self.on_event)              # Observer: the log listens to the game
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.ghost = None
        self.step_once()                                    # draw the first hands

    def step_once(self):
        if self.game.step():
            self.refresh()
            return True
        self.refresh()
        return False

    def play_turn(self):
        self.game.play_turn()
        self.refresh()

    def toggle_run(self):
        if self.running:
            self.stop()
        else:
            self.running = True
            self.run_button.config(text="Pause ⏸")
            self._tick()

    def stop(self):
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if hasattr(self, "run_button"):
            self.run_button.config(text="Auto ▶")

    def _tick(self):
        if not self.running:
            return
        if self.step_once():
            self.after_id = self.after(int(self.speed.get()), self._tick)
        elif self.game.waiting_for():
            self.after_id = self.after(200, self._tick)     # wait for the person, then continue
        else:
            self.stop()                                     # game over

    # ------------------------------------------------------------------ human player
    def waiting_robot(self):
        waiting = self.game.waiting_for()
        return waiting[0] if waiting else None

    def on_program_change(self, cards):
        robot = self.waiting_robot()
        self.ghost = None
        if robot and cards:
            result = simulate(self.game.state, robot.id, cards)
            self.ghost = result.robot.position if result.robot.on_board() else None
        self.draw_board()

    def on_program_confirm(self, cards):
        robot = self.waiting_robot()
        if robot:
            self.game.submit_program(robot.id, cards)
            self.ghost = None
            self.step_once()

    # ------------------------------------------------------------------ drawing
    def refresh(self):
        robot = self.waiting_robot()
        if robot:
            if not self.program_panel.winfo_ismapped() or self.program_panel.title.cget("text").split(":")[0] != robot.id:
                self.program_panel.pack(fill="x", pady=(8, 0), before=self.tabs)
                self.program_panel.show(robot.id, self.game.hands[robot.id], self.game.program_size(robot))
        else:
            self.program_panel.pack_forget()
        self.draw_board()
        state = self.game.state
        phase = self.game.phase.name
        self.turn_label.config(text=f"Turn {state.turn}   ·   {phase}" + ("   ·   your turn to choose" if robot else ""))
        self.table.delete(*self.table.get_children())
        for r in state.robots():
            status = "finished" if r.finished() and r.on_board() else r.status.value
            nxt = "-" if r.finished() else f"CP{r.next_cp}"
            self.table.insert("", "end", values=(r.id, str(r.position) if r.on_board() else "-", nxt, status,
                                                 " ".join(b.name.title() for b in r.bonuses)))

    def draw_board(self):
        state = self.game.state
        robot = self.waiting_robot()
        message = None
        if state.over:
            message = f"{state.winner.name} wins!" if state.winner else "Draw"
        self.board_view.draw(state, highlight=robot.id if robot else None, ghost=self.ghost, message=message)

    def on_event(self, event):
        if event.type not in LOGGED:
            return
        text = f"── Turn {event.data['turn']} ──" if event.type is EventType.TURN_STARTED else str(event)
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")


def run_app(map_path: str) -> None:
    RoboRallyApp(map_path).mainloop()
