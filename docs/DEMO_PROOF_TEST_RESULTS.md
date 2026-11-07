# Terminal proof verification — 2026-11-08

## Windows host

- Reviewed controller, static HTML/JS/CSS, Makefile, README, all C++/shared
  headers, load client and existing tests before implementing.
- Six portable journal/terminal regressions passed with Python 3.13:
  `python -m unittest discover -s tests -p test_proof.py -v`.
- Three existing startup synchronization regressions and the three selected
  controller parser/allowlist regressions passed. Syntax compilation passed.
- The existing loopback HTTP test initially hit Windows sandbox WinError 10013;
  rerunning with socket access outside that sandbox passed.
- No usable Ubuntu WSL distribution; Docker Linux engine was not running.
  No local Ubuntu build, `/proc` run, or VMware visual rehearsal is claimed.

## Ubuntu CI for this change

Pending execution. Earlier 2026-11-07 CI results belong to the previous
Dashboard implementation and do not verify Terminal proof changes.

The updated workflow runs `make`, `make test`, `make test-demo-ui`, and
`make test-demo-proof`. Its dashboard-measurements artifact includes
`.runtime/proof-test-results.json`: actual C++ raw output, journal events, live
terminal transcript, historical replay, errors, cancellation and rerun checks.
Runtime journals and raw output directories are ignored by Git.
