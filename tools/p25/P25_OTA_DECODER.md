# Over-the-Air P25 GPS Decoder — the mission, and everything we worked out

**Written by Claude, for Claude. Canonical capture of the P25 OTA-decode research (2026-11-22).**
This is the NEW primary mission (Jim declared the shift 2026-11-22). Read this before doing any P25 decode work so the hard-won reasoning below is not re-derived from scratch. Public repo → employer-clean (no agency names; Jim's name/handle are fine).

---

## The mission in one paragraph

Today the whole live-GPS stack (the P25 GPS Tracker, The Lookout, the trifecta) depends on the **BK radio cooperating** — a BK base relay decodes the received P25 GPS itself and squirts clean NMEA out its USB **RNDIS** link, and we just read it (`$GNGGA` + `$PP25` on TCP 65535; see the family `CLAUDE.md` and memory). That tether is the limit. **The new mission is to decode the P25 GPS data OURSELVES, over the air, from the radio's discriminator audio — no RNDIS squirt, no BK cooperation.** If we can slice symbols off discriminator audio and pull the location out, then **any P25 fleet from any manufacturer becomes trackable** from a cheap receiver + a sound card. Jim's words: *"This would break us free from the BK world into the entire world of P25."* And: *"All the scanner people want to listen to traffic. I am the opposite, I just want the gps data."*

**Honesty note (blind test):** Jim has **already walked this path himself** and deliberately withheld his findings so a fresh Claude would reason independently. Where this doc's conclusions match his (the discriminator tap point in particular), that is **confirmation, not discovery** — treat it as a second witness, not a claim of credit.

---

## Why it matters / what it unlocks

- **Breaks the BK dependency.** No more needing a BK base on the RNDIS branch to hand us NMEA. A receiver tuned to the fleet's channel + discriminator tap + sound card is the whole front end.
- **Opens the entire P25 world.** P25 is a public-safety interoperability standard; Tier 1 location is specified (below). Decode it once and the tool is manufacturer-agnostic — Motorola, Harris/L3, Tait, BK, etc.
- **Data-only, so the patent wall does not apply.** We want **location data, not voice**. The IMBE/AMBE vocoder (mbelib / DVSI) is patent-encumbered, but it only guards **voice**. Decoding **data PDUs** sidesteps it entirely. This is a real enabler, not a convenience.
- **Still PTT-shaped.** A fix rides when a radio keys up — same "no big brother" posture as the current tracker; we're just reading it off the air instead of off the BK's USB.

---

## The "apple" insight — the known-plaintext rig (Jim's framing, 2026-11-22)

*"Imagine the P25 packet is a series of images, and after a packet comes in the BK says 'hey look, I found an apple in the packet.' Now if you look for an apple it's a lot easier to find."*

The BK base **already tells us the answer.** On the same transmission, the RNDIS branch hands us the **finished NMEA** (lat/lon/time) — ground truth. So we run a **known-plaintext** bring-up:

1. A functional BK base feeds **known, complete NMEA** via the RNDIS branch we already know how to connect to and engage (subscribe `80 04 18 e4 81` to TCP **65535** over RNDIS at `10.250.46.6` — the Lookout/tracker path).
2. On the **same PC**, the receiver's **discriminator signal feeds a Sound Blaster 3** sound-card input.
3. As our decoder climbs the stack, we **diff what falls out of it against the known NMEA in real time.** We know exactly what lat/lon to look for, so finding where those bytes live in the raw frame — and proving each decode stage — is vastly easier than decoding blind.

This rig is the single most valuable asset we have, and it's the thing almost nobody else building P25 decoders has: a live answer key.

---

## The tap point — PROVEN (Jim confirmed; independently re-derived from the schematic)

**Donor radio:** BK **DPH-CMD** portable (Jim has these in abundance, free from the trash — "very good radios"). We only ever **receive**; nothing is transmitted or altered.

**Where to tap:** the recovered FM baseband — **"DISC AUD"** — on the radio's main board-to-board connector:

- Connector **J2 "TO SYSTEM BOARD"**, pin **CZ8 = DISC AUD** (schematic page **6-49** in the DPH-CMD service manual; the J2 pin list ran CZ1 GND · CZ2 SQ_NOISE · CZ3 PST · CZ4 SWA+ · CZ5 — · CZ6 RX+5V · CZ7 -DPTT · **CZ8 DISC AUD** · CZ9 CAR_PRES · CZ10 WIDE_IF).
- **A pin on a major connector is preferred** (Jim's rule): mechanically clean, repeatable, no fine soldering to an IC leg.

**Why discriminator audio is the right tap:** it is the **FM demodulator's output — demodulation is already done.** We do NOT need an SDR or an RF front end to recover C4FM; the radio's own receiver has already turned RF into the 4-level baseband. We go **straight to symbol slicing.** This is the whole reason tapping a hardware radio is cleaner than SDR for our narrow goal.

**RX chain context (so a future Claude can re-read the schematic):** dual-conversion receiver, IFs ~**16.9 MHz** then **455 kHz**; FM IF IC **U7 = BA4116FV** (BK p/n 3134-30670-620); **CF3** 455 kHz ceramic discriminator; **Y1** 17.355 MHz 2nd LO. In the stock radio the recovered **Disc Audio → CODEC → DSP**. **We tap Disc Audio before the CODEC** and do the DSP ourselves in software.

> The service manual is Jim's PDF (uploaded attachment: `bk-dph-digital-service-manual_1.pdf`, 149 pp; TOC ~PDF p.1–10, Theory of Operation ~PDF p.46–56 incl. Fig 4-1 RX block diagram + Fig 4-6 DSP block diagram, RX/TX parts list + schematic ~PDF p.106–121, schematic p.6-49 at ~PDF p.114). It is **not in the repo** (service manual, kept out). A future session needs Jim to re-attach it to re-read the schematic.

---

## The standard — RESEARCHED (strong, to be confirmed on the bench)

Jim's steer: *"The P25 packet structure is highly regulated for public safety use and interoperability. We are using Tier 1 GPS information — research deep to see if that chunk is regulated to be in a common format across manufacturers."* It is.

- **TIA-102.BAJB-A — "Project 25 Tier 1 Location Services."** Position is formatted as **NMEA 0183** and carried **SU-to-SU, Direct Data / Repeated Data**, over a **dedicated CAI SAP** (service access point). Tier 2 = fixed-network / advanced location services.
- Because it's an **interoperability standard**, the location "chunk" is a **common format across manufacturers** — exactly the property that lets one decoder serve the whole P25 world. This is the enabler for the "break free from BK" goal.
- **Distinct from Motorola LRRP** (Location Request/Response Protocol): LRRP is **proprietary/vendor-specific** (IPv4/UDP, token-based). Do **not** conflate the two — Tier 1 (NMEA, standardized) is our target; LRRP is a different, closed thing.

**Caveat kept honest:** "Tier 1 = NMEA inside a dedicated SAP" is the documented standard, but **how BK actually encapsulates it on the air is the one real unknown** (next section). Don't state the encapsulation as settled until the rig shows it.

---

## P25 Phase 1 physical-layer facts (for the symbol slicer)

- **C4FM**, 4-level FM: **4800 symbols/s × 2 bits = 9600 bps**.
- **Frame sync** = a fixed **24-dibit** pattern; after sync comes the **NID = NAC (network access code) + DUID** (data unit ID). DUID **7 = TSBK** (trunking); data PDUs carry the packet payload.
- **PDU**: 12-byte header + 12-byte (unconfirmed) or 16-byte (confirmed) data blocks.
- **FEC** on the data path: **trellis** coding (rate 1/2 unconfirmed, 3/4 confirmed), plus **Golay / Hamming / Reed-Solomon / CRC** depending on the field. The decoder has to undo these to recover clean bytes.

Because we start from **discriminator audio**, the chain is: **DISC AUD → sound card → 4-level symbol slice → frame sync → NID → PDU reassembly + FEC → payload bytes → NMEA extraction.** No RF, no vocoder.

---

## Tooling / parts donors — what's already written and open

- **OP25** (osmocom) — the base P25 decoder. Crucially, **OP25 can take discriminator / sound-card audio input** (not only SDR). This is the project to wire the Sound Blaster into. Confirm its discriminator-input mode when we go to the bench.
- **DSD / DSD+ / dsd-fme** — decode from discriminator audio; voice-centric but useful reference for the symbol/sync front end.
- **SDRTrunk** — SDR-centric, trunk-following; reference, not a fit.
- **`russinnes/P25-sndcp-packet-decoder`** (an **OP25 fork**) — decodes a P25 data channel all the way: **symbols → frames → PDU reassembly → SNDCP → IPv4 → UDP → readable payload.** This proves the **hard middle of the stack is already written and open.** Strong parts donor.
  - **Honest edges (not a drop-in):** (1) **SDR input**, not sound card — its whole hard problem is *retuning an SDR to chase bursty trunked data channels*; (2) **trunk-focused** with channel-chasing; (3) targets **text (Motorola TMS/ARS)**, **not** location/NMEA.
  - **Why our job is EASIER than theirs:** the **BK radio is already locked on the channel**, pumping DISC AUD **continuously** — so we **never chase channels** (their single hardest problem is a non-issue for us). And we have **ground-truth NMEA** to validate against; they decode blind. We feed one sound card and add an "extract NMEA from the payload" step (and the project already parses NMEA).

---

## The one real unknown — and the rig settles it

**Does BK's Tier 1 location ride as full SNDCP / IPv4 / UDP packet data, or as the simpler "dedicated SAP, Direct/Repeated Data" unit** that TIA-102.BAJB describes (NMEA carried more directly, no IP layer)?

- If **SNDCP/IP/UDP** → the russinnes fork's reassembly core is near-directly reusable; we just add NMEA extraction from the datagram payload.
- If **simpler dedicated SAP** → we use OP25/the fork for frame + PDU decode, skip the SNDCP/IP layer, and pull NMEA straight out of the SAP data unit ourselves.
- The standard's wording ("dedicated SAP, direct data") **hints at the simpler path**, but don't guess — the rig shows it in one session.

**First experiment (the whole thing turns on this):**
> **DISC AUD → an OP25-based decoder → watch what PDUs / datagrams actually fall out → diff the bytes against the known RNDIS NMEA.** The transport structure reveals itself, and that decides the architecture of everything we build.

---

## Status ledger (keep this honest)

| Thing | State |
|---|---|
| BK RNDIS NMEA path (the answer key) | **PROVEN** — live, in use (tracker + Lookout) |
| Discriminator tap = DPH-CMD J2 pin **CZ8 DISC AUD** | **PROVEN** (Jim confirmed; re-derived from schematic p.6-49) |
| Discriminator audio = FM demod done → straight to symbols | **ESTABLISHED** (radio theory of operation) |
| Standard = TIA-102.BAJB Tier 1, NMEA in a dedicated SAP, interoperable | **RESEARCHED** (strong; distinct from Motorola LRRP) |
| No vocoder needed (data not voice → no DVSI patent) | **ESTABLISHED** |
| Decode stack + parts donors (OP25, russinnes fork) | **MAPPED** |
| Transport encapsulation (SNDCP/IP vs simple SAP) | **UNKNOWN** — the rig resolves it |
| End-to-end OTA decode of a real GPS fix | **NOT YET** — next bench session |

## Next step

Desk research has done its job: standard, stack, tap, tooling, and the one empirical fork in the road are all mapped. **The next real progress is on the bench, not the browser** — the known-plaintext rig and the first experiment above. Options when work resumes: (a) fire up the rig and look; or (b) one more desk thread first — the exact **TIA-102.BAJB Tier 1 SAP data-unit layout**, or **OP25's discriminator-audio input mode** (so the Sound Blaster is ready to wire straight in).

**PULL THE PARTS (not done yet — we never repo'd them, 2026-11-22).** The donor code is open but not in our hands. A **desk task doable before the bench**: clone **OP25** (osmocom) and **`russinnes/P25-sndcp-packet-decoder`** into the sandbox and READ the real implementation — the C4FM symbol slicer, the 24-dibit sync, NID/DUID typing, the trellis/Golay/Hamming/RS FEC, the PDU reassembly, and (in the fork) the SNDCP→IP/UDP path + its NMEA parser. Goal: map exactly which files/functions are reusable as-is vs. need an input adapter (discriminator/sound-card in place of SDR) and the NMEA-extract add. That turns "the chain is buildable" into "here are the specific parts and the specific glue."

## Sources
- russinnes/P25-sndcp-packet-decoder (GitHub) — SNDCP→IPv4/UDP decode fork of OP25
- OP25 decoder + P25-in-UDP encapsulation wikis (osmocom)
- "A Look at Project 25 (P25) Digital Radio" — CAI/framing (GNU Radio wiki, PDF)
- dsd-fme / OP25 / SDRTrunk comparison (pistack.xyz guide)
- TIA-102.BAJB-A Project 25 Tier 1 Location Services (the standard; NMEA 0183 position, dedicated CAI SAP)
- BK DPH-CMD service manual (Jim's PDF) — RX theory of operation, Fig 4-1/4-6, schematic p.6-49 (J2 pinout)
