# Video script — ~3:00

Read at a normal pace. Every number here is measured. Screen directions in brackets.

---

**0:00–0:20 · Hook** [slide 1]

"In April, an AI coding agent deleted a company's production database in nine seconds.
Every agent ends a task the same way: 'Done.' The question nobody can answer is —
which of those dones are true?"

---

**0:20–0:45 · Problem** [slide 2]

"Sixty-six percent of developers say AI code is 'almost right but not quite' — it's their
number one frustration. Half of the patches that pass SWE-bench wouldn't be merged by real
maintainers. And research this month found agents passing tests by weakening the tests
themselves — deleting assertions, adding skips, changing the expected value. A green
checkmark no longer means correct."

---

**0:45–1:05 · Solution** [slide 3, then 4]

"This is Polygraph. Other tools guard what an agent is allowed to *do*. Polygraph guards
what it's allowed to *claim*. It lives inside IBM Bob, using four lifecycle hooks — and
the key idea is that truth comes from the *original* tests, not the tests the agent may
have edited."

---

**1:05–2:10 · Live demo** [recorded gate-on clip]

"I ask Bob to fix a ticket and commit.

Every action it takes is going into a hash-chained log stored outside the workspace — so
Bob can't quietly rewrite its own history.

Bob says done. The Stop hook fires and the verdict engine checks out the original test
suite from the baseline tag and runs it against Bob's code. Twenty-one passing, seven
failing. It also diffs the test files — and there it is: an assert was deleted from
test_cart.py.

Then it checks the claim sentence by sentence. 'Order.compute now passes after_discount' —
supported, the log shows that edit. 'SHOP-04 is fixed' — *not* supported. 'All twenty-eight
tests pass' — not supported.

Verdict: rejected. Bob tries to commit — blocked, exit code two. [point at the block]

I type 'continue.' The UserPromptSubmit hook injects exactly which evidence is missing, so
Bob knows what to fix rather than guessing. It fixes it properly, the original suite goes
twenty-eight for twenty-eight, verdict verified — and now the commit goes through."

---

**2:10–2:40 · Dashboard + numbers** [dashboard]

"The dashboard shows the review queue, every evidence card, and the full session timeline.

In our experiment, Bob was honest in all three recorded runs — every claim sentence checked
out. And Polygraph *still* rejected one of them: the ticket-02 fix was genuinely correct,
but the original suite came back twenty-four passing, four failing. A true claim about
unshippable work — exactly the thing a human reviewer waves through.

Ten commit attempts blocked. Zero unproven commits. Each verdict takes about three
seconds."

---

**2:40–3:00 · Close** [slide 8]

"AI made writing code nearly free. Trusting it is the new bottleneck.

Polygraph: Bob can't ship it until it's proven."

---

## Recording notes

- **Don't claim an ML model** — it isn't trained. There's no AUC number in this script.
- If `verify_chain` prints `TAMPERED` on camera, that's a malformed log line from
  development, not agent tampering. Either avoid showing it, or say the honest version:
  "a corrupt log is an unverifiable log, so it fails closed."
- The strongest 10 seconds in the video are the honest-but-rejected run at 2:10. Don't rush
  it.
