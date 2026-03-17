import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import re
import sys
from collections import defaultdict
from itertools import combinations

APP_VERSION = "1.3.0"


def _get_base_dir():
    # PyInstaller onefile extracts bundled files into _MEIPASS.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


DATA_DIR = os.path.join(_get_base_dir(), "data")
ICON_DIR = os.path.join(DATA_DIR, "icons")
APP_ICON_ICO = os.path.join(ICON_DIR, "app.ico")
APP_ICON_PNG = os.path.join(ICON_DIR, "logo_tft-finder.png")
I18N_JSON = os.path.join(DATA_DIR, "i18n.json")
DEFAULT_LANGUAGE = "en"
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

# Unit relationship rules used by recommendation and selection logic.
# Tibbers can only be played when Annie is already in the team.
UNIT_DEPENDENCIES = {
    "AnnieTibbers": {"Annie"},
}
# Tibbers becomes available as soon as Annie is in the team.
AUTO_UNLOCK_DEPENDENCIES = {
    "AnnieTibbers": {"Annie"},
}
# Explicit board-slot overrides for special units.
# Galio is modeled as a passive joker unit (0 board slot).
UNIT_SLOT_COST_OVERRIDES = {
    "Galio": 0,
    "Annie": 1,
    "AnnieTibbers": 1,
}
UNIT_CATEGORY_OVERRIDES = {
    "Galio": "joker",
}


def _unit_slot_cost(unit_name):
    return int(UNIT_SLOT_COST_OVERRIDES.get(unit_name, 1))


def _unit_category(unit_name):
    if unit_name in UNIT_CATEGORY_OVERRIDES:
        return UNIT_CATEGORY_OVERRIDES[unit_name]
    if _unit_slot_cost(unit_name) == 0:
        return "joker"
    return "normal"


def _team_slots_used(team_names):
    return sum(_unit_slot_cost(name) for name in set(team_names))


def _unit_dependencies_met(unit_name, team_names):
    deps = UNIT_DEPENDENCIES.get(unit_name)
    if not deps:
        return True
    team_set = set(team_names)
    return set(deps).issubset(team_set)


def _team_dependencies_valid(team_names):
    team_set = set(team_names)
    for unit_name in team_set:
        if not _unit_dependencies_met(unit_name, team_set):
            return False
    return True


def _normalize_team_by_dependencies(team_names):
    normalized = set(team_names)
    changed = True
    while changed:
        changed = False
        for unit_name in list(normalized):
            if not _unit_dependencies_met(unit_name, normalized):
                normalized.remove(unit_name)
                changed = True
    return normalized


def _is_unit_auto_unlocked(unit_name, team_names):
    deps = AUTO_UNLOCK_DEPENDENCIES.get(unit_name)
    if not deps:
        return False
    team_set = set(team_names)
    return set(deps).issubset(team_set)


def _is_unit_unlocked_for_team(unit, unlocked_names, team_names):
    if not unit.get("locked"):
        return True
    if unit["name"] in unlocked_names:
        return True
    return _is_unit_auto_unlocked(unit["name"], team_names)


def _can_add_unit_to_team(unit_name, team_names):
    prospective = set(team_names)
    prospective.add(unit_name)
    return _team_dependencies_valid(prospective)


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
    team_set = set(selected_names)
    count = 0
    for u in units:
        name = u["name"]
        if name in team_set:
            continue
        if not _is_unit_unlocked_for_team(u, unlocked_names, team_set):
            continue
        if not _can_add_unit_to_team(name, team_set):
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
    base_quality = TRAIT_QUALITY_SCORES.get(letter, 0.0)
    if reached_value <= 1:
        breakpoint_multiplier = 1.0
    else:
        # Same tier letter is worth more when the breakpoint requires more units.
        # Example: an S at 11 should outscore an S at 1.
        breakpoint_multiplier = 1.0 + ((reached_value - 1) / (reached_value + 4))
    return base_quality * breakpoint_multiplier, letter, reached_value, reached_index


DEFAULT_WEIGHTS = {
    "tier": 1.0,
    "traits": 1.0,
    "cap_potential": 0.8,
    "odds": 1.0,
    "multi_synergy": 1.0,
    "bridge": 1.0,
}
DEFAULT_PLANNING_EXTRA_SLOTS = 2
DEFAULT_MAX_SWAP_REPLACEMENTS = 2
SWAP_SEED_LIMIT = 6
SWAP_SCENARIO_BUDGET_PER_TOP_RESULT = 20
SCENARIO_SORT_MODES = [
    ("score", "scenario_sort_score"),
    ("roll", "scenario_sort_roll"),
    ("eco", "scenario_sort_eco"),
    ("spike", "scenario_sort_spike"),
]
FORCED_TRAIT_BASE_BONUS = 6.0
FORCED_TRAIT_ACTIVATION_BONUS = 8.0


def load_i18n_data():
    fallback = {"en": {}, "fr": {}}
    if not os.path.exists(I18N_JSON):
        return fallback
    try:
        with open(I18N_JSON, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return fallback
        for lang in ("en", "fr"):
            if lang not in data or not isinstance(data[lang], dict):
                data[lang] = {}
        return data
    except Exception:
        return fallback


I18N = load_i18n_data()


def tr(lang, key, **kwargs):
    lang_table = I18N.get(lang, {})
    text = lang_table.get(key)
    if text is None:
        text = I18N.get(DEFAULT_LANGUAGE, {}).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def tr_trait(lang, trait_name):
    lang_traits = I18N.get(lang, {}).get("trait_names", {})
    if trait_name in lang_traits:
        return lang_traits[trait_name]
    en_traits = I18N.get(DEFAULT_LANGUAGE, {}).get("trait_names", {})
    return en_traits.get(trait_name, trait_name)


def tr_item(lang, item_slug, fallback_name=None):
    if not item_slug:
        return fallback_name or ""
    lang_items = I18N.get(lang, {}).get("item_names", {})
    if item_slug in lang_items:
        return lang_items[item_slug]
    en_items = I18N.get(DEFAULT_LANGUAGE, {}).get("item_names", {})
    if item_slug in en_items:
        return en_items[item_slug]
    return fallback_name if fallback_name is not None else item_slug


def compute_trait_score(candidate, selected_units, all_units_map, trait_thresholds,
                        trait_tiers=None, unlocked_names=None, all_units=None,
                        weights=None, team_size=None, planning_extra_slots=0,
                        emblem_potential_by_trait=None):
    """Score based on trait synergy with tier quality and cap potential.

    Returns (total_trait_score, matching_traits set, trait_details list).
    """
    w = weights or DEFAULT_WEIGHTS
    quality_w = w.get("traits", 1.0)
    cap_w = w.get("cap_potential", 0.8)
    multi_w = w.get("multi_synergy", 1.0)
    bridge_w = w.get("bridge", 1.0)
    planning_slots = max(0, int(planning_extra_slots or 0))
    emblem_map = emblem_potential_by_trait or {}

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
        slots_left_after_pick = max(0, team_size - _team_slots_used(used_after_pick))

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
        potential_count = new
        potential_quality = new_quality
        potential_letter = new_letter
        potential_reached = new_reached
        future_gain = 0.0
        max_possible_count = new
        natural_max_count = new
        emblem_extra = max(0, int(emblem_map.get(t, 0)))
        bridge_bonus = 0.0
        bridge_target = None
        bridge_target_letter = None
        bridge_requires_emblem = False
        if all_units is not None and unlocked_names is not None and slots_left_after_pick is not None:
            available_after_pick = _count_available_for_trait(
                t, used_after_pick, unlocked_names, all_units)
            effective_slots = slots_left_after_pick + planning_slots
            max_extra = min(available_after_pick, effective_slots)
            natural_max_count = new + max_extra
            max_possible_count = natural_max_count + emblem_extra
            potential_count = max_possible_count
            potential_quality, potential_letter, potential_reached, _ = _trait_quality_value(
                t, potential_count, thresholds, trait_tiers
            )
            future_gain = max(0.0, potential_quality - new_quality)
            if future_gain > 0:
                # Discount very long-term potential by how far it is from current state.
                distance = max(1, potential_count - new)
                score += (future_gain / distance) * cap_w

            if bridge_w > 0 and thresholds:
                best_bridge_raw = 0.0
                for th in thresholds:
                    if th <= new or th > max_possible_count:
                        continue
                    target_quality, target_letter, _, _ = _trait_quality_value(
                        t, th, thresholds, trait_tiers
                    )
                    gain_to_target = max(0.0, target_quality - new_quality)
                    # Support long cap chase even when quality letter is unchanged (e.g. S -> S).
                    # In that case, use a small depth gain based on breakpoint distance.
                    if gain_to_target <= 0:
                        tier_span = max(1, thresholds[-1] - thresholds[0]) if thresholds else 1
                        depth_gain = ((th - new) / tier_span) * 1.2
                        effective_gain = max(0.0, depth_gain)
                    else:
                        effective_gain = gain_to_target
                    if effective_gain <= 0:
                        continue
                    distance_to_target = max(1, th - new)
                    progress_to_target = (new / th) if th > 0 else 1.0
                    bridge_raw = (effective_gain / distance_to_target) * (0.5 + progress_to_target)
                    if bridge_raw > best_bridge_raw:
                        best_bridge_raw = bridge_raw
                        bridge_target = th
                        bridge_target_letter = target_letter
                if bridge_target is not None and best_bridge_raw > 0:
                    bridge_bonus = best_bridge_raw * bridge_w * cap_w
                    score += bridge_bonus
                    bridge_requires_emblem = bridge_target > natural_max_count

            # If next threshold is impossible, downweight dead-end picks.
            if next_th and max_possible_count < next_th and immediate_gain <= 0 and future_gain <= 0 and bridge_bonus <= 0:
                score -= 0.8 * quality_w
        else:
            max_possible_count = new + emblem_extra
            potential_count = max_possible_count
            potential_quality, potential_letter, potential_reached, _ = _trait_quality_value(
                t, potential_count, thresholds, trait_tiers
            )
            future_gain = max(0.0, potential_quality - new_quality)

        if current > 0 and next_th:
            progress = new / next_th
            progress_bonus = progress * 0.6 * quality_w
            if max_possible_count < next_th:
                progress_bonus *= 0.35
            score += progress_bonus

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
            "max_natural_count": natural_max_count,
            "emblem_extra": emblem_extra,
            "bridge_bonus": bridge_bonus,
            "bridge_target": bridge_target,
            "bridge_target_letter": bridge_target_letter,
            "bridge_requires_emblem": bridge_requires_emblem,
            "potential_requires_emblem": potential_count > natural_max_count,
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


def _compute_team_power_score(team_names, all_units_map, trait_thresholds, trait_tiers=None, weights=None):
    """Estimate current board power from unit tiers + active trait quality."""
    w = weights or DEFAULT_WEIGHTS
    tier_w = w.get("tier", 1.0)
    quality_w = w.get("traits", 1.0)
    multi_w = w.get("multi_synergy", 1.0)

    team_set = set(team_names)
    tier_score = 0.0
    for name in team_set:
        unit = all_units_map.get(name)
        if unit:
            tier_score += TIER_SCORES.get(unit.get("tier"), 0)

    trait_counts = _compute_team_traits(team_set, all_units_map)
    trait_score = 0.0
    active_trait_count = 0
    for trait_name, count in trait_counts.items():
        thresholds = trait_thresholds.get(trait_name, [])
        quality_value, _, _, _ = _trait_quality_value(trait_name, count, thresholds, trait_tiers)
        if quality_value > 0:
            active_trait_count += 1
            trait_score += quality_value

    multi_bonus = max(0, active_trait_count - 1) * 0.35
    return (tier_score * tier_w) + (trait_score * quality_w) + (multi_bonus * multi_w)


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


def _build_scenario_reason(picks, trait_upgrades, stable_traits, cap_opportunities,
                           swap_out_names=None, lang=DEFAULT_LANGUAGE):
    reasons = []
    swap_out_names = swap_out_names or []

    if swap_out_names and picks:
        out_list = ", ".join(swap_out_names)
        in_list = ", ".join(p["name"] for p in picks)
        reasons.append(tr(lang, "reason_swap", out=out_list, in_=in_list))

    if trait_upgrades:
        labels = [f"{tr_trait(lang, t['name'])} ({t['after_tier_letter'] or '?'} @ {t['after_reached']})" for t in trait_upgrades]
        reasons.append(tr(lang, "reason_active_or_upgraded", list=_short_list(labels)))

    if cap_opportunities:
        labels = [
            f"{tr_trait(lang, c['trait'])} -> {c['potential_tier_letter']} (cap {c['potential_count']})"
            + (f" {tr(lang, 'hint_emblem_short')}" if c.get("potential_requires_emblem") else "")
            for c in cap_opportunities[:3]
        ]
        reasons.append(tr(lang, "reason_cap_potential", list=_short_list(labels)))

    shared_traits = sorted({tr_trait(lang, trait) for p in picks for trait in p["matching"]})
    if shared_traits:
        reasons.append(tr(lang, "reason_reinforce_existing", list=_short_list(shared_traits)))

    avg_odds = sum(p["odds"] for p in picks) / max(1, len(picks))
    if avg_odds >= 0.20:
        reasons.append(tr(lang, "reason_plan_easy_roll", pct=int(avg_odds * 100)))
    elif avg_odds >= 0.08:
        reasons.append(tr(lang, "reason_plan_playable_roll", pct=int(avg_odds * 100)))
    else:
        reasons.append(tr(lang, "reason_plan_greedy", pct=int(avg_odds * 100)))

    if stable_traits:
        labels = [f"{tr_trait(lang, t['name'])} ({t['after_count']})" for t in stable_traits[:3]]
        reasons.append(tr(lang, "reason_keep_stable", list=", ".join(labels)))

    return "\n".join(f"- {reason}" for reason in reasons)


def _build_reason_tooltip(picks, trait_upgrades, stable_traits, cap_opportunities,
                          score, avg_odds, avg_cost, spike_score, swap_out_names=None,
                          lang=DEFAULT_LANGUAGE):
    swap_out_names = swap_out_names or []
    lines = [
        tr(lang, "tooltip_total_scenario", score=f"{score:.2f}"),
        tr(lang, "tooltip_avg_odds", pct=f"{avg_odds * 100:.1f}"),
        tr(lang, "tooltip_avg_cost", value=f"{avg_cost:.2f}"),
        tr(lang, "tooltip_spike_score", value=f"{spike_score:.2f}"),
        "",
        tr(lang, "tooltip_details_per_unit"),
    ]
    if swap_out_names and picks:
        lines.insert(4, tr(lang, "reason_swap", out=", ".join(swap_out_names), in_=", ".join(p["name"] for p in picks)))
        lines.insert(5, "")
    for pick in picks:
        lines.append(
            f"- {pick['name']}: total={pick['score']:.2f} "
            f"(tier={pick['tier_score']:.2f}, traits={pick['trait_score']:.2f}, odds={pick['odds'] * 100:.1f}%)"
        )
        for detail in pick.get("trait_details", []):
            if detail["quality_gain"] <= 0 and detail["future_gain"] <= 0 and detail.get("bridge_bonus", 0) <= 0:
                continue
            curr = detail["current_tier_letter"] or "-"
            new = detail["new_tier_letter"] or "-"
            pot = detail["potential_tier_letter"] or new
            bridge_txt = ""
            if detail.get("bridge_bonus", 0) > 0 and detail.get("bridge_target"):
                needs_emblem = f" ({tr(lang, 'tooltip_needs_emblem')})" if detail.get("bridge_requires_emblem") else ""
                bridge_txt = (
                    f", bridge={detail['bridge_bonus']:.2f} -> "
                    f"{detail.get('bridge_target_letter') or '-'}@{detail['bridge_target']}{needs_emblem}"
                )
            lines.append(
                f"  {tr_trait(lang, detail['trait'])}: +{detail['delta_count']} ({curr} -> {new}), "
                f"gain={detail['quality_gain']:.2f}, cap={pot}, future={detail['future_gain']:.2f}{bridge_txt}"
            )

    if trait_upgrades:
        lines.append("")
        lines.append(tr(lang, "tooltip_trait_upgrades"))
        for delta in trait_upgrades[:6]:
            lines.append(
                f"- {tr_trait(lang, delta['name'])}: {delta['before_tier_letter'] or '-'} -> {delta['after_tier_letter'] or '-'}, "
                f"count {delta['before_count']} -> {delta['after_count']}"
            )
    if cap_opportunities:
        lines.append("")
        lines.append(tr(lang, "tooltip_cap_opportunities"))
        for cap in cap_opportunities[:5]:
            needs_emblem = f" ({tr(lang, 'tooltip_needs_emblem')})" if cap.get("potential_requires_emblem") else ""
            lines.append(
                f"- {tr_trait(lang, cap['trait'])}: now {cap['new_tier_letter'] or '-'} "
                f"-> potential {cap['potential_tier_letter'] or '-'} (future gain {cap['future_gain']:.2f}){needs_emblem}"
            )
    if stable_traits:
        lines.append("")
        lines.append(tr(lang, "tooltip_stable_traits"))
        for delta in stable_traits[:5]:
            lines.append(
                f"- {tr_trait(lang, delta['name'])}: tier {delta['after_tier_letter'] or '-'}, "
                f"count {delta['before_count']} -> {delta['after_count']}"
            )
    return "\n".join(lines)


def summarize_trait_entries(entries, limit=6):
    if not entries:
        return tr(DEFAULT_LANGUAGE, "tooltip_none")
    labels = [f"{e['name']} {e['count']}" for e in entries[:limit]]
    if len(entries) > limit:
        labels.append(f"+{len(entries) - limit}")
    return ", ".join(labels)


def compute_recommendation_scenarios(selected_names, team_size, unlocked_names, units,
                                     trait_thresholds, trait_tiers=None, weights=None, top_n=3,
                                     diversity=0.5, sort_mode="score", lang=DEFAULT_LANGUAGE,
                                     planning_extra_slots=0, emblem_potential_by_trait=None,
                                     max_swap_replacements=DEFAULT_MAX_SWAP_REPLACEMENTS,
                                     constraint_keep_units=None, constraint_avoid_units=None,
                                     constraint_force_traits=None):
    w = weights or DEFAULT_WEIGHTS
    all_units_map = {u["name"]: u for u in units}
    selected_names = _normalize_team_by_dependencies(selected_names)
    level = team_size
    slots = team_size - _team_slots_used(selected_names)
    keep_units = set(constraint_keep_units or []) & set(selected_names)
    avoid_units = set(constraint_avoid_units or []) - keep_units
    forced_traits = set(constraint_force_traits or []) & set(trait_thresholds.keys())

    tier_w = w.get("tier", 1.0)
    odds_w = w.get("odds", 1.0)
    score_cache = {}
    seed_scores_cache = {}
    team_traits_cache = {}

    def _team_traits_for(team_key):
        key = team_key if isinstance(team_key, frozenset) else frozenset(team_key)
        cached = team_traits_cache.get(key)
        if cached is not None:
            return cached
        traits = _compute_team_traits(key, all_units_map)
        team_traits_cache[key] = traits
        return traits

    def _score_unit(u, team):
        team_key = team if isinstance(team, frozenset) else frozenset(team)
        cache_key = (team_key, u["name"])
        if cache_key in score_cache:
            return score_cache[cache_key]
        if u["name"] in team_key:
            score_cache[cache_key] = None
            return None
        if u["name"] in avoid_units:
            score_cache[cache_key] = None
            return None
        if not _is_unit_unlocked_for_team(u, unlocked_names, team_key):
            score_cache[cache_key] = None
            return None
        if not _can_add_unit_to_team(u["name"], team_key):
            score_cache[cache_key] = None
            return None
        free_slots = max(0, team_size - _team_slots_used(team_key))
        candidate_slot_cost = _unit_slot_cost(u["name"])
        if candidate_slot_cost > free_slots:
            score_cache[cache_key] = None
            return None
        # Keep joker units for "team full" situations to avoid under-filling normal slots.
        if candidate_slot_cost == 0 and free_slots > 0:
            score_cache[cache_key] = None
            return None
        odds = get_roll_odds(level, u["cost"])
        if odds <= 0:
            score_cache[cache_key] = None
            return None
        tier_score = TIER_SCORES.get(u["tier"], 0) * tier_w
        trait_score, matching, trait_details = compute_trait_score(
            u, team_key, all_units_map, trait_thresholds, trait_tiers, unlocked_names, units, w, team_size,
            planning_extra_slots=planning_extra_slots,
            emblem_potential_by_trait=emblem_potential_by_trait,
        )
        raw_score = tier_score + trait_score
        if forced_traits:
            team_traits = _team_traits_for(team_key)
            forced_bonus = 0.0
            for trait_name in forced_traits:
                if trait_name not in u["traits"]:
                    continue
                forced_bonus += FORCED_TRAIT_BASE_BONUS
                current_count = team_traits.get(trait_name, 0)
                new_count = current_count + 1
                thresholds = trait_thresholds.get(trait_name, [])
                current_idx, _, _ = _get_trait_tier_state(current_count, thresholds)
                new_idx, _, _ = _get_trait_tier_state(new_count, thresholds)
                if new_idx > current_idx:
                    forced_bonus += FORCED_TRAIT_ACTIVATION_BONUS
            raw_score += forced_bonus
        # odds_w controls how much drop rate matters: 0=ignore odds, 1=full weight
        total = raw_score * (odds ** odds_w) if odds_w > 0 else raw_score
        entry = (total, tier_score, trait_score, odds, matching, trait_details, u)
        score_cache[cache_key] = entry
        return entry

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

    current_team_score = _compute_team_power_score(
        selected_names, all_units_map, trait_thresholds, trait_tiers, w
    )
    before_traits = _compute_team_traits(selected_names, all_units_map)

    def _collect_seed_scores(team):
        team_key = team if isinstance(team, frozenset) else frozenset(team)
        cached = seed_scores_cache.get(team_key)
        if cached is not None:
            return cached
        scores = []
        for unit in units:
            entry = _score_unit(unit, team_key)
            if entry:
                scores.append(entry)
        scores.sort(key=lambda x: -x[0])
        seed_scores_cache[team_key] = scores
        return scores

    seed_scores_now = _collect_seed_scores(selected_names)
    can_add_without_swap = bool(seed_scores_now)
    swap_mode = slots <= 0 and not can_add_without_swap
    slots_to_fill = 1 if (slots <= 0) else slots
    max_swaps = max(1, int(max_swap_replacements or 1))
    normal_seed_limit = max(12, top_n * 6)
    swap_seed_limit = max(4, min(SWAP_SEED_LIMIT, top_n * 2 + 2))
    if slots_to_fill <= 0:
        return []

    def _build_scenario(base_team, slots_target, seed_name=None, swap_out_names=None):
        used = set(base_team)
        picks = []
        swap_out_names = sorted(set(swap_out_names or []))
        if keep_units and any(name in keep_units for name in swap_out_names):
            return None
        blocked_names = set(swap_out_names)

        if seed_name is not None:
            if seed_name in blocked_names:
                return None
            seed_unit = all_units_map.get(seed_name)
            if seed_unit is None:
                return None
            seed_entry = _score_unit(seed_unit, used)
            if not seed_entry:
                return None
            picks.append(_to_pick(seed_entry))
            used.add(seed_name)

        while len(picks) < slots_target:
            best_entry = None
            for u in units:
                if u["name"] in used:
                    continue
                if u["name"] in blocked_names:
                    continue
                entry = _score_unit(u, used)
                if entry and (best_entry is None or entry[0] > best_entry[0]):
                    best_entry = entry
            if best_entry is None:
                break
            pick = _to_pick(best_entry)
            picks.append(pick)
            used.add(pick["name"])

        if len(picks) < slots_target:
            return None
        if not _team_dependencies_valid(used):
            return None

        after_traits = _compute_team_traits(used, all_units_map)
        if forced_traits:
            for trait_name in forced_traits:
                thresholds = trait_thresholds.get(trait_name, [])
                reached_idx, _, _ = _get_trait_tier_state(after_traits.get(trait_name, 0), thresholds)
                if reached_idx < 0:
                    return None
        projected_team_score = _compute_team_power_score(
            used, all_units_map, trait_thresholds, trait_tiers, w
        )
        team_score_delta = projected_team_score - current_team_score
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
        reason = _build_scenario_reason(
            picks, trait_upgrades, stable_traits, cap_opportunities,
            swap_out_names=swap_out_names, lang=lang
        )

        return {
            "score": total_score,
            "current_team_score": current_team_score,
            "projected_team_score": projected_team_score,
            "team_score_delta": team_score_delta,
            "avg_odds": avg_odds,
            "avg_cost": avg_cost,
            "total_cost": total_cost,
            "quality_gain": total_quality_gain,
            "future_gain": total_future_gain,
            "spike_score": spike_score,
            "pick_names": pick_names,
            "pick_set": set(pick_names),
            "swap_out_names": swap_out_names,
            "swap_out_set": set(swap_out_names),
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
                total_score, avg_odds, avg_cost, spike_score,
                swap_out_names=swap_out_names, lang=lang
            ),
        }

    scenarios = []
    seed_limit = swap_seed_limit if swap_mode else normal_seed_limit
    swap_scenario_budget = max(12, top_n * SWAP_SCENARIO_BUDGET_PER_TOP_RESULT)
    if swap_mode:
        selected_sorted = sorted([name for name in selected_names if name not in keep_units])
        max_swap_count = min(max_swaps, len(selected_sorted))
        budget_reached = False
        for swap_count in range(1, max_swap_count + 1):
            if budget_reached:
                break
            for swap_out_tuple in combinations(selected_sorted, swap_count):
                if budget_reached:
                    break
                swap_out_names = list(swap_out_tuple)
                base_team = set(selected_names) - set(swap_out_names)
                base_team = _normalize_team_by_dependencies(base_team)
                if not _team_dependencies_valid(base_team):
                    continue
                slots_to_refill = team_size - _team_slots_used(base_team)
                if slots_to_refill <= 0:
                    continue
                if slots_to_refill > max_swaps:
                    continue
                seed_scores = _collect_seed_scores(base_team)
                if not seed_scores:
                    continue
                seed_names = [None] + [entry[6]["name"] for entry in seed_scores[:seed_limit]]
                for seed_name in seed_names:
                    scenario = _build_scenario(
                        base_team, slots_to_refill, seed_name, swap_out_names=swap_out_names
                    )
                    if scenario:
                        scenarios.append(scenario)
                        if len(scenarios) >= swap_scenario_budget:
                            budget_reached = True
                            break
    else:
        if not seed_scores_now:
            return []
        seed_names = [None] + [entry[6]["name"] for entry in seed_scores_now[:seed_limit]]
        for seed_name in seed_names:
            scenario = _build_scenario(selected_names, slots_to_fill, seed_name)
            if scenario:
                scenarios.append(scenario)

    deduped = {}
    for scenario in scenarios:
        key = (tuple(sorted(scenario["pick_names"])), tuple(sorted(scenario.get("swap_out_names", []))))
        current = deduped.get(key)
        if current is None or scenario["score"] > current["score"]:
            deduped[key] = scenario

    unique_scenarios = list(deduped.values())
    if not unique_scenarios:
        return []

    def _style_value(scenario):
        swap_penalty = max(0, len(scenario.get("swap_out_names", [])) - 1) * 0.8
        if sort_mode == "roll":
            return scenario["avg_odds"] * 100 + scenario["future_gain"] * 0.8 + scenario["score"] * 0.04 - swap_penalty
        if sort_mode == "eco":
            return (6.0 - scenario["avg_cost"]) * 8 + scenario["avg_odds"] * 20 + scenario["score"] * 0.03 - swap_penalty
        if sort_mode == "spike":
            return (
                scenario["spike_score"] * 10
                + scenario["quality_gain"] * 1.5
                + scenario["future_gain"] * 1.2
                + len(scenario["trait_upgrades"]) * 2
                + scenario["score"] * 0.03
                - swap_penalty
            )
        return (
            scenario["score"]
            + scenario["quality_gain"] * 1.3
            + scenario["future_gain"] * 0.9
            + len(scenario["trait_upgrades"]) * 1.2
            + scenario["avg_odds"] * 5
            - swap_penalty
        )

    for scenario in unique_scenarios:
        scenario["style_value"] = _style_value(scenario)

    values = [s["style_value"] for s in unique_scenarios]
    value_span = max(values) - min(values)
    penalty_scale = value_span if value_span > 0 else max(1.0, abs(max(values)))

    def _overlap_ratio(a, b):
        a_tokens = a["pick_set"] | a.get("swap_out_set", set())
        b_tokens = b["pick_set"] | b.get("swap_out_set", set())
        inter = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
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

    # Keep variety in swap size: when max swap > 1, keep at least one 1-for-1 option if available.
    if swap_mode and max_swaps > 1 and selected:
        has_single_swap = any(len(s.get("swap_out_names", [])) == 1 for s in selected)
        single_candidates = [s for s in unique_scenarios if len(s.get("swap_out_names", [])) == 1]
        if single_candidates and not has_single_swap:
            best_single = max(single_candidates, key=lambda s: (s["style_value"], s["score"]))
            if best_single not in selected:
                best_single["style_rank_value"] = best_single.get("style_rank_value", best_single["style_value"])
                if len(selected) < top_n:
                    selected.append(best_single)
                else:
                    selected.sort(key=lambda s: (s.get("style_rank_value", s["style_value"]), s["score"]))
                    drop_index = 0
                    for i, candidate in enumerate(selected):
                        if len(candidate.get("swap_out_names", [])) > 1:
                            drop_index = i
                            break
                    selected.pop(drop_index)
                    selected.append(best_single)

    selected.sort(key=lambda s: (-s.get("style_rank_value", s["style_value"]), -s["score"]))
    return selected[:top_n]


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
        self.sort_mode = "default"  # default, cost, tier
        self.config_visible = False

        # Scoring weight variables (DoubleVar created after root exists)
        self.w_tier = tk.DoubleVar(value=1.0)
        self.w_traits = tk.DoubleVar(value=1.0)
        self.w_cap = tk.DoubleVar(value=0.8)
        self.w_odds = tk.DoubleVar(value=1.0)
        self.w_multi = tk.DoubleVar(value=1.0)
        self.w_bridge = tk.DoubleVar(value=1.0)
        self.scenario_diversity = tk.DoubleVar(value=0.5)
        self.planning_extra_slots = tk.IntVar(value=DEFAULT_PLANNING_EXTRA_SLOTS)
        self.constraints_enabled = tk.BooleanVar(value=False)
        self.constraints_keep_var = tk.StringVar(value="")
        self.constraints_avoid_var = tk.StringVar(value="")
        self.constraints_force_traits_var = tk.StringVar(value="")
        self.constraints_status_var = tk.StringVar(value="")
        self.constraint_keep_units = set()
        self.constraint_avoid_units = set()
        self.constraint_force_traits = set()
        # Max number of champions that can be replaced in one scenario.
        self.max_swap_replacements = DEFAULT_MAX_SWAP_REPLACEMENTS
        self.scenario_sort_mode = "score"
        self.lang_var = tk.StringVar(value=DEFAULT_LANGUAGE)
        self.scenario_sort_buttons = {}
        self.tooltip_window = None
        self.tooltip_label = None
        self.app_icon_image = None

        self._set_app_icon()
        self._load_images()
        self._build_ui()
        self._refresh()

        # Keyboard shortcuts
        self.root.bind("<Escape>", lambda _: self._reset_selection())

    def _t(self, key, **kwargs):
        return tr(self.lang_var.get(), key, **kwargs)

    def _trait_name(self, trait_name):
        return tr_trait(self.lang_var.get(), trait_name)

    def _item_name(self, item_or_slug):
        if isinstance(item_or_slug, dict):
            slug = item_or_slug.get("slug")
            fallback = item_or_slug.get("name", slug or "")
        else:
            slug = item_or_slug
            fallback = self.items_map.get(slug, {}).get("name", slug)
        return tr_item(self.lang_var.get(), slug, fallback)

    @staticmethod
    def _extract_emblem_trait(item):
        if not item or item.get("nature") != "emblem":
            return None
        name = (item.get("name") or "").strip()
        lower_name = name.lower()
        suffix = " emblem"
        if lower_name.endswith(suffix):
            return name[:len(name) - len(suffix)].strip()
        return None

    def _compute_emblem_potential_by_trait(self):
        """Estimate additional trait counts reachable from current emblem inventory/crafts."""
        owned_by_trait = defaultdict(int)
        craftable_by_trait = defaultdict(int)

        for slug, count in self.inventory_counts.items():
            if count <= 0:
                continue
            item = self.items_map.get(slug)
            trait = self._extract_emblem_trait(item)
            if trait:
                owned_by_trait[trait] += int(count)

        for i, comp_a in enumerate(self.component_slugs):
            row = self.component_matrix.get(comp_a, {})
            for comp_b in self.component_slugs[i:]:
                result = row.get(comp_b)
                if not result:
                    continue
                result_item = self.items_map.get(result.get("slug"))
                trait = self._extract_emblem_trait(result_item)
                if not trait:
                    continue
                if not self._can_craft_now(comp_a, comp_b):
                    continue
                craft_count = (
                    self.inventory_counts.get(comp_a, 0) // 2
                    if comp_a == comp_b
                    else min(self.inventory_counts.get(comp_a, 0), self.inventory_counts.get(comp_b, 0))
                )
                if craft_count > craftable_by_trait[trait]:
                    craftable_by_trait[trait] = craft_count

        merged = {}
        for trait_name in set(owned_by_trait) | set(craftable_by_trait):
            merged[trait_name] = owned_by_trait.get(trait_name, 0) + craftable_by_trait.get(trait_name, 0)
        return merged

    @staticmethod
    def _normalize_constraint_token(text):
        return "".join(ch for ch in str(text).lower() if ch.isalnum())

    def _build_constraint_maps(self):
        unit_map = {}
        for unit_name in self.units_map.keys():
            unit_map[self._normalize_constraint_token(unit_name)] = unit_name

        trait_map = {}
        for trait_name in self.trait_thresholds.keys():
            trait_map[self._normalize_constraint_token(trait_name)] = trait_name
            localized = self._trait_name(trait_name)
            trait_map[self._normalize_constraint_token(localized)] = trait_name
        return unit_map, trait_map

    def _parse_constraint_names(self, raw_text, option_map):
        names = set()
        unknown = []
        for token in re.split(r"[,;/|]+", raw_text or ""):
            token = token.strip()
            if not token:
                continue
            key = self._normalize_constraint_token(token)
            resolved = option_map.get(key)
            if resolved:
                names.add(resolved)
            else:
                unknown.append(token)
        return names, unknown

    def _constraints_are_active(self):
        if not self.constraints_enabled.get():
            return False
        return bool(self.constraint_keep_units or self.constraint_avoid_units or self.constraint_force_traits)

    def _sync_constraint_inputs_from_sets(self):
        self.constraints_keep_var.set(", ".join(sorted(self.constraint_keep_units)))
        self.constraints_avoid_var.set(", ".join(sorted(self.constraint_avoid_units)))
        forced_labels = [self._trait_name(name) for name in sorted(self.constraint_force_traits)]
        self.constraints_force_traits_var.set(", ".join(forced_labels))

    def _update_constraints_status(self, unknown_tokens=None):
        if not self.constraints_enabled.get():
            self.constraints_status_var.set(self._t("msg_constraints_disabled"))
            return
        status = self._t(
            "msg_constraints_applied",
            keep=len(self.constraint_keep_units),
            avoid=len(self.constraint_avoid_units),
            traits=len(self.constraint_force_traits),
        )
        unknown = [token for token in (unknown_tokens or []) if token]
        if unknown:
            status += " | " + self._t("msg_constraints_unknown", names=", ".join(unknown[:6]))
        self.constraints_status_var.set(status)

    def _unit_constraint_badge(self, unit_name):
        if not self.constraints_enabled.get():
            return ""
        if unit_name in self.constraint_keep_units:
            return " 🔒"
        if unit_name in self.constraint_avoid_units:
            return " ❌"
        return ""

    def _trait_constraint_badge(self, trait_name):
        if self.constraints_enabled.get() and trait_name in self.constraint_force_traits:
            return " 🔒"
        return ""

    def _display_unit_name(self, unit_name):
        return f"{unit_name}{self._unit_constraint_badge(unit_name)}"

    def _display_trait_name(self, trait_name):
        return f"{self._trait_name(trait_name)}{self._trait_constraint_badge(trait_name)}"

    def _toggle_unit_keep_constraint(self, unit_name):
        self.constraints_enabled.set(True)
        if unit_name in self.constraint_keep_units:
            self.constraint_keep_units.discard(unit_name)
        else:
            self.constraint_keep_units.add(unit_name)
            self.constraint_avoid_units.discard(unit_name)
        self._sync_constraint_inputs_from_sets()
        self._update_constraints_status()
        self._refresh()

    def _toggle_unit_avoid_constraint(self, unit_name):
        self.constraints_enabled.set(True)
        if unit_name in self.constraint_avoid_units:
            self.constraint_avoid_units.discard(unit_name)
        else:
            self.constraint_avoid_units.add(unit_name)
            self.constraint_keep_units.discard(unit_name)
        self._sync_constraint_inputs_from_sets()
        self._update_constraints_status()
        self._refresh()

    def _toggle_trait_force_constraint(self, trait_name):
        self.constraints_enabled.set(True)
        if trait_name in self.constraint_force_traits:
            self.constraint_force_traits.discard(trait_name)
        else:
            self.constraint_force_traits.add(trait_name)
        self._sync_constraint_inputs_from_sets()
        self._update_constraints_status()
        self._refresh()

    def _show_unit_constraints_menu(self, event, unit_name):
        menu = tk.Menu(self.root, tearoff=0)
        keep_var = tk.BooleanVar(value=self.constraints_enabled.get() and unit_name in self.constraint_keep_units)
        avoid_var = tk.BooleanVar(value=self.constraints_enabled.get() and unit_name in self.constraint_avoid_units)
        menu.add_checkbutton(
            label=self._t("menu_keep_champion"),
            variable=keep_var,
            command=lambda n=unit_name: self._toggle_unit_keep_constraint(n),
        )
        menu.add_checkbutton(
            label=self._t("menu_avoid_champion"),
            variable=avoid_var,
            command=lambda n=unit_name: self._toggle_unit_avoid_constraint(n),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_trait_constraints_menu(self, event, trait_name):
        menu = tk.Menu(self.root, tearoff=0)
        force_var = tk.BooleanVar(value=self.constraints_enabled.get() and trait_name in self.constraint_force_traits)
        menu.add_checkbutton(
            label=self._t("menu_force_trait"),
            variable=force_var,
            command=lambda t=trait_name: self._toggle_trait_force_constraint(t),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _apply_constraints_from_inputs(self, should_refresh=True):
        unit_map, trait_map = self._build_constraint_maps()
        keep_units, keep_unknown = self._parse_constraint_names(self.constraints_keep_var.get(), unit_map)
        avoid_units, avoid_unknown = self._parse_constraint_names(self.constraints_avoid_var.get(), unit_map)
        force_traits, trait_unknown = self._parse_constraint_names(self.constraints_force_traits_var.get(), trait_map)

        shared = keep_units & avoid_units
        if shared:
            avoid_units -= shared

        self.constraint_keep_units = keep_units
        self.constraint_avoid_units = avoid_units
        self.constraint_force_traits = force_traits

        unknown = keep_unknown + avoid_unknown + trait_unknown
        self._update_constraints_status(unknown_tokens=unknown)

        if should_refresh:
            self._refresh()

    def _clear_constraints(self):
        self.constraints_enabled.set(False)
        self.constraints_keep_var.set("")
        self.constraints_avoid_var.set("")
        self.constraints_force_traits_var.set("")
        self.constraint_keep_units.clear()
        self.constraint_avoid_units.clear()
        self.constraint_force_traits.clear()
        self._update_constraints_status()
        self._refresh()

    def _get_recommendation_constraints(self):
        if not self._constraints_are_active():
            return {
                "keep_units": set(),
                "avoid_units": set(),
                "force_traits": set(),
                "active": False,
            }
        keep_units = set(self.constraint_keep_units)
        avoid_units = set(self.constraint_avoid_units) - keep_units
        force_traits = set(self.constraint_force_traits)
        return {
            "keep_units": keep_units,
            "avoid_units": avoid_units,
            "force_traits": force_traits,
            "active": True,
        }

    def _on_language_change(self, *_):
        self._rebuild_ui_for_language()

    def _rebuild_ui_for_language(self):
        team_size = self.team_size_var.get() if hasattr(self, "team_size_var") else 6
        search_query = self.search_var.get() if hasattr(self, "search_var") else ""
        item_query = self.item_search_var.get() if hasattr(self, "item_search_var") else ""
        item_nature = self.item_nature_var.get() if hasattr(self, "item_nature_var") else "all"
        item_rank = self.item_rank_var.get() if hasattr(self, "item_rank_var") else "all"
        constraints_enabled = self.constraints_enabled.get()
        keep_raw = self.constraints_keep_var.get()
        avoid_raw = self.constraints_avoid_var.get()
        force_traits_raw = self.constraints_force_traits_var.get()
        was_config_visible = self.config_visible
        self.config_visible = False

        for child in self.root.winfo_children():
            child.destroy()

        self.unit_widgets = {}
        self.item_widgets = {}
        self.sort_buttons = {}
        self.scenario_sort_buttons = {}
        self.unlock_vars = {}

        self._build_ui()
        self.team_size_var.set(team_size)
        self.search_var.set(search_query)
        self.item_search_var.set(item_query)
        self.item_nature_var.set(item_nature)
        self.item_rank_var.set(item_rank)
        self.constraints_enabled.set(constraints_enabled)
        self.constraints_keep_var.set(keep_raw)
        self.constraints_avoid_var.set(avoid_raw)
        self.constraints_force_traits_var.set(force_traits_raw)
        self._apply_constraints_from_inputs(should_refresh=False)
        if was_config_visible:
            self._toggle_config()
        self._refresh()

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

        tk.Label(top, text=self._t("label_team_size"), bg="#2a2b2e", fg="white",
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

        tk.Button(top, text=self._t("button_reset"), bg="#ff5555", fg="white",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=2,
                  command=self._reset_selection).pack(side=tk.RIGHT, padx=(0, 12))

        tk.Button(top, text=self._t("button_config"), bg="#444", fg="white",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=10, pady=2,
                  command=self._toggle_config).pack(side=tk.RIGHT, padx=(0, 6))

        # Config panel (hidden by default)
        self.config_frame = tk.Frame(self.root, bg="#333", pady=8, padx=12)

        cfg_title = tk.Frame(self.config_frame, bg="#333")
        cfg_title.pack(fill=tk.X, pady=(0, 6))
        tk.Label(cfg_title, text=self._t("cfg_scoring_weights"), bg="#333", fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(cfg_title, text=self._t("button_reset_config"), bg="#555", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
                  command=self._reset_config).pack(side=tk.RIGHT)

        sliders_frame = tk.Frame(self.config_frame, bg="#333")
        sliders_frame.pack(fill=tk.X)

        slider_defs = [
            ("cfg_tier", self.w_tier, "cfg_tier_desc"),
            ("cfg_trait_quality", self.w_traits, "cfg_trait_quality_desc"),
            ("cfg_cap_potential", self.w_cap, "cfg_cap_potential_desc"),
            ("cfg_odds", self.w_odds, "cfg_odds_desc"),
            ("cfg_multi_synergy", self.w_multi, "cfg_multi_synergy_desc"),
            ("cfg_bridge", self.w_bridge, "cfg_bridge_desc"),
        ]
        for label_key, var, desc_key in slider_defs:
            sf = tk.Frame(sliders_frame, bg="#333")
            sf.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=8)
            tk.Label(sf, text=self._t(label_key), bg="#333", fg="#aaa",
                     font=("Segoe UI", 9, "bold")).pack()
            tk.Label(sf, text=self._t(desc_key), bg="#333", fg="#666",
                     font=("Segoe UI", 7)).pack()
            tk.Scale(sf, from_=0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                     variable=var, bg="#333", fg="white", highlightthickness=0,
                     troughcolor="#555", length=120,
                     command=lambda _: self._refresh()).pack()

        # Preset strategies
        presets_frame = tk.Frame(self.config_frame, bg="#333")
        presets_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(presets_frame, text=self._t("cfg_presets"), bg="#333", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))

        presets = [
            ("preset_balanced", {"tier": 1.0, "traits": 1.0, "cap_potential": 0.8, "odds": 1.0, "multi_synergy": 1.0, "bridge": 1.0}),
            ("preset_max_synergy", {"tier": 0.3, "traits": 2.0, "cap_potential": 1.4, "odds": 0.5, "multi_synergy": 2.0, "bridge": 1.6}),
            ("preset_brute_force", {"tier": 2.0, "traits": 0.5, "cap_potential": 0.2, "odds": 1.0, "multi_synergy": 0.3, "bridge": 0.2}),
            ("preset_ignore_odds", {"tier": 1.0, "traits": 1.0, "cap_potential": 0.8, "odds": 0.0, "multi_synergy": 1.0, "bridge": 1.0}),
        ]
        for name_key, values in presets:
            tk.Button(presets_frame, text=self._t(name_key), bg="#555", fg="white",
                      font=("Segoe UI", 8), relief=tk.FLAT, padx=8, pady=2,
                      command=lambda v=values: self._apply_preset(v)
                      ).pack(side=tk.LEFT, padx=2)

        scenario_cfg = tk.Frame(self.config_frame, bg="#333")
        scenario_cfg.pack(fill=tk.X, pady=(8, 0))
        tk.Label(scenario_cfg, text=self._t("cfg_scenario_diversity"), bg="#333", fg="#aaa",
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
        tk.Label(scenario_cfg, text=self._t("cfg_planning_slots"), bg="#333", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(14, 8))
        tk.Scale(
            scenario_cfg,
            from_=0,
            to=4,
            resolution=1,
            orient=tk.HORIZONTAL,
            variable=self.planning_extra_slots,
            bg="#333",
            fg="white",
            highlightthickness=0,
            troughcolor="#555",
            length=90,
            command=lambda _: self._refresh(),
        ).pack(side=tk.LEFT)

        constraints_cfg = tk.LabelFrame(
            self.config_frame,
            text=self._t("cfg_constraints"),
            bg="#333",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            bd=1,
            relief=tk.GROOVE,
            padx=8,
            pady=6,
        )
        constraints_cfg.pack(fill=tk.X, pady=(8, 0))

        constraints_toggle = tk.Checkbutton(
            constraints_cfg,
            text=self._t("cfg_constraints_enabled"),
            variable=self.constraints_enabled,
            bg="#333",
            fg="#ddd",
            selectcolor="#444",
            activebackground="#333",
            activeforeground="#fff",
            highlightthickness=0,
            command=lambda: self._apply_constraints_from_inputs(),
        )
        constraints_toggle.pack(anchor="w")

        keep_row = tk.Frame(constraints_cfg, bg="#333")
        keep_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(keep_row, text=self._t("cfg_constraints_keep_units"), bg="#333", fg="#aaa",
                 font=("Segoe UI", 8), width=16, anchor="w").pack(side=tk.LEFT)
        keep_entry = tk.Entry(
            keep_row,
            textvariable=self.constraints_keep_var,
            bg="#444",
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
        )
        keep_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        keep_entry.bind("<Return>", lambda _e: self._apply_constraints_from_inputs())

        avoid_row = tk.Frame(constraints_cfg, bg="#333")
        avoid_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(avoid_row, text=self._t("cfg_constraints_avoid_units"), bg="#333", fg="#aaa",
                 font=("Segoe UI", 8), width=16, anchor="w").pack(side=tk.LEFT)
        avoid_entry = tk.Entry(
            avoid_row,
            textvariable=self.constraints_avoid_var,
            bg="#444",
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
        )
        avoid_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        avoid_entry.bind("<Return>", lambda _e: self._apply_constraints_from_inputs())

        force_row = tk.Frame(constraints_cfg, bg="#333")
        force_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(force_row, text=self._t("cfg_constraints_force_traits"), bg="#333", fg="#aaa",
                 font=("Segoe UI", 8), width=16, anchor="w").pack(side=tk.LEFT)
        force_entry = tk.Entry(
            force_row,
            textvariable=self.constraints_force_traits_var,
            bg="#444",
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
        )
        force_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        force_entry.bind("<Return>", lambda _e: self._apply_constraints_from_inputs())

        constraints_buttons = tk.Frame(constraints_cfg, bg="#333")
        constraints_buttons.pack(fill=tk.X, pady=(5, 0))
        tk.Button(
            constraints_buttons,
            text=self._t("button_apply_constraints"),
            bg="#3b6f9e",
            fg="white",
            activebackground="#4a83b5",
            activeforeground="white",
            relief=tk.FLAT,
            padx=8,
            pady=1,
            command=self._apply_constraints_from_inputs,
        ).pack(side=tk.LEFT)
        tk.Button(
            constraints_buttons,
            text=self._t("button_clear_constraints"),
            bg="#555",
            fg="white",
            relief=tk.FLAT,
            padx=8,
            pady=1,
            command=self._clear_constraints,
        ).pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(
            constraints_cfg,
            text=self._t("cfg_constraints_hint"),
            bg="#333",
            fg="#666",
            font=("Segoe UI", 7, "italic"),
            anchor="w",
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(4, 0))
        if not self.constraints_status_var.get():
            self.constraints_status_var.set(self._t("msg_constraints_disabled"))
        tk.Label(
            constraints_cfg,
            textvariable=self.constraints_status_var,
            bg="#333",
            fg="#9fc7ff",
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        ).pack(fill=tk.X, pady=(4, 0))

        language_cfg = tk.Frame(self.config_frame, bg="#333")
        language_cfg.pack(fill=tk.X, pady=(8, 0))
        tk.Label(language_cfg, text=self._t("cfg_language"), bg="#333", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        language_box = ttk.Combobox(
            language_cfg,
            state="readonly",
            width=6,
            textvariable=self.lang_var,
            values=["en", "fr"],
        )
        language_box.pack(side=tk.LEFT)
        language_box.bind("<<ComboboxSelected>>", self._on_language_change)

        scenario_sort_frame = tk.Frame(self.config_frame, bg="#333")
        scenario_sort_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(scenario_sort_frame, text=self._t("cfg_scenario_style"), bg="#333", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        for mode, label_key in SCENARIO_SORT_MODES:
            btn = tk.Button(
                scenario_sort_frame,
                text=self._t(label_key),
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

        tk.Label(search_bar, text=self._t("search_label"), bg="#2a2b2e", fg="white",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_grid_filter())
        search_entry = tk.Entry(search_bar, textvariable=self.search_var, bg="#444", fg="white",
                                insertbackground="white", font=("Segoe UI", 10), width=25,
                                relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, padx=(8, 12))

        tk.Label(search_bar, text=self._t("search_hint"), bg="#2a2b2e", fg="#888",
                 font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT)

        # Sort buttons
        sort_frame = tk.Frame(search_bar, bg="#2a2b2e")
        sort_frame.pack(side=tk.RIGHT)

        tk.Label(sort_frame, text=self._t("sort_label"), bg="#2a2b2e", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))

        self.sort_buttons = {}
        for mode, label_key in [("default", "sort_default"), ("cost", "sort_cost"), ("tier", "sort_tier")]:
            btn = tk.Button(sort_frame, text=self._t(label_key), bg="#444", fg="white",
                            font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
                            command=lambda m=mode: self._set_sort(m))
            btn.pack(side=tk.LEFT, padx=1)
            self.sort_buttons[mode] = btn
        self._update_sort_buttons()

        # Main area
        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1d1e20",
                              sashwidth=4, sashrelief=tk.FLAT)
        main.pack(fill=tk.BOTH, expand=True)

        # Left: contextual panel (champions on unit tab, items on item tab)
        left_frame = tk.Frame(main, bg="#1d1e20")
        main.add(left_frame, stretch="always")
        self.left_stack = tk.Frame(left_frame, bg="#1d1e20")
        self.left_stack.pack(fill=tk.BOTH, expand=True)
        self.left_champion_view = tk.Frame(self.left_stack, bg="#1d1e20")
        self.left_item_view = tk.Frame(self.left_stack, bg="#1d1e20")

        self._build_left_champion_panel(self.left_champion_view)
        self._build_item_selector_panel(self.left_item_view)
        self.left_champion_view.pack(fill=tk.BOTH, expand=True)

        # Right panel: team + tabs (unit optimization / item optimization)
        right_panel = tk.Frame(main, bg="#1d1e20", width=620)
        main.add(right_panel, stretch="never")

        team_section = tk.LabelFrame(right_panel, text=self._t("section_my_team"), bg="#1d1e20", fg="white",
                                       font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                       labelanchor="n", padx=4, pady=4)
        team_section.pack(fill=tk.X, padx=4, pady=(4, 2))

        self.team_frame = tk.Frame(team_section, bg="#1d1e20")
        self.team_frame.pack(fill=tk.X)

        self.tabs = ttk.Notebook(right_panel)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))

        self.unit_tab = tk.Frame(self.tabs, bg="#1d1e20")
        self.item_tab = tk.Frame(self.tabs, bg="#1d1e20")
        self.tabs.add(self.unit_tab, text=self._t("tab_unit_opt"))
        self.tabs.add(self.item_tab, text=self._t("tab_item_opt"))

        # -- Unit tab: traits + recommendations --
        traits_section = tk.LabelFrame(self.unit_tab, text=self._t("section_active_traits"), bg="#1d1e20", fg="white",
                                       font=("Segoe UI", 11, "bold"), bd=1, relief=tk.GROOVE,
                                       labelanchor="n", padx=4, pady=4)
        traits_section.pack(fill=tk.X, padx=0, pady=0)

        self.traits_frame = tk.Frame(traits_section, bg="#1d1e20")
        self.traits_frame.pack(fill=tk.X)

        rec_section = tk.LabelFrame(self.unit_tab, text=self._t("section_top3"), bg="#1d1e20", fg="white",
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
        self._build_items_tab(self.item_tab)
        self.tabs.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._on_tab_changed()

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

            lbl_name = tk.Label(frame, text=self._display_unit_name(u["name"]), bg="#1d1e20", fg="white",
                                font=("Segoe UI", 7), wraplength=IMG_SIZE + 10)
            lbl_name.pack(fill=tk.X)

            self.unit_widgets[u["name"]] = (frame, lbl_img, lbl_name)

            for widget in (frame, lbl_img, lbl_name):
                widget.bind("<Button-1>", lambda e, name=u["name"]: self._toggle(name))
                widget.bind("<Button-3>", lambda e, name=u["name"]: self._show_unit_constraints_menu(e, name))

    def _build_locked_grid(self):
        for i, u in enumerate(self.locked_units):
            row, col = divmod(i, LOCKED_GRID_COLS)
            cost_color = COST_COLORS.get(u["cost"], "#888")
            frame = tk.Frame(self.locked_grid_frame, bg=cost_color, padx=2, pady=2,
                             bd=2, relief=tk.FLAT)
            frame.grid(row=row, column=col, padx=2, pady=2)

            var = tk.BooleanVar(value=u["name"] in self.unlocked)
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

            lbl_name = tk.Label(cb_frame, text=self._display_unit_name(u["name"]), bg="#1d1e20", fg="#666",
                                font=("Segoe UI", 7), wraplength=IMG_SIZE + 10, cursor="hand2")
            lbl_name.pack(side=tk.LEFT)

            self.unit_widgets[u["name"]] = (frame, lbl_img, lbl_name)

            for widget in (lbl_img, lbl_name):
                widget.bind("<Button-1>", lambda e, name=u["name"]: self._toggle_locked(name))
            for widget in (frame, cb_frame, lbl_img, lbl_name):
                widget.bind("<Button-3>", lambda e, name=u["name"]: self._show_unit_constraints_menu(e, name))

    def _build_left_champion_panel(self, parent):
        left_container = tk.Frame(parent, bg="#1d1e20")
        left_container.pack(fill=tk.BOTH, expand=True)

        left_canvas = tk.Canvas(left_container, bg="#1d1e20", highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient=tk.VERTICAL, command=left_canvas.yview)
        self.left_scroll_frame = tk.Frame(left_canvas, bg="#1d1e20")

        self.left_scroll_frame.bind(
            "<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        left_canvas.create_window((0, 0), window=self.left_scroll_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Normal champions section ---
        tk.Label(self.left_scroll_frame, text=self._t("section_champions"), bg="#1d1e20", fg="white",
                 font=("Segoe UI", 12, "bold"), pady=4).pack(anchor="w", padx=8)

        self.grid_frame = tk.Frame(self.left_scroll_frame, bg="#1d1e20")
        self.grid_frame.pack(fill=tk.X, padx=4, pady=4)
        self._build_champion_grid(self.normal_units, self.grid_frame, GRID_COLS)

        # --- Locked champions section ---
        sep = tk.Frame(self.left_scroll_frame, bg="#444", height=2)
        sep.pack(fill=tk.X, padx=8, pady=(8, 4))

        locked_header = tk.Frame(self.left_scroll_frame, bg="#1d1e20")
        locked_header.pack(fill=tk.X, padx=8)

        tk.Label(locked_header, text=self._t("section_locked_champions"), bg="#1d1e20", fg="#e8a33c",
                 font=("Segoe UI", 12, "bold"), pady=4).pack(side=tk.LEFT)

        btn_frame = tk.Frame(locked_header, bg="#1d1e20")
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text=self._t("button_unlock_all"), bg="#444", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2,
                  command=self._unlock_all).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text=self._t("button_lock_all"), bg="#444", fg="white",
                  font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2,
                  command=self._lock_all).pack(side=tk.LEFT, padx=2)

        self.locked_grid_frame = tk.Frame(self.left_scroll_frame, bg="#1d1e20")
        self.locked_grid_frame.pack(fill=tk.X, padx=4, pady=4)
        self._build_locked_grid()

        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _build_item_selector_panel(self, parent):
        filters = tk.Frame(parent, bg="#1d1e20", pady=4)
        filters.pack(fill=tk.X)

        tk.Label(filters, text=self._t("item_search_label"), bg="#1d1e20", fg="white",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.item_search_var = tk.StringVar()
        self.item_search_var.trace_add("write", lambda *_: self._refresh_item_grid_filter())
        tk.Entry(filters, textvariable=self.item_search_var, bg="#333", fg="white",
                 insertbackground="white", relief=tk.FLAT, width=18,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(6, 10))

        tk.Label(filters, text=self._t("item_category_label"), bg="#1d1e20", fg="#ccc",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.item_nature_var = tk.StringVar(value="all")
        nature_values = ["all", "component", "normal", "radiant", "artifact", "emblem", "trait"]
        nature_box = ttk.Combobox(filters, state="readonly", width=10,
                                  textvariable=self.item_nature_var, values=nature_values)
        nature_box.pack(side=tk.LEFT, padx=(6, 10))
        nature_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_item_grid_filter())

        tk.Label(filters, text=self._t("item_rank_label"), bg="#1d1e20", fg="#ccc",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.item_rank_var = tk.StringVar(value="all")
        rank_box = ttk.Combobox(filters, state="readonly", width=9,
                                textvariable=self.item_rank_var,
                                values=["all", "S", "A", "B", "C", "D", "unranked"])
        rank_box.pack(side=tk.LEFT, padx=(6, 10))
        rank_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_item_grid_filter())

        tk.Button(filters, text=self._t("button_reset_items"), bg="#444", fg="white",
                  relief=tk.FLAT, padx=8, pady=1,
                  command=self._reset_inventory).pack(side=tk.RIGHT)
        tk.Label(filters, text=self._t("item_click_hint"),
                 bg="#1d1e20", fg="#777", font=("Segoe UI", 8, "italic")).pack(side=tk.RIGHT, padx=(0, 10))

        selector = tk.Frame(parent, bg="#1d1e20")
        selector.pack(fill=tk.BOTH, expand=True)
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

        self._build_item_grid()
        self._refresh_item_grid_filter()

    def _build_items_tab(self, parent):
        insights = tk.Frame(parent, bg="#1d1e20")
        insights.pack(fill=tk.BOTH, expand=True)

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

        self._refresh_items_tab()

    def _on_tab_changed(self, _event=None):
        current_tab = self.tabs.select()
        if current_tab == str(self.item_tab):
            self.left_champion_view.pack_forget()
            self.left_item_view.pack(fill=tk.BOTH, expand=True)
            self._refresh_item_grid_filter()
        else:
            self.left_item_view.pack_forget()
            self.left_champion_view.pack(fill=tk.BOTH, expand=True)

    def _build_item_grid(self):
        ordered = sorted(
            self.items,
            key=lambda i: (ITEM_NATURE_ORDER.get(i.get("nature"), 99), self._item_name(i)),
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

            name_lbl = tk.Label(card, text=self._item_name(item), bg="#1d1e20", fg="white",
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
            self.item_action_message = self._t("msg_no_slot_for_item", item=self._item_name(item))
            return False
        self.inventory_counts[item_slug] -= 1
        if self.inventory_counts[item_slug] <= 0:
            self.inventory_counts.pop(item_slug, None)
        self.equipped_items.setdefault(holder, []).append(item_slug)
        self.item_action_message = self._t("msg_item_equipped_on", item=self._item_name(item), holder=holder)
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
            self.item_action_message = self._t("msg_craft_then_equip", item=self._item_name(item), holder=holder)
        else:
            self.inventory_counts[result_slug] = self.inventory_counts.get(result_slug, 0) + 1
            self.item_action_message = self._t("msg_craft_to_inventory_no_slot", item=self._item_name(item))
        return True

    def _craft_option(self, option):
        preferred = option.get("holders", [])
        crafted = self._craft_from_components(option["a"], option["b"], preferred)
        if not crafted:
            self.item_action_message = self._t("msg_craft_impossible_current_inventory")
        self._refresh()

    def _craft_option_for_holder(self, option, holder_name):
        if holder_name not in self.selected:
            self.item_action_message = self._t("msg_holder_not_in_team", holder=holder_name)
            self._refresh()
            return
        if len(self.equipped_items.get(holder_name, [])) >= MAX_ITEMS_PER_UNIT:
            self.item_action_message = self._t("msg_holder_max_items", holder=holder_name, max_items=MAX_ITEMS_PER_UNIT)
            self._refresh()
            return
        crafted = self._craft_from_components(option["a"], option["b"], [holder_name])
        if not crafted:
            self.item_action_message = self._t("msg_craft_impossible_current_inventory")
        self._refresh()

    def _equip_option(self, item_slug, holders=None):
        if not self.selected:
            self.item_action_message = self._t("msg_select_team_before_equip")
            self._refresh()
            return
        if not self._equip_from_inventory(item_slug, holders):
            if not self.item_action_message:
                self.item_action_message = self._t("msg_equip_impossible")
        self._refresh()

    def _unequip_item(self, unit_name, slot_idx):
        equipped = self.equipped_items.get(unit_name, [])
        if slot_idx < 0 or slot_idx >= len(equipped):
            return
        item_slug = equipped.pop(slot_idx)
        if not equipped:
            self.equipped_items.pop(unit_name, None)
        self.inventory_counts[item_slug] = self.inventory_counts.get(item_slug, 0) + 1
        item_name = self._item_name(item_slug)
        self.item_action_message = self._t("msg_item_removed_from", item=item_name, holder=unit_name)
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
        options.sort(key=lambda x: (-x["score"], self._item_name(x["result"])))
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
        if q in self._item_name(item).lower():
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
        self.item_action_message = self._t("msg_inventory_and_equipment_reset")
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
        selected_items.sort(key=lambda i: (ITEM_NATURE_ORDER.get(i.get("nature"), 99), self._item_name(i)))
        team_names = sorted(self.selected)

        tk.Label(
            self.item_insight_frame,
            text=self._t("msg_holder_relevance_legend"),
            bg="#1d1e20",
            fg="#9fc7ff",
            font=("Segoe UI", 8, "italic"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=285,
        ).pack(fill=tk.X, pady=(0, 4))

        inv_section = tk.LabelFrame(self.item_insight_frame, text=self._t("section_inventory"), bg="#1d1e20", fg="white",
                                    font=("Segoe UI", 9, "bold"), bd=1, relief=tk.GROOVE, padx=4, pady=4)
        inv_section.pack(fill=tk.X, pady=(0, 4))

        if not selected_items:
            tk.Label(inv_section, text=self._t("msg_click_items_to_add"),
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 8)).pack(anchor="w")
        else:
            for item in selected_items:
                slug = item["slug"]
                row = tk.Frame(inv_section, bg="#1d1e20")
                row.pack(fill=tk.X, pady=1)
                icon = self.item_inv_images.get(slug)
                tk.Label(row, image=icon, bg="#1d1e20").pack(side=tk.LEFT, padx=(0, 4))
                tk.Label(row, text=f"x{self.inventory_counts[slug]}  {self._item_name(item)}",
                         bg="#1d1e20", fg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT)
                tk.Button(row, text="-", bg="#444", fg="white", relief=tk.FLAT, width=2,
                          command=lambda s=slug: self._toggle_item(s, -1)).pack(side=tk.RIGHT, padx=(2, 0))
                tk.Button(row, text="+", bg="#444", fg="white", relief=tk.FLAT, width=2,
                          command=lambda s=slug: self._toggle_item(s, +1)).pack(side=tk.RIGHT)

        equip_section = tk.LabelFrame(self.item_insight_frame, text=self._t("section_best_holders_completed"),
                                      bg="#1d1e20", fg="white", font=("Segoe UI", 9, "bold"),
                                      bd=1, relief=tk.GROOVE, padx=4, pady=4)
        equip_section.pack(fill=tk.X, pady=(0, 4))

        completed = [i for i in selected_items if i.get("nature") != "component"]
        if not completed:
            tk.Label(equip_section, text=self._t("msg_no_completed_item_selected"),
                     bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")
        elif not team_names:
            tk.Label(equip_section, text=self._t("msg_select_team_for_holder_advice"),
                     bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")
        else:
            completed_scores = []
            for item in completed:
                score, holders = self._item_team_score(item, team_names)
                completed_scores.append((score, item, holders))
            completed_scores.sort(key=lambda x: (-x[0], self._item_name(x[1])))
            for _, item, holders in completed_scores:
                slug = item["slug"]
                qty = self.inventory_counts.get(slug, 0)
                row = tk.Frame(equip_section, bg="#1d1e20")
                row.pack(fill=tk.X, pady=1)

                tk.Button(
                    row,
                    text=self._t("button_equip_best"),
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
                    text=f"x{qty} {self._item_name(item)} ({rank})",
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
                        text=self._t("msg_no_holder_suggestion"),
                        bg="#1d1e20",
                        fg="#777",
                        font=("Segoe UI", 8),
                    ).pack(anchor="w")

                for widget in (icon_lbl, title_lbl):
                    widget.bind("<Button-1>", lambda e, s=slug, h=holders: self._equip_option(s, h))

        component_section = tk.LabelFrame(self.item_insight_frame, text=self._t("section_component_decisions"),
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
            tk.Label(component_section, text=self._t("msg_no_component_selected"), bg="#1d1e20",
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
                options.sort(key=lambda x: (-x["score"], self._item_name(x["result_item"])))
                best_overall = options[0]
                best_now = next((o for o in options if o["craft_now"]), None)
                component_best[comp_slug] = best_overall

                block = tk.Frame(component_section, bg="#1d1e20")
                block.pack(fill=tk.X, pady=2)
                tk.Label(block, image=self.item_inv_images.get(comp_slug), bg="#1d1e20").pack(side=tk.LEFT, padx=(0, 4))
                qty = self.inventory_counts.get(comp_slug, 0)
                tk.Label(block, text=f"{self._item_name(comp)} x{qty}", bg="#1d1e20", fg="white",
                         font=("Segoe UI", 8, "bold")).pack(anchor="w")

                if best_now:
                    partner_name = self._item_name(best_now["partner_slug"])
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
                        text=self._t(
                            "msg_craft_now_with",
                            partner=partner_name,
                            item=self._item_name(best_now["result_item"]),
                            rank=rank,
                        ),
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
                    tk.Label(block, text=self._t("msg_no_immediate_craft_current_inventory"),
                             bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")

                if (not best_overall["craft_now"]) or (best_now and best_overall["score"] > best_now["score"] + 8):
                    partner_name = self._item_name(best_overall["partner_slug"])
                    rank = (best_overall["result_item"].get("rank") or "?").upper()
                    wait_row = tk.Frame(block, bg="#1d1e20")
                    wait_row.pack(fill=tk.X)
                    tk.Label(
                        wait_row,
                        text=self._t(
                            "msg_better_to_wait_for",
                            partner=partner_name,
                            item=self._item_name(best_overall["result_item"]),
                            rank=rank,
                        ),
                        bg="#1d1e20",
                        fg="#e8a33c",
                        font=("Segoe UI", 8),
                        wraplength=250,
                        justify=tk.LEFT,
                        anchor="w",
                    ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                    self._render_holder_icons(wait_row, best_overall["holders"])

        craft_section = tk.LabelFrame(self.item_insight_frame, text=self._t("section_immediate_crafts"),
                                      bg="#1d1e20", fg="white", font=("Segoe UI", 9, "bold"),
                                      bd=1, relief=tk.GROOVE, padx=4, pady=4)
        craft_section.pack(fill=tk.X, pady=(0, 4))

        craft_options = self._current_craft_options(team_names)
        if not craft_options:
            tk.Label(craft_section, text=self._t("msg_no_craft_possible"),
                     bg="#1d1e20", fg="#777", font=("Segoe UI", 8)).pack(anchor="w")
        else:
            for opt in craft_options[:10]:
                res = opt["result"]
                rank = (res.get("rank") or "?").upper()
                comp_a_name = self._item_name(opt["a"])
                comp_b_name = self._item_name(opt["b"])

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
                    text=self._t(
                        "msg_immediate_craft_line",
                        item=self._item_name(res),
                        rank=rank,
                        comp_a=comp_a_name,
                        comp_b=comp_b_name,
                        count=opt["craft_count"],
                    ),
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
                        text=self._t("msg_low_value_waiting_stronger"),
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
        self.w_tier.set(values.get("tier", self.w_tier.get()))
        self.w_traits.set(values.get("traits", self.w_traits.get()))
        self.w_cap.set(values.get("cap_potential", self.w_cap.get()))
        self.w_odds.set(values.get("odds", self.w_odds.get()))
        self.w_multi.set(values.get("multi_synergy", self.w_multi.get()))
        self.w_bridge.set(values.get("bridge", self.w_bridge.get()))
        self._refresh()

    def _reset_config(self):
        self._apply_preset(DEFAULT_WEIGHTS)
        self.scenario_diversity.set(0.5)
        self.planning_extra_slots.set(DEFAULT_PLANNING_EXTRA_SLOTS)
        self.max_swap_replacements = DEFAULT_MAX_SWAP_REPLACEMENTS
        self.constraints_enabled.set(False)
        self.constraints_keep_var.set("")
        self.constraints_avoid_var.set("")
        self.constraints_force_traits_var.set("")
        self.constraint_keep_units.clear()
        self.constraint_avoid_units.clear()
        self.constraint_force_traits.clear()
        self.constraints_status_var.set(self._t("msg_constraints_disabled"))
        self._set_scenario_sort("score")

    def _get_weights(self):
        return {
            "tier": self.w_tier.get(),
            "traits": self.w_traits.get(),
            "cap_potential": self.w_cap.get(),
            "odds": self.w_odds.get(),
            "multi_synergy": self.w_multi.get(),
            "bridge": self.w_bridge.get(),
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

    def _current_team_slots(self):
        return _team_slots_used(self.selected)

    def _is_unit_available_for_selection(self, name):
        unit = self.units_map.get(name)
        if not unit:
            return False
        return _is_unit_unlocked_for_team(unit, self.unlocked, self.selected)

    def _can_add_unit_to_current_team(self, name):
        if name in self.selected:
            return True
        unit = self.units_map.get(name)
        if not unit:
            return False
        if not self._is_unit_available_for_selection(name):
            return False
        trial = set(self.selected)
        trial.add(name)
        if not _team_dependencies_valid(trial):
            return False
        return _team_slots_used(trial) <= self.team_size_var.get()

    def _normalize_selected_team(self, team_size):
        self.selected = _normalize_team_by_dependencies(self.selected)
        while _team_slots_used(self.selected) > team_size and self.selected:
            to_remove = self._pick_unit_to_remove(self.selected, team_size)
            if not to_remove:
                break
            self.selected.discard(to_remove)
            self.selected = _normalize_team_by_dependencies(self.selected)

    def _pick_unit_to_remove(self, team_names, team_size):
        team_set = set(team_names)
        current_slots = _team_slots_used(team_set)
        if current_slots <= team_size:
            return None

        protected_units = set()
        if self._constraints_are_active():
            protected_units = set(self.constraint_keep_units) & team_set
        candidate = self._pick_unit_to_remove_candidate(team_set, team_size, protected_units)
        if candidate is not None:
            return candidate
        if protected_units:
            return self._pick_unit_to_remove_candidate(team_set, team_size, set())
        return None

    def _pick_unit_to_remove_candidate(self, team_set, team_size, protected_units):
        current_slots = _team_slots_used(team_set)
        candidates = []
        for unit_name in sorted(team_set):
            if _unit_slot_cost(unit_name) <= 0:
                continue
            if unit_name in protected_units:
                continue
            trial = set(team_set)
            trial.discard(unit_name)
            trial = _normalize_team_by_dependencies(trial)
            trial_slots = _team_slots_used(trial)
            if trial_slots >= current_slots:
                continue

            unit = self.units_map.get(unit_name, {})
            tier_value = TIER_SCORES.get((unit.get("tier") or "").upper(), 0)
            cost_value = int(unit.get("cost", 0) or 0)
            removal_count = len(team_set) - len(trial)
            overflow_after = max(0, trial_slots - team_size)

            candidates.append((
                overflow_after,
                removal_count,
                tier_value,
                cost_value,
                unit_name,
            ))

        if not candidates:
            return None
        return min(candidates)[-1]

    def _on_unlock_toggle(self, name):
        if self.unlock_vars[name].get():
            self.unlocked.add(name)
        else:
            self.unlocked.discard(name)
            if name in self.selected:
                self.selected.discard(name)
                self.selected = _normalize_team_by_dependencies(self.selected)
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
        if name not in self.selected and not self._can_add_unit_to_current_team(name):
            return
        if name not in self.selected and not self._is_unit_available_for_selection(name):
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
            if q in self._trait_name(t).lower():
                return True
        return False

    def _reset_selection(self):
        self.selected.clear()
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
        if name in self.selected:
            self.selected.remove(name)
            self.selected = _normalize_team_by_dependencies(self.selected)
        else:
            if self._can_add_unit_to_current_team(name):
                self.selected.add(name)
        self._refresh()

    def _apply_scenario(self, scenario):
        team_size = self.team_size_var.get()
        for name in scenario.get("swap_out_names", []):
            self.selected.discard(name)
        self.selected = _normalize_team_by_dependencies(self.selected)
        for name in scenario["pick_names"]:
            if name in self.selected:
                continue
            unit = self.units_map.get(name)
            if not unit:
                continue
            if not _is_unit_unlocked_for_team(unit, self.unlocked, self.selected):
                continue
            trial = set(self.selected)
            trial.add(name)
            if not _team_dependencies_valid(trial):
                continue
            if _team_slots_used(trial) > team_size:
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
            tk.Label(self.team_frame, text=self._t("msg_click_champion_to_add"),
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 9)).pack(pady=8)
            return

        row_frame = tk.Frame(self.team_frame, bg="#1d1e20")
        row_frame.pack(pady=4)

        def _render_team_unit(parent, unit_name):
            unit = self.units_map[unit_name]
            slot = tk.Frame(parent, bg="#1d1e20", padx=2, cursor="hand2")
            slot.pack(side=tk.LEFT, padx=2)

            img = self.team_images.get(unit_name)
            tier_color = TIER_COLORS.get(unit["tier"], "#333")
            lbl_img = tk.Label(slot, image=img, bg=tier_color, bd=2, relief=tk.RAISED)
            lbl_img.pack()

            lbl_name = tk.Label(slot, text=self._display_unit_name(unit_name), bg="#1d1e20", fg="white",
                                font=("Segoe UI", 7), wraplength=TEAM_IMG_SIZE + 10)
            lbl_name.pack()

            equipped_row = tk.Frame(slot, bg="#1d1e20")
            equipped_row.pack(pady=(2, 0))
            equipped = self.equipped_items.get(unit_name, [])
            for idx in range(MAX_ITEMS_PER_UNIT):
                if idx < len(equipped):
                    item_slug = equipped[idx]
                    icon = self.team_item_images.get(item_slug)
                    item_lbl = tk.Label(equipped_row, image=icon, bg="#1d1e20", cursor="hand2")
                    item_lbl.pack(side=tk.LEFT, padx=1)
                    item_lbl.bind("<Button-1>", lambda e, n=unit_name, i=idx: self._on_team_item_click(n, i))
                else:
                    tk.Label(equipped_row, text="", bg="#333", width=2, height=1,
                             relief=tk.SUNKEN, bd=1).pack(side=tk.LEFT, padx=1)

            for w in (slot, lbl_img, lbl_name):
                w.bind("<Button-1>", lambda e, n=unit_name: self._toggle(n))
                w.bind("<Button-3>", lambda e, n=unit_name: self._show_unit_constraints_menu(e, n))

        normal_team_units = sorted([name for name in self.selected if _unit_category(name) != "joker"])
        joker_team_units = sorted([name for name in self.selected if _unit_category(name) == "joker"])

        for name in normal_team_units:
            _render_team_unit(row_frame, name)

        empty = max(0, team_size - _team_slots_used(self.selected))
        for _ in range(empty):
            slot = tk.Frame(row_frame, bg="#1d1e20", padx=2)
            slot.pack(side=tk.LEFT, padx=2)
            tk.Label(slot, text="", width=TEAM_IMG_SIZE // 8, height=TEAM_IMG_SIZE // 16,
                     bg="#333", bd=2, relief=tk.SUNKEN).pack()
            tk.Label(slot, text="?", bg="#1d1e20", fg="#555",
                     font=("Segoe UI", 7)).pack()

        if joker_team_units:
            tk.Label(self.team_frame, text=self._t("label_joker_units"),
                     bg="#1d1e20", fg="#e8a33c", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=6, pady=(4, 0))
            joker_row = tk.Frame(self.team_frame, bg="#1d1e20")
            joker_row.pack(anchor="w", pady=(2, 0))
            for name in joker_team_units:
                _render_team_unit(joker_row, name)

    def _refresh_traits(self):
        for w in self.traits_frame.winfo_children():
            w.destroy()

        active = self._get_active_traits()
        if not active:
            tk.Label(self.traits_frame, text=self._t("msg_no_active_traits"),
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
        icon_lbl = None
        if icon:
            icon_lbl = tk.Label(row, image=icon, bg=row_bg)
            icon_lbl.pack(side=tk.LEFT, padx=(0, 6))

        trait_lbl = tk.Label(row, text=self._display_trait_name(trait_name), bg=row_bg, fg=color,
                             font=("Segoe UI", 9, "bold"), anchor="w")
        trait_lbl.pack(side=tk.LEFT)

        progress = progress_text if progress_text is not None else self._format_trait_progress(trait_name, count)
        progress_lbl = tk.Label(row, text=progress, bg=row_bg, fg=color,
                                font=("Segoe UI", 8))
        progress_lbl.pack(side=tk.RIGHT)

        widgets = [row, trait_lbl, progress_lbl]
        if icon_lbl is not None:
            widgets.append(icon_lbl)
        for widget in widgets:
            widget.bind("<Button-3>", lambda e, t=trait_name: self._show_trait_constraints_menu(e, t))

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

        self._normalize_selected_team(team_size)
        self._sync_equipped_with_team()

        self.selection_count_label.config(text=self._t("selection_count", selected=self._current_team_slots(), total=team_size))

        # Compute recommendation scenarios first (needed for grid highlight)
        weights = self._get_weights()
        emblem_potential = self._compute_emblem_potential_by_trait()
        constraints = self._get_recommendation_constraints()
        scenarios = compute_recommendation_scenarios(
            self.selected, team_size, self.unlocked,
            self.units, self.trait_thresholds, self.trait_tiers, weights, top_n=3,
            diversity=self.scenario_diversity.get(),
            sort_mode=self.scenario_sort_mode,
            lang=self.lang_var.get(),
            planning_extra_slots=self.planning_extra_slots.get(),
            emblem_potential_by_trait=emblem_potential,
            max_swap_replacements=self.max_swap_replacements,
            constraint_keep_units=constraints["keep_units"],
            constraint_avoid_units=constraints["avoid_units"],
            constraint_force_traits=constraints["force_traits"],
        )
        self.recommended_names = {
            name for scenario in scenarios for name in scenario["pick_names"]
        }

        # Update normal grid visuals
        for u in self.normal_units:
            frame, lbl_img, lbl_name = self.unit_widgets[u["name"]]
            cost_color = COST_COLORS.get(u["cost"], "#888")
            lbl_name.config(text=self._display_unit_name(u["name"]))
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
            lbl_name.config(text=self._display_unit_name(u["name"]))
            can_be_added = self._can_add_unit_to_current_team(u["name"])
            is_unlocked = _is_unit_unlocked_for_team(u, self.unlocked, self.selected) and (
                u["name"] in self.selected or can_be_added
            )
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

        current_team_score = _compute_team_power_score(
            self.selected, self.units_map, self.trait_thresholds, self.trait_tiers, weights
        )

        if not scenarios:
            tk.Label(
                self.rec_frame,
                text=self._t("label_current_team_score", score=f"{current_team_score:.1f}"),
                bg="#1d1e20",
                fg="#9fc7ff",
                font=("Segoe UI", 9, "bold"),
            ).pack(pady=(12, 6))
            if constraints["active"]:
                msg = self._t("msg_no_scenario_with_constraints")
            else:
                msg = self._t("msg_team_full") if self._current_team_slots() >= team_size else \
                      self._t("msg_select_champions_and_adjust")
            tk.Label(self.rec_frame, text=msg,
                     bg="#1d1e20", fg="#888", font=("Segoe UI", 10)).pack(pady=20)
            return

        for col in range(3):
            self.rec_frame.grid_columnconfigure(col, weight=1)

        top_delta = max((s.get("team_score_delta", 0.0) for s in scenarios), default=0.0)
        summary_text = self._t("label_current_team_score", score=f"{current_team_score:.1f}")
        if top_delta <= 0:
            summary_text += f"  |  {self._t('msg_current_team_already_best')}"
        tk.Label(
            self.rec_frame,
            text=summary_text,
            bg="#1d1e20",
            fg="#9fc7ff" if top_delta > 0 else "#e8a33c",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            justify=tk.LEFT,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 8))

        for col in range(3):
            scenario = scenarios[col] if col < len(scenarios) else None

            card = tk.Frame(self.rec_frame, bg="#2a2b2e", pady=6, padx=8, bd=1, relief=tk.RIDGE)
            card.grid(row=1, column=col, sticky="nsew", padx=3, pady=3)

            if scenario is None:
                tk.Label(card, text=self._t("label_scenario_num", index=col + 1), bg="#2a2b2e", fg="#777",
                         font=("Segoe UI", 10, "bold")).pack(anchor="w")
                tk.Label(card, text=self._t("label_unavailable"), bg="#2a2b2e", fg="#777",
                         font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
                continue

            header = tk.Frame(card, bg="#2a2b2e")
            header.pack(fill=tk.X)

            tk.Label(header, text=self._t("label_scenario_num", index=col + 1), bg="#2a2b2e", fg="white",
                     font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
            tk.Label(header, text=self._t("label_score_pts", score=f"{scenario['score']:.1f}"), bg="#2a2b2e", fg="#aaa",
                     font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 0))
            tk.Label(header, text=self._t("label_roll_pct", pct=int(scenario['avg_odds'] * 100)), bg="#2a2b2e", fg="#aaa",
                     font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(6, 0))
            tk.Button(
                header,
                text=self._t("button_apply"),
                bg="#3b6f9e",
                fg="white",
                activebackground="#4a83b5",
                activeforeground="white",
                relief=tk.FLAT,
                padx=6,
                pady=1,
                command=lambda s=scenario: self._apply_scenario(s),
            ).pack(side=tk.RIGHT)

            projected = scenario.get("projected_team_score", current_team_score)
            delta = scenario.get("team_score_delta", projected - current_team_score)
            delta_txt = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
            delta_color = "#8fd19e" if delta > 0 else ("#d98f8f" if delta < 0 else "#aaa")
            tk.Label(
                card,
                text=self._t("label_projected_team_score", score=f"{projected:.1f}", delta=delta_txt),
                bg="#2a2b2e",
                fg=delta_color,
                font=("Segoe UI", 8, "bold"),
                anchor="w",
                justify=tk.LEFT,
            ).pack(fill=tk.X, pady=(3, 2))

            reason_label = tk.Label(
                card,
                text=self._t("label_why_prefix") + "\n" + scenario["reason"],
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

            swap_names = scenario.get("swap_out_names", [])
            if swap_names:
                swap_title = tk.Label(
                    card,
                    text=self._t("section_suggested_remplacement"),
                    bg="#2a2b2e",
                    fg="#ff9b9b",
                    font=("Segoe UI", 8, "bold"),
                    anchor="w",
                )
                swap_title.pack(fill=tk.X, pady=(3, 1))
                for unit_name in swap_names:
                    unit_icon = self.rec_pick_images.get(unit_name)
                    swap_badge = tk.Label(
                        card,
                        text=f" {unit_name}",
                        image=unit_icon,
                        compound=tk.LEFT,
                        bg="#7a2f2f",
                        fg="white",
                        font=("Segoe UI", 8, "bold"),
                        padx=4,
                        pady=2,
                        anchor="w",
                    )
                    swap_badge.pack(fill=tk.X, pady=(1, 2))

            picks_title = tk.Label(card, text=self._t("section_proposed_additions"), bg="#2a2b2e", fg="#9fc7ff",
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

            compare_title = tk.Label(card, text=self._t("section_trait_upgrades_net_gain"),
                                     bg="#2a2b2e", fg="#9fc7ff",
                                     font=("Segoe UI", 8, "bold"), anchor="w")
            compare_title.pack(fill=tk.X, pady=(6, 2))

            upgrade_box = tk.Frame(card, bg="#1d1e20")
            upgrade_box.pack(fill=tk.X)
            if scenario["trait_upgrades"]:
                for delta in scenario["trait_upgrades"][:4]:
                    self._render_trait_delta_row(upgrade_box, delta, is_upgrade=True)
            else:
                tk.Label(upgrade_box, text=self._t("msg_no_tier_upgrade"), bg="#1d1e20", fg="#777",
                         font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=2)

            cap_title = tk.Label(card, text=self._t("section_cap_potential"),
                                 bg="#2a2b2e", fg="#9fc7ff",
                                 font=("Segoe UI", 8, "bold"), anchor="w")
            cap_title.pack(fill=tk.X, pady=(6, 2))

            cap_box = tk.Frame(card, bg="#1d1e20")
            cap_box.pack(fill=tk.X)
            if scenario["cap_opportunities"]:
                for cap in scenario["cap_opportunities"][:3]:
                    txt = (
                        f"{self._trait_name(cap['trait'])}: {cap['new_tier_letter'] or '-'} -> "
                        f"{cap['potential_tier_letter'] or '-'} (+{cap['future_gain']:.1f})"
                    )
                    tk.Label(cap_box, text=txt, bg="#1d1e20", fg="#8bc5ff",
                             font=("Segoe UI", 8), anchor="w").pack(fill=tk.X, padx=6, pady=1)
            else:
                tk.Label(cap_box, text=self._t("msg_no_strong_cap_opportunity"), bg="#1d1e20", fg="#777",
                         font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=2)

            stable_title = tk.Label(card, text=self._t("section_stable_traits"),
                                    bg="#2a2b2e", fg="#9fc7ff",
                                    font=("Segoe UI", 8, "bold"), anchor="w")
            stable_title.pack(fill=tk.X, pady=(6, 2))

            stable_box = tk.Frame(card, bg="#1d1e20")
            stable_box.pack(fill=tk.X)
            if scenario["stable_traits"]:
                for delta in scenario["stable_traits"][:3]:
                    self._render_trait_delta_row(stable_box, delta, is_upgrade=False)
            else:
                tk.Label(stable_box, text=self._t("msg_no_stable_active_trait"), bg="#1d1e20", fg="#777",
                         font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=2)

            final_traits_title = tk.Label(card, text=self._t("section_final_active_traits"),
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
