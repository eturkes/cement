# CI + update-automation research (M3.10)

First-party-sourced findings behind the CI unit. Verdict rows R1-R9, then the two committed
files R10 and R11. Taken byte-identical from the dispatch that produced them, since a
gitignored path is dead in every clone.

I’ll verify each row against current first-party documentation, then ground the workflow in this repository’s actual project metadata and gate constraints.
| row | finding | source |
|---|---|---|
| R1 | Current `astral-sh/setup-uv` major = **v10**. Latest release = **v10.0.1**, published **2026-08-14**, commit `20cfd1bf945f4377ade1205e4dbc17946fc9a30d`. With no `version`, the action reads `required-version` from root `uv.toml` or `pyproject.toml`; otherwise, it installs the latest uv. Cache mode defaults to `auto` on GitHub-hosted runners. Its default key includes both `pyproject.toml` and `uv.lock`. It caches the uv cache, not managed Python installations. For this repository, pin `version: "0.12.9"`, set the matrix `python-version`, enable and prune caching, and tolerate the current empty external-dependency cache. Do not override the correct default dependency glob. | [setup-uv README](https://github.com/astral-sh/setup-uv/blob/main/README.md) · [caching](https://github.com/astral-sh/setup-uv/blob/main/docs/caching.md) · [v10.0.1](https://github.com/astral-sh/setup-uv/releases/tag/v10.0.1) |
| R2 | Upstream-supported CPython lines today: **3.10** security-only until 2026-10, **3.11–3.12** security-only, and **3.13–3.14** bugfix. Current stable = **3.14.7**, released 2026-08-05. Python 3.15 remains prerelease until its planned 2026-10-01 release. Test `requires-python = ">=3.11"` on **3.11, 3.12, 3.13, and 3.14**. Do not include 3.10 as a positive compatibility target. `setup-uv`’s `python-version` selects Python through `UV_PYTHON`; `uv python install` installs Astral-managed Python. `actions/setup-python` is an alternative that can be faster because runner images cache its interpreters. Using both installation paths is redundant. | [CPython version status](https://devguide.python.org/versions/) · [Python downloads](https://www.python.org/downloads/) · [uv on GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/) |
| R3 | Use one four-version matrix with `timeout-minutes: 30` and `fail-fast: false`. Thirty minutes gives the measured ~500-second gate more than 3× headroom on smaller hosted runners. Preserve every compatibility result rather than canceling siblings after one failure. Standard GitHub-hosted matrix jobs receive separate fresh VMs, so parallel matrix execution does not put multiple suites on one runner. Keep each suite unsharded and without background work inside its job. Add lint/type-check as one separate fast job after those tools exist; do not repeat it across the Python matrix. Cancel superseded runs by event and PR/ref concurrency group. The test checkout must use `fetch-depth: 0`, because this repository’s migration battery walks historical revisions. | [Hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) · [matrix jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations) · [concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) |
| R4 | Set top-level `permissions: { contents: read }`; every omitted permission becomes `none`. Pin every action to a verified full 40-character commit SHA and retain the release comment for update tooling. GitHub’s current official wording is: **“Pinning an action to a full-length commit SHA is currently the only way to use an action as an immutable release.”** Tags are movable and therefore weaker. | [GitHub secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use) · [workflow permissions](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#permissions) |
| R5 | Use ecosystems **`github-actions`** and **`uv`**, both rooted at `/`. Dependabot supports `uv.lock` today. Current dependabot-core parses PEP 621 dependencies, PEP 735 `[dependency-groups]`, and `[build-system].requires`; it invokes uv to regenerate `uv.lock`, while build-system-only changes update `pyproject.toml` without adding the backend to the application lock. Current core pins uv **0.12.7**, close to this repository’s 0.12.9; every generated update must still pass the gate. Dependabot also updates SHA-pinned actions and their same-line version comments. Exact configuration appears under R10. | [Supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories) · [uv parser](https://github.com/dependabot/dependabot-core/blob/main/uv/helpers/lib/parser.py) · [uv updater](https://github.com/dependabot/dependabot-core/blob/main/uv/lib/dependabot/uv/file_updater/lock_file_updater.rb) · [action updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/auto-update-actions) |
| R6 | Renovate’s `pep621` manager supports `[dependency-groups]`, `[build-system].requires`, `uv.lock`, uv workspaces, legacy `[tool.uv].dev-dependencies`, and scheduled lock-file-only maintenance. The presumed PEP 735 gap is now stale: **Dependabot also supports `[dependency-groups]`**. Renovate’s relevant extra is explicit `lockFileMaintenance`; it also recognizes legacy uv dev-dependency syntax that Dependabot’s current parser omits. Renovate is not GitHub-native: install the hosted Mend Renovate GitHub App, or operate Renovate yourself through its action/CLI/container. | [Renovate PEP 621 manager](https://docs.renovatebot.com/modules/manager/pep621/) · [GitHub Actions manager](https://docs.renovatebot.com/modules/manager/github-actions/) · [running Renovate](https://docs.renovatebot.com/getting-started/running/) |
| R7 | Ranking: **1. Dependabot; 2. Renovate.** Strongest reason: Dependabot now covers all three declared update surfaces without another app, bot identity, token, or maintenance workflow. Strongest counter-argument: Renovate can periodically refresh the complete `uv.lock`, including unchanged transitive constraints, through `lockFileMaintenance`. | [Dependabot configuration](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configuring-dependabot-version-updates) · [Renovate installation](https://docs.renovatebot.com/getting-started/installing-onboarding/) |
| R8 | **Future only; do not add publishing in this phase.** Use separate build and publish jobs. Build with `uv build --no-sources`, smoke-test the wheel and sdist, then transfer `dist/` as a workflow artifact. Give only the publish job `environment: pypi` and `permissions: id-token: write`; run `uv publish --trusted-publishing always`. Trusted Publishing is the current credentialless recommendation. Before the first publish, complete release metadata, configure the PyPI publisher to match owner `eturkes`, repository `cement`, the exact workflow filename, and environment `pypi`, and protect that environment. A pending publisher can create `cement-runtime` on first publication, but it does not reserve the name. | [uv packaging](https://docs.astral.sh/uv/guides/package/) · [uv GitHub release workflow](https://docs.astral.sh/uv/guides/integration/github/) · [PyPI pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) |
| R9 | GitHub schedules use five-field POSIX cron. Supported operators are `*`, `,`, `-`, and `/`; aliases such as `@weekly` are unsupported. The minimum interval is five minutes. Schedules use UTC by default, may specify an IANA timezone, run only from the latest default-branch commit, and can be delayed or dropped during peak load. Use an off-hour minute such as `17 6 * * 1`. In a **public** repository, GitHub disables scheduled workflows after **60 days without repository activity**. | [schedule event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) · [workflow disabling](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows) |

## R10 — `/home/eturkes/Projects/cement/.github/workflows/gate.yml`

```yaml
name: Gate

on:
  pull_request:
  push:
    branches:
      - main
  schedule:
    - cron: "17 6 * * 1"
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-24.04
    timeout-minutes: 30

    strategy:
      fail-fast: false
      matrix:
        python-version:
          - "3.11"
          - "3.12"
          - "3.13"
          - "3.14"

    steps:
      - name: Check out the repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Install uv
        uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d # v10.0.1
        with:
          version: "0.12.9"
          python-version: ${{ matrix.python-version }}
          enable-cache: true
          prune-cache: true
          ignore-nothing-to-cache: true

      - name: Install Python
        run: uv python install "${{ matrix.python-version }}"

      - name: Run the test gate
        run: uv run --locked python -m unittest discover -s tests -t .

  build:
    name: Build distribution
    runs-on: ubuntu-24.04
    timeout-minutes: 10

    steps:
      - name: Check out the repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Install uv
        uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d # v10.0.1
        with:
          version: "0.12.9"
          python-version: "3.14"
          enable-cache: false

      - name: Install Python
        run: uv python install "3.14"

      - name: Build the distribution
        run: uv build
```

## R10 — `/home/eturkes/Projects/cement/.github/dependabot.yml`

```yaml
version: 2

updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "tuesday"
      time: "07:23"
      timezone: "Etc/UTC"

  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "tuesday"
      time: "07:23"
      timezone: "Etc/UTC"
```

### R1

The exact `setup-uv` inputs used above are:

```yaml
with:
  version: "0.12.9"
  python-version: ${{ matrix.python-version }}
  enable-cache: true
  prune-cache: true
  ignore-nothing-to-cache: true
```

The action’s default `cache-dependency-glob` already includes both `pyproject.toml` and `uv.lock`. An explicit narrower glob would miss build-backend-only changes.

If the project later centralizes the uv pin, this is sufficient:

```toml
[tool.uv]
required-version = "==0.12.9"
```

Then omit `with.version`; `setup-uv` discovers the pin automatically. The current `/home/eturkes/Projects/cement/pyproject.toml` has no such entry.

### R3

The full-history checkout is deliberate. `/home/eturkes/Projects/cement/tests/test_migration_battery.py` walks earlier repository revisions, so the default one-commit checkout would invalidate the gate.

The current tree has no configured linter or type checker. Once p01 lands, add one non-matrix `static` job with a short timeout. Run it in parallel with `test`; the hosted runner remains isolated.

### R5

Dependabot’s current helper parses:

- `[project].dependencies`
- `[project.optional-dependencies]`
- `[dependency-groups]`
- `[build-system].requires`

For a build-backend-only dependency, it updates `pyproject.toml` and intentionally leaves `uv.lock` unchanged. For regular and development dependencies, it updates the manifest and lockfile.

### R6

The minimal Renovate alternative would be:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    "helpers:pinGitHubActionDigests"
  ],
  "lockFileMaintenance": {
    "enabled": true
  }
}
```

This file configures Renovate but does not run it. The repository would still need the hosted App or a self-hosted Renovate execution.

### R8

The future publish boundary should be:

1. A read-only build job runs `uv build --no-sources`.
2. The build job smoke-tests both distributions.
3. The build job uploads `dist/` as a workflow artifact.
4. A separate environment-gated job downloads the artifact.
5. Only that job receives `id-token: write`.
6. It generates PEP 740 attestations and runs `uv publish --trusted-publishing always`.

PyPI’s own documentation currently prefers `pypa/gh-action-pypi-publish` over custom OIDC protocol code. Astral separately documents native Trusted Publishing through `uv publish`. Either client must use the same narrowly scoped OIDC publisher.

Before publication, the project must also close its existing release-metadata gap: `/home/eturkes/Projects/cement/pyproject.toml` currently lacks license, ownership, and project URL metadata. The project specification already requires a license and absolute URLs before publication.

Repository scope remained read-only. I did not run the ~500-second gate or `uv build`. The primary tree acquired unrelated battery-test modifications from other work while this research ran; I did not inspect or modify them.

### Sources

- [setup-uv](https://github.com/astral-sh/setup-uv)
- [Python version status](https://devguide.python.org/versions/)
- [GitHub Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Dependabot-supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
- [Dependabot uv implementation](https://github.com/dependabot/dependabot-core/tree/main/uv)
- [Renovate PEP 621 manager](https://docs.renovatebot.com/modules/manager/pep621/)
- [uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [GitHub schedule event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

RES2-DONE-1

## R12 — repository visibility, measured

`github.com/eturkes/cement` is PUBLIC: `curl https://api.github.com/repos/eturkes/cement`
returns HTTP 200 unauthenticated with `"private": false`. `gh` is not installed on this
machine; the unauthenticated API answers the question without it.

Consequences the CI unit must carry:
- R9's 60-day rule applies — GitHub disables a scheduled workflow after 60 days without
  repository activity. `push` and `pull_request` therefore carry the gate; the weekly cron is
  a supplement and nothing load-bearing may depend on it alone.
- GitHub-native secret scanning and push protection are free on public repositories, so
  gitleaks in the gate is the LOCAL half of that control rather than the only one.
- `origin/main` is current: local `main` is 1 commit ahead, 0 behind. The work is publicly
  readable as it lands, which raises the bar on the README register, the `Apache-2.0` LICENSE
  file, and the absolute-URL cleanup already carried as a `Deferred` row.
