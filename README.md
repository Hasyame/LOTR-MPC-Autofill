# LOTRAutofill

Build [MakePlayingCards](https://www.makeplayingcards.com/) (MPC) proxy orders
for **The Lord of the Rings LCG**, à la MPC Autofill.

The tool reads a folder of card images (organised by set / scenario / category)
plus the `cardlist.txt` quantity files, and produces a **build manifest**: the
exact list of front images, back images and quantities to order. A later stage
will drive the MPC website from that manifest.

Zero external dependencies — pure Python standard library (3.10+).

## Expected folder layout

```
<Set>/<Set>/
    Encounter/<Encounter set>/  NNN - Name.jpg + cardlist.txt   (quantities)
    Nightmare/<Encounter set>/  NNN - Name.jpg + cardlist.txt   (quantities)
    Player/                     NNN - Name.jpg                  (1 copy each)
    Quest/                      NNN - 1A - Name.jpg / 1B ...     (double-sided)
Card_Backs/Card_Backs/          Encounter Card Back.jpg, Player Card Back.jpg
```

Campaign boxes add a scenario level (`<Set>/<Set>/<Scenario>/<category>/…`);
both layouts are detected automatically.

### Filename convention

- `NNN - Name.jpg` — card number + name.
- `NNN - 1A - Name.jpg` — quest cards: `stage` + `side` (A = front, B = back).
- `NNN - Name (errata).jpg` — errata variant of the same card number.
- Apostrophes in names become `_` on disk (`Thror's Map` → `Thror_s Map.jpg`);
  matching is normalization- and typo-tolerant.

## Usage

```sh
# From the LOTRAutofill folder:
python -m lotrautofill build "03 - Khazad-dûm"

# Options
python -m lotrautofill build "19 - The Hobbit Saga" \
    --errata prefer \        # prefer | skip | both
    --player-copies 1 \      # copies of each Player card (no cardlist)
    --backs-dir "Card_Backs/Card_Backs" \
    --non-interactive \      # accept defaults, never prompt (default: prompt in a TTY)
    -o builds/hobbit.json
```

The command prints a report and writes `mpc_manifest.json` (unless
`--no-manifest`). The report highlights anything that needs a human eye:

- **Double-sided pairs** — two images auto-paired into one card: A/B quest
  sides, or two images sharing a number (e.g. Nightmare `001 - Flight` +
  `001 - Setup`). Verify which side is the face.
- **Fuzzy matches** — a cardlist name matched a file only approximately
  (spelling/typo). Verify these.
- **Unmatched cardlist entries** — a cardlist line matched no file.
- **Orphan sides** — an A/B side with no partner (branching quests, Nightmare
  quest-back replacements). Non-player orphans get the Encounter back by
  default; use interactive mode to attach them to the right face.
- **Auto-included** — images not referenced by their `cardlist.txt`, added at 1.

### Card matching rules

| Case | Handling |
|---|---|
| Same number, **same** name (one `(errata)`) | errata duplicate → collapsed (`--errata`) |
| Same number, **different** names | one **double-sided** card (face/back) |
| `NNN - 1A` + `NNN - 1B` | double-sided quest card (A = face, B = back) |
| A/B side with no partner | orphan → Encounter back (or interactively attach a face) |
| Encounter/Nightmare single | quantity from `cardlist.txt`; Encounter back |
| Player single | `--player-copies` (default 1); Player back |

### Interactive mode

When run in a terminal, the tool prompts for the ambiguous cases: the common
back per category, which image is the face of a same-number pair, and which
face/back to give an orphan. Every prompt has a default, so `--non-interactive`
(or piping) produces a manifest without blocking.

## Manifest format

```json
{
  "summary": { "unique_cards": 203, "total_slots": 390, ... },
  "cards": [
    {
      "front": "…/076 - Wild Wargs.jpg",
      "back":  "…/Card_Backs/Card_Backs/Encounter Card Back.jpg",
      "quantity": 4,
      "name": "Wild Wargs",
      "number": "076",
      "category": "Encounter",
      "double_sided": false,
      "source": "…/Dungeons Deep and Caverns Dim",
      "match": "exact"
    }
  ],
  "unmatched_cardlist": [], "fuzzy_matches": [], "double_sided_pairs": [],
  "orphans": [], "auto_included": [], "warnings": []
}
```

## Stage 2 — order (MakePlayingCards)

The robust path reuses the proven **[chilli-axe/mpc-autofill](https://github.com/chilli-axe/mpc-autofill)
desktop tool**, which already drives MakePlayingCards reliably and supports
**local images** (a card whose `<id>` is a path that exists on disk is used
directly as a `Local File`). LOTRAutofill's job is the LOTR-specific part —
understanding sets, cardlists, quest A/B, errata and backs — and emitting an
`order.xml` the desktop tool consumes.

### Put your cards in `toPrint/`

Drop your set folders and the `Card_Backs` folder into **`toPrint/`** (see
`toPrint/README.md`). That directory is git-ignored, so your card images are
never committed. `sets` and `pick` scan `toPrint/` automatically.

### Pick set(s) and print

```sh
python -m lotrautofill pick             # scans toPrint/, lists sets, you choose
```

`pick` lists the set folders it finds in `toPrint/` (e.g. `03 - Khazad-dûm`,
`19 - The Hobbit Saga`), lets you select one or several, then for each writes a
manifest **and** an `order.xml` into `builds/`.

### Run the desktop tool (one command)

`autofill` clones the mpc-autofill desktop tool (once, into
`~/.lotr-autofill/`), sets up its virtualenv, and runs it on your `order.xml`:

```sh
python -m lotrautofill autofill builds/03-khazad-dum.order.xml          # drive MPC
python -m lotrautofill autofill builds/03-khazad-dum.order.xml --pdf    # PDF proof
```

The live run uploads your local images, autofills the slots, and stops for you
to review and pay (you sign in yourself). `--pdf` renders the whole order to a
PDF instead of driving the site.

Run `autofill` from a **real Windows terminal (PowerShell or cmd)** — the
desktop tool uses an interactive console UI that does not work under Git Bash.
The first run clones the tool and installs its runtime dependencies (a few
minutes); later runs reuse them. Pass `--skip-install` once set up.

> Validated end to end: the desktop tool's own parser reads a LOTRAutofill
> `order.xml`, resolves every image as a `Local File`, and accepts the
> `(S33) Superior Smooth` cardstock — 0 errors.

Related commands:

```sh
python -m lotrautofill sets                         # just list printable sets
python -m lotrautofill export builds/hobbit.json    # a manifest -> order.xml
python -m lotrautofill export … --stock "(S33) Superior Smooth" --foil
```

### order.xml format

Matches the desktop tool exactly: `<details>` (quantity / stock / foil),
`<fronts>` and `<backs>` (each `<card>` = one image `<id>` path + the 0-indexed
`<slots>` it fills), and a single `<cardback>` (the most common back — for LOTR
the Encounter back — used for every slot not listed under `<backs>`). Quest and
double-sided backs land in `<backs>`; the Player back too.

### Built-in driver (optional)

A self-contained Playwright driver (`upload` command, `mpc.py`) is also
included, with the MPC product-config selectors and editor flow wired from a
live session. It is secondary to the mpc-autofill path; the one unfinished piece
is the async photo-popup's file-input selector. `--dry-run` shows the plan with
no browser and no dependencies.

## Status / roadmap

- [x] **Stage 1 — build:** folder → manifest + validation report.
- [x] Same-number front/back pairing, errata, orphans, interactive resolution.
- [x] **Stage 2 — plan:** manifest → ordered upload plan (`--dry-run`), tested.
- [x] **Stage 2 — export:** manifest → mpc-autofill `order.xml` (local files).
- [x] **Stage 2 — pick:** choose set folder(s) → manifest + order.xml each.
- [x] **Stage 2 — autofill:** one-command clone/install/run of the desktop tool.
- [ ] Optional: finish the built-in Playwright driver's photo-popup selector.

## Development

```sh
python run_tests.py     # zero-dependency runner
python -m pytest        # also works if pytest is installed
```
