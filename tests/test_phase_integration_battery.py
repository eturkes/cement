"""IMPLEMENT phase-close battery — the units together (reviewer-32).

X1: a pinned version answers raw input through its own program across resolve, export and eval.
X2: a superseded challenge no longer counts against a pin (an active example = confirmed, not
revoked, not superseded; `.agent/decisions/m45-contract.md`), exact and projected alike.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from cement_runtime import Candidate, CompilePolicy, StateError, System, parse_function
from cement_runtime.cli import main

P, OP = 'review', 'plan'


def program(*titles):
    return {'abi': 'cement-projection-v1', 'text': 'document', 'keep': [],
            'layouts': [{'name': t, 'title': t, 'entries': [{'label': 'Field'}]} for t in titles]}


def raw(title='FORM A', value='first'):
    return {'document': f'{title}\nField: {value}'}


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cement-r32-ledger-')
        self.addCleanup(self.tmp.cleanup)
        self.db = str(pathlib.Path(self.tmp.name) / 'ledger.db')
        self.system = System(self.db)
        self.system.register_operation(P, OP, policy=CompilePolicy())

    def confirm(self, value, output):
        proposal = self.system.submit_proposal(P, OP, value, candidate=Candidate(output=output, provenance={}))
        return self.system.review(P, proposal, reviewer='learning-pass', decision='accept').example_id

    def publish(self):
        self.system.compile(P, OP)
        result = self.system.verify_drafts(P, OP, verified_by='learning-pass')
        self.assertTrue(result.passed, result)
        plan = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(P, OP, expected_function_hash=plan.function_hash, promoted_by='learning-pass')
        return plan.function_hash

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(['--db', self.db, '--partition', P, *args])
        return rc, out.getvalue(), err.getvalue()

    def assert_served(self, value, expected_hash, output):
        online = self.system.resolve(P, OP, value)
        self.assertTrue(online.verification.passed, online.verification.checks)
        self.assertEqual(online.verification.function_hash, expected_hash)
        self.assertEqual((online.match.matched, online.match.output), (output is not None, output))
        rc, text, err = self.cli('function', 'export', OP)
        self.assertEqual(rc, 0, err)
        self.assertEqual(parse_function(text).function_hash, expected_hash)
        bundle = pathlib.Path(self.tmp.name) / 'bundle.json'
        bundle.write_text(text)
        rc, out, err = self.cli('function', 'eval', '--bundle', str(bundle), '--input', json.dumps(value),
                                 '--expected-function-hash', expected_hash)
        self.assertEqual(rc, 0 if output is not None else 6, err)
        result = json.loads(out)
        self.assertEqual((result['function_hash'], result['matched'], result['output']),
                         (expected_hash, output is not None, output))
        return bundle

    def test_x1_versions_own_program_across_set_promote_reset_and_all_channels(self):
        for title in ('FORM A', 'FORM B'):
            for value in ('first', 'second'):
                self.confirm(raw(title, value), {'read': title})
        self.system.set_projection(P, OP, program('FORM A', 'FORM B'), actor='learning-pass')
        v1 = self.publish()
        self.system.set_switch(P, OP, mode='follow', actor='person')
        unseen = raw('FORM B', 'brand new values')
        self.assert_served(unseen, v1, {'read': 'FORM B'})
        self.system.set_projection(P, OP, program('FORM A'), actor='learning-pass')
        self.assert_served(unseen, v1, {'read': 'FORM B'})
        v2 = self.publish()
        self.assertNotEqual(v1, v2)
        self.assert_served(unseen, v2, None)
        self.system.set_switch(P, OP, mode='pinned', function_hash=v1, actor='person')
        self.assert_served(unseen, v1, {'read': 'FORM B'})
        self.system.revise_operation(P, OP, policy=CompilePolicy(), revised_by='person')
        bundle = self.assert_served(unseen, v1, {'read': 'FORM B'})
        self.system.set_switch(P, OP, mode='off', actor='person')
        off = self.system.resolve(P, OP, unseen)
        self.assertIsNone(off.verification)
        self.assertIsNone(off.match)
        rc, out, err = self.cli('function', 'export', OP)
        self.assertEqual((rc, out), (6, ''), err)
        # A deployed bundle has no ledger switch; §3 explicitly leaves eval unchanged.
        rc, out, err = self.cli('function', 'eval', '--bundle', str(bundle), '--input', json.dumps(unseen))
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)['output'], {'read': 'FORM B'})

    def _superseded_challenge(self, projected):
        value = raw() if projected else {'ask': 'fixed'}
        old = [self.confirm(value, {'fields': ['a']}) for _ in range(2)]
        if projected:
            self.system.set_projection(P, OP, program('FORM A'), actor='learning-pass')
        v1 = self.publish()
        self.system.supersede_examples(P, OP, example_ids=old, output={'fields': ['a', 'b']}, reviewer='learning-pass')
        v2 = self.publish()
        self.assertNotEqual(v1, v2)
        self.system.set_switch(P, OP, mode='pinned', function_hash=v1, actor='person')
        self.assertTrue(self.system.resolve(P, OP, value).verification.passed)
        challenge, suspended = self.system.challenge(P, OP, value, {'fields': []}, reviewer='person')
        self.assertTrue(suspended)
        checks = {check.key: check.passed for check in self.system.resolve(P, OP, value).verification.checks}
        self.assertEqual(checks, {'pinned-receipt-rebuilds': True, 'pinned-evidence-unrevoked': True,
                                  'pinned-members-unsuspended': True, 'pinned-no-counterexample': False})
        self.system.supersede_examples(P, OP, example_ids=[challenge], output={'fields': ['a']}, reviewer='learning-pass')
        rows = {row['id']: row for row in self.system.examples(P, OP)}
        self.assertIsNotNone(rows[challenge]['superseded_by'])
        result = self.system.resolve(P, OP, value)
        self.assertTrue(result.verification.passed,
                        f'superseded challenge still blocks pin: {result.verification.checks}')
        self.assertEqual(result.match.output, {'fields': ['a']})

    def test_x2_superseded_challenge_no_longer_blocks_exact_pin(self):
        self._superseded_challenge(False)

    def test_x2_superseded_challenge_no_longer_blocks_projected_pin(self):
        self._superseded_challenge(True)



class SkillResumeBattery(unittest.TestCase):
    """X3: the saved-program resume rule also finishes a merge that stopped before supersession."""

    def test_x3_the_saved_program_resume_covers_cases_with_differing_active_outputs(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "skills/cement-learn"
        skill = " ".join((root / "SKILL.md").read_text(encoding="utf-8").split())
        workflow = " ".join((root / "references/workflow.md").read_text(encoding="utf-8").split())
        # p120 re-target (standing pin-repair approval): the resume rule moved with the derived program.
        rule = skill[skill.index("a pass that stops resumes from step 1"):]
        rule = rule[: rule.index("continue with step 4")]
        self.assertIn("pending proposals or more than one active output", rule)
        self.assertIn("a case with more than one active output stopped during the merge step", workflow)


if __name__ == '__main__':
    unittest.main()
