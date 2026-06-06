"""
refine.py  --  reprocessing math (ore -> minerals -> ISK).

Uses refine_data.REPROCESS (CCP SDE base yields) + live mineral prices, and the
standard EVE net-yield formula so the answer matches your actual skills/structure.

  effective_efficiency(...)  -> the fraction of base minerals you really get
  minerals_from_units(...)   -> {mineral_id: qty} from reprocessing N units
  refined_value_per_unit(...)-> ISK of minerals in 1 unit of ore (for ISK/m3)
"""
import ore_data
import refine_data

MINERAL_NAME = {m["type_id"]: m["name"] for m in ore_data.MINERALS}


def effective_efficiency(base_pct, reproc=5, reproc_eff=5, ore_specific=5, implant_pct=0.0):
    """How much of the base mineral yield you actually keep, as a fraction.

    base_pct       station/structure base reprocessing %  (≈50 hisec NPC, higher in a rigged Athanor)
    reproc         Reprocessing skill 0-5            (+3%/level)
    reproc_eff     Reprocessing Efficiency skill 0-5 (+2%/level)
    ore_specific   the ore's Processing skill 0-5    (+2%/level)
    implant_pct    reprocessing implant, e.g. 4 for an RX-804
    """
    return (base_pct / 100.0
            * (1 + 0.03 * reproc)
            * (1 + 0.02 * reproc_eff)
            * (1 + 0.02 * ore_specific)
            * (1 + implant_pct / 100.0))


def minerals_from_units(ore_type_id, units, efficiency):
    """{mineral_type_id: quantity} from reprocessing `units` of ore.
    Only whole `portion`-sized batches reprocess (leftovers are wasted)."""
    info = refine_data.REPROCESS.get(str(ore_type_id))
    if not info:
        return {}
    portion = info["portion"] or 1
    batches = int(units) // portion
    return {int(mtid): int(batches * qty * efficiency)
            for mtid, qty in info["materials"].items()}


def refined_value_per_unit(ore_type_id, efficiency, mineral_prices, basis="sell"):
    """ISK value of the minerals contained in ONE unit of ore (for ISK/m³ ranking)."""
    info = refine_data.REPROCESS.get(str(ore_type_id))
    if not info:
        return 0.0
    portion = info["portion"] or 1
    total = sum(qty * efficiency * mineral_prices.get(int(mtid), {}).get(basis, 0.0)
                for mtid, qty in info["materials"].items())
    return total / portion


def refined_value_of_units(ore_type_id, units, efficiency, mineral_prices, basis="sell"):
    """(minerals dict, total ISK) for reprocessing `units` of ore."""
    mins = minerals_from_units(ore_type_id, units, efficiency)
    isk = sum(q * mineral_prices.get(mid, {}).get(basis, 0.0) for mid, q in mins.items())
    return mins, isk
