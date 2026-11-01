#!/usr/bin/env python3
"""Proposed replacement for /workspace/podcast/build/make_audio.py (NOT installed).

Usage (backward compatible):
  make_audio_proposed.py <script.txt> <out.mp3> [rate]          # rate overrides both voices
  options: --male-rate +10% --female-rate +5% --gap 0.25 --no-normalize --check

Changes vs current:
 1. Per-voice rate (male +10%, female +5% by default; Xiaoxiao sounds rushed/choppy at +10%).
 2. Text normalisation before TTS: Arabic numbers -> Chinese words (years digit by digit,
    percentages, decimals, 2+measure -> 两), "/" in names removed, full-width punctuation,
    guaranteed sentence-final punctuation.
 3. Each segment's leading/trailing silence is trimmed and a fixed, short gap is inserted
    (edge-tts adds ~0.17s lead + ~0.5s tail, i.e. ~0.7s dead air at every turn change,
    which makes the dialogue sound read rather than chatted).
 4. Lint pass (always printed; --check = lint + word-segmentation dump, no audio):
    greeting openers, clauses > 22 chars without punctuation, Latin text, and the
    TTS front-end's own word segmentation so wrong splits (e.g. "上 海这边", "反 超大胜",
    "坐 着 陆器", "叫 停司法部") can be spotted and rewritten before synthesis.
"""
import asyncio, sys, subprocess, os, re, argparse, tempfile
import edge_tts

V = {"男": "zh-CN-YunyangNeural", "女": "zh-CN-XiaoxiaoNeural"}

D = "零一二三四五六七八九"
def int_cn(n: int) -> str:
    if n == 0: return "零"
    if n >= 10**8: return int_cn(n // 10**8) + "亿" + (("零" if n % 10**8 < 10**7 else "") + int_cn(n % 10**8) if n % 10**8 else "")
    if n >= 10**4: return int_cn(n // 10**4) + "万" + (("零" if n % 10**4 < 1000 else "") + int_cn(n % 10**4) if n % 10**4 else "")
    s, units, zero = "", [(1000, "千"), (100, "百"), (10, "十"), (1, "")], False
    for u, name in units:
        q = n // u; n %= u
        if q:
            if zero: s += "零"; zero = False
            s += D[q] + name
        elif s: zero = True
    if s.startswith("一十"): s = s[1:]
    return s.rstrip("零")
def dec_cn(t: str) -> str:
    if "." in t:
        a, b = t.split(".", 1)
        return int_cn(int(a)) + "点" + "".join(D[int(c)] for c in b)
    return int_cn(int(t))

MEASURE = "个位枚架张名人天场次项家所条艘颗只"
def normalize(t: str) -> str:
    t = t.replace(",", "，").replace("?", "？").replace("!", "！").replace(":", "：").replace(";", "；")
    t = re.sub(r"\b[rR]/(\w+)", r"\1", t)                     # r/worldnews -> worldnews
    t = t.replace("/", "、")
    t = re.sub(r"(\d{4})年", lambda m: "".join(D[int(c)] for c in m.group(1)) + "年", t)   # 1982年 -> 一九八二年
    t = re.sub(r"(\d+(?:\.\d+)?)%", lambda m: "百分之" + dec_cn(m.group(1)), t)
    t = re.sub(r"(?<![\d.])2(?=[" + MEASURE + "])", "两", t)
    t = re.sub(r"\d+(?:\.\d+)?", lambda m: dec_cn(m.group(0)), t)
    t = re.sub(r"\s*([\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", r"\1", t)  # stray spaces between hanzi
    t = t.strip()
    if t and t[-1] not in "。！？…”": t += "。"
    return t

GREET = re.compile(r"欢迎(大家)?收听|哈喽大家好|大家好|各位听众")
def lint(segs):
    warn = []
    for i, (who, t) in enumerate(segs):
        if i < 3 and GREET.search(t): warn.append(f"[{i}] greeting opener: {t[:20]}")
        for c in re.split(r"[，。！？；：、…]", t):
            if len(c) > 22: warn.append(f"[{i}] long clause ({len(c)} chars) without pause: {c}")
        if re.search(r"[A-Za-z]{2,}", t): warn.append(f"[{i}] Latin text, check reading: {re.findall(r'[A-Za-z][A-Za-z ]+', t)}")
    return warn

async def segmentation(t, v, rate):
    c = edge_tts.Communicate(t, v, rate=rate, boundary="WordBoundary"); ws = []
    async for ch in c.stream():
        if ch["type"] == "WordBoundary": ws.append(ch["text"])
    return " ".join(ws)

def trim(src, dst):
    # strip leading + trailing silence (reverse trick), keep 60 ms tail so words aren't clipped
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,"
          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", af, "-ac", "1", "-ar", "24000", dst], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("out", nargs="?"); ap.add_argument("rate", nargs="?")
    ap.add_argument("--male-rate", default="+10%"); ap.add_argument("--female-rate", default="+5%")
    ap.add_argument("--female-voice", default=V["女"]); ap.add_argument("--male-voice", default=V["男"])
    ap.add_argument("--gap", type=float, default=0.25, help="silence between turns (s)")
    ap.add_argument("--no-normalize", action="store_true"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    V["女"], V["男"] = a.female_voice, a.male_voice
    rates = {"男": a.rate or a.male_rate, "女": a.rate or a.female_rate}
    segs = []
    for l in open(a.script, encoding="utf-8"):
        m = re.match(r"^\s*(男|女)[：:](.*)$", l)
        if m and m.group(2).strip():
            t = m.group(2).strip()
            segs.append((m.group(1), t if a.no_normalize else normalize(t)))
    for w in lint(segs): print("LINT", w, file=sys.stderr)
    if a.check:
        async def chk():
            for i, (who, t) in enumerate(segs):
                print(f"{i:02d} {who} | {await segmentation(t, V[who], rates[who])}")
        asyncio.run(chk()); return
    if not a.out: sys.exit("need out.mp3")
    d = os.path.join(os.path.dirname(os.path.abspath(a.out)), "segs"); os.makedirs(d, exist_ok=True)
    async def synth():
        files = []
        for i, (who, t) in enumerate(segs):
            raw, wav = f"{d}/{i:03d}.mp3", f"{d}/{i:03d}.wav"
            for k in range(3):
                try: await edge_tts.Communicate(t, V[who], rate=rates[who]).save(raw); break
                except Exception:
                    if k == 2: raise
                    await asyncio.sleep(2)
            trim(raw, wav); files.append(wav)
        return files
    files = asyncio.run(synth())
    gap = f"{d}/gap.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(a.gap), gap], check=True)
    lst = f"{d}/list.txt"
    with open(lst, "w") as fh:
        for i, f in enumerate(files):
            fh.write(f"file '{f}'\n")
            if i < len(files) - 1: fh.write(f"file '{gap}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "24000", "-b:a", "128k", a.out], check=True)
    print("segments", len(segs))

if __name__ == "__main__":
    main()
