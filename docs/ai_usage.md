# AI Usage Disclosure

YottaFlex allows AI tools and requires this disclosure. It describes what actually happened. Prompt 9 asked Claude Code to complete it, so Claude Code wrote it from the session record. The candidate should read it and correct anything that is wrong or has changed.

## The most important fact

This codebase was **generated almost entirely by an AI coding tool (Claude Code), operated by the candidate**, using the prompts recorded in `prompt_history.md`.

**Prompt 1 describes a different arrangement.** It says the person running the tool is helping a friend, who is the actual candidate, and that the work will be handed over. Prompt 5 is the operator's statement that they are the candidate and will submit this themselves. Both are kept word for word, and this file follows Prompt 5.

The session record does not say why Prompt 1 describes a friend. That is for the candidate to explain.

FAQ item 7 says: "The project must be your individual work. AI and public learning resources are allowed; implementation help from other people is not."

AI assistance is allowed. In the session record, Claude Code wrote all of the code, and the operator is the only person involved. Claude Code cannot verify anything outside that record.

## What Claude Code did

Claude Code wrote all of the following, and ran them:

- The schema, generator, anomaly injection, detector, reconciliation, evaluation and validation code.
- The automated tests and the Streamlit dashboard.
- All documentation in this repository, including this file.

It also made the design decisions in `decisions.md` itself, within the brief, and chose every threshold in `business_rules.md`.

## Where AI substantially accelerated the work

The whole project was built in one evening session. Nothing of this size would have been produced that fast by hand. The data dictionary, test suite and documentation were all drafted by AI.

## Where AI was relied on heavily

Everything above. No human wrote any of the code. The master prompt was itself created with ChatGPT. The candidate submitted the prompts and did not review the code line by line during the build.

## Which design choices came from AI

All of them, including the ledger, the bridge tables, the rule grain, the SLA values, the evaluation method and the negative-control test. The brief set the priorities and the technology preferences.

## How the work was checked during development

All of these were run by Claude Code, and results are in `validation_report.md`:

- Automated tests, including tests that corrupt data on purpose to prove the checks can fail.
- A clean-data negative control, and repeated runs on other seeds.
- A fixed-seed reproducibility run across two separate processes.
- A dashboard check in a real browser.
- A fresh setup from the handover archive.
- An independent review by a separate AI agent that was given the code but not the author's conclusions. It found 27 issues, including serious ones the tests and the perfect score had missed. See `decisions.md`.

Passing these shows that the system does what its documents say. It is not a human review.

## Known limitations of this process

- The same AI wrote the code, the test data, the labels and the tests, so its blind spots can appear in all four. This actually happened: the detector scored 1.0 while a bug hid late shipments, because the labels shared the flaw. The perfect detection score should be read with that in mind.
- The independent reviewer was also an AI. It did not replace a human review, and more issues may remain.
- The AI can state things confidently and be wrong. Every claim in these documents should be checked, not trusted.
- The business thresholds are reasonable assumptions, not figures from a real finance team.
- Understanding has to be built by the candidate. Reading AI output is not the same as being able to explain it.

## Later prompts

Most of the build came from Prompt 1. Prompt 4 was submitted after the software was finished, and only led to the revision described in `development_log.md`, Milestone 10. It is not the prompt the software was built from. Prompt 5 confirmed who the candidate is and led only to corrections in the documents.

## Other AI tools

The candidate states that they used two AI tools: ChatGPT to create the master prompt, and Claude Code to build the project (Prompt 11).

**Limitation:** the prompts sent to ChatGPT are not included, because they were not provided. FAQ item 6 asks for all prompts to every AI tool, so they should be added to `prompt_history.md` if they can be retrieved.

## What the candidate personally did

This section comes from the session record, so it lists only what that record shows, not everything the candidate may have done elsewhere.

**Recorded:**

- Created the master prompt with ChatGPT, and submitted the prompts in `prompt_history.md`, which set the requirements, priorities, technology preferences and constraints (Prompts 1, 4 and 11).
- Stated that they are the candidate and will submit this themselves (Prompt 5).
- Asked how to run the project (Prompt 2), and whether it was ready to submit (Prompts 3 and 8).
- Checked which names appear in the project, and had an unneeded company mention removed (Prompts 6 and 7).
- Chose to handle Git and publication themselves (Prompt 8).
- Asked Claude Code to complete these disclosure documents and prepare the zip (Prompt 9).
- Stated which AI tools were used (Prompt 11).

**Not recorded at the time this was written:**

- Reading or reviewing the code.
- Changing any code or document by hand.
- Running tests or checks. Every result in this repository was produced by Claude Code.
- Finding any bug. The bugs in `decisions.md` were found by the test runs and an AI reviewer.
