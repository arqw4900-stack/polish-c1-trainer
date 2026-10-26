"""Builds ../index.html from app.html + plain-text sources (words/*.txt, grammar.txt, stories.txt, letters.txt, practice.txt, writing.txt)."""
import json, pathlib, re, sys

SRC = pathlib.Path(__file__).parent
OUT = SRC.parent / "index.html"


def lines(name):
    for n, raw in enumerate((SRC / name).read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if s and not s.startswith("//"):
            yield n, s


def split(s, n=None):
    return [p.strip() for p in (s.split("|", n) if n else s.split("|"))]


def words():
    themes = []
    for f in sorted((SRC / "words").glob("*.txt")):
        th = None
        for n, s in lines(f"words/{f.name}"):
            if s.startswith("#"):
                ru, pl = split(s[1:])
                th = {"name": ru, "pl": pl, "words": []}
                themes.append(th)
                continue
            parts = split(s)
            if len(parts) != 3 or not all(parts):
                sys.exit(f"{f.name}:{n}: expected 'pl | ru | example': {s}")
            pl, ru, ex = parts
            gap = ""
            if "[" in pl:
                gap = pl[pl.index("[") + 1:pl.index("]")]
                pl = pl.replace("[", "").replace("]", "")
            th["words"].append([pl, gap, ru, ex])
    return themes


def grammar():
    out, g = [], None
    for n, s in lines("grammar.txt"):
        k, _, v = s.partition(":")
        v = v.strip()
        if s.startswith("@"):
            gid, grp, abbr, name, pl = split(s[1:])
            g = {"id": gid, "grp": grp, "abbr": abbr, "name": name, "pl": pl, "rule": [], "examples": [], "tip": "", "ex": []}
            out.append(g)
        elif k == "rule": g["rule"].append(v)
        elif k == "table": g["table"] = [split(v)]
        elif k == "row": g["table"].append(split(v))
        elif k == "e": g["examples"].append([p.strip() for p in v.split(";;")])
        elif k == "tip": g["tip"] = v
        elif k == "q": g["ex"].append(v)
        else: sys.exit(f"grammar.txt:{n}: unknown line: {s}")
    return out


def stories():
    out, st = [], None
    for n, s in lines("stories.txt"):
        k, _, v = s.partition(":")
        v = v.strip()
        if s.startswith("@"):
            sid, title, ru, topic, level, *kind = split(s[1:])
            st = {"id": sid, "title": title, "ru": ru, "topic": topic, "level": level, "kind": kind[0] if kind else "", "text": [], "gloss": {}, "q": []}
            out.append(st)
        elif k == "p": st["text"].append(v)
        elif k == "g":
            a, _, b = v.partition("=")
            st["gloss"][a.strip()] = b.strip()
        elif k == "q": st["q"].append(split(v))
        else: sys.exit(f"stories.txt:{n}: unknown line: {s}")
    return out


def letters():
    out, lt = [], None
    for n, s in lines("letters.txt"):
        k, _, v = s.partition(":")
        v = v.strip()
        if s.startswith("@"):
            lid, reg, title, ru = split(s[1:])
            lt = {"id": lid, "reg": reg, "title": title, "ru": ru, "sit": "", "body": [], "regi": [], "phr": [], "ex": []}
            out.append(lt)
        elif k == "sit": lt["sit"] = v
        elif k == "b":
            b = split(v)
            b[1] = b[1].replace("\\n", "\n")
            lt["body"].append(b if len(b) == 4 and b[3] else b[:3])
        elif k == "r": lt["regi"].append(split(v, 1))
        elif k == "f": lt["phr"].append(split(v, 1))
        elif k == "q": lt["ex"].append(v)
        else: sys.exit(f"letters.txt:{n}: unknown line: {s}")
    return out


PTYPES = {"tr": 3, "fix": 3, "para": 4, "reg": 4, "gap": 3, "cont": 4, "use": 4, "op": 3}   # fields per line


def practice():
    # tr/fix/gap: prompt | answer || answer | note;  para/reg: prompt | task | answers | note
    # cont/use: prompt | task | sample | note;  op: question | sample | note   (cont/use/op are open tasks)
    out = {t: [] for t in PTYPES}
    for n, s in lines("practice.txt"):
        k, _, v = s.partition(":")
        parts = [p.strip() for p in re.split(r"(?<!\|)\|(?!\|)", v)]   # "||" separates answers inside a field
        if k not in PTYPES or len(parts) != PTYPES[k] or not all(parts):
            sys.exit(f"practice.txt:{n}: bad line: {s}")
        if len(parts) == 4:
            q, task, ans, note = parts
        else:
            (q, ans, note), task = parts, ""
        out[k].append({"q": q, "task": task, "ans": [a.strip() for a in ans.split("||")], "note": note})
    return out


def writing():
    out, w = [], None
    for n, s in lines("writing.txt"):
        k, _, v = s.partition(":")
        v = v.strip()
        if s.startswith("@"):
            wid, kind, grp, reg, rng, title, ru = split(s[1:])
            lo, hi = map(int, rng.split("-"))
            w = {"id": wid, "kind": kind, "grp": grp, "reg": reg, "min": lo, "max": hi, "title": title, "ru": ru, "task": "", "tru": "", "pts": [], "phr": [], "model": []}
            out.append(w)
        elif k == "task": w["task"] = v
        elif k == "ru": w["tru"] = v
        elif k == "pt": w["pts"].append(v)
        elif k == "ph": w["phr"].append(split(v, 1))
        elif k == "m": w["model"].append(v)
        else: sys.exit(f"writing.txt:{n}: unknown line: {s}")
    return out


def js(name, data):
    return f"const {name} = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"


data = js("THEMES", words()) + js("GRAMMAR", grammar()) + js("STORIES", stories()) + js("LETTERS", letters()) + js("PRACTICE", practice()) + js("WRITING", writing())
html = (SRC / "app.html").read_text(encoding="utf-8").replace("/*@DATA@*/\n", data)
OUT.write_text(html, encoding="utf-8", newline="\n")
print(f"index.html: {len(html.encode())//1024} KB")
