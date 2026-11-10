import json
from pathlib import Path
import sys
import tempfile
import unittest

from init_local_config import initialize
from resolve_config import resolve_config


class FirstRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'skill'
        (self.project / 'templates').mkdir(parents=True)
        source = Path(__file__).resolve().parents[1]
        for name in ['local-config.example.json', 'form-knowledge.empty.json']:
            (self.project / 'templates' / name).write_bytes((source / 'templates' / name).read_bytes())
        (self.project / 'scripts').mkdir()
        (self.project / 'scripts/run_edge_cdp_application.mjs').touch()
        self.profile = self.root / 'profile.json'
        self.profile.write_text(json.dumps({'example_only': False, 'basic': {'name': 'Synthetic'}}))

    def test_fresh_configuration_resolves_and_starts_with_no_mappings(self):
        initialize(self.project, self.profile, sys.executable)
        result = resolve_config(self.project / 'config.local.json')
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(Path(result['profile_file']), self.profile.resolve())
        self.assertEqual(json.loads((self.project / 'private/form-knowledge.json').read_text()),
                         {'version': 1, 'field_map': {}, 'enum_map': {}})

    def test_existing_private_state_is_preserved(self):
        initialize(self.project, self.profile, sys.executable)
        knowledge = self.project / 'private/form-knowledge.json'
        knowledge.write_text('{"user_mapping": true}')
        before = {f: f.read_bytes() for f in [knowledge, self.project / 'config.local.json']}
        with self.assertRaisesRegex(ValueError, 'not_overwritten'):
            initialize(self.project, self.profile, sys.executable)
        for path, contents in before.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_example_cannot_become_live_profile(self):
        self.profile.write_text('{"example_only": true}')
        with self.assertRaisesRegex(ValueError, 'reviewed'):
            initialize(self.project, self.profile, sys.executable)
        self.assertFalse((self.project / 'private').exists())

    def test_profile_must_stay_outside_repository(self):
        internal = self.project / 'profile.json'
        internal.write_bytes(self.profile.read_bytes())
        with self.assertRaisesRegex(ValueError, 'outside_repository'):
            initialize(self.project, internal, sys.executable)
        self.assertFalse((self.project / 'config.local.json').exists())


if __name__ == '__main__':
    unittest.main()
