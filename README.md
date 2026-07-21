# LOTRAutofill

Build [MakePlayingCards](https://www.makeplayingcards.com/) (MPC) proxy orders
for **The Lord of the Rings LCG**, à la MPC Autofill.

The tool reads a folder of card images (organised by set / scenario / category)
plus the `cardlist.txt` quantity files, and produces a **build manifest**: the
exact list of front images, back images and quantities to order. A later stage
will drive the MPC website from that manifest.

Zero external dependencies — pure Python standard library (3.10+).

## Run it

With Python: `python -m lotrautofill <command>` (see commands below).

Or build a **standalone executable** (no Python needed to run it afterwards):

```sh
pip install -e .[build]
python build_exe.py            # -> dist/lotr-autofill.exe
dist/lotr-autofill sets        # then use it like the CLI
```

The `.exe` bundles `build` / `pick` / `export` / `sets`. The `autofill` command
still needs Python on the machine (the mpc-autofill desktop tool is a Python
app); the executable finds it on PATH automatically.

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
    -o MPC_XML/hobbit.json
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
| Same number, **different** names | **double-sided** card(s); an even count is paired into consecutive couples (1st+2nd, 3rd+4th, …) in file order |
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

### Put your cards in `sets_folder/`

Drop your set folders and the `Card_Backs` folder into **`sets_folder/`** (see
`sets_folder/README.md`). That directory is git-ignored, so your card images are
never committed. `sets` and `pick` scan `sets_folder/` automatically.

### Pick set(s) and print

```sh
python -m lotrautofill pick             # scans sets_folder/, lists sets, you choose
```

`pick` lists the set folders it finds in `sets_folder/` (e.g. `03 - Khazad-dûm`,
`19 - The Hobbit Saga`), lets you select one or several, then for each writes a
manifest **and** an `order.xml` into `MPC_XML/`.

**Chapters.** Some sets are split into chapters (a saga or cycle — e.g.
`19 - The Hobbit Saga` → `01 - Over Hill and Under Hill`, `02 - On the
Doorstep`). When a selected set has chapters, `pick` asks which to print (all,
or a subset) and writes **one `order.xml` per chapter**, so each stays a
sensible MPC project size. Plain boxes (no chapters) produce one `order.xml`.

### Run the desktop tool (one command)

`autofill` clones the mpc-autofill desktop tool (once, into
`~/.lotr-autofill/`), sets up its virtualenv, and runs it on your `order.xml`:

```sh
python -m lotrautofill autofill MPC_XML/03-khazad-dum.order.xml          # drive MPC
python -m lotrautofill autofill MPC_XML/03-khazad-dum.order.xml --pdf    # PDF proof
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
python -m lotrautofill export MPC_XML/hobbit.json    # a manifest -> order.xml
python -m lotrautofill export … --stock "(S33) Superior Smooth" --foil
```

### Import a player deck from RingsDB

Print a whole player deck by importing it from [RingsDB](https://ringsdb.com):

```sh
python -m lotrautofill deck mydeck.txt          # a decklist .txt file
python -m lotrautofill deck 12345               # a RingsDB decklist id
python -m lotrautofill deck https://ringsdb.com/decklist/view/12345/…   # or URL
```

A `.txt` decklist has one card per line with a quantity — `3x Gandalf`,
`2 Steward of Gondor`, `Sneak Attack x3` (a trailing `(Pack)` and section
headers/comments are ignored). Card names are resolved against RingsDB with the
same normalized + fuzzy matching (so `Sneak Atack` → `Sneak Attack`) and an
`order.xml` is written to `MPC_XML/`. Every card gets the Player back
(auto-detected in `sets_folder/Card_Backs`, or `--player-back`). Then run `autofill`
on it as usual.

Downloaded card images are **temporary**: they go to a folder in the OS temp
directory (never inside the repo, so they are never committed to git), and
`autofill` deletes the ones it uploaded once the MPC import is done (pass
`--keep-images` to keep them).

### Card library database

`db` indexes the whole library into `MPC_XML/database.json` (sets → chapters →
categories → cards, with counts) — the data a UI reads to browse the collection:

```sh
python -m lotrautofill db                 # index sets_folder/ -> database.json
python -m lotrautofill db --missing-only  # only sets with something to review
```

It also lists `cardlist.txt` entries that matched no image (a small "review"
list — usually double-sided encounter cards named `SideA/SideB`). Note: a
reliable per-card *missing* list can't come from the folders alone (within a
pack all categories share one number sequence, so gaps flag other folders'
cards), and RingsDB only lists player-side cards — so encounter cards can't be
verified against a reference.

### order.xml format

Matches the desktop tool exactly: `<details>` (quantity / stock / foil),
`<fronts>` and `<backs>` (each `<card>` = one image `<id>` path + the 0-indexed
`<slots>` it fills), and a single `<cardback>` (the most common back — for LOTR
the Encounter back — used for every slot not listed under `<backs>`). Quest and
double-sided backs land in `<backs>`; the Player back too.

### Built-in driver (optional)

A self-contained Playwright driver (`upload` command, `mpc.py`) is also included.
Its editor automation is **ported from mpc-autofill's proven `driver.py`**: it
uploads each image to `#uploadId` and places it into each of its exact slots via
`PageLayout.prototype.applyDragPhoto(...)` (per-slot insert, not blind autofill),
paging fronts → backs → review and stopping before checkout. It is secondary to
the `autofill` path and should be validated on a live logged-in run.

```sh
pip install -e .[upload] && playwright install chromium
python -m lotrautofill upload MPC_XML/hobbit.json --dry-run   # plan only, no deps
python -m lotrautofill upload MPC_XML/hobbit.json             # drive MPC (headed)
```

## Status / roadmap

- [x] **Stage 1 — build:** folder → manifest + validation report.
- [x] Same-number front/back pairing, errata, orphans, interactive resolution.
- [x] **Stage 2 — plan:** manifest → ordered upload plan (`--dry-run`), tested.
- [x] **Stage 2 — export:** manifest → mpc-autofill `order.xml` (local files).
- [x] **Stage 2 — pick:** choose set folder(s) → manifest + order.xml each.
- [x] **Stage 2 — autofill:** one-command clone/install/run of the desktop tool.
- [x] **Optional driver:** Playwright upload/insert ported from mpc-autofill.
- [x] **Chapters:** print all chapters of a set, or pick chapters per set.
- [x] **Executable:** `build_exe.py` packages the CLI as a standalone binary.
- [x] **Deck import:** `deck` reads a decklist `.txt`/id/URL and fetches RingsDB.
- [ ] **GUI:** a web/desktop front-end over the CLI (CLI stays supported).

## Development

```sh
python run_tests.py     # zero-dependency runner
python -m pytest        # also works if pytest is installed
```
