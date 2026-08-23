# translation/

Translation, Romanization, and QA pipeline scripts for producing the
5-language dataset from the English BFCL source.

Covers: query translation (PAR/FT), Romanization (native script -> Latin
script via a transliteration tool per Section 5 of
`Indic_ToolCalling_Project_Plan.md`), and QA (back-translation + judge model,
extending the approach validated in the archived pilot -- see the
`archive/pilot-hindi-tamil-simple-python` branch for that prior version).
