"""CS Economy Board - how much money should I commit this round?

Data: economy.csv from Kaggle "CS:GO Professional Matches" (mateusdmachado).
One row = one map. The unit of analysis is the (match_id, _map) pair.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import econ

DATA = Path(__file__).parent / "economy.csv"

# Shown next to the title. The exercise asks for the team name on the dashboard.
TEAM_NAME = "Yancheng Gong's Team"

# ---------------------------------------------------------------- palette
BG = "#0B0D11"
PANEL = "#141821"
GRID = "#242A36"
TEXT = "#E7EAEE"
MUTED = "#858E9C"
AMBER = "#E8A33D"
BLUE = "#4C9BE8"
TEAL = "#35C2A0"
RED = "#DF5B6B"

st.set_page_config(
    page_title="CS Economy Board",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
.block-container {padding-top: 3.4rem; padding-bottom: 2.6rem; max-width: 1500px;}
html, body, [class*="css"] {
  font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
#MainMenu, footer, [data-testid="stAppDeployButton"], [data-testid="stToolbar"] {display: none;}
h1, h2, h3 {letter-spacing: -0.01em;}

.eyebrow {
  font-family: "Consolas", "SF Mono", monospace;
  font-size: 11px; letter-spacing: 0.22em; color: #E8A33D;
  text-transform: uppercase; margin-bottom: 2px;
}
.title {font-size: 40px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.06; color: #E7EAEE;}
.subtitle {font-size: 14.5px; color: #A7AFBB; max-width: 900px; line-height: 1.55; margin-top: 8px;}

.sec {display: flex; align-items: baseline; gap: 12px;
      border-bottom: 1px solid #242A36; padding-bottom: 6px; margin: 30px 0 8px;}
.sec .num {font-family: "Consolas", monospace; font-size: 12px; letter-spacing: .12em;
           color: #E8A33D; font-weight: 700;}
.sec .ttl {font-size: 14.5px; letter-spacing: .17em; font-weight: 600; color: #E7EAEE;}
.take {font-size: 14px; color: #C3CAD4; line-height: 1.6; margin: 2px 0 10px;}
.take b {color: #E7EAEE;}
.note {font-size: 12.5px; color: #858E9C; line-height: 1.6; margin-top: 6px;}

div[data-testid="stMetricLabel"] p {
  text-transform: uppercase; letter-spacing: .13em; font-size: 10.5px; color: #858E9C;
}
div[data-testid="stMetricValue"] {
  font-size: 30px; font-weight: 700; letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
div[data-testid="stMetric"] {background: #141821; border: 1px solid #242A36;
  border-radius: 4px; padding: 14px 16px 10px;}

table.tbl {width: 100%; border-collapse: collapse; font-size: 14px;
  font-variant-numeric: tabular-nums; margin-top: 4px;}
table.tbl th {text-align: right; font-size: 10.5px; letter-spacing: .1em; color: #7C8695;
  text-transform: uppercase; font-weight: 600; padding: 6px 10px; border-bottom: 1px solid #242A36;}
table.tbl th:first-child {text-align: left;}
table.tbl td {text-align: right; padding: 7px 10px; border-bottom: 1px solid #191E27; color: #D7DCE3;
  white-space: nowrap;}
table.tbl th {vertical-align: bottom;}
table.tbl.wrap td, table.tbl.wrap th {white-space: normal;}
table.tbl td:first-child {text-align: left; color: #E7EAEE; font-weight: 500; padding-right: 22px;}
table.tbl tr.hl td {background: #1D232E; color: #FFFFFF; font-weight: 600;}
table.tbl tr.hl td:first-child {color: #E8A33D;}

.verdict {background: #141821; border: 1px solid #2B323F; border-left: 3px solid #E8A33D;
  border-radius: 4px; padding: 16px 18px;}
.verdict .vl {font-family: "Consolas", monospace; font-size: 11px; letter-spacing: .18em;
  color: #858E9C; text-transform: uppercase;}
.verdict .vv {font-size: 34px; font-weight: 700; letter-spacing: -0.02em; color: #FFFFFF;
  line-height: 1.15; margin: 2px 0 6px;}
.verdict .vsub {font-size: 12px; color: #858E9C; letter-spacing: .02em; margin: 0 0 9px;
  font-variant-numeric: tabular-nums;}
.verdict .vt {font-size: 13.5px; color: #A7AFBB; line-height: 1.55;}

.foot {border-top: 1px solid #242A36; margin-top: 34px; padding-top: 16px;
  font-size: 12.5px; color: #858E9C; line-height: 1.75;}
.foot b {color: #C3CAD4; font-weight: 600;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- data
@st.cache_resource(show_spinner="Loading 43,234 maps of round-by-round economy...")
def get_long() -> pd.DataFrame:
    return econ.build_long(econ.read_economy(str(DATA)))


@st.cache_data(show_spinner="Aggregating...")
def get_panels(window: str, _long: pd.DataFrame, v: int = 3) -> dict:
    return econ.compute_panels(_long, window)


@st.cache_data(show_spinner=False)
def get_compare(_long: pd.DataFrame, v: int = 3) -> pd.DataFrame:
    return econ.window_compare(_long)


# ---------------------------------------------------------------- format
def money(x: float) -> str:
    return f"${x:,.0f}"


def kfmt(x: float) -> str:
    return f"${x/1000:,.1f}k"


def pct(x: float, d: int = 1) -> str:
    return f"{x*100:.{d}f}%"


def tbl(df: pd.DataFrame, highlight: str | None = None, wrap: bool = False,
        extra: str = "") -> str:
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    body = []
    for _, row in df.iterrows():
        cls = ' class="hl"' if highlight is not None and row.iloc[0] == highlight else ""
        cells = "".join(f"<td>{v}</td>" for v in row.values)
        body.append(f"<tr{cls}>{cells}</tr>")
    klass = ("tbl wrap " if wrap else "tbl ") + extra
    return f'<table class="{klass}"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def section(num: str, title: str, takeaway: str) -> None:
    st.markdown(
        f'<div class="sec"><span class="num">{num}</span><span class="ttl">{title}</span></div>'
        f'<div class="take">{takeaway}</div>',
        unsafe_allow_html=True,
    )


def base_layout(
    fig: go.Figure,
    height: int,
    legend: bool = True,
    l: int = 10,
    r: int = 10,
    b: int = 34,
) -> go.Figure:
    fig.update_layout(
        height=height,
        template=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='-apple-system, "Segoe UI", Roboto, sans-serif', color=TEXT, size=12),
        margin=dict(l=l, r=r, t=30 if legend else 12, b=b),
        hoverlabel=dict(bgcolor=PANEL, bordercolor=GRID, font_size=12),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11.5)),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED))
    return fig


long = get_long()
window = st.sidebar.radio(
    "Sample",
    options=["Full history", "Latest 3 months"],
    index=0,
    captions=["2017-04 to 2020-03", "2019-12 to 2020-03"],
)
P = get_panels("recent" if window == "Latest 3 months" else "all", long, 3)
K, P1, POST, P3, P4, P5 = P["kpis"], P["p1"], P["post"], P["p3"], P["p4"], P["p5"]

with st.sidebar:
    st.markdown(
        f'<div class="note" style="margin-top:14px"><b style="color:#C3CAD4">In view</b><br>'
        f'{K["maps"]:,} maps<br>{K["rounds"]:,} team-rounds<br>'
        f'{K["date_min"]:%Y-%m-%d} to {K["date_max"]:%Y-%m-%d}</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Method and definitions"):
        st.markdown(
            """
One row of the source file is one map, so every stat here is computed per
`(match_id, _map)` pair. A BO3 shares `match_id` across its maps; merging on
`match_id` alone would count round 1 twice and inflate the pistol-round rates.

Equipment bands use the team's total value at round start, in dollars.

Full buy = $16,000 or more. Eco in panel 04 = $5,000 or less.

Win rates are raw frequencies, not modelled estimates. Nothing on this page is
a prediction about a specific match.

The "Latest 3 months" sample is the last three months present in the file. It
is there to show what a refresh would change, not to claim the game changed.
            """
        )

# ---------------------------------------------------------------- header
st.markdown(
    f'<div class="eyebrow">Counter-Strike / pro match economy / {K["maps"]:,} maps</div>'
    '<div class="title">CS Economy Board</div>'
    f'<div class="note" style="margin-top:3px">Team: {TEAM_NAME}</div>'
    '<div class="subtitle">For ranked players. You do not choose the map or the side, and you '
    'cannot read the other team\'s plan. The one lever you hold every round is how much money to '
    'commit. Every number below comes from 2017-2020 professional matches, so it tells you what '
    'actually happened when a team spent this much against that much.</div>',
    unsafe_allow_html=True,
)

st.caption(
    "For the in-game leader of a ranked five-stack: decides how much money to commit this round."
)

c1, c2, c3 = st.columns(3, gap="small")
c1.metric("Win rate at parity", pct(K["parity"]), help="Equipment difference within +/- $5,000.")
c2.metric("Win rate at +$10k", pct(K["ahead10"]), help="You start $10,000 or more ahead.")
c3.metric(
    "Forcing $6-8k",
    f"{K['force_ev']:.2f} wins",
    help=(
        f"Wins collected over rounds 2-3 after losing the pistol, against {K['save_ev']:.2f} for "
        "saving, so forcing is the worse option."
        if K["force_ev"] < K["save_ev"]
        else f"Wins collected over rounds 2-3 after losing the pistol, against {K['save_ev']:.2f} "
        "for saving. The two are level in this sample."
    ),
)

# ---------------------------------------------------------------- panel 00
section(
    "00",
    "ASK: HOW MUCH SHOULD I SPEND?",
    "Two sliders: what your team has, and what you expect them to spend. The answer is a rung on "
    "the buy ladder, never a share of the bank: what a full buy costs against this opponent, and "
    "the highest level your money actually finishes.",
)

s1, s2 = st.columns([1, 1], gap="large")
with s1:
    budget = st.slider("Your team can spend", 0, 25000, 24000, step=250, format="$%d")
    opp = st.slider("Opponent is expected to spend", 0, 25000, 13000, step=250, format="$%d")

ADV = econ.spend_advice(P["curve"], budget, opp)
spend, keep, price = ADV["spend"], ADV["keep"], ADV["price"]
tier, reason = ADV["tier"], ADV["reason"]
higher = [lv for lv in ADV["ladder"] if lv[1] > spend + 1.0]
next_rung = higher[0] if higher else None
gap_now = ADV["gap_now"]

WHY = {
    "full": (
        f"A full buy costs {money(price)} here: their {money(opp)} buy plus the "
        f"{money(ADV['edge'])} gap the average round winner holds. Put that in and stop. "
        f"{money(keep)} stays banked, and money past that gap does not buy a better round: the "
        f"observed win rate is 86.6% at a +$18,000 lead and 87.8% at +$22,000."
    ),
    "partial": (
        f"{money(spend)} is the highest rung your {money(budget)} finishes. The next one up is "
        f"{money(next_rung[1]) if next_rung else money(price)}, {money(ADV['shortfall'])} further "
        f"than you can reach, so the change stays banked rather than half-finishing a buy. That "
        f"bank plus the round income is {money(ADV['field_next'])} of equipment next round."
    ),
    "eco": (
        f"{money(spend)} buys pistols and a little armour: the only complete level your "
        f"{money(budget)} can field. This is not a round to win, it is a round that protects the "
        f"bank, so the next one can be a real buy at {money(ADV['field_next'])}."
    ),
    "nothing": (
        f"{money(budget)} does not complete even a pistol buy, so nothing goes in. Keep all of it: "
        f"a round you cannot arm for is worth more as the start of the next buy."
    ),
}

with s1:
    st.markdown(
        f'<div class="verdict"><div class="vl">Recommended buy</div>'
        f'<div class="vv">{money(spend)} &nbsp;<span style="font-size:14px;color:#8B94A2;'
        f'font-weight:600;letter-spacing:.16em">{tier}</span></div>'
        f'<div class="vsub">{money(keep)} banked of {money(budget)} &nbsp;·&nbsp; '
        f'a full buy costs {money(price)} &nbsp;·&nbsp; {ADV["share"] * 100:.0f}% committed</div>'
        f'<div class="vt">{WHY[reason]}</div></div>',
        unsafe_allow_html=True,
    )

with s2:
    x, rates = P["curve"]["x"], P["curve"]["rates"]
    grid = np.arange(0, max(budget, price, 1) * 1.06 + 250, 250)
    probs = econ.interp_prob(x, rates, grid - opp)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=grid, y=probs * 100, mode="lines", name="Win chance this round",
            line=dict(color=AMBER, width=2.4), fill="tozeroy", fillcolor="rgba(232,163,61,0.10)",
            hovertemplate="Spend $%{x:,.0f}<br>Win chance %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_vline(x=price, line=dict(color=BLUE, width=1, dash="dot"))
    fig.add_annotation(
        x=price, y=8, text=f"a full buy  {money(price)}", showarrow=False,
        font=dict(color=BLUE, size=10.5), xanchor="right", xshift=-6,
    )
    fig.add_trace(
        go.Scatter(
            x=[spend], y=[ADV["p_now"] * 100], mode="markers", name="Your call",
            marker=dict(color=TEAL, size=13, line=dict(color="#0B0D11", width=2)),
            hovertemplate="Buy $%{x:,.0f}<br>Win chance %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[budget], y=[ADV["p_all"] * 100], mode="markers", name="Everything in",
            marker=dict(color="#6E7A8A", size=10, symbol="circle-open",
                        line=dict(color="#9AA4B2", width=2)),
            hovertemplate="Spend $%{x:,.0f}<br>Win chance %{y:.1f}%<extra></extra>",
        )
    )
    if spend > 0:
        fig.add_annotation(
            x=spend, y=ADV["p_now"] * 100, text=f"{money(spend)}", showarrow=True, arrowhead=0,
            arrowcolor=TEAL, ax=0, ay=-26, font=dict(color=TEAL, size=11), bgcolor="rgba(0,0,0,0)",
        )
    base_layout(fig, 286, l=68, r=18, b=42)
    fig.update_xaxes(tickprefix="$", tickformat=",.0f", title_text="Spent this round",
                     title_font=dict(size=11, color=MUTED),
                     range=[0, max(budget, price) * 1.08])
    fig.update_yaxes(ticksuffix="%", range=[0, 100])
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})

    m1, m2 = st.columns(2)
    m1.metric(
        "Win chance this round",
        pct(ADV["p_now"]),
        help=f"Spending {money(spend)} against their {money(opp)}: a {money(gap_now)} equipment gap.",
    )
    m2.metric(
        "Next round's equipment",
        money(ADV["field_next"]),
        help=f"Bank of {money(keep)} plus {money(econ.INCOME)} of round income.",
    )

# ------------------------------------------------- the ladder, level by level
ladder_rows = []
for level, amount in ADV["ladder"]:
    win = float(econ.interp_prob(x, rates, [min(amount, ADV["cap"]) - opp])[0])
    if amount > budget + 1.0:
        ladder_rows.append(
            {
                "Level": f"{level} (out of reach)",
                "Cost": money(amount),
                "Win chance this round": pct(win),
                "Banked": "-",
                "Equipment next round": "-",
            }
        )
        break
    banked = budget - amount
    ladder_rows.append(
        {
            "Level": level,
            "Cost": money(amount),
            "Win chance this round": pct(win),
            "Banked": money(banked),
            "Equipment next round": money(min(ADV["cap"], banked + econ.INCOME)),
        }
    )
st.markdown(
    tbl(pd.DataFrame(ladder_rows), highlight=tier, extra="fit"), unsafe_allow_html=True
)

# ------------------------------------------------- the call at every budget
pbud, pspend = econ.policy_curve(P["curve"], opp)
fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=[0, 25000], y=[0, 25000], mode="lines", name="If the call were just your budget",
        line=dict(color="#4A5260", width=1.2, dash="dot"), hoverinfo="skip",
    )
)
fig2.add_trace(
    go.Scatter(
        x=pbud, y=pspend, mode="lines", name="The call, budget by budget",
        line=dict(color=TEAL, width=2.4, shape="hv"),
        fill="tozeroy", fillcolor="rgba(53,194,160,0.09)",
        hovertemplate="Budget $%{x:,.0f}<br>Call $%{y:,.0f}<extra></extra>",
    )
)
fig2.add_trace(
    go.Scatter(
        x=[budget], y=[spend], mode="markers", name="Your budget",
        marker=dict(color=AMBER, size=12, line=dict(color="#0B0D11", width=2)),
        hovertemplate="Budget $%{x:,.0f}<br>Call $%{y:,.0f}<extra></extra>",
    )
)
base_layout(fig2, 250, l=68, r=18, b=42)
fig2.update_xaxes(tickprefix="$", tickformat=",.0f", title_text="Your budget",
                  title_font=dict(size=11, color=MUTED))
fig2.update_yaxes(tickprefix="$", tickformat=",.0f", title_text="Recommended spend",
                  title_font=dict(size=11, color=MUTED), range=[0, max(21000, spend * 1.2)])
st.plotly_chart(fig2, theme=None, config={"displayModeBar": False})

st.markdown(
    f'<div class="note">How the call is made. A bought round is priced from the file, not assumed: '
    f'the average round winner enters it <b>{money(ADV["edge"])}</b> ahead '
    f'(E[equipment difference | won] over 2.19m team-rounds), so a full buy costs their expected '
    f'buy plus that gap, capped at {money(ADV["cap"])}, the 95th percentile of equipment teams '
    f'actually field. The ladder is $0, a $2,000 pistol buy, $7,000 force, then 50%, 75% and 100% '
    f'of that price. <b>The call is the highest rung the budget finishes</b>, because a level left '
    f'half-bought is money spent without reaching the equipment it was spent for. Above the full '
    f'buy the number stops rising on purpose: the curve is 86.6% at a +$18,000 lead and 87.8% at '
    f'+$22,000, so extra money is next round\'s buy, not this one\'s. Every percentage on this panel '
    f'is the observed win rate at that equipment gap.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- panel 01
r2e = P1.loc[P1["round"] == 2].iloc[0]
r4e = P1.loc[P1["round"] == 4].iloc[0]
r1e = P1.loc[P1["round"] == 1].iloc[0]
section(
    "01",
    "PISTOL RHYTHM, ROUNDS 2-15",
    f"The pistol round itself is not a money round: both teams start on about "
    f"{kfmt(r1e['pw_equip'])}. What it buys is round 2, where the winner holds "
    f"{kfmt(r2e['pw_equip'])} against {kfmt(r2e['pl_equip'])} and wins "
    f"{pct(r2e['pw_win_rate'])}. By round 4 the loser out-spends the winner "
    f"({kfmt(r4e['pl_equip'])} to {kfmt(r4e['pw_equip'])}) and wins {pct(r4e['pl_win_rate'])}. "
    f"The edge is gone in three rounds.",
)

p1c = P1[P1["round"] >= 2]
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14)
for col, name, color in (("pw", "Won the pistol", AMBER), ("pl", "Lost the pistol", BLUE)):
    fig.add_trace(
        go.Scatter(
            x=p1c["round"], y=p1c[f"{col}_equip"], mode="lines+markers", name=name,
            line=dict(color=color, width=2.2), marker=dict(size=5),
            legendgroup=name, showlegend=True,
            hovertemplate="Round %{x}<br>%{y:$,.0f}<extra>" + name + "</extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=p1c["round"], y=p1c[f"{col}_win_rate"] * 100, mode="lines+markers", name=name,
            line=dict(color=color, width=2.2), marker=dict(size=5), legendgroup=name,
            showlegend=False,
            hovertemplate="Round %{x}<br>%{y:.1f}%<extra>" + name + "</extra>",
        ),
        row=2, col=1,
    )
fig.add_hline(y=50, row=2, col=1, line=dict(color=MUTED, width=1, dash="dot"))
base_layout(fig, 430, l=72, r=22, b=36)
fig.update_xaxes(tickmode="linear", tick0=2, dtick=1, range=[1.6, 15.4])
fig.update_yaxes(
    tickprefix="$", tickformat=",.0f", row=1, col=1,
    title_text="Avg equipment", title_font=dict(size=11, color=MUTED),
)
fig.update_yaxes(
    ticksuffix="%", range=[0, 100], row=2, col=1,
    title_text="Win rate", title_font=dict(size=11, color=MUTED),
)
st.plotly_chart(fig, theme=None, config={"displayModeBar": False})

with st.expander("Round by round, 1-15"):
    rr = pd.DataFrame(
        {
            "Round": P1["round"],
            "Won pistol: equip": P1["pw_equip"].map(money),
            "Won pistol: win rate": P1["pw_win_rate"].map(pct),
            "Lost pistol: equip": P1["pl_equip"].map(money),
            "Lost pistol: win rate": P1["pl_win_rate"].map(pct),
            "Gap, equip": (P1["pw_equip"] - P1["pl_equip"]).map(lambda v: f"{v:+,.0f}"),
        }
    )
    st.markdown(tbl(rr), unsafe_allow_html=True)

# ---------------------------------------------------------------- panel 02
evt = POST["ev"]
REC_BAND = "Half (8-16k)"
force_row = evt.set_index("band").loc["Force (6-8k)"]
save_row = evt.set_index("band").loc["Save (<=2k)"]
full_row = evt.set_index("band").loc["Full (16k+)"]
half_ev = float(evt.set_index("band").loc[REC_BAND, "two_round_wins"])
if K["force_ev"] < K["save_ev"]:
    p2_line = (
        f"Only {pct(force_row['share'])} of teams force-buy at $6-8k in round 2, and it is the "
        f"worst tier on the board: {force_row['two_round_wins']:.2f} wins across rounds 2-3, below "
        f"the {K['save_ev']:.2f} that saving returns. Half-buying at $8-16k returns {half_ev:.2f}."
    )
else:
    p2_line = (
        f"Only {pct(force_row['share'])} of teams force-buy at $6-8k in round 2 in this sample, "
        f"and their two-round return ({force_row['two_round_wins']:.2f} wins) is level with "
        f"saving ({K['save_ev']:.2f}) rather than below it. Half-buying at $8-16k still returns "
        f"the most of the three, at {half_ev:.2f}."
    )
section("02", "AFTER LOSING THE PISTOL: ROUND 2 AND 3", p2_line)

a1, a2 = st.columns(2, gap="large")
with a1:
    st.markdown('<div class="note" style="margin-bottom:2px"><b style="color:#C3CAD4">ROUND 2 '
                "CHOICE</b></div>", unsafe_allow_html=True)
    t2 = POST["r2"][["band", "share", "win_rate", "rounds"]].copy()
    t2.columns = ["Equipment tier", "Teams pick", "Win rate", "Rounds"]
    t2["Teams pick"] = t2["Teams pick"].map(pct)
    t2["Win rate"] = t2["Win rate"].map(pct)
    t2["Rounds"] = t2["Rounds"].map(lambda v: f"{v:,}")
    st.markdown(tbl(t2, highlight=REC_BAND), unsafe_allow_html=True)
with a2:
    st.markdown('<div class="note" style="margin-bottom:2px"><b style="color:#C3CAD4">ROUND 3 '
                "CHOICE, SAME TEAMS</b></div>", unsafe_allow_html=True)
    t3 = POST["r3"][["band", "share", "win_rate", "rounds"]].copy()
    t3.columns = ["Equipment tier", "Teams pick", "Win rate", "Rounds"]
    t3["Teams pick"] = t3["Teams pick"].map(pct)
    t3["Win rate"] = t3["Win rate"].map(pct)
    t3["Rounds"] = t3["Rounds"].map(lambda v: f"{v:,}")
    st.markdown(tbl(t3, highlight="Full (12k+)"), unsafe_allow_html=True)

st.markdown(
    '<div class="take" style="margin-top:18px">A single round cannot separate a good buy from a '
    'bad one, because the team that can afford a full buy is usually the team that played the '
    'pistol better. So the table below follows the same teams into round 3: whatever you spend in '
    'round 2 decides what you can afford in round 3, and the <b>two-round total</b> is the number '
    'that matters.</div>',
    unsafe_allow_html=True,
)

ev_df = evt.copy()
ev_df.columns = [
    "Round 2 tier", "Pairs", "Win rate R2", "Equip in R3", "Win rate R3", "Wins over R2+R3", "Share",
]
ev_df["Pairs"] = ev_df["Pairs"].map(lambda v: f"{v:,}")
for c in ("Win rate R2", "Win rate R3", "Share"):
    ev_df[c] = ev_df[c].map(pct)
ev_df["Equip in R3"] = ev_df["Equip in R3"].map(kfmt)
ev_df["Wins over R2+R3"] = ev_df["Wins over R2+R3"].map(lambda v: f"{v:.2f}")
ev_df = ev_df[["Round 2 tier", "Share", "Win rate R2", "Equip in R3", "Win rate R3", "Wins over R2+R3"]]

v1, v2 = st.columns([1.05, 1], gap="large")
with v1:
    st.markdown(tbl(ev_df, highlight=REC_BAND), unsafe_allow_html=True)
    st.markdown(
        f'<div class="note">Read the last column, not the third. Saving round 2 loses round 2 '
        f'almost always, but it funds a {kfmt(save_row["equip_r3"])} round 3 and the pair ends up '
        f'worth {save_row["two_round_wins"]:.2f} wins. Forcing $6-8k wins a few more round 2s and '
        f'then walks into round 3 with {kfmt(force_row["equip_r3"])}, so the pair is worth '
        f'{force_row["two_round_wins"]:.2f}. The full-buy tier wins the pair outright, but only '
        f'{pct(full_row["share"])} of teams are in it and those are the teams the pistol already '
        f'went well for.</div>',
        unsafe_allow_html=True,
    )
with v2:
    order = evt["band"].tolist()
    trap = K["force_ev"] < K["save_ev"]
    colors = []
    for b in order:
        if b == REC_BAND:
            colors.append(TEAL)
        elif b == "Force (6-8k)" and trap:
            colors.append(RED)
        else:
            colors.append("#3A4353")
    fig = go.Figure(
        go.Bar(
            x=evt["two_round_wins"], y=order, orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:.2f}" for v in evt["two_round_wins"]],
            textposition="outside", textfont=dict(color=TEXT, size=12),
            hovertemplate="%{y}<br>%{x:.2f} wins over R2+R3<extra></extra>",
        )
    )
    base_layout(fig, 300, legend=False, l=106, r=62, b=46)
    fig.update_xaxes(range=[0, 1.2], title_text="Wins collected over rounds 2 and 3",
                     title_font=dict(size=11, color=MUTED))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})

_caveat = (
    "if you are sitting on $6-8k, saving beats forcing"
    if K["force_ev"] < K["save_ev"]
    else "if you are sitting on $6-8k, the two are close enough that the decision belongs to your "
    "next-round plan, not to this table"
)
st.markdown(
    '<div class="note">One caveat the table cannot remove: round 2 money is partly a result of '
    'the pistol round itself, not a free choice. Teams at $8-16k got there by taking the pistol '
    'to more kills and a plant. So compare tiers as descriptions of what happened, and treat the '
    f'one clean choice in the data as this: {_caveat}.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- panel 03
p3 = P3.copy()
gap_even = float(p3.set_index("band").loc["Even (5k)", "win_rate"])
p3["vs parity"] = (p3["win_rate"] - gap_even) * 100
section(
    "03",
    "EQUIPMENT ADVANTAGE: THE LOOKUP TABLE",
    f"A $5,000 advantage is worth about 10 percentage points, a $10,000 advantage about 33. "
    f"Behind by more than $10,000 you win {pct(p3.set_index('band').loc['Behind >10k','win_rate'])} "
    f"of rounds, which is one round in six. The T and CT columns differ by a few points at most, "
    f"so the same table works on both sides.",
)

t3d = pd.DataFrame(
    {
        "Equipment gap": p3["band"],
        "Win rate": p3["win_rate"].map(pct),
        "vs parity": p3["vs parity"].map(lambda v: f"{v:+.0f}pp"),
        "Share of rounds": p3["share"].map(pct),
        "as CT": p3["win_ct"].map(pct),
        "as T": p3["win_t"].map(pct),
        "Rounds": p3["rounds"].map(lambda v: f"{v:,}"),
    }
)
g1, g2 = st.columns([1, 1.15], gap="large")
with g1:
    st.markdown(tbl(t3d, highlight="Even (5k)"), unsafe_allow_html=True)
    st.markdown(
        '<div class="note">This is the table to remember. It is also the quiet argument against '
        'half-measures: the two middle rows cover 21% of all rounds and are separated by 20 points, '
        'so the gap you create in the first fifteen seconds is the gap you play the round from.</div>',
        unsafe_allow_html=True,
    )
with g2:
    fig = go.Figure(
        go.Bar(
            x=p3["win_rate"] * 100, y=p3["band"], orientation="h",
            marker=dict(
                color=[RED if v < 0.5 else TEAL for v in p3["win_rate"]],
                line=dict(width=0),
            ),
            text=[pct(v) for v in p3["win_rate"]],
            textposition="outside", textfont=dict(color=TEXT, size=12),
            hovertemplate="%{y}<br>%{x:.1f}% win rate<extra></extra>",
        )
    )
    fig.add_vline(x=50, line=dict(color=MUTED, width=1, dash="dot"))
    base_layout(fig, 300, legend=False, l=106, r=62, b=46)
    fig.update_xaxes(range=[0, 100], ticksuffix="%", title_text="Round win rate",
                     title_font=dict(size=11, color=MUTED))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})

# ---------------------------------------------------------------- panel 04
p4 = P4.copy()
p4["streak_label"] = np.where(p4["streak"] >= 5, "5+", p4["streak"].astype(str))
section(
    "04",
    "THE LOSS LADDER: WHAT HAPPENS AFTER N STRAIGHT LOSSES",
    f"The ladder is not a straight line. After two straight losses the average team is holding "
    f"{kfmt(p4.set_index('streak').loc[2,'avg_equip'])} and only "
    f"{pct(p4.set_index('streak').loc[2,'full_buy_share'])} full buy, because that is the round "
    f"teams choose to save. One round later {pct(p4.set_index('streak').loc[3,'full_buy_share'])} "
    f"full buy at {kfmt(p4.set_index('streak').loc[3,'avg_equip'])}. The save is what pays for the "
    f"re-buy, not the bonus alone.",
)

t4 = pd.DataFrame(
    {
        "Losses before round": p4["streak_label"],
        "Equip": p4["avg_equip"].map(kfmt),
        "Full buy": p4["full_buy_share"].map(pct),
        "Eco": p4["eco_share"].map(pct),
        "Win rate": p4["win_rate"].map(pct),
        "N": p4["rounds"].map(lambda v: f"{v/1e6:.2f}M" if v >= 1e6 else f"{v/1e3:.0f}k"),
    }
)
l1, l2 = st.columns([1, 1.15], gap="large")
with l1:
    st.markdown(tbl(t4, highlight="2"), unsafe_allow_html=True)
    st.markdown(
        '<div class="note">Win rate follows the money, not the losing streak: 26% after two losses '
        'and 38% after three. Two losses means you are about to be broke; three means you just got '
        'the full buy and the loss bonus is near its cap.</div>',
        unsafe_allow_html=True,
    )
with l2:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=p4["streak_label"], y=p4["avg_equip"] / 1000, name="Avg equipment",
            customdata=p4["avg_equip"],
            marker=dict(color="#38414F", line=dict(width=0)),
            hovertemplate="%{x} losses<br>%{customdata:$,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=p4["streak_label"], y=p4["win_rate"] * 100, name="Win rate",
            mode="lines+markers", line=dict(color=AMBER, width=2.4), marker=dict(size=6),
            hovertemplate="%{x} losses<br>%{y:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )
    base_layout(fig, 312, l=62, r=58, b=46)
    fig.update_yaxes(tickvals=[0, 5, 10, 15, 20, 25],
                     ticktext=["$0", "$5k", "$10k", "$15k", "$20k", "$25k"],
                     secondary_y=False)
    fig.update_yaxes(ticksuffix="%", range=[0, 80], tickformat=".0f", dtick=20,
                     secondary_y=True)
    fig.update_xaxes(title_text="Straight losses going into the round", title_font=dict(size=11, color=MUTED))
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})

# ---------------------------------------------------------------- panel 05
p5 = P5.copy()
mid = p5[(p5["diff"] >= -4000) & (p5["diff"] < 4000)]
edge = p5[(p5["diff"] < -8000) | (p5["diff"] >= 8000)]
section(
    "05",
    "THE VALUE OF THE NEXT $1,000",
    f"The last $1,000 is worth most at the extremes: about "
    f"{edge['pp_per_1k'].mean():.1f} points of win rate when you are crossing out of an eco, and "
    f"only {mid['pp_per_1k'].mean():.1f} point near parity, where both teams already have rifles. "
    f"The rule that falls out: do not trickle money in. Either spend enough to change what is in "
    f"your hands, or keep it.",
)

t5 = pd.DataFrame(
    {
        "Equipment gap": p5["diff"].map(lambda v: "0" if v == 0 else f"{v:+,.0f}"),
        "Win rate": p5["win_rate"].map(pct),
        "Next $1,000": p5["pp_per_1k"].map(lambda v: "-" if pd.isna(v) else f"{v:+.1f}pp"),
        "Rounds": p5["rounds"].map(lambda v: f"{v:,}"),
    }
)
t5 = t5[(p5["diff"] >= -10000) & (p5["diff"] <= 10000)]
b1, b2 = st.columns([1, 1.3], gap="large")
with b1:
    st.markdown(tbl(t5), unsafe_allow_html=True)
    st.markdown(
        '<div class="note">Table covers -$10,000 to +$10,000; the chart runs to the tails.</div>',
        unsafe_allow_html=True,
    )
with b2:
    colors = [RED if v < 0 else TEAL for v in p5["diff"]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=p5["diff"], y=p5["pp_per_1k"], name="Win-rate gain",
            marker=dict(color=colors, line=dict(width=0), opacity=0.55),
            hovertemplate="Gap $%{x:,.0f}<br>%{y:+.1f}pp per $1,000<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=p5["diff"], y=p5["win_rate"] * 100, name="Win rate", yaxis="y2",
            mode="lines", line=dict(color=AMBER, width=2.2),
            hovertemplate="Gap $%{x:,.0f}<br>%{y:.1f}%<extra></extra>",
        )
    )
    base_layout(fig, 344, l=64, r=62, b=50)
    fig.update_layout(
        yaxis=dict(ticksuffix="pp", gridcolor=GRID, zerolinecolor=GRID,
                   tickfont=dict(color=MUTED)),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%",
                    tickformat=".0f", dtick=25, range=[0, 100],
                    tickfont=dict(color=MUTED)),
    )
    fig.update_xaxes(tickprefix="$", tickformat=",.0f",
                     title_text="Equipment gap (yours minus theirs)",
                     title_font=dict(size=11, color=MUTED))
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})

# ---------------------------------------------------------------- footer
st.markdown(
    f'<div class="foot">'
    f'<b>Data</b> &nbsp;43,234 maps, 2017-04-04 to 2020-03-01, from the Kaggle dataset '
    f'"CS:GO Professional Matches" by mateusdmachado. One row is one map; every stat is computed '
    f'per (match_id, _map) pair. Currently showing: {K["maps"]:,} maps, {K["rounds"]:,} '
    f'team-rounds.<br>'
    f'<b>Refresh</b> &nbsp;In production this board would rebuild nightly from the match feed and '
    f'the tournament calendar decides what arrives; the sample switch in the sidebar shows the '
    f'same numbers on the latest three months, which is what a refresh looks like. Data older '
    f'than the current patch is the main thing that goes stale here.<br>'
    f'<b>What this cannot answer</b> &nbsp;The file records a team\'s total equipment value at '
    f'round start. It does not record weapons, grenades or which player bought what, so it cannot '
    f'tell you whether to buy an AK or an M4, or how many smokes to carry. The value is a team '
    f'total, so it cannot be split per player either.'
    '</div>',
    unsafe_allow_html=True,
)

with st.expander("What the latest 3 months change"):
    cmp_df = get_compare(long, 3)
    pretty = pd.DataFrame(
        {
            "Full history": [
                f"{cmp_df.loc['rounds', cmp_df.columns[0]]:,.0f} team-rounds",
                money(cmp_df.loc["avg_equip", cmp_df.columns[0]]),
                pct(cmp_df.loc["full_buy_share", cmp_df.columns[0]]),
                pct(cmp_df.loc["win_even", cmp_df.columns[0]]),
                pct(cmp_df.loc["win_ahead10", cmp_df.columns[0]]),
                pct(cmp_df.loc["win_behind10", cmp_df.columns[0]]),
                money(cmp_df.loc["pistol_loser_r2_equip", cmp_df.columns[0]]),
                pct(cmp_df.loc["force_share", cmp_df.columns[0]]),
                f"{cmp_df.loc['force_ev', cmp_df.columns[0]]:.2f}",
            ],
            "Latest 3 months": [
                f"{cmp_df.loc['rounds', cmp_df.columns[1]]:,.0f} team-rounds",
                money(cmp_df.loc["avg_equip", cmp_df.columns[1]]),
                pct(cmp_df.loc["full_buy_share", cmp_df.columns[1]]),
                pct(cmp_df.loc["win_even", cmp_df.columns[1]]),
                pct(cmp_df.loc["win_ahead10", cmp_df.columns[1]]),
                pct(cmp_df.loc["win_behind10", cmp_df.columns[1]]),
                money(cmp_df.loc["pistol_loser_r2_equip", cmp_df.columns[1]]),
                pct(cmp_df.loc["force_share", cmp_df.columns[1]]),
                f"{cmp_df.loc['force_ev', cmp_df.columns[1]]:.2f}",
            ],
            "Change": [
                "",
                f"{cmp_df.loc['avg_equip','delta']:+,.0f}",
                f"{cmp_df.loc['full_buy_share','delta']*100:+.1f}pp",
                f"{cmp_df.loc['win_even','delta']*100:+.1f}pp",
                f"{cmp_df.loc['win_ahead10','delta']*100:+.1f}pp",
                f"{cmp_df.loc['win_behind10','delta']*100:+.1f}pp",
                f"{cmp_df.loc['pistol_loser_r2_equip','delta']:+,.0f}",
                f"{cmp_df.loc['force_share','delta']*100:+.1f}pp",
                f"{cmp_df.loc['force_ev','delta']:+.2f}",
            ],
        },
        index=[
            "Sample size", "Average equipment", "Full-buy share", "Win rate at parity",
            "Win rate at +$10k", "Win rate at -$10k", "Pistol loser, round 2 spend",
            "Share forcing $6-8k in round 2", "Two-round return of forcing",
        ],
    ).reset_index()
    pretty.columns = ["Metric", "Full history", "Latest 3 months", "Change"]
    st.markdown(tbl(pretty, wrap=True), unsafe_allow_html=True)
    st.markdown(
        '<div class="note">The win-rate lookup is the stable part: parity and both $10k bands land '
        'within a point of the full history, which is why a board built on three years of data '
        'still reads correctly on this month\'s patch. The behaviour around it did move. Teams that '
        'lose the pistol now spend more in round 2, and almost none of them force-buy at $6-8k any '
        'more, so that row of the two-round table rests on a much smaller sample in the new window '
        'and should not be read as a reversal.</div>',
        unsafe_allow_html=True,
    )
