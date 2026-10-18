# CS Economy Board

A Streamlit dashboard for ranked Counter-Strike players. It answers one question: **given what my
team can spend and what the other team is likely to spend, how much should I commit this round?**

Team: Yancheng Gong's Team

Live app: ADD_YOUR_STREAMLIT_URL_HERE

---

## 1. The dataset

Kaggle, "CS:GO Professional Matches" by mateusdmachado:
https://www.kaggle.com/datasets/mateusdmachado/csgo-professional-matches

The download contains four files. Only `economy.csv` is used here (43,234 rows, 24 MB); the other
three (`results.csv`, `picks.csv`, `players.csv`) describe series outcomes, map vetoes and player
statistics, which are not needed for an economy question.

- Coverage: 2017-04-04 to 2020-03-01, professional matches.
- One row is one map of one series. The columns `1_t1` to `30_t1` (and the `_t2` twins) hold each
  team's **total equipment value at the start of round N**, in dollars.
- Unit of analysis: the `(match_id, _map)` pair. A best-of-three shares one `match_id` across its
  maps, so merging or grouping on `match_id` alone mixes rounds from different maps and inflates
  any round-one statistic. Every number on this board is computed per `(match_id, _map)` pair.
- The data is real professional match data. The null case is `N_winner` empty, meaning the map
  ended before round N.

Columns are named from the file, not from the game: `t1_start` / `t2_start` are **not** money, they
record which side (T or CT) each team started on.

## 2. Who it is for

A ranked player who calls the buys for their team, in a five-stack or a pug. Not a coach, not an
analyst, not a viewer.

## 3. The decision it supports

> If the in-game leader sees that the other team is projected to start the round around $13,000
> while our team holds $12,000, the board prices a bought round at $18,944 (their buy plus the
> $5,944 equipment gap the average round winner holds). $12,000 does not finish that, so the call
> is the $9,472 rung — half a bought round — and $2,528 stays in the bank instead of being pushed
> into a buy that completes nothing.

The player controls exactly one lever every round: how much money to commit. They do not control
the map, the side, or the other team's plan. That is why this board has nothing on map vetoes and
nothing on side win rates as a first-class view: a ranked player cannot act on either.

Without the board, the decision is made from memory and feel, which costs real rounds. The common
failure is the force buy at $6-8k, which the data shows returns fewer wins across two rounds than
simply saving.

Why this is a dashboard and not a weekly email: the call is made about thirty times a match, before
the buy timer runs out. An email or a report arrives after the rounds it would have saved are
already lost, so the number has to be on screen while the round is live — the only format that fits
a decision made in the eight seconds between freeze time and the buy.

## 4. What is on the board, and why

The page runs top to bottom in the order a player needs it: the answer first, then the evidence.

| Section | Why it earns the space |
|---|---|
| Three headline numbers | Parity 50%, +$10k 83%, and the two-round cost of forcing. Three is the exercise's ceiling, so the pistol edge that wanted to be a fourth number lives in panel 01 instead, where it has room to be read rather than glanced at. |
| A one-line caption | Under the title, saying who the board is for and the one decision it supports, so the page explains itself before any number is read. |
| Ask the data | Two sliders (your budget, expected opponent spend) return a recommended **amount to commit**, the rung it lands on, the reasoning, the whole buy ladder with the win chance and the banked money at each level, and a chart of the call at every budget. This is the only interactive part, and it is the actual question. |
| 01 Pistol rhythm | Shows *why* the answer changes by round: the pistol winner is $19k against $6k in round 2, and level by round 4. |
| 02 After losing the pistol | The decision tree for rounds 2 and 3, plus the two-round expected value that separates a good buy from a lucky round. |
| 03 Advantage lookup | The five-band table a player can memorise: $5k is worth about 10 points, $10k about 33. |
| 04 Loss ladder | When a team can realistically buy again after losing, by straight losses. |
| 05 Value of the next $1,000 | Where the marginal dollar is worth the most, which is the argument against half-measures. |

Design choices: tables before charts, because a player reads four numbers faster than a line plot;
one accent colour; no emoji; the data period and production refresh rate stated in the footer.

How the recommendation is worked out (the same explanation is on the page, under the sliders).
Everything is measured from the file, nothing is a typed-in constant:

1. **What a bought round costs.** The average round winner enters the round **+$5,944** ahead
   (`E[equipment difference | won]`, and the losers are exactly that far behind). So a full buy is
   their expected buy plus that gap, capped at $31,400 — the 95th percentile of equipment teams
   actually field, above which a team is paying for gear it cannot put on the server.
2. **The ladder.** $0, a $2,000 pistol buy, a $7,000 force, then 50%, 75% and 100% of that price.
   Rungs closer than $1,500 apart are collapsed into one decision.
3. **The call.** The highest rung the budget actually finishes, and the change is banked. A level
   left half-bought is money spent without reaching the equipment it was spent for, which is the
   same finding panel 02 reports from the other direction (a $6-8k force returns fewer wins across
   two rounds than saving).
4. **Why it stops.** Above the full buy the number does not rise, on purpose: the observed win rate
   is 86.6% at a +$18,000 lead and 87.8% at +$22,000, so extra money is next round's buy, not this
   one's. The banked figure and the share of the bank committed keep moving with the slider.

Every percentage on the panel is the observed win rate at the resulting equipment gap, so the board
never shows a number the data does not contain.

## 5. What I chose not to show, and why

- **Map win rates and veto advice.** A ranked player cannot pick the map, so the finding would be
  interesting and unusable.
- **Side (T/CT) splits as a headline panel.** The five-band table shows T and CT separately, and
  they differ by only a few points, so a dedicated panel would not change any decision. It is one
  column instead of one panel.
- **Player-level and weapon-level analysis.** The file has neither. See the limits below.
- **A round-by-round match log.** Nobody opens a dashboard to read one match. It sits in an
  expander under panel 01, where it costs no space.

## 6. Refresh frequency

- **In production: nightly.** Professional matches are played in the evening and results are on
  HLTV within hours; nothing about an economy lookup justifies minute-level updates, and the
  Kaggle snapshot itself arrives in batches.
- **Who reviews it: weekly, by the same player.** Buy patterns shift with patches, not with days.
- **What triggers action:** a Valve economy patch (loss bonus, weapon prices) or a new sample that
  moves a headline number by more than about 3 points. In that case the board gets rebuilt on fresh
  data, not re-read.
- **Stale cost:** the loss-bonus ladder and equipment prices are the two things a patch can change
  overnight. A board that is a patch behind teaches a buy that no longer pays.
- The board states the data period in the footer. The sidebar switch rebuilds every panel on the
  latest three months in the file (2019-12 to 2020-03), which is what a refresh looks like: same
  code, same panels, new numbers. The drift check at the bottom of the page compares the two.

## 7. What this data cannot answer

- It records a team's **total equipment value** at round start. It has no weapons, no grenades, no
  kit purchases, no player-level split. So it cannot answer "AK or M4", "how many smokes", or
  "who should buy the defuse kit". The value is a team total and cannot be attributed to one player.
- It has no money-in-bank figure, only equipment value, so "how much should I keep" is inferred
  from what teams actually spent, not from their accounts.
- It cannot say why a team chose a buy. The two-round table in panel 02 is descriptive: teams that
  reach $8-16k in round 2 got there partly by playing the pistol better, so their numbers cannot be
  read as a pure causal effect of the buy. The one clean comparison the data supports is
  save versus force at the same budget.

## 8. Run it locally

Requires `uv`.

```bash
cd csgo-econ-board
uv run streamlit run app.py
```

Open http://localhost:8501. Dependencies (`streamlit`, `pandas`, `numpy`, `plotly`) are declared in
`pyproject.toml` and installed by `uv` on first run. Python 3.14.

Files:

```
app.py                 layout, charts, the budget simulator
econ.py                data reshaping and all aggregates
economy.csv            the single data file
requirements.txt       exact pinned versions exported from uv.lock, for the cloud build
.streamlit/config.toml dark theme, shared by local and cloud
pyproject.toml         uv project, Python 3.14
.gitignore
```

## 9. Deploy

1. Create the repository on GitHub (public), push this folder (the CSV must be in the repo; it is
   under the 25 MB limit).
2. Go to https://share.streamlit.io, sign in with GitHub, "Create app", "Deploy a public app from
   GitHub".
3. Repository: your repo, branch `main`, main file path `app.py`.
4. Open **Advanced settings**, set the Python version to **3.14**. No secrets are needed.
5. Deploy. The first build installs the dependencies from `pyproject.toml` and takes a few minutes.
6. The public URL is `https://<app-name>.streamlit.app`, shown at the top of the app page and in
   your workspace list.
