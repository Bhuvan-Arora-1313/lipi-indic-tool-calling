# Tamil Cycle 2 -- reviewer behavior notes

Recorded 2026-09-09, right after both Cycle 2 adjudication files
(`Tamil_review_cycle_2_Rohan.xlsx`, `Tamil_review_cycle_2_Dhayanidhi.xlsx`)
came back complete. Purpose: capture *how* the two reviewers actually
behaved when adjudicating disagreements, not just the resolved text --
useful evidence for whether the two-reviewer Cycle 1/Cycle 2 design is
doing its job (catching real disagreement, not just noise) and whether
either reviewer shows a self-favoring or rubber-stamping pattern.

Source data: `tamil_final_resolved.jsonl` and `tamil_cycle2_decisions.json`
in this directory. Raw reviewer files untouched, as always.

## Bucket 3 -- asymmetric disagreements (Rohan adjudicating all 8)

All 8 of the bucket-3 disagreements happened to have Dhayanidhi flagging
Incorrect and Rohan saying Correct in Cycle 1 (not a design choice --
just how the 200 items fell; the adjudicator-is-whoever-said-Correct
rule assigns per item, and it happened to land on Rohan every time
here). Rohan was shown his own original "Correct" call against
Dhayanidhi's proposed fix and reasoning, with no requirement to change
his mind.

| Decision | Count | % |
|---|---|---|
| Accept fix (reversed himself) | 5 | 62.5% |
| Original stands (held his call) | 3 | 37.5% |
| Neither / write new | 0 | 0% |

**Reading**: Rohan reversed his own initial "Correct" verdict more
often than he held it -- the opposite of a defensive/anchoring pattern.
The 3 items where he held firm (`multiple_11, 14, 19`) are worth a
second look if a third opinion is ever wanted, since they're the cases
where the two reviewers still disagree even after adjudication (Rohan's
"Original stands" is the final word structurally, but it's not
independent confirmation -- it's the same person who called it Correct
the first time).

## Bucket 4 -- conflicting fixes (adjudicator randomly assigned, blinded A/B)

8 items, split 4/4 between Rohan and Dhayanidhi by the fixed-seed random
assignment. Both versions shown blinded ("Version A"/"Version B", not
attributed by name) -- the adjudicator is always one of the two original
reviewers, so this blinding can't hide identity from careful reading of
writing style, but it does remove the visible "mine vs. theirs" framing.

| Decision | Count | % |
|---|---|---|
| Version A or B (picked one) | 7 | 87.5% |
| Neither / write new | 1 | 12.5% |

Of the 7 A/B picks, cross-checked post-hoc against the (reviewer-hidden)
authorship record:

| Picked | Count | % of A/B picks |
|---|---|---|
| The OTHER reviewer's fix | 6 | 85.7% |
| Their OWN fix | 1 | 14.3% |

**Reading**: strong lean toward the other reviewer's version, not their
own -- no evidence of self-favoring bias in either direction; if
anything the opposite. Small sample (n=7), so this is a descriptive
note, not a statistically powered claim.

**The one "write new" case (`multiple_37`)** is the clearest example of
real engagement rather than mechanical picking. Source: "Find the final
velocity of an object thrown up at 40 m/s after 6 seconds."
- Version A fixed "up" (தூக்கி எறியப்பட்டது -> மேல்நோக்கி வீசப்பட்டது) but
  left வேகம் (speed) uncorrected to திசைவேகம் (velocity).
- Version B fixed வேகம் -> திசைவேகம் but never restored "up".
- Rohan's written-new answer combines both corrections rather than
  picking the version with only one of the two fixes -- evidence he
  read both proposed fixes closely enough to notice each one was only
  half-right, instead of just choosing the "less wrong" of two options.

## Overall load

Rohan adjudicated 12 of the 16 total Cycle 2 items (8 bucket-3 + 4
bucket-4); Dhayanidhi adjudicated 4 (bucket-4 only). This asymmetry is
a direct consequence of the bucket-3 rule (adjudicator = whoever said
Correct) landing entirely on Rohan's side for this dataset, not a flaw
in the random bucket-4 assignment, which came out exactly balanced
(4/4) as designed.

## Takeaway for the methodology

Both signals -- majority self-reversal in bucket 3, majority
other-preference in bucket 4 -- point the same direction: neither
reviewer appears to be defending their own earlier call by default.
Combined with the one genuinely synthesized "write new" answer, this is
a reasonable evidence base that the Cycle 1/Cycle 2 design is producing
real adjudication, not rubber-stamping in either direction. Worth
re-checking once Hindi and PARA/SYNO Cycle 2 data exist, to see if the
pattern holds with different reviewer pairs.
