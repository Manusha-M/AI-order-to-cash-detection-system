# Setup and Verification Guide

This guide sets the project up from the zip on any Windows laptop, and lists what to check before submitting. It assumes no prior setup.

## 0. Read this first: the "individual work" rule

The YottaFlex FAQ, item 7, says: "The project must be your individual work. AI and public learning resources are allowed; implementation help from other people is not."

**This project was built by Claude Code, operated by you.** AI help is allowed, so this fits the rule as long as no other person helped build it.

Prompt 1 in `docs/prompt_history.md` describes a friend as the candidate. It stays word for word, because YottaFlex requires the real history. Prompt 5 records that you are the candidate. A reviewer will see both, so be ready to explain the difference. You can add your explanation to `docs/ai_usage.md`.

What you must not do:

- Delete or soften `docs/ai_usage.md`.
- Edit, reorder or swap anything in `docs/prompt_history.md`. You may only add to it.
- Claim you wrote, designed or tested something you did not.
- Create a fake commit history, or set commit dates to something untrue. The guidelines say artifact timestamps are used to verify the window.

YottaFlex will ask you to walk through the solution. You will need to explain it yourself.

## A. What is in the zip

| Item | Where |
|---|---|
| Working code | `run.py`, `src/`, `app/` |
| Synthetic data generator | `src/generator.py`, `src/anomaly_injection.py` |
| Database schema and views | `sql/` |
| Detection, reconciliation, evaluation | `src/detector.py`, `src/reconciliation.py`, `src/evaluation.py` |
| Automated tests | `tests/` |
| Starter dataset, ready to view | `data/starter/` (CSV, JSON, SQL, ground truth, manifest) |
| Measured results | `outputs/`, `docs/validation_report.md`, `docs/reproducibility.md` |
| Documentation | `README.md`, `docs/` |
| Prompt history and AI disclosure | `docs/prompt_history.md`, `docs/ai_usage.md` |

**Not included, because you regenerate it:** the full dataset (`data/full/`, about 160 MB) and the database files (`*.db`). The `.venv` folder is also left out, because it only works on the machine that created it.

## B. Set up on your laptop

### 1. Extract the folder

Right-click the zip, choose **Extract All**, and pick a simple location such as `Documents`. You should get a folder called `yottaflex-o2c`.

### 2. Install Python if needed

Open **PowerShell** from the Start menu and run:

```powershell
py -3 --version
```

If you see `Python 3.11` or higher, go to step 3.

If not, install Python from [python.org/downloads](https://www.python.org/downloads/) and tick **Add python.exe to PATH** on the first installer screen. Then close and reopen PowerShell.

Windows can show a message that Python was not found and offer the Microsoft Store. That is a placeholder, not Python. Use the python.org installer.

### 3. Open PowerShell in the project folder

```powershell
cd "$HOME\Documents\yottaflex-o2c"
```

Change the path if you extracted it elsewhere.

### 4. Create a virtual environment

A virtual environment is a private copy of Python for this project, so its packages do not affect anything else.

```powershell
py -3 -m venv .venv
```

If `py` is not found, use `python -m venv .venv`.

### 5. Install the dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This downloads Streamlit, pandas, Altair and pytest. It takes a few minutes.

### 6. Build and check the starter dataset

```powershell
.\.venv\Scripts\python.exe run.py all --scale starter
```

This takes about 15 seconds. It runs every step and prints results.

### 7. Build and check the full dataset

```powershell
.\.venv\Scripts\python.exe run.py all --scale full
```

This takes about two minutes and creates 10,000 quotes, 7,000 orders, 8,000 invoices and 15,000 payments.

### 8. Run the automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

This takes about two minutes.

### 9. Run steps one at a time, if you want to

```powershell
.\.venv\Scripts\python.exe run.py detect --scale full
.\.venv\Scripts\python.exe run.py validate --scale full
.\.venv\Scripts\python.exe run.py reconcile --scale full
.\.venv\Scripts\python.exe run.py evaluate --scale full
```

### 10. Open the dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\dashboard.py
```

Your browser opens at `http://localhost:8501`. The first start can take 20 seconds or so. Press `Ctrl+C` in PowerShell to stop it.

The first time Streamlit runs on a computer it may ask for an email address in PowerShell. You can leave it blank and press Enter.

## C. Your verification checklist

Do these yourself and write down what you see. Add your results to `docs/ai_usage.md`, and take the matching line out of its "Not recorded" list. Do not copy the expected values below into that file without running them.

| Check | Command | What you should see |
|---|---|---|
| Record counts | `run.py validate --scale full` | Includes row counts of 10,000, 7,000, 8,000 and 15,000. Details in `outputs\full\validation.json` |
| Referential integrity | `run.py validate --scale full` | `Structural checks: 98 of 98 passed` |
| Financial reconciliation | `run.py reconcile --scale full` | Six lines, all `PASS`, all `difference 0 paise` |
| All five mandatory anomalies | `run.py validate --scale full` | `Business anomaly tie-outs: 6 of 6` |
| Detector results | `run.py evaluate --scale full` | Precision and recall by label source and by issue type. Read the `injected` line first |
| Clean data stays clean | `run.py negative-control --scale full` | `Negative control (PASS): 0 findings` |
| Same seed, same data | `run.py reproduce --scale full` | `Reproducibility PASS` with matching A and B values |
| Same data as the original build | Compare `combined_sha256` in `data\full\manifest.json` with `docs\reproducibility.md` | Same value on Python 3.13. Another Python version may differ; see below |
| Automated tests | `python -m pytest -q` | All passed |
| Dashboard | Open each of the five tabs | No red errors; numbers match the commands above |
| Other seeds | `python scripts\seed_sweep.py --scale starter` | No false positives or false negatives listed |

To learn the system, try breaking it. Run `run.py generate --scale starter`, then change `LONG_OVERDUE_DAYS` in `src/config.py` from 90 to 60. Now run only `run.py detect --scale starter` and `run.py evaluate --scale starter`. When this was tried, evaluation showed 6 false positives for `LONG_OVERDUE`. Work out why before you change it back. (Hint: the data was generated while the limit was 90, and some normal customers pay up to 80 days late.) If you re-run `all` instead, the generator reads the new value too and the false positives disappear. Think about why that is.

### If something goes wrong

| Problem | Fix |
|---|---|
| `Python was not found` | Install Python from python.org (step 2) |
| `running scripts is disabled` | You do not need to activate the environment. Use the `.\.venv\Scripts\python.exe` commands above exactly |
| `No module named streamlit` | Run step 5 again |
| `o2c.db not found` | Run `run.py generate` first |
| Dashboard says no dataset found | Run step 6, then reload the page |
| Port 8501 already in use | Add `--server.port 8502` to the Streamlit command |
| Checksum differs from the document | Check your Python version. Python's random number functions are not guaranteed identical across versions. `run.py reproduce` must still pass on your machine |

## D. Publishing to GitHub

Section 0 comes first. These steps use your own account. Nothing has been published yet.

1. Install Git from [git-scm.com](https://git-scm.com/) if needed.
2. Set your own identity:

   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "the-email-you-use-on-github@example.com"
   ```

3. Create a **new, dedicated, public** repository on your GitHub account. Do not add a README there.
4. Review what will be published. There should be no secrets, personal information or anything you are not allowed to share. `.gitignore` already leaves out `.venv`, the full dataset and database files.
5. In the project folder:

   ```powershell
   git init
   git add .
   git status
   ```

   Read the `git status` list before going further.

6. Commit truthfully. A single honest first commit such as `Import project prepared with Claude Code (see docs/ai_usage.md)`, followed by real commits for your own changes, is far better than an invented history.
7. Connect and push, using the URL from your repository page:

   ```powershell
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
   git push -u origin main
   ```

8. Open the repository in a private browser window. Check that it is public and that the README shows properly.
9. Follow the README's setup commands once more from a fresh clone.
10. Send the link from the **same email address you used during recruitment**, following the instructions YottaFlex gave you. Keep the repository available until the deadline.

## E. What is in the archive

`scripts/make_handover_zip.py` builds `yottaflex-o2c-handover.zip`. It leaves out `.venv`, caches, `.env` and key files, `*.db` files and `data/full/`. It stops with an error if it finds a likely secret or an absolute path from the development machine.

`outputs/full/` is included so you can compare your results with the original run. Regenerate it yourself rather than relying on it.
