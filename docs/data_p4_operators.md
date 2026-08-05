# Data Dictionary — P-4 Operator / Lease Database

## Dataset Description

This dataset is a full extract of the Railroad Commission of Texas (RRC)
Producer's Transportation Authority and Certificate of Compliance ("P-4")
database — the "Complete P-4" tape. Like the production tape
(`docs/data_rrc_production.md`), this is **not a flat table**: it is a
**hierarchical database dump** with up to 30 different fixed-length
"segment" record types (root lease info, filing history, gatherer/
purchaser/nominator, remarks, severance, gas/oil proration schedules, unit
reporting, fees, etc.), all interleaved in a single file and distinguished
only by a 2-byte record-type key at the start of each record — the exact
same physical convention as the production tape.

- **One "row" (physical record) is one segment of one of 30 possible
  types**, not one lease. See [Record Type
  Key](#record-type-key-segments) and [Segment
  Hierarchy](#segment-hierarchy) below.
- **This file gives operator NUMBER, not operator NAME.** The field
  `P4-OPERATOR-NUMBER` (on the Root segment) is documented as *"The
  RRC-assigned P-5 number of the company listed as the current operator of
  the lease."* It is a numeric ID (an RRC "P-5" organization registration
  number), not a company name string. **No field anywhere in this file
  contains an operator/company name** — the only name field found in the
  whole format spec is `P4-LEASE-NAME` (the lease's own name, e.g. "SMITH
  A", not the operating company's name). See [Known
  Issues](#known-issues--open-questions) — bringing an actual company name
  into the analytics tables will require a separate RRC dataset (the P-5
  Organization Report), which is not among the raw files currently in this
  project.

## Source

- **Publisher**: Railroad Commission of Texas (RRC)
- **Publication**: *Oil and Gas Lease/P-4 Information Magnetic Tape User's
  Guide*, Publication Number **P4A002** (First Edition June 1991; last
  revision July 2012)
- **Format spec file**: `data/raw/operators/p4-user-manual_p4a002_feb2015.pdf`
  (kept alongside the raw data; not modified)
- **Data file**: `data/raw/operators/p4f606.ebc`
- **RRC internal dataset name**: `T.P4F606` ("Complete P-4" tape — 30
  record types; a narrower `T.P4F608` "Form P-4 Only" variant with just 6
  record types also exists per the spec but is not the file we have)

## File Format & Encoding

| Property | Value |
|---|---|
| File name | `p4f606.ebc` |
| File size | 2,787,886,120 bytes |
| Character encoding | **EBCDIC** (assumed IBM code page **037** — same assumption as the production tape; not explicitly stated in this source PDF either, and **not yet validated** against decoded data the way the production tape was — see [Known Issues](#known-issues--open-questions)) |
| Record format | **Fixed-length binary records, 92 bytes each** — no delimiters (blocksize 32,752 = 92 × 356 records/block, matching the spec's stated blocking factor) |
| Total records | **30,303,110** (`2,787,886,120 / 92`, divides evenly) |
| Numeric field encoding | Mix of plain EBCDIC text digits (`PIC 9(n)`) and **COMP-3 packed decimal** for a handful of fields (e.g. wellbore counts, lease depth) — same two encodings as the production tape, see `docs/data_rrc_production.md` for how COMP-3 unpacking works |
| Is it CSV / fixed-width text? | No — same fixed-length binary mainframe extract style as `PDF100.ebc`, produced by the same RRC system template (`IBM 2003-116`, IBM standard tape labels). |

## Segment Hierarchy

Same physical convention as the production tape: each lease's P-4 filing
history is a tree of segments, identified by the first 2 bytes of the
record. The root of the tree (`P4ROOT`, key `01`) fans out into filing
history, name history, restrictions, remarks, severance, gas/oil
scheduling, unit reporting, and fee records:

```
P4ROOT (01)                          one per lease
 ├─ P4INFO (02)                      one per P-4 filing (audit/history trail)
 │   └─ P4GPN (03)                   gatherer/purchaser/nominator for that filing
 ├─ P4REMARK (04)                    P-4 remarks
 ├─ P4LSEPTR (05)                    lease pointer
 ├─ P4RESTR (06)                     lease restrictions
 ├─ P4LSENM (07)                     lease name (only present for original name + name changes)
 │   └─ P4LSERMK (08)                lease remarks
 ├─ P4SEVR (09)                      severance information
 │   └─ P4SEVRMK (10)                severance remarks
 ├─ P4GSCHED (11)                    gas schedule
 │   ├─ P4GSCHCY (12)                gas schedule cycle
 │   └─ P4GSECT (13)                 gas problem/letter section
 │       └─ P4GLTRDT (14)            gas problem/letter date & type
 ├─ P4OSCHED (15)                    oil schedule
 │   ├─ P4OSCHCY (16)                oil schedule cycle
 │   └─ P4OSECT (17)                 oil problem/letter section
 │       └─ P4OLTRDT (18)            oil problem/letter date & type
 ├─ P4YATES (19)                     Yates Field unit info
 ├─ P4OUNIT (20)                     schedule unit information
 │   ├─ P4OUNTCY (21)                unit reporting cycle
 │   ├─ P4OUNTPV (22)                previous unit allowable
 │   └─ P4OUNTRK (23)                unit remarks
 ├─ P4LSEXCP (24)                    lease exceptions
 ├─ P4CMPTR (25)                     commingle permit pointer
 ├─ P4EXDATE (26)                    Form P-17 exception date
 ├─ P4FEEREC (27)                    P4 fee received
 │   └─ P4CHECK (28)                 P4 check register
 ├─ P4SVRFEE (29)                    P4 severance fee
 └─ P4FEEPAY (30)                    P4 severance fee payment
```

## Record Type Key (segments)

Every record's first 2 bytes identify which of the following 30 segment
types it is. Only **P4ROOT** (bold) is documented field-by-field below —
it's the segment that carries the lease key + operator number, which is
all that's currently needed to join operator numbers onto the production
analytics tables. **P4INFO** and **P4LSENM** are summarized (not fully
field-mapped) since they may be useful later — P4INFO for filing-history
audit detail, P4LSENM for the lease's human-readable name. The remaining
27 segments are cataloged here for completeness only.

| Key | Segment Name | Record Length | Description |
|---|---|---|---|
| **01** | **P4ROOT** | **60 bytes** | **Root Segment — lease identity + current operator number** |
| 02 | P4INFO | 80 bytes | General P-4 filing information (one per filing; audit/history trail) |
| 03 | P4GPN | 45 bytes | Gatherer/Purchaser/Nominator info for a filing |
| 04 | P4REMARK | 90 bytes | P-4 remarks |
| 05 | P4LSEPTR | 28 bytes | Lease pointer |
| 06 | P4RESTR | 14 bytes | Lease restrictions |
| 07 | P4LSENM | 58 bytes | Lease name (original + name-change history) |
| 08 | P4LSERMK | 90 bytes | Lease remarks |
| 09 | P4SEVR | 50 bytes | Severance information |
| 10 | P4SEVRMK | 50 bytes | Severance remarks |
| 11 | P4GSCHED | 23 bytes | Gas schedule information |
| 12 | P4GSCHCY | 30 bytes | Gas schedule cycle |
| 13 | P4GSECT | 20 bytes | Gas problem/letter section info |
| 14 | P4GLTRDT | 40 bytes | Gas problem/letter date & type |
| 15 | P4OSCHED | 32 bytes | Oil schedule information |
| 16 | P4OSCHCY | 60 bytes | Oil schedule cycle |
| 17 | P4OSECT | 20 bytes | Oil problem/letter section info |
| 18 | P4OLTRDT | 40 bytes | Oil problem/letter date & type |
| 19 | P4YATES | 50 bytes | Yates Field unit information |
| 20 | P4OUNIT | 72 bytes | Schedule unit information |
| 21 | P4OUNTCY | 79 bytes | Schedule unit reporting cycle |
| 22 | P4OUNTPV | 79 bytes | Previous unit allowable |
| 23 | P4OUNTRK | 90 bytes | Unit remarks |
| 24 | P4LSEXCP | 20 bytes | Lease exceptions |
| 25 | P4CMPTR | 31 bytes | Commingle permit pointer |
| 26 | P4EXDATE | 45 bytes | Form P-17 exception date record |
| 27 | P4FEEREC | 45 bytes | P4 fee received |
| 28 | P4CHECK | 35 bytes | P4 check register |
| 29 | P4SVRFEE | 50 bytes | P4 severance fee |
| 30 | P4FEEPAY | 30 bytes | P4 severance fee payment |

All records, regardless of segment type, are stored in the same physical
**92-byte** slot: `RRC-TAPE-RECORD-ID` (2 bytes) + segment-specific fields,
right-padded with an `RRC-TAPE-FILLER` field out to 92 bytes total — same
convention as the production tape.

## Detailed Field Layout

Byte positions below are **1-indexed**, matching the source COBOL copybook.

### 01 — P4ROOT (Root Segment) — 60 bytes of data + 30 bytes filler = 92 bytes total

Key segment: one per oil lease/gas well. No parent key (top of the tree).

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` (text) | Record type key. `01` = Root Segment |
| `P4-OIL-GAS-CODE` | 3 | `X(01)` (text) | `O` = Oil Lease, `G` = Gas Well |
| `P4-DISTRICT` | 4–5 | `9(2)` (text digits) | RRC district, stored value `01`–`14`. **Same encoding/table as the production tape's `district_code`** — see below |
| `P4-LEASE-RRCID` | 6–11 | `9(06)` (text digits) | Lease/well number, RRC-assigned. Corresponds to `lease_nbr` in the production analytics tables |
| `P4-FIELD-NUMBER` | 12–19 | `9(08)` (text digits) | RRC-assigned field ID the lease currently belongs to |
| `P4-ON-OFF-SCHEDULE-INDICATOR` | 20 | `X(01)` | `N` = on proration schedule, `Y` = off schedule |
| `P4-OPERATOR-NUMBER` | 21–26 | `9(06)` (text digits) | **The RRC "P-5" number of the company currently operating the lease.** Not a name — see [Dataset Description](#dataset-description) |
| `P4-REMOVE-FROM-SCHEDULE-REASON` | 27–28 | `X(02)` | Code for why the lease was taken off schedule (plugged/abandoned, consolidated, subdivided, etc.), spaces if not removed |
| `P4-REMOVE-FROM-SCHED-YEAR/MONTH/DAY` | 29–36 | `9(4)/9(2)/9(2)` | Date removed from schedule, if applicable |
| `P4-STOCK-ON-HAND-INDICATOR` | 37 | `X(01)` | Flags remaining liquid stock blocking removal from schedule (`Y`/`S`/`N`) |
| `P4-SEQUENCE-DATE-KEY-FOR-SCHED` | 38–45 | `9(08)` (text digits) | Internal scheduling sequence key |
| `P4-PENDING-LEASE-REMOVAL-FLAG` | 46 | `X(01)` | `Y` = pending removal |
| `P4-LAND-BORE-CNT` | 47–49 | `S9(05) COMP-3` (3 bytes) | Count of land wellbores on the lease |
| `P4-INLAND-BORE-CNT` | 50–51 | `S9(03) COMP-3` (2 bytes) | Count of inland-water wellbores |
| `P4-BAY-BORE-CNT` | 52–53 | `S9(03) COMP-3` (2 bytes) | Count of bay wellbores |
| `P4-OFFSHORE-BORE-CNT` | 54–55 | `S9(03) COMP-3` (2 bytes) | Count of offshore wellbores |
| `P4-LEASE-TOTAL-DEPTH` | 56–60 | `S9(09) COMP-3` (5 bytes) | Lease total depth |
| `FILLER` | 61–62 | `X(02)` | Unused filler |
| `RRC-TAPE-FILLER` | 63–92 | `X(30)` | Padding to fill the fixed 92-byte physical record |

`P4-ROOT-KEY` = `P4-OIL-GAS-CODE` + `P4-DISTRICT` + `P4-LEASE-RRCID`
(positions 3–11) is the natural key — **structurally identical** to
`PDROOT-KEY` on the production tape (`oil_code` + `district_code` +
`lease_nbr`), which is what makes joining the two datasets
straightforward once decoded.

#### District Code Table (P4-DISTRICT)

Identical encoding to the production tape's `PD-OIL-DISTRICT` — confirms
this is an RRC-wide convention, not specific to one dataset:

| Stored value | RRC District ID | | Stored value | RRC District ID |
|---|---|---|---|---|
| 01 | 1 | | 08 | 7B |
| 02 | 2 | | 09 | 7C |
| 03 | 3 | | 10 | 8 |
| 04 | 4 | | 11 | 8A |
| 05 | 5 | | 12 | 8B (reserved for future use) |
| 06 | 6 | | 13 | 9 |
| 07 | 6E | | 14 | 10 |

### 02 — P4INFO (General P-4 Filing Information) — summary only

One record per P-4 form filed for a lease (a history/audit trail, not a
current-state snapshot like Root). Notable fields per the spec: 
`P4-EFFECTIVE-DATE` / `P4-APPROVAL-DATE` (when the filing took effect /
was approved), a block of Y/N "purpose of filing" flags (new well, change
of gatherer/purchaser/nominator/operator/field/lease name, consolidation,
subdivision, reclassification), and `P4-INFO-OPERATOR-NUMBER` — the
operator number *as of that specific filing*, which may differ from
Root's "current" operator number if the lease has changed hands since.
Not field-mapped in full here since Root's operator number is sufficient
for the immediate join goal.

### 07 — P4LSENM (Lease Name) — summary only

Gives `P4-LEASE-NAME` (`X(32)` text) — the lease's own descriptive name
(e.g. a name like "SMITH A"), **not** an operator/company name. Per the
spec, a record here "will only exist for the original lease name and when
the name has changed" — i.e. this is a name-change history log, not one
row per lease per cycle.

## Known Issues / Open Questions

- **This file gives operator NUMBER, not operator NAME.** This is the
  most important finding from this exploration pass. `P4-OPERATOR-NUMBER`
  is an RRC "P-5" organization registration number. To show an actual
  company name in Looker Studio, a separate RRC dataset (the P-5
  Organization/Operator Report, which maps P-5 numbers to company names
  and addresses) would be needed — it is not currently among this
  project's raw files. Until then, the best this dataset can add to the
  analytics tables is an `operator_number` dimension, not a company name.
- **EBCDIC code page spot-checked, not fully validated.** Assumed `cp037`
  by analogy with the production tape. A 500,000-record sample from the
  start of the file decodes cleanly with `cp037` — all 7,635 sampled Root
  records had a valid `district_code` (`01`) and `oil_gas_code` (`G`), and
  `operator_number`/`lease_nbr` decoded as clean numeric strings, no
  garbled text. This is a good sign but **not yet a full-file check** the
  way `PDF100.ebc` got (where all 165,436 Root records were checked, not
  a sample) — worth doing before this data is trusted at full scale.
- **This file covers both oil leases and gas wells** (`P4-OIL-GAS-CODE` =
  `O` or `G`) — unlike the production tape, which is oil-only. The sampled
  records above happened to be entirely gas wells (`G`), simply a
  property of this sample/file ordering, not a sign anything is wrong.
  **When joining this file to the oil production analytics tables, filter
  to `P4-OIL-GAS-CODE = 'O'` first** — otherwise gas-well operator numbers
  would get matched against oil lease numbers that only coincidentally
  share the same `(district_code, lease_nbr)` value.
- **This file mixes 30 different logical record types** in one physical
  stream, positionally hierarchical with no stored foreign keys — same
  caveat as the production tape. Reconstructing "which operator number
  belongs to which lease" only requires the Root segment alone, so this
  is lower-risk here than the production tape's multi-segment joins were.
- **"Number of records" (30,303,110) counts physical 92-byte slots across
  all 30 segment types combined** — not the number of leases. The actual
  lease count (Root segment records only) has not yet been determined;
  that requires a full-file scan, not done in this pass (steps 1–2 only:
  inspect + document the format, per `CLAUDE.md` Phase 1 Tasks).
- **This dataset is much larger than the production tape**: 2.7 GB / 30.3M
  records vs. 1.1 GB / 10.8M records. A full-file scan (once we get to
  building the extraction code) will take longer than `PDF100.ebc`'s
  ~10-minute scan, proportionally.
- Field layouts for the 27 non-core segment types (02 partially, 03,
  04–06, 08–30) are cataloged by key/name/length only in this document;
  full field-by-field detail can be added later if a specific downstream
  need for them arises (e.g. severance data, gas/oil proration schedules).
