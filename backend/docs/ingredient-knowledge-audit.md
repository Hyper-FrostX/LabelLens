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
  sets. FDA material verifies the U.S. nine major allergen categories but
  does not verify all LabelLens aliases, Indian requirements, or cross-contact
  inference.
- No new Indian-market ingredient records were added. The FSSAI additive
  compendium could not be retrieved, Codex GSFA returned HTTP 403, and the
  EFSA/eCFR sources attempted were blocked or redirected to access challenges.

## Sources consulted

| Official title / organization | URL | Publication/revision | Accessed | What it supports / limitation |
|---|---|---|---|---|
| *Food Allergies* — U.S. Food and Drug Administration | <https://www.fda.gov/food/food-labeling-nutrition/food-allergies> (redirected to FDA's current Food Allergies page) | The page identifies the FASTER Act's sesame effective date (2023-01-01) and lists FDA allergen guidance announced 2025-01-06; no single page revision date shown | 2026-11-15 | Supports the U.S. major-allergen categories and allergy-specific hazard context. It does not verify all LabelLens synonyms or establish that a product contains an allergen. |
| *Brominated Vegetable Oil (BVO)* — U.S. Food and Drug Administration | <https://www.fda.gov/food/food-additives-petitions/brominated-vegetable-oil-bvo> | FDA page states its final rule was issued 2024-07-03 and became effective 2024-08-02; content metadata says 2024-07-02 | 2026-11-15 | Supports former U.S. use as a beverage flavor stabilizer (up to 15 ppm under the former authorization) and the U.S. revocation only. No status in India, the EU, or other jurisdictions is asserted. |
| *Aspartame hazard and risk assessment results released* — International Agency for Research on Cancer (IARC), reporting IARC and FAO/WHO JECFA findings | <https://www.iarc.who.int/news-events/aspartame-hazard-and-risk-assessment-results-released/> | 2023-07-14 | 2026-11-15 | Supports IARC Group 2B with limited evidence and JECFA reaffirmation of an ADI of 40 mg/kg body weight. This does not determine product exposure or individual risk. |
| *Food Safety and Standards Regulations* — Food Safety and Standards Authority of India (FSSAI) | <https://www.fssai.gov.in/cms/food-safety-and-standards-regulations.php> | Not available from returned page | 2026-11-15 | The URL returned a JavaScript application shell without regulation text or source documents; no ingredient claim was verified from it. |
| FSSAI *Compendium_Food_Additives_Regulations.pdf* (expected path) | <https://www.fssai.gov.in/upload/uploadfiles/files/Compendium_Food_Additives_Regulations.pdf> | Not retrieved | 2026-11-15 | Returned HTTP 404. No Indian use categories or limits were inferred. |
| Codex Alimentarius *General Standard for Food Additives (GSFA) Online Database* | <https://www.fao.org/gsfaonline/additives/index.html?lang=en> | Database revision not accessible | 2026-11-15 | Returned HTTP 403. The generic link in prior seed records remains unverified and is not evidence for a particular additive, category, or limit. |
| EFSA Journal articles at Wiley (including DOI pages for 10.2903/j.efsa.2021.6585 and 10.2903/j.efsa.2011.2392) | <https://www.efsa.europa.eu/en/efsajournal/pub/6585> and <https://www.efsa.europa.eu/en/efsajournal/pub/2392> | Article dates vary; content not accessed | 2026-11-15 | Requests redirected to Wiley pages that returned HTTP 403. The legacy EFSA summaries citing these materials remain unverified in this review. |
| U.S. eCFR cited sections (21 CFR §§ 182.3013, 184.1033, 182.3640, 184.1733) | <https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-184/section-184.1033> and corresponding sections | Current codification; source text not accessed | 2026-11-15 | Access was redirected to an eCFR/Federal Register access challenge. These references remain marked unverified; no permission or limit is claimed from them. |

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
| Potassium bromate (`potassium-bromate`) | IARC 2B / animal tumors; broad country bans; avoid | IARC Monographs 73; JECFA | `REVIEW_REQUIRED`; remove hazard, ban, and recommendation wording until source and jurisdiction checks are complete. |
| Titanium dioxide (`titanium-dioxide`) | EFSA nanoparticle/genotoxicity conclusion; EU ban; avoid | EFSA FAF Panel 2021 | `REVIEW_REQUIRED`; particle form, regulatory date, and jurisdiction were not verified. |
| Brominated vegetable oil (`brominated-vegetable-oil`) | Bioaccumulation/cardiac/thyroid effects; U.S./EU bans | FDA final rule 2024; EFSA | `VERIFIED` only for FDA-reported former beverage-stabilizer use and U.S. revocation. No EU or Indian status, product concentration, or product risk is asserted. |
| Partially hydrogenated oil (`partially-hydrogenated-oil`) | Broad cardiovascular harms; U.S. prohibition/EU limit; avoid | WHO REPLACE; FDA | `REVIEW_REQUIRED`; historical and jurisdiction-specific legal status needs current official sources; recommendation withdrawn. |
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
- No new India-focused records were added because identity, function, aliases,
  and regulatory status could not be jointly substantiated from accessible
  authoritative sources during this review.
- Remaining work: obtain authoritative FSSAI additive and labeling documents;
  query Codex GSFA through an accessible official route; retrieve relevant
  EFSA/JECFA opinions; validate each E/INS number and permitted food category
  by jurisdiction; verify the remaining 29 legacy summaries; and date/source
  each of the 9 allergen alias groups. Product concentration and consumption
  remain unknown even after those references are populated.
