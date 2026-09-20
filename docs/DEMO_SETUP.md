# Setting up the demonstration workspace

How to get a working, populated Maanak on a laptop so a judge can watch it work, including
the one demonstration that is worth more than all the others: running the compliance checks
**before** an officer has reviewed anything, and then again after.

Nothing in this file changes any project code. Every command below is an existing script in
the repository, and every figure was read off a real run.

Read `docs/DEMO.md` afterwards. That document is the nine step story to tell. This one is
how to make the workspace those nine steps need.

---

## 1. The short answer

The demonstration data already exists. Two commands build it. If a workspace looks empty,
one of the two has not been run or did not finish.

From the repository root, with the stack already up:

```bash
docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_demo.py

docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_example.py
```

The first makes one account per role and loads the eleven rules, taking each through
simulation and approval using the *second* rule administrator, because an author is not
allowed to approve their own version.

The second walks one case along the entire path. It generates a label image, uploads it as
evidence, waits for the reading, confirms eleven readings, runs the checks, records a
decision, issues a report, opens a case and serves a notice.

When the second one finishes it prints this:

```
  case opened: CASE-2026-000001
  notice prepared: NOT-2026-000001
  notice issued and frozen, response due 2026-10-05
  service recorded against the notice
```

If you do not see those four lines, the example did not finish. Section 3 covers why.

---

## 2. What the seeded workspace contains

Measured on a real run, not described from memory:

| What | Value |
| --- | --- |
| Accounts | 7, one per role, all signing in |
| Rules loaded, simulated and approved | 11 |
| Consumer complaint | `CMP-2026-000001` |
| Inspection | `INSP-2026-000001`, state `case_opened`, decision `violation_found` |
| Evidence on it | 1 file, `packet.jpg`, reading `completed` |
| Machine readings | 11, every one confirmed by an officer |
| Findings | 10: seven compliant, one not allowed, one needs more evidence, one cannot tell |
| Report | `RPT-2026-000001`, frozen and fingerprinted |
| Case | `CASE-2026-000001` |
| Notice | `NOT-2026-000001`, served and frozen |

Sign in at http://localhost:8080/login.html. Every account uses the password the seeder
prints, and all seven are `@example.org`: `admin`, `inspector`, `reviewer`, `controller`,
`ruleauthor`, `ruleapprover`, `otherstate`.

One detail worth knowing before you stand in front of anyone. Open `INSP-2026-000001` and
look at the common name reading. It says **lodised Salt**, not **Iodised Salt**. That is
not a mistake in this document. In most plain fonts a capital I and a lowercase l are the
same shape, so there is nothing in the picture to tell them apart. Maanak keeps what it read
and tells the officer the two letters are confusable here. Point at it. It is the honest
centre of the whole project.

---

## 3. When the workspace comes out empty

Work through these in order. Each one has actually caused this.

### The stack is not ready yet

```bash
curl -s http://localhost:8000/health/ready
```

All four parts must say `ok`. Seeding against a half-started stack fails in the middle and
leaves accounts with no work attached to them.

### Only the first command was run

`seed_demo.py` on its own gives you accounts and rules and **no work at all**, so every
count on the overview reads zero and every detail screen has nothing to open. That is the
most common cause of "there is no demo in the inspection screen". Run `seed_example.py` too.

### The reading did not finish

`seed_example.py` uploads a label and then waits for the background reader. If the worker is
unwell the example stops before the case is created. Check the worker, then run it again:

```bash
docker compose ps worker
docker compose logs --tail 40 worker
```

### Sign-in has started refusing

Sign-in is limited per address and per account and it fails closed, so a long session of
repeated attempts eventually returns an error instead of a session. Clear the counters
without touching any data:

```bash
docker compose exec redis sh -c \
  "redis-cli --scan --pattern 'maanak:rl:*' | xargs -r -n1 redis-cli DEL"
```

### An account is asking for a six digit code

If `inspector@example.org` answers **"This account requires a code from its authenticator
application"**, a second factor was enrolled on it at some point and never removed. This is
a demonstration stopper, and it is easy to hit by accident while exploring the account
screen.

Check which accounts are affected:

```bash
docker compose exec db psql -U maanak -d maanak \
  -c "select email, mfa_enabled from users order by email;"
```

Any `true` there needs clearing. An administrator can reset it from the administration
screen, or start clean with section 6.

### Start completely clean

This throws away all application data and rebuilds it. Safe on a demonstration laptop, and
the right move an hour before presenting:

```bash
docker compose run --rm --no-deps migrate python scripts/reset_data.py
```

Then run the two seed commands from section 1 again.

---

## 4. The demonstration that is worth the most

Everything above gives you a **finished** case. A judge sees the result but never sees the
system decide anything, because all eleven readings were confirmed before they arrived.

The strongest thing you can show is this sequence:

1. Run the compliance checks on an inspection **nobody has reviewed yet**.
   Maanak answers: **seven "show me more", three "cannot tell", zero faults.**
2. Change nothing about the photograph. The officer confirms the readings.
3. Run the same checks again.
   Now: **ten rules apply and one fault appears.**

The evidence did not change. The review did. That single before and after is the entire
argument of the project, and it takes about ninety seconds to perform.

Those numbers are not an estimate. They were read off a run while this file was written.

### Leaving an inspection ready for it

Do this **before** the judge arrives, so that on the day you only have to do the second
half. Entirely through the interface, with no scripts and no code changes.

First, put a label image on the laptop. The repository can generate the same panel the
seeder uses:

```bash
docker compose run --rm --no-deps --user root -v "$PWD/api:/app" \
  --entrypoint python api scripts/make_sample_label.py
```

That writes `api/screenshots/clean-label.jpg`, about 199 KB. Copy it somewhere you can find
it in a file dialog. To choose the destination yourself, set `SAMPLE_LABEL_PATH`.

Then, in the browser:

1. Sign in as `inspector@example.org`.
2. Go to **Inspections**, then the **New inspection** button at the top.
3. Fill in the dialog. The fields it asks for, by their labels on screen:
   - **Inspection date**, already set to today
   - **Source**, leave it on the default
   - **Product**, a dropdown. The quickest route is to pick the salt product the seeder
     already created. If you choose to create a new one instead, three more fields appear
     and all three are required: **Brand**, **Product name** and **Commodity category**.
     For example `Riverside`, `Riverside Iodised Salt 1 kg (sample data)` and `salt`.
   - **Premises name**, optional, for example `Demonstration counter (sample data)`
   Put `(sample data)` in anything you type. Everything on screen during a demonstration
   should say what it is.
4. Press **Create**. The inspection appears in state **draft**.
5. Open it. Go to the evidence section, choose the face **Declaration panel**, and upload
   the label image.
6. Wait a few seconds. The reading runs in the background and the state moves to **officer
   review** on its own. Eleven readings appear, every one of them waiting for you.
7. **Press Run checks now, before confirming anything.** Read the result aloud: seven need
   more evidence, three cannot be told, and **nothing is a fault**.
8. Stop there. Leave the eleven readings unconfirmed. Close the laptop.

### On the day

1. Open that inspection. Show the eleven readings still waiting.
2. Show the check results from yesterday: zero faults.
3. Confirm the readings. Take your time on one of them: show the crop of the photograph
   sitting beside the value Maanak read. Correct one deliberately and point out that the
   machine's original reading is kept rather than overwritten.
4. Run the checks again. One fault appears.
5. Say the line: the photograph never changed, the review did.

### What to expect on screen

| Moment | What Maanak answers |
| --- | --- |
| Checks before any review | 7 need more evidence, 3 cannot be told, **0 faults** |
| Checks after every reading is confirmed | 10 rules apply, **1 fault** |

If your numbers differ slightly, the reading found a different set of declarations on your
image. The shape of the result is what matters: **zero faults before a human looks, and a
fault only after.** That holds every time, because the rule engine refuses to use a value
nobody has reviewed.

---

## 5. Two more moments that land well

### A bad photograph is refused, with the reason in plain words

Take a deliberately poor photograph with a phone: move the camera as you press the button,
or angle it so a light reflects off the packet. Upload that as evidence.

Maanak refuses it and says what is wrong in words a person uses, for example that strong
glare is covering part of the panel. It does not say "quality score 0.42".

The point to make: the officer is still standing in the shop. He can move and take another
photograph. Finding out a week later that the photograph was useless means going back.

### Letter height refuses to answer

Open the finding about minimum letter height. Maanak has not decided anything. It is asking
for a measurement with a real instrument.

A photograph cannot give millimetres. The same letter fills more of the picture from close
up and less from further away, and with no ruler in the frame there is no conversion. So
Maanak asks instead of inventing a number. Give it a measurement of 1.5 mm give or take
0.2 mm against a 1.6 mm minimum and it still answers **cannot tell**, because the true value
might be either side of the line.

Judges remember the system that refused to guess.

---

## 6. A checklist for the hour before

```bash
# 1. Everything up and healthy
docker compose ps
curl -s http://localhost:8000/health/ready

# 2. Clean data
docker compose run --rm --no-deps migrate python scripts/reset_data.py

# 3. Accounts, rules, and the finished worked example
docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_demo.py
docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_example.py

# 4. Clear the sign-in counters after all that seeding
docker compose exec redis sh -c \
  "redis-cli --scan --pattern 'maanak:rl:*' | xargs -r -n1 redis-cli DEL"

# 5. Confirm all seven accounts can actually sign in
docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/check_demo_logins.py

# 6. Generate the label image for the live demonstration
docker compose run --rm --no-deps --user root -v "$PWD/api:/app" \
  --entrypoint python api scripts/make_sample_label.py
```

Then do section 4 to leave one inspection paused at review, and check by hand:

- [ ] Sign in as each role you plan to show, and sign out again
- [ ] No account asks for a six digit code
- [ ] `INSP-2026-000001` opens and shows its photograph, its readings and its findings
- [ ] The second inspection sits at officer review with its readings unconfirmed
- [ ] The report page opens and the public verification page answers for its reference
- [ ] The audit screen opens as the controller
- [ ] Open the audit screen as the reviewer as well, and read the refusal. It must be a
      sentence a person can read, never an internal code

That last one is worth rehearsing. A judge who asks "what happens if someone opens a screen
they should not" is handed the answer in one click.

---

## 7. Things to have straight before you are asked

Have these ready, because a sharp judge will find them anyway and it is far better to say
them first.

**The reader is unreliable on real packets.** Of fourteen photographs taken by ordinary
shoppers, six produced any reading at all and the net quantity came out of none of them.
Say the number. Then say the one that matters: across all fourteen, the number of faults
Maanak raised before a human checked was **zero**. A system that reads "14" where the packet
says "1 kg" and confidently opens a case would score better on a reading test and be far
more dangerous.

**None of the eleven legal interpretations is confirmed.** Nobody has checked them line by
line against a gazette notification. Every rule carries a "not confirmed" mark, and that
mark is printed on every report. This needs a lawyer, not a programmer.

**It is not hardened for the internet.** No HTTPS in this setup, no alerts, and no outside
security or accessibility audit. `docs/PROJECT_REPORT.md` section 19 lists the thirteen
things needed before real use, in order.

**Everything on screen is sample data** and says so. No real product, premises or person.

---

## 8. Where each file mentioned here lives

| File | What it is for |
| --- | --- |
| `api/scripts/seed_demo.py` | Accounts and rules |
| `api/scripts/seed_example.py` | The one finished worked example |
| `api/scripts/reset_data.py` | Throw away all application data |
| `api/scripts/check_demo_logins.py` | Confirm every published account signs in |
| `api/scripts/make_sample_label.py` | Write the label image to a file |
| `docs/DEMO.md` | The nine step story to tell |
| `docs/PROJECT_REPORT.md` | The whole project in plain words, with every figure |
| `docs/RUNNING.md` | Starting from a clean machine |
| `docs/TESTING.md` | Every check, its command, and what it proves |

All of these already exist in the repository. Nothing in this document adds or changes code.
