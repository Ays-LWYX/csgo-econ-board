"""Economy analysis for the CS pro-match board.

All aggregates are computed from the raw per-round team equipment values in
economy.csv. One row in the CSV is one map of one series, so the unit of
analysis is the (match_id, _map) pair: a BO3 shares match_id across maps, and
merging on match_id alone mixes rounds from different maps together.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ROUNDS = 30
FULL_BUY = 16000

# Equipment bands used for the post-pistol decision panel.
R2_EDGES = [0, 2000, 6000, 8000, 16000, 25000]
R2_LABELS = ["Save (<=2k)", "Light (2-6k)", "Force (6-8k)", "Half (8-16k)", "Full (16k+)"]

R3_EDGES = [0, 2000, 6000, 9000, 12000, 100000]
R3_LABELS = ["Save (<=2k)", "Light (2-6k)", "Force (6-9k)", "Half (9-12k)", "Full (12k+)"]

DIFF_EDGES = [-1e9, -10000, -5000, 5000, 10000, 1e9]
DIFF_LABELS = ["Behind >10k", "Behind 5-10k", "Even (5k)", "Ahead 5-10k", "Ahead >10k"]


def read_economy(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def build_long(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape to one row per (map, round, team)."""
    keep = ["date", "match_id", "_map", "t1_start", "t2_start"]
    base = df[keep]
    frames = []
    for i in range(1, ROUNDS + 1):
        a, b, w = f"{i}_t1", f"{i}_t2", f"{i}_winner"
        mask = df[w].notna()
        if not mask.any():
            continue
        won1 = (df[w].values == 1).astype("int8")
        won2 = (df[w].values == 2).astype("int8")
        for team, own, opp, won, side in (
            (1, a, b, won1, "t1_start"),
            (2, b, a, won2, "t2_start"),
        ):
            frames.append(
                pd.DataFrame(
                    {
                        "date": base["date"].values,
                        "match_id": base["match_id"].values,
                        "map": base["_map"].values,
                        "side_start": base[side].values,
                        "round": np.int16(i),
                        "team": np.int8(team),
                        "own": df[own].values.astype("float32"),
                        "opp": df[opp].values.astype("float32"),
                        "won": won,
                    }
                )[mask.values]
            )

    long = pd.concat(frames, ignore_index=True)
    long = long.dropna(subset=["own", "opp", "side_start"])
    long["date"] = pd.to_datetime(long["date"])
    long["diff"] = (long["own"] - long["opp"]).astype("float32")
    flip = long["round"] > 15
    long["side"] = np.where(flip, long["side_start"].map({"t": "ct", "ct": "t"}), long["side_start"])
    long["side"] = long["side"].astype("category")
    for c in ("match_id", "date", "map", "side_start"):
        long[c] = long[c]
    long["match_id"] = long["match_id"].astype("int32")
    long = long.sort_values(["match_id", "map", "team", "round"], kind="stable").reset_index(drop=True)
    long["streak"] = _loss_streak(long)
    long["age_days"] = long["round"]
    return long


def _loss_streak(long: pd.DataFrame) -> np.ndarray:
    """Number of consecutive losses immediately before this round.

    Vectorised: rounds are contiguous per (map, team) after the sort, so a
    per-group running max of "position of last win" is enough. Groups are
    separated by adding an increasing offset larger than any position.
    """
    code, _ = pd.factorize(
        pd.MultiIndex.from_arrays([long["match_id"], long["map"], long["team"]]), sort=False
    )
    pos = long.groupby([long["match_id"], long["map"], long["team"]], sort=False).cumcount().to_numpy()
    big = (pos.max() + 2) * (code.max() + 2) + 1
    winpos = np.where(long["won"].to_numpy() == 1, pos, -1)
    lifted = np.maximum.accumulate(winpos + code * big)
    last_win = lifted - code * big
    prev = np.roll(last_win, 1)
    prev[0] = -1
    new_group = np.r_[True, code[1:] != code[:-1]]
    prev[new_group] = -1
    streak = pos - prev - 1
    return np.clip(streak, 0, None).astype("int16")


def window_mask(long: pd.DataFrame, window: str) -> pd.Series:
    if window == "recent":
        cut = long["date"].max() - pd.DateOffset(months=3)
        return long["date"] >= cut
    return pd.Series(True, index=long.index)


def band_table(d: pd.DataFrame, edges, labels, col: str = "own") -> pd.DataFrame:
    b = pd.cut(d[col], bins=edges, labels=labels, right=True, include_lowest=True)
    out = (
        d.groupby(b, observed=False)
        .agg(rounds=("won", "size"), win_rate=("won", "mean"), avg_equip=("own", "mean"))
        .reset_index()
        .rename(columns={col: "band", "index": "band"})
    )
    out = out[out["rounds"] > 0].copy()
    out["share"] = out["rounds"] / out["rounds"].sum()
    return out


def pistol_trajectory(d: pd.DataFrame) -> pd.DataFrame:
    r1 = d[d["round"] == 1][["match_id", "map", "team", "won"]]
    winners = r1[r1["won"] == 1][["match_id", "map", "team"]].rename(columns={"team": "pistol_winner"})
    a = d.merge(winners, on=["match_id", "map"], how="inner")
    a["won_pistol"] = a["team"] == a["pistol_winner"]
    g = (
        a[a["round"] <= 15]
        .groupby(["round", "won_pistol"])
        .agg(equip=("own", "mean"), win_rate=("won", "mean"), rounds=("won", "size"))
        .reset_index()
    )
    out = g.pivot(index="round", columns="won_pistol", values=["equip", "win_rate"])
    out.columns = [f"{'pw' if c[1] else 'pl'}_{c[0]}" for c in out.columns]
    return out.reset_index()


def post_pistol(d: pd.DataFrame) -> dict:
    lost = d[(d["round"] == 1) & (d["won"] == 0)][["match_id", "map", "team"]]
    los = d.merge(lost, on=["match_id", "map", "team"], how="inner")

    r2 = band_table(los[los["round"] == 2], R2_EDGES, R2_LABELS)
    r3 = band_table(los[los["round"] == 3], R3_EDGES, R3_LABELS)

    a = los[los["round"] == 2][["match_id", "map", "team", "own", "won"]].rename(
        columns={"own": "eq2", "won": "won2"}
    )
    b = los[los["round"] == 3][["match_id", "map", "team", "own", "won"]].rename(
        columns={"own": "eq3", "won": "won3"}
    )
    ev = a.merge(b, on=["match_id", "map", "team"])
    ev["band"] = pd.cut(ev["eq2"], bins=R2_EDGES, labels=R2_LABELS, include_lowest=True)
    evt = (
        ev.groupby("band", observed=True)
        .agg(
            pairs=("won2", "size"),
            win_r2=("won2", "mean"),
            equip_r3=("eq3", "mean"),
            win_r3=("won3", "mean"),
            two_round_wins=("won2", lambda s: (s + ev.loc[s.index, "won3"]).mean()),
        )
        .reset_index()
    )
    evt["share"] = evt["pairs"] / evt["pairs"].sum()
    return {"r2": r2, "r3": r3, "ev": evt, "pairs": int(len(ev))}


def diff_bands(d: pd.DataFrame) -> pd.DataFrame:
    b = pd.cut(d["diff"], bins=DIFF_EDGES, labels=DIFF_LABELS)
    t = (
        d.groupby(b, observed=False)
        .agg(rounds=("won", "size"), win_rate=("won", "mean"))
        .reset_index()
    )
    side = d.pivot_table(index=b, columns="side", values="won", aggfunc="mean", observed=False)
    t = t.merge(side.reset_index(), on="diff", how="left")
    t["share"] = t["rounds"] / t["rounds"].sum()
    return t.rename(columns={"diff": "band", "t": "win_t", "ct": "win_ct"})


def loss_bonus_curve(d: pd.DataFrame) -> pd.DataFrame:
    b = d["streak"].clip(upper=5)
    t = (
        d.assign(streak_b=b)
        .groupby("streak_b")
        .agg(
            rounds=("won", "size"),
            avg_equip=("own", "mean"),
            full_buy_share=("own", lambda s: (s >= FULL_BUY).mean()),
            eco_share=("own", lambda s: (s <= 5000).mean()),
            win_rate=("won", "mean"),
        )
        .reset_index()
        .rename(columns={"streak_b": "streak"})
    )
    return t


def marginal_value(d: pd.DataFrame, bin_size: int = 1000) -> pd.DataFrame:
    edges = np.arange(-15000, 16000, bin_size)
    b = pd.cut(d["diff"], bins=edges, labels=edges[:-1].astype(int))
    t = (
        d.groupby(b, observed=True)
        .agg(rounds=("won", "size"), win_rate=("won", "mean"))
        .reset_index()
        .rename(columns={"diff": "diff"})
    )
    t["diff"] = t["diff"].astype(int)
    t = t[t["rounds"] >= 200].reset_index(drop=True)
    t["pp_per_1k"] = t["win_rate"].diff() * 100
    return t


def win_prob_curve(d: pd.DataFrame, bin_size: int = 500, lo: int = -20000, hi: int = 20000):
    """Empirical win probability as a function of equipment difference.

    Returns (centres, rates, counts) for interpolation; no model is fitted, the
    curve is the observed rate in each $500 bucket, so what the board shows is
    always a number the data contains.
    """
    edges = np.arange(lo, hi + bin_size, bin_size)
    b = pd.cut(d["diff"], bins=edges, labels=edges[:-1] + bin_size / 2)
    g = d.groupby(b, observed=True).agg(win_rate=("won", "mean"), rounds=("won", "size"))
    g = g[g["rounds"] >= 100]
    x = g.index.astype(float).to_numpy()
    return x, g["win_rate"].to_numpy(), g["rounds"].to_numpy()


def interp_prob(x, rates, query):
    q = np.asarray(query, dtype=float)
    out = np.interp(q, x, rates)
    out = np.where(q < x[0], rates[0], out)
    out = np.where(q > x[-1], rates[-1], out)
    return out


# ------------------------------------------------------------ spend advice
#
# Two measurements decide the call. Neither is a number picked by hand:
#
#   edge   teams that win a round enter it $6,187 ahead on average across the
#          2.19m team-rounds in the file, and the teams that lose it are
#          exactly that far behind. That is what a bought round costs in
#          dollars: their expected buy plus that gap.
#   shape  money stops paying at a lead of roughly $18,000. The observed win
#          rate is 86.6% at +$18k and 87.8% at +$22k, so once you are that
#          far ahead the next dollar does not buy a better round, it buys
#          next round. Between those ends $1,000 of equipment is worth about
#          1.5-2.0 points of win rate.
#
# The buy levels below are the same bands panel 02 measures, so the two panels
# cannot tell a player different things. The call is the highest level the
# budget can actually finish, because a level left half-bought is money spent
# without reaching the equipment it was spent for.

ECO_SLICE = 2000.0   # pistols and a little armour: the band panel 02 calls Save
FORCE = 7000.0       # a force buy: the 6-8k band
INCOME = 3400.0      # money back per round: loss bonus ladder plus a plant
MIN_RUNG_GAP = 1500.0


def price_round(curve: dict, opp: float) -> float:
    """What a bought round costs: their expected buy plus the average winning gap.

    Capped at the 95th percentile of equipment actually fielded, because above
    that a team is paying for gear it cannot put on the server.
    """
    return float(min(curve["p95"], opp + curve["edge"]))


def buy_levels(price: float) -> list:
    """The ladder a call can land on, cheapest first.

    Two absolute rungs (a pistol slice and a force) and three that scale with
    the price of this particular round, because what a half buy costs depends
    on what the other team brings. Rungs closer than $1,500 are collapsed: two
    prices that differ by less than a grenade are one decision, not two.
    """
    raw = [
        ("ECO", ECO_SLICE),
        ("FORCE", FORCE),
        ("50% BUY", 0.50 * price),
        ("75% BUY", 0.75 * price),
    ]
    raw = [(lab, amt) for lab, amt in raw if 0.0 < amt < price - MIN_RUNG_GAP]
    raw.sort(key=lambda kv: kv[1])

    out = [("SAVE", 0.0)]
    for lab, amt in raw:
        if amt - out[-1][1] >= MIN_RUNG_GAP:
            out.append((lab, amt))
    out.append(("FULL BUY", price))
    return out


def spend_advice(curve: dict, budget: float, opp: float) -> dict:
    """How much of `budget` to commit this round against an expected `opp` buy.

    The answer is a rung on the buy ladder, not a share of the budget. A team
    holding $24,000 facing a $13,000 buy does not spend $24,000: it spends what
    a full buy costs here and banks the rest. A team holding $9,000 does not
    spend $9,000 either, because $9,000 finishes nothing: it takes the $7,000
    force or it saves. The call is the highest rung the money actually
    completes.

    Every probability returned is read off the observed curve at the resulting
    equipment gap, so nothing here is a modelled estimate.
    """
    x, rates = curve["x"], curve["rates"]
    cap = float(curve["p95"])

    def p(gap: float) -> float:
        return float(np.interp(gap, x, rates))

    price = price_round(curve, opp)
    ladder = buy_levels(price)

    fits = [lv for lv in ladder if lv[1] <= budget + 1.0]
    if not fits:
        tier, spend = "SAVE", 0.0
    else:
        tier, spend = fits[-1]

    if spend <= 0.0:
        reason = "nothing"
    elif spend >= price - 1.0:
        reason = "full"
    elif spend <= ECO_SLICE + 1.0:
        reason = "eco"
    else:
        reason = "partial"

    spend = float(min(spend, budget))
    keep = float(max(budget - spend, 0.0))
    gap_now = float(min(spend, cap) - opp)
    field_next = float(min(cap, keep + INCOME))
    shortfall = float(max(price - budget, 0.0))

    return {
        "spend": spend,
        "keep": keep,
        "tier": tier,
        "reason": reason,
        "price": price,
        "edge": float(curve["edge"]),
        "cap": cap,
        "gap_now": gap_now,
        "p_now": p(gap_now),
        "p_save": p(-opp),
        "p_all": p(min(budget, cap) - opp),
        "field_next": field_next,
        "p_next": p(field_next - opp),
        "shortfall": shortfall,
        "rounds_to_price": int(np.ceil(shortfall / INCOME)) if shortfall > 1.0 else 0,
        "share": (spend / budget) if budget > 0 else 0.0,
        "ladder": ladder,
        "budget": float(budget),
        "opp": float(opp),
    }


def policy_curve(curve: dict, opp: float, step: float = 250.0, top: float = 25000.0):
    """The call at every budget, for the sweep chart in panel 00.

    Plotting this is what makes the rule legible: the call is a staircase, not
    a copy of the budget, and the flat part at the top is where extra money
    stops buying equipment you can field.
    """
    budgets = np.arange(0.0, top + step, step)
    spends = np.array([spend_advice(curve, b, opp)["spend"] for b in budgets])
    return budgets, spends


def kpis(d: pd.DataFrame, post: dict) -> dict:
    p1 = pistol_trajectory(d).set_index("round")
    bands = diff_bands(d).set_index("band")
    ev = post["ev"].set_index("band")
    return {
        "parity": float(bands.loc["Even (5k)", "win_rate"]),
        "ahead10": float(bands.loc["Ahead >10k", "win_rate"]),
        "behind10": float(bands.loc["Behind >10k", "win_rate"]),
        "pistol_gap_r2": float(p1.loc[2, "pw_win_rate"] - p1.loc[2, "pl_win_rate"]),
        "pistol_gap_r4": float(p1.loc[4, "pw_win_rate"] - p1.loc[4, "pl_win_rate"]),
        "force_ev": float(ev.loc["Force (6-8k)", "two_round_wins"]),
        "save_ev": float(ev.loc["Save (<=2k)", "two_round_wins"]),
        "fullbuy_share": float((d["own"] >= FULL_BUY).mean()),
        "avg_equip": float(d["own"].mean()),
        "rounds": int(len(d)),
        "maps": int(d.groupby(["match_id", "map"]).ngroups),
        "date_min": d["date"].min(),
        "date_max": d["date"].max(),
    }


def compute_panels(long: pd.DataFrame, window: str) -> dict:
    d = long[window_mask(long, window)]
    post = post_pistol(d)
    x, r, n = win_prob_curve(d)
    return {
        "kpis": kpis(d, post),
        "p1": pistol_trajectory(d),
        "post": post,
        "p3": diff_bands(d),
        "p4": loss_bonus_curve(d),
        "p5": marginal_value(d),
        "curve": {
            "x": x,
            "rates": r,
            "counts": n,
            # What a bought round costs, measured rather than assumed: the
            # equipment gap the average winner actually holds, and the level
            # above which more equipment stops being fieldable.
            "edge": float(d.loc[d["won"] == 1, "diff"].mean()),
            "p95": float(d["own"].quantile(0.95)),
        },
    }


def window_compare(long: pd.DataFrame) -> pd.DataFrame:
    """Key numbers side by side: full history vs the latest three months."""
    rows = []
    for key, label in (("all", "Full history (2017-04 - 2020-03)"), ("recent", "Latest 3 months (2019-12 - 2020-03)")):
        d = long[window_mask(long, key)]
        post = post_pistol(d)
        p1 = pistol_trajectory(d).set_index("round")
        bands = diff_bands(d).set_index("band")
        rows.append(
            {
                "sample": label,
                "rounds": len(d),
                "maps": int(d.groupby(["match_id", "map"]).ngroups),
                "avg_equip": d["own"].mean(),
                "full_buy_share": (d["own"] >= FULL_BUY).mean(),
                "win_even": bands.loc["Even (5k)", "win_rate"],
                "win_ahead10": bands.loc["Ahead >10k", "win_rate"],
                "win_behind10": bands.loc["Behind >10k", "win_rate"],
                "pistol_loser_r2_equip": p1.loc[2, "pl_equip"],
                "force_ev": post["ev"].set_index("band").loc["Force (6-8k)", "two_round_wins"],
                "force_share": post["ev"].set_index("band").loc["Force (6-8k)", "share"],
            }
        )
    out = pd.DataFrame(rows).set_index("sample").T
    out["delta"] = out.iloc[:, 1] - out.iloc[:, 0]
    return out
