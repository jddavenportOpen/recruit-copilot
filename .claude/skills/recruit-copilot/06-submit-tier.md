# 06 — Submit tier

**Goal of this stage:** decide what this particular application costs to get wrong, and hold the
resume to a bar that matches.

**Done when:** the user knows which tier this employer is in, what bar that set, whether the
panel cleared it, and what the tool will and will not do next.

---

## The idea

Every other tool in this category treats applications as interchangeable units of volume. They
are not. Two applications with identical effort have wildly different downside:

- A **standard** employer is a repeatable event. A mediocre application costs you one rejection
  and you can apply again next quarter with a better one.
- A **reach** employer is close to one-shot. You get one read from that recruiting team this
  cycle, and a weak read is the read they remember. There is no undo, and the cost is not the
  rejection. It is that you spent your one shot at the company you actually wanted while your
  resume was still two revisions away from ready.

So the tier is not a label on the company. It is a statement about **the cost of being wrong**,
and the bar follows from the cost.

## The two bars

`aggregate.py` applies this, using the `company` field from stage 05.

| Tier | Bar | Constant |
|---|---|---|
| Reach | A **majority interview vote** (2 of 3) **AND** `panel_avg >= 90` | `REACH_THRESHOLD = 90` |
| Standard | `panel_avg >= 70` | `DEFAULT_THRESHOLD = 70` |

The reach bar is deliberately a conjunction, and that is the most important design decision in
this file. A high average alone is not enough, because an average can be carried by one
enthusiastic judge. Two votes alone are not enough, because two judges can wave through a resume
that is thin everywhere. Requiring both means a reach application has to be good *and* has to
convince more than one kind of reader, which is exactly what actually happens at a company that
gets thousands of applications.

The gap between 70 and 90 is intentionally large. There is no middle tier, because a middle tier
would immediately become the place everything gets filed.

## The tier list

The `REACH` set lives in `skills/resume-grader/scripts/aggregate.py`. As shipped:

```
anthropic, openai, google, google deepmind, deepmind, meta, microsoft, apple, nvidia,
xai, mistral, cohere, scale ai, databricks, stripe, mckinsey, bcg, bain
```

Matching is on a normalized company name — exact, or the name followed by a space or a comma, so
"Google, Inc." matches and "Googleplex Ventures" does not.

**This list is a starting position, not a claim about which companies are good.** It is the
author's reach set. Yours is different, and it should be — a specific 40-person startup you have
wanted to work at for three years is a reach employer for you and belongs in the list; a famous
company you would take only if nothing else worked is not, whatever its logo is worth.

## The never-auto rule

**This repo has no submit path. Not for reach employers, not for standard ones, not behind a
flag.** That is the state today and it is deliberate; the invariant is not "we haven't built it
yet."

The reasoning is the same arithmetic as above, run to its end. Automated submission is only ever
attractive at volume, volume is only ever cheap at standard employers, and the moment a tool can
submit at standard employers the reach list becomes a config value standing between a user and
their own worst instinct at 1am. Every spray-and-pray product in this category began as a careful
one with a threshold.

There is also a simpler reason: the last human check is the only one that can catch the failure
no gate here can. Stage 04 proves a machine can read the page. Stage 05 proves three judges would
advance it. Neither can prove a claim on it is **true**. Only the person whose name is at the top
can do that, and asking them to do it takes fifteen seconds.

**If you fork this and add submission anyway** — which is a legitimate thing to want, inherit the
policy rather than inventing one:

1. Keep reach employers permanently manual. This is the line worth not crossing.
2. Gate any automated send on `overall_pass == true` from a **complete** panel, not on a score
   you computed.
3. Gate it on both machine gates green, from the same build that produced the file being sent.
4. Log every send to the outcome ledger at the moment of sending (stage 08), not afterwards from
   memory.
5. Put a rate limit on it, and make the limit visible in the UI. A number the user has to look at
   is worth more than a number in a config file.

## Retuning, with the reasoning for each constant

All four live in `aggregate.py`. Change them knowingly.

| Constant | Ships as | Raise it when | Lower it when |
|---|---|---|---|
| `REACH_THRESHOLD` | 90 | Never, really: 90 is the top band on the outcome-anchored scale, and a reach bar below "strong yes" is not a bar | You have outcome data showing 85s converted at reach employers. That is a real reason. Nothing else is. |
| `DEFAULT_THRESHOLD` | 70 | Your ledger shows sub-80s never got a reply. This is the most defensible tuning move in the file | You are early in a search and need volume to learn from. Say out loud that you are trading quality for data |
| `ADVANCE_FLOOR` | 85 | You see personas voting yes and scoring 60s, so the coupling is papering over bad scoring rather than correcting compression | Almost never. Below 85 it stops correcting the failure it exists for |
| `REACH` set | 18 companies | Any employer whose rejection you would actually feel | Any employer on it you would not rearrange a week for |

The one thing not to do is change a threshold to make a specific resume pass. That is not
tuning, it is moving the goalposts with the score on the board, and the ledger in stage 08 will
eventually make it visible anyway.

Next: [`07-apply.md`](07-apply.md).
