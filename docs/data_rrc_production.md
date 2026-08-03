# Data Dictionary — RRC Statewide Production Data (Oil)

## Dataset Description

This dataset is a full extract of the Railroad Commission of Texas (RRC)
Production ("PD") database, oil version. It is not a flat table — it is a
**hierarchical database dump**: one lease's history is represented as a
sequence of fixed-length "segment" records of different types (root lease
info, monthly reporting cycles, production volumes, dispositions, remarks,
etc.), all interleaved in a single file and distinguished only by a 2-byte
record-type key at the start of each record.

- **One "row" (physical record) does not represent one production month.**
  It represents one segment of one of 24 possible types. A single
  lease-month of production is reconstructed from *several* related
  records (see [Record Type Key](#record-type-key-segments) and
  [Segment Hierarchy](#segment-hierarchy) below).
- The dataset covers **oil leases only**. RRC publishes a separate,
  differently-structured gas tape (`T.PDF101`) for gas/casinghead-gas
  leases, which is documented in the same source PDF but is out of scope
  for this file.

## Source

- **Publisher**: Railroad Commission of Texas (RRC)
- **Publication**: *Oil and Gas Production Information User's Guide*,
  Publication Number **PDA001** (First Edition April 1991; last revision
  January 2005)
- **Format spec file**: `data/raw/production/pda001.pdf` (kept alongside the
  raw data; not modified)
- **Data file**: `data/raw/production/PDF100.ebc`
- **RRC internal dataset name**: `T.PDF100` (oil tape)

## File Format & Encoding

| Property | Value |
|---|---|
| File name | `PDF100.ebc` |
| File size | 1,100,339,178 bytes |
| Character encoding | **EBCDIC** (assumed IBM code page **037**, US/Canada — the de facto standard for US mainframe tape extracts of this era; **not explicitly stated** in the source PDF, see [Known Issues](#known-issues--open-questions)) |
| Record format | **Fixed-length binary records, 102 bytes each** — no line breaks, no delimiters |
| Blocksize (per source tape spec) | 32,742 bytes = 102 × 321 records/block (blocking is a tape artifact; the file on disk is just a flat sequence of 102-byte records) |
| Total records | **10,787,639** (`1,100,339,178 / 102`, divides evenly, confirming the fixed 102-byte record length) |
| Numeric field encoding | Most monetary/volume fields use **COMP-3 (packed decimal / BCD)**, not EBCDIC text digits — see [Data Types](#data-types) |
| Is it CSV / fixed-width text? | No. It is a fixed-length **binary mainframe extract** — closer to a COBOL copybook layout than a fixed-width text file. Each of the 24 record types has its own internal field layout occupying the same 102-byte physical slot (short segments are right-padded with filler bytes). |

## Segment Hierarchy

Each oil lease's data is a tree of segments, identified by the first 2 bytes
of the record (the `RRC-TAPE-RECORD-ID` key). Reading the file in order and
grouping consecutive records by parent/child key is required to reconstruct
one lease's production history:

```
PDROOT (01)                         one per lease
 ├─ PDORPTCY (02)                    one per reporting cycle (month, key=MMYY)
 │   ├─ PDOPROD (03)                 production volumes for that cycle
 │   ├─ PDORMVDS (04)                discrepancy-removal flags (non-recurring)
 │   ├─ PDODSP (05)                  disposition & stock adjustment
 │   ├─ PDOCSHDS (06)                casinghead gas disposition
 │   ├─ PDOPRPV (07)                 previous production report (posting metadata)
 │   ├─ PDOCMPMT (08)                commingle permit
 │   │   ├─ PDOCMPRD (09)            commingle production
 │   │   ├─ PDOCMODS (10)            commingle oil disposition
 │   │   ├─ PDOOEB (11)              commingle oldest ending balance
 │   │   └─ PDOCMPV (12)             commingle previous production report
 │   └─ PDOPRVAL (13)                previous allowable
 └─ PDREMARK (22)                    production remarks
     ├─ PDODSPRK (23)                oil disposition remarks
     └─ PDOCMGRK (24)                oil commingle disposition remarks
```

## Record Type Key (segments)

Every record's first 2 bytes identify which of the following 24 segment
types it is. Only the four in **bold** (the segments needed to reconstruct
lease identity + monthly oil volumes) are documented field-by-field below;
the rest are catalogued here for completeness and can be expanded in a later
phase if/when disposition, commingle, or remarks data is needed.

| Key | Segment Name | Record Length | Description |
|---|---|---|---|
| **01** | **PDROOT** | **50 bytes** | **Root Segment — lease identity & rolling balances** |
| **02** | **PDORPTCY** | **80 bytes** | **Reporting Cycle Segment — monthly allowables & status** |
| **03** | **PDOPROD** | **38 bytes** | **Production Segment — reported oil/casinghead-gas volumes** |
| 04 | PDORMVDS | 20 bytes | Prod Report Discrepancy Removal Segment |
| 05 | PDODSP | 7 bytes | Disposition & Stock Adjustment Segment |
| 06 | PDOCSHDS | 7 bytes | Casinghead Disposition Segment |
| **07** | **PDOPRPV** | **20 bytes** | **Previous Production Report Segment — posting metadata** |
| 08 | PDOCMPMT | 20 bytes | Commingle Permit Segment |
| 09 | PDOCMPRD | 38 bytes | Commingle Production Segment |
| 10 | PDOCMODS | 7 bytes | Commingle Oil Disposition Segment |
| 11 | PDOOEB | 10 bytes | Commingle Oldest Ending Balance Segment |
| 12 | PDOCMPV | 20 bytes | Commingle Previous Production Report Segment |
| 13 | PDOPRVAL | 35 bytes | Previous Allowable Segment |
| 22 | PDREMARK | 80 bytes | Production Remarks Segment |
| 23 | PDODSPRK | 60 bytes | Production Oil Disposition Remarks Segment |
| 24 | PDOCMGRK | 60 bytes | Production Oil Commingle Disposition Remarks Segment |

*(Keys 14–21 and 25–27 belong to the separate gas tape, `T.PDF101` /
`PDF101.ebc`, and do not appear in this file.)*

All records, regardless of segment type, are stored in the same physical
**102-byte** slot: `RRC-TAPE-RECORD-ID` (2 bytes) + segment-specific fields,
right-padded with a `RRC-TAPE-FILLER` field out to 102 bytes total.

## Detailed Field Layouts

Byte positions below are **1-indexed**, matching the source COBOL copybook
(`POS.` column in the PDF). All records also carry the 2-byte
`RRC-TAPE-RECORD-ID` at position 1–2 before the fields listed.

### 01 — PDROOT (Root Segment, Oil Version) — 50 bytes of data + 50 bytes filler = 102 bytes total

Key segment: one per oil lease. No parent key (this is the top of the tree).

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` (text) | Record type key. `01` = Root Segment (Oil Version) |
| `PD-OIL-CODE` | 3 | `X(1)` (text) | Record subtype. Always `O` = Oil Lease |
| `PD-OIL-DISTRICT` | 4–5 | `9(2)` (text digits) | Stored value is always numeric `01`–`14`. For districts 7–14 this stored number does **not** match the district's public-facing RRC ID (e.g. stored `08` = district "7B") — see [District Code Table](#rrc-district-code-table) |
| `PD-OIL-LEASE-NBR` | 6–11 | `9(06)` (text digits) | RRC-assigned lease number, unique within district |
| `PD-MOVABLE-BALANCE` | 12–16 | `S9(09) COMP-3` (packed decimal, 5 bytes) | Cumulative net barrels of oil in storage that may legally be moved off the lease |
| `PD-BEGINNING-OIL-STATUS` | 17–21 | `S9(09) COMP-3` (5 bytes) | Cumulative oil overproduction as of the most recently rolled-off reporting cycle |
| `PD-BEGINNING-CSGHD-STATUS` | 22–26 | `S9(09) COMP-3` (5 bytes) | Cumulative casinghead gas overproduction as of the most recently rolled-off reporting cycle |
| `PD-OIL-OLDEST-EOM-BALANCE` | 27–31 | `S9(09) COMP-3` (5 bytes) | Lease's oldest end-of-month balance still on the database |
| `FILLER` | 32–52 | `X(21)` | Unused filler, value zeros |
| `RRC-TAPE-FILLER` | 53–102 | `X(50)` | Padding to fill the fixed 102-byte physical record |

`PDROOT-KEY` = `PD-OIL-CODE` + `PD-OIL-DISTRICT` + `PD-OIL-LEASE-NBR`
(positions 3–11) is the natural key for a lease.

#### RRC District Code Table

**Validated against the full file**: a targeted scan of all 165,436 Root
records found exactly the 13 stored values below (every one of `01`–`14`
except `12`, which the source PDF itself marks "not used") — confirming
both the code list and that `12` genuinely never appears in this dataset.

| Stored value (`PD-OIL-DISTRICT`) | RRC District ID | | Stored value | RRC District ID |
|---|---|---|---|---|
| 01 | 1 | | 08 | 7B |
| 02 | 2 | | 09 | 7C |
| 03 | 3 | | 10 | 8 |
| 04 | 4 | | 11 | 8A |
| 05 | 5 | | 12 | 8B (not used) |
| 06 | 6 | | 13 | 9 |
| 07 | 6E (oil only) | | 14 | 10 |

### 02 — PDORPTCY (Reporting Cycle Segment, Oil Version) — 80 bytes of data + 20 bytes filler = 102 bytes total

Key segment: one per lease per reporting cycle (month). Child of Root (01).

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` | `02` = Reporting Cycle Segment |
| `PD-OIL-RPT-CYCLE-KEY` | 3–6 | `9(04)` | Reporting period. Source PDF states format **MMYY**, but decoded sample data clearly runs **YYMM** in chronological order (e.g. `2105, 2106, ..., 2112, 2201, ...`) — see [Known Issues](#known-issues--open-questions) |
| `PD-DAILY-OIL-PRORATED-ALLOW` | 7–11 | `S9(09) COMP-3` | Sum of daily oil allowables for all prorated wells on the lease (before production factor applied) |
| `PD-DAILY-OIL-EXEMPT-ALLOW` | 12–16 | `S9(09) COMP-3` | Sum of daily oil allowables for all exempt wells on the lease |
| `PD-DAILY-CSH-PRORATED-ALLOW` | 17–21 | `S9(09) COMP-3` | Sum of daily casinghead gas limits for all prorated wells |
| `PD-DAILY-CSH-EXEMPT-ALLOW` | 22–26 | `S9(09) COMP-3` | Sum of daily casinghead gas limits for all exempt wells |
| `PD-OIL-ALLOWABLE-CYCLE-BBLS` | 27–31 | `S9(09) COMP-3` | Sum of all oil well allowables for the lease for the cycle (barrels) |
| `PD-CSH-LIMIT-CYCLE-MCF` | 32–36 | `S9(09) COMP-3` | Sum of all casinghead gas limits for the lease for the cycle (MCF) |
| `PD-OIL-ALLOW-EFFECT-YEAR/MONTH/DAY` | 37–44 | `9(4)/9(2)/9(2)` | Effective date of the oil allowable |
| `PD-OIL-ALLOW-ISSUE-YEAR/MONTH/DAY` | 45–52 | `9(4)/9(2)/9(2)` | Issue date of the oil allowable |
| `PD-OIL-ENDING-BALANCE` | 53–57 | `S9(09) COMP-3` | Barrels of oil in storage at end of month, as reported by operator |
| `PD-PRESENT-OIL-STATUS` | 58–62 | `S9(09) COMP-3` | Cumulative oil overproduction through the last reported production |
| `PD-PRESENT-CSGHD-STATUS` | 63–67 | `S9(09) COMP-3` | Cumulative casinghead gas overproduction through the last reported production |
| `PD-ADJUSTED-OIL-STATUS` | 68–72 | `S9(09) COMP-3` | Adjustment (+/-) to cumulative oil overproduction |
| `PD-ADJUSTED-CSGHD-STATUS` | 73–77 | `S9(09) COMP-3` | Adjustment (+/-) to cumulative casinghead gas overproduction |
| `FILLER` | 78–82 | `X(5)` | Unused filler |
| `RRC-TAPE-FILLER` | 83–102 | `X(20)` | Padding to fill the fixed 102-byte physical record |

### 03 — PDOPROD (Production Segment, Oil Version) — 38 bytes of data + 62 bytes filler = 102 bytes total

Key segment: the actual reported oil/casinghead-gas volumes for one lease's
reporting cycle. **No key of its own** — inherits lease + cycle identity
from its parent Root (01) / Reporting Cycle (02) segments in the hierarchy.

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` | `03` = Production Segment |
| `PD-OIL-CORRECTED-REPORT-FLAG` | 3 | `X(01)` | `N` = original report, `Y` = corrected report |
| `FILLER` | 4–6 | `X(03)` | Unused filler, value zeros |
| `PD-OIL-PRODUCTION-AMOUNT` | 7–11 | `S9(09) COMP-3` | **Barrels of oil produced** from the lease, as reported by operator |
| `PD-OIL-CASINGHEAD-GAS-AMOUNT` | 12–16 | `S9(09) COMP-3` | **MCF of casinghead gas produced** from the lease |
| `PD-OIL-CASINGHEAD-GAS-LIFT` | 17–21 | `S9(09) COMP-3` | MCF of gas-lift gas injected into the lease (re-produced gas; subtract from disposition total for net production) |
| `PD-OIL-BATCH-NUMBER` | 22–24 | `X(03)` | Internal RRC batch ID for the production report |
| `PD-OIL-ITEM-NUMBER` | 25–28 | `9(04)` | Internal RRC posting order within the batch |
| `PD-OIL-POSTING-YEAR/MONTH/DAY` | 29–36 | `9(04)/9(02)/9(02)` | Date the production report was posted to the database |
| `PD-OIL-FILED-BY-EDI-FLAG` | 37 | `X(01)` | `Y` = filed electronically, `N` = not |
| `FILLER` | 38–40 | `X(03)` | Unused filler |
| `RRC-TAPE-FILLER` | 41–102 | `X(62)` | Padding to fill the fixed 102-byte physical record |

### 07 — PDOPRPV (Previous Production Report Segment, Oil Version) — 20 bytes of data + 82 bytes filler = 102 bytes total

Posting/audit metadata for the previous production report on file (as
opposed to `PDOPROD`'s current report). No key of its own — child of the
Reporting Cycle (02) segment.

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` | `07` = Previous Production Report Segment |
| `PD-OIL-PREV-POSTING-YEAR/MONTH/DAY` | 3–10 | `9(04)/9(02)/9(02)` | Date the *previous* production report was posted (format YYYY/MM/DD) |
| `PD-OIL-PREV-BATCH-NUMBER` | 11–13 | `X(03)` | Internal RRC batch ID |
| `PD-OIL-PREV-ITEM-NUMBER` | 14–17 | `9(04)` | Internal RRC posting order within the batch |
| `PD-OIL-PREV-CHANGED-FLAG` | 18 | `X(01)` | `C` = changed |
| `PD-OIL-PREV-FILED-BY-EDI-FLAG` | 19 | `X(01)` | `Y` = filed electronically |
| `FILLER` | 20 | `X(03)` | Unused filler |
| `RRC-TAPE-FILLER` | ~19–102 | `X(84)` | Padding to fill the fixed 102-byte physical record (note: source PDF's own position arithmetic is inconsistent here — filler position listed as 19, likely a typo for the position after byte 20; flagged in Known Issues) |

## Data Types

Two distinct "text" encodings and one binary encoding appear, all inside the
same EBCDIC-encoded file:

| Type | COBOL PICTURE | Storage | Notes |
|---|---|---|---|
| Alphanumeric / text digits | `PIC X(n)` or `PIC 9(n)` (DISPLAY, the implicit default) | 1 byte per character, EBCDIC-encoded | Includes record ID keys, lease numbers, dates, flags |
| Packed decimal | `PIC S9(9) COMP-3` | 5 bytes (2 digits per byte + 1 sign nibble) | Used for nearly all volume/balance/allowable fields. Must be **unpacked from BCD**, not decoded as EBCDIC text. Sign nibble: `C`/`F` = positive, `D` = negative |
| Dates | Split `9(4)`/`9(2)`/`9(2)` sub-fields (year/month/day) | Text digits, EBCDIC-encoded | No single date type; always three adjacent numeric sub-fields |

## Known Issues / Open Questions

- **EBCDIC code page not stated in source PDF** — assumed IBM code page
  037 (US/Canada). **Validated against the full file** in
  `notebooks/01_explore_rrc_production.ipynb`: decoding with `cp037`
  produces 100% valid `PD-OIL-CODE` (`O`) across all 165,436 Root records,
  and the 13 distinct `PD-OIL-DISTRICT` values decoded are exactly the 13
  expected codes from the [District Code Table](#rrc-district-code-table)
  (`01`–`14` minus `12`, which the PDF itself marks unused) — no unexpected
  or garbled values anywhere. Strong evidence `cp037` is correct; not
  formally proven against an external source, but no contradicting
  evidence found across the entire dataset.
- **`PD-OIL-RPT-CYCLE-KEY` format contradicts the source PDF.** The PDF
  states format MMYY, but decoded full-file values are unambiguously
  **YYMM** — 26 distinct values total, running `2105` through `2306`
  (May 2021 – June 2023). Treat as YYMM going forward; flagged here since
  it deviates from the official spec document.
- **This is a rolling/current-window extract, not a full historical
  archive.** Only 26 months of reporting cycles exist in the entire file
  (2021-05 through 2023-06). This matches the Root segment's own
  `PD-OIL-OLDEST-EOM-BALANCE` concept ("oldest end-of-month balance still
  on the database") — older cycles are evidently rolled off. Anyone
  wanting multi-decade Texas oil production history will need RRC's
  historical/archive extracts, not this file.
- **This file mixes 24 different logical record types** in one physical
  stream; there is no per-record length indicator other than the type key,
  so a wrong key lookup (e.g. mis-aligned read start) will silently
  misinterpret the following bytes. Byte-alignment must be maintained by
  reading strictly in fixed 102-byte strides from the start of the file.
  Records must be split first before determining what they contain.
  Any resync after an error requires re-reading from a known-good boundary
  since there are no record delimiters.
  (See `notebooks/01_explore_rrc_production.ipynb` for a working reader.)
- **Filler position arithmetic in the source PDF is occasionally
  inconsistent** (e.g. `PDOPRPV`'s `RRC-TAPE-FILLER` is annotated at
  position 19, one byte before the preceding field logically ends at 20).
  Believed to be a transcription artifact in the original document; the
  segment's total record length (20 bytes + generated filler = 102) is
  internally consistent regardless.
  Field positions in this document up to that point are taken directly
  from the PDF and have not yet been cross-validated against actual decoded
  data.
  Filler byte counts elsewhere are unaffected.
- **Available years, confirmed from a full-file scan.** `PD-OIL-RPT-CYCLE-KEY`
  spans `2105`–`2306` (26 distinct months); `PD-OIL-POSTING-DATE` years are
  2021 (360,090 records), 2022 (825,876), 2023 (439,989 — partial year).
- **"Number of records" (10,787,639) counts physical 102-byte slots across
  all 24 segment types combined** — it is not the number of leases, nor the
  number of lease-months, nor the number of oil-production values. A full
  scan (`notebooks/01_explore_rrc_production.ipynb`) breaks this down:
  165,436 Root (unique leases), 2,377,134 Reporting Cycle, 1,625,955
  Production, 326,839 Previous Production Report records — plus the
  remaining ~5.3M records across the 20 non-core segment types.
- Field layouts for the 20 non-core segment types (04–06, 08–13, 22–24) are
  cataloged by key/name/length only in this document; full field-by-field
  detail can be added in a later phase if needed (see the [Record Type
  Key](#record-type-key-segments) table).
