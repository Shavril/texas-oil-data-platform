# Data Dictionary — P-5 Organization Report Database

## Dataset Description

This dataset is a full extract of the Railroad Commission of Texas (RRC)
Organization Report ("P-5") system — the master list of every organization
(company) that has filed a Form P-5 with the RRC, active or inactive. This
is the dataset that maps the operator numbers found in the production and
P-4 tapes (`docs/data_rrc_production.md`, `docs/data_p4_operators.md`) to
an actual **company name**.

Same physical convention as the other two RRC tapes: a **hierarchical
database dump**, fixed-length records distinguished by a record-type key
at the start of each record. Two differences from the other two files:

- The record-type key here is a **2-character alphanumeric code** (e.g.
  `'A '`, `'F '`, `'1T'`) rather than a 2-digit number.
- The hierarchy is much shallower — **9 record types** total, vs. 24
  (production) or 30 (P-4).

- **One "row" (physical record) is one segment of one of 9 possible
  types**, not one organization. Only the `'A '` (Organization
  Information) segment is needed for the immediate goal — it carries the
  operator/organization number, the company name, and P-5 filing status
  all in one record, with no further joins required.
- Record types `000001`–`000015` are internal RRC office designations and
  `123456` is a training/test record — per the spec these "will not be
  duplicated onto the tape," so they shouldn't appear in this extract.

## Source

- **Publisher**: Railroad Commission of Texas (RRC)
- **Publication**: *Organization Report (P-5) System Magnetic Tape User's
  Guide*, Publication Number **ORA001** (First Edition October 1981; last
  revision October 2014)
- **Format spec file**:
  `data/raw/organizations/ora001_p5_manual_october-2014.pdf` (kept
  alongside the raw data; not modified)
- **Data file**: `data/raw/organizations/orf850.ebc`
- **RRC internal dataset name**: `S.ORF850` (Organization Report File Tape)

## File Format & Encoding

| Property | Value |
|---|---|
| File name | `orf850.ebc` |
| File size | 213,886,400 bytes |
| Character encoding | **EBCDIC** (assumed IBM code page **037** — same assumption as the other two RRC files; not explicitly named in this source PDF either, but **validated against decoded data** below) |
| Record format | **Fixed-length binary records, 350 bytes each** — no delimiters (blocksize 10,500 = 350 × 30 records/block, matching the spec's stated blocking factor) |
| Total records | **611,104** (`213,886,400 / 350`, divides evenly) |
| Is it CSV / fixed-width text? | No — same fixed-length binary mainframe extract style as the other two RRC files, same system template (`IBM 2003-116`, IBM standard tape labels, 1600/6250 BPI). |

**EBCDIC validated against real data**: decoded a 50,000-record sample
with `cp037` — all 6,071 sampled `'A '` (Organization) records produced
clean, sensible company names (e.g. `"A & S VACUUM SERVICE"`, `"A&A
ENERGY SERVICES LLC"`, `"A-1 ROCKET ENERGY SERVICES, LLC"`) and valid
status codes, no garbled text anywhere. Stronger validation than the P-4
file got, though still a sample rather than the full 611,104 records.

## Segment Hierarchy

```
'1T' (Specialty/activity code table — NOT tied to an organization;
       all '1T' records sit at the front of the tape)

'A ' (Organization Information — one per organization; the root)
 ├─ 'F ' (Specialty codes / specialty mailing addresses; optional, repeatable)
 │   └─ 'H ' (District mailing addresses within a specialty code; optional, repeatable)
 │       └─ 'J ' (Field information; optional, repeatable — reserved for future use per spec)
 ├─ 'K ' (Officer/agent information; optional, repeatable)
 ├─ 'P ' (Remarks, RRC-internal use; optional, repeatable)
 ├─ 'U ' (Activity indicators — e.g. gas gatherer, oil operator; optional, repeatable)
 └─ 'R ' (Activity restrictions; optional, repeatable)
```

## Record Type Key (segments)

Only **`'A '`** (bold) is documented field-by-field below — it alone
carries everything needed to map an operator number to a company name.
The rest are cataloged here for completeness only.

| Key | Record Description |
|---|---|
| `1T` | Specialty code / activity indicator table (reference data, not org-specific) |
| **`A `** | **Organization Information — master record: operator number, company name, P-5 status, address** |
| `F ` | Specialty codes (specialty mailing addresses) |
| `H ` | Specialty addresses by district |
| `J ` | Field information (reserved for future use) |
| `K ` | Officer/agent information |
| `P ` | Remarks (RRC internal use only) |
| `U ` | Activity indicators (e.g. gas gatherer, oil operator, gas purchaser) |
| `R ` | Activity restrictions |

All records are stored in the same physical **350-byte** slot, right-padded
with filler beyond each segment's actual data length — same convention as
the other two RRC files.

## Detailed Field Layout

Byte positions below are **1-indexed**. Unlike the other two RRC format
PDFs, this document's "POSITION" column got scrambled by PDF-to-text
extraction (`pdftotext -layout` visually merged it with an unrelated
column). Positions below were **reconstructed by hand** — summing each
field's `PIC` width in declaration order — then **cross-validated**
against the handful of position numbers that did extract correctly
further down the document (e.g. `OROR-PHONE-NUMBER` at position 259);
every single one matched the hand-reconstructed value exactly.

### `'A '` — Organization Information (Root Segment) — first ~268 of 350 bytes

Key segment: one per organization (company). No parent key — this is the
root of the hierarchy for a given organization.

| Field | Position | Type | Description |
|---|---|---|---|
| `OROR-ORGANIZATION-INFO-ID` | 1–2 | `X(02)` (text) | Record type key. `'A '` = Organization Information |
| `OROR-ORG-OPERATOR-NUMBER` | 3–8 | `9(06)` (text digits) | **The RRC-assigned operator/organization ID number.** Same number as `P4-OPERATOR-NUMBER` on the P-4 tape and `PD-...` equivalents — this is the join key |
| `OROR-ORG-ORGANIZATION-NAME` | 9–40 | `X(32)` (text) | **The company name, as filed on RRC Form P-5.** This is the field this whole exploration was for |
| `OROR-REFILING-REQUIRED-FLAG` | 41 | `X(01)` | `Y`/`N` — whether annual P-5 refiling is required |
| `OROR-P-5-STATUS` | 42 | `X(01)` | `A` = Active, `I` = Inactive, `D` = Delinquent, `S` = See remarks. **Real data also contains undocumented values `X`, `H`, `R`** (confirmed via a full-file scan of all 74,947 `'A '` records — see [Known Issues](#known-issues--open-questions)) |
| `OROR-HOLD-MAIL-CODE` | 43 | `X(01)` | `H` = hold mail (all mailing addresses for this org are invalid), `N` = don't hold |
| `OROR-RENEWAL-LETTER-CODE` | 44 | `X(01)` | `P` = property renewal, `N` = non-property renewal |
| `OROR-ORGANIZATION-CODE` | 45 | `X(01)` | Entity type: `A` corporation, `B` limited partnership, `C` sole proprietor, `D` partnership, `E` trust, `F` joint venture, `G` other |
| `OROR-ORGAN-OTHER-COMMENT` | 46–65 | `X(20)` | Free-text comment when entity type is "other" |
| `OROR-GATHERER-CODE` | 66–70 | `X(05)` | Gatherer code |
| `OROR-ORG-ADDR-LINE1` | 71–101 | `X(31)` | Mailing address line 1 |
| `OROR-ORG-ADDR-LINE2` | 102–132 | `X(31)` | Mailing address line 2 |
| `OROR-ORG-ADDR-CITY` | 133–145 | `X(13)` | Mailing address city |
| `OROR-ORG-ADDR-STATE` | 146–147 | `X(02)` | Mailing address state |
| `OROR-ORG-ADDR-ZIP` | 148–152 | `9(05)` | Mailing address ZIP |
| `OROR-ORG-ADDR-ZIP-SUFFIX` | 153–156 | `9(04)` | Mailing address ZIP+4 |
| `OROR-LOCATION-ADDR-LINE1` | 157–187 | `X(31)` | Physical location address line 1 |
| `OROR-LOCATION-ADDR-LINE2` | 188–218 | `X(31)` | Physical location address line 2 |
| `OROR-LOCATION-ADDR-CITY` | 219–231 | `X(13)` | Physical location city |
| `OROR-LOCATION-ADDR-STATE` | 232–233 | `X(02)` | Physical location state |
| `OROR-LOCATION-ADDR-ZIP` | 234–238 | `9(05)` | Physical location ZIP |
| `OROR-LOCATION-ADDR-ZIP-SUFFIX` | 239–242 | `9(04)` | Physical location ZIP+4 |
| `OROR-DATE-BUILT` | 243–250 | `9(08)` (CCYYMMDD) | Date this organization record was created |
| `OROR-DATE-INACTIVE` | 251–258 | `9(08)` (CCYYMMDD) | Date the organization became inactive, if applicable |
| `OROR-PHONE-NUMBER` | 259–268 | `9(10)` | Phone number (area code + prefix + suffix) |

Remaining bytes (269–350, ~82 bytes: `OROR-REFILE-NOTICE-MONTH` and
further fields/filler) not mapped in this pass — not needed for the
immediate operator-number → company-name join.

## Known Issues / Open Questions

- **Undocumented `P-5` status values found in real data.** The spec
  defines only `A`/`I`/`D`/`S` for `OROR-P-5-STATUS`. A full-file scan of
  all 74,947 `'A '` records (`notebooks/03_explore_p5_organizations.ipynb`)
  found the full distribution: `I`=63,393, `A`=6,829, `D`=3,923, `X`=549,
  `S`=247, `H`=4, `R`=2. Three values (`X`, `H`, `R`) aren't in the source
  PDF at all — an earlier smaller sample (6,071 records) only caught `X`;
  `H` and `R` are rare enough (4 and 2 occurrences) that they only surfaced
  once the full file was scanned. Not yet investigated further; treat all
  three as "unknown status" rather than guessing their meaning. Worth
  revisiting if status filtering matters for a join (e.g. "active
  operators only").
- **This dataset can have multiple `'A '` records historically** — the
  spec doesn't fully clarify whether an inactive/superseded organization
  keeps a permanent `'A '` record or whether operator numbers ever get
  reused. Given `OROR-DATE-INACTIVE` exists as a field, it's likely one
  `'A '` record persists per organization (updated in place), not one per
  historical state — but this hasn't been confirmed against real data.
- **"Number of records" (611,104) counts physical 350-byte slots across
  all 9 record types combined** — not the number of organizations. A full
  scan (filtering to `'A '` records only) would be needed to get the
  actual organization count; not done in this pass (steps 1–2 only:
  inspect + document, per `CLAUDE.md` Phase 1 Tasks).
- Field layouts for the 8 non-core record types (`1T`, `F `, `H `, `J `,
  `K `, `P `, `U `, `R `) are cataloged by key/description only — full
  field-by-field detail can be added later if a specific need arises
  (e.g. `U ` activity indicators, to distinguish operators from gatherers
  from purchasers).
