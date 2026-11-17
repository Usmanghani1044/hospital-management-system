# Validation record

## Executed checks

- 20 automated unittest cases passed on Python 3.12 with SQLite in the delivery environment.
- JavaScript syntax checked with `node --check static/app.js`.
- Fresh SQLite schema, fictional initialization, integrity check and foreign-key check passed.
- Twelve SQL report queries executed against the fictional SQLite database.
- HTTP tests cover page/static routes, token/Host checks, blocked database/source-file access, input errors, registration, CSV export and backup downloads.
- Workflow tests include concurrent booking attempts, concurrent payments, exact money handling, duplicate dispensing, expiry/mismatched stock, admission exclusivity, rollback after invalid invoice lines and injected audit failure, backup recovery and repeat initialization.

## Not verified

The dashboard has not been visually tested in a browser in this environment. Cloud-browser preview was blocked by automatic approval review, and no workaround was used. Browser form interaction, responsive layout and downloaded file handling should be smoke-tested on the user's Mac before publication.

The MySQL companion scripts have not been executed on a live MySQL server. Python 3.9 compatibility is targeted, but the automated suite ran on Python 3.12. No claim of production security, clinical fitness, load testing or multi-user deployment is made.

## Repeat locally

```bash
python3 -m unittest discover -s tests -v
python3 main.py --check
python3 main.py
```

Then follow `docs/demo-guide.md`. Keep any genuine patient records outside this demonstration.
