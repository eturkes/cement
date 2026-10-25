---
paths:
  - "pyproject.toml"
  - "uv.lock"
  - ".github/**"
  - ".agent/gitleaks"
  - ".agent/zizmor"
  - ".agent/shellcheck"
  - ".agent/fetch-tool"
  - "examples/command_source/pyproject.toml"
  - "examples/command_source/build-constraints.txt"
  - "prototype/webui-demo/package.json"
  - "prototype/webui-demo/pnpm-lock.yaml"
  - "prototype/webui-demo/static/vendor/**"
  - "prototype/webui-demo/static/fonts/**"
---

# Dependency + toolchain pins

- Law (owner): every pin at its latest release; a held-back pin = a `.agent/deferred.md` row naming its blocker. A hash-pinned lock's latest = a fresh compile of its header requirement (owner-ruled; grader p131): an entry that its target's own metadata pins exactly, caps or excludes by conflict (open-webui 0.12.3: 84 of 266 below PyPI latest) belongs to the target and moves with the target's bump, never by `--override`, since the lock mirrors that target; p137 holds their advisories. Dependabot (`.github/dependabot.yml`: `uv` + `github-actions`) bumps `pyproject.toml`, `uv.lock` + action refs, and moves a range (the `uv_build` floor) only once latest leaves it; the setup-uv `version:`, runner, Python legs, gitleaks, zizmor, ShellCheck, prototype + targets have no updater ⇒ `uv run python .agent/pins` (p125) prints current vs latest + source per pin (rows derived from the pinned files), rc 1 = a pin behind with no open queue row or a hold whose row is gone (holds = its `HELD` map: pin → row), rc 2 = a source failed; run it before + after any upgrade.
- Where each lives:
  - Python dev tools (exact `==`) + the `uv_build` floor = `pyproject.toml`; transitive = `uv.lock` (`uv lock --upgrade`).
  - gitleaks, zizmor, ShellCheck = `.agent/gitleaks`, `.agent/zizmor`, `.agent/shellcheck` (`version=` + the release asset's sha256 per platform = GitHub's asset `digest`; download + refusal = `.agent/fetch-tool`).
  - Provider wheel `cement-command-source` (`examples/command_source/`): hatchling = `pyproject.toml` `build-system.requires` (exact); its build dependencies = `build-constraints.txt` (hash-pinned, `uv build --require-hashes`), regenerated (Hash-pinned locks, below) on a hatchling bump; `.agent/pins` rows `command-source hatchling` + `command-source build constraints` (a fresh compile of the header vs the file).
  - CI = `.github/workflows/gate.yml`: actions by commit SHA + `# v<tag>` (`gh api repos/<r>/commits/<tag>`); uv = setup-uv `version:`; runner = `runs-on`; Python legs = `python-version`. `UV_PYTHON_PREFERENCE=only-managed` ⇒ each leg = the newest patch its pinned uv ships (the image's own Python is older), so a uv bump moves every leg's patch.
  - Prototype: Playwright + the Chromium it installs = `package.json` + `pnpm-lock.yaml`; driver.js = `static/vendor/driver.js-<version>/` (README `Third-party code`); `static/fonts/*.woff2` = `@fontsource/space-grotesk` + `@fontsource/jetbrains-mono` 5.3.0 latin files + each family's `LICENSE` (OFL-1.1, as `LICENSE-<family>`), byte-identical (`cmp` against the npm tarball).
  - Deployment targets = owner rulings (`.agent/spec.md` `Decisions`), each bumped with its live regimen: Open WebUI (`examples/open_webui/local.py` `OPEN_WEBUI`; `PYTHON` = Cement's target line; `local-requirements.txt` = the hash-pinned install, regenerated (Hash-pinned locks, below) on either bump or a `.agent/pins` `open-webui lock transitive` BEHIND; its OSV audit = `uv run python .agent/owui-audit` (pinned pip-audit, row `pip-audit (owui-audit)`; every finding held by an open queue row in `.agent/decisions/owui-audit-holds.json`, `--emit-holds <row>` rewrites them, p131)) + nucllei (`nucllei.md`; the jail stand-in image mirrors its jail); each mirror's Python is graded against its target, never the newest line: the Open WebUI `PYTHON` against the Kimi target line (the nucllei jail stand-in), the jail stand-in against nucllei's own `sandbox/Dockerfile` at the target tag (p126).
- Hash-pinned locks (`build-constraints.txt`, `local-requirements.txt`) regenerate by the header command + `--upgrade` (an existing output file otherwise keeps its pins) + `--custom-compile-command "<that header command>"`: uv otherwise writes its own argv as the header, dropping the `echo <target> |` that `test_p128_the_lock_pins_the_target_and_hashes_every_package` reads. `.agent/pins` compares every entry against a fresh compile, `name==v ; marker` lines included (torch's CUDA stack, `uvloop`, `pywin32`), keyed name + marker so a fork by marker stays two entries.
- Python lines (owner-ruled) = the latest CPython line (CI `full`, D28 included) + the Kimi target's line (the nucllei jail's 3.12 = CI `split`, the `requires-python` floor, the Open WebUI regimen's `PYTHON`); `.agent/pins` grades each. A nucllei Python bump moves all three. A new latest line moves `full`: D28 replays every range revision's OWN suite on that interpreter ⇒ a revision pinning an older interpreter's behavior reds D28, and the range then opens at the first revision that passes (`D28_START`, an owner-approved gate change; 3.15: argparse's default `suggest_on_error` reds V18 + D14 at every revision before `_JSONArgumentParser._check_value` owned the CLI's wording — `e7137f3` on 3.15.1 `FAILED (failures=2)`, `99f260a` OK — so `D28_START = 99f260a`, p123).
- A `uv.lock` change re-keys every D28 verdict (the content key holds its sha256; the CI cache key `hashFiles('uv.lock')`), and so does a new interpreter build (`sys.version`) or SQLite (`sqlite3.sqlite_version`), while a runner image alone keeps the key (`sys.platform`) ⇒ an upgrade's CI gate replays every range revision cold, and `main`'s first run after it replays cold again, because `ci/*` cache saves stay branch-scoped.
