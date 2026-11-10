import json
from pathlib import Path
import unittest
from unittest.mock import patch

from edge_form_graph.contracts import redacted_profile, compile_plan, ContractError
from edge_form_graph.model import CodexJsonModel
from edge_form_graph.page_planner import records_for, row_match, collection_kind
from tests.test_graph import snapshot


class OnboardingContractTests(unittest.TestCase):
    def test_template_experiences_are_available_to_planner(self):
        profile = json.loads((Path(__file__).resolve().parents[1] / 'templates/autofill-profile.template.json').read_text())
        profile['employment'] = [{'record_id': 'work-1', 'company': 'Synthetic Employer'}]
        self.assertEqual(len(records_for(profile, 'employment', '实习经历')[0]), 1)
        self.assertEqual(records_for(profile, 'employment', 'Work Experience')[0][0][0]['record_collection'], '/employment')

    def test_legacy_internship_pointer_is_preserved(self):
        profile = {'internships': [{'record_id': 'intern-1', 'company': 'Synthetic Employer'}]}
        binding = records_for(profile, 'employment', '实习经历')[0][0][0]
        self.assertEqual(binding['record_collection'], '/internships')

    def test_school_name_must_match_even_when_degree_matches(self):
        for school_key in ('school', 'school_name'):
            profile = {'education': [{'record_id': 'edu-1', school_key: 'Synthetic A', 'education_level': '本科'}]}
            candidates = records_for(profile, 'education', '教育')[0]
            def row(school):
                return {'snapshot': {'fields': [{'label': '学校名称', 'value': school, 'kind': 'text'},
                                                {'label': '学历', 'value': '本科', 'kind': 'text'}]}}
            self.assertEqual(row_match(row('Synthetic B'), candidates, 'education')[0], 'ambiguous')
            self.assertEqual(row_match(row('Synthetic A'), candidates, 'education')[0], 'matched')

    def test_missing_canonical_school_cannot_prove_identity(self):
        candidates = records_for({'education': [{'record_id': 'edu-1', 'education_level': '本科'}]}, 'education', '教育')[0]
        row = {'snapshot': {'fields': [{'label': '学校名称', 'value': 'Synthetic B'}, {'label': '学历', 'value': '本科'}]}}
        self.assertEqual(row_match(row, candidates, 'education')[0], 'ambiguous')

    def test_nested_credentials_never_reach_mapping_model(self):
        profile = {'basic': {'name': 'Synthetic', 'password': 'SYNTHETIC_SECRET', 'api_key': 'SYNTHETIC_KEY', 'accessToken': 'SYNTHETIC_ACCESS', 'apiKey': 'SYNTHETIC_API'},
                   'identity': {'identity_document_number': 'SYNTHETIC_ID'},
                   'contact': {'email': 'synthetic@example.test'}, 'token': 'SYNTHETIC_TOKEN'}
        model = CodexJsonModel('synthetic-model')
        with patch.object(model, 'ask', return_value={}) as ask:
            model.map(profile, snapshot())
        sent = ask.call_args.args[1]['profile']
        self.assertNotIn('password', sent['basic'])
        self.assertNotIn('api_key', sent['basic'])
        self.assertNotIn('token', sent)
        self.assertNotIn('accessToken', sent['basic'])
        self.assertNotIn('apiKey', sent['basic'])
        self.assertEqual(sent['basic']['name'], 'Synthetic')
        self.assertEqual(sent['identity']['identity_document_number'], 'SYNTHETIC_ID')

    def test_protected_snapshot_value_is_not_sent_as_data(self):
        data = {'fields': [{'label': 'Password', 'value': 'SYNTHETIC_SECRET', 'protected': True}]}
        self.assertIsNone(redacted_profile(data)['fields'][0]['value'])

    def test_password_cannot_be_mapped_to_other_field(self):
        p = {'mappings': [{'field_id': '#school', 'source': '/password', 'transform': 'identity', 'depends_on': []}], 'deferred': []}
        with self.assertRaises(ContractError):
            compile_plan({'password': 'SYNTHETIC_SECRET'}, snapshot(), p)

    def test_english_resume_sections_are_classified(self):
        for label, kind in [('Education', 'education'), ('Work Experience', 'employment'),
                            ('Internships', 'employment'), ('Projects', 'projects'), ('Publications', 'research')]:
            self.assertEqual(collection_kind(label), kind)

    def test_conflicting_education_aliases_require_resolution(self):
        profile = {'education': [{'record_id': 'edu-1', 'school': 'Synthetic A', 'school_name': 'Synthetic B'}]}
        with self.assertRaisesRegex(ValueError, 'conflicting_school_aliases'):
            records_for(profile, 'education', 'Education')

    def test_duplicate_employment_alias_records_cannot_be_added_twice(self):
        record = {'record_id': 'work-1', 'company': 'Synthetic Employer'}
        with self.assertRaisesRegex(ValueError, 'duplicate_employment_record_id'):
            records_for({'employment': [record], 'internships': [record]}, 'employment', 'Internships')
