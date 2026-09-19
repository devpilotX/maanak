# Known limits

What this system does not do, and what has not been proven. Read this before drawing
conclusions from anything else in the repository.

## Not implemented

| Feature | Status | Why it is absent rather than half-built |
| --- | --- | --- |
| **OCR accuracy benchmark** | Measured on two corpora, both small | On generated labels, `scripts/measure_ocr_accuracy.py` scores 72 of 80 fields, 90 per cent, detailed in the table below. On real packaging, `scripts/measure_ocr_real.py` scores 14 consumer photographs of Indian packs taken from Open Food Facts, using each product's declared quantity as ground truth: 6 of the 14 yielded at least one declaration, 10 declarations were located in total, and **net quantity was read from none of them**, against 12 that had a declared quantity to compare with. The quality gate refused 5 of the 14 outright. Neither corpus is a labelled benchmark and 14 photographs is far too few to publish a percentage from. The figure that matters is the other one: **no photograph produced a non-compliant finding before officer review**, which is the behaviour the design promises. |
| **Reading a declaration off a real pack** | Weak. Region isolation is the constraint, not contrast | Diagnosed on one photograph where the panel is plainly legible: a crop of a Tata Salt pouch, 1897 by 383, showing "NET QUANTITY: 1 kg" in large bold type. Whole-image reads fail. All seven profiles return either nothing or noise, and Tesseract 5.3.0 invoked directly returns empty text at psm 3. **Crop to the text and plain greyscale reads `NET QUANTITY:` exactly, at psm 6 and psm 7, with no preprocessing at all.** So the engine can read this print and the failure is that one pass over a whole curved pack asks it to segment graphics, Hindi, English and substrate texture at once. The value is a separate and harder problem: `1 kg` still misreads as `14`, `1%`, `ig` or `1K` even cropped to 277 by 145, because the tight `kg` pair in that condensed face defeats it. That suggested text-region detection would improve the reported state rather than the extraction rate. The row below records what happened when that was built and measured, which is not what this predicted. |
| **Contrast preprocessing for real packs** | Tried, measured, rejected | Local contrast equalisation with a 2x upscale was added as two escalating profiles and reverted. On the 14 photographs it changed the end-to-end result not at all: 10 declarations located, 6 photographs yielding any, net quantity read from **none**, identical to before. A first measurement suggested it recovered 8 of 24 declared quantity tokens, and that measurement was wrong: it counted the amount *or* the unit appearing anywhere in the text, so a stray `g` in a field of noise scored a hit. Asked strictly, the amount and unit adjacent as the extractor needs them, every profile scores 0 of 14 with preprocessing and without. It also made things worse in one direction, raising the Tata Salt crop from 0 words to 68 words of noise at 0.43 confidence. Recorded here so the next attempt does not repeat it. |
| **Load and capacity** | Measured on one host | `scripts/measure_load.py` ramps read concurrency and drains a queue of OCR jobs. On 8 CPUs: reads peak at about 111 requests per second at 4 threads, p50 35 ms and p95 56 ms, and beyond 4 threads throughput is flat while p50 latency climbs to 136 ms at 16. The worker completes 18 jobs a minute at 3.3 seconds each, bounded by `max_jobs = 2`, which `app/worker/main.py` sets deliberately because OCR is CPU-bound. These are a capacity baseline for one machine and one dataset, not a published benchmark, and they will move on different hardware. What is still missing is a sustained soak test and a figure for concurrent evidence upload from many districts at once. |
| **A general API rate limit** | Declared, not enforced | Found by measuring: 3,067 read requests across four sessions produced zero 429 responses. `API_PER_SESSION` is defined in `security/ratelimit.py` at 600 requests per 60 seconds and referenced nowhere else, so it protects nothing; `LISTING_FETCH_PER_USER` is the same, though that one belongs to the listing fetcher which is deliberately absent. Both are now annotated as unwired in the source. Switching `API_PER_SESSION` on as written would cap a session at 10 requests per second against a measured capacity of about 111, so it needs a number derived from measurement first. `docs/THREAT_MODEL.md` already states that rate limits protect specific endpoints and that there is no general protection, so the documentation was accurate and only the source was misleading. |
| **Automatic text-region detection** | Built, measured, not shipped | The row above predicted that isolating regions would improve the *state* rather than the extraction rate, by finding a declaration label whose value cannot be read. Measured over all 14 photographs, that prediction is wrong. A morphological region detector, gradient then a wide closing then contours filtered on aspect and area, was compared against the whole-image pass. Labels read: **10 either way**. The whole-image pass already finds every label the regions find, so the better state never materialises. Regions alone are worse, 6 labels against 10, because the detector loses text the single pass catches. The union of both reads net quantity from **1 of 14** where the whole-image pass reads 0, which is the first strict read of a declared quantity from a real photograph in this project. The knee is page segmentation rather than box count: capped at 14 boxes, psm 7 alone gains nothing, psm 6 and 7 together gain the quantity, and raising the cap to 60 adds only time. Cost is about twice the OCR time per image, which would take the worker from 18 jobs a minute to roughly 9. One extra quantity read out of 14, no better labels, for half the throughput measured in `measure_load.py` is not a trade worth making automatically, so it is recorded rather than merged. A future attempt should start from the knee: psm 6 on isolated phrase-shaped boxes is what works. |
| **E-commerce listing fetcher** | Not implemented | An outbound fetcher needs DNS pinning, redirect refusal, private-address blocking, byte limits, decompression limits and network isolation to be safe. Configuration for it exists in `app/config.py`, but no code fetches a URL, so there is nothing to exploit and nothing to claim. |
| **Offline field capture with sync** | Partial | The interface detects online and offline state and tells the officer. Local draft storage, an upload queue, conflict resolution and device-loss handling are not implemented. |
| **In-page camera** | Works, with one condition | A browser only grants a page access to the camera in a secure context. That covers `http://localhost` and any HTTPS deployment, but not a deployment served over plain HTTP, where the button hands off to the operating system camera app instead and says so. A capture encoded from the page carries no EXIF, so the quality report may mark it as possibly not a photograph, which is a correct reading of an image with no camera metadata. The filename records that it came from the camera. |
| **Food-label tool** | Not implemented | Ingredient, nutrition and allergen extraction is absent. The original prototype had an undocumented "health score", which was removed rather than kept: a score with no reviewed method behind it is worse than nothing. |
| **Digital signature** | Adapter only | The signer returns `none` or a clearly labelled `development` HMAC. There is no certificate and no signing service. Every place the value appears says so. |
| **MFA / SSO** | Architecture only | The `User` model carries `mfa_enabled`, `mfa_secret` and `external_subject`, and the session layer would accommodate either. No second factor is enforced and no OIDC flow exists. |
| **Password reset by email** | Partial | A single-use hashed token is issued and can be redeemed. There is no email delivery: an administrator issues the token and passes it on. `notification_backend` defaults to `console`. |
| **Malware scanning on upload** | Interface only | `Evidence.malware_scan_state` defaults to `not_scanned`. Files are validated as images from their own bytes, which is not the same as scanning them. |
| **Performance and load testing** | Not done | No response-time budget has been measured under load, no concurrency test beyond correctness, no storage-growth projection. |
| **Backup and restore drill** | Script only | `docs/BACKUP_RESTORE.md` documents the procedure and the integrity re-verification, but a full restore into a clean environment was not executed as part of this build. |

## Verified but narrowly

| Claim | What was actually tested | What was not |
| --- | --- | --- |
| OCR reads English and Hindi | Generated label images rendered with DejaVu and Noto Devanagari, read correctly through the full pipeline. `scripts/measure_ocr_accuracy.py` scores ten declarations with known correct values against the extraction output under eight conditions: as generated at 1700 by 1100, scaled to 1200 and to 900 wide, rotated 2 and 6 degrees, JPEG quality 55, blurred, and centred on a white backdrop. The result is 72 of 80 fields, 90 per cent, with every failure being the same one: the reader returns "lodised" for "Iodised" because capital I and lowercase l are the same shape in a sans-serif face. No profile or dictionary setting fixed it, so the ambiguity is now reported on the candidate rather than corrected, and `tests/test_imaging_quality.py` covers the detector in both directions | Real photographs of real packaging, curved surfaces, reflective film, worn print. **The 90 per cent figure is for generated labels under known degradation and must not be quoted as an accuracy figure for photographs.** That still needs a labelled corpus, which does not exist here |
| Image quality signals are calibrated | Thresholds documented with reasoning; verified against generated images covering each failure mode. Two corrections came from real inputs rather than from the generated set: the glare detector once flagged white packaging, and a plain studio backdrop was counted twice, as glare and again as bright clipping, so a catalogue photograph of a panel was refused for a background rather than for the light on it. Both are covered by `tests/test_imaging_quality.py`, in both directions | Calibration against a labelled set of real photographs with human quality judgements. The backdrop test is geometric: a clipped flat region reaching three or more edges of the frame is a background. A photograph where a genuine highlight reaches three edges would be discounted, though such an image is almost entirely blown out and the brightness and clipping signals report it anyway |
| Accessibility targets WCAG 2.2 AA | axe-core (wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22a, wcag22aa) reports zero violations at any severity on twenty-nine pages: fourteen public, all fourteen workspace screens, and the inspection screen again as a reviewer. No workspace screen scrolls sideways at 320, 360, 390 or 820 pixels. Every register is asserted to show real rows rather than an empty state. One `h1` per page, skip link as first tab stop, all form fields labelled | Manual screen-reader testing with NVDA, JAWS or VoiceOver; testing with real assistive-technology users; manual keyboard and focus-order review, because an axe pass finds markup faults and not an illogical tab order |
| Reports render Hindi | The PDF registers Noto Devanagari and selects it automatically for Devanagari text; if the font is missing the document says so instead of printing empty boxes | A report containing substantial Hindi content has not been visually proof-read |
| Jurisdiction isolation | Cross-jurisdiction read returns 404, the register excludes out-of-scope records, and the controller hierarchy works, all against a live API | A systematic sweep of every one of the 97 routes for object-level authorisation |
| Audit chain is tamper-evident | The database refuses UPDATE and DELETE; a forged INSERT with a wrong `previous_hash` is detected and the offending sequence named | Behaviour under an attacker with direct database superuser access, who could drop the trigger |

## Deliberate design limits

These are choices, not gaps.

**Absent evidence is never a violation.** If a declaration cannot be read the outcome is
`unable_to_determine` or `additional_evidence_required`. This means Maanak will
under-report rather than over-report, which is the correct bias for a system whose output
could support enforcement.

**Character height needs a physical measurement.** The system refuses to convert pixels
to millimetres. This makes the check less automatic and more defensible.

**Net quantity is never verified.** Label analysis cannot establish package contents.
Every report states this in its limits section.

**A barcode is not proof of authenticity.** A successful read proves an identifier is
printed on a package. `officer_confirmed` is recorded separately, and nothing infers
country of origin from a GS1 prefix.

**Products are not jurisdiction-scoped.** The product catalogue is a shared national
reference; inspections are scoped. Duplicating a package variant per district would
defeat the purpose of a shared repository.

**Rate limiting fails closed on sensitive endpoints.** If Redis is unavailable, sign-in,
password reset and public complaint submission are refused rather than allowed
unprotected. This trades availability for safety on exactly the endpoints where that is
the right trade.

## Operational limits of this build

- `MAANAK_ENV=development` by default. Cookies are not `Secure`, API documentation is
  exposed, and `TRUSTED_HOSTS` is `*`. `MAANAK_ENV=production` refuses to start until
  those are corrected, but it cannot check the non-technical items.
- Secrets live in a `.env` file. A real deployment needs a managed secret store.
- MinIO uses its built-in KMS with a local key. Production needs a real KMS or the
  storage service's own encryption at rest.
- The application connects to PostgreSQL as the owning role. The append-only audit
  guarantee currently rests on triggers rather than on a role that lacks `UPDATE` and
  `DELETE` grants. Adding a restricted role is straightforward and is the stronger
  control.
- Contact details on the public pages are placeholders and are labelled as such. They
  must be replaced with verified official contacts.

## What would change these limits

In rough order of value:

1. A labelled corpus of real package photographs, which would turn the OCR and quality
   claims from "the mechanism works" into measured figures with error bars.
2. Confirmation of every rule citation and threshold by a qualified authority, which is
   what moves `legal_authority_confirmed` from false to true.
3. Manual screen-reader testing, which is the half of accessibility that automated tools
   cannot cover.
4. A restricted database role for the application, removing the trigger as the only
   thing standing between a compromised application and the audit trail.
5. Load testing with realistic image sizes and concurrency, to set a real performance
   budget rather than an assumed one.
