# sets_folder/ — your card library (never committed)

Put your **set folders** and the **`Card_Backs`** folder here. Everything in
this directory except this README is git-ignored, so your (large) card images
are never committed or pushed.

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
