import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
IMG_SIZE = 48
TEAM_IMG_SIZE = 56
TRAIT_ICON_SIZE = 20
GRID_COLS = 10
LOCKED_GRID_COLS = 8
TIER_SCORES = {"S": 10, "A": 7, "B": 5, "C": 3, "D": 1}
TIER_COLORS = {"S": "#ff7f7f", "A": "#ffbf7f", "B": "#ffdf7f", "C": "#7fbfff", "D": "#aaaaaa"}
# Trait threshold tier colors: bronze, silver, gold, prismatic
TRAIT_TIER_COLORS = ["#cd7f32", "#ffffff", "#ffd700", "#e45fff"]
# Cost border colors (like in-game): 1g gray, 2g green, 3g blue, 4g purple, 5g+ gold
COST_COLORS = {1: "#888888", 2: "#11b288", 3: "#207ac7", 4: "#c440da", 5: "#ffb93b",
               6: "#ffb93b", 7: "#ffb93b"}
# Recommended champion highlight color
REC_HIGHLIGHT = "#e8a33c"

# Level -> probability (0-1) per unit cost (1-5). Cost 6/7 use cost 5 odds.
ROLL_ODDS = {
    2:  {1: 1.00, 2: 0.00, 3: 0.00, 4: 0.00, 5: 0.00},
    3:  {1: 0.75, 2: 0.25, 3: 0.00, 4: 0.00, 5: 0.00},
    4:  {1: 0.55, 2: 0.30, 3: 0.15, 4: 0.00, 5: 0.00},
    5:  {1: 0.45, 2: 0.33, 3: 0.20, 4: 0.02, 5: 0.00},
    6:  {1: 0.30, 2: 0.40, 3: 0.25, 4: 0.05, 5: 0.00},
    7:  {1: 0.16, 2: 0.30, 3: 0.43, 4: 0.10, 5: 0.01},
    8:  {1: 0.15, 2: 0.20, 3: 0.32, 4: 0.30, 5: 0.03},
    9:  {1: 0.10, 2: 0.17, 3: 0.25, 4: 0.33, 5: 0.15},
    10: {1: 0.05, 2: 0.10, 3: 0.20, 4: 0.40, 5: 0.25},
    11: {1: 0.01, 2: 0.02, 3: 0.12, 4: 0.50, 5: 0.35},
}


def load_data():
    with open(os.path.join(DATA_DIR, "units.json"), encoding="utf-8") as f:
        units = json.load(f)
    with open(os.path.join(DATA_DIR, "traits.json"), encoding="utf-8") as f:
        traits_raw = json.load(f)
    trait_thresholds = {}
    trait_icons = {}
    for t in traits_raw:
        trait_thresholds.setdefault(t["name"], []).append(t["count"])
        if t["name"] not in trait_icons:
            trait_icons[t["name"]] = t.get("image")
    for k in trait_thresholds:
        trait_thresholds[k] = sorted(set(trait_thresholds[k]))
    return units, trait_thresholds, trait_icons


def _count_available_for_trait(trait_name, selected_names, unlocked_names, units):
    """Count how many more units with this trait are available to pick."""
    count = 0
    for u in units:
        if u["name"] in selected_names:
            continue
        if u["locked"] and u["name"] not in unlocked_names:
            continue
        if trait_name in u["traits"]:
            count += 1
    return count


DEFAULT_WEIGHTS = {"tier": 1.0, "traits": 1.0, "odds": 1.0, "multi_synergy": 1.0}


def compute_trait_score(candidate, selected_units, all_units_map, trait_thresholds,
                        unlocked_names=None, all_units=None, weights=None):
    """Score based on trait synergy. Returns (total_trait_score, matching_traits set)."""
    w = weights or DEFAULT_WEIGHTS
    trait_w = w.get("traits", 1.0)
    multi_w = w.get("multi_synergy", 1.0)

    selected_traits = {}
    for name in selected_units:
        for t in all_units_map[name]["traits"]:
            selected_traits[t] = selected_traits.get(t, 0) + 1

    score = 0
    matching = set()
    for t in candidate["traits"]:
        current = selected_traits.get(t, 0)
        new = current + 1
        thresholds = trait_thresholds.get(t, [])

        if current > 0:
            matching.add(t)

        # Bonus for crossing a threshold (activating a new tier)
        for i, th in enumerate(thresholds):
            tier_bonus = (i + 1) * 3
            if new >= th > current:
                score += tier_bonus * trait_w
            elif new >= th:
                score += 1 * trait_w

        # Proximity bonus: reward getting closer to the next threshold
        if current > 0:
            next_th = None
            next_tier = 0
            for i, th in enumerate(thresholds):
                if th > current:
                    next_th = th
                    next_tier = i + 1
                    break
            if next_th:
                missing = next_th - new
                if missing == 0:
                    pass  # Already handled by threshold crossing above
                else:
                    if all_units is not None and unlocked_names is not None:
                        available = _count_available_for_trait(
                            t, selected_units, unlocked_names, all_units)
                        units_still_needed = next_th - new
                        if available < units_still_needed:
                            proximity = new / next_th
                            score += proximity * next_tier * 0.5 * trait_w
                            continue
                    proximity = new / next_th
                    score += proximity * next_tier * 3 * trait_w
            else:
                score += 1 * trait_w

    # Multi-synergy bonus
    if len(matching) >= 2:
        score += len(matching) * 2 * multi_w

    return score, matching


def get_roll_odds(level, cost):
    """Get the probability of rolling a unit of given cost at given level."""
    odds = ROLL_ODDS.get(level, ROLL_ODDS[11])
    lookup_cost = min(cost, 5)
    return odds.get(lookup_cost, 0.0)


def compute_recommendations(selected_names, team_size, unlocked_names, units,
                            trait_thresholds, weights=None):
    w = weights or DEFAULT_WEIGHTS
    all_units_map = {u["name"]: u for u in units}
    level = team_size
    slots = team_size - len(selected_names)
    if slots <= 0:
        return []

    tier_w = w.get("tier", 1.0)
    odds_w = w.get("odds", 1.0)

    def _score_unit(u, team):
        odds = get_roll_odds(level, u["cost"])
        if odds <= 0:
            return None
        tier_score = TIER_SCORES.get(u["tier"], 0) * tier_w
        trait_score, matching = compute_trait_score(
            u, team, all_units_map, trait_thresholds, unlocked_names, units, w)
        raw_score = tier_score + trait_score
        # odds_w controls how much drop rate matters: 0=ignore odds, 1=full weight
        total = raw_score * (odds ** odds_w) if odds_w > 0 else raw_score
        return (total, tier_score, trait_score, odds, matching, u)

    # Score each candidate individually
    candidates = []
    for u in units:
        if u["name"] in selected_names:
            continue
        if u["locked"] and u["name"] not in unlocked_names:
            continue
        entry = _score_unit(u, selected_names)
        if entry:
            candidates.append(entry)

    if slots <= 1 or not candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[:slots]

    # Combo optimization: greedy approach with re-scoring after each pick
    combo = []
    used = set(selected_names)
    for _ in range(slots):
        best = None
        for c in candidates:
            u = c[5]
            if u["name"] in used:
                continue
            entry = _score_unit(u, used)
            if entry and (best is None or entry[0] > best[0]):
                best = entry
        if best is None:
            break
        combo.append(best)
        used.add(best[5]["name"])

    return combo


class TFTFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TFT Finder - Season 16")
        self.root.configure(bg="#1d1e20")

        self.units, self.trait_thresholds, self.trait_icon_paths = load_data()
        self.units_map = {u["name"]: u for u in self.units}
        self.normal_units = [u for u in self.units if not u["locked"]]
        self.locked_units = [u for u in self.units if u["locked"]]
        self.selected = set()
        self.unlocked = set()
        self.unlock_vars = {}
        self.unit_images = {}
        self.team_images = {}
        self.trait_images = {}
        self.unit_widgets = {}
        self.recommended_names = set()
        self.history = []  # undo history: list of previous selected sets
        self.sort_mode = "default"  # default, cost, tier
        self.config_visible = False

        # Scoring weight variables (DoubleVar created after root exists)
        self.w_tier = tk.DoubleVar(value=1.0)
        self.w_traits = tk.DoubleVar(value=1.0)
        self.w_odds = tk.DoubleVar(value=1.0)
        self.w_multi = tk.DoubleVar(value=1.0)

        self._load_images()
        self._build_ui()
        self._refresh()

        # Keyboard shortcuts
        self.root.bind("<Control-z>", lambda _: self._undo())
        self.root.bind("<Escape>", lambda _: self._reset_selection())

    def _load_images(self):
        for u in self.units:
            path = os.path.join(DATA_DIR, u["image"])
            if os.path.exists(path):
                img = Image.open(path)
                self.unit_images[u["name"]] = ImageTk.PhotoImage(
                    img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS))
                self.team_images[u["name"]] = ImageTk.PhotoImage(
                    img.resize((TEAM_IMG_SIZE, TEAM_IMG_SIZE), Image.LANCZOS))
        for trait_name, img_path in self.trait_icon_paths.items():
            if img_path:
                full = os.path.join(DATA_DIR, img_path)
                if os.path.exists(full):
                    img = Image.open(full).resize((TRAIT_ICON_SIZE, TRAIT_ICON_SIZE), Image.LANCZOS)
                    self.trait_images[trait_name] = ImageTk.PhotoImage(img)

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg="#2a2b2e", pady=8, padx=12)
        top.pack(fill=tk.X)

        tk.Label(top, text="Taille equipe:", bg="#2a2b2e", fg="white",
                 font=("Segoe UI", 11)).pack(side=tk.LEFT)

        self.team_size_var = tk.IntVar(value=6)
        self.team_slider = tk.Scale(top, from_=1, to=10, orient=tk.HORIZONTAL,
                                     variable=self.team_size_var, bg="#2a2b2e", fg="white",
                                     highlightthickness=0, troughcolor="#444",
                                     command=lambda _: self._refresh())
        self.team_slider.pack(side=tk.LEFT, padx=(8, 24))

        self.selection_count_label = tk.Label(top, text="", bg="#2a2b2e", fg="#aaa",
                                              font=("Segoe UI", 10))
        self.selection_count_label.pack(side=tk.RIGHT)

        tk.Button(top, text="Reset", bg="#ff5555", fg="white",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=2,
                  command=self._reset_selection).pack(side=tk.RIGHT, padx=(0, 12))

        tk.Button(top, text="Config", bg="#444", fg="white",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=10, pady=2,
                  command=self._toggle_config).pack(side=tk.RIGHT, padx=(0, 6))

        # Config panel (hidden by default)
        self.config_frame = tk.Frame(self.root, bg="#333", pady=8, padx=12)

        cfg_title = tk.Frame(self.config_frame, bg="#333")
        cfg_title.pack(fill=tk.X, pady=(0, 6))
        tk.Label(cfg_title, text="Poids du scoring", bg="#333", fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(cfg_title, text="Reset config", bg="#555", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
                  command=self._reset_config).pack(side=tk.RIGHT)

        sliders_frame = tk.Frame(self.config_frame, bg="#333")
        sliders_frame.pack(fill=tk.X)

        slider_defs = [
            ("Tier", self.w_tier, "Puissance brute (S > A > B...)"),
            ("Synergies", self.w_traits, "Bonus des traits actives"),
            ("Odds", self.w_odds, "Probabilite de trouver l'unite"),
            ("Multi-synergie", self.w_multi, "Bonus si 2+ traits matchent"),
        ]
        for label, var, desc in slider_defs:
            sf = tk.Frame(sliders_frame, bg="#333")
            sf.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=8)
            tk.Label(sf, text=label, bg="#333", fg="#aaa",
                     font=("Segoe UI", 9, "bold")).pack()
            tk.Label(sf, text=desc, bg="#333", fg="#666",
                     font=("Segoe UI", 7)).pack()
            tk.Scale(sf, from_=0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                     variable=var, bg="#333", fg="white", highlightthickness=0,
                     troughcolor="#555", length=120,
                     command=lambda _: self._refresh()).pack()

        # Preset strategies
        presets_frame = tk.Frame(self.config_frame, bg="#333")
        presets_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(presets_frame, text="Presets:", bg="#333", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))

        presets = [
            ("Equilibre", {"tier": 1.0, "traits": 1.0, "odds": 1.0, "multi_synergy": 1.0}),
            ("Synergie max", {"tier": 0.3, "traits": 2.0, "odds": 0.5, "multi_synergy": 2.0}),
            ("Brute force", {"tier": 2.0, "traits": 0.5, "odds": 1.0, "multi_synergy": 0.3}),
            ("Ignorer les odds", {"tier": 1.0, "traits": 1.0, "odds": 0.0, "multi_synergy": 1.0}),
        ]
        for name, values in presets:
            tk.Button(presets_frame, text=name, bg="#555", fg="white",
                      font=("Segoe UI", 8), relief=tk.FLAT, padx=8, pady=2,
                      command=lambda v=values: self._apply_preset(v)
                      ).pack(side=tk.LEFT, padx=2)

        # Search bar + sort buttons
        search_bar = tk.Frame(self.root, bg="#2a2b2e", pady=6, padx=12)
        search_bar.pack(fill=tk.X)

        tk.Label(search_bar, text="Recherche:", bg="#2a2b2e", fg="white",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_grid_filter())
        search_entry = tk.Entry(search_bar, textvariable=self.search_var, bg="#444", fg="white",
                                insertbackground="white", font=("Segoe UI", 10), width=25,
                                relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, padx=(8, 12))

        tk.Label(search_bar, text="nom, cout (ex: 3) ou trait", bg="#2a2b2e", fg="#888",
                 font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT)

        # Sort buttons
        sort_frame = tk.Frame(search_bar, bg="#2a2b2e")
        sort_frame.pack(side=tk.RIGHT)

        tk.Label(sort_frame, text="Tri:", bg="#2a2b2e", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))

        self.sort_buttons = {}
        for mode, label in [("default", "Defaut"), ("cost", "Cout"), ("tier", "Tier")]:
            btn = tk.Button(sort_frame, text=label, bg="#444", fg="white",
                            font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
                            command=lambda m=mode: self._set_sort(m))
            btn.pack(side=tk.LEFT, padx=1)
            self.sort_buttons[mode] = btn
        self._update_sort_buttons()

        # Main area
        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1d1e20",
                              sashwidth=4, sashrelief=tk.FLAT)
        main.pack(fill=tk.BOTH, expand=True)

        # Left: champion grids (normal + locked)
        left_frame = tk.Frame(main, bg="#1d1e20")
        main.add(left_frame, stretch="always")

        left_container = tk.Frame(left_frame, bg="#1d1e20")
        left_container.pack(fill=tk.BOTH, expand=True)

        left_canvas = tk.Canvas(left_container, bg="#1d1e20", highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient=tk.VERTICAL, command=left_canvas.yview)
        self.left_scroll_frame = tk.Frame(left_canvas, bg="#1d1e20")

        self.left_scroll_frame.bind("<Configure>",
                                     lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.create_window((0, 0), window=self.left_scroll_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Normal champions section ---
        tk.Label(self.left_scroll_frame, text="Champions", bg="#1d1e20", fg="white",
                 font=("Segoe UI", 12, "bold"), pady=4).pack(anchor="w", padx=8)

        self.grid_frame = tk.Frame(self.left_scroll_frame, bg="#1d1e20")
        self.grid_frame.pack(fill=tk.X, padx=4, pady=4)

        self._build_champion_grid(self.normal_units, self.grid_frame, GRID_COLS)

        # --- Locked champions section ---
        sep = tk.Frame(self.left_scroll_frame, bg="#444", height=2)
        sep.pack(fill=tk.X, padx=8, pady=(8, 4))

        locked_header = tk.Frame(self.left_scroll_frame, bg="#1d1e20")
        locked_header.pack(fill=tk.X, padx=8)

        tk.Label(locked_header, text="Champions verrouilles", bg="#1d1e20", fg="#e8a33c",
                 font=("Segoe UI", 12, "bold"), pady=4).pack(side=tk.LEFT)

        btn_frame = tk.Frame(locked_header, bg="#1d1e20")
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text="Tout debloquer", bg="#444", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2,
                  command=self._unlock_all).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Tout verrouiller", bg="#444", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2,
                  command=self._lock_all).pack(side=tk.LEFT, padx=2)

        self.locked_grid_frame = tk.Frame(self.left_scroll_frame, bg="#1d1e20")
        self.locked_grid_frame.pack(fill=tk.X, padx=4, pady=4)

        self._build_locked_grid()

        # Right panel: team + traits + recommendations
        right_panel = tk.Frame(main, bg="#1d1e20", width=380)
        main.add(right_panel, stretch="never")

        # -- Mon equipe --
        team_section = tk.LabelFrame(right_panel, text="Mon equipe", bg="#1d1e20", fg="white",
                                      font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                      labelanchor="n", padx=4, pady=4)
        team_section.pack(fill=tk.X, padx=4, pady=(4, 2))

        self.team_frame = tk.Frame(team_section, bg="#1d1e20")
        self.team_frame.pack(fill=tk.X)

        # -- Traits actifs --
        traits_section = tk.LabelFrame(right_panel, text="Traits actifs", bg="#1d1e20", fg="white",
                                        font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                        labelanchor="n", padx=4, pady=4)
        traits_section.pack(fill=tk.X, padx=4, pady=2)

        self.traits_frame = tk.Frame(traits_section, bg="#1d1e20")
        self.traits_frame.pack(fill=tk.X)

        # -- Recommandations --
        rec_section = tk.LabelFrame(right_panel, text="Recommandations", bg="#1d1e20", fg="white",
                                     font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                     labelanchor="n", padx=4, pady=4)
        rec_section.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))

        rec_container = tk.Frame(rec_section, bg="#1d1e20")
        rec_container.pack(fill=tk.BOTH, expand=True)

        rec_canvas = tk.Canvas(rec_container, bg="#1d1e20", highlightthickness=0, width=350)
        rec_scrollbar = ttk.Scrollbar(rec_container, orient=tk.VERTICAL, command=rec_canvas.yview)
        self.rec_frame = tk.Frame(rec_canvas, bg="#1d1e20")

        self.rec_frame.bind("<Configure>",
                            lambda e: rec_canvas.configure(scrollregion=rec_canvas.bbox("all")))
        rec_canvas.create_window((0, 0), window=self.rec_frame, anchor="nw")
        rec_canvas.configure(yscrollcommand=rec_scrollbar.set)

        rec_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rec_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_champion_grid(self, unit_list, parent, cols):
        for i, u in enumerate(unit_list):
            row, col = divmod(i, cols)
            cost_color = COST_COLORS.get(u["cost"], "#888")
            frame = tk.Frame(parent, bg=cost_color, padx=2, pady=2, cursor="hand2",
                             bd=2, relief=tk.FLAT)
            frame.grid(row=row, column=col, padx=2, pady=2)

            img = self.unit_images.get(u["name"])
            lbl_img = tk.Label(frame, image=img, bg="#333", bd=0)
            lbl_img.pack()

            lbl_name = tk.Label(frame, text=u["name"], bg="#1d1e20", fg="white",
                                font=("Segoe UI", 7), wraplength=IMG_SIZE + 10)
            lbl_name.pack(fill=tk.X)

            self.unit_widgets[u["name"]] = (frame, lbl_img, lbl_name)

            for widget in (frame, lbl_img, lbl_name):
                widget.bind("<Button-1>", lambda e, name=u["name"]: self._toggle(name))

    def _build_locked_grid(self):
        for i, u in enumerate(self.locked_units):
            row, col = divmod(i, LOCKED_GRID_COLS)
            cost_color = COST_COLORS.get(u["cost"], "#888")
            frame = tk.Frame(self.locked_grid_frame, bg=cost_color, padx=2, pady=2,
                             bd=2, relief=tk.FLAT)
            frame.grid(row=row, column=col, padx=2, pady=2)

            var = tk.BooleanVar(value=False)
            self.unlock_vars[u["name"]] = var

            img = self.unit_images.get(u["name"])
            lbl_img = tk.Label(frame, image=img, bg="#555", bd=0, cursor="hand2")
            lbl_img.pack()

            cb_frame = tk.Frame(frame, bg="#1d1e20")
            cb_frame.pack(fill=tk.X)

            cb = tk.Checkbutton(cb_frame, variable=var, bg="#1d1e20", selectcolor="#444",
                                activebackground="#1d1e20", highlightthickness=0,
                                command=lambda n=u["name"]: self._on_unlock_toggle(n))
            cb.pack(side=tk.LEFT)

            lbl_name = tk.Label(cb_frame, text=u["name"], bg="#1d1e20", fg="#666",
                                font=("Segoe UI", 7), wraplength=IMG_SIZE + 10, cursor="hand2")
            lbl_name.pack(side=tk.LEFT)

            self.unit_widgets[u["name"]] = (frame, lbl_img, lbl_name)

            for widget in (lbl_img, lbl_name):
                widget.bind("<Button-1>", lambda e, name=u["name"]: self._toggle_locked(name))

    def _toggle_config(self):
        self.config_visible = not self.config_visible
        if self.config_visible:
            # Insert config panel after top bar (index 1)
            self.config_frame.pack(fill=tk.X, after=self.root.winfo_children()[0])
        else:
            self.config_frame.pack_forget()

    def _apply_preset(self, values):
        self.w_tier.set(values["tier"])
        self.w_traits.set(values["traits"])
        self.w_odds.set(values["odds"])
        self.w_multi.set(values["multi_synergy"])
        self._refresh()

    def _reset_config(self):
        self._apply_preset(DEFAULT_WEIGHTS)

    def _get_weights(self):
        return {
            "tier": self.w_tier.get(),
            "traits": self.w_traits.get(),
            "odds": self.w_odds.get(),
            "multi_synergy": self.w_multi.get(),
        }

    def _set_sort(self, mode):
        self.sort_mode = mode
        self._update_sort_buttons()
        self._resort_grid()

    def _update_sort_buttons(self):
        for m, btn in self.sort_buttons.items():
            if m == self.sort_mode:
                btn.config(bg="#666", relief=tk.SUNKEN)
            else:
                btn.config(bg="#444", relief=tk.FLAT)

    def _resort_grid(self):
        if self.sort_mode == "cost":
            sorted_units = sorted(self.normal_units, key=lambda u: (u["cost"], u["name"]))
        elif self.sort_mode == "tier":
            tier_order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
            sorted_units = sorted(self.normal_units, key=lambda u: (tier_order.get(u["tier"], 9), u["name"]))
        else:
            sorted_units = self.normal_units

        for i, u in enumerate(sorted_units):
            row, col = divmod(i, GRID_COLS)
            frame, _, _ = self.unit_widgets[u["name"]]
            frame.grid(row=row, column=col, padx=2, pady=2)

        self._refresh_grid_filter()

    def _on_unlock_toggle(self, name):
        if self.unlock_vars[name].get():
            self.unlocked.add(name)
        else:
            self.unlocked.discard(name)
            self.selected.discard(name)
        self._refresh()

    def _unlock_all(self):
        for u in self.locked_units:
            self.unlock_vars[u["name"]].set(True)
            self.unlocked.add(u["name"])
        self._refresh()

    def _lock_all(self):
        for u in self.locked_units:
            self.unlock_vars[u["name"]].set(False)
            self.unlocked.discard(u["name"])
            self.selected.discard(u["name"])
        self._refresh()

    def _toggle_locked(self, name):
        if name not in self.unlocked:
            return
        self._toggle(name)

    def _matches_filter(self, unit, query):
        if not query:
            return True
        q = query.lower()
        if q in unit["name"].lower():
            return True
        if q.isdigit() and int(q) == unit["cost"]:
            return True
        for t in unit["traits"]:
            if q in t.lower():
                return True
        return False

    def _reset_selection(self):
        if self.selected:
            self.history.append(set(self.selected))
        self.selected.clear()
        self._refresh()

    def _undo(self):
        if self.history:
            self.selected = self.history.pop()
            self._refresh()

    def _refresh_grid_filter(self):
        query = self.search_var.get().strip()
        for u in self.units:
            frame, _, _ = self.unit_widgets[u["name"]]
            if self._matches_filter(u, query):
                frame.grid()
            else:
                frame.grid_remove()

    def _toggle(self, name):
        self.history.append(set(self.selected))
        if name in self.selected:
            self.selected.remove(name)
        else:
            if len(self.selected) < self.team_size_var.get():
                self.selected.add(name)
        self._refresh()

    def _get_active_traits(self):
        traits = {}
        for name in self.selected:
            for t in self.units_map[name]["traits"]:
                traits[t] = traits.get(t, 0) + 1
        return dict(sorted(traits.items(), key=lambda x: -x[1]))

    def _get_highest_threshold(self, trait_name, count):
        thresholds = self.trait_thresholds.get(trait_name, [])
        reached = 0
        reached_index = -1
        next_th = None
        for i, th in enumerate(thresholds):
            if count >= th:
                reached = th
                reached_index = i
            elif next_th is None:
                next_th = th
        return reached, next_th, reached_index

    def _refresh_team(self):
        for w in self.team_frame.winfo_children():
            w.destroy()

        team_size = self.team_size_var.get()

        if not self.selected:
            tk.Label(self.team_frame, text="Cliquez sur un champion pour l'ajouter",
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 9)).pack(pady=8)
            return

        row_frame = tk.Frame(self.team_frame, bg="#1d1e20")
        row_frame.pack(pady=4)

        for name in self.selected:
            u = self.units_map[name]
            slot = tk.Frame(row_frame, bg="#1d1e20", padx=2, cursor="hand2")
            slot.pack(side=tk.LEFT, padx=2)

            img = self.team_images.get(name)
            tier_color = TIER_COLORS.get(u["tier"], "#333")
            lbl_img = tk.Label(slot, image=img, bg=tier_color, bd=2, relief=tk.RAISED)
            lbl_img.pack()

            lbl_name = tk.Label(slot, text=name, bg="#1d1e20", fg="white",
                                font=("Segoe UI", 7), wraplength=TEAM_IMG_SIZE + 10)
            lbl_name.pack()

            for w in (slot, lbl_img, lbl_name):
                w.bind("<Button-1>", lambda e, n=name: self._toggle(n))

        empty = team_size - len(self.selected)
        for _ in range(empty):
            slot = tk.Frame(row_frame, bg="#1d1e20", padx=2)
            slot.pack(side=tk.LEFT, padx=2)
            tk.Label(slot, text="", width=TEAM_IMG_SIZE // 8, height=TEAM_IMG_SIZE // 16,
                     bg="#333", bd=2, relief=tk.SUNKEN).pack()
            tk.Label(slot, text="?", bg="#1d1e20", fg="#555",
                     font=("Segoe UI", 7)).pack()

    def _refresh_traits(self):
        for w in self.traits_frame.winfo_children():
            w.destroy()

        active = self._get_active_traits()
        if not active:
            tk.Label(self.traits_frame, text="Aucun trait actif",
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 9)).pack(pady=6)
            return

        for trait_name, count in active.items():
            reached, next_th, reached_index = self._get_highest_threshold(trait_name, count)

            if reached_index < 0:
                color = "#aaa"
            else:
                clamped = min(reached_index, len(TRAIT_TIER_COLORS) - 1)
                color = TRAIT_TIER_COLORS[clamped]

            row = tk.Frame(self.traits_frame, bg="#2a2b2e", pady=2, padx=6)
            row.pack(fill=tk.X, pady=1)

            icon = self.trait_images.get(trait_name)
            if icon:
                tk.Label(row, image=icon, bg="#2a2b2e").pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(row, text=trait_name, bg="#2a2b2e", fg=color,
                     font=("Segoe UI", 9, "bold"), anchor="w").pack(side=tk.LEFT)

            if next_th:
                progress = f"{count}/{next_th}"
            elif reached > 0:
                progress = f"{count} (max)"
            else:
                progress = str(count)
            tk.Label(row, text=progress, bg="#2a2b2e", fg=color,
                     font=("Segoe UI", 8)).pack(side=tk.RIGHT)

    def _refresh(self):
        team_size = self.team_size_var.get()

        while len(self.selected) > team_size:
            self.selected.pop()

        self.selection_count_label.config(
            text=f"{len(self.selected)} / {team_size} selectionnes")

        # Compute recommendations first (needed for grid highlight)
        recs = compute_recommendations(
            self.selected, team_size, self.unlocked,
            self.units, self.trait_thresholds, self._get_weights()
        )
        self.recommended_names = {r[5]["name"] for r in recs}

        # Update normal grid visuals
        for u in self.normal_units:
            frame, lbl_img, lbl_name = self.unit_widgets[u["name"]]
            cost_color = COST_COLORS.get(u["cost"], "#888")
            if u["name"] in self.selected:
                lbl_img.config(bg="#555", relief=tk.SUNKEN, bd=0)
                lbl_name.config(fg="#666")
                frame.config(bg="#555", bd=2, relief=tk.SUNKEN)
            elif u["name"] in self.recommended_names:
                lbl_img.config(bg="#333", relief=tk.FLAT, bd=0)
                lbl_name.config(fg="white")
                frame.config(bg=REC_HIGHLIGHT, bd=2, relief=tk.RIDGE)
            else:
                lbl_img.config(bg="#333", relief=tk.FLAT, bd=0)
                lbl_name.config(fg="white")
                frame.config(bg=cost_color, bd=2, relief=tk.FLAT)

        # Update locked grid visuals
        for u in self.locked_units:
            frame, lbl_img, lbl_name = self.unit_widgets[u["name"]]
            cost_color = COST_COLORS.get(u["cost"], "#888")
            is_unlocked = u["name"] in self.unlocked
            if u["name"] in self.selected:
                lbl_img.config(bg="#555", relief=tk.SUNKEN, bd=0)
                lbl_name.config(fg="#666")
                frame.config(bg="#555", bd=2, relief=tk.SUNKEN)
            elif is_unlocked and u["name"] in self.recommended_names:
                lbl_img.config(bg="#333", relief=tk.FLAT, bd=0)
                lbl_name.config(fg="white")
                frame.config(bg=REC_HIGHLIGHT, bd=2, relief=tk.RIDGE)
            elif is_unlocked:
                lbl_img.config(bg="#333", relief=tk.FLAT, bd=0)
                lbl_name.config(fg="white")
                frame.config(bg=cost_color, bd=2, relief=tk.FLAT)
            else:
                lbl_img.config(bg="#555", relief=tk.FLAT, bd=0)
                lbl_name.config(fg="#444")
                frame.config(bg=cost_color, bd=2, relief=tk.FLAT)

        self._refresh_team()
        self._refresh_traits()

        for w in self.rec_frame.winfo_children():
            w.destroy()

        if not recs:
            msg = "Equipe complete !" if len(self.selected) >= team_size else \
                  "Selectionnez des champions\net ajustez la taille"
            tk.Label(self.rec_frame, text=msg,
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 10)).pack(pady=20)
            return

        for total, tier_score, trait_score, odds, matching, u in recs:
            row = tk.Frame(self.rec_frame, bg="#2a2b2e", pady=4, padx=6, cursor="hand2")
            row.pack(fill=tk.X, pady=2)

            img = self.unit_images.get(u["name"])
            if img:
                tk.Label(row, image=img, bg="#2a2b2e").pack(side=tk.LEFT, padx=(0, 8))

            info = tk.Frame(row, bg="#2a2b2e")
            info.pack(side=tk.LEFT, fill=tk.X, expand=True)

            header = tk.Frame(info, bg="#2a2b2e")
            header.pack(fill=tk.X)

            tk.Label(header, text=u["name"], bg="#2a2b2e", fg="white",
                     font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)

            tier_color = TIER_COLORS.get(u["tier"], "white")
            tk.Label(header, text=f" [{u['tier']}]", bg="#2a2b2e", fg=tier_color,
                     font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

            tk.Label(header, text=f"  {total:.1f}pts", bg="#2a2b2e", fg="#aaa",
                     font=("Segoe UI", 9)).pack(side=tk.LEFT)

            odds_pct = int(odds * 100)
            tk.Label(header, text=f"  {odds_pct}% drop", bg="#2a2b2e",
                     fg="#4caf50" if odds >= 0.20 else "#e8a33c" if odds >= 0.05 else "#ff5555",
                     font=("Segoe UI", 8)).pack(side=tk.LEFT)

            # Score detail line
            detail = f"tier:{tier_score} + traits:{trait_score:.1f}"
            tk.Label(info, text=detail, bg="#2a2b2e", fg="#666",
                     font=("Segoe UI", 7), anchor="w").pack(fill=tk.X)

            # Traits with matching ones highlighted in green
            traits_frame = tk.Frame(info, bg="#2a2b2e")
            traits_frame.pack(fill=tk.X)
            for i, t in enumerate(u["traits"]):
                color = "#4caf50" if t in matching else "#7fbfff"
                text = t if i == 0 else f", {t}"
                tk.Label(traits_frame, text=text, bg="#2a2b2e", fg=color,
                         font=("Segoe UI", 8)).pack(side=tk.LEFT)

            # Click anywhere on the recommendation row to add to team
            def _bind_click(widget, name):
                widget.bind("<Button-1>", lambda _: self._toggle(name))
                for child in widget.winfo_children():
                    _bind_click(child, name)
            _bind_click(row, u["name"])


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1350x750")
    app = TFTFinderApp(root)
    root.mainloop()
