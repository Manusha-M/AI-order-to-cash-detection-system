# Prompt History

FAQ item 6 requires all prompts submitted to every AI tool. This file holds what is available.

## How this file was made

The Claude Code prompts below were exported by a script from the tool's own session record on the development machine, so the text and timestamps are exact and were not retyped. Only tool wrappers were removed. The prompts were typed by the person operating the tool, who states in Prompt 5 that they are the candidate. Prompt 1 says a friend is the candidate, and is kept as submitted. The prompts include the operator's local file paths and the name of their company, and are unedited because the requirement is for the full prompt history.

AI responses are optional under the FAQ and are not included.

## Which prompt did what

- **Prompt 1** is the prompt the software was built from.
- **Prompts 2 and 3** are short questions asked after the build.
- **Prompt 4** was submitted after the software was finished, and led only to the revision in `development_log.md`, Milestone 10. Its last line asks for it to be stored as the prompt used to create the software. That was not done, because it would not be true.
- **Prompt 5** answers Claude Code's question "Who is actually submitting this?". It led only to corrections in the documents.
- **Prompts 6 to 8** are short follow-up questions. Prompt 7 led to one line of `final_audit.md` being reworded.
- **Prompt 9** asked Claude Code to complete the disclosure documents and prepare the zip.
- **Prompts 10 and 11** state which AI tools were used.

## Claude Code (development machine)

### Prompt 1: 2026-10-30 20:18:38 IST

`````text
@"C:\Users\Asus\Documents\YottaFlex Project\Problem statement.txt" @"C:\Users\Asus\Documents\YottaFlex Project\YottaFlex AI Candidate Project Submission Guidelines.pdf" @"C:\Users\Asus\Documents\YottaFlex Project\YottaFlex AI Candidate Project-FAQ.pdf"


# YOTTAFLEX AI — COMPLETE CLAUDE CODE MASTER PROMPT
## Order-to-Cash Revenue Leakage & Process Delay Detection System

### ROLE AND OBJECTIVE

You are Claude Code, acting as an experienced Python software engineer, SQL/data architect, business-process analyst, quality assurance engineer, and technical reviewer.

Your objective is to help develop a technically correct, reproducible, professionally documented, and executable solution for the YottaFlex AI Candidate Project Challenge.

The project will initially be developed in a **local Windows environment** and handed over to the actual candidate, who will independently run, inspect, understand, modify where appropriate, validate, and publish the project from their own computer and GitHub account.

You are not authorized to submit the project, publish code, or interact with personal or company GitHub accounts.

Prioritize:
1. Exact compliance with the problem statement.
2. Correct relational data modeling.
3. Deterministic synthetic data generation.
4. Traceable business logic and exception detection.
5. Reliable reconciliation and reproducibility.
6. Measurable evaluation results.
7. A clear and useful analytical interface.
8. Clean, maintainable Python/SQL code.
9. Complete local reproducibility and handover documentation.
10. Honest authorship, AI disclosure, and candidate review.

Avoid unnecessary complexity and generic, over-engineered AI-generated application patterns. The quality of the solution should come from sound engineering choices, independently verified behavior, clear explanations, and genuine technical understanding.

---

# 1. ABSOLUTE RESTRICTION — NO GITHUB OR EXTERNAL PUBLICATION

**THIS IS A LOCAL DEVELOPMENT AND HANDOVER TASK ONLY.**

The person providing this development environment is helping a friend prepare for the challenge. The eventual candidate owns the submission process.

### Strictly prohibited actions

Under no circumstances may you:

- Push anything to the current user's personal GitHub.
- Push anything to any Nevora GitHub account, organization, or repository.
- Create a repository under the current user's personal or Nevora accounts.
- Use existing GitHub authentication or credentials.
- Run `gh auth login` or `gh repo create`.
- Run `git push`.
- Configure a Git remote pointing to any existing account.
- Deploy to Vercel, Netlify, Render, Railway, or any other external hosting platform.
- Upload the project to external storage or cloud services.
- Read or reuse personal GitHub tokens, SSH keys, or other unrelated credentials.
- Modify global Git settings.
- Publish project files, documentation, or datasets anywhere.

Do not even initialize a Git repository or create commits in this development workspace unless specifically authorized later.

### What you ARE allowed to do

You may:

- Create and edit files inside the explicitly designated local project folder.
- Create a local Python virtual environment.
- Install necessary free/open-source dependencies in that environment.
- Create SQLite databases locally.
- Run the synthetic-data generator.
- Run SQL queries and Python scripts.
- Run the application on localhost.
- Execute tests and validation checks.
- Generate local reports and documentation.
- Prepare a clean project archive for handover.

Do not use unrelated local projects, credentials, company resources, or personal files.

### Final GitHub ownership

The actual candidate will:

1. Receive the project files.
2. Review and understand the implementation.
3. Run the project on their own laptop.
4. Make any necessary independent changes.
5. Validate its behavior.
6. Set up their own Git identity and GitHub repository.
7. Make truthful, meaningful commits reflecting actual work.
8. Push the project to their own public repository.
9. Submit the link through their registered recruitment email.

Your task ends at **local project completion, verification, and handover preparation**.

Never claim that a GitHub submission or deployment has occurred.

---

# 2. TIME CONSTRAINT — CRITICAL

**Confirmed challenge deadline: October 31, 2026, 10:00 PM IST.**

Reference planning time: October 30, 2026, 8:00 PM IST.

At the start of your session, determine the actual current time and calculate the remaining time until the deadline.

Do not assume the original 26 hours remain.

Because the finished files must be transferred to another laptop and validated by the candidate, prioritize finishing the local project several hours before the official submission deadline.

Target local handover no later than **October 31, 2026, 6:00 PM IST**, if feasible.

Use the available time intelligently:

- Deliver a working minimum end-to-end solution first.
- Implement required data scale and anomalies before optional UI enhancements.
- Prefer proven, lightweight dependencies.
- Test each major component as it is implemented.
- Reserve time for reproducibility and portability checks.
- Never let a decorative feature delay mandatory work.

If the remaining time becomes short, preserve working business logic, validation, and documented outputs before UI polish.

Work autonomously within the local folder. Ask questions only for genuinely blocking decisions or actions requiring approval.

---

# 3. READ AND UNDERSTAND THE SOURCE MATERIALS

The challenge documents are:

- `Problem statement.txt`
- `YottaFlex AI Candidate Project Submission Guidelines.pdf`
- `YottaFlex AI Candidate Project-FAQ.pdf`

Locate and read these files completely in the local workspace.

If a file is missing, report the exact missing file. Do not pretend you have inspected it.

If PDFs cannot be read directly, use an appropriate local extraction method.

Before building, create a concise requirement traceability matrix containing:

| Field | Meaning |
|---|---|
| Requirement ID | Unique identifier |
| Source | Document and relevant section |
| Description | Specific requirement |
| Priority | Mandatory or optional |
| Implementation | File/module responsible |
| Verification | How correctness is demonstrated |
| Status | Not started / In progress / Pass / Partial / Fail |

Preserve the source requirements and distinguish them from additional engineering choices or assumptions.

Do not change business requirements to fit a convenient framework.

---

# 4. BUSINESS PROBLEM

Build an end-to-end **Order-to-Cash Revenue Leakage and Process Delay Analysis System**.

The system must track:

Account → Quote → Sales Order → Shipment/Fulfillment → Invoice → Payment → Dispute.

Its objectives are to:

- Identify revenue leakage.
- Detect financial discrepancies.
- Track process delays.
- Measure receivables and aging.
- Expose abnormal business states.
- Preserve transaction and lifecycle history.
- Explain exceptions using underlying evidence.
- Produce measurable outputs and evaluation metrics.

The primary actors include:

- Customer/prospect
- Marketing/sales operations
- Support agent
- Analyst
- System administrator

This is primarily a data engineering, relational modeling, and business analytics challenge.

Do not prioritize generic CRUD screens, authentication, or decorative features over the analytical core.

---

# 5. RECOMMENDED TECHNOLOGY STACK

The developer is most comfortable with Python, SQL, and data engineering.

Prefer:

- **Python 3.11+** for orchestration and business rules.
- **SQLite** for relational data storage.
- **SQL** for business queries and reconciliation.
- **Pandas**, only where helpful for analysis and export.
- **Streamlit** for a lightweight interactive dashboard.
- **Pytest** for automated validation.
- Python standard-library modules wherever practical.

Use a small dependency set compatible with a Windows laptop.

Avoid:

- Docker requirements.
- Cloud databases.
- Paid APIs.
- Microservices.
- Redis, Kafka, or distributed systems.
- Large machine-learning frameworks.
- Unnecessary AI APIs.
- Complex frontend build systems.

The problem statement does not require machine learning.

A deterministic, explainable rules engine is the preferred foundation.

If a UI can be completed without threatening the core, implement a polished Streamlit dashboard.

Otherwise deliver a strong CLI and reporting system with clear outputs.

Explain and document the final stack decision.

---

# 6. PROJECT ARCHITECTURE

Create a modular but practical structure, such as:

```text
yottaflex-o2c/
│
├── app/
│   └── dashboard.py
│
├── src/
│   ├── config.py
│   ├── database.py
│   ├── generator.py
│   ├── lifecycle.py
│   ├── anomaly_injection.py
│   ├── detector.py
│   ├── reconciliation.py
│   ├── evaluation.py
│   └── validation.py
│
├── sql/
│   ├── schema.sql
│   └── analytics.sql
│
├── tests/
│   ├── test_generator.py
│   ├── test_integrity.py
│   ├── test_lifecycle.py
│   ├── test_financials.py
│   └── test_detection.py
│
├── data/
│   └── sample/
│
├── outputs/
│
├── docs/
│   ├── data_dictionary.md
│   ├── architecture.md
│   ├── business_rules.md
│   ├── decisions.md
│   ├── validation_report.md
│   ├── reproducibility.md
│   ├── development_log.md
│   ├── ai_usage.md
│   └── prompt_history.md
│
├── scripts/
│
├── README.md
├── HANDOFF.md
├── requirements.txt
├── .gitignore
└── .env.example
```

You may simplify this layout if justified.

Avoid empty placeholder modules.

Only introduce files that have actual responsibilities.

Use relative paths and portable configuration. Never hardcode the current user's Windows username or absolute directory paths.

---

# 7. REQUIRED DATA MODEL

Implement all eleven source-required entities:

1. Account
2. Quote
3. QuoteLine
4. SalesOrder
5. OrderLine
6. Shipment
7. Invoice
8. InvoiceLine
9. Payment
10. Dispute
11. StatusEvent

Add support tables such as ShipmentLine and PaymentAllocation when needed for correct modeling.

For every field document:

- Data type
- Required or optional
- Allowed values
- Units
- Validation rule
- Uniqueness constraint

For every relationship document:

- Primary key
- Foreign key
- Cardinality
- Optionality
- Lifecycle implications
- Effective-date constraints where relevant

Use explicit bridge tables for many-to-many relationships.

Enforce foreign-key constraints.

Store status transitions as historical events.

Do not overwrite history.

Preserve valid references even when injecting intentional business anomalies.

Use exact monetary representations, such as integer minor units or Decimal, and document the currency assumption.

---

# 8. SYNTHETIC DATA GENERATION

Implement a deterministic configurable generator.

**Fixed seed: `20261022`**

Support two generation modes.

### Starter dataset

A small dataset that runs quickly and includes:

- Complete entity relationships
- Valid workflows
- Mandatory anomalies
- Representative normal cases
- Boundary cases

### Full dataset

Meet the problem statement's baseline:

- 10,000 Quotes
- 7,000 Orders
- 8,000 Invoices
- 15,000 Payments/Events

Document the exact interpretation of "Payments/Events" and the counts generated for each table.

If feasible, generate 15,000 payment records plus the necessary independent status events; otherwise use a defensible documented interpretation.

Use deterministic ID conventions:

```text
QTE-2026-000001
SO-2026-000001
SHP-2026-000001
INV-2026-000001
PAY-2026-000001
DSP-2026-000001
```

Apply equivalent consistent IDs to other entities.

Generate parents before children.

Use consistent foreign keys.

Use realistic distributions for:

- Account activity
- Quote acceptance/rejection
- Order quantities
- Payment terms
- Fulfillment delays
- Invoice timing
- Partial shipments
- Multiple invoices per order
- Partial payments
- Overdue balances
- Dispute rates

Generate legitimate records first and then inject deliberate labelled anomalies.

Do not independently randomize totals, account balances, or other derived values.

All derived outputs must be computed from source transactions.

Ensure that generation is deterministic across repeated executions with the same seed.

Use stable timestamps, ordering, exports, and numeric formatting.

---

# 9. MANDATORY NEGATIVE SCENARIOS

Implement all five explicitly required scenarios:

### A. Invoice exceeds fulfilled quantity

Create a traceable invoice-line overbilling case.

Detection must compare billed quantity against legitimate fulfilled quantity and identify the excess.

### B. Payment allocated twice

Model a payment being incorrectly allocated more than once.

Use valid related records and preserve the allocation evidence.

Detection must identify duplicate or excessive allocation.

### C. Order closed with unpaid invoice

Create a sales order in a closed state with an unpaid invoice.

Detect the inconsistency using order status and outstanding receivables.

### D. Status event skips a required state

Inject a lifecycle transition that bypasses a required status.

Preserve the historical event sequence.

Detect the illegal transition using the documented state machine.

### E. Dispute not reflected in receivables

Create a dispute whose receivables treatment is inconsistent with the documented rule.

Detect and explain the discrepancy.

Also include:

- Partial shipments
- Underbilling
- Duplicate invoices
- Short payments
- Long-overdue balances

Avoid conflating legitimate business variations with invalid records.

For every anomaly, provide:

- Rule ID
- Affected entity
- Related record IDs
- Expected behavior
- Observed behavior
- Financial/process impact
- Supporting evidence

---

# 10. EVENT HISTORY AND LIFECYCLE RULES

Implement an explicit lifecycle transition system.

Document valid transitions for:

- Quotes
- Sales orders
- Shipments
- Invoices
- Payments
- Disputes

Retain historical StatusEvent rows.

Make it possible to reconstruct the sequence of business state changes.

Define date-ordering rules and legal transitions.

Where lifecycle states are not prescribed in the source materials, choose reasonable states and document assumptions.

Create intentionally invalid transition events only as labelled scenarios.

A business-state anomaly must not unnecessarily violate database referential integrity.

---

# 11. ANOMALY DETECTION ENGINE

Create an independent, deterministic rule-based detection engine.

It must identify:

- Overbilling
- Underbilling
- Duplicate invoicing
- Duplicate payment allocation
- Unpaid closed orders
- Illegal lifecycle transitions
- Dispute/receivables inconsistencies
- Short payments
- Aging exceptions
- Process delays

Each detected finding should contain:

- Finding ID
- Issue type
- Source entity
- Source record IDs
- Related records
- Severity
- Rule description
- Financial impact or delay
- Evidence

Make the detection logic inspect actual transactional tables and event histories.

Do not read ground-truth labels during detection.

Support filters and aggregated findings.

Do not misrepresent potential overbilling, uncollected receivables, and actual revenue loss as identical metrics.

Avoid double-counting financial exposure.

---

# 12. GROUND TRUTH AND EVALUATION

Produce a separate file:

`ground_truth.csv` or `ground_truth.json`

It must include the known injected anomalies, their affected records, expected labels, and rule-based explanations.

Do not include ground-truth labels as detector input features.

After executing the detector independently, compare results to ground truth.

Calculate:

- True positives
- False positives
- False negatives
- Precision
- Recall
- F1 score
- Results by anomaly type

Define a stable matching rule so one actual anomaly is not counted multiple times.

Explain whether evaluation is performed at a finding, record, or event level.

Do not fabricate perfect detection metrics.

If results reveal weaknesses, identify and correct meaningful implementation errors.

Include a real evaluation report based on executed code.

---

# 13. FINANCIAL RECONCILIATION AND PROCESS METRICS

Calculate metrics from source records.

Include, where supported:

- Total quoted value
- Ordered value
- Fulfilled value
- Invoiced value
- Collected value
- Outstanding receivables
- Underbilled value
- Overbilled exposure
- Duplicate-billing exposure
- Payment allocation discrepancies
- Disputed balances
- Overdue balances
- Order-to-fulfillment delays
- Fulfillment-to-invoice delays
- Invoice-to-payment delays

Use an explicit analysis cutoff date.

Document:

- Each metric's formula
- Its source tables
- The applicable business assumptions
- Its interpretation
- Any limitations

Ensure that legitimate partial payments, multiple shipments, and multiple invoices are handled correctly.

Separate financial exposure measures to avoid misleading totals.

---

# 14. DATA VALIDATION

Create executable checks for:

- Primary-key uniqueness
- Foreign-key integrity
- Required values
- Allowed enumerations
- Relationship consistency
- Date ordering
- Monetary arithmetic
- Invoice quantity reconciliation
- Payment allocation totals
- Lifecycle transitions
- Duplicate detection
- Ground-truth consistency
- Deterministic identifiers
- Expected row counts

Differentiate:

**Structural integrity errors:** Invalid relationships, broken keys, or corrupted data structures.

**Business-rule anomalies:** Deliberate, documented cases that should be detected and reported.

An intentional business anomaly must not be silently treated as a successful normal transaction.

Run tests on both normal and injected anomaly scenarios.

Include boundary-value testing and focused regression tests.

Use actual execution results in the documentation.

---

# 15. REPRODUCIBILITY

The problem statement requires regeneration twice using the same seed and comparison of row counts/checksums.

Implement this explicitly.

For reproducibility verification:

1. Generate dataset A using seed `20261022`.
2. Generate dataset B independently using the same configuration.
3. Compare table row counts.
4. Compare deterministic exported records.
5. Calculate stable checksums.
6. Report PASS or FAIL.
7. Investigate discrepancies.

Ensure deterministic record ordering and serialization.

Do not compare inherently changing SQLite database file metadata as a substitute for comparing logical record contents.

Produce a reproducibility report showing actual tested values.

---

# 16. ANALYTICS DASHBOARD — TIME PERMITTING

Choose the smallest interface that adds meaningful value.

Preferred implementation: Streamlit.

Suggested sections:

### Executive Overview

- Quotes, orders, and invoices
- Total invoiced and collected amounts
- Outstanding receivables
- Exception count
- Revenue leakage/exposure
- Aging distribution

### Revenue Leakage Explorer

- Underbilling
- Overbilling
- Duplicate invoices
- Payment allocation inconsistencies

### Process Delays

- Order processing
- Fulfillment delays
- Invoice generation delays
- Overdue receivables

### Exception Details

Allow investigation of:

- Exception rule
- Entity
- Record ID
- Related records
- Status events
- Financial impact
- Supporting evidence

### Data Quality

Display actual:

- Record counts
- Integrity results
- Reconciliation results
- Ground-truth evaluation metrics
- Reproducibility results

Use a clean, readable interface.

Avoid hardcoded metrics, placeholder charts, fake statistics, unnecessary animations, and excessive CSS.

Every visible metric must originate from actual data.

If UI development threatens core requirements, reduce UI scope.

---

# 17. TESTING STRATEGY

Follow an incremental testing process.

### Stage 1: Schema

Verify table creation, keys, constraints, and relationships.

### Stage 2: Small-scale generator

Verify predictable records and valid joins.

### Stage 3: Business rules

Test financial calculations and legal status transitions.

### Stage 4: Anomaly injection

Check all required negative scenarios individually.

### Stage 5: Detector

Confirm that expected anomalies are found without relying on labels.

### Stage 6: Full-scale generation

Generate the required baseline counts.

### Stage 7: Evaluation

Measure detection performance against ground truth.

### Stage 8: Reproducibility

Run the fixed-seed two-generation checksum comparison.

### Stage 9: Local application

Launch the application and test major user workflows.

### Stage 10: Handover validation

Test the documented setup commands from a clean local environment.

Record actual commands, observations, failures, and fixes.

Never claim a test passed unless it ran successfully.

---

# 18. DOCUMENTATION REQUIREMENTS

Create an excellent `README.md`.

The README must explain:

1. Project purpose.
2. Business workflow.
3. Implemented functionality.
4. Architecture and technology choices.
5. Entity relationships.
6. Dataset generation methodology.
7. Anomaly injection strategy.
8. Detection and evaluation approach.
9. Financial metric definitions.
10. Installation prerequisites.
11. Windows PowerShell setup instructions.
12. Commands for starter and full datasets.
13. Commands for validation and tests.
14. How to launch the interface.
15. Real measured outputs.
16. Assumptions and trade-offs.
17. Known limitations.
18. AI-assisted development disclosure.

Provide a readable data dictionary, design decisions, source manifest, and validation summary.

The project should be explainable by someone familiar with Python and SQL without having to reverse-engineer complicated framework internals.

Do not claim that the candidate personally performed tests or design decisions unless they confirm doing so.

---

# 19. AI TRANSPARENCY — MANDATORY

YottaFlex explicitly allows AI tools and requires prompt-history disclosure.

The project must comply with this requirement.

Create:

`docs/prompt_history.md`

and

`docs/ai_usage.md`

Record the complete, available user-submitted prompts used during development, including this master prompt.

Do not summarize prompts when the original full text can be preserved.

Maintain a timestamped record where reliable timestamps are available.

If full prompt export is unavailable, explain the limitation rather than fabricating missing prompts.

Provide a place for prompts from ChatGPT and any other AI tools involved.

AI disclosure should distinguish:

- What Claude Code implemented.
- Where AI substantially accelerated development.
- Which design choices were suggested by AI.
- What the candidate personally reviewed.
- What the candidate independently modified.
- What testing and validation the candidate actually performed.
- Known limitations of the AI-assisted process.

Do not invent candidate contributions or conceal outside assistance.

The YottaFlex FAQ requires individual work and prohibits implementation help from other people. Therefore, clearly flag that the actual candidate must personally direct, understand, independently validate, and take responsibility for their submission. If another person materially implements or prepares the project, this must not be falsely represented as solely the candidate's independent work.

---

# 20. LOCAL WINDOWS DEVELOPMENT

Use Windows PowerShell-compatible operations.

Keep the project self-contained.

Use a project-local virtual environment where practical.

Suggested setup commands:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Handle systems where `py` is unavailable and `python` must be used instead.

Do not assume Python or Git is already configured.

Avoid administrator privileges unless absolutely necessary, and request approval before system-wide changes.

Use project-relative file paths.

Do not store credentials or personally identifying information in the repository.

Never commit or transfer `.venv`, local caches, credentials, or unrelated user files.

All core components must work locally without paid accounts or external API dependencies.

---

# 21. DEVELOPMENT EXECUTION PROTOCOL

Work autonomously within the designated local folder.

Do not repeatedly request approval for normal implementation decisions.

Use this workflow:

**Inspect → Plan briefly → Implement → Execute → Validate → Fix → Document → Handover**

Maintain a short progress record.

For each major milestone, record:

- Components completed
- Actual files created
- Requirements covered
- Commands run
- Test results
- Outstanding issues
- Next highest-priority task

Prefer vertical slices of working functionality rather than generating the entire codebase before testing.

For example, first demonstrate:

One account → one accepted quote → one order → one shipment → one invoice → one payment → one detectable exception.

Then scale the generator and analysis engine.

If a test fails, investigate and fix the root cause.

Do not suppress errors or create fake successful reports.

Avoid unnecessary refactoring once the core solution is stable and the deadline approaches.

Stop and ask before:

- Deleting unrelated user files.
- Making changes outside the project directory.
- Installing system-wide software.
- Accessing private credentials.
- Any GitHub, remote, deployment, or publication action.

The last category is prohibited unless the user later provides explicit, separate authorization. Do not assume approval.

---

# 22. MANDATORY FRIEND-HANDOVER PACKAGE

This is a critical project-specific requirement.

**The final result must be transferable to another Windows laptop without depending on the original development computer.**

Create a root-level:

`HANDOFF.md`

This document must explain, in simple language:

### A. What is being handed over

- Folder structure
- Working code
- Synthetic-data generator
- Database/schema
- Analytics modules
- Tests
- Reports
- Documentation
- Prompt history

### B. Recipient setup

Explain the exact process for:

1. Copying or extracting the project folder.
2. Installing Python if needed.
3. Opening PowerShell in the project directory.
4. Creating a virtual environment.
5. Installing dependencies.
6. Generating the starter dataset.
7. Generating the full dataset.
8. Running validations.
9. Running anomaly detection.
10. Opening the dashboard, if included.

### C. Candidate verification checklist

Provide concrete commands and expected evidence for checking:

- Required record counts
- Referential integrity
- Financial reconciliation
- All five mandatory anomalies
- Detector precision/recall
- Fixed-seed reproducibility
- Dashboard operation
- Missing dependencies
- Portability issues

The candidate should actually execute these checks on their laptop and record the outcomes.

### D. GitHub publication instructions

Provide informational instructions for the candidate to:

- Set their own Git identity.
- Create their own dedicated public GitHub repository.
- Review sensitive files before publishing.
- Commit genuine reviewed work with meaningful messages.
- Push from their own computer.
- Confirm README and setup commands.
- Submit the correct URL using their registered recruitment email.

**Do not execute any GitHub publication steps yourself.**

Do not reference the current user's personal or Nevora GitHub accounts as publishing destinations.

### E. Archive preparation

Create a clean, portable local handover folder or ZIP archive if the necessary tools are available.

Exclude:

- `.venv`
- `__pycache__`
- Temporary files
- Local credentials
- Secrets
- Absolute-path configuration
- Unnecessary large generated intermediates

Ensure the archive contains all required source files, setup instructions, and deliverables.

If full datasets are too large to transfer or publish comfortably, preserve deterministic commands to regenerate them and include suitably sized example data.

Document what is included and what the recipient must regenerate.

Check the archive's contents before declaring it ready.

Do not share or upload the archive automatically.

---

# 23. REQUIRED FINAL OUTPUTS

At completion, provide a concise report listing:

**Implementation**
- Completed components
- Files created
- Actual project folder path

**Data**
- Row counts by entity
- Seed used
- Mandatory anomaly coverage
- Ground-truth file location

**Validation**
- Structural checks
- Reconciliation outcomes
- Automated test results
- Detector evaluation results
- Reproducibility results

**Documentation**
- README
- Data dictionary
- Architecture
- AI disclosure
- Prompt history
- Handover guide

**Portability**
- Windows setup verified
- Project archive location
- Dependencies
- Recipient setup instructions

**Limitations**
- Unfinished items
- Known bugs
- Untested behaviors
- Candidate actions still required

Do not fabricate any outcome or use placeholder claims.

---

# 24. FINAL REQUIREMENT AUDIT

Before declaring the local project complete, audit all requirements from the original challenge documents.

Explicitly verify:

- All required entities exist.
- Keys and relationships are valid.
- Lifecycle events are retained.
- Required data volumes are generated.
- IDs follow specified patterns.
- Derived values reconcile.
- Mandatory five anomalies exist.
- Additional required exception cases are represented.
- Ground truth is separate.
- Detection works independently of labels.
- Financial metrics are explainable.
- Aging cutoff is documented.
- Data quality checks execute.
- Evaluation metrics are measured.
- Two-run reproducibility is demonstrated.
- Exports and manifest are available.
- README commands are verified.
- Prompt history is preserved to the extent available.
- AI disclosure is honest.
- The local project is portable.
- No personal/Nevora GitHub accounts have been used.
- No GitHub push, remote publication, or deployment has occurred.

Use the following statuses:

- PASS
- PARTIAL
- FAIL
- NOT VERIFIED

Provide evidence for each status.

Prioritize fixing mandatory FAIL items before adding optional functionality.

---

# 25. START EXECUTION

Begin immediately by:

1. Checking the current date/time against the October 31, 2026, 10 PM IST deadline.
2. Inspecting the current local workspace.
3. Reading the problem statement, submission guidelines, and FAQ.
4. Checking Python and PowerShell development readiness.
5. Producing a concise requirements matrix.
6. Selecting a minimal architecture suited to Python and SQL.
7. Creating a realistic execution plan based on time remaining.
8. Implementing the first working end-to-end workflow.
9. Scaling to the required synthetic dataset.
10. Continuing through anomaly detection, validation, interface, documentation, and local handover.

Do not stop after writing an architecture document.

Continue implementing and validating within the authorized local folder.

Do not require constant manual confirmations.

**FINAL SUCCESS CONDITION:**

A self-contained, functioning, documented, reproducible Order-to-Cash analytics project exists entirely within the designated local directory, is ready to be transferred to the actual candidate, and contains everything reasonably necessary for them to inspect, independently verify, understand, and prepare their own compliant submission.

**The final deliverable is a LOCAL PROJECT AND HANDOVER PACKAGE — NOT A GITHUB REPOSITORY, PUSH, DEPLOYMENT, OR SUBMISSION.**

Begin now.
`````

### Prompt 2: 2026-10-30 22:31:46 IST

`````text
how to run it so i can chcek it out
`````

### Prompt 3: 2026-10-30 22:36:12 IST

`````text
so this is it? are you sure? i can submit this as it is?
`````

### Prompt 4: 2026-10-30 22:53:20 IST

`````text
MASTER PROMPT — YOTTAFLEX AI CANDIDATE PROJECT
Order-to-Cash Revenue Leakage and Process Delay Detection System
ROLE
Act as a senior Python engineer, SQL/data architect, business-process analyst, software quality engineer, and technical reviewer.
Your task is to help me design, implement, test, document, and prepare a complete solution for the YottaFlex AI Candidate Project Challenge.
The solution must be technically sound, reproducible, maintainable, explainable, and executable on a Windows laptop.
I am comfortable with Python, SQL, and data engineering. Prefer straightforward, well-reasoned engineering decisions over excessive abstractions or unnecessary technologies.
Take an execution-focused approach: independently handle routine technical decisions, explain significant architectural trade-offs, and involve me when decisions materially affect requirements, security, or submission.
Prioritize correctness and verification over feature count. Never fabricate results, tests, implementation progress, or documentation.
1. DEADLINE AND EXECUTION PRIORITIES
Official submission deadline: October 31, 2026, 10:00 PM IST.
At the beginning of execution:

1. Check the current system time.
2. Calculate the actual time remaining until the deadline in IST.
3. Create a realistic, time-boxed implementation plan.
4. Identify the minimum complete, demonstrable solution.
5. Reserve the final portion of the available time for testing, documentation, GitHub publication, and submission verification.

Do not assume that the original 72-hour challenge window remains available.
Use the following priority order:
P0 — Mandatory

* Complete relational schema
* Deterministic synthetic-data generator
* Required baseline data volumes
* Valid business workflows
* Five mandatory negative scenarios
* Event-history preservation
* Ground-truth generation
* Exception detection
* Financial reconciliation
* Validation and reproducibility

P1 — High value

* Evaluation metrics
* Analytical reporting
* Usable exception explorer
* Automated regression tests
* Excellent documentation

P2 — Optional

* Advanced visualizations
* Additional business insights
* UI enhancements
* Extra analytical features

Never sacrifice P0 requirements to complete P2 features.
Maintain a brief progress record and adjust priorities as time decreases.
2. SOURCE DOCUMENTS AND REQUIREMENT ANALYSIS
The project workspace contains the following source materials:

* `Problem statement.txt`
* `YottaFlex AI Candidate Project Submission Guidelines.pdf`
* `YottaFlex AI Candidate Project-FAQ.pdf`

Begin by locating and reading these documents completely.
Treat the problem statement as the authoritative source for business and technical requirements.
Treat the candidate guidelines and FAQ as the authoritative sources for development, AI transparency, repository, and submission requirements.
Before implementation:

1. Extract every mandatory requirement.
2. Identify the required data entities.
3. Map the business workflow and conditional rules.
4. Identify the required negative scenarios.
5. Extract the expected data volumes.
6. Determine the evaluation and reproducibility criteria.
7. Identify ambiguities and necessary assumptions.
8. Create a concise requirement traceability checklist.

For each requirement, record:

* Requirement ID
* Description
* Source
* Implementation location
* Validation method
* Completion status

Do not silently omit requirements.
Make reasonable assumptions when the documents are ambiguous, and explain them in the documentation.
Do not spend excessive time on planning before implementation.
3. BUSINESS PROBLEM AND OBJECTIVE
Build an end-to-end Order-to-Cash Revenue Leakage and Process Delay Detection System.
The system must track the following business workflow:
Account → Quote → Sales Order → Fulfillment/Shipment → Invoice → Payment → Dispute.
The objective is to detect financial leakage, operational delays, and inconsistent business states while preserving data integrity and full traceability.
The solution must demonstrate:

* Realistic business entities and relationships
* Valid parent-child transaction generation
* Conditional business rules
* Historical lifecycle events
* Revenue leakage detection
* Payment and receivables reconciliation
* Process-delay analysis
* Explicit exception scenarios
* Independent ground-truth labels
* Measurable detection outcomes
* Fixed-seed reproducibility

Primary actors include customers/prospects, marketing and sales operations, support agents, analysts, and administrators.
This is fundamentally a relational data engineering and business analytics problem.
Do not reduce it to a basic CRUD application or a visually attractive dashboard without reliable underlying logic.
4. TECHNOLOGY STACK
Use an appropriate, lightweight technology stack optimized for the remaining deadline.
Preferred technologies:

* Python 3.11+ for data generation, business logic, and orchestration
* SQLite for relational persistence and SQL-based analytics
* SQL for queries, validation, and reconciliation
* Pandas where useful for analysis and exports
* Pytest for automated tests
* Streamlit for an optional lightweight analytical dashboard

You may adjust the stack if another locally runnable solution is demonstrably simpler or more reliable.
Follow these constraints:

* Use only free or locally runnable services.
* Avoid unnecessarily large or slow dependencies.
* Do not require paid APIs.
* Prefer minimal configuration.
* Ensure compatibility with Windows PowerShell.
* Avoid cloud infrastructure unless explicitly required.
* Do not introduce machine learning where deterministic business rules are sufficient.

Use appropriate modularity without over-engineering.
Explain important architectural decisions and trade-offs.
5. RELATIONAL DATA MODEL
Implement the 11 required entities:

1. Account
2. Quote
3. QuoteLine
4. SalesOrder
5. OrderLine
6. Shipment
7. Invoice
8. InvoiceLine
9. Payment
10. Dispute
11. StatusEvent

Create additional supporting tables where needed for correct relationships, including:

* ShipmentLine
* PaymentAllocation

For each entity, define and document:

* Primary key
* Foreign keys
* Data types
* Required and optional fields
* Allowed values
* Uniqueness rules
* Validation constraints
* Units and monetary precision
* Lifecycle states
* Effective dates
* Relationship cardinality

Use bridge tables for many-to-many relationships.
Enable and validate database foreign-key constraints.
Ensure all transactions reference valid parent records.
Preserve historical state changes in StatusEvent rather than overwriting prior history.
Make current business status consistent with the recorded event sequence, except where an intentionally labelled anomaly is present.
For financial calculations, use exact numeric representations such as integer minor currency units or Decimal.
Document the currency and rounding assumptions.
6. DETERMINISTIC SYNTHETIC DATA GENERATION
Implement a configurable synthetic-data generator using the fixed seed:
`20261022`
Support:
Starter mode: A small, quickly generated dataset that covers all required workflows and anomaly categories.
Full mode: The required baseline dataset.
The full dataset must target:

* 10,000 quotes
* 7,000 sales orders
* 8,000 invoices
* 15,000 payments/events

Document the exact interpretation and distribution of the combined payments/events volume.
Ensure that the larger invoice count is supported by legitimate business relationships, such as multiple invoices per order and partial fulfillment.
Use deterministic, zero-padded identifiers following the required conventions:

```
QTE-2026-000001
SO-2026-000001
SHP-2026-000001
INV-2026-000001
PAY-2026-000001
DSP-2026-000001
```

Apply consistent conventions to the remaining entities.
Generate data in the correct dependency order:

1. Accounts
2. Quotes and quote lines
3. Accepted quotes and sales orders
4. Order lines
5. Fulfillment and shipment events
6. Invoices and invoice lines
7. Payments and allocations
8. Disputes
9. Status events and derived business outcomes

Adjust event-generation timing as necessary to preserve the correct chronological lifecycle.
Use coherent distributions for:

* Quote acceptance
* Order values and quantities
* Customer activity
* Payment terms
* Shipment delays
* Partial fulfillment
* Invoice generation
* Partial payments
* Overdue receivables
* Disputes

Calculate derived values from source transactions rather than independently generating totals or labels.
Generate valid baseline records first, then inject documented anomalies.
Ensure the same seed and configuration produce the same logical dataset, record ordering, and deterministic exports.
7. REQUIRED BUSINESS EXCEPTIONS
Implement all five mandatory negative scenarios.
7.1 Invoice exceeds fulfilled quantity
Create cases where invoiced quantity exceeds the quantity legitimately fulfilled.
Detection must identify:

* Relevant invoice and invoice line
* Related order and shipment
* Fulfilled quantity
* Invoiced quantity
* Excess quantity
* Potential overbilling impact

7.2 Payment allocated twice
Create cases where a payment allocation is duplicated or exceeds the payment's valid allocatable value.
Preserve valid payment and invoice references.
Detect the allocation inconsistency without incorrectly flagging legitimate multiple allocations.
7.3 Order closed with unpaid invoice
Create cases where a sales order is closed while one or more related invoices retain an unpaid balance.
Identify the inconsistent state and supporting financial records.
7.4 Status event skips a required state
Create an event sequence containing an invalid lifecycle transition.
Preserve the actual event sequence.
Detect the violation using an explicit, documented state-transition model.
7.5 Dispute not reflected in receivables
Create cases where the receivables treatment of a dispute is inconsistent with the documented accounting/business rule.
Identify the discrepancy and supporting source records.
Also include the following scenarios:

* Partial shipment
* Underbilling
* Duplicate invoice
* Short payment
* Long-overdue balance

Maintain structural integrity when injecting business exceptions.
Do not corrupt unrelated foreign keys or silently delete historical events.
Every intentional anomaly must be traceable to the source records that caused it.
8. BUSINESS RULES AND LIFECYCLE ENGINE
Implement explicit lifecycle rules for quotes, orders, shipments, invoices, payments, and disputes.
Define:

* Allowed states
* Valid transitions
* Required predecessor states
* Terminal states
* Applicable timestamps
* State-specific business rules

Examples of possible transitions include:

* Quote: Draft → Submitted → Accepted/Rejected
* Order: Created → Confirmed → Partially Fulfilled → Fulfilled → Closed
* Invoice: Issued → Partially Paid → Paid/Overdue
* Dispute: Open → Under Review → Resolved

Finalize the exact transition graph based on the chosen business model and document it.
Maintain historical StatusEvent records.
Do not generate statuses independently of their preceding business events.
Calculate aging and overdue statuses using a documented analysis cutoff date rather than uncontrolled current-time calculations.
9. ANOMALY DETECTION ENGINE
Create an independent, explainable rule-based engine to detect:

* Invoice quantity exceeding fulfillment
* Underbilling
* Duplicate invoices
* Duplicate payment allocations
* Closed orders with unpaid invoices
* Invalid lifecycle transitions
* Dispute/receivables mismatches
* Short payments
* Overdue balances
* Process delays

For each finding, produce:

* Unique finding identifier
* Issue type
* Rule ID
* Severity
* Source entity
* Affected record IDs
* Supporting related records
* Expected behavior
* Actual behavior
* Financial or operational impact
* Explanation

Use actual source records as evidence.
Implement stable matching and deduplication logic.
Distinguish financial exposure, unpaid receivables, actual collections, and potential revenue leakage.
Do not double-count values across overlapping categories.
10. GROUND TRUTH AND EVALUATION
Generate a separate:
`ground_truth.csv` or `ground_truth.json`
Include:

* Anomaly ID
* Issue type
* Affected record IDs
* Related entity references
* Expected label
* Rule identifier
* Expected impact, where applicable
* Causal explanation

The ground-truth data must be derived from documented anomaly-injection rules.
Do not leak ground-truth labels into detector inputs.
Keep synthetic-data generation, anomaly detection, and evaluation logically separated.
Evaluate detector findings against the isolated ground truth.
Report:

* True positives
* False positives
* False negatives
* Precision
* Recall
* F1 score
* Per-anomaly detection performance

Define the evaluation unit clearly to avoid counting the same issue multiple times.
Do not assume perfect metrics or fabricate performance numbers.
All reported results must come from executed evaluation code.
11. FINANCIAL RECONCILIATION AND ANALYTICS
Calculate relevant metrics from source transactions.
Required analytical capabilities should include:

* Quoted value
* Ordered value
* Fulfilled value
* Invoiced value
* Collected value
* Outstanding receivables
* Overdue receivables
* Underbilled value
* Potential overbilling exposure
* Duplicate-billing exposure
* Allocation inconsistencies
* Disputed balances
* Order-to-fulfillment delays
* Fulfillment-to-invoice delays
* Invoice-to-payment delays

Implement aging buckets using a documented cutoff date.
For each metric, document:

* Formula
* Source tables
* Units
* Filtering conditions
* Business interpretation
* Known limitations

Ensure the calculations are internally consistent.
Handle legitimate partial shipments, multiple invoices, partial payments, and disputes without introducing false inconsistencies.
12. VALIDATION AND AUTOMATED TESTING
Implement executable checks covering:
Structural validation

* Primary-key uniqueness
* Foreign-key integrity
* Required values
* Allowed enums
* Data types
* Date ordering
* Relationship consistency

Financial validation

* Line-item calculations
* Invoice totals
* Payment allocation arithmetic
* Outstanding balance calculations
* Quantity reconciliation
* Duplicate identification

Lifecycle validation

* Legal transitions
* Event ordering
* State consistency
* Closed-order conditions

Dataset validation

* Required record counts
* Deterministic identifiers
* Expected anomaly coverage
* Ground-truth consistency
* Derived-value correctness

Distinguish structural data corruption from deliberately injected business-rule exceptions.
Create focused tests for normal cases, boundary cases, failure cases, and all mandatory negative scenarios.
Run the tests and report actual results.
Fix underlying implementation defects rather than suppressing failed checks.
13. REPRODUCIBILITY VERIFICATION
The challenge requires regenerating the dataset twice using the same seed and comparing row counts and checksums.
Implement a repeatable verification process:

1. Generate dataset A using seed `20261022`.
2. Independently generate dataset B using the same configuration.
3. Compare all relevant table counts.
4. Export records in stable order.
5. Normalize deterministic representations where necessary.
6. Calculate checksums.
7. Compare the checksums.
8. Report PASS or FAIL.

Investigate mismatches.
Do not substitute nondeterministic database-file checksums for deterministic logical-data comparisons.
Create a reproducibility report containing actual execution evidence.
14. ANALYTICS INTERFACE
After the core system is working, implement a lightweight Streamlit dashboard if the remaining time permits.
Prefer five useful sections:
Executive Overview

* Business volume
* Total invoiced and collected value
* Outstanding receivables
* Exception count
* Potential leakage
* Aging summary

Revenue Leakage

* Underbilling
* Overbilling
* Duplicate invoicing
* Payment allocation anomalies

Process Delays

* Fulfillment delays
* Invoicing delays
* Payment delays
* Aging distribution

Exception Explorer

* Filter findings by issue type and severity
* Inspect related source records
* Trace supporting lifecycle events
* View financial impact and rule explanations

Data Quality and Evaluation

* Dataset counts
* Validation results
* Detector metrics
* Reproducibility results

Use a clean, readable interface with meaningful labels and sensible formatting.
All displayed metrics must be computed from actual generated records.
Avoid unnecessary animations, placeholder data, decorative complexity, and excessive dependencies.
A complete, reliable backend is more valuable than an incomplete dashboard.
15. PROJECT ORGANIZATION
Use a clear structure suitable for a Python and SQL project.
Suggested layout:

```
yottaflex-o2c/
├── app/
│   └── dashboard.py
├── src/
│   ├── config.py
│   ├── database.py
│   ├── generator.py
│   ├── lifecycle.py
│   ├── anomalies.py
│   ├── detector.py
│   ├── reconciliation.py
│   ├── evaluation.py
│   └── validation.py
├── sql/
│   ├── schema.sql
│   └── analytics.sql
├── tests/
├── data/
├── outputs/
├── docs/
│   ├── data_dictionary.md
│   ├── architecture.md
│   ├── business_rules.md
│   ├── assumptions.md
│   ├── validation_report.md
│   ├── reproducibility.md
│   ├── ai_usage.md
│   └── prompt_history.md
├── scripts/
├── README.md
├── requirements.txt
└── .gitignore
```

Adapt the structure when a simpler implementation is preferable.
Avoid empty modules and unnecessary abstractions.
Use relative paths to ensure portability across Windows systems.
16. DOCUMENTATION AND REQUIRED ARTIFACTS
Produce the artifacts required by the problem statement:

* Executable source code
* SQL schema
* Complete data dictionary
* Synthetic-data generator
* Fixed-seed configuration
* CSV/JSON/SQL seed data
* Source manifest
* Ground-truth file
* Validation summary
* Reproducibility report
* Evaluation results
* Setup and run instructions

Create a high-quality README explaining:

1. Project overview.
2. Business problem.
3. Core workflow.
4. Implemented features.
5. Architecture and data model.
6. Business rules and assumptions.
7. Synthetic-data methodology.
8. Exception scenarios.
9. Detection methodology.
10. Financial reconciliation.
11. Evaluation methodology.
12. Installation instructions.
13. Generation and execution commands.
14. Validation and test commands.
15. Real results.
16. Limitations and next steps.
17. AI usage and prompt-history references.

The project should be understandable and reproducible by another developer.
Every command shown in the README must be verified where possible.
Do not include fabricated screenshots, test results, metrics, or implementation claims.
Use synthetic data by default. If any external public data is used, document its source, version, retrieval date, license, attribution, transformations, and discarded fields.
Do not introduce confidential or improperly licensed data.
17. AI USAGE AND PROMPT HISTORY
YottaFlex AI explicitly allows AI coding tools and requires transparent disclosure.
Maintain an accurate record of submitted prompts.
Create:

* `docs/prompt_history.md`
* `docs/ai_usage.md`

Preserve available original user prompts rather than rewriting them as if they had been submitted in another form.
Include prompts from other AI tools when provided.
Clearly document:

* How AI accelerated implementation
* Areas receiving substantial AI assistance
* Important AI-suggested design decisions
* What I reviewed and validated
* Changes I personally made
* Known limitations

Do not invent manual development, testing, or review that has not actually occurred.
Make explanations concise and specific enough to support an interview walkthrough.
18. WINDOWS DEVELOPMENT AND PORTABILITY
Build and test on Windows using PowerShell.
Check whether Python and Git are installed before depending on them.
Use a project-local Python virtual environment.
Suggested setup:

```
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Provide equivalents where necessary.
Use portable file paths and avoid hardcoded machine-specific directories.
Keep dependencies minimal.
Document commands for:

* Installing dependencies
* Generating starter data
* Generating full data
* Running validations
* Running evaluation
* Running automated tests
* Launching the dashboard

Test the documented workflow.
Avoid storing credentials, secrets, personal information, or unrelated files in project artifacts.
19. GIT AND GITHUB SUBMISSION PREPARATION
The submission requires a dedicated public GitHub repository.
Prepare the project for a professional repository submission.
Include:

* Clear repository organization
* Appropriate `.gitignore`
* Meaningful documentation
* Reproducible execution commands
* Required prompt history
* Safe synthetic data
* Relevant generated reports
* Accurate limitations

Use meaningful Git commits representing actual changes and development milestones.
Do not fabricate or backdate commit history.
Never include credentials or sensitive data.
Before publishing:

1. Verify the repository contents.
2. Check for secrets and unnecessary large files.
3. Verify setup and test commands.
4. Confirm documentation and required artifacts.
5. Confirm the account and intended repository.
6. Request authorization before creating a public repository or pushing code.

After authorized publication, verify that the public repository contains the expected files.
The submission link must be sent according to the recruitment instructions, using the registered email address.
Do not claim that repository publication or email submission has occurred unless verified.
20. DEVELOPMENT WORKFLOW
Use an incremental implementation strategy.
Phase 1 — Requirements and architecture

* Inspect documents.
* Confirm scope.
* Select stack.
* Define schema and business rules.
* Create requirement checklist.

Phase 2 — Working core
Implement one complete workflow:
Account → Quote → Order → Shipment → Invoice → Payment.
Verify the relevant relationships, calculations, and event records.
Phase 3 — Full data generation

* Build the seeded generator.
* Reach required baseline volumes.
* Add realistic distributions.
* Inject mandatory exceptions.
* Produce separate ground truth.

Phase 4 — Detection and reconciliation

* Implement detection rules.
* Calculate financial metrics.
* Calculate aging and delays.
* Trace findings to source records.

Phase 5 — Evaluation and validation

* Run structural checks.
* Run reconciliation tests.
* Evaluate detection performance.
* Perform two-run reproducibility verification.

Phase 6 — Analytics interface
Develop the smallest polished, useful dashboard that fits the available time.
Phase 7 — Documentation and delivery

* Finalize README.
* Generate data dictionary.
* Record assumptions and trade-offs.
* Preserve prompt history.
* Document AI usage.
* Verify installation and execution.
* Prepare the repository for submission.

At each milestone, briefly report what is implemented, what was actually tested, remaining risks, and the next action.
Do not repeatedly request approval for routine technical decisions.
Ask only when a decision is genuinely blocking or materially changes scope, security, or publication.
21. QUALITY AND ENGINEERING STANDARDS
Follow these principles:
Correctness first. Business calculations and relationships must be demonstrably valid.
Explainability. Every anomaly and metric should be traceable to a documented rule and underlying records.
Simplicity. Avoid unnecessary dependencies, abstraction layers, and architecture patterns.
Maintainability. Use readable naming, coherent modules, and focused functions.
Evidence over claims. Only report results that have actually been generated or tested.
Meaningful testing. Cover normal, boundary, and failure behavior.
Reproducibility. Generated datasets must be stable for identical seed and configuration.
Practical documentation. Explain why decisions were made, not just what files exist.
Originality. Design a solution that responds to the actual problem, with purposeful analytics, relevant exception handling, and practical engineering trade-offs rather than generic boilerplate.
Transparency. Accurately document AI assistance and actual review activity.
Keep the codebase understandable enough for a detailed technical walkthrough.
22. FINAL ACCEPTANCE CHECKLIST
Before declaring completion, verify the following:

* All 11 required entities implemented
* Correct primary and foreign keys
* Relationship cardinality documented
* Valid lifecycle state modeling
* Historical StatusEvent records retained
* Required deterministic ID conventions
* 10,000 quotes generated
* 7,000 orders generated
* 8,000 invoices generated
* 15,000 payments/events baseline satisfied
* Partial shipment scenarios included
* Underbilling scenarios included
* Duplicate invoice scenarios included
* Short payment scenarios included
* Long-overdue balances included
* Invoice exceeding fulfilled quantity
* Payment allocated twice
* Closed order with unpaid invoice
* Invalid lifecycle-state transition
* Dispute not reflected in receivables
* Ground truth generated separately
* Independent exception detection working
* Financial balances reconciled
* Aging cutoff documented
* Structural validations executed
* Automated tests executed
* Evaluation metrics calculated
* Fixed-seed reproducibility verified twice
* CSV/JSON/SQL exports provided
* Data dictionary and schema documented
* Source manifest included
* README commands verified
* AI usage disclosed accurately
* Prompt history preserved
* Repository contents reviewed for safety
* Submission readiness checked

For each item, report:

* PASS
* PARTIAL
* FAIL
* NOT VERIFIED

Provide supporting evidence rather than unsupported success claims.
Fix mandatory failures before investing further time in optional features.
23. START IMPLEMENTATION NOW
Begin by inspecting the project workspace, checking the current time, and reading all available challenge documents.
Your first response should briefly contain:

1. Your understanding of the problem.
2. The mandatory deliverables.
3. Your proposed architecture.
4. The five highest implementation risks.
5. Your time-aware execution plan.

Then proceed directly to implementation.
Do not stop after producing a plan.
Build, execute, test, fix, and document the solution iteratively.
Continue until the working solution and mandatory deliverables are complete or the available execution window is exhausted.
FINAL OBJECTIVE
Deliver a reliable, reproducible, technically defensible Order-to-Cash Revenue Leakage and Process Delay Detection System that meets the YottaFlex AI challenge requirements, provides measurable evidence of correctness, and is ready for a transparent, professional public GitHub submission before October 31, 2026, 10:00 PM IST.


make the necessary changes and store this as the prompt used to create this software
`````

### Prompt 5: 2026-10-30 23:24:36 IST

`````text
I am
`````

### Prompt 6: 2026-10-30 23:32:22 IST

`````text
is any friend or whose name is written in this project if any?
`````

### Prompt 7: 2026-10-30 23:33:41 IST

`````text
remove nevora if any thats not needed
`````

### Prompt 8: 2026-10-30 23:38:46 IST

`````text
so is this ready for submission apart from git i will do on my own
`````

### Prompt 9: 2026-10-30 23:45:06 IST

`````text
i need you to fill them out all those ai usage, prompt history and other which should be eligible for submission of the project make the needed changes and prepare me the zip
`````

### Prompt 10: 2026-10-30 23:51:41 IST

`````text
Yes, I'll paste them
`````

### Prompt 11: 2026-10-30 23:52:11 IST

`````text
used chatgpt for creating the master prompt and claude code to make it thats all
`````

## Briefs Claude Code wrote for its own sub-agents

These were not typed by a person. Claude Code wrote them while working and they are listed for completeness.

### Adversarial review of detector logic: 2026-10-30 21:16:00 IST

`````text
Adversarially review a Python/SQLite Order-to-Cash project for real correctness bugs. Do NOT edit any file inside the project. You may write throwaway scripts only in this scratch folder: C:\Users\Asus\AppData\Local\Temp\claude\C--Users-Asus-Documents-YottaFlex-Project\2ae80776-e96f-4e37-91b2-42d5617e0db0\scratchpad\review

Project root: C:\Users\Asus\Documents\YottaFlex Project\yottaflex-o2c
Run Python with: "C:\Users\Asus\Documents\YottaFlex Project\yottaflex-o2c\.venv\Scripts\python.exe" with the project root as the working directory.
Spec: C:\Users\Asus\Documents\YottaFlex Project\Problem statement.txt

Read: src/detector.py, src/reconciliation.py, src/evaluation.py, src/validation.py, src/generator.py, src/anomaly_injection.py, src/lifecycle.py, src/config.py, sql/schema.sql, sql/analytics.sql. tests/conftest.py has a hand-built one-order `chain` fixture; tests/test_detection.py shows how to bend it, which is the quickest way to build a counterexample.

Goal: find cases where a rule gives the wrong answer on data the generator happens not to produce, plus anything in the spec the code does not actually satisfy. Think about what a sceptical senior reviewer at the hiring company would poke at. Examples of angles (not an exhaustive list, and not a statement of what is or is not broken):
- Rule logic that only works because of how this particular generator behaves.
- Money that can be double-counted between findings, or a reconciliation identity that would pass even when something is wrong (a tautology).
- Evaluation matching that could overstate results, or labels that are derived in a way that makes the score meaningless.
- Boundary dates, void invoices, reversed payments, multi-invoice orders, partial shipments, disputes on invoices with multiple payments.
- Nondeterminism: anything depending on set/dict ordering, locale, or platform.
- Ground-truth leakage into the detector.
- Validation checks that cannot fail.

For each issue you report, PROVE it: give the smallest concrete input and the wrong output you actually observed by running it. Do not report style points, naming, or speculation. If you tried an angle and it held up, list it in one line under "Held up" so I know it was tested.

Return: a list ordered by severity, each with file:line, the failing scenario, observed vs expected output, and a suggested minimal fix. Keep it under 500 words unless you found many real bugs.
`````

## Other AI tools

The candidate states that ChatGPT was used to create the master prompt, and that Claude Code and ChatGPT are the only AI tools used (Prompt 11).

**Limitation:** the prompts sent to ChatGPT were not provided, so they are not included here, and none have been invented. They belong in this section if they can be retrieved.
