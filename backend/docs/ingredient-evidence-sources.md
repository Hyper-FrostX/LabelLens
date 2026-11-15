# LabelLens ingredient evidence sources

**Review date:** 2026-11-15  
**Scope:** source access and claim-level support for the ingredient and additive
catalog reviewed in [ingredient-knowledge-audit.md](./ingredient-knowledge-audit.md).
This document records research access, not a toxicological assessment or legal
opinion.

## Method

1. Reviewed the existing 27 normalized ingredient records, 31 legacy additive
   detector records, and 9 allergen alias groups in the repository.
2. Used official regulatory and public-health sources where available. A
   source URL or a database listing is not, on its own, verification of the
   record's identity, aliases, function, health claim, permitted category, or
   limit.
3. Marked only the narrowly supported claim as verified. Kept the whole record
   `PROVISIONAL` where other catalog properties remain unchecked.
4. Did not infer Indian permission from Codex, U.S., or EU material, or infer
   product exposure from a label-name match.
5. If a regulator's source index was available but the linked document text
   could not be inspected, recorded the index metadata and treated the
   substantive regulatory claim as unverified.

## Sources inspected

| Organization / title | URL | Publication / revision | Accessed | Jurisdiction and supported claim | Limitation |
|---|---|---|---|---|---|
| U.S. FDA, *Food Allergies* | <https://www.fda.gov/food/food-labeling-nutrition/food-allergies> (redirects to the current FDA page) | FDA page lists allergen guidance announced 2025-01-06 and a 2026 public meeting; no single page revision date shown | 2026-11-15 | U.S. major allergen categories: milk, eggs, fish, crustacean shellfish, tree nuts, peanuts, wheat, soybeans, and sesame; explains allergy hazards and labeling/cross-contact controls | Does not verify every LabelLens synonym, Indian labeling law, an ingredient association, or presence in a particular product. |
| U.S. FDA, *Brominated Vegetable Oil (BVO)* | <https://www.fda.gov/food/food-additives-petitions/brominated-vegetable-oil-bvo> | FDA final rule issued 2024-07-03; effective 2024-08-02; compliance date is one year after the effective date | 2026-11-15 | U.S. former beverage stabilizer use and FDA revocation of the U.S. authorization | No Indian or global legal status is established. The page discusses animal studies and regulatory grounds; it does not determine exposure or risk from a particular product. |
| IARC, reporting IARC and FAO/WHO JECFA, *Aspartame hazard and risk assessment results released* | <https://www.iarc.who.int/news-events/aspartame-hazard-and-risk-assessment-results-released/> | 2023-07-14 | 2026-11-15 | IARC Group 2B with limited evidence for carcinogenicity in humans; JECFA reaffirmed an ADI of 40 mg/kg body weight | Hazard identification and risk assessment are distinct. This source does not establish a product's aspartame amount, an individual's intake, or product-specific risk. |
| WHO/FAO JECFA, *Ninety-sixth meeting — Joint FAO/WHO Expert Committee on Food Additives* | <https://www.who.int/publications/m/item/ninety-sixth-meeting-joint-fao-who-expert-committee-on-food-additives-(jecfa)> | Meeting 2023-06-27 to 2023-07-06; page dated 2023-07-14 | 2026-11-15 | Confirms the meeting and links its summary/conclusions and the aspartame joint findings | The linked PDF was not text-inspected here; claim-level aspartame text above is supported by the IARC/WHO/FAO joint announcement, not by an independent parse of the JECFA PDF. |

## FSSAI source access and findings

The official [FSSAI food safety regulations portal](https://www.fssai.gov.in/cms/food-safety-and-standards-regulations.php)
is a JavaScript application shell. Its current application bundle links to:

- The *Food Safety and Standards (Food Products Standards and Food Additives)
  Regulations, 2011*, at
  <https://www.fssai.gov.in/docs/food-law/regulations/Food_Additives_Regulations.pdf>.
- The official chapter-wise compendium at
  <https://www.fssai.gov.in/food-law/regulations/compendium/food-products-standards>,
  including Chapter 3, “Substances added to food,” and Appendices A, B, and C.
- The official [Food Products Standards and Food Additives amendments index](https://www.fssai.gov.in/food-law/regulations/amendments/food-products-standards),
  whose current listing includes amendment no. 84 dated 2025-07-10. The
  listing also links the 2016 additive-harmonization notification.
- The official [Labelling and Display amendments index](https://www.fssai.gov.in/food-law/regulations/amendments/labelling-display),
  whose current listing includes amendments dated through 2026-11-06.

The FSSAI compendium page states that the compendium consolidates amendments
for reference, is not itself a legal document, and that original notifications
prevail. A subsequent source review made searchable text available for the
specific regulation, compendium chapters, and notification below. These are
narrow source findings, not a complete review of all amendments, categories,
or effective dates.

### Readable FSSAI provisions

- In the original 2011 regulation, the Maida standard (PDF p. 71; Gazette
  p. 357) lists “Potassium bromate (Max) 20 p.p.m.” as a bakery
  flour-treatment agent. Regulation 3.1.17 (PDF p. 148; Gazette p. 434) lists
  potassium bromate and/or potassium iodate at 50 ppm for bread, and
  potassium bromate at 20 ppm for flour for bakery. These are provisions in
  the original text; they do not establish current status after later
  amendments. A separate entry appears in Appendix A, “Use of Food Additives
  in Food Products,” Table 1, “List of food additives for use in bread and
  biscuits,” C. Improver, serial 7 (PDF p. 164; Gazette p. 450): “Potassium
  bromate and/or Potassium iodate — 50 ppm max (On flour mass basis)” in the
  Bread column. It is not the Regulation 3.1.17 provision.
- The current [Chapter 3: Substances Added to Food compendium](https://www.fssai.gov.in/docs/food-law/regulations/compendium/food-products-standards/Chapter%203_Substances%20added%20to%20food(1).pdf)
  (Version 4, dated 2025-08-01) gives identity and purity specifications for
  titanium dioxide (INS 171). The [2016 additive-harmonization Gazette
  notification](https://www.fssai.gov.in/docs/food-law/regulations/amendments/food-products-standards/Gazette_Notification_Additive_Harmonization_16_09_2016.pdf)
  also lists INS 171 at GMP for double-fortified salt. These narrow statements
  do not establish a general permission, other food-category uses, or the
  current effect of all subsequent amendments.
- The current [Chapter 2.2: Fats, Oils and Fat Emulsions
  compendium](https://www.fssai.gov.in/docs/food-law/regulations/compendium/food-products-standards/Chapter%202_2_Fats_oils%20and%20fat%20emulsions.pdf)
  (Version 5, dated 2025-08-01), Regulation 2.2.3(1) (PDF p. 35), sets a
  5%-by-weight ceiling for oil, with maximum limits of 3% from 2021-01-01 and
  2% from 2022-01-01. It carries amendment marker 72, which the official
  [amendment-reference document](https://www.fssai.gov.in/docs/food-law/regulations/compendium/food-products-standards/Amendment%20number%20reference.pdf)
  maps to notification F. No. 1-116/Scientific
  Committee/Notif./2010-FSSAI, dated 2020-12-29. This does not establish that
  every partially hydrogenated oil is prohibited or determine the trans-fat
  content of any product.

The PDF page numbers above refer to the downloaded documents; Gazette page
numbers are included where visible. PDF text was extracted from the fetched
bytes using `pypdf`, without OCR. The separate 2015 trans-fat notification
copy was image-only, so its substantive text was not inspected.

### High-priority current-status findings

**Potassium bromate (INS 924a).** FSSAI's *Direction under Section 16(5) of
the Food Safety and Standards Act, 2006 dated 12th Feb. 2018 regarding
prohibition of use of potassium bromate in any food article* is an official
direction dated 2018-02-12 (PDF pp. 1-2; not a Gazette notification). The
title identifies a prohibition in any food article. The direction is scanned;
no separate notification number or effective-date clause was readable. The
original 2011 regulation still contains the specific flour/bread provisions
listed above. No official FSSAI withdrawal/rescission instrument for the
direction or express Gazette amendment deleting the old entries was located
in the materials reviewed. This does not establish that no such instrument
exists. The evidence establishes the existence and stated scope of the FSSAI
prohibition direction, but not a formal textual repeal of the older entries
or a complete amendment/revocation history. Keep the additive
`REVIEW_REQUIRED`; do not restore the unsupported health summary or make
claims beyond the direction's stated scope.

**Brominated vegetable oil (BVO, INS 443).** The original 2011 regulation's
general additive list (PDF p. 224; Gazette p. 510) identifies BVO and gives
the functions “Emulsifier, stabilizer”; that list does not itself specify a
permitted food category. The official *Food Products Standards and Food
Additives Compendium*, Appendix A, Version 3 (2025-08-01), is the current
food-category table reviewed; it contains no INS 443 category-use entry in
the material inspected. That absence does not prove a ban. No affirmative
current category permission or express FSSAI prohibition/deletion was found
in the primary texts reviewed. Current Indian category status remains
unresolved; keep `REVIEW_REQUIRED`.

**Titanium dioxide (INS 171).** The *Food Safety and Standards (Food Products
Standards and Food Additives) Seventh Amendment Regulations, 2016*, F. No.
11/09/Reg/Harmoniztn/2014, dated 2016-09-05 and published in the Gazette on
2016-09-08 (No. 342; 4344 GI/2016), has a conditional GMP table on PDF
pp. 332-333: listed additives “may be used in all food categories (except
those categories listed in the ‘Annex to GMP’ list),” and includes INS 171.
The Annex (PDF pp. 333-335) is headed “Food Categories or Individual Food
Items where GMP Table shall not apply” and enumerates the excluded categories
and food items. This qualifies the scope of the table; exclusion from that
table is not itself a prohibition in those categories.
The same amendment's Table 12 (PDF p. 300), category 12.1.1 (salt), says
“Only the following additives permitted in double fortified salt” and lists
“Titanium dioxide 171 GMP.” The current FSSAI Appendix A, Version 3
(2025-08-01), PDF p. 274, repeats that express double-fortified-salt entry;
Chapter 3, Version 4 (2025-08-01), PDF p. 31, provides identity/purity
specifications, not a food-category authorization. No explicit later Gazette
clause resolving the relationship between the 2016 broad conditional GMP
table and the 2025 compendium's express category entry was found. Confirm the
double-fortified-salt entry only; do not infer a general ban or permission
for other categories. Keep `REVIEW_REQUIRED`.

**Indian allergen declarations.** The *Food Safety and Standards (Labelling
and Display) Regulations, 2020*, notification F. No.
1-94/FSSAI/SP(Labelling)/2014 (Pt-2), dated 2020-11-17 (5602 GI/2020),
Regulation 5(14) (original Gazette PDF pp. 36-37), requires separate “Contains
... (Name of allergy causing ingredients)” declaration for the listed
allergens. FSSAI's *Labelling and Display Regulations, Version VIII*
(2025-09-09), Regulation 5(14), PDF p. 18, lists:

1. cereals containing gluten (including wheat, rye, barley, oats, spelt,
   hybrids and their products; name the cereal);
2. crustaceans and their products;
3. milk and milk products;
4. eggs and egg products;
5. fish and fish products;
6. peanuts, tree nuts and their products;
7. soybeans and their products; and
8. sulphite at 10 mg/kg or more.

The *Food Safety and Standards (Labelling and Display) First Amendment
Regulations, 2022*, Gazette No. 442 (6074 GI/2022), published 2022-09-09,
amends Regulation 5(14): its gluten-related exceptions appear on amendment
PDF p. 2 (Gazette p. 245), and the substituted exception for oils and
distilled alcoholic beverages appears on PDF p. 4 (Gazette p. 247). The
*Food Safety and Standards (Labelling and Display) First Amendment
Regulations, 2026*, F. No. STD/SP-08/A1.2022/N-01, dated 2026-03-24
(Gazette identifier 2147 GI/2026), provides in clause 1(2) for commencement
on 2027-07-01. Its complete operative clause 2 amends Regulations 5(3), 8(1),
10, Schedule I and Schedule II, not Regulation 5(14) (PDF/Gazette pp. 5-7).
The *Food Safety and Standards (Labelling and Display) Second Amendment
Regulations, 2026*, F. No. SS-T017/1/2023-Standard-FSSAI, dated 2026-11-06
(Gazette identifier 8567 GI/2026), provides in clause 1(2) for commencement
on 2028-07-01. Clause 2 amends Schedule I by inserting a milk and milk
products logo provision, not Regulation 5(14) (PDF/Gazette pp. 3-4). These
conclusions derive from the complete operative clauses, not absence from a
compendium; neither amendment changes the allergen-declaration sub-regulation.
The Version VIII compendium says cross-contamination presence may be declared
separately as “May Contains” (p. 19), exempts raw agricultural commodities
from allergen labelling (p. 19), and includes point-of-sale/food-service
allergen information requirements at Regulations 8(4)(b) (p. 22) and 9(2)(a)
(p. 23), with exceptions in 9(3). Treat the compendium as a consolidated
reference, not the underlying legal instrument.

These rules do not make the nine LabelLens alias groups fully verified: the
FSSAI list includes sulphites but not sesame, while the LabelLens groups
include sesame and no sulphite group; FSSAI combines peanuts/tree nuts and
names crustaceans rather than all shellfish. LabelLens matching is not a
determination of regulatory labelling compliance. Keep all nine groups
`REVIEW_REQUIRED`.

The official amendment-reference document lists additive amendment references
through F. No. STD/FA/38/FSSAI(Part-1), dated 2024-10-21. The 2016
harmonization amendment is relevant to INS 171; the 2018 Section 16(5)
direction is relevant to potassium bromate; and the 2022 amendment is relevant
to allergen exceptions. No official withdrawal/rescission instrument for the
2018 direction was located in the reviewed materials, but this is not proof
that none exists. The 2026 amendment notifications were reviewed directly,
and neither amends Regulation 5(14). No specific later Gazette text resolving
BVO category use or the current scope/effect of the 2016 titanium-dioxide GMP
provision was identified. The precise current effect of those provisions
remains unresolved.

The linked indexes are useful primary-source navigation, but are not evidence
for any individual conclusion. Do not treat presence in a general additive
listing, a category-specific historical notice, or a Codex entry as proof of
current permission in another Indian food category.

## Other sources attempted

| Organization / source | URL | Access result on 2026-11-15 | Disposition |
|---|---|---|---|
| Codex Alimentarius, General Standard for Food Additives (GSFA) | <https://www.fao.org/gsfaonline/additives/index.html?lang=en> | Previously returned HTTP 403; the current Codex GSFA path redirected to `codex.fao.org` and returned “Page not found.” The Codex home page itself was reachable. | No additive/category/limit claim verified. A generic Codex URL is not a specific citation. |
| U.S. eCFR, legacy ingredient sections cited by the seed records (21 CFR §§ 182.3013, 184.1033, 182.3640, 184.1733) | <https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-184/section-184.1033> and corresponding sections | Previously redirected to an access challenge; substantive text was not inspected in this review. | Legacy source references remain unverified and are not used to establish safety, use limits, or Indian permissions. |
| EFSA Journal / Wiley article, DOI 10.2903/j.efsa.2021.6585 | <https://www.efsa.europa.eu/en/efsajournal/pub/6585> | Redirected to Wiley and returned HTTP 403. | No EFSA conclusion is newly verified here. |
| WHO JECFA general group page | <https://www.who.int/groups/joint-fao-who-expert-committee-on-food-additives> | Returned HTTP 404; the specific 96th-meeting page above was reachable. | The inaccessible general page supports no claim. |
| PubMed | <https://pubmed.ncbi.nlm.nih.gov/> | Home page reachable; no targeted literature query was used to verify a catalog claim. | Not evidence for an individual ingredient in this review. |

## Catalog disposition

No evidence-supported expansion or status promotion was made from these
sources. The current catalog remains:

- 27 ingredient records: 2 `PROVISIONAL`, 6 `REVIEW_REQUIRED`, and 19
  `UNVERIFIED`;
- 31 additive records: 1 `VERIFIED` (BVO, U.S.-specific regulatory facts
  only), 1 `PROVISIONAL` (aspartame assessment claim only), and 29
  `REVIEW_REQUIRED`;
- 9 allergen alias groups: all `REVIEW_REQUIRED`.

The seed now requires an explicit evidence-review marker in addition to a
source URL before a legacy health claim is emitted as verified. A URL alone
does not establish that its contents support the attached claim.

## Remaining work

The Phase 5.1.1 audit, implementation review, and requested validation are
complete. Remaining regulatory questions are explicitly retained as
`REVIEW_REQUIRED` rather than inferred from incomplete sources: the current
effect of the 2018 potassium-bromate direction against the unrepealed 2011
text, BVO category status, and the current scope/effect of the 2016
titanium-dioxide GMP provision. Broader claim-by-claim review of the remaining
27 ingredient records, 31 additive records, and 9 allergen alias groups is
still warranted. No record should be promoted based only on an index,
omission from a compendium, or a historical category-specific notice.
