# Maanak project report

A report on what we built, why we built it that way, what we measured, and what is still
missing. Written for a reader who has not seen the code.

Maanak is not a government service. It is not connected to any authority, nobody has
approved it, and it takes no action of its own. Every legal call it records is recorded
against the officer who made it.

---

## 1. What Maanak does, in one paragraph

An officer photographs a packaged product. Maanak checks whether the photo is good enough
to read. It then reads the label, pulls out the printed declarations such as MRP and net
quantity, and shows each reading next to the piece of the photo it came from. The officer
confirms, corrects or rejects each one. Only the readings an officer has confirmed go to
the rule engine. The engine applies a rule version someone has approved, writes down its
arithmetic, and produces a report. The report is frozen and fingerprinted, so anyone can
check later that it has not changed, without being shown the case.

The short version: read the label, keep the proof.

---

## 2. The problem we started from

Checking packaged goods for correct labelling is paper work today. An officer visits a
shop, looks at a packet, writes on a form, and files it. Three things go wrong with that.

**The proof and the decision get separated.** The photo, if there is one, ends up in one
place and the conclusion in another. Months later nobody can put them back together. If a
trader challenges the finding, the file cannot answer.

**Arithmetic errors are hard to catch.** Unit sale price is a division. Do it in your head
or in a spreadsheet with floating point and a case can turn on a rounding difference of
one paisa, with no record of how the number was reached.

**Missing evidence looks the same as a violation.** A form with a blank box does not say
whether the packet lacked the declaration, or the photo did not show it, or the print was
too blurred to read. Those are three different facts and only one of them is an offence.

We built Maanak around the third problem, because it is the one that decides whether the
record is worth anything.

---

## 3. The two rules that shape everything else

Almost every design decision follows from these two. They are not written in a document
and hoped for. They are enforced in code and covered by tests.

### Missing proof is never a violation

Three situations look identical on a screen and mean completely different things:

| What is true | What Maanak answers |
| --- | --- |
| The packet genuinely does not carry the declaration | Non-compliant |
| The photo does not show that part of the packet | More evidence needed |
| That part is visible but cannot be read | Cannot tell |

Only the first is a failure. No setting makes the other two report as a violation.

You can watch this happen. Run the checks on an inspection **before** the officer reviews
the readings: 7 rules answer "more evidence needed", 3 answer "cannot tell", and **zero**
say non-compliant. Review the same photograph, change nothing else, and run them again: 10
rules now apply and one non-compliant finding appears. The evidence did not change. The
review did.

### The machine and the officer are two separate records

OCR writes a candidate reading with a machine state and a confidence score. The officer
writes a review state separately. A correction never overwrites what the machine read: the
old value is saved to a revision first, and both appear on the report.

Only reviewed values reach the rule engine, and that is checked inside the engine rather
than left to the screen to remember. If a value has not been reviewed, no rule can use it,
whatever the interface does.

---

## 4. What happens to one package

1. The officer photographs the packet in the browser, or attaches a file already on the
   phone. On a phone the camera opens inside the page, so the panel can be lined up before
   anything is kept. There is no app to install.
2. The image is checked from its own bytes and scored on eleven things: sharpness, glare,
   highlight clipping, shadow clipping, brightness, contrast, resolution, skew, framing,
   text size and where the file came from. The officer is told what to fix in plain words,
   for example "strong glare is covering part of the panel".
3. The original bytes are stored exactly as they arrived, fingerprinted with SHA-256, and
   the chain of custody is written down. Location is never taken from photo metadata.
4. A separate background worker reads the panel with Tesseract in English and Hindi. It
   tries several language and rotation settings and keeps whichever one measurably reads
   best. The officer never waits for this.
5. Eleven declarations are found and tidied up using exact decimal arithmetic and
   unit-aware conversion: MRP, net quantity, unit sale price, manufacturer, consumer care,
   country of origin, date marking and batch among them.
6. Each reading is shown beside the region of the image it came from, to confirm, correct
   or reject with a reason.
7. Approved rule versions run on the reviewed values. Every finding records the provision
   it cites, why that version was chosen, the inputs it used and the arithmetic it did.
8. A report snapshot is frozen and hashed, then rendered to PDF and to an editable
   document from that same snapshot.
9. A public page confirms the report exists and has not changed, and says nothing about
   the case.

A consumer report can be triaged into an inspection, carrying the consumer's photo across
as evidence. A reported inspection can become a case with a served notice that cannot then
be edited.

---

## 5. What the public can do without an account

Four services, gathered on one page:

| Service | What you need | What you get back |
| --- | --- | --- |
| Read what must be printed on a package | nothing | The eleven declarations in plain words, each with the provision it is attributed to and whether that attribution is confirmed |
| Report a packaged product | a photo and a description | A reference to keep. Contact details are optional |
| Track that report | the reference **and** the contact detail you gave | Progress only, never the inspection that followed |
| Check a report reference | the reference and its printed code | Whether the report was issued and is unchanged, and nothing about the case |

The same page also states what Maanak does not do, which matters more than looking
complete. **Nothing here judges nutrition, ingredients, allergens or food safety.** No
rule comes from the Food Safety and Standards regulations and it gives no dietary advice.
Net quantity cannot be confirmed from a photo, and a barcode that scans is not proof that
a product is genuine. For each of those the page names the body that does hold the power:
FSSAI, the state Controller of Legal Metrology, the National Consumer Helpline on 1915,
and filing before a consumer commission.

---

## 6. Why the letter-height check refuses to answer

A minimum character height in millimetres cannot be worked out from a photo. The same
letter covers more pixels from close up and fewer from further away. Without a known scale
in the frame there is no conversion.

So the check refuses. With no officer measurement it answers "more evidence needed" and
says what is needed. With a measurement it compares against the threshold **together with
the stated uncertainty**, and a measurement whose range crosses the threshold answers
"cannot tell" rather than giving a decision that would not survive being challenged.

This is the clearest example of a general habit: the system would rather say it does not
know.

---

## 7. How it is built

One application in clean layers, not a pile of services. FastAPI serves the API. A
separate arq worker runs OCR so no request ever waits on it. Redis carries the queue.
MinIO provides S3-compatible storage encrypted on disk. PostgreSQL 16 is the only
database. nginx serves the pages and passes API calls through.

The front end is plain HTML, CSS and ES modules. **No build step, no framework, no
bundler, no outside script.** The content security policy is `default-src 'self'` with no
`unsafe-inline`, which is a checkable claim rather than a hopeful one: an inline `style`
attribute in the officer workspace was found and removed because the policy refuses it.

Layers run one way only. `app/api/v1/` holds routes and no logic. `app/schemas/`
validates. `app/services/` holds all behaviour. `app/models/` holds tables. `app/domain/`
holds the enums and state machines and is the single source of truth: it generates both
the database CHECK constraints **and** the words the browser shows, so the two cannot
drift apart.

Some invariants worth knowing:

- Area of responsibility is applied inside the SQL query, never filtered from results
  afterwards. Asking for a record outside your area returns **404, not 403**, because a
  403 would confirm the record exists.
- `audit_events` refuses `UPDATE` and `DELETE` through a database trigger, so an
  administrator with full application access still cannot edit history. Entries are
  hash-chained. Forging one has been tested: verification named the offending sequence
  number and reported that its previous hash did not match.
- Money and quantities are `Decimal` throughout, rounded half up to the paisa. Never
  floating point.
- Report snapshots, served notices and evidence identity cannot be changed, by trigger.
- Sessions are cookie-only. There are no bearer tokens anywhere in the design.
- Every request schema sets `extra="forbid"`, so a caller cannot set a field the endpoint
  never meant to expose.

Hardware is modest. Six containers peaked at 693 MiB during OCR on one ordinary machine.
The only field device is a camera phone.

---

## 8. The rule interpretations are not confirmed, and the system says so

Eleven interpretations ship with the software. **None has been checked against a gazette
notification.** Each carries a legal-authority flag set to false, and that flag appears on
the rule, on every finding that uses it, and printed on every report.

Some values are placeholders and are labelled as such. The minimum character height is a
single figure where the real minimum changes with the area of the principal display panel.
The permitted unit lists come from ordinary retail practice rather than from the Second
Schedule.

`docs/LEGAL_SOURCES.md` names every one of them and the procedure to close each gap. An
authority can approve a corrected version without a code change, and the author of a
version cannot approve their own.

The engine and the citations are two separate claims. What the engine does is tested and
holds whether or not a citation string turns out to be right.

---

## 9. How well the reader actually reads

Two benchmarks. The weaker one is the honest one.

**On labels this project generates**, `measure_ocr_accuracy.py` scores ten declarations
with known correct values under eight kinds of damage: as generated, scaled to 1200 and
900 pixels wide, rotated 2 and 6 degrees, JPEG quality 55, slightly blurred, and on a
white backdrop. It gets **72 of 80 fields right**. All eight failures are the same
failure: the reader returns *lodised* for *Iodised*, because capital I and lowercase l are
the same shape in a plain font. No profile or dictionary setting fixed it, so the reading
is kept and the ambiguity is reported to the officer instead of being quietly corrected. A
rule that turned a leading lowercase l into a capital I would also turn *Lemon* into
*Iemon*.

**On photographs of real packaging the picture is much worse**, and it is worth saying
plainly. `measure_ocr_real.py` runs 14 consumer photographs of Indian packs contributed to
Open Food Facts, using each product's declared quantity as the correct answer. Six of the
14 produced any declaration at all, ten declarations were found in total, and **net
quantity was read from none of them**. One failure is a crop of a salt pouch showing "NET
QUANTITY: 1 kg" in large bold type; all seven reader profiles return nothing or noise on
the whole image. Crop to just those words and plain greyscale reads "NET QUANTITY:"
exactly. That moves the diagnosis: the engine can read this print, and asking it to make
sense of a whole curved packet in one pass is what defeats it. The value is harder still,
because "1 kg" misreads even when isolated.

**There is no 100 per cent here and there is not going to be.** What the system does
instead is refuse to turn a failed reading into a finding. Across all 14 photographs,
including the five the quality gate refused outright, the number of non-compliant findings
produced before officer review was **zero**. That is the property worth having: the reader
is unreliable on real packaging, and the design already assumes it.

---

## 10. What we measured

Every suite prints each check with the value it measured, so a passing run reads as a
statement of what was verified rather than a count. All the figures below were read off a
run on the current tree.

### Correctness

| Suite | Result |
| --- | --- |
| `verify_schema.py` | 14 checks: 30 tables, 184 indexes, 29 CHECK constraints, and the audit table rejects UPDATE and DELETE |
| `verify_security.py` | 51 checks |
| `verify_extraction.py` | 62 checks |
| `verify_rules.py` | 71 checks |
| `verify_auth_flow.py` | 70 checks |
| `verify_pipeline.py` | 56 checks |
| `verify_workflow.py` | 117 checks |
| `verify_matters.py` | 86 checks |
| **Total across the eight** | **527 checks** |
| pytest | 321 unit items, 5 more that need the live stack |
| `quality.sh` | 139 files formatted, lint clean, types clean on 88 files |

### The interface

| Suite | Result |
| --- | --- |
| `verify_browser.py` | 60 checks, 0 accessibility violations on 8 pages |
| `audit_app.py` | 140 checks: every page, all 14 workspace screens scanned, 0 violations, every register showing real rows, and no sideways scroll at 320, 360, 390 or 820 pixels |
| `verify_officer_flow.py` | 44 checks: the whole officer workflow driven through the interface, from opening an inspection to opening a case |
| `measure_a11y.py` | 0 violations across 14 public pages at WCAG 2.0, 2.1 and 2.2 level A and AA; 0 targets under 24 by 24; 0 sticky or fixed elements |
| `check_links.py` | 0 broken links, 76 in-page anchors land on something |
| `scan_tints.py` | 0 warm-tinted surfaces across 24 pages at 3 widths |
| `check_workspace_chrome.py` | 14 screens: one header, one footer, the standing note present |
| per-role navigation | 5 roles, 0 mismatches: 9, 9, 7, 7 and 4 links visible |
| second-factor panels | 25 of 25 checks, with each panel driven visible first because a scanner ignores hidden content |

### The words a reader sees

| Suite | Result |
| --- | --- |
| `check_prose.py` | 0 machine-writing tells across 28 pages and 15 documents |
| `check_error_messages.py` | 177 error messages, 0 naming a JSON key or a database column |
| `check_permission_names.py` | 33 permission names used by the interface, 0 that do not exist |
| `check_js_bindings.py` | 27 modules, 0 using a helper they never imported |
| `check_report_text.py` | 2 documents: the text of the generated PDF and Word file, 0 problems |
| `check_api_reach.py` | 98 API operations: 74 reached from a screen, 24 recorded with a reason, 0 unexplained |

### Recovery and speed

| Suite | Result |
| --- | --- |
| `verify_restore.py` | 11 checks on a restored deployment: the audit chain recomputes, its head sequence, head hash and event count all match what the backup recorded, the append-only trigger survived, and every stored object still matches its hash |
| `verify_package.sh` | 39 checks on the release archive |
| `measure_load.py` | Reads peak at 156 requests per second at 2 threads, p50 14 ms and p95 19 ms. The worker clears 17 OCR jobs a minute at 3.6 seconds each, bounded on purpose by `max_jobs = 2`. One machine, not a published benchmark |

Two of these exist because standard tooling does not cover them. `measure_a11y.py`
measures WCAG 2.2 success criterion 2.5.8, for which axe-core has no rule, and lists
sticky positioning for 2.4.11. `check_prose.py` enforces the writing rules this project
holds itself to, so "the copy is not machine-generated filler" is a check and not a claim.
It treats the em dash as a hard failure rather than rationing it: every place the code
reached for one turned out to be a sentence that read better rebuilt around a colon, a
full stop or a different clause order.

Both found real defects. Target-size measurement caught utility links at 19 pixels,
checkboxes at 13 by 13 and file inputs at 21. Extending the accessibility scan to the
inspection screen caught a critical and a serious violation on the most important screen
in the application.

---

## 11. What can go wrong, and what we did about it

| Risk | What we did |
| --- | --- |
| Real packets are hard to read. Of 14 shopper photos, 6 gave any reading and net quantity came out of none | Built for a reader that fails. Across all 14, violations raised before review: zero |
| Capital I and small l are one shape, so "Iodised" reads as "lodised" in 8 of 80 generated fields | Report the ambiguity to the officer. Never correct it quietly, because the same rule would turn "Lemon" into "Iemon" |
| No rule interpretation is confirmed against a gazette notification | Carry the doubt to the reader. Every rule is marked unverified on the rule, on each finding, and on the printed report |
| Letter height cannot be measured from a photo | Refuse rather than decide. Ask for a measurement, then weigh its error bars |
| The shipped setup is not hardened | Make the gaps checkable. Turning on production mode refuses to start while several settings are still unsafe |
| A legal call belongs to a Controller, not to software | Version the interpretations, so an authority approves a new one without a code change, and nobody approves their own |

---

## 12. What is missing before real use

This is a working local deployment, not an accredited production system. The gaps are
named one by one rather than gestured at, here and on the project's own security and
accessibility pages.

Absent today: TLS, malware scanning on upload, managed secrets, monitoring, alerting, an
incident process, and any independent security or accessibility assessment. No screen
reader has been run against the interface and nobody has tested it with disabled users.

Backup and restore are built and proven rather than absent. `scripts/backup.sh`,
`scripts/restore.sh` and `api/scripts/verify_restore.py` exist, and the drill has been
run: a fresh backup, a restore over the deployment, then 11 checks confirming the restored
copy holds the same trail, the same evidence and the same reports. What is still missing
there is scheduling and an off-machine target, both of which are deployment decisions.

Before field use an authority must:

- have every legal interpretation confirmed against the gazette and recorded against the
  rule version;
- terminate TLS and set `COOKIE_SECURE=true`, `DOCS_ENABLED=false` and explicit
  `TRUSTED_HOSTS`;
- move secrets into a managed store;
- require the second factor rather than only offering it;
- replace the development report signer with a real signing service, or leave signing off
  rather than implying a signature exists;
- commission independent security, accessibility, legal and user-acceptance testing.

Setting `MAANAK_ENV=production` refuses to start while several of those remain unsafe. It
checks what can be checked and cannot check the rest.

---

## 13. How the work was done

Every change went through the same path: open an issue, branch, make one focused change,
run the checks locally, commit with a message that says why, push the branch, open a pull
request that links the issue, let continuous integration run, read the whole diff, then
squash and merge and delete the branch. No direct pushes to the main branch.

Seven continuous integration jobs gate every pull request and then run again on the main
branch:

| Job | What it does |
| --- | --- |
| `quality` | Formatting, lint and types |
| `unit` | The fast tests, with coverage kept as an artefact |
| `static-checks` | The prose gate, the import check, the permission-name check, the error-message check |
| `migrations` | Upgrade, downgrade, upgrade again, then fail if the models have drifted from the schema |
| `integration` | The full stack, the live-stack suites, the browser suite, then a seeded workspace and the page and document checks |
| `supply-chain` | Dependency audit, a bill of materials, a secret scan, and a container scan that fails on high or critical findings |
| `release-archive` | Builds the release archive and checks it extracts complete |

Two honest limits on review. The automated reviewer answered that it had reached its quota,
and the platform does not let an author approve their own pull request, so approval could
not be satisfied from the authoring account. We say that rather than claiming the change
was reviewed by someone else.

---

## 14. Running it and checking it yourself

Docker with Compose v2 is the only requirement. No Python, Node or database on the host.

```bash
cp .env.example .env
# replace every CHANGE-ME value, then
docker compose up --build -d
```

| What | Where |
| --- | --- |
| Browser application | http://localhost:8080 |
| API readiness | http://localhost:8000/health/ready |
| API documentation | http://localhost:8000/docs |
| Object storage console | http://localhost:9001 |

`GET /health/ready` reports each dependency on its own and returns 503 while any of the
four is unavailable.

Two commands fill a workspace you can explore. The first creates an account per role,
loads the starter rules, and takes each one through simulation and approval using the
*second* rule administrator, because an author cannot approve their own version. The
second walks one case through the whole path:

```bash
docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_demo.py

docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_example.py
```

That produces one connected example: consumer report `CMP-2026-000001`, inspection
`INSP-2026-000001`, 11 readings confirmed, checks, a decision, report `RPT-2026-000001`,
case `CASE-2026-000001` and notice `NOT-2026-000001` served.

`docs/TESTING.md` lists every suite, the exact command that runs it, and what it proves.
`docs/RUNNING.md` covers a clean machine step by step. `docs/KNOWN_LIMITS.md` records both
OCR figures and the diagnosis behind them.

---

## 15. Who built it

devpilotX and catburglarX. The code is at https://github.com/devpilotX/maanak under the
Apache License 2.0.

axe-core is included under `api/scripts/` for the accessibility suite, unmodified, under
the Mozilla Public License 2.0. It is never served to users and is not part of the
deployed application.
