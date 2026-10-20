# Hallucination Check

## Summary

- Paper: Indic Tool-Calling Robustness, Midterm Report (main.tex, references.bib, 23 entries)
- Total references extracted: 23
- Verified: 16
- Malformed (real work, wrong metadata): 7
- Not found (possible fabrication): 0
- Unverifiable: 0
- Incomplete: 0

Every entry is a real work. No reference looks fabricated. Seven entries carry wrong or outdated metadata. Three of them are superseded preprints (MLCL, Gorilla, Hammer). One has a missing author (Toolformer). One uses a corporate author that does not match the record (Qwen3). Two blog posts are cited under titles that are not their real titles (Falcon 3, Sarvam-M). A corrected bibliography with all 23 keys unchanged is in `references_corrected.bib`.

## Detailed Results

| # | Ref | Status | Confidence | Cited title | Issue(s) | Canonical source (URL) |
|---|---|---|---|---|---|---|
| 1 | luo2026lost | MALFORMED (venue) | High | Lost in Execution: On the Multilingual Robustness of Tool Calling in Large Language Models | Cited as arXiv preprint. Published at ACL 2026, Volume 1 Long Papers. | https://aclanthology.org/2026.acl-long.2039/ |
| 2 | chauhan2026api | VERIFIED | High | When the API Speaks the Wrong Language: Revisiting Post-Training for Multilingual Tool Use | None. arXiv v1 only, no venue found. See Claim Consistency for a framing issue. | https://arxiv.org/abs/2608.11715 |
| 3 | patil2025bfcl | VERIFIED | High | The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models | None | https://proceedings.mlr.press/v267/patil25a.html |
| 4 | patil2023gorilla | MALFORMED (venue, year) | High | Gorilla: Large Language Model Connected with Massive APIs | Cited as 2023 arXiv preprint. Published at NeurIPS 2024 (vol. 37). | https://proceedings.neurips.cc/paper_files/paper/2024/hash/e4c61f578ff07830f5c37378dd3ecb0d-Abstract-Conference.html |
| 5 | schick2023toolformer | MALFORMED (authors) | High | Toolformer: Language Models Can Teach Themselves to Use Tools | NeurIPS version has 9 authors. Eric Hambro is missing from the cited list. | https://proceedings.neurips.cc/paper_files/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html |
| 6 | qin2024toolllm | VERIFIED | High | ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs | None. ICLR 2024 spotlight. "and others" for 19 authors. | https://proceedings.iclr.cc/paper_files/paper/2024/hash/28e50ee5b72e90b50e7196fde8ea260e-Abstract-Conference.html |
| 7 | li2023apibank | VERIFIED | High | API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs | None. EMNLP 2023 main. | https://aclanthology.org/2023.emnlp-main.187/ |
| 8 | gala2023indictrans2 | VERIFIED | High | IndicTrans2: Towards High-Quality and Accessible Machine Translation Models for all 22 Scheduled Indian Languages | None. TMLR 2023. | https://openreview.net/forum?id=vfT4YuzAYA |
| 9 | madhani2023aksharantar | VERIFIED | High | Aksharantar: Open Indic-language Transliteration Datasets and Models for the Next Billion Users | Casing only. Findings of EMNLP 2023 is correct. | https://aclanthology.org/2023.findings-emnlp.4/ |
| 10 | ahuja2023mega | VERIFIED | High | MEGA: Multilingual Evaluation of Generative AI | None. EMNLP 2023 main. | https://aclanthology.org/2023.emnlp-main.258/ |
| 11 | singh2024indicgenbench | VERIFIED | High | IndicGenBench: A Multilingual Benchmark to Evaluate Generation Capabilities of LLMs on Indic Languages | None. ACL 2024 long. | https://aclanthology.org/2024.acl-long.595/ |
| 12 | doddapaneni2023indicxtreme | VERIFIED | High | Towards Leaving No Indic Language Behind: Building Monolingual Corpora, Benchmark and Models for Indic Languages | None. ACL 2023 long. | https://aclanthology.org/2023.acl-long.693/ |
| 13 | husain2024romansetu | VERIFIED | High | RomanSetu: Efficiently Unlocking Multilingual Capabilities of Large Language Models via Romanization | Casing only. ACL 2024 long. | https://aclanthology.org/2024.acl-long.833/ |
| 14 | khanuja2020gluecos | VERIFIED | High | GLUECoS: An Evaluation Benchmark for Code-Switched NLP | None. ACL 2020. | https://aclanthology.org/2020.acl-main.329/ |
| 15 | yang2025qwen3 | MALFORMED (authors) | High | Qwen3 Technical Report | Cited author "Qwen Team". The arXiv record and the Qwen3 README citation list 60 named authors led by An Yang. | https://arxiv.org/abs/2505.09388 |
| 16 | gemma2025gemma3 | VERIFIED | High | Gemma 3 Technical Report | None. "Gemma Team" is the first listed author on arXiv and the author Google's model card asks for. | https://arxiv.org/abs/2503.19786 |
| 17 | grattafiori2024llama3 | VERIFIED | High | The Llama 3 Herd of Models | None. Tech report, no venue. | https://arxiv.org/abs/2407.21783 |
| 18 | lin2024hammer | MALFORMED (venue, title, year) | High | Hammer: Robust Function-Calling for On-Device Language Models via Function Masking | Published at ICLR 2025 (spotlight) under the title "Robust Function-Calling for On-Device Language Model via Function Masking". | https://proceedings.iclr.cc/paper_files/paper/2025/hash/d45e0bfb5a39477d56b55c0824200008-Abstract-Conference.html |
| 19 | falcon3 | MALFORMED (title) | High | The Falcon 3 Family of Open Models | Real title is "Welcome to the Falcon 3 Family of Open Models!" | https://huggingface.co/blog/falcon3 |
| 20 | sarvamm | MALFORMED (title) | High | Sarvam-M: A Hybrid-Reasoning Indic Language Model | Real page title is "Sarvam-M" with subtitle "Explorations in Post Training and Inferencing Optimizations for a Hybrid Indic LLM". The cited title does not appear on the page. | https://www.sarvam.ai/blogs/sarvam-m |
| 21 | kwon2023vllm | VERIFIED | High | Efficient Memory Management for Large Language Model Serving with PagedAttention | None. SOSP 2023. | https://doi.org/10.1145/3600006.3613165 |
| 22 | cohen1960kappa | VERIFIED | High | A Coefficient of Agreement for Nominal Scales | None | https://doi.org/10.1177/001316446002000104 |
| 23 | mcnemar1947note | VERIFIED | High | Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages | None | https://doi.org/10.1007/BF02295996 |

Author placeholders (Phase 2, advisory). Ten entries name one author followed by "and others". These are qin2024toolllm (19 real authors), li2023apibank (9), gala2023indictrans2 (14), madhani2023aksharantar (8), ahuja2023mega (12), singh2024indicgenbench (5), doddapaneni2023indicxtreme (7), husain2024romansetu (7), grattafiori2024llama3 (561 on arXiv) and the original lin2024hammer (12). An unnumbered "and others" renders as "et al." and does not state a false count, so none of these is a truncation error. Four entries use a corporate author (Qwen Team, Gemma Team, Technology Innovation Institute, Sarvam AI). Only the Qwen one conflicts with the record.

## Malformed References

### luo2026lost

Raw citation. `@article{luo2026lost, title={Lost in Execution: On the Multilingual Robustness of Tool Calling in Large Language Models}, author={Luo, Z. and Kutralingam, T. P. and Okoani, O. N. and Xu, W. and Wei, H. and Hu, X.}, journal={arXiv preprint arXiv:2601.05366}, year={2026}}`

| Field | Cited | Real |
|---|---|---|
| Title | Lost in Execution: On the Multilingual Robustness of Tool Calling in Large Language Models | Same |
| Authors | Luo, Kutralingam, Okoani, Xu, Wei, Hu (6, initials) | Zheng Luo, T Pranav Kutralingam, Ogochukwu N. Okoani, Wanpeng Xu, Hua Wei, Xiyang Hu (6) |
| Venue | arXiv preprint | Proceedings of the 64th Annual Meeting of the ACL (Volume 1, Long Papers), pages 44059 to 44077 |
| Year | 2026 | 2026 |
| Identifier | arXiv:2601.05366 (resolves correctly, Comments field says "ACL 2026") | DOI 10.18653/v1/2026.acl-long.2039 |

Canonical source is https://aclanthology.org/2026.acl-long.2039/. This is a superseded preprint. Use the ACL Anthology BibTeX, which is in the corrected file.

### patil2023gorilla

Raw citation. `@article{patil2023gorilla, title={Gorilla: Large Language Model Connected with Massive {API}s}, author={Patil, Shishir G. and Zhang, Tianjun and Wang, Xin and Gonzalez, Joseph E.}, journal={arXiv preprint arXiv:2305.15334}, year={2023}}`

| Field | Cited | Real |
|---|---|---|
| Title | Gorilla: Large Language Model Connected with Massive APIs | Same |
| Authors | Patil, Zhang, Wang, Gonzalez (4) | Same (4) |
| Venue | arXiv preprint | Advances in Neural Information Processing Systems 37 (NeurIPS 2024), pages 126544 to 126565 |
| Year | 2023 | 2024 |
| Identifier | arXiv:2305.15334 (resolves correctly) | DOI 10.52202/079017-4020 |

Canonical source is the NeurIPS proceedings page in the table above. This is a superseded preprint. The in-text citation will now read "Patil et al., 2024".

### schick2023toolformer

Raw citation. `@inproceedings{schick2023toolformer, ..., author={Schick, Timo and Dwivedi-Yu, Jane and Dess{\`\i}, Roberto and Raileanu, Roberta and Lomeli, Maria and Zettlemoyer, Luke and Cancedda, Nicola and Scialom, Thomas}, booktitle={Advances in Neural Information Processing Systems (NeurIPS)}, year={2023}}`

| Field | Cited | Real |
|---|---|---|
| Title | Toolformer: Language Models Can Teach Themselves to Use Tools | Same |
| Authors | 8 named | 9. Schick, Dwivedi-Yu, Dessì, Raileanu, Lomeli, Hambro, Zettlemoyer, Cancedda, Scialom |
| Venue | NeurIPS | NeurIPS 2023 (vol. 36), pages 68539 to 68551 |
| Year | 2023 | 2023 |
| Identifier | None | DOI 10.52202/075280-2997 |

The cited list matches arXiv v1, which has 8 authors. The NeurIPS version that the entry claims to cite adds Eric Hambro.

### yang2025qwen3

Raw citation. `@article{yang2025qwen3, title={Qwen3 Technical Report}, author={{Qwen Team}}, journal={arXiv preprint arXiv:2505.09388}, year={2025}}`

| Field | Cited | Real |
|---|---|---|
| Title | Qwen3 Technical Report | Same |
| Authors | "Qwen Team" (corporate) | 60 named authors, first is An Yang. The Qwen3 GitHub README citation uses the same named list. |
| Venue | arXiv preprint | arXiv preprint (tech report, no venue) |
| Year | 2025 | 2025 |
| Identifier | arXiv:2505.09388 | Resolves correctly |

The citation key already assumes "Yang". With the corporate author, the in-text citation would read "Qwen Team, 2025" instead of "Yang et al., 2025".

### lin2024hammer

Raw citation. `@article{lin2024hammer, title={Hammer: Robust Function-Calling for On-Device Language Models via Function Masking}, author={Lin, Qiqiang and others}, journal={arXiv preprint arXiv:2410.04587}, year={2024}}`

| Field | Cited | Real (published version) |
|---|---|---|
| Title | Hammer: Robust Function-Calling for On-Device Language Models via Function Masking | Robust Function-Calling for On-Device Language Model via Function Masking (ICLR proceedings metadata). The camera-ready PDF header reads "Language Models". |
| Authors | Lin and others | 12. Lin, Wen, Peng, Nie, Liao, Jun Wang, Mo, Zhou, Cheng, Zhao, Jun Wang, Zhang |
| Venue | arXiv preprint | ICLR 2025 (spotlight), pages 85446 to 85466 |
| Year | 2024 | 2025 |
| Identifier | arXiv:2410.04587 (resolves correctly) | OpenReview yVQcr4qjD6 |

The ICLR proceedings BibTeX lists only 11 authors because it collapses the two co-authors named Jun Wang into one and moves him. The camera-ready PDF and OpenReview both list 12. The corrected entry uses the proceedings BibTeX with the author field replaced by the 12-author OpenReview order. That author field was edited by hand.

### falcon3

Raw citation. `@misc{falcon3, title={The {Falcon 3} Family of Open Models}, author={{Technology Innovation Institute}}, year={2024}, howpublished={\url{https://huggingface.co/blog/falcon3}}}`

| Field | Cited | Real |
|---|---|---|
| Title | The Falcon 3 Family of Open Models | Welcome to the Falcon 3 Family of Open Models! |
| Authors | Technology Innovation Institute | Falcon LLM TII UAE (the TII organisation account) |
| Venue | Hugging Face blog URL | Same |
| Year | 2024 | Published 17 December 2024 |
| Identifier | URL | Resolves correctly |

Minor. No official BibTeX exists. The title was corrected by hand from the page.

### sarvamm

Raw citation. `@misc{sarvamm, title={{Sarvam-M}: A Hybrid-Reasoning {I}ndic Language Model}, author={{Sarvam AI}}, year={2025}, howpublished={\url{https://www.sarvam.ai/blogs/sarvam-m}}}`

| Field | Cited | Real |
|---|---|---|
| Title | Sarvam-M: A Hybrid-Reasoning Indic Language Model | Sarvam-M. Subtitle "Explorations in Post Training and Inferencing Optimizations for a Hybrid Indic LLM" |
| Authors | Sarvam AI | Sarvam AI |
| Venue | Sarvam blog URL | Same |
| Year | 2025 | Published 23 May 2025 |
| Identifier | URL | Resolves correctly |

The cited title appears nowhere on the page and looks paraphrased. No official BibTeX exists. The title was corrected by hand from the page heading and subheading.

## Not Found References

None.

## Unverifiable References

None.

## Incomplete References

None. Every entry has an author, a title and a venue or URL.

## Consistency Issues

- Duplicate-work clusters. None found.
- Orphan in-text citations. None found. All 23 keys used in main.tex exist in references.bib.
- Uncited bibliography entries. None found. All 23 entries are cited at least once.
- Key and year drift (advisory). After the fixes, patil2023gorilla carries year 2024 and lin2024hammer carries year 2025. The keys were kept unchanged as requested. The rendered citations will show the new years.

## Preprint to published upgrades

| Key | Verdict | Canonical URL |
|---|---|---|
| luo2026lost | Published at ACL 2026 (main conference, Long Papers). Replaced. | https://aclanthology.org/2026.acl-long.2039/ |
| chauhan2026api | No published version found. Stays arXiv. Only v1 (12 Aug 2026) exists, with no Comments or Journal-ref. Searches of ACL Anthology, OpenReview and proceedings sites found nothing. | https://arxiv.org/abs/2608.11715 |
| patil2023gorilla | Published at NeurIPS 2024. Replaced. | https://proceedings.neurips.cc/paper_files/paper/2024/hash/e4c61f578ff07830f5c37378dd3ecb0d-Abstract-Conference.html |
| lin2024hammer | Published at ICLR 2025 (spotlight) under a shortened title. Replaced. | https://proceedings.iclr.cc/paper_files/paper/2025/hash/d45e0bfb5a39477d56b55c0824200008-Abstract-Conference.html |
| yang2025qwen3 | Tech report, stays arXiv. No Journal-ref. Author field fixed. | https://arxiv.org/abs/2505.09388 |
| gemma2025gemma3 | Tech report, stays arXiv. No Journal-ref. | https://arxiv.org/abs/2503.19786 |
| grattafiori2024llama3 | Tech report, stays arXiv. No Journal-ref. | https://arxiv.org/abs/2407.21783 |

The non-arXiv venues were also checked. ToolLLM (ICLR 2024), API-Bank (EMNLP 2023 main), IndicTrans2 (TMLR 2023), Aksharantar (Findings of EMNLP 2023), MEGA (EMNLP 2023 main), IndicGenBench (ACL 2024 long), IndicXTREME (ACL 2023 long), RomanSetu (ACL 2024 long), GLUECoS (ACL 2020), BFCL (ICML 2025, PMLR 267), vLLM (SOSP 2023), Cohen 1960 and McNemar 1947 are all cited with the correct track and year. The Aksharantar arXiv page notes that the arXiv text is an extended manuscript. The Findings version cited here is the right peer-reviewed record.

Provenance of the corrected entries.
- luo2026lost comes verbatim from https://aclanthology.org/2026.acl-long.2039.bib, with only the key changed.
- patil2023gorilla comes from the NeurIPS proceedings BibTeX. The only change is braces around "API" in "{API}s" to keep the casing.
- schick2023toolformer comes from the NeurIPS proceedings BibTeX. The only change is the accent restored in "Dess{\`\i}" (the export has "Dessi").
- lin2024hammer comes from the ICLR proceedings BibTeX. The author field was edited by hand from OpenReview and the camera-ready PDF.
- yang2025qwen3 keeps the original title, journal and year. The author field is copied from the arXiv BibTeX export.
- falcon3 and sarvamm have no official BibTeX. Only the title field was edited by hand from each page.

## Claim Consistency

1. Line 123 describes MLCL. It says MLCL used BFCL queries translated into Chinese, Hindi and Igbo, an NT/PAR/FT by NO/PARA/SYNO grid, an 8-level error taxonomy, parameter-value language mismatch as the dominant failure, and partial recovery from inference-time mitigations. SUPPORTED. The ACL paper uses the BFCL v4 `multiple` subset, defines exactly these compositions and perturbations, and has an eight-category taxonomy in Figure 3. Categories 3 to 5 are the three language-mismatch types, which matches line 225. The abstract says the mitigations "cannot fully recover English-level performance".
2. Lines 96, 124 and 474 say that MLCL tests native script only, that Indic-native models were out of its scope, and that the PARA and SYNO prompts come from its App. A.8 to A.9. SUPPORTED. The evaluated models are the GPT-5 family, DeepSeek V3.2, Qwen3, Llama 3.1 and Granite 4. No Indic-specialised model is included, and there is no Romanized condition. Appendix A.8 is the paraphrase prompt and A.9 is the synonym prompt with one worked example.
3. Line 123 says "Chauhan et al. name the same phenomenon argument language mismatch and study SFT and RL post-training against it." UNSUPPORTED in part. The SFT and RL part is accurate (SFT, PPO and GRPO on Qwen2.5 7B to 32B). The "same phenomenon" part is not. Chauhan et al. define the correct value language as the user's language (lang(v) = lang(u) unless the API requires otherwise). Their own Figure 1 example counts English argument values for a Spanish request as the error, and their translated benchmark localises user-derived values into the target language. MLCL and this paper use the opposite convention, where English values are correct and user-language values are the failure. Suggested wording is "a related, inverse-convention failure they call argument language mismatch".
4. Lines 96 and 124 say Chauhan et al. "share the same input assumptions" and "use native script only". SUPPORTED with a caveat. Their languages are Spanish, French, Italian and Dutch, all Latin script. They use fully translated queries, train on Spanish only, and include no Romanized or Indic condition. The phrase "native script only" is technically true but adds little for Latin-script languages. Naming their languages would be more informative.
5. Line 230 says "Direct (non-reasoning) decoding for every model ... matches MLCL's setting." This sentence has no citation but makes a factual claim about MLCL. UNSUPPORTED by the MLCL text. MLCL says models are run with "officially supported tool-calling interfaces and recommended decoding configurations". It never says that reasoning or thinking was disabled, and its model list includes GPT-5 and Qwen3, whose recommended configurations use reasoning. Soften this to "approximates" or confirm it with the MLCL authors or their code.

## Methodology Note

Each entry was checked against its canonical record. These were arXiv abstract pages, ACL Anthology pages and .bib exports, NeurIPS, ICLR and PMLR proceedings pages and BibTeX exports, OpenReview search records, Crossref DOI records for the two statistics papers, and the live blog pages for the two model announcements. dblp and the OpenReview note API were behind bot challenges during this pass, so dblp was not used. OpenReview metadata came from its search endpoint. VERIFIED means the record was found and every field matches, apart from casing or a harmless "and others". MALFORMED means the work is real but at least one field is wrong, including a preprint citation for a work that has since been formally published. NOT FOUND would mean no record turned up after a title search, an author and keyword search, and an identifier lookup. That is a flag for manual review, not proof of fabrication. UNVERIFIABLE would cover genuine works that cannot be confirmed online, such as anonymized submissions, obscure books or paywalled records. No entry fell into either category in this pass. The corrected bibliography could not be test-compiled because no TeX installation is available locally. Brace balance and key order were checked by script.

## Addendum: two references added later on 2026-10-13

| # | Ref | Status | Confidence | Cited title | Issue(s) | Canonical source |
|---|---|---|---|---|---|---|
| 24 | kamath2025bfclhi | VERIFIED | High | Benchmarking Hindi LLMs: A New Suite of Datasets and a Comparative Analysis | None. The arXiv preprint 2508.19831 is superseded by the BHASHA 2025 workshop version, which is the one cited. | https://aclanthology.org/2025.bhasha-1.5/ |
| 25 | jain2026voiceagentbench | VERIFIED | High | VoiceAgentBench: Are Voice Assistants ready for agentic tasks? | None. arXiv only (v3, 13 Feb 2026). No Comments or Journal-ref, and dblp lists CoRR only. The year 2026 follows arXiv's own BibTeX export. | https://arxiv.org/abs/2510.07978 |

Claims checked against the full texts:
- **BFCL-Hi.** The paper's Table 1 marks it "Translated (not human evaluated)". It was translated with the GCP translation service, and function definitions stay in English. It has 2,251 items from BFCL V2. The paper reports no comparison with English and no error-type analysis. Our sentence "machine-translates BFCL queries into Hindi without human review" is SUPPORTED.
- **VoiceAgentBench.** It covers six Indic languages (Hindi, Bengali, Marathi, Tamil, Telugu, Malayalam). Queries were translated by Gemma3 27B (Llama-3.3 70B for Malayalam). Parameter filling is judged by GPT-4o-mini. The paper describes no native-speaker review of Indic translations, and models are told to give arguments in English only. It reports a clear English vs. Indic gap. Our sentence "LLM-translated queries and an LLM judge for argument values. It reports a large gap between English and Indic queries" is SUPPORTED.


## Link check of the compiled short paper (2026-10-13)

Every one of the 24 cited references now carries a link in the compiled PDF. Each link was opened by script and the page title, or the Crossref record for DOIs, was compared with the cited title. Note that 16 entries had no link before this check, and they were added here.

| Key | Paper | Link in PDF | Result |
|---|---|---|---|
| ahuja2023mega | MEGA | https://aclanthology.org/2023.emnlp-main.258/ | 200, title matches |
| chauhan2026api | When the API Speaks the Wrong Language | https://arxiv.org/abs/2608.11715 | 200, title matches |
| cohen1960kappa | A Coefficient of Agreement for Nominal Scales | https://doi.org/10.1177/001316446002000104 | 302 to SAGE (bots get 403), Crossref title matches |
| doddapaneni2023indicxtreme | Towards Leaving No Indic Language Behind | https://aclanthology.org/2023.acl-long.693/ | 200, title matches |
| falcon3 | Welcome to the Falcon 3 Family of Open Models! | https://huggingface.co/blog/falcon3 | 200, title matches |
| gala2023indictrans2 | IndicTrans2 | https://openreview.net/forum?id=vfT4YuzAYA | OpenReview blocks scripts. ID confirmed in the official TMLR paper list (jmlr.org/tmlr/papers). |
| gemma2025gemma3 | Gemma 3 Technical Report | https://arxiv.org/abs/2503.19786 | 200, title matches |
| grattafiori2024llama3 | The Llama 3 Herd of Models | https://arxiv.org/abs/2407.21783 | 200, title matches |
| husain2024romansetu | RomanSetu | https://aclanthology.org/2024.acl-long.833/ | 200, title matches |
| jain2026voiceagentbench | VoiceAgentBench | https://arxiv.org/abs/2510.07978 | 200, title matches |
| kamath2025bfclhi | Benchmarking Hindi LLMs (BFCL-Hi) | https://doi.org/10.18653/v1/2025.bhasha-1.5 | 200, Crossref title matches |
| kwon2023vllm | Efficient Memory Management ... PagedAttention | https://doi.org/10.1145/3600006.3613165 | 302 to ACM DL (bots get 403), Crossref title matches |
| li2023apibank | API-Bank | https://aclanthology.org/2023.emnlp-main.187/ | 200, title matches |
| lin2024hammer | Robust Function-Calling for On-Device Language Model via Function Masking | https://proceedings.iclr.cc/paper_files/paper/2025/file/d45e0bfb5a39477d56b55c0824200008-Paper-Conference.pdf | 200 PDF, abstract page title matches |
| luo2026lost | Lost in Execution (MLCL) | https://doi.org/10.18653/v1/2026.acl-long.2039 | 200, Crossref title matches |
| madhani2023aksharantar | Aksharantar | https://aclanthology.org/2023.findings-emnlp.4/ | 200, title matches |
| mcnemar1947note | Note on the Sampling Error ... | https://doi.org/10.1007/BF02295996 | 200, Crossref title matches |
| patil2025bfcl | The Berkeley Function Calling Leaderboard (BFCL) | https://proceedings.mlr.press/v267/patil25a.html | 200, title matches |
| patil2023gorilla | Gorilla | https://doi.org/10.52202/079017-4020 | 200, Crossref title matches |
| qin2024toolllm | ToolLLM | https://proceedings.iclr.cc/paper_files/paper/2024/hash/28e50ee5b72e90b50e7196fde8ea260e-Abstract-Conference.html | 200, title matches |
| sarvamm | Sarvam-M | https://www.sarvam.ai/blogs/sarvam-m | 200, page heading matches the cited title |
| schick2023toolformer | Toolformer | https://doi.org/10.52202/075280-2997 | 200, Crossref title matches |
| singh2024indicgenbench | IndicGenBench | https://aclanthology.org/2024.acl-long.595/ | 200, title matches |
| yang2025qwen3 | Qwen3 Technical Report | https://arxiv.org/abs/2505.09388 | 200, title matches |

## Update: Falcon3 citation (2026-10-13)

There is still no Falcon3 paper. The official model cards on huggingface.co/tiiuae say "Technical Report: Coming soon....".
- **Old entry:** the blog's page heading, "Welcome to the Falcon 3 Family of Open Models!", credited to "Technology Innovation Institute".
- **New entry:** the citation the model cards recommend. Title "The Falcon 3 Family of Open Models", author "Falcon-LLM Team", December 2024, url https://huggingface.co/blog/falcon3.
- **Sarvam-M:** its model card gives no citation block and links to the same blog, so that entry is unchanged.
- **Formatting:** both entries moved their link from `howpublished` into `url`. The title is now the clickable link, which removes the broken "https: //" line in the reference list.

## Full metadata re-check of the final bibliography (2026-10-13)

Every cited entry was compared with its official record: ACL Anthology `.bib`, the arXiv API or abstract page, Crossref for DOIs, the PMLR and ICLR proceedings metadata, and the TMLR paper list. The check covered the full author list in order, the year and the link. All 24 match.

Fixes made in this pass:
- **Full author lists:** eight entries that listed only the first author plus "et al." now list everyone. The ACL papers (MEGA, IndicXTREME, RomanSetu, API-Bank, Aksharantar, IndicGenBench) use the official ACL Anthology BibTeX. IndicTrans2 follows the TMLR list (14 authors) and ToolLLM the ICLR 2024 proceedings (19 authors).
- **VoiceAgentBench year:** 2026 -> 2025, the year of the first arXiv version (2510.07978).

Checked and left as they are:
- **Hammer:** 12 authors, with two different people named Jun Wang. This matches arXiv 2410.04587. The ICLR page metadata merges them into one.
- **Gemma 3:** the corporate author "Gemma Team", as Google credits it.
- **Llama 3:** "Grattafiori et al.". The paper has 561 authors.
- **Falcon3 and Sarvam-M:** official release posts. No papers exist.
