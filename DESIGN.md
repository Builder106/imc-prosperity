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

## Hero: say what TradeTell is for

The first redesign opened on the market's shape ("Both goods opened at 10,000. Only the root grew.")
and left the purpose to a small "market workbench" label. Visitors could not tell what the page
was for. The hero now follows Prosperity's own: a headline that names the thing, a paragraph that
says what it is and who it is for, and a row of actions.

- Wordmark subtitle (every layer): "Study tools for IMC Prosperity 4".
- Ground headline: "Read the market. Replay a Trader." then "Ask the wiki." in the gradient. One
  clause per tool.
- Lede: what TradeTell is, then what each tool does with the recorded data.
- Actions (ground only): "Open the order book" (primary; scrolls to the section and focuses the
  probe), "Replay a Trader", "Ask the wiki".
- The market fact moved into the chart card's title, with the two goods' behavior as its note. A
  zoomed day changes the card, never the hero. The other layers keep their own headlines (the
  replay result, Field notes, the index).

## Art direction

The section concept stays. Its visual language now follows the official Prosperity 4 site
(prosperity.imc.com), so the workbench looks like it belongs to the competition it studies. This
reverses the earlier call against borrowing the game's look. TradeTell keeps its own name and mark
and does not use IMC's logo or the PROSPERITY wordmark.

**Palette** (Prosperity's deep space)

| Role | Hex | Use |
|---|---|---|
| space (ground) | `#000000` | page ground; `static/stars.svg` sits behind the hero only and fades out |
| card underlay | `rgba(0,0,0,0.72)` | the section, readout and Trader cards, so stars never sit under data |
| navy | `#012649` | the footer band, the user's chat avatar |
| glass | `rgba(0,25,49,0.6)` | secondary controls: layers, Trader options, the menu, the mark's tab |
| IMC blue | `rgba(7,81,226,0.6)` | the current layer, pressed options |
| ring | 110° white, 0.3 to 0.05 to 0.3 | a 1 px masked gradient edge on every glass control (`.tt-glass`) |
| line | `rgba(255,255,255,0.1)` | card hairlines, table rules, FAQ rows |
| ink | `#FFFFFF` | text, ledes, fill marks |
| muted | `#9FB0C8` | secondary text, axis labels |
| headline gradient | `#B2CCFF` to `#6095FB` at 98° | the second line of every headline, card titles, index headings |
| glare | `#FDD681` | the gold line and glow along the top edge |
| osmium | `#8FD3E8` | Ash-Coated Osmium everywhere |
| pepper | `#FF7A3D` | Intarian Pepper Root everywhere (the orange of Intara's ground) |

The two goods keep one color each across the section, ladders, labels and fills. The Trader's P&L
is drawn as Prosperity's own line graph: the headline gradient as a stroke, a cyan glow
(`rgba(0,225,255,0.85)`, blur 13) and a navy area fill (`#0A2C60` at 0.32 fading to nothing).
The goods get a softer glow in their own color and an area fill that fades to the floor. Probe
dots are Prosperity's graph nodes: a 0.25 halo, then a dot in a 1.2 px white ring.

**Type:** Oswald 600, uppercase, for the wordmark, headlines, card titles, layer names, day labels
and big numbers. Figtree for text, as the open stand-in for Prosperity's Mark Pro. Both load from
Google Fonts through the Streamlit theme. The wordmark is tracked at 0.62em with a dimmed `P4`
after it, the way Prosperity dims the `4` in its own.

| Token | Size | Use |
|---|---|---|
| `--t-xl` | clamp(2rem, 1.3rem + 2vw, 3rem) | the hero headline (48 px, Prosperity's hero size) |
| `--t-l` | clamp(1.6rem, 1.2rem + 1.4vw, 2.5rem) | readout prices |
| `--t-card` | 1.5rem | card titles in the gradient |
| lede | 1.0625rem to 1.25rem, weight 500, white | the sentence under the headline |
| button | 0.75rem, weight 500, uppercase | every glass control label |

**Grid:** Prosperity's 1184 px content column, centered, with a 40 px margin (16 px on phone).
Inside it, 12 columns with a 24 px gutter: the legend takes columns 1 to 3 and the readout card
starts at column 4; on the Trader layer the readout spans 4 to 7 and the Trader card 8 to 12.
Field notes and the index hang from column 4 too. The plot's inner margin is 28 px (12 px on
phone) and matches `frame()` in `ground.js`.

**Shape:** cards have 15 px corners, 24 px padding and a hairline. Glass buttons are 48 px pills
(40 px radius); layers are 15 px; the menu is Prosperity's 48 px icon button with 14 px corners.
The chart frame carries viewfinder corners like Prosperity's video frames (hidden on phone, where
they would crowd the labels). The mark hangs from the glare in a glass tab.

**Bands:** the page is black; the footer is a full-width navy band with stacked uppercase links
and a line saying the tool is not made by or affiliated with IMC.

**Motion:** GSAP 3.13 for tweens, on one clock (`gsap.ticker`) that also draws the canvas.
`grow` = `power2.inOut` 1.4 s for lines drawing forward; `settle` = `power3.out` 0.5 s for panels
and readouts; zoom = `expo.inOut` 0.9 s; seam split 0.7 s. Under reduced motion every line is drawn
at once, zoom cuts, and nothing drifts.

**Idle:** a faint pulse travels up the pepper root every five seconds, like sap. It is the
concept moving, it never moves data, and it stops off screen and under reduced motion.

**Interaction treatments (two):**
- Navigation and options (layers, Trader settings, the menu): glass that lifts 2 px and darkens to
  navy on hover; the current or pressed one takes the IMC blue. Day labels and footer links grow a
  gradient underline from the left.
- Suggested questions: Prosperity's FAQ rows, one hairline each, with a plus that turns a quarter
  on hover.

## Genericness test

- Skeleton: one object (the section) with a legend that switches layers. Not a navbar over a hero
  with stacked sections.
- Changed after the test: the tool tabs became the section legend; the price chart became two
  strata with their own scales after zoom; the metric tiles became the core readout and one
  results line; mono labels were dropped for tabular figures.

## Asset list

- Mark and favicon: a seam with a root rising from its left end, drawn in Glaxnimate. The source is
  `assets/logo.svg` (also inlined in `src/ui/ground/ground.html`); `assets/logo.png` is the
  256 px render used as the page icon.
- Starfield: `static/stars.svg`, a seeded 1920 by 1000 sky with a Milky Way band, a few haloed
  bright stars and a fade to transparent at the bottom.
- Imagery: the recorded data, drawn live on canvas. No stock imagery and no fake screens.
