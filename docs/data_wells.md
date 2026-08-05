# Data Dictionary — Well Bore Database

## Dataset Description

This dataset is a full extract of the Railroad Commission of Texas (RRC)
Oil and Gas Well Bore System — the master registry of every individual
well bore in the state, keyed by API number. Like the other three RRC
tapes (`docs/data_rrc_production.md`, `docs/data_p4_operators.md`,
`docs/data_p5_organizations.md`), this is **not a flat table**: it is a
**hierarchical database dump** with 28 different fixed-length "segment"
record types, distinguished only by a 2-byte numeric record-type key at
the start of each record.

- **One "row" (physical record) is one segment of one of 28 possible
  types**, not one well. See [Record Type
  Key](#record-type-key-segments) and [Segment
  Hierarchy](#segment-hierarchy) below.
- **Structurally simpler than the production/P-4 hierarchies**: this tape
  is a flat fan-out, not a deeply nested tree. Every segment type (02–28)
  is a **direct child of the most recent Root (01) record** — there is no
  multi-level nesting like production's Root → Cycle → Production chain.
  "To proceed to the next well bore on the tape, look for the next
  key=01 record" (per the source PDF's own system description).
- **The Root segment's key is the well's API number, not a
  district+lease key.** This is a real structural difference from the
  other three tapes. `WBROOT` carries `WB-API-CNTY` + `WB-API-UNIQUE`
  (county + a well-unique number), not `district_code` + `lease_nbr`.
  The **Completion segment (`WBCOMPL`, key `02`)** is what carries the
  production-tape-compatible key (`WB-OIL-DIST` + `WB-OIL-LSE-NBR`) —
  see [Known Issues](#known-issues--open-questions) for why this matters
  for joining to the rest of this project's data.
- **A lease can have multiple wells.** `WBCOMPL` also carries
  `WB-OIL-WELL-NBR` — a dimension invisible everywhere else in this
  project, since production/allowable volumes are only ever reported at
  the lease level, never per well.

## Source

- **Publisher**: Railroad Commission of Texas (RRC)
- **Publication**: *Oil and Gas Well Bore System Magnetic Tape User's
  Guide*, Publication Number **WBA091** (First Edition May 1984; last
  revision May 2019)
- **Format spec file**: `data/raw/wells/wba091_well-bore-database.pdf`
  (kept alongside the raw data; not modified)
- **Data file**: `data/raw/wells/dbf900.ebc`
- **RRC internal dataset name**: `T.DBF900`

## File Format & Encoding

| Property | Value |
|---|---|
| File name | `dbf900.ebc` |
| File size | 7,366,305,947 bytes |
| Character encoding | **EBCDIC** (assumed IBM code page **037** — same assumption as the other three RRC tapes; not explicitly stated in this source PDF either, and **not yet independently validated** against decoded data — see [Known Issues](#known-issues--open-questions)) |
| Record format | **Fixed-length binary records, 247 bytes each** — no delimiters (blocksize 32,604 = 247 × 132 records/block, matching the spec's stated blocking factor) |
| Total records | **29,823,101** (`7,366,305,947 / 247`, divides evenly) |
| Numeric field encoding | Mix of plain EBCDIC text digits (`PIC 9(n)`) and **signed zoned-decimal DISPLAY fields with trailing overpunch sign** (`PIC S9(n)V9(m)` without `COMP-3`) for the New Location segment's latitude/longitude — a **third numeric encoding** not seen on the other three tapes (which only use plain digits and `COMP-3` packed decimal). See [Detailed Field Layout](#detailed-field-layout) below |
| Is it CSV / fixed-width text? | No — same fixed-length binary mainframe extract style as the other three tapes, same system template (`IBM 2003-116`, IBM standard tape labels, 1600 BPI). |
| Is it the biggest file in this project? | **Yes** — 7.3 GB / 29.8M records, roughly 2.6× the P-4 tape (2.7 GB) and 6.7× the production tape (1.1 GB). |

## Segment Hierarchy

Unlike the production and P-4 tapes' deep multi-level trees, this is a
**flat fan-out**: every segment type is a direct child of the nearest
preceding Root record. Only Root (01), Completion (02), and New Location
(13) are parsed for this project (bold below); the rest are cataloged for
completeness only.

```
WBROOT (01)                          one per well bore (API number, root of the tree)
 ├─ WBCOMPL (02)                     completion info (recurring — a well can have >1 completion)
 ├─ WBDATE (03)                      technical data forms file date (recurring)
 ├─ WBRMKS (04)                      remarks (recurring)
 ├─ WBTUBE (05)                      tubing (recurring)
 ├─ WBCASE (06)                      casing (recurring)
 ├─ WBPERF (07)                      perforations (recurring)
 ├─ WBLINE (08)                      liner (recurring)
 ├─ WBFORM (09)                      formation (recurring)
 ├─ WBSQEZE (10)                     squeeze (recurring)
 ├─ WBFRESH (11)                     usable quality water protection (recurring)
 ├─ WBOLDLOC (12)                    old (legacy, pre-GPS) location (non-recurring)
 ├─ WBNEWLOC (13)                    new (GPS/WGS84) location (non-recurring)
 ├─ WBPLUG (14)                      plugging data (recurring)
 ├─ WBPLRMKS (15)                    plugging remarks (recurring)
 ├─ WBPLREC (16)                     plugging record (non-recurring)
 ├─ WBPLCASE (17)                    plugging data casing-tubing (recurring)
 ├─ WBPLPERF (18)                    plugging perfs (recurring)
 ├─ WBPLNAME (19)                    plugging data nomenclature (non-recurring)
 ├─ WBDRILL (20)                     drilling permit number (recurring)
 ├─ WBWELLID (21)                    well-ID (recurring)
 ├─ WB14B2 (22)                      14B2 well (non-recurring)
 ├─ WBH15 (23)                       H-15 report (recurring)
 ├─ WBH15RMK (24)                    H-15 remarks (recurring)
 ├─ WBSB126 (25)                     Senate Bill 126, 2-Yr Inactive Program (non-recurring)
 ├─ WBDASTAT (26)                    drilling permit status (recurring)
 ├─ WBW3C (27)                       W3C data (recurring)
 └─ WB14B2RM (28)                    14B2 remarks (recurring)
```

## Record Type Key (segments)

| Key | Segment Name | Recurring? | Description |
|---|---|---|---|
| **01** | **WBROOT** | No | **Root Segment — well identity (API number), county, depth, plug status** |
| **02** | **WBCOMPL** | Yes | **Completion Information — the lease key (district + lease_nbr + well_nbr)** |
| 03 | WBDATE | Yes | Technical Data Forms File Date |
| 04 | WBRMKS | Yes | Remarks |
| 05 | WBTUBE | Yes | Tubing |
| 06 | WBCASE | Yes | Casing |
| 07 | WBPERF | Yes | Perforations |
| 08 | WBLINE | Yes | Liner |
| 09 | WBFORM | Yes | Formation |
| 10 | WBSQEZE | Yes | Squeeze |
| 11 | WBFRESH | Yes | Usable Quality Water Protection |
| 12 | WBOLDLOC | No | Old Location (pre-GPS, lease name + survey/section description) |
| **13** | **WBNEWLOC** | No | **New Location — WGS84 latitude/longitude** |
| 14 | WBPLUG | Yes | Plugging Data |
| 15 | WBPLRMKS | Yes | Plugging Remarks |
| 16 | WBPLREC | No | Plugging Record |
| 17 | WBPLCASE | Yes | Plugging Data Casing-Tubing |
| 18 | WBPLPERF | Yes | Plugging Perfs |
| 19 | WBPLNAME | No | Plugging Data Nomenclature |
| 20 | WBDRILL | Yes | Drilling Permit Number |
| 21 | WBWELLID | Yes | Well-ID |
| 22 | WB14B2 | No | 14B2 Well |
| 23 | WBH15 | Yes | H-15 Report |
| 24 | WBH15RMK | Yes | H-15 Remarks |
| 25 | WBSB126 | No | Senate Bill 126 (2-Yr Inactive Program) |
| 26 | WBDASTAT | Yes | Drilling Permit Status |
| 27 | WBW3C | Yes | W3C Data |
| 28 | WB14B2RM | Yes | 14B2 Remarks |

All records, regardless of segment type, are stored in the same physical
**247-byte** slot: `RRC-TAPE-RECORD-ID` (2 bytes) + segment-specific
fields, right-padded with an `RRC-TAPE-FILLER` field out to 247 bytes
total — same convention as the other three tapes.

## Detailed Field Layout

Byte positions below are **1-indexed**, matching the source COBOL
copybook.

### 01 — WBROOT (Root Segment) — 165 bytes of data + 82 bytes filler = 247 bytes total

Key segment: one per well bore. No parent key (top of the tree) — the
segment key is `WB-API-NUMBER`.

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` (text) | Record type key. `01` = Root Segment |
| `WB-API-CNTY` | 3–5 | `9(03)` (text digits) | County the well bore is located in. For offshore wells, reflects the nearest onshore county |
| `WB-API-UNIQUE` | 6–10 | `9(05)` (text digits) | Number assigned to the well bore which, combined with `WB-API-CNTY`, forms the statewide-unique API number |
| `WB-NXT-AVAIL-SUFFIX` | 11–12 | `9(02)` | Sidetrack-well suffix — documented as "currently not in use" |
| `WB-NXT-AVAIL-HOLE-CHGE-NBR` | 13–14 | `9(02)` | Documented as "currently not in use" |
| `WB-FIELD-DISTRICT` | 15–16 | `9(02)` (text digits) | RRC district the well's field is located in. **Same 14-value encoding as the production/P-4 tapes' district code** (see below) |
| `WB-RES-CNTY-CODE` | 17–19 | `9(03)` (text digits) | For offshore wells, the associated onshore county code |
| `WB-ORIG-COMPL-CC` | 20 | `X(01)` | Century code for `WB-ORIG-COMPL-DATE`: `0`=zeros/unset, `1`=19th century, `2`=20th century, `3`=21st century |
| `WB-ORIG-COMPL-CENT/YY/MM/DD` | 21–28 | `9(2)/9(2)/9(2)/9(2)` | Date well was originally completed, per the W-2/G-1 form |
| `WB-TOTAL-DEPTH` | 29–33 | `9(05)` (text digits) | Maximum depth of the well bore |
| `WB-VALID-FLUID-LEVEL` | 34–38 | `9(05)` | H-15 testing: valid distance (feet) between bottom of usable water and top of fluid, if different from the 250' standard |
| `WB-CERTIFICATION-REVOKED-DATE` | 39–46 | `9(2)×4` | Date House Bill 1975 certification was revoked (CCYYMMDD) |
| `WB-CERTIFICATION-DENIAL-DATE` | 47–54 | `9(2)×4` | Date House Bill 1975 certification was denied |
| `WB-DENIAL-REASON-FLAG` | 55 | `X(01)` | `A`=denied automatically, `M`=denied manually |
| `WB-ERROR-API-ASSIGN-CODE` | 56 | `X(01)` | Flags that a previously assigned API has since changed |
| `WB-REFER-CORRECT-API-NBR` | 57–64 | `9(08)` | Most recent resolved/correct API assignment |
| `WB-DUMMY-API-NUMBER` | 65–72 | `9(08)` | 80,000-range placeholder API for bores without a real API as of Dec 1983 |
| `WB-DATE-DUMMY-REPLACED` | 73–80 | `9(08)` | Date the dummy API was replaced (documented as not in use as of Jan 1984) |
| `WB-NEWEST-DRL-PMT-NBR` | 81–86 | `9(06)` | Date-derived number of the most recently issued drilling permit for this bore |
| `WB-CANCEL-EXPIRE-CODE` | 87 | `X(01)` | Whether the newest drilling permit was cancelled/expired vs. used |
| `WB-EXCEPT-13-A` | 89 | `X(01)` | `Y`/`N` — exception to Statewide Rule 13A granted |
| `WB-FRESH-WATER-FLAG` | 90 | `X(01)` | `Y` = well converted to a fresh water well |
| `WB-PLUG-FLAG` | 91 | `X(01)` | `Y` = well bore has been plugged |
| `WB-PREVIOUS-API-NBR` | 92–99 | `9(08)` | Previous API number, if reassigned |
| `WB-COMPLETION-DATA-IND` | 100 | `X(01)` | `Y`/`N` — completion data on file |
| `WB-HIST-DATE-SOURCE-FLAG` | 101 | `9(01)` | `1`=date from P&I tape, `2`=date from other source |
| `WB-EX14B2-COUNT` | 103–104 | `9(02)` | Count related to 14B2 exceptions |
| `WB-DESIGNATION-HB-1975-FLAG` | 105 | `X(01)` | `A`=auto-designated, `M`=manually designated (House Bill 1975) |
| `WB-DESIGNATION-EFFECTIVE-DATE` | 106–111 | `9(2)×3` | HB 1975 designation effective date (CC/YY/MM) |
| `WB-DESIGNATION-REVISED-DATE` | 112–117 | `9(2)×3` | HB 1975 designation revised date |
| `WB-DESIGNATION-LETTER-DATE` | 118–125 | `9(2)×4` | Date of HB 1975 designation letter |
| `WB-CERTIFICATION-EFFECT-DATE` | 126–131 | `9(2)×3` | HB 1975 certification effective date |
| `WB-WATER-LAND-CODE` | 132 | `X(01)` | `I`=inland waterway, `B`=bay/estuary, `O`=offshore, `L`=land |
| `WB-TOTAL-BONDED-DEPTH` | 133–145 | `9(06)`/`9(07)` (overlapping redefinition) | Bonded depth of the well |
| `WB-OVERRIDE-EST-PLUG-COST` | 146–151 | `9(06)` | Overridden estimated plugging cost |
| `WB-SHUT-IN-DATE` / redefined fields | 152–167 | mixed (see source) | Shut-in date and several 14B2/W3X flag fields sharing overlapping byte ranges via COBOL `REDEFINES` — **not decoded in this pass**, see [Known Issues](#known-issues--open-questions) |
| `RRC-TAPE-FILLER` | 168–247 | `X(80)` | Padding to fill the fixed 247-byte physical record |

`parse_root` in `src/oil_pipeline/extract/wells.py` only decodes
`api_number` (`WB-API-CNTY` + `WB-API-UNIQUE`, concatenated), `field_district`,
`res_cnty_code`, `orig_compl` year/month/day, `total_depth`, `plug_flag`,
and `water_land_code` — the fields needed for the visualizations scoped
for this dataset. The `REDEFINES`-heavy tail of the segment (positions
~152–167) was not decoded; see Known Issues.

#### District Code Table (WB-FIELD-DISTRICT)

Identical encoding to the production and P-4 tapes' district code —
confirms this is a genuinely RRC-wide convention across all four
datasets in this project:

| Stored value | RRC District ID | | Stored value | RRC District ID |
|---|---|---|---|---|
| 01 | 1 | | 08 | 7B |
| 02 | 2 | | 09 | 7C |
| 03 | 3 | | 10 | 8 |
| 04 | 4 | | 11 | 8A |
| 05 | 5 | | 12 | 8B (reserved) |
| 06 | 6 | | 13 | 9 |
| 07 | 6E | | 14 | 10 |

### 02 — WBCOMPL (Completion Information) — recurring

The segment that carries the **production/P-4-compatible lease key**.

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` | `02` = Completion Information |
| `WB-OIL-CODE` | 3 | `X(01)` | Indicates well is carried on the oil schedule |
| `WB-OIL-DIST` | 4–5 | `9(02)` (text digits) | District of the completed oil well. **Same `district_code` encoding as the production/P-4 tapes** |
| `WB-OIL-LSE-NBR` | 6–10 | `9(05)` (text digits) | Lease number of the completed oil well |
| `WB-OIL-WELL-NBR` | 11–16 | `X(06)` (text) | Well number within the lease — **the dimension that reveals multiple wells per lease** |
| *(WB-GAS-KEY redefines WB-OIL-KEY for gas wells — not decoded in this pass; see Known Issues)* | | | |
| `WB-ACTIVE-INACTIVE-CODE` | 46 | `X(01)` | Active/inactive status of this completion |

`parse_completion` decodes `oil_code`, `district_code`, `lease_nbr`,
`well_nbr`, and `active_inactive_code` only.

**Note on `WB-OIL-LSE-NBR` width**: this field is `9(05)` (5 digits) here,
vs. `9(06)` (6 digits) on the production and P-4 tapes' lease number
field. Confirmed as a real difference in the source spec, not a
transcription error — see [Known Issues](#known-issues--open-questions)
for the join implication.

### 13 — WBNEWLOC (New Location) — non-recurring

The segment that carries **modern GPS coordinates**.

| Field | Position | Type | Description |
|---|---|---|---|
| `RRC-TAPE-RECORD-ID` | 1–2 | `X(02)` | `13` = New Location |
| `WB-LOC-COUNTY` | 3–5 | `9(03)` (text digits) | County of the well's surface location |
| ... (abstract/survey/section/block text fields; not decoded) | 6–131 | mixed | Legal land-description fields — not needed for map visualizations, not decoded in this pass |
| `WB-WGS84-LATITUDE` | 133–142 | `S9(3)V9(7)` zoned-decimal DISPLAY | Latitude in WGS84 spherical coordinates |
| `WB-WGS84-LONGITUDE` | 143–152 | `S9(3)V9(7)` zoned-decimal DISPLAY | Longitude in WGS84 spherical coordinates. **Stored as an unsigned magnitude** despite the `S` in the PICTURE clause — see [Known Issues](#known-issues--open-questions) |

`parse_new_location` decodes `loc_county`, `latitude`, and `longitude`
only (`unpack_zoned_decimal` in `src/oil_pipeline/utils.py`).

The source PDF includes an explicit disclaimer on this segment: *"THE
DIGITAL MAPPING DATA... ARE PROVIDED FOR INFORMATIONAL PURPOSES ONLY...
THE RAILROAD COMMISSION... MAKES NO CLAIM AS TO ITS ACCURACY OR
COMPLETENESS. USERS ARE RESPONSIBLE FOR CHECKING THE ACCURACY,
COMPLETENESS, CURRENCY, AND/OR SUITABILITY OF THIS DATA."*

## Known Issues / Open Questions

- **Longitude is stored as an unsigned magnitude, not signed, despite the
  `S9(3)V9(7)` PICTURE clause implying a sign.** Checked the sign nibble
  (trailing overpunch) across ~50,000 `WBNEWLOC` records sampled from 5
  different points across the full file (start, 25%, 50%, 75%, 90%): the
  sign nibble is `0xC` (positive) or `0xF` (zero placeholder) in every
  single case — never `0xD` (negative). Since all Texas wells are west of
  the prime meridian, `parse_new_location` negates the decoded value so
  the resulting `longitude` is standard signed WGS84, directly usable by
  any mapping tool. Latitude, by contrast, decodes correctly as-is
  (positive, since Texas is north of the equator). **Validated against
  the full file**: of 1,018,543 New Location records, 1,011,645 (99.3%)
  have a real (non-zero) coordinate, and **100%** of those land inside
  Texas's actual bounding box (25.86°–36.50°N, -106.54°–-93.53°W) —
  see `notebooks/04_explore_wells.ipynb`.
- **Root's `WB-FIELD-DISTRICT` is unreliable — 55.7% of all 1,211,829
  Root records have it unpopulated (`00`).** This was not anticipated
  from the format spec alone; found via the full-file scan in
  `notebooks/04_explore_wells.ipynb`. **Completion's `district_code` is
  the reliable district source instead**: 0 unpopulated values out of
  777,471 oil completions, full 13-value spread matching the known
  district encoding. Any district/county analysis on this dataset should
  join through Completion, not rely on Root's district field.
- **`WB-ORIG-COMPL-YEAR` contains a handful of clearly invalid values.**
  A full-file scan found 743,017 Root records with a real (non-`0000`)
  completion year, spanning a sensible 1920s–2020s range and shape
  (peaking in the 1980s) — but also 4 records with obviously wrong years
  (`88` and `1200`, appearing once and twice respectively). Trivial
  volume, but filter these out before any drilling-year trend chart
  rather than plotting them as-is.
- **Root's API number and Completion's lease key are two different,
  independent identifiers**, joined only by file position (Completion
  records physically follow their Root record, same convention as
  production/P-4's positional hierarchy). `load_dbf900` stamps
  `api_number` from Root onto every Completion/New Location record
  encountered before the next Root, so all three parsed tables can be
  joined back together downstream by `api_number`.
- **`WB-OIL-LSE-NBR` is 5 digits, not 6.** The production tape's
  `lease_nbr` and P-4's `P4-LEASE-RRCID` are both `9(06)`. Joining
  Completion's lease number to the rest of this project's `lease_id`
  values will need zero-padding to 6 digits first (e.g. `"04411"` →
  `"004411"`) — not yet implemented, flagged here for the transform step.
- **`WB-GAS-KEY` (redefining `WB-OIL-KEY` for gas wells) was not
  decoded.** Only the oil-lease key fields (`WB-OIL-CODE`/`WB-OIL-DIST`/
  `WB-OIL-LSE-NBR`/`WB-OIL-WELL-NBR`) were parsed, matching this
  project's oil-only scope elsewhere. A Completion record for a gas well
  would have its oil-key bytes reinterpreted incorrectly if read as oil
  fields — not a concern for this project since we filter to oil, but
  worth knowing if gas data is ever added.
- **EBCDIC code page not independently validated for this file** the way
  the production tape was (full-file district-code cross-check). Real
  decoded latitude/longitude values landing squarely inside Texas's
  actual bounding box (25.8°–36.5°N, -106.6°–-93.5°W) across a 300,000+
  record sample is a strong practical signal that `cp037` is correct
  here too, but this hasn't been checked as rigorously as the production
  tape's full-file validation.
- **The Root segment's tail (roughly positions 152–167) uses COBOL
  `REDEFINES`** to overlap several fields (`WB-SHUT-IN-DATE` and various
  14B2/W3X flags) in the same byte range depending on context. Not
  decoded in this pass — not needed for the currently scoped
  visualizations (map, county, drilling-year trend, active/plugged,
  depth, wells-per-lease, land/water code).
- **"Number of records" (29,823,101) counts physical 247-byte slots
  across all 28 segment types combined** — not the number of wells. The
  actual well count (Root segment records only) requires a full-file
  scan; not yet run as of writing this document (pending the exploration
  notebook).
- Field layouts for the 25 non-core segment types (03–12, 14–28) are
  cataloged by key/name/recurrence only in this document; full
  field-by-field detail can be added later if a specific downstream need
  arises (e.g. casing/tubing/perforation detail, plugging records).
