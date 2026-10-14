import hashlib
import json
from types import SimpleNamespace

import pytest

from sideseeing_tools.analysis import activity_models


def test_model_bundle_validates_hash_configuration_and_loaded_shape(tmp_path, monkeypatch):
    weights = tmp_path / 'activity.keras'
    weights.write_bytes(b'fixture-model')
    configuration = dict(model_file=weights.name,
                         model_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),
                         input_shape=[26, 3], inference=dict(window_samples=26,
                                                           labels=['stationary', 'walking', 'running']))
    (tmp_path / 'model.json').write_text(json.dumps(configuration))
    expected = SimpleNamespace(input_shape=(None, 26, 3), output_shape=(None, 3))
    calls = []
    def load_model(path, **kwargs):
        calls.append((path, kwargs))
        return expected
    tensorflow = SimpleNamespace(keras=SimpleNamespace(models=SimpleNamespace(load_model=load_model)))
    monkeypatch.setattr(activity_models.importlib, 'import_module', lambda name: tensorflow)
    model, parameters = activity_models.load_activity_model(tmp_path)
    assert model is expected
    assert parameters['model_id'].startswith('sha256:')
    assert calls[0][1] == dict(compile=False, safe_mode=True)
    weights.write_bytes(b'changed')
    with pytest.raises(ValueError, match='weights'):
        activity_models.load_activity_model(tmp_path)


def test_bundle_paths_cannot_escape_directory(tmp_path):
    (tmp_path / 'model.json').write_text(json.dumps(dict(model_file='../outside.keras')))
    with pytest.raises(ValueError, match='filename'):
        activity_models.load_activity_model(tmp_path)
