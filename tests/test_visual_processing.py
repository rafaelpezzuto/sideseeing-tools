import contextlib
import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from PIL import Image

from sideseeing_tools.vision import segmentation
from sideseeing_tools.vision.results import save_segmentations, load_segmentation
from sideseeing_tools.privacy.redaction import redact_image, save_redacted_image


@pytest.fixture
def image_path(tmp_path):
    image = np.arange(12 * 16 * 3, dtype=np.uint16).reshape(12, 16, 3).astype(np.uint8)
    path = tmp_path / 'image.png'
    cv2.imwrite(str(path), image)
    return path


def record(path, empty=False):
    masks = np.zeros((0 if empty else 1, 12, 16), dtype=bool)
    if not empty:
        masks[0, 2:9, 3:12] = True
    return dict(image_path=str(path), prompt='face', masks=masks,
                scores=np.array([] if empty else [.8]),
                boxes=np.empty((0, 4)) if empty else np.array([[3, 2, 12, 9]]),
                parameters={'revision': segmentation.MODEL_REVISION})


def test_instance_roundtrip_preserves_empty_results_and_provenance(tmp_path, image_path):
    manifest = save_segmentations([record(image_path, empty=True)], tmp_path / 'results',
                                  source_id='route', timestamps_s=[43.9])
    result = load_segmentation(manifest, 0)
    assert result['masks'].shape == (0, 12, 16)
    assert result['metadata']['timestamp_s'] == 43.9
    assert json.loads(manifest.read_text())['source_id'] == 'route'


def test_rejects_missing_corrupt_and_wrong_source(tmp_path, image_path):
    manifest = save_segmentations([record(image_path)], tmp_path / 'results')
    path = manifest.parent / 'frame-000000.npz'
    data = path.read_bytes()
    path.unlink()
    with pytest.raises(FileNotFoundError):
        load_segmentation(manifest, 0)
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='Corrupt'):
        load_segmentation(manifest, 0)
    path.write_bytes(data)
    cv2.imwrite(str(image_path), np.zeros((12, 16, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match='provenance'):
        load_segmentation(manifest, 0)


def test_failed_persistence_does_not_publish_partial_run(tmp_path, image_path):
    invalid = record(image_path)
    invalid['masks'] = np.zeros((1, 2, 2), dtype=bool)
    output = tmp_path / 'results'
    with pytest.raises(ValueError, match='resolution'):
        save_segmentations([record(image_path), invalid], output)
    assert not output.exists()


@pytest.mark.parametrize('mode', ['solid', 'pixel', 'blur'])
def test_redaction_preserves_unmasked_pixels_and_input(image_path, mode):
    image = cv2.imread(str(image_path))
    original = image.copy()
    masks = record(image_path)['masks']
    output = redact_image(image, masks, mode=mode, blur_kernel=5, pixel_block_size=4)
    assert np.array_equal(image, original)
    assert np.array_equal(output[~masks[0]], image[~masks[0]])
    assert not np.array_equal(output[masks[0]], image[masks[0]])


@pytest.mark.parametrize("mode", ["blur", "pixel", "solid"])
def test_single_sensitive_pixel_is_not_ignored(image_path, mode):
    image = cv2.imread(str(image_path))
    mask = np.zeros(image.shape[:2], dtype=bool)
    mask[3, 4] = True
    output = redact_image(image, mask, mode=mode)
    assert (output[3, 4] == 0).all()


def test_missing_and_mismatched_masks_are_rejected(image_path):
    image = cv2.imread(str(image_path))
    for mask in [None, np.zeros((2, 2), dtype=bool), np.zeros((12, 16))]:
        with pytest.raises(ValueError):
            redact_image(image, mask)
    assert np.array_equal(redact_image(image, np.empty((0, 12, 16), dtype=bool)), image)


def test_lossless_export_and_no_overwrite(tmp_path, image_path):
    masks = record(image_path)['masks']
    output = tmp_path / 'redacted' / 'image.png'
    save_redacted_image(image_path, masks, output, mode='solid')
    image = cv2.imread(str(image_path))
    assert np.array_equal(cv2.imread(str(output))[~masks[0]], image[~masks[0]])
    assert json.loads((output.parent / 'redaction.json').read_text())['status'] == 'processed-not-privacy-validated'
    with pytest.raises(FileExistsError):
        save_redacted_image(image_path, masks, output)


def test_sam3_batch_conversion_without_weights(image_path):
    class Tensor:
        def __init__(self, values):
            self.values = np.asarray(values)
        def detach(self):
            return self
        def cpu(self):
            return self
        def numpy(self):
            return self.values
    class Inputs(dict):
        def to(self, device):
            return self
    class Processor:
        def __call__(self, **kwargs):
            assert kwargs['text'] == ['face']
            return Inputs()
        def post_process_instance_segmentation(self, outputs, **kwargs):
            assert kwargs['target_sizes'] == [(12, 16)]
            return [dict(masks=Tensor(np.zeros((0, 12, 16))),
                         scores=Tensor([]), boxes=Tensor(np.empty((0, 4))))]
    model = segmentation.Sam3Segmenter.__new__(segmentation.Sam3Segmenter)
    model.image_module = Image
    model.device = 'cpu'
    model.torch = SimpleNamespace(inference_mode=contextlib.nullcontext)
    model.model = lambda **kwargs: None
    model.processor = Processor()
    model.provenance = {'revision': segmentation.MODEL_REVISION}
    result = model.segment([image_path], 'face')[0]
    assert result['masks'].shape == (0, 12, 16)
    assert result['boxes'].shape == (0, 4)
    assert result['masks'].dtype == np.bool_
    with pytest.raises(ValueError, match='unique'):
        model.segment([image_path, image_path], 'face')


def test_model_requires_pinned_revision():
    with pytest.raises(ValueError, match='fixed'):
        segmentation.Sam3Segmenter(revision='main')
