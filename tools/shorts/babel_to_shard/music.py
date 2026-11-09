# Original soundtrack for "Babel to the Shard" (48 s), composed in code by Claude.
import numpy as np, wave
SR = 44100; T = 48.0; n = int(SR * T); t = np.arange(n) / SR
def note(f): return 440 * 2 ** ((f - 69) / 12)
def env(a, d, start, length):
    e = np.zeros(n); i0 = int(start * SR); i1 = min(n, int((start + length) * SR)); k = np.arange(i1 - i0) / SR
    e[i0:i1] = np.minimum(1, k / a) * np.exp(-k / d); return e
out = np.zeros(n)
# pad: D minor -> Bb -> F -> C -> (hop) Gm -> Bb -> resolve D major at the Shard
chords = [(0, [50, 57, 62, 65]), (6, [46, 53, 58, 62]), (12, [41, 48, 53, 57]), (17, [48, 55, 60, 64]),
          (22, [43, 50, 55, 58]), (27, [46, 53, 58, 62]), (32, [50, 57, 62, 66]), (40, [45, 52, 57, 61]), (44, [50, 57, 62, 66])]
for i, (s, ns) in enumerate(chords):
    L = (chords[i + 1][0] if i + 1 < len(chords) else T) - s + 1.5
    w = np.zeros(n); i0 = int(s * SR); i1 = min(n, int((s + L) * SR)); k = np.arange(i1 - i0) / SR
    shape = np.minimum(1, k / 1.2) * np.minimum(1, (L - k) / 1.5)
    for m in ns:
        f = note(m)
        w[i0:i1] += (np.sin(2 * np.pi * f * k) + 0.4 * np.sin(2 * np.pi * f * 2.003 * k) + 0.2 * np.sin(2 * np.pi * f * 0.5 * k)) * shape
    out += 0.05 * w
# heartbeat pulse (wooden wheel turning) during Babel 6-17 s, then ticking faster on the hop
for b in np.arange(6, 17, 0.75): out += 0.35 * np.sin(2 * np.pi * 55 * t) * env(0.005, 0.12, b, 0.4)
for b in np.arange(17, 32, 0.375): out += 0.22 * np.sin(2 * np.pi * 70 * t) * env(0.005, 0.08, b, 0.25)
# climb-out whoosh 17-32 s (filtered noise swelling and falling)
rng = np.random.default_rng(3); noise = rng.standard_normal(n)
ker = np.ones(80) / 80; wn = np.convolve(noise, ker, mode="same")
sw = np.clip(np.sin(np.pi * (t - 17) / 15), 0, None) * ((t > 17) & (t < 32)); out += 0.5 * wn * sw
# bells: crane reveal (13 s) and the Shard (32 s), cranes (40 s)
for s, ms in ((13, [74, 77, 81]), (32, [74, 78, 81, 86]), (40, [78, 81, 85])):
    for j, m in enumerate(ms):
        f = note(m); e = env(0.003, 2.2, s + 0.09 * j, 5)
        out += 0.09 * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-(t - s) * 1.5).clip(0, 1)) * e
fade = np.minimum(1, t / 1.5) * np.minimum(1, (T - t) / 3); out *= fade
out /= np.abs(out).max() * 1.12
st = np.stack([out, np.roll(out, 300)], 1)
with wave.open("music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())
print("ok")
