# TradeTell design: the Intara section

TradeTell studies the Prosperity 4 market on Intara. The repository holds four recorded days of it
(Round 1 days −2, −1 and 0, and Round 2 day 1) for the two goods that the built-in Traders trade.
This document records the redesign brief, the concept and the visual system so later passes stay
consistent.

## Brief

- **Subject:** the user's IMC Prosperity 4 workbench. It reads the recorded market, replays the
  built-in Round 1 and Round 2 Traders, and answers questions from the competition wiki with
  sources.
- **Audience:** Prosperity competitors studying the goods, and people looking at the project in a
  portfolio who need to see in seconds what it does.
- **Job:** make the market legible, make a replay feel like running a Trader through real ticks,
  and keep every answer traceable to its source.
- **Constraint:** Streamlit 1.66 stays. Python owns data, replay and retrieval. The interface is
  built from Streamlit's v2 components (HTML, CSS and JavaScript mounted in the page DOM with no
  iframe and no shadow root, so headings, focus and links belong to the document), static file
  serving and theme settings, plus native chat elements for answers.
- **Loading:** Python sends every 25th mid price of the record with the first run (about 3,200
  numbers), so the section draws and the intro plays at once; the full books stream in behind it.
- **Data decision:** the old desk mixed a Prosperity 3 fixture (seashells, eight products) with
  Prosperity 4 replay samples. The redesign uses only the Prosperity 4 record, so the market you
  read and the market you replay are the same ticks. Full days are shipped as gzipped CSVs in
  `static/intara/`; the browser decompresses them itself and Python replays the same files.

## The anchor

Both goods opened at 10,000 XIRECs on day −2. Ash-Coated Osmium stayed there: its mean is within
2 XIRECs of 10,000 on every recorded day. Intarian Pepper Root climbed almost exactly 1,000 XIRECs a
day, from 9,998.5 to 13,999.5 over four days. The wiki calls it "a hardy, slow-growing root" and
calls osmium "rumored to be a bit more volatile" with "a hidden pattern". One good is a mineral and
one is a root. No other market in the genre has this shape.

## Concepts considered

| | A. The section (material) | B. The outpost (place) | C. Tells (name) |
|---|---|---|---|
| Idea | The record is cut open like ground: a flat osmium seam at 10,000 and a pepper root growing out of it | The app is the outpost seen from above; each tool is a structure that grows with profit | Each good has a tell; the app is a dossier of tells with evidence and a test |
| Anchor | the two goods' real price shapes and names | Prosperity 4's Outpost View | the name TradeTell and the wiki's "hidden pattern" |
| What the app is | one ground section, four days wide | an outpost diorama | a dossier |
| Movement | zoom from four days into one; drag a probe along ticks; switch layers in the legend | walk between buildings | read claim by claim |
| One unit | a tick, opened as a core of the order book | a building | a tell |
| Signature | the seam splits into two strata when you zoom into a day; the probe draws a core of the book | buildings rise | the claim draws its evidence |
| O / F / Fe / P / S | 4 / 5 / 4 / 1 / 4 | 3 / 4 / 2 / 2 / 5 | 3 / 4 / 4 / 3 / 3 |

**Pick A.** It is true only of this market, the data itself draws it, and every tool becomes a layer
of the same object. From C: the wiki quote about the root is the first suggested question. From B:
nothing; imitating the official game interface would read as borrowed branding.

## Concept card

```
Idea:        Four recorded days of Intara's market cut open like ground: osmium is the seam that
             never moved, pepper root is the line that grew through it.
Metaphor:    a geological section with a borehole core.
Signature:   the probe. Drag it (or use arrow keys) along the section and a core of the order book
             draws out of the ground at that tick: three asks above, three bids below, for both
             goods, with exact numbers beside it. Zooming into a day splits the seam so each good
             gets its own scale.
Emotion:     the first three seconds should feel like seeing a cut face: one flat line, one rising
             line, and the gap between them.
Motion verb: grow and settle. Lines grow forward in time; panels and readouts settle into place
             with a short heavy ease and no bounce.
Screenshot:  the four-day section with the pepper root climbing from the seam to 14,000 and the
             core open at day 1.
Structure:   the app is the section. The legend is the navigation: its layers are the views.
             Base ground is Read, "Your Trader" adds the replay layer, "Field notes" opens Ask.
             One unit is a tick (?day=0&t=412300), a day is a zoom level.
Escape hatch: ?layer=index lists every day, the goods, the views and the data notes as plain links and
             tables.
```

## Structure plan

```
DESKTOP 1440                                                          PHONE 390
┌───────────────────────────────────────────────────────────┐        ┌──────────────────┐
│ TradeTell                       Both goods opened at      │        │ TradeTell  Index │
│ Index                           10,000. Only the root grew│        │ Both goods ...   │
│                                                           │        │                  │
│ 14,000                                   ╱ pepper root    │        │ section, 4 days  │
│                                    ╱╱╱╱                   │        │ (touch: drag the │
│                         ╱╱╱╱╱╱  ┃core                     │        │  probe)          │
│            ╱╱╱╱╱╱╱              ┃                         │        │                  │
│ 10,000 ━━━━━━━━━━━━━━━━━━━━━━━━━┃━━━━━━━━ osmium seam     │        │ core readout     │
│ day −2      day −1      day 0   ┃  day 1   (click to zoom)│        │ (two ladders)    │
│                                                           │        │                  │
│ LEGEND (navigation)            CORE READOUT at the probe  │        │ layer content    │
│  Ground       ← Read           osmium ladder | root ladder│        │                  │
│  Your Trader  ← Replay         trades at this tick        │        ├──────────────────┤
│  Field notes  ← Ask                                       │        │ Ground Trader    │
│                                                           │        │ Notes  (legend)  │
│ [layer content: replay controls + result, or notes]       │        └──────────────────┘
└───────────────────────────────────────────────────────────┘
```

- `/` (Read): the section at the four-day zoom, probe at day 1. `?zoom=` opens a day;
  `?day=` and `?t=` place the probe. The core readout sits under the section, beside the legend.
- `?layer=trader`: the same section zoomed to the replay day with the Trader layer on: fills planted on
  each good's line and the Trader's equity drawn as a third stratum under the goods. Controls:
  Trader (Round 1 or Round 2), day, and public-trade matching. Results: P&L, drawdown, fills,
  rejections, volume, and P&L per good. The probe readout adds position and equity at the tick.
- `?layer=notes`: the section collapses to a thin strip (still a link back to the ground). Field notes
  hold the suggested questions, the conversation, and each answer's sources as specimen labels.
- `?layer=index`: plain links and tables; the keyboard and crawler route.
- Unknown paths fall back to Streamlit's default page with its not-found notice. Streamlit has no
  custom 404 hook, so this is a known gap.

## Art direction

**Palette** (Intara at night: basalt, ash-blue metal, pepper red)

| Role | Hex | Use |
|---|---|---|
| basalt (ground) | `#0D0E10` | page ground |
| shelf (surface) | `#16181B` | the section's bed, readout surfaces |
| dust (ink) | `#E7E9EC` | text, the Trader's equity line |
| muted | `#959CA6` | secondary text, axis labels (7.0:1 on basalt) |
| line | `rgba(231,233,236,0.12)` | hairlines, used sparingly |
| osmium | `#8EA9C6` | Ash-Coated Osmium everywhere |
| pepper | `#EE5A36` | Intarian Pepper Root everywhere |

The two hues are data encodings, not decoration: each good owns one color across the section,
ladders, labels, fills and answers.

**Type:** Archivo (Google, OFL, variable width 62 to 125 and weight 100 to 900) for everything.
Display is Archivo at width 112 and weight 800 with tracking −0.035em; text is width 100,
weight 400; readouts use tabular figures. Code in answers uses Streamlit's mono. One family, two
personalities, no mono labels.

| Token | Size | Use |
|---|---|---|
| `--t-xl` | clamp(2.4rem, 1.2rem + 4.4vw, 5.6rem) | the headline fact |
| `--t-l` | clamp(1.5rem, 1.1rem + 1.4vw, 2.4rem) | layer titles, big numbers |
| `--t-m` | 1.25rem | readout prices |
| `--t-body` | 1rem to 1.0625rem | reading text |
| `--t-s` | 0.875rem | labels, axis |

**Grid:** 12 columns, 24 px gutter, 40 px outer margin on desktop; 4 columns and 16 px on phone.
Three vertical lines carry everything: column 1 (legend, mark, axis), column 5 (readout) and
column 9 (headline, results).

**Shape:** zero radius on the section and readouts (cut faces have no rounded corners); 999 px only
on the probe handle.

**Motion:** GSAP 3.13 for tweens, on one clock (`gsap.ticker`) that also draws the canvas.
`grow` = `power2.inOut` 1.4 s for lines drawing forward; `settle` = `power3.out` 0.5 s for panels
and readouts; zoom = `expo.inOut` 0.9 s; seam split 0.7 s. Under reduced motion every line is drawn
at once, zoom cuts, and nothing drifts.

**Idle:** a faint pulse travels up the pepper root every five seconds, like sap. It is the
concept moving, it never moves data, and it stops off screen and under reduced motion.

**Interaction treatments (two):**
- Navigation (legend layers, day labels, index links): a pepper underline grows from the left,
  like a root; the current layer keeps it.
- Buttons (Run replay, suggested questions): the fill rises from the bottom like sediment.

## Genericness test

- Skeleton: one object (the section) with a legend that switches layers. Not a navbar over a hero
  with stacked sections.
- Changed after the test: the tool tabs became the section legend; the price chart became two
  strata with their own scales after zoom; the metric tiles became the core readout and one
  results line; mono labels were dropped for tabular Archivo.

## Asset list

- Mark and favicon: a seam with a root rising from its left end, drawn in Glaxnimate. The source is
  `assets/logo.svg` (also inlined in `src/ui/ground/ground.html`); `assets/logo.png` is the
  256 px render used as the page icon.
- Imagery: the recorded data, drawn live on canvas. No stock imagery and no fake screens.
