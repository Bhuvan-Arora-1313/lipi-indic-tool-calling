# Hindi Cycle 2 -- reviewer behavior notes

Recorded 2026-09-19, right after both Cycle 2 adjudication files
(`Hindi cycle_2  review Anshul Gupta.xlsx`, `Hindi cycle_2  review - Jayant
Kapoor.xlsx`) came back complete. Same purpose as
`tamil_cycle2_reviewer_behavior.md`: capture *how* the two reviewers
behaved when adjudicating, not just the resolved text, and compare
against Tamil's pattern now that a second reviewer pair's data exists.

Source data: `hindi_final_resolved.jsonl` and `hindi_cycle2_decisions.json`
in this directory. Raw reviewer files untouched, as always.

## Bucket 3 -- asymmetric disagreements (split 4 Anshul / 4 Jayant)

Unlike Tamil (where all 8 bucket-3 items happened to land on one
adjudicator), Hindi's 8 split evenly by the adjudicator-is-whoever-said-
Correct rule.

| Adjudicator | Accept fix | Original stands |
|---|---|---|
| Anshul (4 items) | 1 (25%) | 3 (75%) |
| Jayant (4 items) | 2 (50%) | 2 (50%) |
| **Overall (8 items)** | **3 (37.5%)** | **5 (62.5%)** |

**Reading**: majority held their own original "Correct" call rather than
reversing it -- the opposite lean from Tamil, where Rohan reversed
himself 5/8 times (62.5% accept fix). Both are small samples (n=8), so
this is a descriptive contrast, not a statistically powered claim, but
it's a clean opposite-direction result worth tracking as more languages
complete Cycle 2.

## Bucket 4 -- conflicting fixes (split 2 Anshul / 3 Jayant)

| base_id | Adjudicator | Decision | Picked own fix? |
|---|---|---|---|
| multiple_4 | Anshul | Version A | Yes |
| multiple_6 | Anshul | Version A | Yes |
| multiple_64 | Jayant | Version A | No |
| multiple_99 | Jayant | Version A | No |
| multiple_106 | Jayant | Version B | Yes |

| Picked | Count | % |
|---|---|---|
| Their OWN fix | 3 | 60% |
| The OTHER reviewer's fix | 2 | 40% |

**Reading**: majority picked their own fix -- again the opposite lean
from Tamil (85.7% picked the *other* reviewer's fix there). n=5, even
smaller than bucket 3's n=8, so read this as a single data point, not a
trend. No "write new" cases this round (Tamil had one).

## Overall load

Anshul adjudicated 6 of 13 total Cycle 2 items (4 bucket-3 + 2 bucket-4);
Jayant adjudicated 7 (4 bucket-3 + 3 bucket-4) -- close to even, unlike
Tamil's 12/4 split, because Hindi's bucket-3 "whoever said Correct"
assignment happened to fall evenly here rather than onto one reviewer.

## Takeaway for the methodology

Hindi shows the opposite behavioral lean from Tamil on both axes
(more self-consistency, less deference to the other reviewer's fix),
while Tamil showed a deferential/self-reversing pattern. Neither pattern
on its own indicates a problem with the design -- both are plausible
outcomes of genuine independent judgment, and neither reviewer pair
shows an extreme (e.g. 100% rubber-stamp or 100% reversal) that would
suggest someone isn't actually engaging with the adjudication. But the
sign flip between the two languages is a reminder not to treat either
single dataset's reviewer-behavior stats as a general property of "how
adjudication goes" -- it's reviewer-pair-specific, and small-n (5-13
items) in both cases. Worth re-checking once Gujarati and PARA/SYNO
Cycle 2 data exist to see if a consistent pattern emerges across more
than two pairs, or if this stays idiosyncratic per pair.
