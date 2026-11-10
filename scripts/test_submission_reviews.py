import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import review_application_submission as application
import review_submission_outcome as outcome


class SubmissionReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return str(path)

    def test_plan_uses_only_observed_english_submit_and_filters_profile_credentials(self):
        evidence = self.write('evidence.json', {'candidate_controls': [
            {'id': 'action-1', 'selector': '#real-submit', 'text': 'Submit Application', 'input_value': False}]})
        profile = self.write('profile.json', {'basic': {'name': 'Synthetic', 'password': 'SYNTHETIC_SECRET'}})
        job = self.write('job.json', {'url': 'https://example.test/job/1'})
        history = self.write('history.json', {'applications': []})
        output = str(self.root / 'plan.json')
        model = SimpleNamespace(model='synthetic-reviewer', last_timings={}, ask=Mock(return_value={
            'approved': True, 'coverage_complete': True, 'eligible': True, 'history_clear': True,
            'issues': [], 'action_candidate_id': 'action-1'}))
        args = ['review', '--evidence', evidence, '--profile', profile, '--job', job,
                '--history', history, '--company', 'synthetic', '--job-id', '1',
                '--job-title', 'Engineer', '--output', output]
        with patch('sys.argv', args), patch.object(application, 'review_model', return_value=model), patch('builtins.print'):
            application.main()
        plan = json.loads(Path(output).read_text())
        self.assertEqual(plan['action']['selector'], '#real-submit')
        self.assertEqual(plan['action']['text'], 'Submit Application')
        self.assertEqual(plan['review']['model'], 'synthetic-reviewer')
        self.assertNotIn('password', model.ask.call_args.args[1]['profile']['basic'])
        model.ask.return_value['action_candidate_id'] = 'invented-control'
        with patch('sys.argv', args), patch.object(application, 'review_model', return_value=model):
            with self.assertRaisesRegex(ValueError, 'observed_submission_control_required'):
                application.main()

    def test_confirmation_candidate_cannot_prove_success(self):
        evidence = self.write('evidence.json', {'text': 'Confirm submission'})
        journal = self.write('journal.json', {'phase': 'submit', 'before': {'text': 'Application form'}})
        candidates = self.write('candidates.json', [{'id': 'outcome-1', 'kind': 'confirmation',
                                                   'selector': '#confirm', 'text': 'Confirm submission'}])
        model = SimpleNamespace(model='synthetic-reviewer', ask=Mock(return_value={
            'approved': True, 'outcome': 'submitted', 'website_candidate_id': 'outcome-1', 'issues': []}))
        args = ['review', '--evidence', evidence, '--journal', journal, '--candidates', candidates,
                '--output', str(self.root / 'review.json')]
        with patch('sys.argv', args), patch.object(outcome, 'review_model', return_value=model):
            with self.assertRaisesRegex(ValueError, 'observed_outcome_candidate_required'):
                outcome.main()
        self.assertFalse((self.root / 'review.json').exists())
