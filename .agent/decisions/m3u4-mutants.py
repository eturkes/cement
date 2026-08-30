#!/usr/bin/env python
"""Run the M3.4 proposal-binding mutation campaign and regenerate its catalogue.

Usage:
  uv run python .agent/decisions/m3u4-mutants.py [--id M01 ...]
  uv run python .agent/decisions/m3u4-mutants.py [--verdict MODULE ...]

The runner first grades a pristine control against every verdict module. Each mutant uses
one or more exact anchors whose count must be one. It then proves that the patch changed
bytes, purges every ``__pycache__``, and launches ``uv run python`` with bytecode writes
disabled. A separate import probe proves that Python loaded the mutated file from this
worktree before the verdict tests run. Every source file is restored byte-for-byte after
each mutant, checked with ``cmp`` against a pristine copy, and checked again at campaign
exit.

A targeted existing test may establish a kill without rerunning its whole module. If that
test stays green, the runner grades every configured verdict module. Thus each ``killed``
verdict is witnessed by a named test in a configured module, while each ``survived``
verdict means the complete configured module set passed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Final, cast

ROOT = Path(__file__).resolve()
while not (ROOT / "pyproject.toml").exists():
    if ROOT == ROOT.parent:
        raise SystemExit("pyproject.toml not found above this script")
    ROOT = ROOT.parent

CATALOGUE = ROOT / ".agent" / "decisions" / "m3u4-mutants.json"
SYSTEM = "src/cement_runtime/system.py"
MODELS = "src/cement_runtime/models.py"
EXPORTS = "src/cement_runtime/__init__.py"
VERDICT_MODULES: Final = (
    "tests.test_proposal_binding",
    "tests.test_proposal_binding_battery",
    "tests.test_system",
    "tests.test_cli",
)
ENVIRONMENT: Final = dict(
    os.environ,
    PYTHONDONTWRITEBYTECODE="1",
    PYTHONPATH=str(ROOT / "src"),
)
# Two forms name a failing test. The summary header (`FAIL: name (tests.M.C.name)`) is
# authoritative because it survives both a docstring and a subtest: a docstring moves the
# verbose progress line's `... FAIL` onto the following line, away from the test id, and a
# subtest appends its own parenthetical. The battery documents every test, so the
# progress-line form alone once aborted a whole campaign with VERDICT-FAIL-WITHOUT-TEST.
# The progress line stays as the second alternative for the docstring-free modules.
FAILURE_ID = re.compile(
    r"^(?:FAIL|ERROR): \S+ \((tests\.[^)\s]+)\)"
    r"|^.*?\((tests\.[^)]+)\).*?\.\.\. (?:FAIL|ERROR)$",
    re.MULTILINE,
)
RAN_TESTS = re.compile(r"Ran (\d+) tests?")


@dataclass(frozen=True, slots=True)
class Edit:
    path: str
    old: str
    new: str


@dataclass(frozen=True, slots=True)
class Mutant:
    identifier: str
    edits: tuple[Edit, ...]
    target_tests: tuple[str, ...]
    future_killer: str


def edit(path: str, old: str, new: str) -> Edit:
    return Edit(path, old, new)


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "M01",
        (
            edit(
                SYSTEM,
                "    if type(selection) is _ProposalIds:\n",
                "    if type(selection) is _ProposalFeed:\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_request_idempotency_and_partition_isolation",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_selection_dispatch_is_exact is absent from this worktree",
    ),
    Mutant(
        "M02",
        (
            edit(
                SYSTEM,
                "        if not selection.values:\n"
                "            return _ProposalBindingSet(total=0, rows=())\n",
                "        if False:\n"
                "            return _ProposalBindingSet(total=0, rows=())\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_empty_identifier_selection_returns_empty is absent from this worktree",
    ),
    Mutant(
        "M03",
        (
            edit(
                SYSTEM,
                "        if len(set(selection.values)) != len(selection.values):\n"
                "            raise IntegrityError(\"proposal binding selection contains duplicate identifiers\")\n",
                "        if False:\n"
                "            raise IntegrityError(\"proposal binding selection contains duplicate identifiers\")\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_duplicate_identifier_selection_is_rejected is absent from this worktree",
    ),
    Mutant(
        "M04",
        (
            edit(
                SYSTEM,
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
                "            WHERE p.partition <> ? AND p.id IN ({placeholders})\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_request_idempotency_and_partition_isolation",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_identifier_selection_is_partition_exact is absent from this worktree",
    ),
    Mutant(
        "M05",
        (
            edit(
                SYSTEM,
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
                "            WHERE p.partition = ? AND p.id NOT IN ({placeholders})\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_request_idempotency_and_partition_isolation",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_identifier_selection_uses_the_requested_ids is absent from this worktree",
    ),
    Mutant(
        "M06",
        (
            edit(
                SYSTEM,
                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\n",
                "            WHERE p.partition = ? AND (? IS NULL OR p.status <> ?)\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_monotonic_feeds_survive_transitions_and_clock_rollback",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_feed_status_filter_is_exact is absent from this worktree",
    ),
    Mutant(
        "M07",
        (
            edit(
                SYSTEM,
                "              AND p.status_sequence > ?\n",
                "              AND p.status_sequence <= ?\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_monotonic_feeds_survive_transitions_and_clock_rollback",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_feed_after_sequence_is_strictly_monotonic is absent from this worktree",
    ),
    Mutant(
        "M08",
        (
            edit(
                SYSTEM,
                "            ORDER BY p.status_sequence LIMIT ?\n",
                "            ORDER BY p.status_sequence DESC LIMIT ?\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_feed_order_and_limit_are_exact is absent from this worktree",
    ),
    Mutant(
        "M09",
        (
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.status = 'pending'\n",
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition LIKE ? AND p.status = 'pending'\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_proposals_bind_partition_operation_request_and_revision",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_pending_count_partition_predicate_is_like_and_case_exact is absent",
    ),
    Mutant(
        "M10",
        (
            edit(
                SYSTEM,
                "        if count_row is None:\n"
                "            raise IntegrityError(\"pending proposal count is missing\")\n",
                "        if count_row is not None:\n"
                "            raise IntegrityError(\"pending proposal count is missing\")\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_validates_arguments_and_registered_empty_resolution",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_missing_pending_count_row_fails_closed is absent from this worktree",
    ),
    Mutant(
        "M11",
        (
            edit(
                SYSTEM,
                "            WHERE p.partition = ? AND r.operation = ? AND p.status = 'pending'\n"
                "            ORDER BY p.id LIMIT ?\n",
                "            WHERE p.partition LIKE ? AND r.operation = ? AND p.status = 'pending'\n"
                "            ORDER BY p.id LIMIT ?\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_proposals_bind_partition_operation_request_and_revision",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_pending_detail_partition_predicate_is_like_and_case_exact is absent",
    ),
    Mutant(
        "M12",
        (
            edit(
                SYSTEM,
                "            ORDER BY p.id LIMIT ?\n",
                "            ORDER BY p.id DESC LIMIT ?\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_proposals_bind_partition_operation_request_and_revision",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_pending_detail_order_is_canonical is absent from this worktree",
    ),
    Mutant(
        "M13",
        (
            edit(
                SYSTEM,
                "            ORDER BY p.id LIMIT ?\n",
                "            ORDER BY p.id LIMIT ? OFFSET 1\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_proposals_bind_partition_operation_request_and_revision",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_pending_detail_limit_starts_at_the_first_row is absent from this worktree",
    ),
    Mutant(
        "M14",
        (
            edit(
                SYSTEM,
                "        total = _stored_int(count_row[\"item_count\"], \"pending proposal count\")\n",
                "        total = min(\n"
                "            _stored_int(count_row[\"item_count\"], \"pending proposal count\"),\n"
                "            selection.limit,\n"
                "        )\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_count_reaches_the_10001_tail_with_bounded_detail",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_pending_total_is_unbounded_by_the_detail_limit is absent",
    ),
    Mutant(
        "M15",
        (
            edit(
                SYSTEM,
                "    else:\n"
                "        raise IntegrityError(\"proposal binding selection is invalid\")\n",
                "    else:\n"
                "        return _ProposalBindingSet(total=0, rows=())\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_invalid_selection_type_is_rejected is absent from this worktree",
    ),
    Mutant(
        "M16",
        (
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
                "            LEFT JOIN requests AS r ON r.partition LIKE p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
            ),
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\n",
                "            LEFT JOIN requests AS r ON r.partition LIKE p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\n",
            ),
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.status = 'pending'\n",
                "            LEFT JOIN requests AS r ON r.partition LIKE p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.status = 'pending'\n",
            ),
            edit(
                SYSTEM,
                "            JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND r.operation = ? AND p.status = 'pending'\n"
                "            ORDER BY p.id LIMIT ?\n",
                "            JOIN requests AS r ON r.partition LIKE p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND r.operation = ? AND p.status = 'pending'\n"
                "            ORDER BY p.id LIMIT ?\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_proposals_bind_partition_operation_request_and_revision",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_every_join_partition_term_is_exact is absent from this worktree",
    ),
    Mutant(
        "M17",
        (
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id LIKE p.request_id\n"
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
            ),
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\n",
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id LIKE p.request_id\n"
                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\n",
            ),
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.status = 'pending'\n",
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id LIKE p.request_id\n"
                "            WHERE p.partition = ? AND p.status = 'pending'\n",
            ),
            edit(
                SYSTEM,
                "            JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND r.operation = ? AND p.status = 'pending'\n"
                "            ORDER BY p.id LIMIT ?\n",
                "            JOIN requests AS r ON r.partition = p.partition AND r.id LIKE p.request_id\n"
                "            WHERE p.partition = ? AND r.operation = ? AND p.status = 'pending'\n"
                "            ORDER BY p.id LIMIT ?\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_request_join_is_like_and_case_exact",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_every_join_request_identifier_term_is_exact is absent",
    ),
    Mutant(
        "M18",
        (
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
                "            JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.id IN ({placeholders})\n",
            ),
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\n",
                "            JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\n",
            ),
            edit(
                SYSTEM,
                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.status = 'pending'\n",
                "            JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\n"
                "            WHERE p.partition = ? AND p.status = 'pending'\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_orphan_visibility_fails_closed_under_inner_joins is absent from this worktree",
    ),
    Mutant(
        "M19",
        (
            edit(
                SYSTEM,
                "    try:\n"
                "        proposal_id = _request_id(row[\"id\"])\n"
                "        request_id = _request_id(row[\"bound_request_id\"])\n"
                "        operation = _name(row[\"operation\"], \"operation\")\n"
                "        operation_revision = _stored_int(\n"
                "            row[\"operation_revision\"],\n"
                "            \"proposal operation revision\",\n"
                "            minimum=1,\n"
                "        )\n"
                "        input_hash = _digest(row[\"input_hash\"], \"proposal input_hash\")\n",
                "    try:\n"
                "        proposal_id = str(row[\"id\"])\n"
                "        request_id = str(row[\"bound_request_id\"])\n"
                "        operation = str(row[\"operation\"])\n"
                "        operation_revision = int(row[\"operation_revision\"])\n"
                "        input_hash = str(row[\"input_hash\"])\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_rows_validate_middle_and_last_scalars_and_bindings",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_binding_row_validates_every_scalar is absent from this worktree",
    ),
    Mutant(
        "M20",
        (
            edit(
                SYSTEM,
                "    except (IndexError, KeyError, TypeError, ValidationError) as exc:\n"
                "        raise IntegrityError(\"proposal binding row has invalid scalar fields\") from exc\n",
                "    except (IndexError, KeyError, TypeError) as exc:\n"
                "        raise IntegrityError(\"proposal binding row has invalid scalar fields\") from exc\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_rows_validate_middle_and_last_scalars_and_bindings",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_binding_row_translates_validation_errors is absent from this worktree",
    ),
    Mutant(
        "M21",
        (
            edit(
                SYSTEM,
                "        request_status=str(row[\"bound_request_status\"]),\n",
                "        request_status=str(row[\"status\"]),\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_binding_request_status_comes_from_the_request_row is absent from this worktree",
    ),
    Mutant(
        "M22",
        (
            edit(
                SYSTEM,
                "    if result.total != 1:\n"
                "        raise IntegrityError(\"proposal binding lookup returned the wrong cardinality\")\n",
                "    if result.total == 1:\n"
                "        raise IntegrityError(\"proposal binding lookup returned the wrong cardinality\")\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_request_idempotency_and_partition_isolation",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_singular_binding_requires_exactly_one_row is absent from this worktree",
    ),
    Mutant(
        "M23",
        (
            edit(
                SYSTEM,
                "    if not result.rows:\n"
                "        return None\n",
                "    if not result.rows:\n"
                "        raise IntegrityError(\"proposal binding lookup returned no rows\")\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_request_idempotency_and_partition_isolation",
        ),
        "tests.test_proposal_binding_battery.ProposalBindingAdapterTests."
        "test_singular_binding_returns_none_for_no_row is absent from this worktree",
    ),
    Mutant(
        "M24",
        (
            edit(
                SYSTEM,
                "            UPDATE requests SET status = 'rejected', updated_at_us = ?\n"
                "            WHERE partition = ? AND id = ? AND status = 'pending'\n"
                "              AND proposal_id = ?\n",
                "            UPDATE requests SET status = 'resolved', updated_at_us = ?\n"
                "            WHERE partition = ? AND id = ? AND status = 'pending'\n"
                "              AND proposal_id = ?\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence",
        ),
        "tests.test_proposal_binding_battery.ProposalStatusWriterTests."
        "test_reject_sets_only_the_rejected_pending_request is absent",
    ),
    Mutant(
        "M25",
        (
            edit(
                SYSTEM,
                "            WHERE partition = ? AND id = ? AND status = 'pending'\n"
                "              AND proposal_id = ?\n"
                "            \"\"\",\n"
                "            (now_us, binding.partition, binding.request_id, binding.proposal_id),\n",
                "            WHERE partition = ? AND id = ? AND status = 'pending'\n"
                "              AND proposal_id <> ?\n"
                "            \"\"\",\n"
                "            (now_us, binding.partition, binding.request_id, binding.proposal_id),\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence",
        ),
        "tests.test_proposal_binding_battery.ProposalStatusWriterTests."
        "test_reject_binds_the_exact_proposal_identifier is absent from this worktree",
    ),
    Mutant(
        "M26",
        (
            edit(
                SYSTEM,
                "    if final is None or example_id is None:\n"
                "        raise IntegrityError(\"a resolved request needs its confirmed output and example\")\n",
                "    if final is None and example_id is None:\n"
                "        raise IntegrityError(\"a resolved request needs its confirmed output and example\")\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalStatusWriterTests."
        "test_resolved_writer_rejects_each_missing_output_component is absent",
    ),
    Mutant(
        "M27",
        (
            edit(
                SYSTEM,
                "        SET status = 'resolved', output_json = ?, source_kind = 'confirmed',\n"
                "            example_id = ?, updated_at_us = ?\n",
                "        SET status = 'resolved', output_json = ?, source_kind = 'artifact',\n"
                "            example_id = ?, updated_at_us = ?\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_monotonic_feeds_survive_transitions_and_clock_rollback",
        ),
        "tests.test_proposal_binding_battery.ProposalStatusWriterTests."
        "test_resolved_writer_sets_every_confirmed_assignment is absent",
    ),
    Mutant(
        "M28",
        (
            edit(
                SYSTEM,
                "        WHERE partition = ? AND id = ? AND status = 'pending'\n"
                "          AND proposal_id = ?\n"
                "        \"\"\",\n"
                "        (\n"
                "            final.text,\n",
                "        WHERE partition = ? AND id = ? AND status = 'resolved'\n"
                "          AND proposal_id = ?\n"
                "        \"\"\",\n"
                "        (\n"
                "            final.text,\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_monotonic_feeds_survive_transitions_and_clock_rollback",
        ),
        "tests.test_proposal_binding_battery.ProposalStatusWriterTests."
        "test_resolved_writer_updates_only_the_pending_bound_request is absent",
    ),
    Mutant(
        "M29",
        (
            edit(
                SYSTEM,
                "            (now_us, binding.partition, binding.request_id, binding.proposal_id),\n"
                "        ).rowcount\n",
                "            (now_us, binding.partition, binding.request_id, binding.proposal_id),\n"
                "        ).rowcount + 1\n",
            ),
            edit(
                SYSTEM,
                "            binding.request_id,\n"
                "            binding.proposal_id,\n"
                "        ),\n"
                "    ).rowcount\n",
                "            binding.request_id,\n"
                "            binding.proposal_id,\n"
                "        ),\n"
                "    ).rowcount + 1\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence",
        ),
        "tests.test_proposal_binding_battery.ProposalStatusWriterTests."
        "test_writer_returns_the_database_rowcount is absent from this worktree",
    ),
    Mutant(
        "M30",
        (
            edit(
                SYSTEM,
                "        with self.store.transaction() as connection:\n"
                "            binding = _proposal_binding(\n"
                "                connection,\n"
                "                partition=partition,\n"
                "                proposal_id=proposal_id,\n"
                "            )\n"
                "            if binding is None:\n"
                "                raise NotFoundError(\"proposal does not exist in this partition\")\n"
                "            row = binding.row\n",
                "        with self.store.transaction() as connection:\n"
                "            binding = _proposal_binding(\n"
                "                connection,\n"
                "                partition=partition,\n"
                "                proposal_id=proposal_id,\n"
                "            )\n"
                "            if False:\n"
                "                raise NotFoundError(\"proposal does not exist in this partition\")\n"
                "            row = binding.row\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_request_idempotency_and_partition_isolation",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_get_proposal_translates_a_missing_binding_to_not_found is absent",
    ),
    Mutant(
        "M31",
        (
            edit(
                SYSTEM,
                "            binding = _proposal_binding(\n"
                "                connection,\n"
                "                partition=partition,\n"
                "                proposal_id=proposal_id,\n"
                "            )\n"
                "            if binding is None:\n"
                "                raise NotFoundError(\"proposal does not exist in this partition\")\n"
                "            return self._proposal_record(binding)\n",
                "            binding = _proposal_binding(\n"
                "                connection,\n"
                "                partition=partition,\n"
                "                proposal_id=f\"{proposal_id}-mutant\",\n"
                "            )\n"
                "            if binding is None:\n"
                "                raise NotFoundError(\"proposal does not exist in this partition\")\n"
                "            return self._proposal_record(binding)\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_proposal_reads_the_requested_binding is absent from this worktree",
    ),
    Mutant(
        "M32",
        (
            edit(
                SYSTEM,
                "                selection=_ProposalFeed(\n"
                "                    status=selected_status,\n"
                "                    after_sequence=after_sequence,\n"
                "                    limit=limit,\n"
                "                ),\n",
                "                selection=_ProposalFeed(\n"
                "                    status=selected_status,\n"
                "                    after_sequence=0,\n"
                "                    limit=limit,\n"
                "                ),\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_monotonic_feeds_survive_transitions_and_clock_rollback",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_proposals_forwards_every_feed_parameter is absent from this worktree",
    ),
    Mutant(
        "M33",
        (
            edit(
                SYSTEM,
                "            \"operation\": binding.operation,\n"
                "            \"operation_revision\": binding.operation_revision,\n"
                "            \"proposed_output\": proposed.value,\n",
                "            \"operation\": binding.operation,\n"
                "            \"operation_revision\": binding.operation_revision,\n"
                "            \"request_id\": binding.request_id,\n"
                "            \"proposed_output\": proposed.value,\n",
            ),
        ),
        (),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_proposal_record_has_the_exact_public_key_set is absent from this worktree",
    ),
    Mutant(
        "M34",
        (
            edit(
                SYSTEM,
                "        self._validate_proposal_shape(row)\n"
                "        input_json, proposed, provenance = self._proposal_content(binding)\n",
                "        self._validate_proposal_shape(row)\n"
                "        input_json, proposed, provenance = self._proposal_content(binding.row)\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_monotonic_feeds_survive_transitions_and_clock_rollback",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_proposal_content_receives_the_bound_row is absent from this worktree",
    ),
    Mutant(
        "M35",
        (
            edit(
                SYSTEM,
                "                    current is None\n"
                "                    or int(current[\"revision\"]) != binding.operation_revision\n"
                "                )\n",
                "                    current is None\n"
                "                    or int(current[\"revision\"]) == binding.operation_revision\n"
                "                )\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_monotonic_feeds_survive_transitions_and_clock_rollback",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_review_fences_nonreject_decisions_by_operation_revision is absent",
    ),
    Mutant(
        "M36",
        (
            edit(
                SYSTEM,
                "                    binding=binding,\n"
                "                    status=\"rejected\",\n"
                "                    final=None,\n"
                "                    example_id=None,\n",
                "                    binding=binding,\n"
                "                    status=\"resolved\",\n"
                "                    final=None,\n"
                "                    example_id=None,\n",
            ),
            edit(
                SYSTEM,
                "                binding=binding,\n"
                "                status=\"resolved\",\n"
                "                final=final,\n"
                "                example_id=example_id,\n",
                "                binding=binding,\n"
                "                status=\"rejected\",\n"
                "                final=final,\n"
                "                example_id=example_id,\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_review_forwards_exact_writer_arguments_for_each_decision is absent",
    ),
    Mutant(
        "M37",
        (
            edit(
                SYSTEM,
                "                return ReviewResult(\n"
                "                    proposal_id=proposal_id,\n"
                "                    status=\"rejected\",\n"
                "                    example_id=None,\n"
                "                    output=None,\n"
                "                )\n",
                "                return ReviewResult(\n"
                "                    proposal_id=proposal_id,\n"
                "                    status=\"accepted\",\n"
                "                    example_id=None,\n"
                "                    output=None,\n"
                "                )\n",
            ),
            edit(
                SYSTEM,
                "        return ReviewResult(\n"
                "            proposal_id=proposal_id,\n"
                "            status=proposal_status,\n"
                "            example_id=example_id,\n"
                "            output=final.value,\n"
                "        )\n",
                "        return ReviewResult(\n"
                "            proposal_id=proposal_id,\n"
                "            status=\"rejected\",\n"
                "            example_id=example_id,\n"
                "            output=final.value,\n"
                "        )\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_review_result_carries_exact_values_for_every_decision is absent",
    ),
    Mutant(
        "M38",
        (
            edit(
                SYSTEM,
                "            pending_count = pending_bindings.total\n",
                "            pending_count = len(pending_bindings.rows)\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_count_reaches_the_10001_tail_with_bounded_detail",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_function_report_uses_the_unbounded_pending_total is absent",
    ),
    Mutant(
        "M39",
        (
            edit(
                SYSTEM,
                "                selection=_PendingProposals(\n"
                "                    operation=operation,\n"
                "                    limit=projection_limit,\n"
                "                ),\n",
                "                selection=_PendingProposals(\n"
                "                    operation=operation,\n"
                "                    limit=10_000,\n"
                "                ),\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_count_reaches_the_10001_tail_with_bounded_detail",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_function_report_forwards_the_projection_limit_to_pending_detail is absent",
    ),
    Mutant(
        "M40",
        (
            edit(
                SYSTEM,
                "        return PendingProposalGap(\n"
                "            proposal_id=binding.proposal_id,\n"
                "            operation_revision=binding.operation_revision,\n"
                "            input_hash=binding.input_hash,\n"
                "        )\n",
                "        return PendingProposalGap(\n"
                "            proposal_id=binding.request_id,\n"
                "            operation_revision=binding.operation_revision,\n"
                "            input_hash=binding.input_hash,\n"
                "        )\n",
            ),
        ),
        (
            "tests.test_system.SystemTests."
            "test_function_report_pending_proposals_bind_partition_operation_request_and_revision",
        ),
        "tests.test_proposal_binding_battery.ProposalConsumerTests."
        "test_pending_gap_projects_the_exact_binding_fields is absent",
    ),
    Mutant(
        "M41",
        (
            edit(
                MODELS,
                "@dataclass(frozen=True, slots=True)\n"
                "class ReviewResult:\n",
                "@dataclass(frozen=False, slots=False)\n"
                "class ReviewResult:\n",
            ),
        ),
        (
            "tests.test_proposal_binding.FrozenPublicShapeTests."
            "test_review_result_and_proposal_shapes_are_frozen",
        ),
        "tests.test_proposal_binding_battery.PublicShapeTests."
        "test_review_result_is_frozen_and_slotted is absent from this worktree",
    ),
    Mutant(
        "M42",
        (
            edit(
                MODELS,
                "class ProposalView:\n"
                "    id: str\n"
                "    partition: str\n"
                "    operation: str\n"
                "    operation_revision: int\n"
                "    input: JSONValue\n"
                "    proposed_output: JSONValue\n"
                "    provenance: JSONValue\n"
                "    created_at_us: int\n",
                "class ProposalView:\n"
                "    id: str\n"
                "    partition: str\n"
                "    operation: str\n"
                "    operation_revision: int\n"
                "    input: JSONValue\n"
                "    proposed_output: JSONValue\n"
                "    provenance: JSONValue\n"
                "    created_at_us: int\n"
                "    request_id: str | None = None\n",
            ),
        ),
        (
            "tests.test_proposal_binding.FrozenPublicShapeTests."
            "test_review_result_and_proposal_shapes_are_frozen",
        ),
        "tests.test_proposal_binding_battery.PublicShapeTests."
        "test_proposal_view_excludes_request_identity is absent from this worktree",
    ),
    Mutant(
        "M43",
        (
            edit(
                MODELS,
                "class PendingProposalGap:\n"
                "    proposal_id: str\n"
                "    operation_revision: int\n"
                "    input_hash: str\n",
                "class PendingProposalGap:\n"
                "    proposal_id: str\n"
                "    operation_revision: int\n"
                "    input_hash: str\n"
                "    request_id: str | None = None\n",
            ),
        ),
        (
            "tests.test_proposal_binding.FrozenPublicShapeTests."
            "test_review_result_and_proposal_shapes_are_frozen",
        ),
        "tests.test_proposal_binding_battery.PublicShapeTests."
        "test_pending_gap_excludes_request_identity is absent from this worktree",
    ),
    Mutant(
        "M44",
        (
            edit(
                EXPORTS,
                "    ReviewRequired,\n"
                "    ReviewResult,\n"
                "    StaleRevisionAnomaly,\n",
                "    ReviewRequired,\n"
                "    StaleRevisionAnomaly,\n",
            ),
            edit(
                EXPORTS,
                "    \"ReviewRequired\",\n"
                "    \"ReviewResult\",\n"
                "    \"StaleRevisionAnomaly\",\n",
                "    \"ReviewRequired\",\n"
                "    \"StaleRevisionAnomaly\",\n",
            ),
        ),
        (
            "tests.test_proposal_binding.FrozenPublicShapeTests."
            "test_review_result_is_exported",
        ),
        "tests.test_proposal_binding_battery.PublicShapeTests."
        "test_review_result_is_imported_and_listed is absent from this worktree",
    ),
)


def purge_bytecode(root: Path = ROOT) -> None:
    for cache in root.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run_python(arguments: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    purge_bytecode()
    return subprocess.run(
        ["uv", "run", "python", *arguments],
        cwd=ROOT,
        env=ENVIRONMENT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_tests(names: list[str], *, verbose: bool) -> subprocess.CompletedProcess[str]:
    arguments = ["-m", "unittest"]
    if verbose:
        arguments.append("-v")
    arguments.extend(names)
    return run_python(arguments)


def output_of(completed: subprocess.CompletedProcess[str]) -> str:
    return completed.stdout + completed.stderr


def control(verdict_modules: list[str]) -> bool:
    print(
        "control: pristine workers=1 verdict_modules="
        f"{verdict_modules} ...",
        flush=True,
    )
    completed = run_tests(verdict_modules, verbose=False)
    output = output_of(completed)
    if completed.returncode != 0:
        print(output, file=sys.stderr)
        print("CONTROL: FAIL", file=sys.stderr)
        return False
    match = RAN_TESTS.search(output)
    count = match.group(1) if match else "unknown"
    print(
        "control: green workers=1 tests="
        f"{count} verdict_modules={verdict_modules}",
        flush=True,
    )
    return True


def apply_mutant(mutant: Mutant, pristine: dict[str, bytes]) -> dict[str, bytes]:
    changed: dict[str, bytes] = {}
    for patch in mutant.edits:
        before = changed.get(patch.path, pristine[patch.path]).decode("utf-8")
        count = before.count(patch.old)
        if count != 1:
            raise RuntimeError(
                f"ANCHOR-MISS {mutant.identifier} {patch.path}: count={count}"
            )
        after = before.replace(patch.old, patch.new)
        if after == before:
            raise RuntimeError(f"IDENTITY {mutant.identifier} {patch.path}")
        changed[patch.path] = after.encode("utf-8")
    for path, content in changed.items():
        target = ROOT / path
        target.write_bytes(content)
        if target.read_bytes() == pristine[path]:
            raise RuntimeError(f"PATCH-NOT-APPLIED {mutant.identifier} {path}")
    return changed


def prove_loaded(mutant: Mutant, changed: dict[str, bytes]) -> None:
    module_for = {
        SYSTEM: "cement_runtime.system",
        MODELS: "cement_runtime.models",
        EXPORTS: "cement_runtime",
    }
    for path, content in changed.items():
        expected_path = (ROOT / path).resolve()
        expected_digest = hashlib.sha256(content).hexdigest()
        probe = (
            "import hashlib, importlib, pathlib, sys\n"
            "name, expected_path, expected_digest = sys.argv[1:]\n"
            "module = importlib.import_module(name)\n"
            "loaded_path = pathlib.Path(module.__file__).resolve()\n"
            "assert loaded_path == pathlib.Path(expected_path), "
            "(loaded_path, expected_path)\n"
            "loaded_digest = hashlib.sha256(loaded_path.read_bytes()).hexdigest()\n"
            "assert loaded_digest == expected_digest, "
            "(loaded_digest, expected_digest)\n"
            "assert sys.dont_write_bytecode\n"
        )
        completed = run_python(
            ["-c", probe, module_for[path], str(expected_path), expected_digest]
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"LOAD-PROBE-FAIL {mutant.identifier} {path}\n{output_of(completed)}"
            )


def first_failure(completed: subprocess.CompletedProcess[str]) -> str | None:
    match = FAILURE_ID.search(output_of(completed))
    if match is None:
        return None
    return match.group(1) or match.group(2)


def grade_mutant(
    mutant: Mutant,
    verdict_modules: list[str],
) -> tuple[str, str]:
    for test in mutant.target_tests:
        completed = run_tests([test], verbose=True)
        if completed.returncode != 0:
            return "killed", test
    completed = run_tests(verdict_modules, verbose=True)
    if completed.returncode != 0:
        killer = first_failure(completed)
        if killer is None:
            raise RuntimeError(
                f"VERDICT-FAIL-WITHOUT-TEST {mutant.identifier}\n{output_of(completed)}"
            )
        return "killed", killer
    return "survived", mutant.future_killer


def restore_and_cmp(pristine: dict[str, bytes], copies: dict[str, Path]) -> None:
    for path, content in pristine.items():
        target = ROOT / path
        target.write_bytes(content)
        if subprocess.run(["cmp", "-s", target, copies[path]]).returncode != 0:
            raise RuntimeError(f"RESTORE-CMP-FAIL {path}")


def describe_anchor(mutant: Mutant, pristine: dict[str, bytes]) -> str:
    parts: list[str] = []
    for patch in mutant.edits:
        source = pristine[patch.path].decode("utf-8")
        line = source.count("\n", 0, source.index(patch.old)) + 1
        parts.append(f"{patch.path}:{line} exact source fragment:\n{patch.old}")
    return "\n---\n".join(parts)


def describe_mutation(mutant: Mutant) -> str:
    return "\n---\n".join(
        f"{patch.path} exact replacement text:\n{patch.new}" for patch in mutant.edits
    )


def load_catalogue() -> dict[str, object]:
    document = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    if document.get("kind") != "mutants" or not isinstance(document.get("rows"), list):
        raise RuntimeError("catalogue is not a mutants document")
    return document


def write_catalogue(document: dict[str, object]) -> None:
    CATALOGUE.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_catalogue(
    document: dict[str, object],
    mutant: Mutant,
    pristine: dict[str, bytes],
    result: str,
    killer: str,
    verdict_modules: list[str],
) -> None:
    rows = document["rows"]
    assert isinstance(rows, list)
    row = next((item for item in rows if item.get("id") == mutant.identifier), None)
    if row is None:
        raise RuntimeError(f"catalogue row is missing: {mutant.identifier}")
    row["anchor"] = describe_anchor(mutant, pristine)
    row["mutation"] = describe_mutation(mutant)
    if result == "killed":
        row["expected_killer"] = (
            f"{killer} failed; configured verdict modules: {', '.join(verdict_modules)}"
        )
    else:
        row["expected_killer"] = (
            f"{killer}; configured verdict modules all passed: "
            f"{', '.join(verdict_modules)}"
        )
    row["result"] = result
    write_catalogue(document)


def run(selection: list[str], verdict_modules: list[str]) -> int:
    by_id = {mutant.identifier: mutant for mutant in MUTANTS}
    unknown = sorted(set(selection) - set(by_id))
    if unknown:
        raise RuntimeError(f"unknown mutant ids: {unknown}")
    chosen = [mutant for mutant in MUTANTS if not selection or mutant.identifier in selection]
    if not chosen:
        raise RuntimeError("selection is empty")
    targets = sorted({patch.path for mutant in chosen for patch in mutant.edits})
    pristine = {path: (ROOT / path).read_bytes() for path in targets}

    # Pre-flight every anchor before the control runs. `apply_mutant` raises ANCHOR-MISS
    # on the first bad anchor, which ABORTS the campaign and hides every later verdict:
    # one stale anchor once cost a whole sweep and reported nothing about the other 35
    # mutants. A production fix that rewrites a targeted statement stales its anchors by
    # construction, so this is the ordinary case, not the exotic one. Report the whole
    # census at once and let one run produce the entire repair list.
    stale = [
        f"{mutant.identifier} {patch.path}: count="
        f"{pristine[patch.path].decode('utf-8').count(patch.old)}"
        for mutant in chosen
        for patch in mutant.edits
        if pristine[patch.path].decode("utf-8").count(patch.old) != 1
    ]
    if stale:
        for entry in stale:
            print(f"ANCHOR-MISS {entry}", file=sys.stderr)
        print(
            f"ANCHOR-CENSUS: {len(stale)} stale of "
            f"{sum(len(mutant.edits) for mutant in chosen)} patches; re-anchor with "
            ".agent/decisions/m3u4-reanchor-mutants.py",
            file=sys.stderr,
        )
        return 2
    document = load_catalogue()
    killed: list[str] = []
    survived: list[str] = []

    with tempfile.TemporaryDirectory(prefix="cement-m3u4-pristine-") as temporary:
        copy_root = Path(temporary)
        copies: dict[str, Path] = {}
        for index, (path, content) in enumerate(pristine.items()):
            copy = copy_root / f"{index}.pristine"
            copy.write_bytes(content)
            copies[path] = copy

        try:
            restore_and_cmp(pristine, copies)
            if not control(verdict_modules):
                return 2
            for mutant in chosen:
                changed: dict[str, bytes] = {}
                try:
                    changed = apply_mutant(mutant, pristine)
                    prove_loaded(mutant, changed)
                    result, killer = grade_mutant(mutant, verdict_modules)
                finally:
                    restore_and_cmp(pristine, copies)
                update_catalogue(
                    document,
                    mutant,
                    pristine,
                    result,
                    killer,
                    verdict_modules,
                )
                print(
                    f"{result:9} {mutant.identifier} killer={killer} "
                    f"verdict_modules={verdict_modules}",
                    flush=True,
                )
                (killed if result == "killed" else survived).append(mutant.identifier)
        finally:
            restore_and_cmp(pristine, copies)
            purge_bytecode()

    print(
        "summary: "
        f"total={len(chosen)} killed={len(killed)} equivalent=0 "
        f"survivors={survived} verdict_modules={verdict_modules} cmp=clean",
        flush=True,
    )
    return 1 if survived else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", default=[], dest="ids")
    parser.add_argument("--verdict", action="append", default=[], dest="verdict")
    arguments = vars(parser.parse_args(argv))
    ids = cast(list[str], arguments["ids"])
    verdict = cast(list[str], arguments["verdict"])
    return run(ids, verdict or list(VERDICT_MODULES))


if __name__ == "__main__":
    raise SystemExit(main())
