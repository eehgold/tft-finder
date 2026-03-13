import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import sys
from collections import defaultdict

APP_VERSION = "1.2.0"


def _get_base_dir():
    # PyInstaller onefile extracts bundled files into _MEIPASS.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


DATA_DIR = os.path.join(_get_base_dir(), "data")
ICON_DIR = os.path.join(DATA_DIR, "icons")
APP_ICON_ICO = os.path.join(ICON_DIR, "app.ico")
APP_ICON_PNG = os.path.join(ICON_DIR, "logo_tft-finder.png")
IMG_SIZE = 48
TEAM_IMG_SIZE = 56
TRAIT_ICON_SIZE = 20
REC_PICK_ICON_SIZE = 20
ITEM_IMG_SIZE = 42
ITEM_INV_ICON_SIZE = 24
TEAM_ITEM_ICON_SIZE = 18
GRID_COLS = 10
LOCKED_GRID_COLS = 8
ITEM_GRID_COLS = 6
MAX_ITEMS_PER_UNIT = 3
TIER_SCORES = {"S": 10, "A": 7, "B": 5, "C": 3, "D": 1}
TIER_COLORS = {"S": "#ff7f7f", "A": "#ffbf7f", "B": "#ffdf7f", "C": "#7fbfff", "D": "#aaaaaa"}
# Trait threshold tier colors: bronze, silver, gold, prismatic
TRAIT_TIER_COLORS = ["#cd7f32", "#ffffff", "#ffd700", "#e45fff"]
RANK_BADGE_COLORS = {"S": "#ff7f7f", "A": "#ffbf7f", "B": "#ffdf7f", "C": "#7fbfff", "D": "#aaaaaa", "?": "#888888"}
ITEM_NATURE_ORDER = {"component": 0, "normal": 1, "radiant": 2, "artifact": 3, "emblem": 4, "trait": 5}
ITEM_RANK_FALLBACK = {
    "radiant": 8.0,
    "artifact": 6.0,
    "emblem": 5.0,
    "trait": 3.0,
    "normal": 4.0,
    "component": 0.0,
}
# Cost border colors (like in-game): 1g gray, 2g green, 3g blue, 4g purple, 5g+ gold
COST_COLORS = {1: "#888888", 2: "#11b288", 3: "#207ac7", 4: "#c440da", 5: "#ffb93b",
               6: "#ffb93b", 7: "#ffb93b"}
# Recommended champion highlight color
REC_HIGHLIGHT = "#e8a33c"
TRAIT_QUALITY_SCORES = {"D": 1.0, "C": 3.0, "B": 5.0, "A": 8.0, "S": 12.0}
DEFAULT_TRAIT_QUALITY_ORDER = ["D", "C", "B", "A", "S"]

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
    trait_tiers = {}
    for t in traits_raw:
        trait_thresholds.setdefault(t["name"], []).append(t["count"])
        if t["name"] not in trait_icons:
            trait_icons[t["name"]] = t.get("image")
        tier_letter = (t.get("tier") or "").strip().upper()
        if tier_letter:
            trait_tiers.setdefault(t["name"], {})[t["count"]] = tier_letter
    for k in trait_thresholds:
        trait_thresholds[k] = sorted(set(trait_thresholds[k]))
    return units, trait_thresholds, trait_icons, trait_tiers


def load_items_data():
    with open(os.path.join(DATA_DIR, "items.json"), encoding="utf-8") as f:
        items = json.load(f)
    with open(os.path.join(DATA_DIR, "components.json"), encoding="utf-8") as f:
        components_payload = json.load(f)

    items_map = {item["slug"]: item for item in items}
    component_order = [c["slug"] for c in components_payload.get("components", [])]
    component_matrix = components_payload.get("matrix", {})
    return items, items_map, component_order, component_matrix


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


def _trait_uses_explicit_quality(trait_name, trait_tiers, thresholds):
    tier_map = (trait_tiers or {}).get(trait_name, {})
    labels = [tier_map.get(th) for th in thresholds if tier_map.get(th) in TRAIT_QUALITY_SCORES]
    unique_labels = set(labels)
    if len(thresholds) <= 1:
        return bool(unique_labels)
    return len(unique_labels) > 1


def _trait_quality_letter(trait_name, reached_value, reached_index, thresholds, trait_tiers):
    if reached_index < 0 or reached_value <= 0:
        return None
    tier_map = (trait_tiers or {}).get(trait_name, {})
    if _trait_uses_explicit_quality(trait_name, trait_tiers, thresholds):
        letter = tier_map.get(reached_value)
        if letter in TRAIT_QUALITY_SCORES:
            return letter
    return DEFAULT_TRAIT_QUALITY_ORDER[min(reached_index, len(DEFAULT_TRAIT_QUALITY_ORDER) - 1)]


def _trait_quality_value(trait_name, count, thresholds, trait_tiers):
    reached_index, reached_value, _ = _get_trait_tier_state(count, thresholds)
    letter = _trait_quality_letter(trait_name, reached_value, reached_index, thresholds, trait_tiers)
    if not letter:
        return 0.0, None, reached_value, reached_index
    return TRAIT_QUALITY_SCORES.get(letter, 0.0), letter, reached_value, reached_index


DEFAULT_WEIGHTS = {
    "tier": 1.0,
    "traits": 1.0,
    "cap_potential": 0.8,
    "odds": 1.0,
    "multi_synergy": 1.0,
}
SCENARIO_SORT_MODES = [
    ("score", "Score max"),
    ("roll", "Facile a roll"),
    ("eco", "Economie"),
    ("spike", "Power spike rapide"),
]


def compute_trait_score(candidate, selected_units, all_units_map, trait_thresholds,
                        trait_tiers=None, unlocked_names=None, all_units=None,
                        weights=None, team_size=None):
    """Score based on trait synergy with tier quality and cap potential.

    Returns (total_trait_score, matching_traits set, trait_details list).
    """
    w = weights or DEFAULT_WEIGHTS
    quality_w = w.get("traits", 1.0)
    cap_w = w.get("cap_potential", 0.8)
    multi_w = w.get("multi_synergy", 1.0)

    selected_traits = {}
    for name in selected_units:
        for t in all_units_map[name]["traits"]:
            selected_traits[t] = selected_traits.get(t, 0) + 1

    score = 0
    matching = set()
    details = []
    used_after_pick = set(selected_units)
    used_after_pick.add(candidate["name"])
    slots_left_after_pick = None
    if team_size is not None:
        slots_left_after_pick = max(0, team_size - len(used_after_pick))

    for t in candidate["traits"]:
        current = selected_traits.get(t, 0)
        new = current + 1
        thresholds = trait_thresholds.get(t, [])

        if current > 0:
            matching.add(t)

        current_quality, current_letter, current_reached, current_idx = _trait_quality_value(
            t, current, thresholds, trait_tiers
        )
        new_quality, new_letter, new_reached, new_idx = _trait_quality_value(
            t, new, thresholds, trait_tiers
        )
        immediate_gain = max(0.0, new_quality - current_quality)
        score += immediate_gain * quality_w

        # Minor progress bonus even when threshold not crossed.
        next_th = None
        for th in thresholds:
            if th > new:
                next_th = th
                break
        if current > 0 and next_th:
            progress = new / next_th
            score += progress * 0.6 * quality_w

        potential_count = new
        potential_quality = new_quality
        potential_letter = new_letter
        potential_reached = new_reached
        future_gain = 0.0
        max_possible_count = new
        if all_units is not None and unlocked_names is not None and slots_left_after_pick is not None:
            available_after_pick = _count_available_for_trait(
                t, used_after_pick, unlocked_names, all_units)
            max_extra = min(available_after_pick, slots_left_after_pick)
            max_possible_count = new + max_extra
            potential_count = max_possible_count
            potential_quality, potential_letter, potential_reached, _ = _trait_quality_value(
                t, potential_count, thresholds, trait_tiers
            )
            future_gain = max(0.0, potential_quality - new_quality)
            if future_gain > 0:
                # Discount very long-term potential by how far it is from current state.
                distance = max(1, potential_count - new)
                score += (future_gain / distance) * cap_w

            # If next threshold is impossible in remaining slots, downweight this trait.
            if next_th and max_possible_count < next_th:
                score -= 0.8 * quality_w

        details.append({
            "trait": t,
            "delta_count": 1,
            "current_count": current,
            "new_count": new,
            "current_reached": current_reached,
            "new_reached": new_reached,
            "current_tier_letter": current_letter,
            "new_tier_letter": new_letter,
            "potential_count": potential_count,
            "potential_reached": potential_reached,
            "potential_tier_letter": potential_letter,
            "quality_gain": immediate_gain,
            "future_gain": future_gain,
            "max_possible_count": max_possible_count,
        })

    # Multi-synergy bonus
    if len(matching) >= 2:
        score += len(matching) * 2 * multi_w

    return score, matching, details


def get_roll_odds(level, cost):
    """Get the probability of rolling a unit of given cost at given level."""
    odds = ROLL_ODDS.get(level, ROLL_ODDS[11])
    lookup_cost = min(cost, 5)
    return odds.get(lookup_cost, 0.0)


def _compute_team_traits(team_names, all_units_map):
    traits = {}
    for name in team_names:
        for trait_name in all_units_map[name]["traits"]:
            traits[trait_name] = traits.get(trait_name, 0) + 1
    return traits


def _get_trait_tier_state(count, thresholds):
    reached_tier = -1
    reached_value = 0
    next_value = None
    for i, threshold in enumerate(thresholds):
        if count >= threshold:
            reached_tier = i
            reached_value = threshold
        elif next_value is None:
            next_value = threshold
    return reached_tier, reached_value, next_value


def _get_active_trait_entries(trait_counts, trait_thresholds, trait_tiers=None):
    active = []
    for trait_name, count in trait_counts.items():
        thresholds = trait_thresholds.get(trait_name, [])
        tier_idx, reached_value, _ = _get_trait_tier_state(count, thresholds)
        _, tier_letter, _, _ = _trait_quality_value(trait_name, count, thresholds, trait_tiers)
        if tier_idx >= 0:
            active.append({
                "name": trait_name,
                "count": count,
                "tier_idx": tier_idx,
                "reached": reached_value,
                "tier_letter": tier_letter,
            })
    active.sort(key=lambda x: (-x["tier_idx"], -x["count"], x["name"]))
    return active


def _get_trait_upgrades(before_counts, after_counts, trait_thresholds, trait_tiers=None):
    upgrades = []
    for trait_name, after_count in after_counts.items():
        thresholds = trait_thresholds.get(trait_name, [])
        before_tier, _, _ = _get_trait_tier_state(before_counts.get(trait_name, 0), thresholds)
        after_tier, reached_value, _ = _get_trait_tier_state(after_count, thresholds)
        _, before_tier_letter, _, _ = _trait_quality_value(
            trait_name, before_counts.get(trait_name, 0), thresholds, trait_tiers
        )
        _, after_tier_letter, _, _ = _trait_quality_value(
            trait_name, after_count, thresholds, trait_tiers
        )
        if after_tier > before_tier and after_tier >= 0:
            upgrades.append({
                "name": trait_name,
                "count": after_count,
                "tier_idx": after_tier,
                "reached": reached_value,
                "before_tier_letter": before_tier_letter,
                "after_tier_letter": after_tier_letter,
            })
    upgrades.sort(key=lambda x: (-x["tier_idx"], -x["count"], x["name"]))
    return upgrades


def _analyze_trait_deltas(before_counts, after_counts, trait_thresholds, trait_tiers=None):
    deltas = []
    for trait_name in sorted(set(before_counts) | set(after_counts)):
        before_count = before_counts.get(trait_name, 0)
        after_count = after_counts.get(trait_name, 0)
        thresholds = trait_thresholds.get(trait_name, [])
        before_tier, before_reached, _ = _get_trait_tier_state(before_count, thresholds)
        after_tier, after_reached, _ = _get_trait_tier_state(after_count, thresholds)
        _, before_tier_letter, _, _ = _trait_quality_value(
            trait_name, before_count, thresholds, trait_tiers
        )
        _, after_tier_letter, _, _ = _trait_quality_value(
            trait_name, after_count, thresholds, trait_tiers
        )
        if before_tier < 0 and after_tier < 0:
            continue
        deltas.append({
            "name": trait_name,
            "before_count": before_count,
            "after_count": after_count,
            "before_tier": before_tier,
            "after_tier": after_tier,
            "before_reached": before_reached,
            "after_reached": after_reached,
            "before_tier_letter": before_tier_letter,
            "after_tier_letter": after_tier_letter,
        })

    upgrades = [d for d in deltas if d["after_tier"] > d["before_tier"]]
    stable = [d for d in deltas if d["before_tier"] >= 0 and d["after_tier"] == d["before_tier"]]
    new_active = [d for d in deltas if d["before_tier"] < 0 <= d["after_tier"]]

    upgrades.sort(key=lambda x: (-x["after_tier"], -(x["after_count"] - x["before_count"]), x["name"]))
    stable.sort(key=lambda x: (-x["after_count"], x["name"]))
    new_active.sort(key=lambda x: (-x["after_tier"], -x["after_count"], x["name"]))
    return deltas, upgrades, stable, new_active


def _short_list(items, limit=3):
    if len(items) <= limit:
        return ", ".join(items)
    return ", ".join(items[:limit]) + f" +{len(items) - limit}"


def _build_scenario_reason(picks, trait_upgrades, stable_traits, cap_opportunities):
    reasons = []

    if trait_upgrades:
        labels = [f"{t['name']} ({t['after_tier_letter'] or '?'} @ {t['after_reached']})" for t in trait_upgrades]
        reasons.append(f"Active ou ameliore: {_short_list(labels)}")

    if cap_opportunities:
        labels = [f"{c['trait']} -> {c['potential_tier_letter']} (cap {c['potential_count']})" for c in cap_opportunities[:3]]
        reasons.append(f"Potentiel cap max: {_short_list(labels)}")

    shared_traits = sorted({trait for p in picks for trait in p["matching"]})
    if shared_traits:
        reasons.append(f"Renforce des synergies deja presentes: {_short_list(shared_traits)}")

    avg_odds = sum(p["odds"] for p in picks) / max(1, len(picks))
    if avg_odds >= 0.20:
        reasons.append(f"Plan facile a roll ({int(avg_odds * 100)}% moyen)")
    elif avg_odds >= 0.08:
        reasons.append(f"Plan jouable en roll ({int(avg_odds * 100)}% moyen)")
    else:
        reasons.append(f"Plan plus greedy ({int(avg_odds * 100)}% moyen)")

    if stable_traits:
        labels = [f"{t['name']} ({t['after_count']})" for t in stable_traits[:3]]
        reasons.append(f"Garde stables: {', '.join(labels)}")

    return "\n".join(f"- {reason}" for reason in reasons)


def _build_reason_tooltip(picks, trait_upgrades, stable_traits, cap_opportunities,
                          score, avg_odds, avg_cost, spike_score):
    lines = [
        f"Total scenario: {score:.2f}",
        f"Avg odds: {avg_odds * 100:.1f}%",
        f"Avg cost: {avg_cost:.2f}",
        f"Spike score: {spike_score:.2f}",
        "",
        "Details per unit:",
    ]
    for pick in picks:
        lines.append(
            f"- {pick['name']}: total={pick['score']:.2f} "
            f"(tier={pick['tier_score']:.2f}, traits={pick['trait_score']:.2f}, odds={pick['odds'] * 100:.1f}%)"
        )
        for detail in pick.get("trait_details", []):
            if detail["quality_gain"] <= 0 and detail["future_gain"] <= 0:
                continue
            curr = detail["current_tier_letter"] or "-"
            new = detail["new_tier_letter"] or "-"
            pot = detail["potential_tier_letter"] or new
            lines.append(
                f"  {detail['trait']}: +{detail['delta_count']} ({curr} -> {new}), "
                f"gain={detail['quality_gain']:.2f}, cap={pot}, future={detail['future_gain']:.2f}"
            )

    if trait_upgrades:
        lines.append("")
        lines.append("Trait upgrades:")
        for delta in trait_upgrades[:6]:
            lines.append(
                f"- {delta['name']}: {delta['before_tier_letter'] or '-'} -> {delta['after_tier_letter'] or '-'}, "
                f"count {delta['before_count']} -> {delta['after_count']}"
            )
    if cap_opportunities:
        lines.append("")
        lines.append("Cap opportunities:")
        for cap in cap_opportunities[:5]:
            lines.append(
                f"- {cap['trait']}: now {cap['new_tier_letter'] or '-'} "
                f"-> potential {cap['potential_tier_letter'] or '-'} (future gain {cap['future_gain']:.2f})"
            )
    if stable_traits:
        lines.append("")
        lines.append("Stable traits:")
        for delta in stable_traits[:5]:
            lines.append(
                f"- {delta['name']}: tier {delta['after_tier_letter'] or '-'}, "
                f"count {delta['before_count']} -> {delta['after_count']}"
            )
    return "\n".join(lines)


def summarize_trait_entries(entries, limit=6):
    if not entries:
        return "none"
    labels = [f"{e['name']} {e['count']}" for e in entries[:limit]]
    if len(entries) > limit:
        labels.append(f"+{len(entries) - limit}")
    return ", ".join(labels)


def compute_recommendation_scenarios(selected_names, team_size, unlocked_names, units,
                                     trait_thresholds, trait_tiers=None, weights=None, top_n=3,
                                     diversity=0.5, sort_mode="score"):
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
        trait_score, matching, trait_details = compute_trait_score(
            u, team, all_units_map, trait_thresholds, trait_tiers, unlocked_names, units, w, team_size
        )
        raw_score = tier_score + trait_score
        # odds_w controls how much drop rate matters: 0=ignore odds, 1=full weight
        total = raw_score * (odds ** odds_w) if odds_w > 0 else raw_score
        return (total, tier_score, trait_score, odds, matching, trait_details, u)

    def _to_pick(entry):
        total, tier_score, trait_score, odds, matching, trait_details, unit = entry
        quality_gain = sum(d["quality_gain"] for d in trait_details)
        future_gain = sum(d["future_gain"] for d in trait_details)
        return {
            "name": unit["name"],
            "unit": unit,
            "score": total,
            "tier_score": tier_score,
            "trait_score": trait_score,
            "quality_gain": quality_gain,
            "future_gain": future_gain,
            "odds": odds,
            "matching": sorted(matching),
            "trait_details": trait_details,
        }

    available_units = []
    first_pass_scores = []
    for u in units:
        if u["name"] in selected_names:
            continue
        if u["locked"] and u["name"] not in unlocked_names:
            continue
        available_units.append(u)
        entry = _score_unit(u, selected_names)
        if entry:
            first_pass_scores.append(entry)

    if not available_units or not first_pass_scores:
        return []

    before_traits = _compute_team_traits(selected_names, all_units_map)

    def _build_scenario(seed_name=None):
        used = set(selected_names)
        picks = []

        if seed_name is not None:
            seed_unit = all_units_map[seed_name]
            seed_entry = _score_unit(seed_unit, used)
            if not seed_entry:
                return None
            picks.append(_to_pick(seed_entry))
            used.add(seed_name)

        while len(picks) < slots:
            best_entry = None
            for u in available_units:
                if u["name"] in used:
                    continue
                entry = _score_unit(u, used)
                if entry and (best_entry is None or entry[0] > best_entry[0]):
                    best_entry = entry
            if best_entry is None:
                break
            pick = _to_pick(best_entry)
            picks.append(pick)
            used.add(pick["name"])

        if not picks:
            return None

        after_traits = _compute_team_traits(used, all_units_map)
        trait_deltas, trait_upgrades, stable_traits, new_active_traits = _analyze_trait_deltas(
            before_traits, after_traits, trait_thresholds, trait_tiers
        )
        active_traits = _get_active_trait_entries(after_traits, trait_thresholds, trait_tiers)
        total_score = sum(p["score"] for p in picks)
        avg_odds = sum(p["odds"] for p in picks) / len(picks)
        total_cost = sum(p["unit"]["cost"] for p in picks)
        avg_cost = total_cost / len(picks)
        total_quality_gain = sum(p["quality_gain"] for p in picks)
        total_future_gain = sum(p["future_gain"] for p in picks)
        spike_score = 0.0
        for delta in trait_deltas:
            if delta["after_tier"] > delta["before_tier"]:
                jump = delta["after_tier"] - delta["before_tier"]
                spike_score += jump * (delta["after_tier"] + 1)
            elif delta["before_tier"] >= 0 and delta["after_count"] > delta["before_count"]:
                spike_score += 0.3
        cap_map = {}
        for pick in picks:
            for detail in pick["trait_details"]:
                if detail["future_gain"] <= 0:
                    continue
                current = cap_map.get(detail["trait"])
                if current is None or detail["future_gain"] > current["future_gain"]:
                    cap_map[detail["trait"]] = detail
        cap_opportunities = sorted(
            cap_map.values(),
            key=lambda d: (-d["future_gain"], -d["potential_count"], d["trait"])
        )
        pick_names = [p["name"] for p in picks]
        reason = _build_scenario_reason(picks, trait_upgrades, stable_traits, cap_opportunities)

        return {
            "score": total_score,
            "avg_odds": avg_odds,
            "avg_cost": avg_cost,
            "total_cost": total_cost,
            "quality_gain": total_quality_gain,
            "future_gain": total_future_gain,
            "spike_score": spike_score,
            "pick_names": pick_names,
            "pick_set": set(pick_names),
            "picks": picks,
            "trait_deltas": trait_deltas,
            "active_traits": active_traits,
            "trait_upgrades": trait_upgrades,
            "stable_traits": stable_traits,
            "new_active_traits": new_active_traits,
            "cap_opportunities": cap_opportunities,
            "reason": reason,
            "reason_tooltip": _build_reason_tooltip(
                picks, trait_upgrades, stable_traits, cap_opportunities,
                total_score, avg_odds, avg_cost, spike_score
            ),
        }

    first_pass_scores.sort(key=lambda x: -x[0])
    seed_count = min(len(first_pass_scores), max(12, top_n * 6))
    seed_names = [None] + [entry[6]["name"] for entry in first_pass_scores[:seed_count]]

    scenarios = []
    for seed_name in seed_names:
        scenario = _build_scenario(seed_name)
        if scenario:
            scenarios.append(scenario)

    deduped = {}
    for scenario in scenarios:
        key = tuple(sorted(scenario["pick_names"]))
        current = deduped.get(key)
        if current is None or scenario["score"] > current["score"]:
            deduped[key] = scenario

    unique_scenarios = list(deduped.values())
    if not unique_scenarios:
        return []

    def _style_value(scenario):
        if sort_mode == "roll":
            return scenario["avg_odds"] * 100 + scenario["future_gain"] * 0.8 + scenario["score"] * 0.04
        if sort_mode == "eco":
            return (6.0 - scenario["avg_cost"]) * 8 + scenario["avg_odds"] * 20 + scenario["score"] * 0.03
        if sort_mode == "spike":
            return (
                scenario["spike_score"] * 10
                + scenario["quality_gain"] * 1.5
                + scenario["future_gain"] * 1.2
                + len(scenario["trait_upgrades"]) * 2
                + scenario["score"] * 0.03
            )
        return (
            scenario["score"]
            + scenario["quality_gain"] * 1.3
            + scenario["future_gain"] * 0.9
            + len(scenario["trait_upgrades"]) * 1.2
            + scenario["avg_odds"] * 5
        )

    for scenario in unique_scenarios:
        scenario["style_value"] = _style_value(scenario)

    values = [s["style_value"] for s in unique_scenarios]
    value_span = max(values) - min(values)
    penalty_scale = value_span if value_span > 0 else max(1.0, abs(max(values)))

    def _overlap_ratio(a, b):
        inter = len(a["pick_set"] & b["pick_set"])
        union = len(a["pick_set"] | b["pick_set"])
        return inter / union if union else 0.0

    remaining = sorted(unique_scenarios, key=lambda s: (-s["style_value"], -s["score"]))
    selected = []
    diversity = max(0.0, min(1.0, diversity))

    while remaining and len(selected) < top_n:
        best = None
        best_adjusted = None
        for scenario in remaining:
            if not selected:
                adjusted = scenario["style_value"]
            else:
                overlap = max(_overlap_ratio(scenario, chosen) for chosen in selected)
                adjusted = scenario["style_value"] - (diversity * overlap * penalty_scale)
            if best is None or adjusted > best_adjusted:
                best = scenario
                best_adjusted = adjusted
        best["style_rank_value"] = best_adjusted
        selected.append(best)
        remaining.remove(best)

    selected.sort(key=lambda s: (-s.get("style_rank_value", s["style_value"]), -s["score"]))
    return selected[:top_n]


def compute_recommendations(selected_names, team_size, unlocked_names, units,
                            trait_thresholds, trait_tiers=None, weights=None):
    """Backward-compatible wrapper kept for older UI paths."""
    scenarios = compute_recommendation_scenarios(
        selected_names, team_size, unlocked_names, units, trait_thresholds, trait_tiers, weights, top_n=1)
    if not scenarios:
        return []
    recs = []
    for pick in scenarios[0]["picks"]:
        u = pick["unit"]
        recs.append((
            pick["score"],
            pick["tier_score"],
            pick["trait_score"],
            pick["odds"],
            set(pick["matching"]),
            u,
        ))
    return recs


class TFTFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"TFT Finder - Season 16 - v{APP_VERSION}")
        self.root.configure(bg="#1d1e20")

        self.units, self.trait_thresholds, self.trait_icon_paths, self.trait_tiers = load_data()
        self.items, self.items_map, self.component_slugs, self.component_matrix = load_items_data()
        self.units_map = {u["name"]: u for u in self.units}
        self.normal_units = [u for u in self.units if not u["locked"]]
        self.locked_units = [u for u in self.units if u["locked"]]
        self.selected = set()
        self.inventory_counts = {}
        self.equipped_items = {}
        self.item_action_message = ""
        self.unlocked = set()
        self.unlock_vars = {}
        self.unit_images = {}
        self.team_images = {}
        self.rec_pick_images = {}
        self.trait_images = {}
        self.unit_widgets = {}
        self.item_images = {}
        self.item_inv_images = {}
        self.team_item_images = {}
        self.item_widgets = {}
        self.recommended_names = set()
        self.history = []  # undo history: list of previous selected sets
        self.sort_mode = "default"  # default, cost, tier
        self.config_visible = False

        # Scoring weight variables (DoubleVar created after root exists)
        self.w_tier = tk.DoubleVar(value=1.0)
        self.w_traits = tk.DoubleVar(value=1.0)
        self.w_cap = tk.DoubleVar(value=0.8)
        self.w_odds = tk.DoubleVar(value=1.0)
        self.w_multi = tk.DoubleVar(value=1.0)
        self.scenario_diversity = tk.DoubleVar(value=0.5)
        self.scenario_sort_mode = "score"
        self.scenario_sort_buttons = {}
        self.tooltip_window = None
        self.tooltip_label = None
        self.app_icon_image = None

        self._set_app_icon()
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
                self.rec_pick_images[u["name"]] = ImageTk.PhotoImage(
                    img.resize((REC_PICK_ICON_SIZE, REC_PICK_ICON_SIZE), Image.LANCZOS))
        for trait_name, img_path in self.trait_icon_paths.items():
            if img_path:
                full = os.path.join(DATA_DIR, img_path)
                if os.path.exists(full):
                    img = Image.open(full).resize((TRAIT_ICON_SIZE, TRAIT_ICON_SIZE), Image.LANCZOS)
                    self.trait_images[trait_name] = ImageTk.PhotoImage(img)
        for item in self.items:
            icon_path = item.get("icon")
            if not icon_path:
                continue
            full_icon = os.path.join(DATA_DIR, icon_path)
            if not os.path.exists(full_icon):
                continue
            try:
                src = Image.open(full_icon)
                self.item_images[item["slug"]] = ImageTk.PhotoImage(
                    src.resize((ITEM_IMG_SIZE, ITEM_IMG_SIZE), Image.LANCZOS)
                )
                self.item_inv_images[item["slug"]] = ImageTk.PhotoImage(
                    src.resize((ITEM_INV_ICON_SIZE, ITEM_INV_ICON_SIZE), Image.LANCZOS)
                )
                self.team_item_images[item["slug"]] = ImageTk.PhotoImage(
                    src.resize((TEAM_ITEM_ICON_SIZE, TEAM_ITEM_ICON_SIZE), Image.LANCZOS)
                )
            except Exception:
                continue

    def _set_app_icon(self):
        if os.name == "nt" and os.path.exists(APP_ICON_ICO):
            try:
                self.root.iconbitmap(APP_ICON_ICO)
            except tk.TclError:
                pass
        if os.path.exists(APP_ICON_PNG):
            try:
                icon_img = Image.open(APP_ICON_PNG).resize((32, 32), Image.LANCZOS)
                self.app_icon_image = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, self.app_icon_image)
            except Exception:
                self.app_icon_image = None

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg="#2a2b2e", pady=8, padx=12)
        top.pack(fill=tk.X)

        tk.Label(top, text="Team size:", bg="#2a2b2e", fg="white",
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

        self.version_label = tk.Label(top, text=f"v{APP_VERSION}", bg="#2a2b2e", fg="#7f8fa4",
                                      font=("Segoe UI", 9, "bold"))
        self.version_label.pack(side=tk.RIGHT, padx=(0, 10))

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
        tk.Label(cfg_title, text="Scoring weights", bg="#333", fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(cfg_title, text="Reset config", bg="#555", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
                  command=self._reset_config).pack(side=tk.RIGHT)

        sliders_frame = tk.Frame(self.config_frame, bg="#333")
        sliders_frame.pack(fill=tk.X)

        slider_defs = [
            ("Tier", self.w_tier, "Raw power (S > A > B...)"),
            ("Trait quality", self.w_traits, "Immediate value from trait tier gains"),
            ("Cap potential", self.w_cap, "Future value from reachable high tiers"),
            ("Odds", self.w_odds, "Probability to find the unit"),
            ("Multi-synergy", self.w_multi, "Bonus if 2+ traits match"),
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
            ("Balanced", {"tier": 1.0, "traits": 1.0, "cap_potential": 0.8, "odds": 1.0, "multi_synergy": 1.0}),
            ("Max synergy", {"tier": 0.3, "traits": 2.0, "cap_potential": 1.4, "odds": 0.5, "multi_synergy": 2.0}),
            ("Brute force", {"tier": 2.0, "traits": 0.5, "cap_potential": 0.2, "odds": 1.0, "multi_synergy": 0.3}),
            ("Ignore odds", {"tier": 1.0, "traits": 1.0, "cap_potential": 0.8, "odds": 0.0, "multi_synergy": 1.0}),
        ]
        for name, values in presets:
            tk.Button(presets_frame, text=name, bg="#555", fg="white",
                      font=("Segoe UI", 8), relief=tk.FLAT, padx=8, pady=2,
                      command=lambda v=values: self._apply_preset(v)
                      ).pack(side=tk.LEFT, padx=2)

        scenario_cfg = tk.Frame(self.config_frame, bg="#333")
        scenario_cfg.pack(fill=tk.X, pady=(8, 0))
        tk.Label(scenario_cfg, text="Scenario diversity", bg="#333", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        tk.Scale(
            scenario_cfg,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.scenario_diversity,
            bg="#333",
            fg="white",
            highlightthickness=0,
            troughcolor="#555",
            length=130,
            command=lambda _: self._refresh(),
        ).pack(side=tk.LEFT)

        scenario_sort_frame = tk.Frame(self.config_frame, bg="#333")
        scenario_sort_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(scenario_sort_frame, text="Scenario style:", bg="#333", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        for mode, label in SCENARIO_SORT_MODES:
            btn = tk.Button(
                scenario_sort_frame,
                text=label,
                bg="#444",
                fg="white",
                font=("Segoe UI", 8),
                relief=tk.FLAT,
                padx=6,
                pady=1,
                command=lambda m=mode: self._set_scenario_sort(m),
            )
            btn.pack(side=tk.LEFT, padx=1)
            self.scenario_sort_buttons[mode] = btn
        self._update_scenario_sort_buttons()

        # Search bar + sort buttons
        search_bar = tk.Frame(self.root, bg="#2a2b2e", pady=6, padx=12)
        search_bar.pack(fill=tk.X)

        tk.Label(search_bar, text="Search:", bg="#2a2b2e", fg="white",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_grid_filter())
        search_entry = tk.Entry(search_bar, textvariable=self.search_var, bg="#444", fg="white",
                                insertbackground="white", font=("Segoe UI", 10), width=25,
                                relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, padx=(8, 12))

        tk.Label(search_bar, text="name, cost (ex: 3) or trait", bg="#2a2b2e", fg="#888",
                 font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT)

        # Sort buttons
        sort_frame = tk.Frame(search_bar, bg="#2a2b2e")
        sort_frame.pack(side=tk.RIGHT)

        tk.Label(sort_frame, text="Sort:", bg="#2a2b2e", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))

        self.sort_buttons = {}
        for mode, label in [("default", "Default"), ("cost", "Cost"), ("tier", "Tier")]:
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

        tk.Label(locked_header, text="Locked champions", bg="#1d1e20", fg="#e8a33c",
                 font=("Segoe UI", 12, "bold"), pady=4).pack(side=tk.LEFT)

        btn_frame = tk.Frame(locked_header, bg="#1d1e20")
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text="Unlock all", bg="#444", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2,
                  command=self._unlock_all).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Lock all", bg="#444", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2,
                  command=self._lock_all).pack(side=tk.LEFT, padx=2)

        self.locked_grid_frame = tk.Frame(self.left_scroll_frame, bg="#1d1e20")
        self.locked_grid_frame.pack(fill=tk.X, padx=4, pady=4)

        self._build_locked_grid()

        # Right panel: team + tabs (unit optimization / item optimization)
        right_panel = tk.Frame(main, bg="#1d1e20", width=620)
        main.add(right_panel, stretch="never")

        # -- Mon equipe --
        team_section = tk.LabelFrame(right_panel, text="My team", bg="#1d1e20", fg="white",
                                      font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                      labelanchor="n", padx=4, pady=4)
        team_section.pack(fill=tk.X, padx=4, pady=(4, 2))

        self.team_frame = tk.Frame(team_section, bg="#1d1e20")
        self.team_frame.pack(fill=tk.X)

        self.tabs = ttk.Notebook(right_panel)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))

        unit_tab = tk.Frame(self.tabs, bg="#1d1e20")
        item_tab = tk.Frame(self.tabs, bg="#1d1e20")
        self.tabs.add(unit_tab, text="Opti unites")
        self.tabs.add(item_tab, text="Opti items")

        # -- Unit tab: traits + recommendations --
        traits_section = tk.LabelFrame(unit_tab, text="Active traits", bg="#1d1e20", fg="white",
                                       font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                       labelanchor="n", padx=4, pady=4)
        traits_section.pack(fill=tk.X, padx=0, pady=0)

        self.traits_frame = tk.Frame(traits_section, bg="#1d1e20")
        self.traits_frame.pack(fill=tk.X)

        rec_section = tk.LabelFrame(unit_tab, text="Top 3 scenarios", bg="#1d1e20", fg="white",
                                    font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                    labelanchor="n", padx=4, pady=4)
        rec_section.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        rec_container = tk.Frame(rec_section, bg="#1d1e20")
        rec_container.pack(fill=tk.BOTH, expand=True)

        rec_canvas = tk.Canvas(rec_container, bg="#1d1e20", highlightthickness=0, width=590)
        rec_scrollbar = ttk.Scrollbar(rec_container, orient=tk.VERTICAL, command=rec_canvas.yview)
        self.rec_frame = tk.Frame(rec_canvas, bg="#1d1e20")

        self.rec_frame.bind("<Configure>",
                            lambda e: rec_canvas.configure(scrollregion=rec_canvas.bbox("all")))
        rec_canvas.create_window((0, 0), window=self.rec_frame, anchor="nw")
        rec_canvas.configure(yscrollcommand=rec_scrollbar.set)

        rec_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rec_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # -- Item tab --
        self._build_items_tab(item_tab)

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

    def _build_items_tab(self, parent):
        filters = tk.Frame(parent, bg="#1d1e20", pady=4)
        filters.pack(fill=tk.X)

        tk.Label(filters, text="Search item:", bg="#1d1e20", fg="white",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.item_search_var = tk.StringVar()
        self.item_search_var.trace_add("write", lambda *_: self._refresh_item_grid_filter())
        tk.Entry(filters, textvariable=self.item_search_var, bg="#333", fg="white",
                 insertbackground="white", relief=tk.FLAT, width=18,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(6, 10))

        tk.Label(filters, text="Category:", bg="#1d1e20", fg="#ccc",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.item_nature_var = tk.StringVar(value="all")
        nature_values = ["all", "component", "normal", "radiant", "artifact", "emblem", "trait"]
        nature_box = ttk.Combobox(filters, state="readonly", width=10,
                                  textvariable=self.item_nature_var, values=nature_values)
        nature_box.pack(side=tk.LEFT, padx=(6, 10))
        nature_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_item_grid_filter())

        tk.Label(filters, text="Rank:", bg="#1d1e20", fg="#ccc",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.item_rank_var = tk.StringVar(value="all")
        rank_box = ttk.Combobox(filters, state="readonly", width=9,
                                textvariable=self.item_rank_var,
                                values=["all", "S", "A", "B", "C", "D", "unranked"])
        rank_box.pack(side=tk.LEFT, padx=(6, 10))
        rank_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_item_grid_filter())

        tk.Button(filters, text="Reset items", bg="#444", fg="white",
                  relief=tk.FLAT, padx=8, pady=1,
                  command=self._reset_inventory).pack(side=tk.RIGHT)
        tk.Label(filters, text="Left click = +1, right click = -1",
                 bg="#1d1e20", fg="#777", font=("Segoe UI", 8, "italic")).pack(side=tk.RIGHT, padx=(0, 10))

        tab_main = tk.PanedWindow(parent, orient=tk.HORIZONTAL, bg="#1d1e20",
                                  sashwidth=3, sashrelief=tk.FLAT)
        tab_main.pack(fill=tk.BOTH, expand=True)

        selector = tk.Frame(tab_main, bg="#1d1e20")
        insights = tk.Frame(tab_main, bg="#1d1e20", width=290)
        tab_main.add(selector, stretch="always")
        tab_main.add(insights, stretch="never")

        selector_canvas = tk.Canvas(selector, bg="#1d1e20", highlightthickness=0)
        selector_scroll = ttk.Scrollbar(selector, orient=tk.VERTICAL, command=selector_canvas.yview)
        self.item_grid_frame = tk.Frame(selector_canvas, bg="#1d1e20")

        self.item_grid_frame.bind(
            "<Configure>", lambda e: selector_canvas.configure(scrollregion=selector_canvas.bbox("all"))
        )
        selector_canvas.create_window((0, 0), window=self.item_grid_frame, anchor="nw")
        selector_canvas.configure(yscrollcommand=selector_scroll.set)
        selector_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        selector_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        insight_canvas = tk.Canvas(insights, bg="#1d1e20", highlightthickness=0)
        insight_scroll = ttk.Scrollbar(insights, orient=tk.VERTICAL, command=insight_canvas.yview)
        self.item_insight_frame = tk.Frame(insight_canvas, bg="#1d1e20")

        self.item_insight_frame.bind(
            "<Configure>", lambda e: insight_canvas.configure(scrollregion=insight_canvas.bbox("all"))
        )
        insight_canvas.create_window((0, 0), window=self.item_insight_frame, anchor="nw")
        insight_canvas.configure(yscrollcommand=insight_scroll.set)
        insight_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        insight_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_item_grid()
        self._refresh_item_grid_filter()
        self._refresh_items_tab()

    def _build_item_grid(self):
        ordered = sorted(
            self.items,
            key=lambda i: (ITEM_NATURE_ORDER.get(i.get("nature"), 99), i.get("name", "")),
        )
        self.item_display_slugs = [item["slug"] for item in ordered]

        for idx, item in enumerate(ordered):
            row, col = divmod(idx, ITEM_GRID_COLS)
            slug = item["slug"]
            rank = (item.get("rank") or "?").upper()
            rank_color = RANK_BADGE_COLORS.get(rank, RANK_BADGE_COLORS["?"])

            card = tk.Frame(self.item_grid_frame, bg="#2a2b2e", padx=2, pady=2, bd=2, relief=tk.FLAT, cursor="hand2")
            card.grid(row=row, column=col, padx=2, pady=2, sticky="n")

            rank_lbl = tk.Label(card, text=rank, bg=rank_color, fg="black",
                                font=("Segoe UI", 7, "bold"), width=3)
            rank_lbl.pack(fill=tk.X)

            icon = self.item_images.get(slug)
            icon_lbl = tk.Label(card, image=icon, bg="#333")
            icon_lbl.pack()

            name_lbl = tk.Label(card, text=item["name"], bg="#1d1e20", fg="white",
                                font=("Segoe UI", 7), wraplength=ITEM_IMG_SIZE + 18, justify=tk.CENTER)
            name_lbl.pack(fill=tk.X)

            meta_lbl = tk.Label(card, text=item.get("nature", ""), bg="#2a2b2e", fg="#9aa7b8",
                                font=("Segoe UI", 6, "italic"))
            meta_lbl.pack(fill=tk.X)

            count_lbl = tk.Label(card, text="", bg="#2a2b2e", fg="#ffd27f",
                                 font=("Segoe UI", 7, "bold"))
            count_lbl.pack(fill=tk.X)

            self.item_widgets[slug] = (card, rank_lbl, icon_lbl, name_lbl, meta_lbl, count_lbl)

            for widget in (card, rank_lbl, icon_lbl, name_lbl, meta_lbl, count_lbl):
                widget.bind("<Button-1>", lambda e, s=slug: self._toggle_item(s, +1))
                widget.bind("<Button-3>", lambda e, s=slug: self._toggle_item(s, -1))

    def _item_rank_score(self, item):
        rank = (item.get("rank") or "").upper()
        if rank in TIER_SCORES:
            return float(TIER_SCORES[rank])
        return ITEM_RANK_FALLBACK.get(item.get("nature"), 4.0)

    def _win_rate_value(self, unit_name):
        raw = str(self.units_map[unit_name].get("win_rate", "")).replace("%", "").strip()
        if not raw:
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return 0.0

    def _unit_strength(self, unit_name):
        unit = self.units_map[unit_name]
        tier_score = TIER_SCORES.get((unit.get("tier") or "C").upper(), 3)
        cost = float(unit.get("cost", 1))
        win_rate = self._win_rate_value(unit_name)
        return (tier_score * 1.3) + (cost * 0.9) + (win_rate * 0.08)

    def _item_holder_candidates(self, item, team_names):
        candidates = []
        recommended_set = set(item.get("recommended_units", []))
        emblem_trait = None
        if item.get("nature") == "emblem" and item["name"].endswith(" Emblem"):
            emblem_trait = item["name"].replace(" Emblem", "")

        for unit_name in team_names:
            base = self._unit_strength(unit_name)
            is_recommended = unit_name in recommended_set
            if is_recommended:
                base += 18.0
            if emblem_trait:
                if emblem_trait in self.units_map[unit_name]["traits"]:
                    base -= 2.0
                else:
                    base += 4.0
            candidates.append({"name": unit_name, "score": base, "recommended": is_recommended})

        candidates.sort(key=lambda x: (-x["score"], x["name"]))
        return candidates

    def _item_team_score(self, item, team_names):
        rank_score = self._item_rank_score(item)
        holders = self._item_holder_candidates(item, team_names)
        holder_score = holders[0]["score"] if holders else 0.0
        direct_bonus = 10.0 if holders and holders[0]["recommended"] else 0.0
        return (rank_score * 6.0) + holder_score + direct_bonus, holders

    def _sync_equipped_with_team(self):
        selected_now = set(self.selected)
        for unit_name in list(self.equipped_items.keys()):
            equipped = self.equipped_items.get(unit_name, [])
            if unit_name not in selected_now:
                for item_slug in equipped:
                    self.inventory_counts[item_slug] = self.inventory_counts.get(item_slug, 0) + 1
                self.equipped_items.pop(unit_name, None)
                continue
            if len(equipped) > MAX_ITEMS_PER_UNIT:
                overflow = equipped[MAX_ITEMS_PER_UNIT:]
                self.equipped_items[unit_name] = equipped[:MAX_ITEMS_PER_UNIT]
                for item_slug in overflow:
                    self.inventory_counts[item_slug] = self.inventory_counts.get(item_slug, 0) + 1

    def _holders_to_names(self, holders):
        names = []
        for holder in holders or []:
            if isinstance(holder, dict):
                name = holder.get("name")
            else:
                name = holder
            if name and name in self.selected and name not in names:
                names.append(name)
        return names

    def _holders_with_grades(self, holders, max_icons=3):
        suggestions = []
        seen = set()
        for holder in holders or []:
            if isinstance(holder, dict):
                name = holder.get("name")
                score = holder.get("score")
            else:
                name = holder
                score = None
            if not name or name not in self.selected or name in seen:
                continue
            seen.add(name)
            try:
                score = float(score) if score is not None else None
            except (TypeError, ValueError):
                score = None
            suggestions.append({"name": name, "score": score})
            if len(suggestions) >= max_icons:
                break

        if not suggestions:
            return []

        top_score = suggestions[0]["score"]
        for idx, entry in enumerate(suggestions):
            if idx == 0:
                grade = "S"
            else:
                score = entry["score"]
                gap = (top_score - score) if (top_score is not None and score is not None) else None
                if idx == 1:
                    grade = "A" if (gap is None or gap <= 5.0) else "B"
                elif idx == 2:
                    grade = "B" if (gap is None or gap <= 5.0) else "C"
                else:
                    grade = "D"
            entry["grade"] = grade
        return suggestions

    def _find_holder_with_slot(self, item, preferred_holders=None):
        team_names = sorted(self.selected)
        if not team_names:
            return None

        preferred = self._holders_to_names(preferred_holders)
        for name in preferred:
            if len(self.equipped_items.get(name, [])) < MAX_ITEMS_PER_UNIT:
                return name

        for cand in self._item_holder_candidates(item, team_names):
            unit_name = cand["name"]
            if len(self.equipped_items.get(unit_name, [])) < MAX_ITEMS_PER_UNIT:
                return unit_name
        return None

    def _equip_from_inventory(self, item_slug, preferred_holders=None):
        item = self.items_map.get(item_slug)
        if not item:
            return False
        if self.inventory_counts.get(item_slug, 0) <= 0:
            return False
        holder = self._find_holder_with_slot(item, preferred_holders)
        if not holder:
            self.item_action_message = f"Aucun slot item libre dans l'equipe pour {item['name']}."
            return False
        self.inventory_counts[item_slug] -= 1
        if self.inventory_counts[item_slug] <= 0:
            self.inventory_counts.pop(item_slug, None)
        self.equipped_items.setdefault(holder, []).append(item_slug)
        self.item_action_message = f"{item['name']} equipe sur {holder}."
        return True

    def _craft_from_components(self, comp_a, comp_b, preferred_holders=None):
        if not self._can_craft_now(comp_a, comp_b):
            return False
        result = self.component_matrix.get(comp_a, {}).get(comp_b)
        if not result:
            result = self.component_matrix.get(comp_b, {}).get(comp_a)
        if not result:
            return False
        result_slug = result.get("slug")
        item = self.items_map.get(result_slug)
        if not item:
            return False

        self.inventory_counts[comp_a] -= 1
        if self.inventory_counts[comp_a] <= 0:
            self.inventory_counts.pop(comp_a, None)
        self.inventory_counts[comp_b] -= 1
        if self.inventory_counts[comp_b] <= 0:
            self.inventory_counts.pop(comp_b, None)

        holder = self._find_holder_with_slot(item, preferred_holders)
        if holder:
            self.equipped_items.setdefault(holder, []).append(result_slug)
            self.item_action_message = f"Craft {item['name']} puis equipe sur {holder}."
        else:
            self.inventory_counts[result_slug] = self.inventory_counts.get(result_slug, 0) + 1
            self.item_action_message = f"Craft {item['name']} (ajoute a l'inventaire, aucun slot libre)."
        return True

    def _craft_option(self, option):
        preferred = option.get("holders", [])
        crafted = self._craft_from_components(option["a"], option["b"], preferred)
        if not crafted:
            self.item_action_message = "Craft impossible avec l'inventaire actuel."
        self._refresh()

    def _craft_option_for_holder(self, option, holder_name):
        if holder_name not in self.selected:
            self.item_action_message = f"{holder_name} n'est pas dans l'equipe."
            self._refresh()
            return
        if len(self.equipped_items.get(holder_name, [])) >= MAX_ITEMS_PER_UNIT:
            self.item_action_message = f"{holder_name} a deja {MAX_ITEMS_PER_UNIT} items."
            self._refresh()
            return
        crafted = self._craft_from_components(option["a"], option["b"], [holder_name])
        if not crafted:
            self.item_action_message = "Craft impossible avec l'inventaire actuel."
        self._refresh()

    def _equip_option(self, item_slug, holders=None):
        if not self.selected:
            self.item_action_message = "Selectionne une equipe avant d'equiper un item."
            self._refresh()
            return
        if not self._equip_from_inventory(item_slug, holders):
            if not self.item_action_message:
                self.item_action_message = "Equipement impossible."
        self._refresh()

    def _unequip_item(self, unit_name, slot_idx):
        equipped = self.equipped_items.get(unit_name, [])
        if slot_idx < 0 or slot_idx >= len(equipped):
            return
        item_slug = equipped.pop(slot_idx)
        if not equipped:
            self.equipped_items.pop(unit_name, None)
        self.inventory_counts[item_slug] = self.inventory_counts.get(item_slug, 0) + 1
        item_name = self.items_map.get(item_slug, {}).get("name", item_slug)
        self.item_action_message = f"{item_name} retire de {unit_name}."
        self._refresh()

    def _on_team_item_click(self, unit_name, slot_idx):
        self._unequip_item(unit_name, slot_idx)
        return "break"

    def _render_holder_icons(self, parent, holders, max_icons=3, on_click=None):
        holder_entries = self._holders_with_grades(holders, max_icons=max_icons)
        if not holder_entries:
            return
        bg = parent.cget("bg") if hasattr(parent, "cget") else "#1d1e20"
        icons_box = tk.Frame(parent, bg=bg)
        icons_box.pack(side=tk.RIGHT, padx=(4, 0))
        for entry in holder_entries:
            name = entry["name"]
            grade = entry.get("grade", "?")
            slot = tk.Frame(icons_box, bg=bg)
            slot.pack(side=tk.LEFT, padx=1)

            icon = self.rec_pick_images.get(name)
            icon_lbl = tk.Label(
                slot,
                image=icon,
                text="" if icon else name[:1].upper(),
                bg=bg,
                fg="white",
                cursor="hand2" if on_click else "arrow",
                font=("Segoe UI", 7, "bold"),
            )
            icon_lbl.pack()

            badge_bg = RANK_BADGE_COLORS.get(grade, RANK_BADGE_COLORS["?"])
            grade_lbl = tk.Label(
                slot,
                text=grade,
                bg=badge_bg,
                fg="black",
                font=("Segoe UI", 6, "bold"),
                width=2,
            )
            grade_lbl.pack(pady=(1, 0))

            if on_click:
                icon_lbl.bind("<Button-1>", lambda e, n=name: (on_click(n), "break")[1])
                grade_lbl.bind("<Button-1>", lambda e, n=name: (on_click(n), "break")[1])

    def _can_craft_now(self, comp_a, comp_b):
        count_a = self.inventory_counts.get(comp_a, 0)
        count_b = self.inventory_counts.get(comp_b, 0)
        if comp_a == comp_b:
            return count_a >= 2
        return count_a >= 1 and count_b >= 1

    def _current_craft_options(self, team_names):
        options = []
        for i, comp_a in enumerate(self.component_slugs):
            row = self.component_matrix.get(comp_a, {})
            for comp_b in self.component_slugs[i:]:
                result = row.get(comp_b)
                if not result:
                    continue
                if not self._can_craft_now(comp_a, comp_b):
                    continue
                result_item = self.items_map.get(result["slug"])
                if not result_item:
                    continue
                score, holders = self._item_team_score(result_item, team_names)
                craft_count = (
                    self.inventory_counts.get(comp_a, 0) // 2
                    if comp_a == comp_b
                    else min(self.inventory_counts.get(comp_a, 0), self.inventory_counts.get(comp_b, 0))
                )
                options.append({
                    "a": comp_a,
                    "b": comp_b,
                    "result": result_item,
                    "score": score,
                    "holders": holders[:3],
                    "craft_count": max(1, craft_count),
                })
        options.sort(key=lambda x: (-x["score"], x["result"]["name"]))
        return options

    def _matches_item_filter(self, item, query, nature_filter, rank_filter):
        if nature_filter != "all" and item.get("nature") != nature_filter:
            return False
        item_rank = (item.get("rank") or "").upper()
        if rank_filter != "all":
            if rank_filter == "unranked":
                if item_rank in TIER_SCORES:
                    return False
            elif item_rank != rank_filter:
                return False

        if not query:
            return True

        q = query.lower()
        if q in item["name"].lower():
            return True
        if q in item["slug"].lower():
            return True
        if q in (item.get("nature") or "").lower():
            return True
        if q == (item.get("rank") or "").lower():
            return True
        for unit_name in item.get("recommended_units", []):
            if q in unit_name.lower():
                return True
        return False

    def _refresh_item_grid_filter(self):
        if not hasattr(self, "item_display_slugs"):
            return
        query = (self.item_search_var.get() if hasattr(self, "item_search_var") else "").strip()
        nature_filter = self.item_nature_var.get() if hasattr(self, "item_nature_var") else "all"
        rank_filter = self.item_rank_var.get() if hasattr(self, "item_rank_var") else "all"
        rank_filter = rank_filter.upper() if rank_filter not in ("all", "unranked") else rank_filter

        visible = []
        for slug in self.item_display_slugs:
            item = self.items_map[slug]
            frame = self.item_widgets[slug][0]
            if self._matches_item_filter(item, query, nature_filter, rank_filter):
                visible.append(slug)
            else:
                frame.grid_remove()

        for idx, slug in enumerate(visible):
            row, col = divmod(idx, ITEM_GRID_COLS)
            self.item_widgets[slug][0].grid(row=row, column=col, padx=2, pady=2, sticky="n")

        self._refresh_item_widget_styles()

    def _refresh_item_widget_styles(self):
        for slug in self.item_display_slugs:
            count = self.inventory_counts.get(slug, 0)
            card, _, _, _, meta_lbl, count_lbl = self.item_widgets[slug]
            if count > 0:
                card.config(bg="#3a5a36", relief=tk.RIDGE)
                meta_lbl.config(bg="#3a5a36")
                count_lbl.config(bg="#3a5a36", text=f"x{count}")
            else:
                card.config(bg="#2a2b2e", relief=tk.FLAT)
                meta_lbl.config(bg="#2a2b2e")
                count_lbl.config(bg="#2a2b2e", text="")

    def _toggle_item(self, slug, delta):
        current = self.inventory_counts.get(slug, 0)
        updated = max(0, current + delta)
        if updated <= 0:
            self.inventory_counts.pop(slug, None)
        else:
            self.inventory_counts[slug] = updated
        self.item_action_message = ""
        self._refresh_items_tab()

    def _reset_inventory(self):
        self.inventory_counts.clear()
        self.equipped_items.clear()
        self.item_action_message = "Inventaire et equipements reinitialises."
        self._refresh()

    def _refresh_items_tab(self):
        if not hasattr(self, "item_insight_frame"):
            return
        self._refresh_item_grid_filter()

        for w in self.item_insight_frame.winfo_children():
            w.destroy()

        if self.item_action_message:
            tk.Label(
                self.item_insight_frame,
                text=self.item_action_message,
                bg="#2b3d2e",
                fg="#b9f4c1",
                font=("Segoe UI", 8, "bold"),
                anchor="w",
                padx=6,
                pady=3,
                wraplength=285,
                justify=tk.LEFT,
            ).pack(fill=tk.X, pady=(0, 4))
            self.item_action_message = ""

        selected_items = [
            self.items_map[slug]
            for slug, count in self.inventory_counts.items()
            if count > 0 and slug in self.items_map
        ]
        selected_items.sort(key=lambda i: (ITEM_NATURE_ORDER.get(i.get("nature"), 99), i["name"]))
        team_names = sorted(self.selected)

        tk.Label(
            self.item_insight_frame,
            text="Pertinence porteur: ordre + badge sous la tete (S meilleur -> D plus faible).",
            bg="#1d1e20",
            fg="#9fc7ff",
            font=("Segoe UI", 8, "italic"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=285,
        ).pack(fill=tk.X, pady=(0, 4))

        inv_section = tk.LabelFrame(self.item_insight_frame, text="Inventory", bg="#1d1e20", fg="white",
                                    font=("Segoe UI", 9, "bold"), bd=1, relief=tk.GROOVE, padx=4, pady=4)
        inv_section.pack(fill=tk.X, pady=(0, 4))

        if not selected_items:
            tk.Label(inv_section, text="Click items/components to add them.",
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 8)).pack(anchor="w")
        else:
            for item in selected_items:
                slug = item["slug"]
                row = tk.Frame(inv_section, bg="#1d1e20")
                row.pack(fill=tk.X, pady=1)
                icon = self.item_inv_images.get(slug)
                tk.Label(row, image=icon, bg="#1d1e20").pack(side=tk.LEFT, padx=(0, 4))
                tk.Label(row, text=f"x{self.inventory_counts[slug]}  {item['name']}",
                         bg="#1d1e20", fg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT)
                tk.Button(row, text="-", bg="#444", fg="white", relief=tk.FLAT, width=2,
                          command=lambda s=slug: self._toggle_item(s, -1)).pack(side=tk.RIGHT, padx=(2, 0))
                tk.Button(row, text="+", bg="#444", fg="white", relief=tk.FLAT, width=2,
                          command=lambda s=slug: self._toggle_item(s, +1)).pack(side=tk.RIGHT)

        equip_section = tk.LabelFrame(self.item_insight_frame, text="Best holders for completed items",
                                      bg="#1d1e20", fg="white", font=("Segoe UI", 9, "bold"),
                                      bd=1, relief=tk.GROOVE, padx=4, pady=4)
        equip_section.pack(fill=tk.X, pady=(0, 4))

        completed = [i for i in selected_items if i.get("nature") != "component"]
        if not completed:
            tk.Label(equip_section, text="No completed item selected.",
                     bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")
        elif not team_names:
            tk.Label(equip_section, text="Select champions in your team to get holder advice.",
                     bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")
        else:
            completed_scores = []
            for item in completed:
                score, holders = self._item_team_score(item, team_names)
                completed_scores.append((score, item, holders))
            completed_scores.sort(key=lambda x: (-x[0], x[1]["name"]))
            for _, item, holders in completed_scores:
                slug = item["slug"]
                qty = self.inventory_counts.get(slug, 0)
                row = tk.Frame(equip_section, bg="#1d1e20")
                row.pack(fill=tk.X, pady=1)

                tk.Button(
                    row,
                    text="Equip best",
                    bg="#3b6f9e",
                    fg="white",
                    activebackground="#4a83b5",
                    activeforeground="white",
                    relief=tk.FLAT,
                    padx=6,
                    pady=1,
                    state=tk.NORMAL if qty > 0 else tk.DISABLED,
                    command=lambda s=slug, h=holders: self._equip_option(s, h),
                ).pack(side=tk.RIGHT, padx=(4, 0))

                content = tk.Frame(row, bg="#1d1e20")
                content.pack(side=tk.LEFT, fill=tk.X, expand=True)
                icon_lbl = tk.Label(content, image=self.item_inv_images.get(slug), bg="#1d1e20", cursor="hand2")
                icon_lbl.pack(side=tk.LEFT, padx=(0, 4))
                text_col = tk.Frame(content, bg="#1d1e20")
                text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
                rank = (item.get("rank") or "?").upper()
                title_lbl = tk.Label(
                    text_col,
                    text=f"x{qty} {item['name']} ({rank})",
                    bg="#1d1e20",
                    fg="white",
                    font=("Segoe UI", 8, "bold"),
                )
                title_lbl.pack(anchor="w")
                if holders:
                    top = ", ".join(h["name"] for h in holders[:3])
                    holder_row = tk.Frame(text_col, bg="#1d1e20")
                    holder_row.pack(fill=tk.X)
                    tk.Label(
                        holder_row,
                        text=f"  -> {top}",
                        bg="#1d1e20",
                        fg="#9fc7ff",
                        font=("Segoe UI", 8),
                        anchor="w",
                    ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                    self._render_holder_icons(holder_row, holders)
                else:
                    tk.Label(
                        text_col,
                        text="  -> No holder suggestion",
                        bg="#1d1e20",
                        fg="#777",
                        font=("Segoe UI", 8),
                    ).pack(anchor="w")

                for widget in (icon_lbl, title_lbl):
                    widget.bind("<Button-1>", lambda e, s=slug, h=holders: self._equip_option(s, h))

        component_section = tk.LabelFrame(self.item_insight_frame, text="Component decisions (craft vs wait)",
                                          bg="#1d1e20", fg="white", font=("Segoe UI", 9, "bold"),
                                          bd=1, relief=tk.GROOVE, padx=4, pady=4)
        component_section.pack(fill=tk.X, pady=(0, 4))

        owned_components = [
            self.items_map[slug]
            for slug in self.component_slugs
            if self.inventory_counts.get(slug, 0) > 0 and slug in self.items_map
        ]
        component_best = {}
        if not owned_components:
            tk.Label(component_section, text="No component selected.", bg="#1d1e20",
                     fg="#777", font=("Segoe UI", 8)).pack(anchor="w")
        else:
            for comp in owned_components:
                comp_slug = comp["slug"]
                options = []
                matrix_row = self.component_matrix.get(comp_slug, {})
                for partner_slug in self.component_slugs:
                    result = matrix_row.get(partner_slug)
                    if not result:
                        continue
                    result_item = self.items_map.get(result["slug"])
                    if not result_item:
                        continue
                    score, holders = self._item_team_score(result_item, team_names)
                    need_now = 2 if partner_slug == comp_slug else 1
                    can_now = self.inventory_counts.get(partner_slug, 0) >= need_now
                    options.append({
                        "partner_slug": partner_slug,
                        "result_item": result_item,
                        "score": score,
                        "holders": holders,
                        "craft_now": can_now,
                    })
                if not options:
                    continue
                options.sort(key=lambda x: (-x["score"], x["result_item"]["name"]))
                best_overall = options[0]
                best_now = next((o for o in options if o["craft_now"]), None)
                component_best[comp_slug] = best_overall

                block = tk.Frame(component_section, bg="#1d1e20")
                block.pack(fill=tk.X, pady=2)
                tk.Label(block, image=self.item_inv_images.get(comp_slug), bg="#1d1e20").pack(side=tk.LEFT, padx=(0, 4))
                qty = self.inventory_counts.get(comp_slug, 0)
                tk.Label(block, text=f"{comp['name']} x{qty}", bg="#1d1e20", fg="white",
                         font=("Segoe UI", 8, "bold")).pack(anchor="w")

                if best_now:
                    partner_name = self.items_map[best_now["partner_slug"]]["name"]
                    rank = (best_now["result_item"].get("rank") or "?").upper()
                    result_slug = best_now["result_item"]["slug"]
                    now_row = tk.Frame(block, bg="#1d1e20")
                    now_row.pack(fill=tk.X)
                    now_option = {"a": comp_slug, "b": best_now["partner_slug"], "holders": best_now["holders"]}
                    now_icon = tk.Label(
                        now_row,
                        image=self.item_inv_images.get(result_slug),
                        bg="#1d1e20",
                    )
                    now_icon.pack(side=tk.LEFT, padx=(0, 4))
                    now_text = tk.Label(
                        now_row,
                        text=f"  Craft now with {partner_name}: {best_now['result_item']['name']} ({rank})  [click holder icon]",
                        bg="#1d1e20",
                        fg="#9fc7ff",
                        font=("Segoe UI", 8),
                        wraplength=240,
                        justify=tk.LEFT,
                        anchor="w",
                    )
                    now_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    self._render_holder_icons(
                        now_row,
                        best_now["holders"],
                        on_click=lambda holder, o=now_option: self._craft_option_for_holder(o, holder),
                    )
                else:
                    tk.Label(block, text="  No immediate craft from current inventory.",
                             bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")

                if (not best_overall["craft_now"]) or (best_now and best_overall["score"] > best_now["score"] + 8):
                    partner_name = self.items_map[best_overall["partner_slug"]]["name"]
                    rank = (best_overall["result_item"].get("rank") or "?").upper()
                    wait_row = tk.Frame(block, bg="#1d1e20")
                    wait_row.pack(fill=tk.X)
                    tk.Label(
                        wait_row,
                        text=f"  Better to wait for {partner_name}: {best_overall['result_item']['name']} ({rank})",
                        bg="#1d1e20",
                        fg="#e8a33c",
                        font=("Segoe UI", 8),
                        wraplength=250,
                        justify=tk.LEFT,
                        anchor="w",
                    ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                    self._render_holder_icons(wait_row, best_overall["holders"])

        craft_section = tk.LabelFrame(self.item_insight_frame, text="Immediate crafts available",
                                      bg="#1d1e20", fg="white", font=("Segoe UI", 9, "bold"),
                                      bd=1, relief=tk.GROOVE, padx=4, pady=4)
        craft_section.pack(fill=tk.X, pady=(0, 4))

        craft_options = self._current_craft_options(team_names)
        if not craft_options:
            tk.Label(craft_section, text="No craft possible with current components.",
                     bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")
        else:
            for opt in craft_options[:10]:
                res = opt["result"]
                rank = (res.get("rank") or "?").upper()
                comp_a_name = self.items_map[opt["a"]]["name"]
                comp_b_name = self.items_map[opt["b"]]["name"]

                row = tk.Frame(craft_section, bg="#1d1e20")
                row.pack(fill=tk.X, pady=1)

                content = tk.Frame(row, bg="#1d1e20")
                content.pack(side=tk.LEFT, fill=tk.X, expand=True)
                icon_lbl = tk.Label(content, image=self.item_inv_images.get(res["slug"]), bg="#1d1e20")
                icon_lbl.pack(side=tk.LEFT, padx=(0, 4))
                text_col = tk.Frame(content, bg="#1d1e20")
                text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
                title_row = tk.Frame(text_col, bg="#1d1e20")
                title_row.pack(fill=tk.X)
                title_lbl = tk.Label(
                    title_row,
                    text=f"{res['name']} ({rank}) | {comp_a_name} + {comp_b_name} | x{opt['craft_count']}  [click holder icon]",
                    bg="#1d1e20",
                    fg="white",
                    font=("Segoe UI", 8),
                    wraplength=238,
                    justify=tk.LEFT,
                    anchor="w",
                )
                title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._render_holder_icons(
                    title_row,
                    opt["holders"],
                    on_click=lambda holder, o=opt: self._craft_option_for_holder(o, holder),
                )

                best_a = component_best.get(opt["a"])
                best_b = component_best.get(opt["b"])
                better_wait = False
                if best_a and (not best_a["craft_now"]) and best_a["score"] > opt["score"] + 8:
                    better_wait = True
                if best_b and (not best_b["craft_now"]) and best_b["score"] > opt["score"] + 8:
                    better_wait = True
                if rank in ("D", "C") or better_wait:
                    tk.Label(
                        text_col,
                        text="  Attention: low value now, waiting for a better component can be stronger.",
                        bg="#1d1e20",
                        fg="#e8a33c",
                        font=("Segoe UI", 8, "italic"),
                        wraplength=230,
                        justify=tk.LEFT,
                    ).pack(anchor="w")

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
        self.w_cap.set(values["cap_potential"])
        self.w_odds.set(values["odds"])
        self.w_multi.set(values["multi_synergy"])
        self._refresh()

    def _reset_config(self):
        self._apply_preset(DEFAULT_WEIGHTS)
        self.scenario_diversity.set(0.5)
        self._set_scenario_sort("score")

    def _get_weights(self):
        return {
            "tier": self.w_tier.get(),
            "traits": self.w_traits.get(),
            "cap_potential": self.w_cap.get(),
            "odds": self.w_odds.get(),
            "multi_synergy": self.w_multi.get(),
        }

    def _set_sort(self, mode):
        self.sort_mode = mode
        self._update_sort_buttons()
        self._resort_grid()

    def _set_scenario_sort(self, mode):
        self.scenario_sort_mode = mode
        self._update_scenario_sort_buttons()
        self._refresh()

    def _update_sort_buttons(self):
        for m, btn in self.sort_buttons.items():
            if m == self.sort_mode:
                btn.config(bg="#666", relief=tk.SUNKEN)
            else:
                btn.config(bg="#444", relief=tk.FLAT)

    def _update_scenario_sort_buttons(self):
        for m, btn in self.scenario_sort_buttons.items():
            if m == self.scenario_sort_mode:
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

    def _apply_scenario(self, scenario):
        self.history.append(set(self.selected))
        team_size = self.team_size_var.get()
        for name in scenario["pick_names"]:
            if len(self.selected) >= team_size:
                break
            self.selected.add(name)
        self._refresh()

    def _show_tooltip(self, event, text):
        if not text:
            return
        self._hide_tooltip()
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.configure(bg="#111")
        self.tooltip_label = tk.Label(
            self.tooltip_window,
            text=text,
            justify=tk.LEFT,
            bg="#111",
            fg="#ddd",
            font=("Consolas", 8),
            padx=6,
            pady=4,
            wraplength=360,
        )
        self.tooltip_label.pack()
        self._move_tooltip(event)

    def _move_tooltip(self, event):
        if not self.tooltip_window:
            return
        x = event.x_root + 12
        y = event.y_root + 12
        self.tooltip_window.geometry(f"+{x}+{y}")

    def _hide_tooltip(self, _event=None):
        if self.tooltip_window is not None:
            self.tooltip_window.destroy()
            self.tooltip_window = None
            self.tooltip_label = None

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
            tk.Label(self.team_frame, text="Click a champion to add it",
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 9)).pack(pady=8)
            return

        row_frame = tk.Frame(self.team_frame, bg="#1d1e20")
        row_frame.pack(pady=4)

        for name in sorted(self.selected):
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

            equipped_row = tk.Frame(slot, bg="#1d1e20")
            equipped_row.pack(pady=(2, 0))
            equipped = self.equipped_items.get(name, [])
            for idx in range(MAX_ITEMS_PER_UNIT):
                if idx < len(equipped):
                    item_slug = equipped[idx]
                    icon = self.team_item_images.get(item_slug)
                    item_lbl = tk.Label(equipped_row, image=icon, bg="#1d1e20", cursor="hand2")
                    item_lbl.pack(side=tk.LEFT, padx=1)
                    item_lbl.bind("<Button-1>", lambda e, n=name, i=idx: self._on_team_item_click(n, i))
                else:
                    tk.Label(equipped_row, text="", bg="#333", width=2, height=1,
                             relief=tk.SUNKEN, bd=1).pack(side=tk.LEFT, padx=1)

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
            tk.Label(self.traits_frame, text="No active traits",
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 9)).pack(pady=6)
            return

        for trait_name, count in active.items():
            self._render_trait_row(self.traits_frame, trait_name, count)

    def _format_trait_progress(self, trait_name, count):
        reached, next_th, reached_index = self._get_highest_threshold(trait_name, count)
        if next_th:
            return f"{count}/{next_th}"
        if reached > 0:
            return f"{count} (max)"
        return str(count)

    def _render_trait_row(self, parent, trait_name, count, progress_text=None, row_bg="#2a2b2e"):
        reached, _, reached_index = self._get_highest_threshold(trait_name, count)

        if reached_index < 0:
            color = "#aaa"
        else:
            clamped = min(reached_index, len(TRAIT_TIER_COLORS) - 1)
            color = TRAIT_TIER_COLORS[clamped]

        row = tk.Frame(parent, bg=row_bg, pady=2, padx=6)
        row.pack(fill=tk.X, pady=1)

        icon = self.trait_images.get(trait_name)
        if icon:
            tk.Label(row, image=icon, bg=row_bg).pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(row, text=trait_name, bg=row_bg, fg=color,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(side=tk.LEFT)

        progress = progress_text if progress_text is not None else self._format_trait_progress(trait_name, count)
        tk.Label(row, text=progress, bg=row_bg, fg=color,
                 font=("Segoe UI", 8)).pack(side=tk.RIGHT)

    def _render_trait_delta_row(self, parent, delta, is_upgrade=False):
        gain = delta["after_count"] - delta["before_count"]
        gain_txt = f"+{gain}" if gain >= 0 else str(gain)
        tier_txt = delta.get("after_tier_letter")
        progress_txt = f"{gain_txt} ({tier_txt})" if tier_txt else gain_txt
        row_bg = "#2f3a31" if is_upgrade else "#2a2b2e"
        self._render_trait_row(
            parent,
            delta["name"],
            delta["after_count"],
            progress_text=progress_txt,
            row_bg=row_bg,
        )

    def _refresh(self):
        team_size = self.team_size_var.get()

        while len(self.selected) > team_size:
            self.selected.pop()
        self._sync_equipped_with_team()

        self.selection_count_label.config(
            text=f"{len(self.selected)} / {team_size} selected")

        # Compute recommendation scenarios first (needed for grid highlight)
        scenarios = compute_recommendation_scenarios(
            self.selected, team_size, self.unlocked,
            self.units, self.trait_thresholds, self.trait_tiers, self._get_weights(), top_n=3,
            diversity=self.scenario_diversity.get(),
            sort_mode=self.scenario_sort_mode,
        )
        self.recommended_names = {
            name for scenario in scenarios for name in scenario["pick_names"]
        }

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
        self._refresh_items_tab()
        self._hide_tooltip()

        for w in self.rec_frame.winfo_children():
            w.destroy()

        if not scenarios:
            msg = "Team full!" if len(self.selected) >= team_size else \
                  "Select champions\nand adjust team size"
            tk.Label(self.rec_frame, text=msg,
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 10)).pack(pady=20)
            return

        for col in range(3):
            self.rec_frame.grid_columnconfigure(col, weight=1)

        for col in range(3):
            scenario = scenarios[col] if col < len(scenarios) else None

            card = tk.Frame(self.rec_frame, bg="#2a2b2e", pady=6, padx=8, bd=1, relief=tk.RIDGE)
            card.grid(row=0, column=col, sticky="nsew", padx=3, pady=3)

            if scenario is None:
                tk.Label(card, text=f"Scenario {col + 1}", bg="#2a2b2e", fg="#777",
                         font=("Segoe UI", 10, "bold")).pack(anchor="w")
                tk.Label(card, text="Indisponible", bg="#2a2b2e", fg="#777",
                         font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
                continue

            header = tk.Frame(card, bg="#2a2b2e")
            header.pack(fill=tk.X)

            tk.Label(header, text=f"Scenario {col + 1}", bg="#2a2b2e", fg="white",
                     font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
            tk.Label(header, text=f"{scenario['score']:.1f}pts", bg="#2a2b2e", fg="#aaa",
                     font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 0))
            tk.Label(header, text=f"{int(scenario['avg_odds'] * 100)}% roll", bg="#2a2b2e", fg="#aaa",
                     font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(6, 0))
            tk.Button(
                header,
                text="Apply",
                bg="#3b6f9e",
                fg="white",
                activebackground="#4a83b5",
                activeforeground="white",
                relief=tk.FLAT,
                padx=6,
                pady=1,
                command=lambda s=scenario: self._apply_scenario(s),
            ).pack(side=tk.RIGHT)

            reason_label = tk.Label(
                card,
                text=f"Pourquoi:\n{scenario['reason']}",
                bg="#2a2b2e",
                fg="#b8b8b8",
                font=("Segoe UI", 8, "italic"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=175,
            )
            reason_label.pack(fill=tk.X, pady=(4, 4))
            reason_label.bind(
                "<Enter>", lambda e, txt=scenario["reason_tooltip"]: self._show_tooltip(e, txt)
            )
            reason_label.bind("<Motion>", self._move_tooltip)
            reason_label.bind("<Leave>", self._hide_tooltip)

            picks_title = tk.Label(card, text="Ajouts proposes", bg="#2a2b2e", fg="#9fc7ff",
                                   font=("Segoe UI", 8, "bold"), anchor="w")
            picks_title.pack(fill=tk.X)

            for pick in scenario["picks"]:
                unit_name = pick["name"]
                unit_icon = self.rec_pick_images.get(unit_name)
                pick_button = tk.Button(
                    card,
                    text=f" {unit_name}",
                    image=unit_icon,
                    compound=tk.LEFT,
                    bg="#26272a",
                    fg="white",
                    activebackground="#333",
                    activeforeground="white",
                    relief=tk.FLAT,
                    anchor="w",
                    padx=4,
                    command=lambda n=unit_name: self._toggle(n),
                )
                pick_button.pack(fill=tk.X, pady=1)

            compare_title = tk.Label(card, text="Paliers montes (gain net)",
                                     bg="#2a2b2e", fg="#9fc7ff",
                                     font=("Segoe UI", 8, "bold"), anchor="w")
            compare_title.pack(fill=tk.X, pady=(6, 2))

            upgrade_box = tk.Frame(card, bg="#1d1e20")
            upgrade_box.pack(fill=tk.X)
            if scenario["trait_upgrades"]:
                for delta in scenario["trait_upgrades"][:4]:
                    self._render_trait_delta_row(upgrade_box, delta, is_upgrade=True)
            else:
                tk.Label(upgrade_box, text="No tier upgrade", bg="#1d1e20", fg="#777",
                         font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=2)

            cap_title = tk.Label(card, text="Potentiel cap max",
                                 bg="#2a2b2e", fg="#9fc7ff",
                                 font=("Segoe UI", 8, "bold"), anchor="w")
            cap_title.pack(fill=tk.X, pady=(6, 2))

            cap_box = tk.Frame(card, bg="#1d1e20")
            cap_box.pack(fill=tk.X)
            if scenario["cap_opportunities"]:
                for cap in scenario["cap_opportunities"][:3]:
                    txt = (
                        f"{cap['trait']}: {cap['new_tier_letter'] or '-'} -> "
                        f"{cap['potential_tier_letter'] or '-'} (+{cap['future_gain']:.1f})"
                    )
                    tk.Label(cap_box, text=txt, bg="#1d1e20", fg="#8bc5ff",
                             font=("Segoe UI", 8), anchor="w").pack(fill=tk.X, padx=6, pady=1)
            else:
                tk.Label(cap_box, text="No strong cap opportunity", bg="#1d1e20", fg="#777",
                         font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=2)

            stable_title = tk.Label(card, text="Traits stables",
                                    bg="#2a2b2e", fg="#9fc7ff",
                                    font=("Segoe UI", 8, "bold"), anchor="w")
            stable_title.pack(fill=tk.X, pady=(6, 2))

            stable_box = tk.Frame(card, bg="#1d1e20")
            stable_box.pack(fill=tk.X)
            if scenario["stable_traits"]:
                for delta in scenario["stable_traits"][:3]:
                    self._render_trait_delta_row(stable_box, delta, is_upgrade=False)
            else:
                tk.Label(stable_box, text="No stable active trait", bg="#1d1e20", fg="#777",
                         font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=2)

            final_traits_title = tk.Label(card, text="Traits actifs finaux",
                                          bg="#2a2b2e", fg="#9fc7ff",
                                          font=("Segoe UI", 8, "bold"), anchor="w")
            final_traits_title.pack(fill=tk.X, pady=(6, 2))

            final_traits_box = tk.Frame(card, bg="#1d1e20")
            final_traits_box.pack(fill=tk.X)
            for trait_entry in scenario["active_traits"][:4]:
                self._render_trait_row(final_traits_box, trait_entry["name"], trait_entry["count"])


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1350x750")
    app = TFTFinderApp(root)
    root.mainloop()
