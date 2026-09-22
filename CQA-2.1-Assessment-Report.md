# CQA 2.1 Content Quality Assessment Report — Service Interconnect (Skupper)

**Scope**: Full repository — 25 assemblies + 63 modules (excluding troubleshooting)
**Content location**: `/home/paulwright/repos/sk/vale/sk-vale/` (assemblies/, modules/)
**Source location**: `/home/paulwright/repos/sk/vale/skupper-docs/input/`
**Date of review**: 2026-09-22

## Summary

| Tab | Parameters | Average Score | Rating |
|-----|-----------|---------------|--------|
| Pre-migration (P1-P19) | 19 | 3.11 | Mostly meets |
| Quality (Q1-Q25) | 25 | 3.40 | Mostly meets |
| Onboarding (O1-O10) | 10 | 1.60 | Does not meet |
| **Overall** | **54** | **2.96** | **Mostly meets** |

## Automated Check Results

| Check | Result | Details |
|-------|--------|---------|
| Vale | PASS | 0 errors, 0 warnings |
| Readability (FK grade) | PASS | Grade 8.66 (94.9% meeting ≤12) |
| Scannability | PASS | 0 sentences >30 words |
| Fluff patterns | PASS | 0 violations |
| Simple words | PASS | 0 complex words |
| Conscious language | PASS | 0 exclusionary terms |
| Content types | FAIL | 93 files lack naming prefixes (repo-wide) |
| Cross-references | FAIL | 2 broken xrefs (pipeline path issue) |
| Product names | FAIL | No attributes.adoc |
| Legal notices | FAIL | No LICENSE, no titles/ |
| TP disclaimers | FAIL | Missing snippet |

## Fixes Applied (Markdown Source)

| Fix Type | Count | Files |
|----------|-------|-------|
| Gerund → imperative headings | ~50 | All sections |
| Emoji admonitions → blockquote | 28 | kube-cli, kube-yaml, system-cli, system-yaml, overview |
| Self-referential text removed | 9 | service-exposure, site-linking, resources, custom-certs, console |
| "make sure" → "ensure" | 8 | site-linking, custom-certs, site-configuration |
| "set up" → "configure" | 1 | overview/connectivity |
| "This procedure describes" → direct | 2 | kube-cli/site-linking, system-cli/site-linking |
| Long sentences split (>30 words) | 11 | overview, kube-yaml, kube-cli, system-yaml |

## Pre-migration Tab (P1-P19) — Average: 3.11

| # | Parameter | Score | Evidence |
|---|-----------|-------|----------|
| P1 | Vale linting | 4 | 0 errors, 0 warnings across 93 files |
| P2 | Content type consistency | 4 | Every module declares exactly one content type (CONCEPT/PROCEDURE/REFERENCE) |
| P3 | File naming conventions | 1 | All 93 files lack standard prefixes (assembly_, con_, proc_, ref_). Pipeline/repo-wide issue |
| P4 | IDs use `_{context}` suffix | 1 | All IDs use bare slugs, none follow `_{context}` pattern. Pipeline-wide |
| P5 | Abstract present | 4 | All assemblies and modules include `[role="_abstract"]` with descriptive paragraph |
| P6 | ID format | 4 | All IDs use `[id="..."]` format. Zero legacy `[[...]]` |
| P7 | Xref resolution | 3 | 24/26 xrefs resolve. 2 broken: file-path xrefs to custom-certs.adoc |
| P8 | Assembly titles descriptive | 4 | All 25 titles are descriptive and unique with clear scope (K8s/local, CLI/YAML) |
| P9 | Module titles descriptive | 4 | All titles clearly describe content. Procedure titles state the action |
| P10 | Sentence case | 3 | Most titles follow sentence case. Minor: "Application Networks" capital N |
| P11 | Imperative mood | 3 | All module procedure titles use imperative. 13 assembly titles still use gerund (convention) |
| P12 | Ordered lists for procedures | 4 | All procedures use ordered lists. Non-sequential items use unordered |
| P13 | Consistent terminology | 4 | Commands match examples. No "make sure" or "set up" remaining |
| P14 | No contractions | 4 | 0 contractions across 93 files |
| P15 | Internal xrefs format | 3 | Most use `xref:id[text]`. 2 use relative file paths (pipeline artifact) |
| P16 | External links valid | 4 | 28 external links, all to known-good domains |
| P17 | Anchors/IDs present | 3 | All 93 files have `[id="..."]` anchors. Lack `_{context}` suffix |
| P18 | Product name attributes | 1 | 129 hardcoded "Skupper" mentions, 0 `{ProductName}`. No attributes.adoc |
| P19 | Product version attributes | 1 | No version attributes. `{{skupper_cli_version}}` appears as literal text |

## Quality Tab (Q1-Q25) — Average: 3.40

| # | Parameter | Score | Evidence |
|---|-----------|-------|----------|
| Q1 | Active voice | 4 | "Create a site", "Check the status", "Apply the token" throughout |
| Q2 | No self-referential text | 4 | 0 instances of "This section/topic/document" |
| Q3 | Second person | 4 | Consistent "you" throughout. No third-person instructions |
| Q4 | Present tense | 4 | Consistent present tense: "creates", "connects", "applies" |
| Q5 | Concise writing | 4 | Readability grade 8.66, 0 long sentences, 0 fluff |
| Q6 | Content addresses task | 4 | Procedures are task-oriented with clear goals |
| Q7 | Appropriate detail | 4 | Good balance of explanation and command-level detail. Prerequisites listed, output shown |
| Q8 | Acronyms expanded | 3 | CLI expanded. VPN, TLS, TCP, UUID, PVC, PKI used without expansion |
| Q9 | Navigation aids | 3 | 10 modules have .Additional resources. Many procedures lack cross-references |
| Q10 | Admonitions correct | 4 | 24 admonitions using proper `[NOTE]/====` format. Zero emoji pseudo-admonitions |
| Q11 | Abstract user-focused | 4 | All abstracts are action/goal-oriented. No self-referential text |
| Q12 | Atomic steps | 3 | Most steps single-action. A few bundle multiple continuation blocks |
| Q13 | Prerequisites listed | 3 | 25/35 procedures have .Prerequisites. 10 omit them |
| Q14 | .Procedure title | 4 | All 35 procedure modules have .Procedure block titles |
| Q15 | .Verification section | 1 | Only 1/35 procedures has formal .Verification. Many have inline "check status" steps |
| Q16 | .Additional resources | 2 | Only 7/35 procedures have .Additional resources. 28 lack them |
| Q17 | Conscious language | 4 | 0 exclusionary terms |
| Q18 | List punctuation | 3 | Mostly consistent. Some prerequisite lists mix period/no-period |
| Q19 | Tables well-structured | 3 | Header rows present. Some lack `[cols=]` for explicit widths |
| Q20 | Formal tone | 4 | No contractions, colloquialisms, or emoji |
| Q21 | Images have alt text | 3 | 9 images have alt text but it is filename-based, not descriptive |
| Q22 | Screenshots current | 3 | SVG architecture diagrams likely current. Console PNG may need updating |
| Q23 | Product name consistent | 3 | "Skupper" used consistently. Minor: "v2" vs "V2" inconsistency |
| Q24 | Links descriptive text | 4 | Zero "click here" or "read more". All links use descriptive text |
| Q25 | Related content linked | 3 | Some modules link related content. Many could benefit from more cross-linking |

## Onboarding Tab (O1-O10) — Average: 1.60

| # | Parameter | Score | Evidence |
|---|-----------|-------|----------|
| O1 | Legal notice | 1 | No LICENSE file at repo root |
| O2 | Copyright notice | 1 | No titles/ directory, no docinfo.xml |
| O3 | Product attributes file | 1 | No common/attributes.adoc |
| O4 | Tech preview snippet | 1 | No snip_technology-preview.adoc |
| O5 | Trademark attribution | 2 | "Skupper" used without trademark designation |
| O6 | Prerequisite knowledge | 4 | Prerequisites listed. Logical progression: overview → sites → linking → services |
| O7 | Terminology consistent | 3 | Consistent "site", "link", "connector", "listener". Minor: "v2" vs "V2" |
| O8 | Publishing (pantheon) | 1 | No pantheon.yml |
| O9 | Publishing (titles) | 1 | No titles/ directory |
| O10 | Publishing (LICENSE) | 1 | No LICENSE file |

## Score Comparison

| Date | Overall | Pre-migration | Quality | Onboarding |
|------|---------|---------------|---------|------------|
| 2026-09-22 (initial, troubleshooting only) | 2.89 | 3.05 | 2.96 | 2.40 |
| 2026-09-22 (round 1, troubleshooting only) | 3.13 | 3.32 | 3.28 | 2.40 |
| 2026-09-22 (round 2, troubleshooting only) | 3.28 | 3.37 | 3.56 | 2.40 |
| 2026-09-22 (full repo, post-fixes) | 2.96 | 3.11 | 3.40 | 1.60 |

## Remaining Gaps (Not Fixable in Markdown)

| Issue | Parameters | Scope | Notes |
|-------|-----------|-------|-------|
| File naming prefixes | P3 | 93 files | Needs pipeline convention change |
| IDs lack `_{context}` suffix | P4, P17 | 93 files | Needs pipeline and assembly changes |
| Product name/version attributes | P18, P19, O3 | Repo-wide | Needs `common/attributes.adoc` |
| Publishing infrastructure | O1, O2, O8-O10 | Repo-wide | Needs `titles/`, `pantheon.yml`, `LICENSE` |
| Tech preview snippet | O4 | Repo-wide | Needs `snip_technology-preview.adoc` |
| 2 broken xrefs | P7, P15 | 2 modules | Pipeline path refs to custom-certs.adoc |
| .Verification sections | Q15 | 34 procedures | Add formal `.Verification` blocks |
| .Additional resources | Q16, Q9, Q25 | 28 procedures | Add cross-references to related content |
| Image alt text | Q21 | 9 images | Replace filename-based with descriptive text |
| Acronym expansion | Q8 | Multiple | Expand VPN, TLS, TCP, UUID, PVC, PKI on first use |
