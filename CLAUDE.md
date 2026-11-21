# ecamm-runner

> **Sync:** studio, mbp

Command-line Ecamm Live broadcasts: schedule or go live now, to Facebook and LinkedIn or to Facebook only.

- **This repo is public.** Keep personal data out of it: no names, account IDs, links, episode titles or local paths. Personal values belong in `~/.config/ecamm-runner/settings.json`, which lives outside the repo. Workflow steps specific to one channel belong outside this repo too.
- The entry point is `bin/run-ecamm-stream.sh`. `docs/how-it-works.md` describes what each script looks for in Ecamm. Update it whenever an Ecamm version moves something.
- Every script checks its own end state and exits 1 when that state is wrong. Every run is a dry run unless `--go` is passed, and `--go` is the only way a broadcast gets created.
- The build number lives in `build.txt`. Bump it on every commit.
