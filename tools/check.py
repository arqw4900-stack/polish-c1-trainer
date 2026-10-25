"""Checks the data inside index.html: python tools/check.py [path/to/index.html]

Words: at least 200 per theme, no duplicate Polish words, no two words with the same Russian translation.
Grammar, stories and letters: complete records and well-formed exercises. Prints a summary and exits 1 on errors.
"""
import json, re, sys, pathlib, collections

path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent.parent / "index.html")
html = path.read_text(encoding="utf-8")


def const(name):
    m = re.search(rf"^const {name} = (.*);$", html, re.M)
    if not m:
        sys.exit(f"const {name} not found")
    return json.loads(m.group(1))


errors, notes = [], []
err = errors.append

# ---------- words ----------
themes = const("THEMES")
norm = lambda s: re.sub(r"\s+", " ", s.lower()).strip()
senses = lambda ru: frozenset(p.strip() for p in re.split(r"[,;]", re.sub(r"\(.*?\)", "", ru)) if p.strip())
seen_pl, seen_ru = {}, {}
print(f"{'Тема':<28}{'слов':>6}")
for th in themes:
    ws = th["words"]
    print(f"{th['name']:<28}{len(ws):>6}")
    if len(ws) < 200:
        err(f"{th['name']}: only {len(ws)} words")
    for w in ws:
        if len(w) != 4 or not w[0] or not w[2] or not w[3] or w[1] != "":
            err(f"bad record: {w}")
            continue
        pl, _, ru, ex = w
        k = norm(pl)
        if k in seen_pl:
            err(f"duplicate Polish word: {pl} ({seen_pl[k]} / {th['name']})")
        seen_pl[k] = th["name"]
        r = senses(ru)
        if r in seen_ru:
            err(f"same Russian translation: «{ru}» — {pl} / {seen_ru[r]}")
        seen_ru[r] = pl
        if "(" in pl:
            notes.append(f"hint in Polish word: {pl}")
        if not re.search(r"[.!?…]$", ex):
            notes.append(f"example without final punctuation: {pl}: {ex}")
total = sum(len(t["words"]) for t in themes)
print(f"{'Всего':<28}{total:>6}")
shared = collections.Counter(s for r in seen_ru for s in r)
overlap = sum(1 for s, c in shared.items() if c > 1)
print(f"Русских значений, общих для нескольких слов: {overlap} (не ошибка: такие слова не ставятся вариантами друг к другу)")


def check_item(where, e):
    body, _, rest = e.partition("#")
    tid, _, why = rest.partition("#")
    parts = body.split("|")
    if len(parts) != 4 and len(parts) != 5:
        err(f"{where}: needs sentence|answer|2-3 wrong: {e[:80]}")
        return
    sent, ans, *wrong = parts
    if "___" not in sent:
        err(f"{where}: no ___ in: {sent}")
    if len(set(p.strip() for p in [ans, *wrong])) != len(parts) - 1 or not all(p.strip() for p in parts):
        err(f"{where}: empty or repeated option: {body}")
    if sent.count("___") != len(ans.split("…")):
        err(f"{where}: blanks ≠ answer parts: {body}")
    if len(why.strip()) < 15:
        err(f"{where}: no explanation: {body[:60]}")
    return tid


# ---------- grammar ----------
grammar = const("GRAMMAR")
ids = {g["id"] for g in grammar}
print(f"\nГрамматика: {len(grammar)} тем, {sum(len(g['ex']) for g in grammar)} упражнений")
for g in grammar:
    if len(g["ex"]) < 10:
        err(f"grammar {g['id']}: only {len(g['ex'])} exercises")
    if not g["rule"] or not g["examples"] or not g["tip"]:
        err(f"grammar {g['id']}: rule/examples/tip missing")
    if any(len(e) != 2 for e in g["examples"]):
        err(f"grammar {g['id']}: example without translation")
    if "table" in g and len({len(r) for r in g["table"]}) != 1:
        err(f"grammar {g['id']}: table rows of different length")
    for e in g["ex"]:
        tid = check_item(f"grammar {g['id']}", e)
        if tid and tid not in ids:
            err(f"grammar {g['id']}: unknown topic id {tid}")
    if len(set(g["ex"])) != len(g["ex"]):
        err(f"grammar {g['id']}: repeated exercise")

# ---------- stories ----------
stories = const("STORIES")
print(f"Истории: {len(stories)}")
for s in stories:
    text = " ".join(s["text"])
    nw = len(text.split())
    if len(s["q"]) != 3 or any(len(q) < 3 for q in s["q"]):
        err(f"story {s['id']}: needs 3 questions with options")
    for k in s["gloss"]:
        if not re.search(rf"(?<!\w){re.escape(k)}(?!\w)", text, re.I):
            err(f"story {s['id']}: gloss word not in text: {k}")
    print(f"  {s['id']:<14}{nw:>4} слов, {len(s['gloss'])} глосс")

# ---------- letters ----------
letters = const("LETTERS")
regs = collections.Counter(l["reg"] for l in letters)
print(f"Письма: {len(letters)} ({dict(regs)})")
if len(letters) < 10:
    err(f"only {len(letters)} letters")
for l in letters:
    if l["reg"] not in ("off", "semi", "inf"):
        err(f"letter {l['id']}: bad register {l['reg']}")
    if len(l["body"]) < 4 or any(len(b) < 3 or not all(b[:3]) for b in l["body"]):
        err(f"letter {l['id']}: incomplete body")
    if any(len(b) == 4 and b[3] not in ("r", "ra", "c") for b in l["body"]):
        err(f"letter {l['id']}: bad alignment")
    if not l["sit"] or len(l["regi"]) < 2 or len(l["phr"]) < 6 or len(l["ex"]) < 4:
        err(f"letter {l['id']}: needs situation, ≥2 register notes, ≥6 phrases, ≥4 exercises")
    if any(len(p) != 2 for p in l["regi"] + l["phr"]):
        err(f"letter {l['id']}: phrase without explanation")
    for e in l["ex"]:
        check_item(f"letter {l['id']}", e)

ids_all = [x["id"] for x in grammar + stories + letters]
for i, c in collections.Counter(ids_all).items():
    if c > 1:
        err(f"repeated id: {i}")

if notes:
    print(f"\nЗамечания ({len(notes)}):")
    for n in notes[:30]:
        print("  " + n)
if errors:
    print(f"\nОШИБКИ ({len(errors)}):")
    for e in errors[:80]:
        print("  " + e)
    sys.exit(1)
print("\nОшибок нет.")
