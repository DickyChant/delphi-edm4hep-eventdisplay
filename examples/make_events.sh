#!/usr/bin/env bash
# The two events from the Sept 2026 talk, as interactive pages.
# Track indices come from the original dump_event.py --run --event (data)
# and mc_dump_event.py --entry (simulation).
#
# The edm4hep files live on EOS and are not in this repository:
#   /eos/experiment/eealliance/Users/zhangj/edm4hepSimBTagging/
# Point $D at a local copy, or at /eos directly on lxplus.
set -euo pipefail
D=${D:-/eos/experiment/eealliance/Users/zhangj/edm4hepSimBTagging}
OUT=${OUT:-docs/events}

delphi-display "$D/data_94c/Y13709.126.edm4hep.root" --entry 3990 --out "$OUT/data_48758_2666.html" \
  --view all \
  --require-vd \
  --title 'Z → bb̄ with a displaced φ → K⁺K⁻' \
  --note 'SVs at 9.66 mm (φ side) and 2.87 mm' \
  --group 'φ → K⁺K⁻ (both kaons RICH-identified):#d62728:20,22' \
  --group 'third identified K⁻, same SV:#ff7f0e:21' \
  --group 'identified K⁺ at the other SV:#1f77b4:6' \
  --group 'p̄ candidate (RICH), other SV:#9467bd:25' \
  --rich 20,22,21,6,25

delphi-display "$D/Zbb/bb_1000182.edm4hep.root" --entry 422 --out "$OUT/mc_bb1000182_e423.html" \
  --view all \
  --title 'Simulated Z → bb̄ — B⁺ (φ and D̄⁰) + B̄⁰ (D⁺ → K⁻π⁺π⁺)' \
  --note 'simulation: Pythia 8 + DELSIM' \
  --group 'φ → K⁺K⁻ from D_s⁺ (RICH-identified):#d62728:4,0' \
  --group 'K⁺ from D̄⁰ (RICH tight):#ff7f0e:7' \
  --group 'D⁺ → K⁻π⁺π⁺ (m = 1.878 GeV):#1f77b4:9,10,5' \
  --rich 4,0,7,9

delphi-pages
