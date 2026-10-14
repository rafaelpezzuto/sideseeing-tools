"""Load a persisted activity model with verified configuration and weights."""

import hashlib
import importlib
import json
from importlib import resources
from pathlib import Path

MODEL_PACKAGE = 'sideseeing_tools'
MODEL_DIRECTORY = 'models/activity'
CONFIGURATION_FILE = 'model.json'


def load_activity_model(model_directory=None):
    """Load a verified model bundle and its inference parameters.

    TensorFlow is optional. Caller-supplied bundles must be trusted.
    """
    directory = (
        Path(model_directory)
        if model_directory is not None
        else resources.files(MODEL_PACKAGE).joinpath(MODEL_DIRECTORY)
    )
    configuration = json.loads(directory.joinpath(CONFIGURATION_FILE).read_text())
    model_file = configuration['model_file']

    if Path(model_file).name != model_file or Path(model_file).suffix != '.keras':
        raise ValueError('Invalid model filename')

    weights = directory.joinpath(model_file)
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()

    if digest != configuration['model_sha256']:
        raise ValueError('Model weights do not match their configuration')

    parameters = configuration['inference'].copy()
    expected_shape = [parameters['window_samples'], 3]

    if configuration['input_shape'] != expected_shape:
        raise ValueError('Model and preprocessing input configurations differ')

    try:
        tensorflow = importlib.import_module('tensorflow')
    except ImportError as error:
        raise ImportError('Install sideseeing-tools[har] to load Keras activity models') from error

    with resources.as_file(weights) as path:
        model = tensorflow.keras.models.load_model(path, compile=False, safe_mode=True)

    if list(model.input_shape[1:]) != expected_shape or model.output_shape[-1] != len(
        parameters['labels']
    ):
        raise ValueError('Loaded model shape does not match preprocessing configuration')

    parameters['model_id'] = f'sha256:{digest}'

    return model, parameters
