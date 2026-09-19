---
name: human-prose
description: Write and rewrite prose so it reads as genuinely human-written rather than machine-generated. Removes AI slop, LLM tells, and chatbot tics — AI vocabulary (delve, showcase, underscore, tapestry, pivotal), participial tails, negative parallelisms ("not just X but Y"), rule-of-three padding, copula avoidance ("serves as" for "is"), significance inflation, "Challenges"/"Legacy"/"Conclusion" scaffolding, title-case headings, bold spam, inline-header bullet lists, em dash abuse, curly quotes, emoji headers, and tool leak markers (oaicite, turn0search, utm_source=chatgpt.com). Use when asked to humanize, de-slop, de-AI, or naturalize text; when writing articles, blog posts, docs, READMEs, essays, emails, bios, commit messages, or PR descriptions that must not sound AI-generated; or when the user says text "sounds like ChatGPT."
license: CC-BY-SA-4.0
compatibility: Any environment. The optional linter needs Python 3.8+ (standard library only, no network).
metadata:
  version: "1.0.0"
  author: human-prose
  basis: "Wikipedia:Signs of AI writing (WP:AISIGNS), CC BY-SA 4.0"
---

# human-prose

Produce text a careful reader would attribute to a person who knows the subject, not to a model averaging over the internet.

## When this skill is active

Apply it to **every** run of prose you emit in the session: new drafts, rewrites, summaries, docs, commit messages, replies. Do not apply it to code, config, log output, or verbatim quotations from sources.

Two modes:

| Mode | Trigger | What you do |
| --- | --- | --- |
| **Compose** | User asks for new writing | Draft under the rules below, then run the audit before returning |
| **Repair** | User supplies text to humanize | Diagnose tell by tell, rewrite, report what changed and why |

In Repair mode, never hand back a silent rewrite. Show a short diagnosis list (`tell -> fix`) so the user can judge the edit.

---

## 1. The root cause, and the one fix

A language model predicts the likeliest next token, so it drifts toward the statistical center: the phrasing that fits the widest range of topics. Specifics are rare, so they get smoothed away and replaced with importance claims. "Invented a train-coupling device in 1873" becomes "played a pivotal role in the evolving landscape of rail transport." The subject gets **vaguer and louder at the same time**. Every tell in this skill is a symptom of that single drift.

The fix is not a thesaurus pass. Swapping *pivotal* for *important* leaves the sentence just as empty.

> **Specificity is the only real cure.** Replace each unfalsifiable claim with a fact that could be checked and could be wrong: a number, a date, a name, a place, a price, a version, a measurement, a quotation, a failure.

Test every sentence: **could this sentence appear, nearly unchanged, in an article about a different subject?** If yes, it is filler. Cut it or replace it with something only true of this subject.

Second test: **would a person with an actual opinion about this topic bother to write this sentence?** Nobody volunteers "this reflects broader trends in the industry." People volunteer "the 2019 model leaked oil and they never admitted it."

---

## 2. Hard bans

Never emit these. No exceptions, no "one is fine."

**2.1 Tool leak markers.** Any of these means the text is provably machine output:
`:contentReference[oaicite:0]{index=0}` · `oai_citation` · `turn0search1` · `turn0image0` · `citeturn0news0` · `[cite: 3, 12]` · `[span_1](start_span)` · `grok_card` · `grok_render_citation_card_json` · `【85†L261-269】` · `[attached_file:1]` · `[web:1]` · `ppl-ai-file-upload` · `:::writing{variant="document" id="…"}` · `?utm_source=chatgpt.com` · `utm_source=openai` · `utm_source=copilot.com` · `referrer=grok.com`

Strip UTM and referrer parameters from every URL you write.

**2.2 Talk aimed at the user, left inside the deliverable.** `Certainly!` · `Of course!` · `You're absolutely right!` · `I hope this helps` · `Let me know if…` · `Would you like me to…` · `Here is a…` · `In this article, we will explore` · any `<!-- note to reviewer -->`, "delete this before submission," or self-assessment that the text complies with the platform's rules. If you need to say something to the user, say it in chat, outside the artifact.

**2.3 Knowledge-cutoff and gap speculation.** `As of my last update` · `Up to my training data` · `While specific details are limited` · `not widely documented` · `based on available information` · `maintains a low profile` · `keeps personal details private`. If you do not know a fact, either leave it out or state the gap in the user's voice with a reason: "The company has not published unit sales." Never invent a "likely" value to fill the hole, and never assert that information is undocumented as a way of padding.

**2.4 Placeholders shipped as prose.** `[Company Name]` · `[Insert date]` · `2025-xx-xx` · `(Add your URL here)` · `X and Y` filler. Either fill it in or ask the user.

**2.5 Fabricated citations.** No source you did not actually retrieve. No invented DOIs, ISBNs, page numbers, or URLs. See `references/05-citations-and-artifacts.md`.

**2.6 The signature constructions.** These four carry more weight than any word choice:

1. **Participial tail** — a comma plus an `-ing` verb that editorializes at the end of a sentence: `…, highlighting its significance.` `…, reflecting broader trends.` `…, ensuring accuracy.` `…, cementing his legacy.` Delete it. If the claim matters, make it its own sentence with evidence.
2. **Negative parallelism** — `not just X but Y` · `it's not X, it's Y` · `no X, no Y, just Z` · `Y rather than X`. Say what the thing is.
3. **Rule-of-three padding** — `fast, reliable, and scalable` · `in schools, hospitals, and workplaces`. Cut to the one or two items you can support, or to four unbalanced ones.
4. **Copula avoidance** — `serves as` · `stands as` · `functions as` · `represents` · `boasts` · `features` · `offers` · `marks` where `is`, `are`, or `has` is the honest verb. Write `Gallery 825 is the association's exhibition space` and `it has four rooms`.

**2.7 Outline scaffolding.** No section, heading, or closing paragraph named or functioning as: Introduction · Overview (as a wrapper for the real content) · Key Features · Challenges · Challenges and Opportunities · Impact · Legacy · Significance · Future Prospects · Future Outlook · Awards and Recognition · Conclusion · In Summary · Final Thoughts · Key Takeaways. Also banned: the closing move "Despite these challenges, X continues to…". End when the content ends.

---

## 3. Vocabulary discipline

Full table with replacements: `references/01-vocabulary.md`. The short version:

**Tier 1 — never write these words in their figurative or evaluative sense:**
delve · showcase · underscore (as verb) · tapestry · testament · landscape (abstract) · realm · interplay · intricate · pivotal · crucial · vital · meticulous · garner · foster · bolster · boast · myriad · plethora · seamless · holistic · multifaceted · nuanced (as praise) · profound · vibrant · groundbreaking · revolutionary · cutting-edge · transformative · unparalleled · indelible · enduring · ever-evolving · resonate · align with · leverage (as verb) · utilize · navigate (figurative) · unpack · shed light on · deep dive · at its core · at the heart of · nestled · in today's world · in an era of · stands as a testament · plays a key role · it is important to note · worth noting · valuable insights

**Tier 2 — one per 1,000 words, only when it is the precise word:**
highlight · emphasize · enhance · robust · comprehensive · significant · key (adj.) · notable · renowned · diverse · rich · complex · dynamic · framework · ecosystem (non-biological) · cornerstone · hallmark · turning point · Additionally · Moreover · Furthermore · Notably · Ultimately · reflects

**Tier 3 — fine in literal senses.** `underscore` for an underline character. `landscape` for terrain. `ecosystem` for actual organisms. `tapestry` for woven cloth. Context decides.

Density rule: **zero Tier 1 hits, and fewer than 3 Tier 2 hits per 1,000 words.** One such word is coincidence; a cluster is a fingerprint, because these words co-occur in model output far more than in human writing.

Model-specific extras: Grok over-uses `empirical`, `causal`, `correlate`, `holdouts`, and keeps over-using `underscore`. Fiction defaults to `Elara`, `whispering woods`, `the smell of ozone`, `somewhere, a dog barked`, `a mix of X and Y`, `she let out a breath she didn't know she was holding`.

---

## 4. Formatting discipline

Details in `references/03-formatting.md`.

- **Headings**: sentence case (`Early life`, not `Early Life`). No repeated article title as an H1 above the body. No heading whose only content is more headings. Never skip a level. Avoid the `X and Y` heading habit.
- **Bold**: for genuine terms of art on first use, and for nothing else. No bolding every instance of a keyword. Zero bold in narrative prose is normal and correct.
- **Lists**: a vertical list of `**Bold header:** explanatory sentence` items is the single most recognizable chatbot layout. Convert to prose unless the content is a genuine enumeration (steps, parameters, options, specs). Prose is the default; a list is a decision you must justify.
- **Em dash**: at most one per ~500 words, unspaced (`word—word`) or per the target style guide. Prefer commas, colons, parentheses, or a full stop. Never use one to "punch" a parallelism.
- **Quotes and apostrophes**: match the surrounding document. Do not silently emit curly `“ ” ’` into plain-text contexts such as code, Markdown source, YAML, or wiki markup.
- **Emoji**: never as heading decoration or bullet markers.
- **Thematic breaks**: no `---` between every section.
- **Tables**: only for data with two or more real dimensions. A two-row table restating three facts should be a sentence.
- **Markup**: emit exactly the target markup language. Never mix Markdown into wikitext, never leave a ```` ```wikitext ```` fence in output, never leave Markdown `**bold**` or `## heading` in a wiki, Jira, plain-email, or LaTeX target.

---

## 5. Rhythm and shape

Model prose is uniform. Human prose is lumpy.

- **Sentence length**: vary hard. Target a mean of 14 to 20 words with a standard deviation above 7. Put a 4-word sentence next to a 35-word one. If every sentence lands between 15 and 25 words, the passage reads as generated even when every word is defensible.
- **Paragraph length**: vary from one sentence to nine. Never three paragraphs of three sentences in a row.
- **Sentence openings**: no two paragraphs in a row starting with the subject-verb pattern. Do not open sentences with `Additionally`, `Moreover`, `Furthermore`, or `Notably`. `But`, `And`, and `So` at the start of a sentence are human and allowed.
- **Structure**: let the material dictate order. Chronology, a problem you hit, a specific example expanded, an argument that starts mid-thought. Anything but Intro-Body-Body-Body-Conclusion.
- **Commit**: humans state things flatly. `The API returns 429 after 60 requests.` Not `The API may return rate-limiting responses depending on usage patterns.`

---

## 6. What to add, not just remove

Deleting tells leaves clean, dead text. Human writing has positive markers that models suppress. Full list in `references/06-human-signals.md`. The core seven:

1. **Plain copulas and verbs.** `is`, `are`, `has`, `wrote`, `moved`, `used`, `tried`, `died`. Not `authored`, `relocated`, `utilized`, `attempted`, `passed away`.
2. **Superlatives and absolutes when true.** `the only`, `the first`, `the worst`, `nobody does this`. Models hedge these into mush.
3. **Hedges when honest.** `probably`, `roughly`, `I think`, `as far as I can tell`, `tends to`. Paired with a reason for the doubt.
4. **Checkable specifics.** Named people, exact dates, model numbers, dollar amounts, versions, filenames, error codes, street names.
5. **Wordiness that a style guide would flag.** `the fact that`, `in order to`, `a part of`, `all of the`. Perfectly compressed prose is a tell.
6. **Asymmetry.** One example explored for a paragraph beats four examples listed. Real writers have favorites and blind spots.
7. **Evidence of a body and a history.** What was tried first and failed, what it cost, what took three hours, what the author still does not understand and why. This is the hardest thing for a model to fake and the fastest way to sound human. When you lack this, ask the user for it rather than inventing it.

---

## 7. Workflow

Run in order. Do not merge passes; each one catches what the previous created.

1. **Brief.** Fix the writer (who, what they know, what they care about), the reader, the register, the dialect (en-US / en-GB / en-IN, then hold it), the target markup, and a hard length cap. Guess and state your guess if the user did not say.
2. **Facts.** List the concrete claims you can support before writing a sentence. If the list is thin, ask the user or narrow the piece. Never let structure outrun evidence — that gap is exactly what gets filled with significance padding.
3. **Draft.** Write to the fact list. One idea per sentence. No section you did not earn.
4. **Cut claim-free sentences.** Apply the two tests from section 1 to every sentence. Delete, do not soften. Expect to lose 15 to 30 percent of a first draft.
5. **Sentence surgery.** Hunt the four signature constructions (2.6). Restore copulas. Break triples. Vary length aggressively.
6. **Vocabulary.** Sweep for Tier 1 and Tier 2 words. For each hit, ask what the sentence actually claims, then write that instead. Do not substitute a synonym for an empty word; delete the empty claim.
7. **Formatting.** Section 4, top to bottom. Convert bullet stacks to prose. Fix heading case. Strip bold. Check the markup language matches the destination.
8. **Sources.** Verify every citation resolves and supports the sentence attached to it. Strip tracking parameters. Add page numbers for books.
9. **Audit.** Run the linter (section 8), fix findings, then re-read once from the top out loud. The read-aloud pass catches monotone rhythm that no regex can.
10. **Report.** In Repair mode, list the tells you removed. In Compose mode, state any fact you could not verify and any place you need input from the user.

---

## 8. Audit with the linter

```bash
python3 scripts/slopscan.py draft.md
python3 scripts/slopscan.py draft.md --verbose          # every hit with line numbers
python3 scripts/slopscan.py draft.md --json             # machine-readable
python3 scripts/slopscan.py draft.md --min-score 85     # exit 1 below threshold
cat draft.md | python3 scripts/slopscan.py -            # stdin
python3 scripts/slopscan.py docs/*.md --quiet           # batch, findings only
```

It reports fatal artifacts, phrase and vocabulary hits by tier, structural metrics (copula ratio, participial tails, bold density, em dash rate, sentence-length variance, title-case headings), and a 0-100 score.

**Ship at 90 or above. Below 75, rewrite rather than patch.** The score is a smoke detector, not a verdict: a 100 can still be vacuous, and a legitimate passage about musical underscores will lose points. Read the findings; do not chase the number. In particular, never "fix" a finding by paraphrasing around the regex while keeping the empty claim.

---

## 9. Calibration: do not overcorrect

Read `references/09-calibration.md` before accusing text of being AI-generated or stripping a document bare.

- Humans are near chance at spotting AI text, and detection tools have real error rates. Do not tell a user their writing "is AI." Point at specific patterns instead.
- These are **not** evidence of AI: perfect grammar, formal or academic vocabulary, any single em dash, curly quotes from Word or macOS, mixing casual and clinical registers, unsourced claims, correct markup, odd HTML artifacts from editors and extensions.
- Overcorrection has its own smell: zero em dashes anywhere, no transitions at all, every sentence clipped to eight words, all structure flattened, contractions forced into a formal document. Balanced human writing uses `however` sometimes and lists sometimes.
- Match the genre. A README should have bullet lists and code fences. A recipe should be numbered. Applying encyclopedic rules to a changelog produces something equally artificial.

**Scope and honesty.** This skill improves prose quality; it is not a guarantee against any detector, and no such guarantee exists. Where a venue, instructor, employer, journal, or platform requires disclosure of AI assistance, follow that rule. Say so plainly if a user asks you to help conceal AI use where disclosure is mandatory, then help them write well and disclose.

---

## 10. Pre-return gate

Do not emit prose until all ten are true:

- [ ] Zero tool leak markers, zero UTM parameters, zero chat pleasantries, zero placeholders
- [ ] Zero Tier 1 words; Tier 2 under 3 per 1,000 words
- [ ] Zero participial tails, negative parallelisms, and unearned triples
- [ ] `is` / `are` / `has` used wherever they are the honest verb
- [ ] No banned scaffold section; the piece ends without a summary
- [ ] Headings sentence-case, no skipped levels, no title repeat; bold rare; bullet stacks converted to prose
- [ ] Sentence-length standard deviation above 7; paragraph lengths uneven
- [ ] Every claim checkable, or explicitly attributed, or gone
- [ ] Every source retrieved and verified against the sentence it supports
- [ ] Dialect, register, and markup language consistent from first word to last

Then read it aloud once. If it sounds like a brochure, an outline, or a helpful assistant, go back to pass 4.

---

## Reference index

Load on demand; do not read all of these at once.

| File | Read it when |
| --- | --- |
| `references/01-vocabulary.md` | Full tiered word list with concrete replacements, era-by-era word drift, model-specific vocabulary |
| `references/02-sentence-patterns.md` | Syntax-level tells and how to rewrite each: participial tails, parallelisms, triples, copula avoidance, appositive stacking, rhythm targets |
| `references/03-formatting.md` | Headings, bold, lists, dashes, quotes, emoji, tables, markup mixing, per-platform layout rules |
| `references/04-content-tells.md` | Significance inflation, notability metacoverage, superficial analysis, scaffold sections, weasel attribution, disclaimers, commit-message and edit-summary tells |
| `references/05-citations-and-artifacts.md` | Source verification protocol, hallucinated DOI/ISBN detection, per-tool leak marker table, link hygiene |
| `references/06-human-signals.md` | The positive markers to add, with examples of each |
| `references/07-genre-playbooks.md` | Per-genre rules: encyclopedic, docs/README, blog, email, essay, marketing, commit/PR, bio, social, fiction |
| `references/08-worked-rewrites.md` | Six annotated before/after rewrites showing the full workflow |
| `references/09-calibration.md` | False positives, ineffective indicators, overcorrection, ethics and disclosure |
| `assets/final-pass-checklist.md` | Copy-paste checklist for a human reviewer |
| `scripts/slopscan.py` | The linter |

Derived from [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), CC BY-SA 4.0. Observations were reorganized and rewritten as generative rules; wording is original. Content was rephrased for compliance with licensing restrictions.
