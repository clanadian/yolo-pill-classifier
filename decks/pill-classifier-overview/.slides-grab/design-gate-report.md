# slides-grab Design Gate Report

Verdict: proceed
Generated: 2026-07-28T08:05:46.303Z
Slide mode: presentation
Resolution: 1080p

## Pass A: System Contract / Constraint Integrity

# Pass A: System Contract / Constraint Integrity

VERDICT: PASS
Confidence: High
Evidence: decks/pill-classifier-overview/gate-preview/slide-01.png, decks/pill-classifier-overview/gate-preview/slide-02.png, decks/pill-classifier-overview/gate-preview/slide-03.png, decks/pill-classifier-overview/gate-preview/slide-04.png, decks/pill-classifier-overview/gate-preview/slide-05.png, decks/pill-classifier-overview/gate-preview/slide-06.png, decks/pill-classifier-overview/gate-preview/slide-07.png, decks/pill-classifier-overview/gate-preview/slide-08.png, decks/pill-classifier-overview/gate-preview/slide-09.png, decks/pill-classifier-overview/gate-preview/slide-10.png, decks/pill-classifier-overview/gate-preview/slide-11.png, decks/pill-classifier-overview/gate-preview/slide-12.png, decks/pill-classifier-overview/gate-preview/slide-13.png, decks/pill-classifier-overview/gate-preview/slide-14.png, decks/pill-classifier-overview/gate-preview/slide-15.png, decks/pill-classifier-overview/gate-preview/slide-16.png, decks/pill-classifier-overview/gate-preview/slide-17.png, decks/pill-classifier-overview/gate-preview/slide-18.png
Slide fingerprints: slide-01.html: 33abd49c542923d36ebb0a72b27cb4971124a3344da87037e3fe14349236142d, slide-02.html: 69c806145250196ebafebba3ace0d691bad782e9d8b33c8d07b0f69e9953f434, slide-03.html: 5ce95eedfbc8ef5a685dd5c90657def2d0a4f8a9d47570c45ab9c4c83b7f78af, slide-04.html: 04614b13b8c2035c2809843e6d3f50f06d910043625f16273d23874cf31b3656, slide-05.html: 05d7e98e8eb9f9be474fea6c5a02a6c36f955a256dadc172fdc57c2071ea0e23, slide-06.html: a3481e10a0e05520a928f10a9c12b2468b488c88e9888ddf2bcddc58a3b598fa, slide-07.html: 745a03883904699916861fdf242441cffbbde55e3ddffc9af3e8ff7c7d93da3b, slide-08.html: 7a3c5fa6c934e41fe7d3fd081c53c72a2a509a2f94875a5b393401ae11adc0a6, slide-09.html: 11fab698ca32b6f676ebaeaad2422f323b3720a017c7216fa495b7867e27c385, slide-10.html: ec5cde70c059a64fb891228288cea45098d67ade6dbe10f443899a69af7cd37d, slide-11.html: ad42e469c180c5598ffe9b78b5f2a34874c39b42a15839ce373f4cf716a9580e, slide-12.html: 7422ca1ce70c9421058e9d5c36ba84b7d59c520f6ee8565fe2df89cba88815d2, slide-13.html: a1b5df1fdce36d0630cb8cdb50864fbbd4d47b4ec87622b1a9d456c9323b2385, slide-14.html: 076cb6273f229238ed8ba2e3f21fddba35dcd880a5ff5fea750e29cac3d3c342, slide-15.html: df0963cb23cdacaebf99c645f493a7942dd951e3e365712997a689e3e1d810cf, slide-16.html: bf7f7f8ff843e7cd108d0ec28a65eb194deb06c5a17231760ecd272fd58e551e, slide-17.html: 247bd84864611256924c34492c47792e9227eff16d1b96f74ff98e2785c8095e, slide-18.html: cdce477beca95e8fdfb8f165fd8a1894ede66ba3672565eea213548d09ce88eb
Unresolved Critical: 0
Blocking findings: None

## Checks
- [x] System consistency: PASS — Grepped all 18 files for hex colors; every light slide (01-07, 09-11, 13-15, 17) uses only #FFFFFF background, #111111 primary text, #444444 secondary text, #DDDDDD dividers, #E8000D accent, plus the shared `.pageno`/`.section-label`/monospace-label utility color #8A8A8A. Dark slides (08, 12, 16, 18) uniformly use #111111 (near-black bg equivalent) + #FFFFFF text + #E8000D accent + #AAAAAA/#777777/#333333 as documented dark-surface tiers. Exactly two background systems deck-wide (light/dark), one accent (#E8000D), one typeface (Pretendard) — confirmed via direct visual inspection of all 18 rendered PNGs. No per-slide drift in header rule, left spine bar, or page-number placement found.
- [x] Color discipline: PASS — Full hex audit (`grep -oE '#[0-9A-Fa-f]{3,8}'` across all slide-*.html) shows only palette colors plus previously-accepted documented exceptions: #8A8A8A (shared muted label/pageno/monospace-tag color, used consistently on 15+ slides — not a one-off), #0a0d13 (image-cell letterbight background, real screenshot content), #bbbbbb (screenshot caption label, real content), #fff (shorthand for #FFFFFF, cosmetically inconsistent capitalization only, not a new color). No unsanctioned new hex values introduced since round 1. Slide-04's round-1 `#F5F5F5` code-chip background is gone — verified by grep (no F5F5F5 anywhere in slide-04.html or any other file) and by direct visual read of slide-04.png (code now renders as plain black monospace text with no background chip, matching slide-03's bare `.chip .cls` monospace treatment).
- [x] AI slop tropes: PASS — Grepped all files for `linear-gradient|radial-gradient|box-shadow|border-radius|emoji|<svg`: zero matches across all 18 slides. Visual inspection confirms no rounded corners anywhere (pipeline boxes on slide-03/05, GOOD/CAUTION badges on slide-06/14, stat dividers, and image frames on slide-13-15 all render as sharp rectangles), no drop shadows, no inline-SVG iconography, no gradients, no emoji, and no generic "feature grid with icon-in-circle" pattern. Fonts are Korean Pretendard + monospace for code/class-name tokens only — no secondary generic sans fallback visible in render. Faux-chrome browser/OS window decoration is absent; the "Pill Detector" mock UI on slides 13-15 is treated as real screenshot content (already accepted in round 1) and uses plain rectangular frames, not fake traffic-light buttons.
- [x] Content discipline: PASS — Every number on every slide traces to real project facts: 820장/23%/259장 (slide-09, auto-labeling failure), purple_pill 1개 excluded / 6개 remaining classes (slide-10), 2.59 → 0.15~1.3 color-error and 403장 (slide-11), class counts 149/188/169/186/181/187 for capsule/green_caplet/mint_circle/pink_caplet/white_caplet/yellow_caplet plus 919/161 train/val split and 1,080장 total, 20 negative samples (slide-04) — all internally consistent and cross-referenced correctly between slide-04's per-class table and slide-03/13's six named classes. No invented/filler stats (no fabricated "95% accuracy" or similar unsupported metrics) found anywhere in the deck.

## Findings
| Slide | Finding | Severity | Fix | Status |
|-------|---------|----------|-----|--------|
| slide-04 | Round-1 finding (unique #F5F5F5 code-chip background) confirmed resolved — code now renders as bare monospace text matching slide-03's treatment | Note | None needed | tracked |
| slide-01 | Round-1 finding (missing page number) confirmed resolved — "01" now present in `.pageno` span, positioned and styled identically to slide-02/03/04 | Note | None needed | tracked |
| slide-08, slide-12, slide-16, slide-18 | Dark-surface tier colors #AAAAAA/#777777/#333333 remain in use as documented dark-mode equivalents of the light palette's #8A8A8A/#444444/#DDDDDD | Minor | Already tracked from round 1, no action required | tracked |
| slide-13, slide-14, slide-15 | Image-cell letterbox #0a0d13 and caption label #bbbbbb remain in use inside real Jetson demo screenshots | Minor | Already tracked from round 1, no action required | tracked |

## Pass B: Audience Impact / Expressive Readability

# Pass B: Audience Impact / Expressive Readability

VERDICT: PASS
Confidence: High
Evidence: decks/pill-classifier-overview/gate-preview/slide-01.png, decks/pill-classifier-overview/gate-preview/slide-02.png, decks/pill-classifier-overview/gate-preview/slide-03.png, decks/pill-classifier-overview/gate-preview/slide-04.png, decks/pill-classifier-overview/gate-preview/slide-05.png, decks/pill-classifier-overview/gate-preview/slide-06.png, decks/pill-classifier-overview/gate-preview/slide-07.png, decks/pill-classifier-overview/gate-preview/slide-08.png, decks/pill-classifier-overview/gate-preview/slide-09.png, decks/pill-classifier-overview/gate-preview/slide-10.png, decks/pill-classifier-overview/gate-preview/slide-11.png, decks/pill-classifier-overview/gate-preview/slide-12.png, decks/pill-classifier-overview/gate-preview/slide-13.png, decks/pill-classifier-overview/gate-preview/slide-14.png, decks/pill-classifier-overview/gate-preview/slide-15.png, decks/pill-classifier-overview/gate-preview/slide-16.png, decks/pill-classifier-overview/gate-preview/slide-17.png, decks/pill-classifier-overview/gate-preview/slide-18.png
Slide fingerprints: slide-01.html: 33abd49c542923d36ebb0a72b27cb4971124a3344da87037e3fe14349236142d, slide-02.html: 69c806145250196ebafebba3ace0d691bad782e9d8b33c8d07b0f69e9953f434, slide-03.html: 5ce95eedfbc8ef5a685dd5c90657def2d0a4f8a9d47570c45ab9c4c83b7f78af, slide-04.html: 04614b13b8c2035c2809843e6d3f50f06d910043625f16273d23874cf31b3656, slide-05.html: 05d7e98e8eb9f9be474fea6c5a02a6c36f955a256dadc172fdc57c2071ea0e23, slide-06.html: a3481e10a0e05520a928f10a9c12b2468b488c88e9888ddf2bcddc58a3b598fa, slide-07.html: 745a03883904699916861fdf242441cffbbde55e3ddffc9af3e8ff7c7d93da3b, slide-08.html: 7a3c5fa6c934e41fe7d3fd081c53c72a2a509a2f94875a5b393401ae11adc0a6, slide-09.html: 11fab698ca32b6f676ebaeaad2422f323b3720a017c7216fa495b7867e27c385, slide-10.html: ec5cde70c059a64fb891228288cea45098d67ade6dbe10f443899a69af7cd37d, slide-11.html: ad42e469c180c5598ffe9b78b5f2a34874c39b42a15839ce373f4cf716a9580e, slide-12.html: 7422ca1ce70c9421058e9d5c36ba84b7d59c520f6ee8565fe2df89cba88815d2, slide-13.html: a1b5df1fdce36d0630cb8cdb50864fbbd4d47b4ec87622b1a9d456c9323b2385, slide-14.html: 076cb6273f229238ed8ba2e3f21fddba35dcd880a5ff5fea750e29cac3d3c342, slide-15.html: df0963cb23cdacaebf99c645f493a7942dd951e3e365712997a689e3e1d810cf, slide-16.html: bf7f7f8ff843e7cd108d0ec28a65eb194deb06c5a17231760ecd272fd58e551e, slide-17.html: 247bd84864611256924c34492c47792e9227eff16d1b96f74ff98e2785c8095e, slide-18.html: cdce477beca95e8fdfb8f165fd8a1894ede66ba3672565eea213548d09ce88eb
Unresolved Critical: 0
Blocking findings: None

## Checks
- [x] Composition & hierarchy: PASS — Every slide still reads as a single-anchor poster. Section dividers (08/12/16) and closing (18) hold their deliberate near-black inversion cleanly; content slides (01–07, 09–11, 13–15, 17) keep one headline + one supporting structure (pipeline row, two-column diagnosis, stat block, or image grid) with no competing focal points.
- [x] Typography & legibility: PASS — Full-deck grep of `font-size` confirms nothing below 10pt remains (previous 7.5pt/8pt/9pt/9.5pt instances on slide-06 badge, slide-13 `.cap .cls`, slide-14 `.tag`/`.cap`, slide-15 `.cell .label` are all now 10pt). Visually, slide-06's GOOD/CAUTION badges, slide-13's class-name captions ("capsule", "green_caplet", etc.), slide-14's GOOD/CAUTION tags, and slide-15's dark header labels ("비타민D 2개 동시 감지", "복용량 안내 상세 화면") all sit comfortably in their containers with no overflow or awkward enlargement.
- [x] Korean/CJK word-break integrity: PASS — `word-break: keep-all;` is present in the `body` rule of all 18 slide HTML files (verified by grep), and no per-element override reintroduces `break-all`/`normal`. Visual re-check of the 8 previously-broken slides confirms clean word-boundary wraps: slide-03 headline now breaks "...탐지하고, Jetson Nano에서 바로 웹으로 / 확인한다" with "확인한다" intact on line 2; slide-07 headline reads "...동작하는 / "안내형" 서비스 구조를 검증" via the inserted `<br>`, both lines balanced; slide-17 item 01 wraps "...보장하지 / 않는다 — 실제 박스 좌표..." with "않는다" whole. Slides 05, 06, 09, 10, 11 show no mid-syllable splits in any headline, diagnosis label, or paragraph. The other 10 slides (01, 02, 04, 08, 12, 13, 14, 15, 16, 18) show no new overflow, clipping, or unexpected wrap side effects from the global CSS change — all text fits within its container with normal line breaks.
- [x] Review Litmus: PASS — Each slide grasps in 3-5 seconds: one dominant claim in the headline, one visual anchor (pipeline diagram, stat pair, screenshot grid, or limit box), no filler line that could be removed without loss.

## Findings
| Slide | Finding | Severity | Fix | Status |
|-------|---------|----------|-----|--------|
| slide-03 | Round-1 mid-word break ("...확"/"인한다") — re-verified fixed, "확인한다" now whole on second line | Note | word-break:keep-all applied globally | resolved |
| slide-07 | Round-1 ragged headline ("...검증" orphaned) — re-verified fixed via explicit `<br>` after "동작하는", two balanced lines | Note | `<br>` inserted | resolved |
| slide-06, slide-13, slide-14, slide-15 | Round-1 sub-10pt labels (badge 8pt, `.cls` 7.5pt, `.tag`/`.cap` 7.5–9pt, `.label` 9.5pt) — re-verified all now exactly 10pt and visually proportionate, no overflow | Note | font-size bumped to 10pt floor across deck | resolved |
| slide-15 | Round-1 screenshot artifacts (top gradient sliver, right-edge scrollbar track on both embedded images) — re-verified clean; source images re-cropped (filenames now suffixed `-crop.png`) | Note | images re-cropped | resolved |
## Template Fidelity Report

Status: not-applicable

## Slide Fingerprints

- slide-01.html: 33abd49c542923d36ebb0a72b27cb4971124a3344da87037e3fe14349236142d
- slide-02.html: 69c806145250196ebafebba3ace0d691bad782e9d8b33c8d07b0f69e9953f434
- slide-03.html: 5ce95eedfbc8ef5a685dd5c90657def2d0a4f8a9d47570c45ab9c4c83b7f78af
- slide-04.html: 04614b13b8c2035c2809843e6d3f50f06d910043625f16273d23874cf31b3656
- slide-05.html: 05d7e98e8eb9f9be474fea6c5a02a6c36f955a256dadc172fdc57c2071ea0e23
- slide-06.html: a3481e10a0e05520a928f10a9c12b2468b488c88e9888ddf2bcddc58a3b598fa
- slide-07.html: 745a03883904699916861fdf242441cffbbde55e3ddffc9af3e8ff7c7d93da3b
- slide-08.html: 7a3c5fa6c934e41fe7d3fd081c53c72a2a509a2f94875a5b393401ae11adc0a6
- slide-09.html: 11fab698ca32b6f676ebaeaad2422f323b3720a017c7216fa495b7867e27c385
- slide-10.html: ec5cde70c059a64fb891228288cea45098d67ade6dbe10f443899a69af7cd37d
- slide-11.html: ad42e469c180c5598ffe9b78b5f2a34874c39b42a15839ce373f4cf716a9580e
- slide-12.html: 7422ca1ce70c9421058e9d5c36ba84b7d59c520f6ee8565fe2df89cba88815d2
- slide-13.html: a1b5df1fdce36d0630cb8cdb50864fbbd4d47b4ec87622b1a9d456c9323b2385
- slide-14.html: 076cb6273f229238ed8ba2e3f21fddba35dcd880a5ff5fea750e29cac3d3c342
- slide-15.html: df0963cb23cdacaebf99c645f493a7942dd951e3e365712997a689e3e1d810cf
- slide-16.html: bf7f7f8ff843e7cd108d0ec28a65eb194deb06c5a17231760ecd272fd58e551e
- slide-17.html: 247bd84864611256924c34492c47792e9227eff16d1b96f74ff98e2785c8095e
- slide-18.html: cdce477beca95e8fdfb8f165fd8a1894ede66ba3672565eea213548d09ce88eb
