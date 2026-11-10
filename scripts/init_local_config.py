"""Create first-run configuration without overwriting existing private state."""
import argparse
import json
from pathlib import Path
import sys


def initialize(project, profile, python, semantic_model='gpt-6-luna', review_model='gpt-6-luna'):
    project = Path(project).resolve()
    profile = Path(profile).expanduser().resolve()
    python = Path(python).expanduser().resolve()
    if not profile.is_file() or not python.is_file():
        raise ValueError('profile_and_python_must_exist')
    try:
        profile.relative_to(project)
    except ValueError:
        pass
    else:
        raise ValueError('keep_personal_profile_outside_repository')
    data = json.loads(profile.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or data.get('example_only') is not False:
        raise ValueError('profile_must_be_reviewed_with_example_only_false')
    config = project / 'config.local.json'
    runtime = project / 'private/local-config.json'
    knowledge = project / 'private/form-knowledge.json'
    targets = [config, runtime, knowledge]
    if any(path.exists() for path in targets):
        raise ValueError('existing_configuration_or_knowledge_not_overwritten')
    runtime_data = json.loads((project / 'templates/local-config.example.json').read_text())
    runtime_data['profile'] = str(profile)
    for key, model in [('semantic_model', semantic_model), ('review_model', review_model)]:
        if not isinstance(model, str) or not model.strip() or model in {'program', 'main'}:
            raise ValueError('explicit_model_name_required')
        runtime_data[key] = model
    config_data = {'workspace_root': '.', 'project_directory': '.',
                   'profile_file': str(profile), 'python_executable': str(python),
                   'cdp_endpoint': 'http://127.0.0.1:9333'}
    knowledge_data = json.loads((project / 'templates/form-knowledge.empty.json').read_text())
    for path, value in zip(targets, [config_data, runtime_data, knowledge_data]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    return {'status': 'configured', 'note': 'No browser connection or application action performed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    parser.add_argument('--semantic-model', default='gpt-6-luna')
    parser.add_argument('--review-model', default='gpt-6-luna')
    args = parser.parse_args()
    try:
        result = initialize(Path(__file__).resolve().parents[1], args.profile, args.python, args.semantic_model, args.review_model)
    except (OSError, ValueError) as error:
        print(json.dumps({'status': 'blocked', 'error': str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
