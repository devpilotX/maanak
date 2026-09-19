---
name: session-continuity
description: Survive session restarts without losing context. Maintains one durable, gitignored state file per project that records verified facts, standing decisions, exact runnable commands and outstanding work, then reads it first on every resume. Use at the start of any session in an unfamiliar or resumed project, before any task expected to run longer than a few turns, whenever the user says they restarted, lost the session, ran out of context, or asks "do you remember", and continuously during long tasks so a crash loses minutes rather than hours. Also use when handing work to another person or agent. Guards specifically against the stale-handover failure, where a state file exists, is trusted, and is wrong.
license: CC0-1.0
compatibility: Any environment with a writable project directory. No network, no dependencies. Git is used when present but is not required.
metadata:
  version: "1.0.0"
  author: session-continuity
  basis: "Failure modes observed in practice on resumed sessions, listed in section 1"
---

# session-continuity

A session ends without warning. The next one starts with no memory of it. Everything the
user paid for in the last session that lives only in the model's head is gone: what was
tried and rejected, why a number is what it is, which of the two plausible approaches was
already ruled out.

The fix is not a longer summary at the end. It is a file in the project that is written
during the work and read before it, and that is honest about which of its own statements
have been checked.

## When this skill is active

Apply it whenever any of these is true:

- The session is resuming work, or the user says they restarted, lost context, or asks
  whether you remember.
- You are about to start a task with more than a few steps.
- You are in a project you have not read yet in this session.
- You are about to end a turn having changed something.

It applies to any project in any language. Nothing in it is specific to one repository.

## 1. The failure modes this exists to prevent

Each of these has happened. The rules in section 3 map one to one onto them, and the
reason the rules look pedantic is that the cheap version of each rule failed.

**1.1 The state file existed and was stale.** A handover file recorded "106 checks
passing" and "nine screens unmeasured". Both had been true. By the time it was read the
real numbers were 134 and zero, because the session that fixed them updated the project's
own documentation and not the handover. An agent that trusted the file would have
reported false state confidently, which is worse than having no file, because no file
prompts a fresh look.

**1.2 A number was copied forward until nobody knew where it came from.** A count of "26
modules" appeared in two documents. The directory held 27. The number had been correct
when written and was never re-measured, only recopied.

**1.3 Inferred state was recorded as observed state.** A file said the local branch was
"ahead 14 commits". That came from a remote-tracking ref that had not been fetched for
days. Asking the remote directly showed local and remote at the identical commit. Nothing
was ahead.

**1.4 The environment had changed under the notes.** A state file said "no git, node or
npm on the host" and gave elaborate workarounds. In the next session all three were
present, because the shell was a different one. Following the notes would have meant
using slow workarounds for tools that were installed.

**1.5 A whole session of work sat uncommitted and undescribed.** Seven modified files and
three new ones, with no record of why they were not committed. A crash would have lost
work nobody could reconstruct, and the next session could not tell deliberate from
unfinished.

**1.6 Deliberate refusals were re-litigated.** A previous session declined to fabricate a
100 per cent accuracy figure, and declined to make a development signing key look like a
real signature. Neither refusal was written down as a decision. A fresh session, trying
to be helpful, will close exactly these gaps, because closing gaps looks like progress
and the reasoning against it is invisible.

**1.7 A command silently checked nothing.** A checker run from the wrong working
directory printed "no JavaScript under web/js" and exited zero. Recorded as "passing".
A command in a state file is only useful if the working directory and mounts are part of
the record.

## 2. The artifact

One file per project. Ask for nothing, create it yourself.

| | |
| --- | --- |
| Path | Project root, or the tooling directory if the project has one |
| Name | `_SESSION_STATE.md`, or match a name already in the project's ignore rules |
| Visibility | Never committed. Add the pattern to the ignore file if it is absent. |

Before creating it, look for one that exists. Names in use include `_HANDOVER.md`,
`HANDOVER.md`, `NOTES.md`, `CONTEXT.md`, `.agent/state.md`, `TODO.md`. Read what you
find and continue it rather than starting a second file beside it. Two state files
disagreeing is worse than one that is out of date, because neither is obviously the
current one.

Confirm the file is ignored before writing anything into it. A state file that gets
committed leaks working notes into the project's history, and on a shared repository it
will reach people the notes were not written for.

## 3. The rules

**3.1 Every claim carries its evidence and its date.** Not "51 checks pass" but "51
checks pass, `verify_security.py`, run 2026-09-19, exit 0". A claim you cannot attribute
to a command you ran is not a finding, and belongs in section 4.6 as an assumption.

**3.2 Never copy a number forward.** On resume, a recorded measurement is a claim about
the past. Either re-measure it or mark it stale. Prefer recording the command that
produces the number over the number, because the command stays true.

**3.3 Separate observed from inferred.** Write what a command printed. If you concluded
something from it, label the conclusion. `git status` saying "ahead 14" is observed; "the
remote is missing 14 commits" is inferred, and in the case above it was false. Where a
cheap authoritative check exists, use it and record that one instead.

**3.4 Re-detect the environment. Never trust the recorded list.** Tool availability,
shell, paths and container state are the fastest things to go out of date. Recording them
is still useful, as a hint about what to check, but the record is never the authority.

**3.5 Commands are recorded verbatim and runnable.** Full command, working directory, and
any mount or environment variable it depends on. No prose paraphrase, no placeholder the
next session has to guess at. If it must run from the repository root, say so, because
the same command from one directory down can pass while checking nothing.

**3.6 Decisions outrank status.** Status is cheap to re-measure; a decision costs an
argument to reconstruct. Record what was decided, what the alternative was, and why the
alternative lost. Mark the ones that must not be reopened without the user. This is the
single highest-value section and it is the one most often missing.

**3.7 Record refusals as decisions.** Anything deliberately not done goes in writing with
its reasoning: gaps left open on purpose, figures not claimed, work the user deferred.
Without this a later session reverses them while believing it is helping.

**3.8 Describe uncommitted work.** List the changed paths, what the change is for, and
why it is not committed. A diffstat is a good record. "Work in progress" is not.

**3.9 Write during, not after.** Update the file when something is decided, measured,
finished or discovered to be wrong. A file written only at the end is exactly the file
that does not exist when the session dies. The cost of an update is a few lines.

**3.10 Delete what is no longer true.** The file is a current-state document, not a log.
When a gap closes, remove it rather than appending "now fixed" beneath it. A file that
only grows becomes a file nobody reads.

**3.11 Keep it short enough to be read.** Two hundred lines is generous. If it is longer,
the detail belongs in the project's real documentation, and the state file should point at
it. Anything worth keeping permanently is not session state.

**3.12 Never put secrets in it.** No tokens, passwords, keys or connection strings with
credentials. Record how a credential is supplied, such as the environment variable name,
and never its value. Throwaway local fixtures are the one exception, and only when the
project already publishes them.

## 4. The template

Adapt the headings; keep the order. Nothing here is optional except sections that are
genuinely empty, which you delete rather than filling with "none".

```markdown
# <project> session state

Local, ignored, not published. Read before doing anything. Written continuously.
Last updated: <date, time, and what triggered the update>

## 1. What this project is
Two or three sentences. Enough to orient someone who has never seen it.
Root path. Repository URL. Language and stack.

## 2. Verified now
Only what was checked in the most recent session, each with the command and the date.
| Fact | How it was checked | When | Result |

## 3. Stale, needs re-measuring
Claims carried over from an earlier session that were not re-checked. Move a row up to
section 2 only after re-running the command.

## 4. Standing decisions, do not reopen without asking
| Decision | Alternative rejected | Why |
Include every deliberate refusal and everything the user deferred.

## 5. Commands
Verbatim, with working directory and mounts. Grouped by purpose.

## 6. Work in progress
Changed paths and why. Diffstat if the project uses version control.
Whether it is committed, and whether it is pushed, each verified rather than assumed.

## 7. Open questions for the user
Things blocked on a decision or a credential only they can give.

## 8. Traps
Project-specific behaviour that cost real time and will cost it again. Each with the
symptom, so it is recognisable, and the fix.
```

## 5. Session start

Do this before the first substantive action, and do not skip it because the user's
request sounds simple.

1. Look for a state file under the names in section 2. Read all of it.
2. Say plainly whether you have context. If the file is missing or thin, say you do not
   remember and are reconstructing. Never imply continuity you do not have. The user
   asking "do you remember" wants a straight answer, and a confident wrong one costs them
   the rest of the session.
3. Re-verify, by running commands, in this order: version control state, whether work is
   committed, whether it is pushed, what is running, what the environment provides. Use
   authoritative checks over cached ones.
4. Reconcile. Every disagreement between the file and reality is a finding: report it,
   then correct the file. In the case in 1.1 the file was wrong about nine screens and
   two check counts, and saying so was more useful than the rest of the summary.
5. Read section 4 of the file before proposing any work, so you do not propose something
   already rejected.
6. Only then start.

When no state file exists and the project is unfamiliar, reconstruct from the project
itself: recent version control history, uncommitted changes, ignored working files, the
test and CI configuration, and the project's own documentation. Then write the file. Do
not ask the user to re-explain what the repository already records.

## 6. During the session

Update the file at these moments, not on a timer:

- A decision is made, or an approach is rejected. Section 4, immediately, with the
  reasoning. This is the one that cannot be reconstructed later.
- A measurement is taken. Section 2, with the command.
- A command turns out to need a specific directory, mount or variable. Section 5.
- Something behaves unexpectedly and you work out why. Section 8.
- The user defers something or declines something. Section 4.
- A gap closes. Delete the row rather than annotating it.

Keep it to a few lines each time. An update that feels like a chore will be skipped, and
a skipped update is the whole failure this skill exists to prevent.

## 7. Session end

Before the final summary:

1. Re-read the file against what actually happened and fix every line that is now wrong.
2. Move anything not re-measured into section 3 rather than leaving it in section 2.
3. Confirm work-in-progress matches reality by running the status command again, not from
   memory.
4. Check section 4 covers every refusal, including refusals inside your own reasoning that
   you never said out loud.
5. Confirm no secrets are in the file.

Then write the summary for the user. The summary and the file have different jobs: the
summary is for a person who watched, the file is for an agent who did not.

## 8. Anti-patterns

| Do not | Instead |
| --- | --- |
| Trust the state file because it exists | Re-verify, and report every disagreement |
| Record a number without its command | Record the command; prefer it to the number |
| Write "all tests pass" | Name the suites, the counts, the date, the exit status |
| Write the file at the end only | Write it as you go |
| Append "fixed" under a closed gap | Delete the row |
| Keep a running log of every action | Keep current state, and keep it short |
| Paraphrase a command | Paste it, with its working directory |
| Leave a refusal unwritten | Record it as a decision with its reasoning |
| Say "I remember" after reading a file | Say what you read and what you re-checked |
| Start a second state file | Continue the one that is there |
| Assume pushed because committed | Ask the remote |
| Carry forward a tool list as fact | Re-detect, and treat the list as a hint |

## 9. Self-audit

Run through this before ending any session. Every answer must be yes, or the file is not
doing its job.

1. Could an agent with no memory of this session resume it from the file alone?
2. Does every claim in section 2 name a command and a date?
3. Is anything unverified sitting in section 2 instead of section 3?
4. Does section 4 record every rejected approach and every deliberate refusal, with
   reasoning a stranger would find persuasive?
5. Can every command in section 5 be pasted and run, from a stated directory?
6. Does section 6 match what the status command prints right now?
7. Is committed distinguished from pushed, each verified?
8. Are all closed gaps deleted rather than annotated?
9. Is it under two hundred lines?
10. Are there no secrets in it?
11. Is it ignored by version control, checked rather than assumed?
12. If the user asked "do you remember", does the file let you answer honestly and
    specifically rather than reassuringly?
