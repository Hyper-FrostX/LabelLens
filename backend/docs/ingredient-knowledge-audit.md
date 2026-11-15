# LabelLens ingredient knowledge audit

**Review date:** 2026-11-15  
**Scope:** the 27 normalized ingredient records, the 9 allergen alias groups,
their evidence/regulatory references, and all 31 entries in the legacy
`CURATED_ADDITIVES` detector. This is a source review, not a toxicological
assessment or a determination of product safety.

## Executive result

- **27 normalized ingredient records:** 2 `PROVISIONAL`, 6 `REVIEW_REQUIRED`,
  and 19 `UNVERIFIED`. No record is treated as fully `VERIFIED` because the
  reviewed evidence does not verify every stored identity, alias, function,
  identifier, and jurisdictional statement together.
- The peanut-allergy evidence is supported by the FDA source below, and the
  aspartame Group 2B / JECFA ADI statement is supported by the IARC/WHO/FAO
  source below. Both remain `PROVISIONAL` as complete catalog records because
  not every alias, identifier, or associated property was checked.
- **31 legacy additive entries:** BVO has one `VERIFIED`, U.S.-specific
  regulatory statement; aspartame has one `PROVISIONAL` record with a
  verified assessment statement; the other 29 are `REVIEW_REQUIRED`.
- **9 allergen alias groups:** all remain `REVIEW_REQUIRED` as complete alias
  sets. FSSAI Regulation 5(14) requires declaration of its listed allergens,
  including sulphites at 10 mg/kg or more; LabelLens has no sulphite group
  and includes sesame, which is not on that FSSAI list. The FSSAI list also
  combines peanuts/tree nuts and names crustaceans rather than all shellfish,
  so it does not verify the LabelLens alias sets. FDA's U.S. allergen list is
  separate and does not establish Indian requirements.
- No new Indian-market ingredient records were added. Readable FSSAI text
  includes a 2018 Section 16(5) direction titled as a potassium-bromate
  prohibition in any food article, but the original 2011 text still contains
  use provisions; no official withdrawal/rescission of the direction or formal
  repeal of those entries was located in the materials reviewed. A 2011 BVO
  listing identifies its name/function but not a permitted category. Titanium
  dioxide has an express double-fortified-salt entry and an earlier broad,
  conditional GMP provision whose Annex excludes listed food categories; its
  current relationship to the category-specific entry is unresolved.
  Current compendium trans-fat limits and allergen declaration rules are
  documented below. The Codex GSFA route was unavailable, and EFSA/eCFR
  sources attempted were blocked or redirected to access challenges.

## Sources consulted

| Official title / organization | URL | Publication/revision | Accessed | What it supports / limitation |
|---|---|---|---|---|
| *Food Allergies* — U.S. Food and Drug Administration | <https://www.fda.gov/food/food-labeling-nutrition/food-allergies> (redirected to FDA's current Food Allergies page) | The page identifies the FASTER Act's sesame effective date (2023-01-01) and lists FDA allergen guidance announced 2025-01-06; no single page revision date shown | 2026-11-15 | Supports the U.S. major-allergen categories and allergy-specific hazard context. It does not verify all LabelLens synonyms or establish that a product contains an allergen. |
| *Brominated Vegetable Oil (BVO)* — U.S. Food and Drug Administration | <https://www.fda.gov/food/food-additives-petitions/brominated-vegetable-oil-bvo> | FDA page states its final rule was issued 2024-07-03 and became effective 2024-08-02; content metadata says 2024-07-02 | 2026-11-15 | Supports former U.S. use as a beverage flavor stabilizer (up to 15 ppm under the former authorization) and the U.S. revocation only. No status in India, the EU, or other jurisdictions is asserted. |
| *Aspartame hazard and risk assessment results released* — International Agency for Research on Cancer (IARC), reporting IARC and FAO/WHO JECFA findings | <https://www.iarc.who.int/news-events/aspartame-hazard-and-risk-assessment-results-released/> | 2023-07-14 | 2026-11-15 | Supports IARC Group 2B with limited evidence and JECFA reaffirmation of an ADI of 40 mg/kg body weight. This does not determine product exposure or individual risk. |
| FSSAI *Food Safety and Standards (Food Products Standards and Food Additives) Regulations, 2011* and current regulations portal | <https://www.fssai.gov.in/cms/food-safety-and-standards-regulations.php> and <https://www.fssai.gov.in/docs/food-law/regulations/Food_Additives_Regulations.pdf> | Regulation notified 2011-08-01; Maida standard PDF p. 71 (Gazette p. 357); Regulation 3.1.17 PDF p. 148 (Gazette p. 434); general additive list PDF p. 224 (Gazette p. 510) | 2026-11-15 | The original text lists potassium bromate (max) 20 ppm for bakery flour treatment and the bread/flour provisions in Regulation 3.1.17. Its general additive list identifies BVO (INS 443) as “Emulsifier, stabilizer”; that listing is not a category permission. |
| FSSAI *Food Safety and Standards (Food Products Standards and Food Additives) Regulations, 2011*, Appendix A, “Use of Food Additives in Food Products,” Table 1, “List of food additives for use in bread and biscuits,” C. Improver, serial 7 | <https://www.fssai.gov.in/docs/food-law/regulations/Food_Additives_Regulations.pdf> | Notified 2011-08-01; PDF p. 164 (Gazette p. 450) | 2026-11-15 | Lists potassium bromate and/or potassium iodate at 50 ppm max on flour mass basis in the Bread column. This is separate from Regulation 3.1.17 and does not resolve current status after later instruments. |
| FSSAI *Direction under Section 16(5) of the Food Safety and Standards Act, 2006 dated 12th Feb. 2018 regarding prohibition of use of potassium bromate in any food article* | <https://www.fssai.gov.in/docs/whatsnew/advisories-orders/5a93c346df548Direction_Prohibition_Potassium_Bromate_12_02_20181_1.pdf> | 2018-02-12; PDF pp. 1-2; scanned direction, not a Gazette notification | 2026-11-15 | The official direction title states a prohibition in any food article. No separate effective-date clause was readable; no formal Gazette deletion of the older 2011 entries was located, so the amendment/repeal relationship remains qualified. |
| FSSAI *Chapter 3: Substances Added to Food*, Version 4 | <https://www.fssai.gov.in/docs/food-law/regulations/compendium/food-products-standards/Chapter%203_Substances%20added%20to%20food(1).pdf> | 2025-08-01; PDF p. 31 | 2026-11-15 | Gives titanium dioxide (INS 171) identity/purity specifications, not a food-category authorization. |
| FSSAI *Food Safety and Standards (Food Products Standards and Food Additives) Seventh Amendment Regulations, 2016* | <https://www.fssai.gov.in/docs/food-law/regulations/amendments/food-products-standards/Gazette_Notification_Additive_Harmonization_16_09_2016.pdf> | F. No. 11/09/Reg/Harmoniztn/2014, dated 2016-09-05; Gazette 2016-09-08, No. 342 (4344 GI/2016); Table 12 PDF p. 300; conditional GMP table PDF pp. 332-333; “Annex to GMP” PDF pp. 333-335 | 2026-11-15 | Table 12, category 12.1.1, says only listed additives are permitted in double-fortified salt and lists INS 171 at GMP. The later table says listed GMP additives may be used in all food categories except those listed in the “Annex to GMP,” headed “Food Categories or Individual Food Items where GMP Table shall not apply.” Those exceptions limit the scope of the table and are not, by themselves, prohibitions in the excluded categories. The current effect/relationship of these provisions is not resolved by the compendium alone. |
| FSSAI *Food Safety and Standards (Food Products Standards and Food Additives) Compendium*, Appendix A: Food Category System, Version 3 | <https://www.fssai.gov.in/docs/food-law/regulations/compendium/food-products-standards/Appendix%20A(4).pdf> | 2025-08-01; PDF p. 274; category 12.1.1 | 2026-11-15 | Explicitly lists INS 171 at GMP for double-fortified salt. The compendium is a consolidated reference, not the underlying legal instrument; no broader current permission or ban is inferred. Appendix A contained no INS 443 category-use entry in the reviewed material; absence is not treated as a ban. |
| FSSAI *Chapter 2.2: Fats, Oils and Fat Emulsions*, Version 5 and amendment-reference document | <https://www.fssai.gov.in/docs/food-law/regulations/compendium/food-products-standards/Chapter%202_2_Fats_oils%20and%20fat%20emulsions.pdf> and <https://www.fssai.gov.in/docs/food-law/regulations/compendium/food-products-standards/Amendment%20number%20reference.pdf> | Regulation 2.2.3(1), PDF p. 35; 2025-08-01; amendment marker 72 maps to notification dated 2020-12-29 | 2026-11-15 | The compendium sets a 5%-by-weight ceiling for oil, with maximum limits of 3% from 2021-01-01 and 2% from 2022-01-01. This does not establish that every partially hydrogenated oil is prohibited or a product's trans-fat content. |
| FSSAI *Food Products Standards and Food Additives* amendment index | <https://www.fssai.gov.in/food-law/regulations/amendments/food-products-standards> | Current index lists amendments through no. 84 (2025-07-10) | 2026-11-15 | The index links the 2016 additive-harmonization notification and later amendments; listing metadata alone is not evidence of a particular rule. |
| FSSAI *Food Safety and Standards (Labelling and Display) Regulations, 2020* and Version VIII compendium | <https://www.fssai.gov.in/docs/food-law/regulations/5fd87c6a0f6adGazette_Notification_Labelling_Display_14_12_2020.pdf> and <https://www.fssai.gov.in/docs/food-law/regulations/Comp_Labelling%20Display_Version%20VIII_09_09_2025.pdf> | F. No. 1-94/FSSAI/SP(Labelling)/2014 (Pt-2), dated 2020-11-17 (5602 GI/2020); Regulation 5(14), original Gazette pp. 36-37; Version VIII dated 2025-09-09, PDF p. 18 | 2026-11-15 | Requires separate “Contains” declaration for gluten cereals, crustaceans, milk, eggs, fish, peanuts/tree nuts, soybeans, and sulphite at 10 mg/kg or more. The exact rule includes exceptions; it does not verify all LabelLens aliases or sesame as an Indian listed allergen. |
| FSSAI *Food Safety and Standards (Labelling and Display) First Amendment Regulations, 2022* | <https://www.fssai.gov.in/docs/food-law/regulations/amendments/labelling-display/Gazette_Notification_FSS_Label_12_09_2022.pdf> | Gazette No. 442 (6074 GI/2022), published 2022-09-09; Regulation 5(14), amendment PDF p. 2 (Gazette p. 245) and p. 4 (Gazette p. 247) | 2026-11-15 | Adds specified gluten-related exceptions and an exception for oils and distilled alcoholic beverages derived from the listed ingredients. |
| FSSAI *Food Safety and Standards (Labelling and Display) First Amendment Regulations, 2026* | <https://www.fssai.gov.in/docs/food-law/regulations/amendments/labelling-display/Notification%20dt%2024_03_2026_NRC.pdf> | F. No. STD/SP-08/A1.2022/N-01; dated 2026-03-24; Gazette identifier 2147 GI/2026; clauses 1(2)-2, PDF/Gazette pp. 5-7; effective 2027-07-01 | 2026-11-15 | Complete operative clauses amend Regulations 5(3), 8(1), 10, Schedule I and Schedule II, not Regulation 5(14). This establishes the scope of this amendment only; it does not change the allergen-declaration sub-regulation. |
| FSSAI *Food Safety and Standards (Labelling and Display) Second Amendment Regulations, 2026* | <https://www.fssai.gov.in/docs/food-law/regulations/amendments/labelling-display/FSS(Labelling%20and%20Display)%20-%20Milk%20logo.pdf> | F. No. SS-T017/1/2023-Standard-FSSAI; dated 2026-11-06; Gazette identifier 8567 GI/2026; clause 2 and inserted Schedule I paragraph (3), PDF/Gazette pp. 3-4; effective 2028-07-01 | 2026-11-15 | Amends Schedule I to insert the milk and milk products logo requirement, not Regulation 5(14). This establishes the scope of this amendment only; it does not change the allergen-declaration sub-regulation. |
| FSSAI *Labelling and Display* amendment index | <https://www.fssai.gov.in/food-law/regulations/amendments/labelling-display> | Current index lists amendments through 2026-11-06 | 2026-11-15 | Index metadata only for later amendments; not used alone to claim a change to Regulation 5(14). |
| Codex Alimentarius *General Standard for Food Additives (GSFA) Online Database* | <https://www.fao.org/gsfaonline/additives/index.html?lang=en> and <https://codex.fao.org/codex-texts/dbs/gsfa/en/> | Current GSFA route unavailable | 2026-11-15 | Earlier route returned HTTP 403; the current route redirected to Codex's “Page not found.” The generic link in prior seed records is not evidence for an additive, category, or limit. |
| EFSA Journal articles at Wiley (including DOI pages for 10.2903/j.efsa.2021.6585 and 10.2903/j.efsa.2011.2392) | <https://www.efsa.europa.eu/en/efsajournal/pub/6585> and <https://www.efsa.europa.eu/en/efsajournal/pub/2392> | Article dates vary; content not accessed | 2026-11-15 | Requests redirected to Wiley pages that returned HTTP 403. The legacy EFSA summaries citing these materials remain unverified in this review. |
| WHO/FAO JECFA, *Ninety-sixth meeting* | <https://www.who.int/publications/m/item/ninety-sixth-meeting-joint-fao-who-expert-committee-on-food-additives-(jecfa)> | Meeting 2023-06-27 to 2023-07-06; page dated 2023-07-14 | 2026-11-15 | The official meeting page and linked aspartame finding were reachable. The aspartame finding is supported by the IARC/WHO/FAO announcement; the linked JECFA PDF was not independently text-inspected. |
| U.S. eCFR cited sections (21 CFR §§ 182.3013, 184.1033, 182.3640, 184.1733) | <https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-184/section-184.1033> and corresponding sections | Current codification; source text not accessed | 2026-11-15 | Access was redirected to an eCFR/Federal Register access challenge. These references remain marked unverified; no permission or limit is claimed from them. |

### Phase 5.1.1 source-access update

The earlier note that an expected FSSAI compendium URL returned 404 referred to
an outdated guessed path. A second review found the correct regulation PDF,
chapter-wise compendium, amendment index, and selected readable document text.
The FSSAI allergen declaration list is now documented. The current effect of
the 2018 potassium-bromate direction relative to the 2011 text, BVO category
status, and the broader effect of the 2016 titanium-dioxide GMP provision
remain unresolved. The Phase 5.1.1 review, implementation checks, and
validation are complete; these legal questions remain explicitly unverified
rather than being treated as blockers to this conservative audit disposition.

## Normalized ingredient records

Aliases and functions below are the existing stored values, not independent
verification. INS/E-number values are shown exactly as stored. “No
allergens/evidence” means none are recorded, not that none exist.

| Canonical record | Stored aliases / identifiers | Stored category and function | Status | Audit finding |
|---|---|---|---|---|
| Peanut | `peanut`, `peanuts`, `groundnut`, `groundnuts` | Other food ingredients; “adds flavor, texture, and protein”; direct Peanuts association | `PROVISIONAL` | FDA supports peanut as a major allergen and allergy-specific risk. The source does not establish all groundnut aliases or the culinary function. Evidence remains verified for the allergy statement only. |
| Ascorbic acid | `ascorbic acid`, `vitamin c`, `e300`; E300 | Other food ingredients; antioxidant/nutrient | `REVIEW_REQUIRED` | The eCFR citation could not be accessed. No safety, broad permitted-use, or function claim is verified here. |
| Citric acid | `citric acid`, `e330`, `ins 330`; INS 330, E330 | Other food ingredients; acidity regulator, flavoring agent | `REVIEW_REQUIRED` | Legacy eCFR source was inaccessible; Codex source returned 403. Identity/function and regulatory claims need a specific source. |
| Potassium sorbate | `potassium sorbate`, `e202`, `sorbate`; INS 202, E202 | Preservatives; preservative | `REVIEW_REQUIRED` | Legacy eCFR citation inaccessible; Codex source returned 403. Do not infer use limits or safety from the E-number. |
| Sodium benzoate | `sodium benzoate`, `e211`, `benzoate of soda`; INS 211, E211 | Preservatives; preservative | `REVIEW_REQUIRED` | Legacy eCFR citation inaccessible; Codex source returned 403. The former benzene warning is not included as a verified claim. |
| Rice grits | `rice grits`, `rice grit` | Other food ingredients; cereal solids/texture | `UNVERIFIED` | No source reference or review evidence is stored; description and alias need source review. |
| Potato flakes | `potato flakes`, `dehydrated potato flakes` | Other food ingredients; bulk/texture | `UNVERIFIED` | No source reference or review evidence is stored. |
| Corn grits | `corn grits`, `maize grits` | Other food ingredients; cereal solids/texture | `UNVERIFIED` | No source reference or review evidence is stored. |
| Edible vegetable oil | `edible vegetable oil`; variants mentioning corn/soybean; `corn oil`, `soybean oil`, `soya oil` | Other food ingredients; cooking/frying oil | `UNVERIFIED` | The aliases combine an unspecified oil with specific oils; those must not be treated as equivalent without label context. No source or allergen association is stored. |
| Iodized salt | `iodized salt`, `iodised salt`, `salt iodized`, `salt iodised` | Other food ingredients; seasoning/iodine | `UNVERIFIED` | No source or review evidence is stored. |
| Sugar | `sugar`, `sucrose`, `cane sugar` | Other food ingredients; sweetener | `UNVERIFIED` | No source or review evidence is stored; alias coverage is not exhaustive. |
| Calcium carbonate | `calcium carbonate`, `ins 170(i)` | Other food ingredients; function explicitly unspecified | `UNVERIFIED` | INS variant and identity are not sourced in this record; do not infer a technical function. |
| Silicon dioxide | `silicon dioxide`, `silica`, `ins 551`; INS 551 | Other food ingredients; anti-caking | `UNVERIFIED` | No supporting source is stored; identity, code, and function need verification. |
| Chilli powder | `chilli powder`, `chili powder`, `chilli pwd`, `chili pwd` | Other food ingredients; spice/flavor | `UNVERIFIED` | No source or review evidence is stored. |
| Black pepper powder | `black pepper powder`, `black pepper pwd`, `ground black pepper`, `black pepper` | Other food ingredients; spice/flavor | `UNVERIFIED` | No source or review evidence is stored. |
| Garlic and onion powder | spelling and ampersand variants | Other food ingredients; seasoning blend | `UNVERIFIED` | No source or review evidence is stored; blend composition is not established by the name. |
| Acetic acid | `acetic acid`, `ins 260`; INS 260 | Other food ingredients; acidity regulator/flavoring | `UNVERIFIED` | No source or review evidence is stored. |
| Malic acid | `malic acid`, `ins 296`; INS 296 | Other food ingredients; acidity regulator/flavoring | `UNVERIFIED` | No source or review evidence is stored. |
| Natural and nature-identical flavouring substances | British/American spelling and punctuation variants | Other food ingredients; flavoring substances | `UNVERIFIED` | Label phrase does not identify individual compounds; no properties or source are stored. |
| Tamarind powder | `tamarind powder`, `tamarind pwd` | Other food ingredients; tart flavor | `UNVERIFIED` | No source or review evidence is stored. |
| Disodium guanylate | `disodium guanylate`, `ins 627`; INS 627 | Other food ingredients; flavor enhancer | `UNVERIFIED` | No source or review evidence is stored for identity, code, or function. |
| Disodium inosinate | `disodium inosinate`, `ins 631`; INS 631 | Other food ingredients; flavor enhancer | `UNVERIFIED` | No source or review evidence is stored for identity, code, or function. |
| Spice extract | `spice extract`, `spice extracts` | Other food ingredients; generic flavoring | `UNVERIFIED` | Label phrase is not a unique identity; source and composition are absent. |
| Paprika extract | `paprika extract`, `ins 160c(i)` | Other food ingredients; coloring | `UNVERIFIED` | The INS variant and function are not supported by a stored source. |
| Monosodium glutamate | `MSG`, `sodium glutamate`; INS 621, E621 | Flavour enhancers; flavour enhancer | `REVIEW_REQUIRED` | The code/function/aliases were added with a generic, inaccessible Codex URL. No health claim is made; identity and regulatory details still need a specific accessible source. |
| Aspartame | `aspartame sweetener`; INS 951, E951 | Sweeteners; sweetener | `PROVISIONAL` | A verified IARC/JECFA assessment statement is stored. Alias and INS/E-number mapping and any authorization/labeling claims require separate evidence. |
| Sucralose | no aliases; INS 955, E955 | Sweeteners; sweetener | `REVIEW_REQUIRED` | The code/function was added with an inaccessible generic Codex URL; no permissions, limits, or health claim is verified. |

### Allergen alias groups and association

The database has one ingredient association: Peanut → Peanuts, now
`PROVISIONAL` at association level; the FDA source supports the allergy hazard,
but alias coverage and association provenance need more complete review. All
other names below are aliases in the profile-matching catalog, not established
ingredient-to-allergen associations. Each complete alias group is
`REVIEW_REQUIRED`.

| Allergen group | Stored aliases | Status / caveat |
|---|---|---|
| Gluten | gluten, wheat, barley, rye, malt | `REVIEW_REQUIRED`; FDA's major allergen list identifies wheat, not this broader group as an equivalent. |
| Dairy | dairy, milk, casein, whey, lactose, butter, ghee, cream, cheese(s), yogurt/yoghurt | `REVIEW_REQUIRED`; individual milk-derived ingredient relationships need evidence and context. |
| Soy | soy, soya, soybean, tofu, tempeh, soy/soya lecithin | `REVIEW_REQUIRED`; source/protein and processing distinctions are not captured. |
| Tree nuts | tree nuts and almond, walnut, cashew, pistachio, hazelnut, pecan, Brazil nut, macadamia variants | `REVIEW_REQUIRED`; FDA identifies tree nuts but not every alias and regional classification here. |
| Peanuts | peanut(s), groundnut(s) | `REVIEW_REQUIRED` alias group; peanut category itself is supported by FDA. |
| Eggs | egg(s), albumin, ovalbumin | `REVIEW_REQUIRED`; aliases not individually sourced. |
| Fish | fish, salmon, tuna, cod, anchovy, sardine, mackerel | `REVIEW_REQUIRED`; alias set is not exhaustive or individually sourced. |
| Shellfish | shellfish, shrimp/prawn, crab, lobster, crayfish, mollusc/mollusk, oyster, clam, mussel, scallop variants | `REVIEW_REQUIRED`; FDA's cited list says crustacean shellfish; molluscs need separate scope/evidence. |
| Sesame | sesame, sesame seed(s), tahini | `REVIEW_REQUIRED` alias group; FDA confirms sesame as a major allergen in the U.S.; alias equivalence is not fully sourced. |

## Legacy additive warning audit

Before this review, the detector returned a high/moderate/low scale, categorical
recommendations, and broad regulatory statements. Those ratings conflated
hazard identification, jurisdictional regulation, and unknown product
exposure. Runtime records now withhold prior summaries/recommendations unless
the cited statement could be narrowly supported. Previously supplied source
labels are recorded below as **unaccessed legacy citations**, not as evidence.

| Legacy entry (catalog ID) | Previous claim (shortened) | Previously cited source label (not independently accessed) | New status and disposition |
|---|---|---|---|
| Potassium bromate (`potassium-bromate`) | IARC 2B / animal tumors; broad country bans; avoid | IARC Monographs 73; JECFA | `REVIEW_REQUIRED`; unsupported health wording and broad multi-country claims and the recommendation are withdrawn. FSSAI's 2018 Section 16(5) direction is titled as prohibiting use in any food article; the relationship to the still-present 2011 text and any formal repeal remain unresolved. |
| Titanium dioxide (`titanium-dioxide`) | EFSA nanoparticle/genotoxicity conclusion; EU ban; avoid | EFSA FAF Panel 2021 | `REVIEW_REQUIRED`; FSSAI's 2016 conditional GMP table and 2025 double-fortified-salt entry are documented, but current scope outside that express entry and particle-form/health claims remain unresolved. |
| Brominated vegetable oil (`brominated-vegetable-oil`) | Bioaccumulation/cardiac/thyroid effects; U.S./EU bans | FDA final rule 2024; EFSA | `VERIFIED` only for FDA-reported former beverage-stabilizer use and U.S. revocation. No EU or Indian status, product concentration, or product risk is asserted. |
| Partially hydrogenated oil (`partially-hydrogenated-oil`) | Broad cardiovascular harms; U.S. prohibition/EU limit; avoid | WHO REPLACE; FDA | `REVIEW_REQUIRED`; the current FSSAI compendium supports specific trans-fat limits, but does not establish a blanket prohibition on partially hydrogenated oil; legacy recommendation withdrawn. |
| Propylparaben (`propylparaben`) | Endocrine/reproductive effects; EU prohibition/U.S. restriction | EFSA opinion; Regulation (EC) 1333/2008 | `REVIEW_REQUIRED`; source does not identify the exact claim, dose, or applicable food use. |
| Potassium iodate (`potassium-iodate`) | Thyroid/renal effects; international and EU/Canada restrictions | JECFA; Codex CXS 152 | `REVIEW_REQUIRED`; exposure conditions and jurisdiction claims were not verified. |
| Sodium nitrite (`sodium-nitrite`) | Curing benefit vs. high-heat nitrosamines; moderation | IARC Monograph 114; EFSA 2017 | `REVIEW_REQUIRED`; conditions, amounts, and current limits were not verified. |
| Sodium nitrate (`sodium-nitrate`) | Conversion to nitrite/nitrosamine concern; moderation | EFSA sodium nitrate re-evaluation | `REVIEW_REQUIRED`; dose, conditions, and authorization statements were not verified. |
| Red 40 / Allura Red AC (`red-40`) | Southampton-study child behavior and allergy claims; EU warning | Lancet 2007; EFSA/EC Regulation | `REVIEW_REQUIRED`; population, effect size, warning-label rule, and jurisdiction were not checked. |
| Yellow 5 / Tartrazine (`yellow-5`) | Aspirin-sensitive reactions/asthma and child behavior | EFSA NDA Panel; FDA CFR | `REVIEW_REQUIRED`; the stated susceptibility and causal language were not verified. |
| Yellow 6 / Sunset Yellow FCF (`yellow-6`) | Southampton-study behavior and sensitivity; ADI/warning | EFSA re-evaluation | `REVIEW_REQUIRED`; current opinion, population, ADI, and warning rule were not accessed. |
| BHA (`bha`) | NTP carcinogen listing/rodent tumors; use limits | NTP 15th Report; EFSA ANS 2011 | `REVIEW_REQUIRED`; hazard classification, exposure relevance, and current limits need direct review. |
| BHT (`bht`) | Animal liver changes, “safe trace exposure,” ADI | EFSA; JECFA | `REVIEW_REQUIRED`; dose response and present ADI were not checked. “Synthetic nature draws caution” removed as unsupported reasoning. |
| Aspartame (`aspartame`) | IARC Group 2B; JECFA/FDA ADI; PKU warning; “safe” recommendation | WHO/IARC/JECFA 2023; FDA | `PROVISIONAL`; retain only the verified IARC Group 2B / limited-evidence and JECFA 40 mg/kg ADI statement, with hazard/risk and exposure caveats. Remove FDA and global approval claims and product-level advice. |
| Acesulfame potassium (`acesulfame-potassium`) | Breakdown-product/environmental concerns; EU/US ADIs | EFSA re-evaluation; FDA CFR | `REVIEW_REQUIRED`; claims and jurisdictional numbers not checked. |
| Sucralose (`sucralose`) | Heating breakdown products, microbiome concern, broad ADI/approval | BfR 2019; FDA | `REVIEW_REQUIRED`; temperature, product-formation, and microbiome claims require direct evidence. |
| Sodium benzoate (`sodium-benzoate`) | Benzene formation with vitamin C/heat/light; universal limit; avoid combination | FDA beverage guidance; EFSA ANS 2016 | `REVIEW_REQUIRED`; no claim is shown until mechanism, conditions, current jurisdiction limits, and source are verified. |
| High-fructose corn syrup (`high-fructose-corn-syrup`) | Fatty liver, insulin resistance, visceral adiposity | AHA advisory; NIH studies | `REVIEW_REQUIRED`; broad causal wording and product-specific advice removed. |
| Carrageenan (`carrageenan`) | Poligeenan animal effects; GI reports; infant-formula restriction | JECFA; EFSA re-evaluation | `REVIEW_REQUIRED`; food-grade/degraded distinction and jurisdiction scope need source verification. |
| Caramel color IV (`caramel-color-iv`) | 4-MEI / IARC 2B, limits, California warning | IARC Monograph 101; EFSA | `REVIEW_REQUIRED`; contaminant levels, exposure, and legal requirements were not checked. |
| Citric acid (`citric-acid`) | “Completely safe,” global unrestricted use | FDA GRAS; JECFA | `REVIEW_REQUIRED`; safety certainty and quantum-satis claim removed; legacy eCFR/Codex sources inaccessible. |
| Ascorbic acid (`ascorbic-acid`) | No toxic risk; beneficial nutrient | National Academies; EFSA | `REVIEW_REQUIRED`; identity/function statement is not a basis for a universal health conclusion; cited assessments not accessed. |
| Soy lecithin (`soy-lecithin`) | “Completely safe/non-toxic”; global unrestricted use | FDA GRAS; EFSA | `REVIEW_REQUIRED`; source/allergen distinctions and broad safety claim need verification. |
| Xanthan gum (`xanthan-gum`) | Safe/non-absorbed; laxative at high intake | EFSA 2017 | `REVIEW_REQUIRED`; the specific opinion and intake conditions were not accessed. |
| Guar gum (`guar-gum`) | Prebiotic benefit and broad safe status | EFSA 2017; FDA | `REVIEW_REQUIRED`; health-benefit and authorization wording needs direct support. |
| Pectin (`pectin`) | Cardiovascular/cholesterol benefit; unconditional global status | JECFA; EFSA 2017 | `REVIEW_REQUIRED`; benefit claims and regulatory wording are not established by the stored source label. |
| Calcium propionate (`calcium-propionate`) | Fully metabolized; safe; prevents harmful bacteria | FDA CFR; EFSA 2014 | `REVIEW_REQUIRED`; mechanistic, safety, and regulatory assertions need source verification. |
| Monosodium glutamate (`monosodium-glutamate`) | No chronic toxicity/symptom complex; safe; sodium-reduction benefit | FDA; EFSA glutamate re-evaluation | `REVIEW_REQUIRED`; cited reviews not accessed; no population-wide safety conclusion or sodium benefit is asserted. |
| Propylene glycol (`propylene-glycol`) | Non-toxic at use levels; global/US/EU status | FDA CFR; ATSDR | `REVIEW_REQUIRED`; dose, population, route, and jurisdiction claims were not reviewed. |
| Sodium erythorbate (`sodium-erythorbate`) | Nitrosamine inhibition; safe; global approval | FDA CFR; EFSA 2016 | `REVIEW_REQUIRED`; specific use conditions and evidence were not accessed. |
| Potassium sorbate (`potassium-sorbate`) | “Clean” metabolism, well-tolerated, global approval/ADI | EFSA 2015; FDA GRAS | `REVIEW_REQUIRED`; source pages inaccessible; safety and ADI assertions withdrawn. |

## Implementation and remaining research

- The four statuses are stored on `Ingredient`, `IngredientAllergen`, and
  `AllergenAlias`; evidence/regulatory sources retain verified flags and review
  dates. The detector includes status in each result and only exposes a health
  concern from a verified evidence row. Unknown matches remain unknown.
- Seed updates are idempotent and update catalog-owned verification metadata;
  they do not delete user or product data. Existing IDs and relationships are
  preserved. Migration `a8f3c12e9b71` adds the status and evidence review-date
  fields; it has SQLite batch-alter upgrade/downgrade coverage.
- Legacy API response keys remain, but the old high/moderate/safe values are
  replaced by `review_required`/`informational` and neutral copy. `counts`
  retains `high`, `moderate`, and `low` keys (zero while no such assessment is
  verified) and adds `review_required` and `informational`.
- No new India-focused records or full-record jurisdictional status promotions
  were made: the inspected FSSAI clauses do not jointly establish identity,
  function, aliases, category permissions, or later amendments for any full
  catalog record.
- Remaining work: resolve the effect of relevant FSSAI additive amendments
  and directions, especially for potassium bromate, BVO and titanium dioxide;
  query Codex GSFA through an accessible
  official route; retrieve relevant EFSA/JECFA opinions; validate each E/INS
  number and permitted food category by jurisdiction; verify the remaining 29
  legacy summaries; and date/source each of the 9 allergen alias groups.
  Product concentration and consumption remain unknown even after those
  references are populated.
