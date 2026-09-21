# Maanak project report

Everything about this project, written in plain words. If you have never seen the code, you
should still be able to read this from start to finish and understand what we built, why we
built it this way, what we measured, and what is still missing.

There is a list of words at the end. If a term is unfamiliar, it is explained there.

**Maanak is not a government service.** No authority runs it, nobody has approved it, and
it punishes nobody. Every legal decision it stores is stored against the name of the
officer who made it.

---

## 1. The whole idea in one page

An officer goes to a shop. He picks up a packet. He wants to know whether the packet has
everything printed on it that the law requires, and whether what is printed is correct.

Today he writes this on a paper form.

With Maanak he takes a photo instead. Then this happens:

1. Maanak looks at the photo and says whether it is good enough to read. If there is shine
   on the label, or it is blurry, or part of it is cut off, it says so in plain words while
   the packet is still in his hand.
2. Maanak reads the words on the label by itself and pulls out the values the law cares
   about, such as the price and the weight.
3. The officer looks at each value Maanak read. Next to each one, Maanak shows the exact
   piece of the photo it came from. The officer says yes, or corrects it, or rejects it.
4. Only the values the officer said yes to are used. Maanak then applies the rules and
   writes down its working, step by step.
5. Maanak makes a report and locks it. Nobody can change it afterwards, including the
   people who run the system.
6. Anyone in the world can check later that the report is real and unchanged, without
   being shown anything about the case.

That is the whole idea. Read the label, keep the proof.

---

## 2. The problem, with a real example

Say an officer checks a one kilogram packet of salt priced at 28 rupees. The law says the
packet must show the weight, the price, who made it, where to complain, and several other
things. It also says the price per kilogram must be correct.

Here is what goes wrong on paper.

### The proof and the decision get separated

The officer writes "price per kg wrong" on the form. Eight months later the trader
challenges it in front of a judge.

Now somebody has to prove it. Where is the packet? Thrown away. Where is the photo? Maybe
on somebody's phone, maybe nowhere. What exactly was printed on it? Nobody can say. What
sum did the officer do? Nobody wrote it down.

The finding might be completely correct and still fall apart, because the proof went one
way and the decision went another.

### Small sums cause big arguments

Price per kilogram is a division. 28 divided by 1 is easy. But real packets are 235 grams,
or 1.5 litres, or a box of 6 pieces of 50 grams each.

Do that division on a phone calculator and you get 119.14893617 rupees per kilogram. Write
down 119.14 and the trader says it should be 119.15. Now the case is about rounding instead
of about the label.

### A blank box can mean three different things

The form has a box for "consumer care details". The officer leaves it empty.

What does that mean?

- The packet did not print consumer care details at all. That is a real offence.
- The packet printed them, but on the back, and the photo only shows the front. That is not
  an offence. It means somebody needs to take another photo.
- The packet printed them, but the ink was smudged and the officer could not read them.
  That is also not an offence. It means nobody knows yet.

On paper all three look like the same empty box. In court, one of them is a case and two of
them are nothing.

**We built Maanak around this third problem**, because it decides whether the whole record
is worth anything.

---

## 3. Who uses it, and what each person does

Five kinds of people, and each one can do only their own part. This is not a rule we
invented. It is how a Legal Metrology office already works.

| Person | What they can do | What they cannot do |
| --- | --- | --- |
| Inspector | Open an inspection, take photos, check the values Maanak read, run the rules | Make the final decision. Cannot see other districts |
| Reviewer | Make the final decision, sign and issue the report | Change the photo or the officer's checked values |
| Controller | See everything in the state, open cases, read the full history | Edit the history. Nobody can |
| Rule administrator | Write a new version of a rule, test it | Approve their own version. Somebody else must |
| Administrator | Create accounts, set roles and districts | See case details outside their own area |

A sixth person matters too: **the shopper**. A shopper needs no account at all. See
section 7.

One rule is worth stating on its own. **A rule writer cannot approve their own rule.** Two
different people must be involved, the way two different people sign off on anything that
carries legal weight. We tested this. Trying to approve your own version is refused.

---

## 4. The two rules that decide everything else

Almost every decision in this project comes from these two ideas. They are not written in a
document and hoped for. They are built into the code and tested.

### Rule one: no proof is not the same as guilty

When Maanak cannot see something, it says which kind of "cannot see" it is:

| What is actually true | What Maanak answers |
| --- | --- |
| The packet really does not have it printed | **Not allowed.** This is a fault |
| The photo does not show that part of the packet | **Show me more.** Take another photo |
| It is in the photo but cannot be read | **I cannot tell.** Nobody knows yet |

Only the first one is a fault. There is no setting anywhere that makes the other two turn
into a fault. We did not leave this to a person to remember. The rule engine itself refuses.

**You can watch this happen.** Take one inspection. Before the officer checks anything, run
the rules:

- 7 rules answer "show me more"
- 3 rules answer "I cannot tell"
- **0 rules answer "not allowed"**

Now the officer checks the values. Nothing else changes. The photo is the same photo. Run
the rules again:

- 10 rules now apply
- 1 fault is found

The proof did not change. The checking did. That is the whole point.

### Rule two: the machine and the officer are two separate records

When Maanak reads a value off a label, it saves it as a guess, with a score for how sure it
is. That is the machine's record.

When an officer looks at that guess and says yes or no, that is saved separately. That is
the officer's record.

If the officer corrects the value, **we do not throw away what the machine read.** We save
the old value first, then the new one. Both appear on the final report. So anybody reading
the report later can see that the machine read "119.14" and the officer changed it to
"119.15", and when, and who.

And only values an officer checked can reach a rule. This is checked inside the rule engine,
not on the screen. Even if somebody wrote a new screen tomorrow that forgot to check, the
engine would still refuse.

---

## 5. Every step, from photo to report

### Step 1: take the photo

The officer opens a web page on his phone. The camera opens inside the page. There is no app
to download and no store to visit.

He can also attach a photo already on the phone, or one a shopper sent in.

### Step 2: check whether the photo is usable

Before anything else, Maanak measures the photo itself on eleven things:

| What we measure | Why it matters |
| --- | --- |
| Sharpness | A blurry photo cannot be read |
| Shine | A bright reflection hides whatever is under it |
| Bright patches burnt out | White areas where the detail is simply gone |
| Dark patches | Black areas where the detail is gone the other way |
| Overall brightness | Too dark or too bright and nothing reads |
| Contrast | Grey text on grey plastic reads badly |
| Size in pixels | A tiny photo has no detail to find |
| Tilt | Text at an angle reads worse |
| Framing | Part of the label outside the photo edge |
| Text size | Letters too small in the photo to be read |
| Where the file came from | A camera photo and a screenshot are different things |

Then it tells the officer what to fix, in words a person uses: "strong glare is covering
part of the panel". Not a score out of ten, and not an error code.

This matters because of when it happens. The officer is still standing in the shop. He can
move, change the angle, and take another photo. Finding out a week later that the photo was
useless means going back to the shop.

We also refuse photos outright if they are too poor. Of the 14 real shopper photos we tested
against, Maanak refused 5 as too poor to use. That is the correct answer for those 5.

### Step 3: lock the photo

The photo file is saved **exactly** as it arrived. We do not shrink it, sharpen it or
re-save it. The bytes stay the bytes.

Then we make a code from the file. This is a long string of letters and numbers worked out
from the contents. Change one dot in the photo and the code comes out completely different.

So if anyone ever asks "is this the same photo the officer took?", you work the code out
again and compare. If it matches, it is the same photo. If not, something changed.

We also write down who touched the file and when. And we never read the location out of the
photo's hidden data, because the officer should say where he was, not the camera.

### Step 4: read the label

A separate helper program does the reading. This matters for a simple reason: reading takes
about four seconds, and nobody should sit and watch a spinner for four seconds. The officer
carries on. The reading arrives when it is done.

The reader is Tesseract, a free label reader that has existed for years. We load both
English and Hindi. It tries the label several different ways, in different settings, and
keeps whichever attempt reads best by a measured score, not by a guess.

Section 11 is honest about how well this works. It is the weakest part of the project and we
say so.

### Step 5: tidy up the values

Reading gives us text. Text is not yet a number we can use.

"Net Qty. 235g", "NET WEIGHT: 235 gm" and "235 grams" all mean the same thing. So do
Devanagari digits. A box of "6 x 50 g" means 300 grams in total.

We turn all of that into one exact number with one unit. The maths is done in exact paise
and exact grams, never in the kind of rough numbers that drift as you add them up. If a sum
needs rounding, we round it the normal way, half up, and we print the step so anyone can
follow it.

### Step 6: the officer checks each value

This screen is the most important one in the project.

For each value, the officer sees the value Maanak read, **and next to it the exact piece of
the photo it came from**. Not the whole photo. The crop.

He then does one of three things:

- **Yes.** The value is right.
- **Correct it.** He types the right value. The old one is kept.
- **Reject it.** He gives a reason.

Nothing goes forward until he has done this. And, as in section 4, the engine enforces it.

### Step 7: apply the rules

Now the rules run, on the checked values only.

Each rule has a version number, and only a version somebody has approved can run. Every
finding records:

- which rule and which version
- why that version was the right one to use, given the date
- what values went in
- what sum was done, written out
- the line of law it is attributed to
- and whether that attribution has been confirmed against the government notice (see
  section 17)

### Step 8: make the report and lock it

Maanak takes a copy of everything as it is at that moment, and freezes it. Then it makes a
code from that frozen copy, the same way it did for the photo.

The PDF and the Word file are both made **from that same frozen copy**, so the two documents
cannot disagree with each other or with the record.

The database itself refuses to change a report after this. Not "the software refuses". The
database.

### Step 9: anyone can verify it

A report carries a reference and a short printed code. Anybody can type those two things
into a public page and get one of two answers:

- this report was issued and has not changed, or
- we have no such report

That is all. No product name, no shop, no officer, no finding. A trader can prove a notice is
genuine without the page telling a stranger anything about the case.

---

## 6. The eleven things we look for

These are the declarations the Legal Metrology rules require on a packet. Maanak looks for
all eleven.

| What | In plain words | Why a shopper should care |
| --- | --- | --- |
| Name and address of the maker or packer | Who to hold responsible | Without it there is nobody to complain to and nobody to prosecute |
| Common or generic name | What the thing actually is, such as "Iodised Salt" | A brand name alone can hide what you are buying |
| Net quantity | How much is inside, by weight, volume or count | This is the single most cheated declaration. A packet sold as 1 kg holding 900 g is theft repeated thousands of times |
| Month and year | When it was made or packed | Old stock sold as new |
| Retail sale price | The maximum price, marked as including all taxes | Charging above it is the most common complaint the helpline receives |
| Unit sale price | The price per kilogram or per litre | This is what lets you compare a 235 g packet against a 500 g one. Without it, comparing prices is guesswork |
| Consumer care details | A name, phone number or email to complain to | A complaint you cannot deliver is not a right |
| Country of origin | Needed for imported goods | You are entitled to know where a thing came from |
| Dimensions, where relevant | For goods sold by size | A pipe or a cloth sold short |
| Batch or code number | So one production run can be traced | When something goes wrong, this is what lets a recall find the right stock |
| Minimum letter height | The print must be big enough to read | A declaration printed too small to read is the same as not printing it |

Two of these deserve a closer look, because they are where most of the real harm sits.

**Net quantity and unit sale price work together.** Suppose a packet says 235 g and 28
rupees. The unit price should be 119 rupees 15 paise per kilogram. If the packet prints
119 rupees 14 paise, that is a wrong declaration. If it prints nothing at all, that is a
missing declaration. And if the packet actually holds 200 g rather than 235 g, no photograph
in the world will tell you, which is why Maanak says plainly that it cannot confirm net
quantity from a picture, and names the office that can weigh it.

**Minimum letter height is the one Maanak refuses to answer.** Section 8 explains why in
full. The short version: a photograph cannot give you millimetres.

---

## 7. What a shopper can do, with no account

Four things. No sign up, no password, no app.

| What you can do | What you give | What you get |
| --- | --- | --- |
| Read what must be printed on a packet | nothing | All eleven things above, in plain words, each with the line of law and whether we have confirmed it |
| Report a product | a photo and a description | A reference number to keep. Your phone and email are optional |
| Follow your report | the reference **and** the contact detail you gave | How far it has got. Never the inspection that followed |
| Check a report is genuine | the reference and its printed code | Whether it was issued and is unchanged. Nothing about the case |

Two of these are worth a closer look.

**Following your report needs two things, not one.** The reference alone is not enough. You
also need the phone number or email you gave. Otherwise anybody who found a reference on a
piece of paper could look up somebody else's complaint.

**We also say what we do not do.** This is on the page, in plain words, because looking
complete is less useful than being clear:

- We do not judge nutrition, ingredients, allergens or food safety. Not one of our rules
  comes from the food safety regulations. We give no dietary advice. That is **FSSAI's**
  work, and we name them.
- We cannot confirm net quantity from a photo. A photo shows what is printed. It does not
  show what is inside. Weighing it is the **state Controller of Legal Metrology's** work,
  and we name them.
- A barcode that scans is not proof that a product is genuine.
- For a general complaint, we point you to the **National Consumer Helpline on 1915** and to
  filing before a **consumer commission**.

---

## 8. Why we refuse to measure letter size

The law says the printed letters must be at least a certain height in millimetres.

**This cannot be worked out from a photo, and we will not pretend otherwise.**

Here is why. Hold your phone close to a packet and the letters fill a lot of the picture.
Step back and the same letters fill very little. The letters did not change size. Your
distance did.

To convert picture size into real millimetres you need something of known size in the frame,
like a ruler next to the label. Without that there is no sum to do. Any number we produced
would be invented.

So the check refuses:

- **With no measurement**, it answers "show me more" and says exactly what it needs: an
  officer's measurement with a proper instrument.
- **With a measurement**, it compares against the legal minimum, and it also uses the plus
  or minus the officer gave. If the officer measured 1.5 mm give or take 0.2 mm, and the
  legal minimum is 1.6 mm, then the true value might be above or below the line. So the
  answer is "I cannot tell", not a decision.

That last part is the bit people usually leave out. A measurement of 1.5 mm looks like a
clear fail until you notice the instrument is only accurate to 0.2 mm. We do not round that
away, because a decision that cannot survive being questioned is worse than no decision.

This is the clearest example of a habit that runs through the whole project: **Maanak would
rather say it does not know.**

---

## 9. How the software is put together

### The six parts

One command starts all six. On a normal computer they used about 693 MB of memory together
at the busiest moment, while reading a label.

| Part | What it does |
| --- | --- |
| The main program | Takes requests from the browser, holds all the rules and logic |
| The helper | Reads labels in the background, so nobody waits |
| The database | Stores everything. PostgreSQL |
| The queue | Holds the list of labels waiting to be read. Redis |
| The file store | Holds the photos, locked with a key. MinIO |
| The web server | Sends the pages to the browser. nginx |

There is a page that reports whether each of the six is healthy, one by one. If any single
one is unwell, the page says the system is not ready, and names which part.

### Why one program instead of many

Splitting a system into many small services is fashionable. We did not do it. With a team
this size and a workload this size, it would add a lot of moving parts and network calls to
solve a problem we do not have.

Instead the one program is kept in strict layers, and the layers only run one way:

- The **routes** layer handles the web request and holds no logic at all.
- The **checking** layer refuses a request that does not look right.
- The **service** layer holds all the actual behaviour.
- The **table** layer talks to the database.
- The **rule** layer holds the lists of allowed values and the allowed steps.

That last one is worth explaining, because it prevents a whole class of bug. The list of
allowed values lives in **exactly one place**. From that one list we generate both the
database rules that refuse bad data and the words the browser shows a user. So the database
and the screen cannot drift apart and start disagreeing. They read the same list.

### The browser side

Plain HTML, plain CSS, and plain JavaScript. No framework, no build step, nothing to compile.

And no script from any other website. We tell the browser to load nothing from outside, and
to run no code written inline in the page. This makes a whole family of attacks impossible
rather than unlikely.

This is checked rather than claimed. We found one small inline style left in the officer
screen, precisely because the browser refused it.

### Things that are true no matter what

A few promises that hold everywhere in the system:

- **Out of your area means "not found", not "not allowed".** If you ask for a record from
  another district, you get 404. We do not say "you cannot see this", because saying that
  would confirm the record exists. The filtering happens inside the database question, not
  afterwards on the results.
- **The history can only be added to.** The database has a trigger that refuses any attempt
  to change or delete a history entry. So somebody with full control of the application
  still cannot rewrite what happened.
- **Each history entry is linked to the one before it** by a code worked out from both. So
  you cannot quietly remove entry 40 out of the middle. We tested this by forging an entry
  on purpose. The check caught it and named the exact entry number that did not add up.
- **Money and weights are exact.** Never the kind of number that drifts.
- **Reports, served notices and photo records cannot be changed.** By database trigger.
- **Logging in uses only a cookie.** There are no long-lived access keys anywhere in the
  design, so there is nothing to steal from a phone or copy out of a log file.
- **A request cannot set a field we did not ask for.** Every request is checked against an
  exact list, and anything extra is refused outright.

---

## 10. How we keep the record honest

This section collects the things that exist purely so the record can be trusted later.

**The photo cannot be swapped.** Its code is saved at upload. Section 5, step 3.

**The machine's reading cannot be quietly overwritten.** A correction keeps both. Section 4.

**The report cannot be edited.** Frozen, coded, and protected by the database. Section 5,
step 8.

**The history cannot be edited or thinned out.** Add-only, and each entry linked to the last.
Section 9.

**The rules cannot be changed behind your back.** Each rule has a version number, and a
finding records exactly which version ran. If somebody approves a corrected version next
year, old reports still show the rule that actually ran at the time.

**Who did what is always recorded.** Every decision carries the name of the person who made
it. Maanak decides nothing on its own.

**A wrong report can be corrected without hiding the first one.** The original stays. The
correction is a new record that points at it.

---

## 11. How well the label reading actually works

This is the weakest part of the project. We are going to be completely straight about it,
because pretending otherwise would be the one thing that could sink the whole idea.

There are two tests. The second one is the honest one.

### Test one: labels we made ourselves

We generate a clean label with ten known values on it. Then we damage it eight different
ways and see how many values still come out right:

| How we damaged it | Right out of 10 |
| --- | --- |
| Not at all | 9 |
| Shrunk to 1200 pixels wide | 9 |
| Shrunk to 900 pixels wide | 9 |
| Tilted 2 degrees | 9 |
| Tilted 6 degrees | 9 |
| Saved as a low quality JPEG | 9 |
| Slightly blurred | 9 |
| On a white background | 9 |
| **Total** | **72 of 80, which is 90 per cent** |

Now look at the failures. All eight are **the same failure**. The reader returns *lodised*
where the label says *Iodised*.

Why? In most plain fonts, a capital I and a lowercase l are the **same shape**. Not similar.
Identical. There is no information in the picture to tell them apart.

We could add a rule: if a word starts with a lowercase l and looks odd, change it to a
capital I. We did not, and we will not. That same rule would turn *Lemon* into *Iemon*. So
instead we keep what was read and tell the officer that these two letters are confusable
here. He can see the crop. He knows it says Iodised. He corrects it in one click.

### Test two: real photos taken by real shoppers

This is the hard test, and this is the number that matters.

We took 14 real photos of Indian packets that ordinary people uploaded to Open Food Facts, a
public database. For each one, the person had also typed in the weight. So we had a right
answer to score ourselves against.

Results:

| What we asked | What happened |
| --- | --- |
| Photos that gave us any value at all | **6 of 14** |
| Total values found across all 14 | 10 |
| Photos refused as too poor to use | 5 |
| Net quantity read correctly | **0 of 12 that had an answer to check** |

Net quantity came out of **none of them**. Not one.

We spent real time on why. Here is the clearest case. One photo is a close crop of a salt
pouch. It plainly shows **"NET QUANTITY: 1 kg"** in large bold type. A person reads it
instantly. All seven of our reader settings return either nothing or nonsense.

So we cropped the photo down to just those words and tried again with no clever processing at
all. It read **"NET QUANTITY:"** exactly right.

That changes the diagnosis completely. The reader **can** read this print. What defeats it is
being handed a whole curved packet at once and asked to work out, in one pass, which parts
are pictures, which are Hindi, which are English, and which are just plastic texture.

The value itself is harder still. Even cropped tight, "1 kg" comes out as "14", "1%", "ig" or
"1K", because the k and g sit so close together in that squeezed font.

### Three things we tried that did not work

We are recording these so nobody repeats them.

**Boosting contrast before reading.** We added two extra reader settings that stretch the
contrast and double the size. Measured over all 14 photos, the end result changed **not at
all**: same 10 values, same 6 photos, still zero net quantities. Worse, on the salt crop it
turned 0 words of output into 68 words of confident nonsense.

**Finding the text areas first.** We built something that looks for text-shaped blocks and
reads each one separately. It found **10** values, exactly the same as reading the whole
photo. Reading only the blocks was worse, 6 instead of 10, because the block finder loses
text that a whole-photo pass catches. Combining both did read net quantity from **1 of 14**,
which is the first time this project has ever read a weight off a real photo. But it costs
about twice the reading time, which would take the helper from about 17 photos a minute down
to about 9. One extra weight out of 14, no extra labels, for half the speed, is not a trade
worth making automatically. So we wrote it down instead of shipping it.

**Measuring at the wrong point.** Our first measurement of the contrast idea showed a big
gain. It was wrong. The measurement counted a hit if the number **or** the unit appeared
anywhere in the output, so a stray "g" in a field of nonsense scored as a success. Asked
properly, with the number and unit next to each other the way the extractor actually needs
them, every setting scores 0 of 14 with the contrast boost and without it. This mistake cost
most of a working session, and it is the reason we now insist that every measurement asks
the strict question.

### So why is this project still worth anything

Because of this number:

> Across all 14 real photos, including the 5 refused as too poor, the number of faults
> Maanak raised before an officer checked anything was **zero**.

The reader is unreliable on real packets. We know. **The design already assumes it.** A
reading that fails does not become a fault. It becomes "show me more" or "I cannot tell",
and it lands in front of a human being.

Compare that with a system that reads "14" where the packet says "1 kg" and confidently
opens a case. That system scores better on a reading test and is far more dangerous.

**There is no 100 per cent here and there is not going to be.** A photo of the front of a
packet does not show the back, and no amount of software fixes that.

---

## 12. Every test we run, and what each one proves

Every test prints each check with the value it measured, so a passing run reads as a
statement of what was checked rather than a number. Every figure below came from a run on
the current code.

### Does the logic work

| Test | Checks | What it proves |
| --- | --- | --- |
| Database shape | 14 | 30 tables, 184 indexes, 29 built-in refusals, and the history table refusing to be edited or deleted |
| Security basics | 51 | How passwords are stored and salted, that an unknown account takes as long to fail as a wrong password, that a tampered login is refused, and the full who-can-do-what table |
| Reading values | 62 | Weights and volumes parsed and converted exactly, Devanagari digits, multi-piece totals, Indian price formatting, rounding to the paisa, dates with their vagueness kept |
| The rule engine | 71 | No proof never becomes a fault, price sums with the steps recorded, letter height refusing to guess, band edges, date windows, only approved versions running |
| Logging in | 70 | First-administrator setup works once only, cookies set correctly, the anti-forgery check, session tokens rotating, reusing an old one killing the whole family, one-time codes against the official published test numbers |
| The photo pipeline | 56 | A blurred and glared photo refused with a reason, the saved file matching its code, duplicates refused, the helper reporting real progress, the crops sitting inside the photo |
| The whole office flow | 117 | Rules loading as drafts, approval refused before testing, self-approval refused, no faults before checking, a correction keeping the old value, every finding citing an approved version, an inspector unable to decide, another district returning 404, report codes, public checking leaking nothing |
| Complaints and cases | 86 | A public complaint with no account, follow-up needing both reference and contact, a complaint becoming an inspection and carrying the photo across, the controller hierarchy, a served notice frozen, and a forged history entry being caught by number |
| **Total across these eight** | **527** | |
| Small tests on the code | 321 | The sums, the labels, the state machines, the check digits, the one-time codes, and the wording |

### Does the screen work

| Test | What it proves |
| --- | --- |
| Browser basics, 60 checks | No serious accessibility problem on eight pages, one main heading per page, a skip link first in the tab order, every form field labelled, no sideways scrolling on a narrow phone, login and logout working through the real interface |
| Every page and screen, 140 checks | All 28 pages load and get their data, all 14 office screens scanned for accessibility with **zero** problems, no page showing a raw code or an "undefined" to a user, every list showing real rows, and no sideways scrolling at four different screen widths |
| The whole officer job, 44 checks | Driven through the real interface from an empty inspection to an opened case: a glared photo refused by name, a good one accepted, the helper waited for, eleven values confirmed, rules run, decision recorded, report issued, case opened |
| Accessibility across the public site | Zero problems on all 14 public pages, at both standard levels. Zero buttons smaller than the minimum tap size. Nothing that sticks to the screen and covers what you are reading |
| Links | Zero broken links. All 76 in-page jumps land on something real |
| Colour | Zero wrongly tinted surfaces, checked at three screen widths across 24 pages |
| Page frame, 14 screens | One header and one footer on every office screen, with the standing notice present on each |

Two of these exist because the standard tools do not cover them.

The **tap size** check exists because the usual accessibility scanner has no rule for it. We
wrote our own. It found utility links at 19 pixels, tick boxes at 13 by 13, and file buttons
at 21, all below the 24 pixel minimum. All were fixed.

Extending the accessibility scan to the **officer's own screen** found one critical and one
serious problem on the single most important screen in the whole application. It had been
missed because scans usually cover public pages only.

### Do the words work

| Test | What it proves |
| --- | --- |
| Writing check, 28 pages and 15 documents | No filler writing, no machine-writing habits, and no long dash anywhere. This project holds its own documents to a written standard, and the standard is a test rather than a promise |
| Error messages, 177 of them | Not one error a user reads names a database column or an internal field. This caught a real one: a user was told "Your role does not permit audit.read" |
| Permission names, 33 of them | Every permission the screen asks about actually exists. A name with a typo is never held by anyone, so the button it guards silently disappears for everybody with no error anywhere |
| Imports, 27 files | No file uses a helper it forgot to import. A missing import only breaks when that line runs, so one in a rare branch can sit broken for months |
| The finished documents | The text pulled back out of the generated PDF and Word file, and checked for the same faults. What the reader receives is checked, rather than only what we sent to the printer |
| Every endpoint, 98 of them | Each one is either reachable from a screen or written down, with a reason, as deliberately not reachable. **Zero unexplained.** So there is no forgotten endpoint sitting there unused |

### Can we recover, and is it fast enough

| Test | Result |
| --- | --- |
| Getting the data back, 11 checks | We saved a copy, wiped the system, put the copy back, then checked: the history adds up again, its last entry number, its code and its count all match what was recorded at save time, the add-only protection survived, every stored file still matches its code, and the report recomputes |
| The release package, 39 checks | The packaged copy extracts complete and every file in it compiles |
| Speed | 156 pages a second at the best setting, half of them answered within 14 milliseconds. Reading one photo takes about 3.6 seconds, so about 17 photos a minute |

### The seven automatic checks on every change

Every change to the code runs all seven before it can be merged, and again afterwards:

| Check | What it does |
| --- | --- |
| Style and types | Formatting, common mistakes, and type consistency across 88 files |
| Small tests | All 321, with a coverage report kept |
| Writing and wiring | The writing check, the import check, the permission-name check, the error-message check |
| Database upgrades | Upgrade, downgrade, upgrade again, then fail if the code and the database have drifted apart |
| Everything running together | The full six-part system, the live tests, the browser tests, then a filled workspace and every page and document check |
| Supply chain | Known holes in the libraries we use, a parts list, a scan for leaked passwords, and a scan of the finished container that fails on anything serious |
| The release package | Build it and check it extracts complete |

---

## 13. Speed and size

We measured this rather than guessing, because "will it cope" is a fair question and an
estimate is not an answer.

| What | Measured |
| --- | --- |
| Pages served per second, best setting | 156 |
| Half of requests answered within | 14 milliseconds |
| 95 out of 100 answered within | 19 milliseconds |
| Requests refused for going too fast | 0 out of 4,153 |
| Label readings per minute | about 17 |
| Time for one label reading | about 3.6 seconds |
| Memory used by all six parts at the busiest moment | about 693 MB |

Two honest notes.

**This number moves.** We ran the same test twice on the same computer and got 111 pages a
second once and 156 another time, because the computer was doing different other things. We
record both, because one number on its own would suggest a precision this test does not have.

**The reading speed is deliberate, not a limit we hit.** We only read two labels at once on
purpose. Label reading uses a lot of processor, and running more at once on a small computer
makes every single one slower without getting more done in total. On a bigger machine you
raise that number.

What we have **not** done: a long soak test over hours, and a test of many districts
uploading photos at the same moment.

---

## 14. Getting the data back after a disaster

A backup you have never restored is not a backup. It is a hope.

So we ran the whole thing:

1. **Saved a copy.** The database, all the photos and files, and the last entry number of the
   history with its code. 406 files, and the history recorded at entry 96 with 96 entries
   in total.
2. **Restored it** over the running system. This dropped the database and put it back from
   the saved copy, and put every file back.
3. **Checked it**, rather than assuming. Eleven checks, all passed:
   - the history adds up again from the start, all 96 entries
   - the last entry number matches what was recorded: 96 against 96
   - the last entry code matches, character for character
   - the count of entries matches: 96 against 96
   - the history table still refuses to be edited after the restore
   - the photo still matches the code taken when it was uploaded
   - all five other stored files still match their codes
   - the report recomputes to the same thing

That third step is the one people skip. Restoring is easy. **Proving the restored copy is
the same thing you saved** is the part that tells you the backup was real.

What is still missing here is scheduling it automatically and keeping the copy on a different
machine. Both are decisions for whoever deploys it, not code we can write for them.

---

## 15. Security, and what we have not done

### What is built

- **Passwords** are stored using a slow, salted method designed for passwords, so a stolen
  database does not hand over the passwords.
- **An unknown account takes as long to fail as a wrong password**, so nobody can work out
  which email addresses exist by timing the replies.
- **Logging in uses a cookie only.** The cookie cannot be read by page scripts. There are no
  long-lived access keys to steal.
- **A second cookie guards against forged requests** from another website.
- **Session tokens rotate.** Using an old one kills the whole chain immediately, which is
  what a stolen token looks like.
- **A second factor is available**, the six-digit code from a phone app. Our codes are
  checked against the official published test numbers, rather than against our own
  working.
- **Logging in is rate limited** per address and per account, and it fails closed. Too many
  tries and it stops, rather than letting them through.
- **Out of your area returns "not found"**, never "not allowed".
- **The history cannot be edited**, by anyone, enforced by the database.
- **Uploads are checked from the file's own bytes**, not from what the uploader claims the
  file is.
- **The browser is told to load nothing from outside** and to run no inline code.
- **Real-use mode refuses to start** while several settings are still unsafe. It checks what
  can be checked automatically and says plainly that it cannot check the rest.

### What is not built, stated plainly

- **No HTTPS.** Traffic is not encrypted in this setup. This is the first thing to fix.
- **No virus scanning on uploaded files.**
- **No managed password store.** Settings sit in a file.
- **No monitoring and no alerts.** Nobody gets woken up if it breaks.
- **No written incident process.**
- **No outside security review.** We have not been tested by anyone but ourselves.
- **No outside accessibility review**, and no screen reader has been run against the
  interface by a person who uses one. Automatic scanning finds what a tool can find. It does
  not tell you what using the thing feels like.
- **The report signing key is a clearly labelled development key.** We could have made the
  reports look signed. We did not, because a signature that means nothing is worse than no
  signature. It stays labelled until somebody connects a real signing service.
- **The second factor is offered, not required.**

---

## 16. Privacy, and what we store about people

We store as little about people as we can, and we say what we store.

| About whom | What we keep | Why |
| --- | --- | --- |
| Officers | Name, work email, role, district | To let them in and to record who decided what |
| Shoppers who complain | The photo and description. Phone or email **only if given** | To be able to reply. A complaint works with no contact detail at all |
| Traders and shops | Whatever the inspection records about the premises | It is the subject of the record |

A few decisions worth naming:

- **Contact details are optional for a shopper.** You can complain anonymously. You just
  cannot then follow the complaint, because following needs the contact detail as the second
  half of the key.
- **We never read the location out of a photo's hidden data.** The officer states where he
  was. A camera's guess is not evidence.
- **Following a complaint never shows the inspection.** You see how far your report has got.
  You do not see the case, the trader or the finding.
- **Checking a report reveals nothing.** Two answers only: issued and unchanged, or no such
  report.
- **There is no public sign up.** The first administrator is created once, through a route
  that then refuses to work again while any account exists. After that, accounts are made by
  an administrator.

---

## 17. The rules of law, and why none is marked confirmed

Eleven rule interpretations come with the software. **Not one of them has been checked, line
by line, against a government gazette notice.**

We are not hiding this. Every single rule carries a flag that says "legal authority not
confirmed", and that flag appears in three places:

1. on the rule itself
2. on every finding that used it
3. **printed on every report**

Some of the values are openly placeholders:

- The **minimum letter height** is a single number. The real minimum changes with the size of
  the front panel of the packet. A single number is wrong for most packets, and it is marked
  as a placeholder.
- The **lists of allowed units** come from ordinary shop practice, not from the schedule in
  the rules.

`docs/LEGAL_SOURCES.md` names every gap and gives the exact procedure to close it: find the
notice, check the wording, record the reference against the rule version, and have a second
person approve it. No code change is needed. That is the whole reason rules have version
numbers.

**Two separate claims.** What the rule engine does is tested and correct: it does the sums
right, it applies only approved versions, and it never turns missing proof into a fault.
Whether a particular line of law is quoted correctly is a different question, and the answer
today is "we have not checked". Those two things do not need to fall together, and this
project is careful never to let one be used as evidence for the other.

---

## 18. What can go wrong, and what we did about it

| Risk | What we did |
| --- | --- |
| Real packets read badly. 6 of 14 photos gave anything, and weight came from none | Built for a reader that fails. Faults raised before a human checked, across all 14: **zero** |
| Capital I and small l are the same shape, so "Iodised" reads as "lodised" | Tell the officer about the ambiguity. Never silently fix it, because the same fix turns "Lemon" into "Iemon" |
| No rule is confirmed against the gazette | Carry the doubt everywhere: on the rule, on the finding, and on the printed report |
| Letter height cannot come from a photo | Refuse to answer. Ask for a real measurement, then use its error margin too |
| A photo could be swapped later | Code the file at upload and check it any time afterwards |
| Somebody with full access could rewrite history | The database refuses, not the software. Entries are chained so a gap shows up |
| An officer could be blamed for a machine's mistake | Machine reading and human decision are separate records, and both appear on the report |
| A rule could be quietly changed to fit a case | Rules have versions, a finding records which version ran, and nobody approves their own |
| The setup is not hardened | Make the gaps checkable. Real-use mode refuses to start while settings are unsafe |
| Somebody might treat this as an official system | Say it is not, on every page and on every report |
| A legal decision needs an authority, not software | Maanak records. It never decides |

---

## 19. What is still missing before real use

This is a working system on one computer. It is not an approved production service. Here is
the full list, in order.

**Must happen first:**

1. An authority confirms every one of the eleven rule interpretations against the gazette,
   and records the reference against the rule version.
2. Turn on HTTPS, and set the three related settings: secure cookies, documentation page
   off, and the exact list of allowed host names.
3. Move the settings and passwords into a managed store.
4. Make the second factor compulsory instead of optional.
5. Either connect a real report signing service, or leave signing switched off. Do not imply
   a signature that does not exist.

**Then:**

6. Commission an outside security review.
7. Commission an outside accessibility review, including a real screen reader user.
8. Commission legal review of the rule wording.
9. Run acceptance testing with actual inspectors in actual shops.
10. Add virus scanning on uploads.
11. Add monitoring, alerts, and a written process for when it breaks.
12. Schedule the backups and keep a copy on another machine.
13. Replace the single letter-height number with the real table that varies by panel size.

Setting the real-use flag today refuses to start while several of the first five remain
undone. It checks what a program can check. It cannot check that a lawyer read the gazette.

---

## 20. What a finished report actually contains

A trader or a judge receiving the output should be able to check it without asking anybody
for help. Here is what is printed on it.

**The heading.** The report reference, the date it was issued, the officer who issued it, and
the office they belong to.

**What was inspected.** The product brand and name, the shop or premises, the date of the
inspection, and the reference of the consumer complaint if it started as one.

**The photograph's fingerprint.** The long code worked out from the image file. Anyone holding
the original file can work the code out again and see that it matches. The image itself stays
in the evidence record.

**Every value, twice.** For each of the eleven declarations, the report shows what the machine
read and what the officer decided. Where the officer corrected something, both values appear,
with the time and the name. Nothing is quietly replaced.

**Every finding, with its working.** For each rule: the answer, the line of law it is
attributed to, which version of the rule ran, the values that went in, and the sum that was
done. If the answer was "cannot tell" or "show me more", the report says which and why.

**The unconfirmed mark.** Printed on the face of the report, because none of the eleven legal
interpretations has been checked against a gazette notification. A reader is told this without
having to ask.

**What this is not.** That Maanak is not a government service, that it enforces nothing, and
that the decision belongs to the named officer.

**The verification block.** The report reference and a short printed code. Type those two into
the public page and it tells you whether the report was issued and whether it has changed. It
tells you nothing else, so a trader can prove a notice is genuine without a stranger learning
anything about the case.

The same report is produced as a PDF and as an editable Word file, both generated from the
same frozen copy, so the two cannot disagree with each other or with the record.

---

## 21. The stages an inspection passes through

An inspection cannot jump around. It moves through named stages, and every move records who
did it and when. Software that lets a record go anywhere is software nobody can audit.

| Stage | What it means | Who moves it on |
| --- | --- | --- |
| Draft | Created, nothing attached yet | Inspector |
| Evidence collection | Photographs are being added and graded | Inspector |
| Reading | The background helper is reading the labels | Nobody. It moves itself |
| Officer review | Every machine reading is waiting for a person | Inspector |
| Checks run | The rules have been applied to reviewed values | Inspector |
| Awaiting decision | Sent to a reviewer | Inspector |
| Decided | A person has recorded the conclusion | Reviewer |
| Report issued | The frozen, fingerprinted document exists | Reviewer |
| Case opened | A formal case has been started from the report | Controller |

Three rules about this list are worth stating on their own.

**You cannot skip review.** The rules will not run on a value nobody has looked at. This is
enforced inside the rule engine rather than on the screen, so no screen written in future can
forget it.

**You cannot decide on your own evidence.** An inspector collects and reviews. A reviewer
decides. The same person is not allowed to do both on one inspection.

**You cannot open a case without a report.** The case has to point at an issued report, and a
report cannot be edited once issued.

A consumer complaint has a shorter path of its own: submitted, triaged, then either converted
into an inspection or closed with a reason. When it is converted, the shopper's photograph
travels across as evidence rather than being taken again, and the complaint keeps its own
reference so the shopper can still follow it.

---

## 22. What it costs to run

A fair question, and "it depends" is not an answer.

**Software licences: nothing.** Every part is free and open source. Python, FastAPI,
PostgreSQL, Redis, MinIO, nginx, Tesseract, OpenCV, Pillow and Docker. No licence per officer,
per office or per district.

**Per packet checked: nothing.** This is the decision that matters most for cost. The label
reading happens on the office computer. It does not call out to a paid service, so the bill
does not grow when the number of packets grows. A cloud reading service charging a fraction of
a rupee per image sounds cheap until a state does two million inspections in a year.

**Hardware: one ordinary computer per office.** All six parts together used about 693 MB of
memory at the busiest moment, while reading a label. That is a normal desktop machine, not a
server room.

**Field devices: nothing new.** The officer uses the phone already in his pocket. The camera
opens inside the web page, so there is no app to buy, distribute, update or support.

**Storage.** Photographs are the only thing that really grows. A declaration panel photograph
is roughly 200 KB to 2 MB. Ten thousand inspections with two photographs each is somewhere
between four and forty gigabytes, which is an ordinary disk.

**What does cost money**, and we will not pretend otherwise:

- Somebody's time to confirm all eleven legal interpretations against the gazette.
- An independent security review.
- An independent accessibility review, including a real screen reader user.
- A certificate, and the work to turn on encrypted connections.
- Whatever the office already spends on people, which does not change.

The honest summary: running it costs close to nothing. Setting it up properly costs expert
human time rather than software.

---

## 23. How this would grow from one district to a state

The version in this report runs on one computer for one district. Nothing would have to be
rewritten to serve more, and here is what would actually change.

**Areas of responsibility already work.** District, state and national levels exist in the
data today, and an officer sees only records inside their own area. A controller sees their
state. This was built in from the start rather than added later, and the filtering happens
inside the database question rather than afterwards on the results. That is the difference
between a real boundary and a cosmetic one.

**Reading is the only part that needs more machines.** Everything else is fast. Serving pages
runs at about 156 a second on one computer, far more than an office needs. Reading one label
takes about 3.6 seconds, and we deliberately read only two at a time, because reading uses a
lot of processor and running more at once on a small machine makes every one slower. To read
more per minute you add more reading machines. They take work from the same queue, so adding
one is a setting rather than a code change.

**Rough arithmetic.** One computer clears about 17 labels a minute, so roughly a thousand an
hour. A district doing two hundred inspections a day with two photographs each needs four
hundred readings, which is under half an hour of reading spread across a working day. One
machine per district is generous.

**What we have not tested**, and would want to before promising anything:

- A long soak test running for days rather than minutes.
- Many districts uploading photographs at the same moment.
- How the database behaves after several years of records rather than a few hundred.
- Restoring a backup that is large rather than small.

**One thing that does not scale, on purpose.** The officer review step. Every value is looked
at by a person. That is the whole design and the reason the record is worth anything. Any plan
to handle more inspections needs more officers, not fewer.

---

## 24. Choices we made, and what we chose against

Most of these went the less obvious way, and each has a reason.

**One program in clean layers, rather than many small services.** Splitting a system into many
small pieces is fashionable and solves problems we do not have. It would add network calls,
more things to deploy and more ways to fail, all to serve one office. We kept one program and
were strict about its internal layers instead.

**Plain web pages, rather than a modern front-end framework.** No framework, no build step,
nothing to compile. This lets the pages refuse to load any code from outside, which makes a
whole family of attacks impossible rather than unlikely. It also means somebody can read the
page source in five years and still understand it.

**Reading on our own machine, rather than a cloud reading service.** A cloud service would
read real packets better than Tesseract does. We chose against it for three reasons: the
photograph is evidence and should not leave the office, the bill would grow with every packet,
and an office with a poor connection would stop working. We accepted a worse reader to keep
those three properties.

**Refusing to answer, rather than giving a confident number.** The easy version of this project
reads a label, applies rules and reports violations. It would demonstrate better. It would also
produce findings that fall apart the first time a trader brings a lawyer. We chose the version
that says "I cannot tell".

**Telling the officer about confusable letters, rather than correcting them.** We could add a
rule turning a leading lowercase l into a capital I, and our reading score would improve. The
same rule turns "Lemon" into "Iemon". We kept the honest reading and reported the ambiguity.

**Marking all eleven rules unconfirmed, rather than looking finished.** Flipping one flag would
make the system look complete and authoritative. It would also be a lie, printed on every
report.

**A clearly labelled development signing key, rather than a real-looking signature.** We could
have made the reports appear digitally signed. A signature that means nothing is worse than no
signature, so it stays labelled until somebody connects a real signing service.

**Answering "not found" for another district's record, rather than "not allowed".** Saying "you
are not allowed to see this" confirms the record exists, which is itself a leak. So the answer
is the same one you get for a record that does not exist.

**Building a text-region detector and then not shipping it.** We built something to find the
text areas in a photograph and read each one separately. Measured over fourteen real photos it
found exactly the same ten values as reading the whole photograph, for twice the reading time.
Combining both approaches read one net quantity where the simple approach read none. One extra
value out of fourteen for half the speed is not a trade worth making automatically, so it is
written down rather than merged.

---

## 25. Questions you may want to ask, with straight answers

**Does it work?** Yes, on one computer, today. One command starts it. The tests are in section
12 and those numbers came from a real run.

**How accurate is the label reading?** On labels we generate, 72 of 80 values. On real
photographs taken by shoppers, six of fourteen produced any value at all and the net quantity
came out of none. That second number is the honest one.

**Then how is this useful?** Because a failed reading does not become a finding. Across all
fourteen real photographs, the number of faults raised before a person checked was zero. The
system hands hard cases to a human instead of guessing.

**Is the legal part correct?** Unknown, and marked as unknown. None of the eleven
interpretations has been checked line by line against a gazette notification. Every rule carries
an unconfirmed mark and that mark is printed on every report. Closing this needs a lawyer, not
a programmer.

**Could an officer fake a finding?** He can record a wrong decision, as he can on paper, and his
name is on it. What he cannot do is change the photograph, remove the machine's original
reading, edit a report after it is issued, or delete anything from the history. Those are
blocked by the database itself, not by the software asking nicely.

**Could an administrator cover something up?** No. The history table refuses changes and
deletions at the database level, and each entry is linked to the one before it, so removing one
from the middle shows up. We tested this by forging an entry on purpose. The check caught it and
named the exact entry number that did not add up.

**What happens if the computer dies?** We save a copy of the database, all the files, and the
last entry of the history with its code. We have run the full drill: saved, wiped, restored,
then eleven checks confirming the restored copy holds the same history, the same evidence and
the same reports. What is still missing is scheduling it automatically and keeping the copy on a
different machine.

**Is it secure?** Partly, and the gaps are listed rather than hidden. Passwords are stored
properly, sessions use a cookie only, a second factor is available, and an out-of-area record
answers "not found". There is no encrypted connection in this setup, no virus scanning on
uploads, no monitoring, and no outside security review. Section 15 lists both halves.

**Who has reviewed the code?** Nobody outside the team. Seven automatic checks run on every
change and all seven pass, but the platform does not let an author approve their own work and
the automated reviewer ran out of its quota. Machine checks are not review, and we will not
call them that.

**Can a shopper really use it without an account?** Yes. Four services need no sign-up: read
what must be printed on a packet, report a product, follow that report, and check whether a
report is genuine. Following a report needs both the reference and the contact detail given, so
a found piece of paper is not enough to read somebody else's complaint.

**What stops this being used to harass a trader?** Every legal conclusion is recorded against a
named officer. Maanak decides nothing by itself, cannot issue a penalty, and says so on every
page and every report.

**Is any of the data real?** No. Everything in the demonstration is marked as sample data and
refers to no real product, premises, brand or person.

**Why should we believe the numbers in this report?** Because each one can be reproduced. Every
figure here was read off a run, and section 12 gives the command that produces it. The code is
public.

---

## 26. How we worked

Every single change went the same way, with no exceptions:

1. Open an issue that describes the problem, with a list of what "done" means.
2. Make a branch.
3. Change one thing. Not three unrelated things.
4. Run the checks on our own machine first.
5. Commit with a message that explains **why**, and not only what.
6. Push the branch. Never straight to the main code.
7. Open a merge request that links the issue and says what was tested.
8. Let all seven automatic checks run.
9. Read the whole difference, line by line.
10. Merge as a single tidy commit, then delete the branch.

Reading the difference back is not a formality. On the most recent change it caught two of
our own statements being stronger than the test behind them, and both were corrected before
merging.

**Two limits on review, stated plainly.** The automatic code reviewer reports that it has
run out of its quota. And the platform does not let the author of a change approve their own
change, so approval could not be satisfied from the account that wrote it. That means the
seven automatic checks are machine evidence, and **no second human has reviewed this code**.
We say so rather than implying a review happened.

---

## 27. How to run it yourself

You need Docker. Nothing else. No Python, no database, nothing installed on your computer.

```bash
cp .env.example .env
# open .env and replace every CHANGE-ME value, then
docker compose up --build -d
```

| What | Where |
| --- | --- |
| The application | http://localhost:8080 |
| Is it ready | http://localhost:8000/health/ready |
| The list of endpoints | http://localhost:8000/docs |
| The file store console | http://localhost:9001 |

The readiness page reports all six parts separately, and says "not ready" while any one of
them is unwell.

Two more commands fill it with something to look at. The first makes one account per role
and loads the starter rules, taking each through testing and approval using the **second**
rule administrator, because an author cannot approve their own. The second walks one case all
the way through:

```bash
docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_demo.py

docker compose run --rm --no-deps -e API_URL=http://api:8000 \
  --entrypoint python api scripts/seed_example.py
```

You get one connected example: a shopper complaint, an inspection, eleven values confirmed,
the rules run, a decision, an issued report, a case, and a served notice.

Worth clicking, in this order:

1. Sign in as the **rule author** and count the menu links. Then sign in as the
   **administrator** and count again. Four against nine. The menu is built from what your
   role can actually do.
2. As the **reviewer**, type the audit screen address straight into the browser. You are not
   allowed there. Read the refusal. It must be a sentence a person can read, never an
   internal code.
3. Open the **inspection** screen and look at one value with the photo crop beside it. That
   screen is the heart of the project.
4. Open the **reports** list and read the product name. It must read once, not twice.

`docs/TESTING.md` lists every test, the exact command, and what it proves. `docs/RUNNING.md`
covers a clean machine step by step. `docs/KNOWN_LIMITS.md` records both reading scores and
the reasoning behind them.

---

## 28. Words used in this report

| Word | What it means here |
| --- | --- |
| Declaration | One of the eleven things the law says must be printed on a packet |
| Net quantity | How much is actually inside: weight, volume or count |
| Unit sale price | Price per kilogram or per litre, worked out from the price and the quantity |
| Principal display panel | The main front face of a packet, the one a shopper sees on the shelf |
| Label reading | Software turning a picture of words into text. Often called OCR |
| Code, or fingerprint | A long string worked out from a file's contents. Change the file at all and the string changes completely, so it proves nothing was altered |
| Chained history | A record where each entry includes a code of the one before, so an entry cannot be removed from the middle without showing |
| Add-only | A table the database will let you add to but never change or delete |
| Frozen, or locked | Saved and then protected from change by the database itself |
| Rule version | One numbered reading of a line of law. A finding records which version ran |
| Finding | One rule's answer about one inspection, with its sum and the law it cites |
| Report | The frozen, coded document that gathers the findings for one inspection |
| Notice | The formal document served on a trader once a case is opened |
| District, or area | The part of the country an officer can see records for |
| The helper | The separate program that reads labels in the background |
| Container | A packaged copy of one program with everything it needs, so it runs the same anywhere |
| Accessibility | Whether the pages work for people who cannot see well, cannot use a mouse, or use a screen reader |
| Screen reader | Software that reads a page aloud for a person who cannot see it |
| Second factor | The six-digit code from a phone app, asked for after the password |
| Rate limit | A cap on how many times something can be tried in a period, to stop guessing attacks |

---

## 29. Who built it

devpilotX and catburglarX.

All the code is public at https://github.com/devpilotX/maanak under the Apache License 2.0,
which means anyone may read it, use it, change it and build on it.

The accessibility scanner we use for testing is included under `api/scripts/`, unchanged,
under its own licence. It is never sent to a user's browser and is not part of the running
application.
