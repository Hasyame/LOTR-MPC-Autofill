# sets_folder/ — your card library

Put your **set folders** here. The **`Card_Backs/`** folder (the shared
encounter/player backs) and this README **are** tracked in git — everyone needs
the same backs. Your **set folders and the cards inside them are git-ignored**,
so your (large) card images are never committed or pushed.

**Naming:** name set/chapter folders in **English**. A leading `NN - ` number is
**optional** — it only controls display order; the tool finds sets and matches
them (to Hall of Beorn, RingsDB, …) with or without it. So `Core Set` and
`01 - Core Set` both work.

Expected layout:

```
sets_folder/
├── Card_Backs/Card_Backs/       Encounter Card Back.jpg, Player Card Back.jpg, …
├── 03 - Khazad-dûm/             a set
├── 19 - The Hobbit Saga/        another set
└── …                            add as many sets as you like
```

Each set folder follows:

```
<Set>/<Set>/<optional scenario>/
    Encounter/<encounter set>/   NNN - Name.jpg + cardlist.txt
    Nightmare/…                  (same)
    Player/                      NNN - Name.jpg
    Quest/                       NNN - 1A / 1B - Name.jpg
```

The tool discovers whatever is here at run time — just drop in a new set folder
and it shows up:

```sh
python -m lotrautofill sets      # lists every set in sets_folder/
python -m lotrautofill pick      # choose set(s) -> MPC_XML/<set>.order.xml
```
