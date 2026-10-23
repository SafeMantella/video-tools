#!/usr/bin/env python3
"""video-camadas: pessoa | verde | faces | camadas | zoom | sfx. Local, sem API. Ver .claude/skills/video-camadas/SKILL.md"""
import argparse, io, json, re, subprocess, wave
import numpy as np
from PIL import Image

def sh(cmd): subprocess.run(cmd, check=True)
def dims(w): return w, round(w * 16 / 9 / 2) * 2
def frames(stream):  # JPEGs de um pipe image2pipe
    buf = b""
    while chunk := stream.read(1 << 20):
        buf += chunk
        while (a := buf.find(b"\xff\xd8")) >= 0 and (b := buf.find(b"\xff\xd9", a + 2)) >= 0:
            yield buf[a:b + 2]; buf = buf[b + 2:]
def jpegs(src, vf):
    return subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-vf", vf, "-f", "image2pipe", "-c:v", "mjpeg", "-q:v", "3", "-"], stdout=subprocess.PIPE)

def pessoa(a):  # Apple Vision, silhueta por frame -> vídeo cinza (ffv1)
    import Vision, Quartz, Foundation
    W, H = dims(a.w)
    req = Vision.VNGeneratePersonSegmentationRequest.alloc().initWithCompletionHandler_(None)
    req.setQualityLevel_(Vision.VNGeneratePersonSegmentationRequestQualityLevelBalanced)
    req.setOutputPixelFormat_(Quartz.kCVPixelFormatType_OneComponent8)
    wr = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", "30", "-i", "-", "-c:v", "ffv1", a.out], stdin=subprocess.PIPE)
    n = 0
    for jpg in frames(jpegs(a.video, f"scale={W}:{H},fps=30").stdout):
        h = Vision.VNImageRequestHandler.alloc().initWithData_options_(Foundation.NSData.dataWithBytes_length_(jpg, len(jpg)), None)
        h.performRequests_error_([req], None)
        pb = req.results()[0].pixelBuffer(); Quartz.CVPixelBufferLockBaseAddress(pb, 1)
        mw, mh, bpr = Quartz.CVPixelBufferGetWidth(pb), Quartz.CVPixelBufferGetHeight(pb), Quartz.CVPixelBufferGetBytesPerRow(pb)
        arr = np.frombuffer(Quartz.CVPixelBufferGetBaseAddress(pb).as_buffer(bpr * mh), np.uint8).reshape(mh, bpr)[:, :mw].copy()
        Quartz.CVPixelBufferUnlockBaseAddress(pb, 1)
        wr.stdin.write(np.asarray(Image.fromarray(arr).resize((W, H), Image.BICUBIC)).tobytes()); n += 1
    wr.stdin.close(); wr.wait(); print(f"{n} frames -> {a.out}")

def verde(a):  # tela verde (ou outra cor): matte por chromakey; cor 'auto' = média dos 2 cantos de cima do 1º frame (os de baixo costumam pegar o corpo)
    W, H = dims(a.w)
    if a.cor == "auto":
        im = Image.open(io.BytesIO(subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.video, "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"], capture_output=True, check=True).stdout)).convert("RGB")
        w, h = im.size; p = [np.asarray(im.crop(c)).reshape(-1, 3).mean(0) for c in [(0, 0, 40, 40), (w - 40, 0, w, 40)]]
        a.cor = "0x%02X%02X%02X" % tuple(int(v) for v in np.mean(p, 0))
    sh(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", a.video, "-vf", f"scale={W}:{H},fps=30,chromakey={a.cor}:{a.sim}:{a.blend},format=yuva420p,alphaextract", "-an", "-c:v", "ffv1", a.out])
    print(f"cor {a.cor} -> {a.out}")  # ponytail: sem despill; se sobrar verde na borda, subir --blend ou aplicar despill no compose

def faces(a):  # caixa do rosto a cada N s -> JSON + zona livre (coords 1080x1920)
    import Vision, Foundation
    req = Vision.VNDetectFaceRectanglesRequest.alloc().initWithCompletionHandler_(None); out = []
    for i, jpg in enumerate(frames(jpegs(a.video, f"fps=1/{a.cada},scale=1080:1920").stdout)):
        h = Vision.VNImageRequestHandler.alloc().initWithData_options_(Foundation.NSData.dataWithBytes_length_(jpg, len(jpg)), None)
        h.performRequests_error_([req], None)
        for r in (req.results() or [])[:1]:
            b = r.boundingBox(); x, y, w, hh = b.origin.x * 1080, (1 - b.origin.y - b.size.height) * 1920, b.size.width * 1080, b.size.height * 1920
            out.append({"t": round(i * a.cada, 2), "x": round(x), "head_top": round(y - .45 * hh), "chin": round(y + hh), "w": round(w)})  # ponytail: cabelo ~45% da altura do rosto acima da caixa
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"{len(out)} amostras. topo da cabeça mais alto y={min(o['head_top'] for o in out)}, queixo mais baixo y={max(o['chin'] for o in out)} (1920). Motion no topo: y < {min(o['head_top'] for o in out)}; legenda abaixo de y={max(o['chin'] for o in out)}")

def camadas(a):  # base -> atrás -> pessoa(máscara) -> frente -> tela cheia -> legenda (+ áudio)
    W, H = dims(a.w); ins = ["-i", a.base]; f = [f"[0:v]format=yuv420p[c0]"]; n = [0]; cur = ["c0"]
    def add(path, pre="", off=None, enable=None):
        ins.extend((["-itsoffset", str(off)] if off else []) + ["-i", path]); i = len(ins and [x for x in ins if x == "-i"]) - 1
        n[0] += 1; f.append(f"[{i}:v]{pre}scale={W}:{H}[l{n[0]}]")
        en = f":enable='between(t,{enable})'" if enable else ""
        f.append(f"[{cur[0]}][l{n[0]}]overlay=format=auto:eof_action=pass{en}[c{n[0]}]"); cur[0] = f"c{n[0]}"
    if a.atras: add(a.atras)
    if a.mascara:
        ins += ["-i", a.mascara]; m = len([x for x in ins if x == "-i"]) - 1
        f += [f"[{m}:v]format=gray[m]", "[0:v][m]alphamerge[pe]", f"[{cur[0]}][pe]overlay=format=auto:eof_action=pass[cp]"]; cur[0] = "cp"
    if a.frente: add(a.frente)
    if a.slot: ini, fim, p = a.slot.split(":", 2); add(p, off=float(ini), enable=f"{ini},{fim}")
    if a.legenda: add(a.legenda)
    maps = ["-map", f"[{cur[0]}]"]
    if a.audio:
        ins += ["-i", a.audio]; k = len([x for x in ins if x == "-i"]) - 1
        f.append(f"[0:a][{k}:a]amix=inputs=2:duration=first:normalize=0[au]"); maps += ["-map", "[au]"]
    else: maps += ["-map", "0:a"]
    sh(["ffmpeg", "-nostdin", "-y", "-v", "error"] + ins + ["-filter_complex", ";".join(f)] + maps + ["-c:v", "libx264", "-crf", str(a.crf), "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", a.out])
    print("ok", a.out)

def zoom(a):  # Z(t) = 1 + degraus suavizados (smoothstep), ancorado no centro. --tabela "t:zoom:dur,..."
    W, H = dims(a.w); terms, prev = [], 1.0
    for t, z, d in (map(float, s.split(":")) for s in a.tabela.split(",")):
        p = f"clip((t-{t})/{d},0,1)"; terms.append(f"({z - prev:.4f})*({p}*{p}*(3-2*{p}))"); prev = z
    ze = "1+" + "+".join(terms)
    sh(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", a.video, "-vf", f"scale={W}:{H},scale=w='2*ceil({W}*({ze})/2)':h='2*ceil({H}*({ze})/2)':eval=frame,crop={W}:{H}:'(in_w-{W})/2':'(in_h-{H})/2'", "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "copy", a.out])
    print("ok", a.out)

def sfx(a):  # cliques + whoosh/impact/riser/ding sintetizados; eventos: JSON [[t,"kind",dur?],...]
    SR, rng = 44100, np.random.default_rng(7)
    def lp(x, k):
        y, s, k = np.zeros_like(x), 0.0, np.broadcast_to(k, x.shape)
        for i in range(len(x)): s += k[i] * (x[i] - s); y[i] = s
        return y
    nm = lambda x: x / (np.abs(x).max() + 1e-9)
    def click(kind):
        f, d, g = {"main": (2600, .014, 1), "soft": (3400, .008, .55), "cut": (900, .026, 1.1)}[kind]
        t = np.arange(int(SR * d)) / SR; e = np.exp(-t / (d / 4)); k = 14 if kind == "cut" else 4
        return g * nm(.6 * np.convolve(rng.standard_normal(len(t)) * e, np.ones(k) / k, mode="same") + .8 * np.sin(2 * np.pi * f * t) * e)
    def whoosh(d=.45): t = np.linspace(0, 1, int(SR * d)); return nm(lp(rng.standard_normal(len(t)), .02 + .5 * np.sin(np.pi * t) ** 2)) * np.sin(np.pi * t) ** 1.6 * .9
    def impact(d=.4): t = np.arange(int(SR * d)) / SR; ph = 2 * np.pi * np.cumsum(40 + 70 * np.exp(-t / .05)) / SR; return nm(np.sin(ph) * np.exp(-t / .12) + .5 * lp(rng.standard_normal(len(t)), .25) * np.exp(-t / .02)) * 1.3
    def riser(d=.8): t = np.linspace(0, 1, int(SR * d)); return nm(lp(rng.standard_normal(len(t)), .01 + .35 * t ** 2)) * t ** 1.5 * .6
    def ding(d=.6): t = np.arange(int(SR * d)) / SR; return nm(np.sin(2 * np.pi * 1568 * t) + .4 * np.sin(2 * np.pi * 2352 * t)) * np.exp(-t / .16) * .5
    K = {"main": (lambda d: click("main"), 1), "soft": (lambda d: click("soft"), 1), "cut": (lambda d: click("cut"), 1), "whoosh": (lambda d: whoosh(d or .45), .8), "impact": (lambda d: impact(), 1.1), "riser": (lambda d: riser(d or .8), .55), "ding": (lambda d: ding(), .5)}
    out = np.zeros(int(SR * a.dur))
    for e in json.load(open(a.eventos)):
        fn, g = K[e[1]]; c = fn(e[2] if len(e) > 2 else None) * a.peak * g; i = int(e[0] * SR)
        if i + len(c) < len(out): out[i:i + len(c)] += c
    with wave.open(a.out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
    print("ok", a.out)

def self_check():
    assert dims(960) == (960, 1706) and dims(2160) == (2160, 3840)
    print("self-check ok")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__); s = p.add_subparsers(dest="cmd", required=True)
    def sub(name, fn, *args, **kw):
        q = s.add_parser(name); q.set_defaults(fn=fn)
        for flag, d in args: q.add_argument(flag, **d)
        return q
    sub("pessoa", pessoa, ("video", {}), ("out", {}), ("--w", {"type": int, "default": 960}))
    sub("verde", verde, ("video", {}), ("out", {}), ("--w", {"type": int, "default": 960}), ("--cor", {"default": "auto"}), ("--sim", {"default": "0.15"}), ("--blend", {"default": "0.08"}))
    sub("faces", faces, ("video", {}), ("out", {}), ("--cada", {"type": float, "default": 1.0}))
    sub("camadas", camadas, ("base", {}), ("out", {}), ("--w", {"type": int, "default": 960}), ("--atras", {}), ("--mascara", {}), ("--frente", {}), ("--slot", {"help": "ini:fim:arquivo"}), ("--legenda", {}), ("--audio", {}), ("--crf", {"type": int, "default": 24}))
    sub("zoom", zoom, ("video", {}), ("out", {}), ("--w", {"type": int, "default": 960}), ("--tabela", {"required": True, "help": "t:zoom:dur,..."}))
    sub("sfx", sfx, ("eventos", {}), ("out", {}), ("--dur", {"type": float, "required": True}), ("--peak", {"type": float, "default": 0.038}))
    sub("self-check", lambda a: self_check())
    a = p.parse_args(); a.fn(a)
