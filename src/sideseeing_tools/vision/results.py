"""Persist segmentation instances and provenance without merging away detections."""

import hashlib
import json
from pathlib import Path
import tempfile

import cv2
import numpy as np

MANIFEST_VERSION = 1


def save_segmentations(records, output_dir, source_id=None, timestamps_s=None):
    """Publish ordered detections and source hashes as one complete directory."""
    records = list(records)

    if timestamps_s is not None:
        timestamps_s = list(timestamps_s)

        if len(timestamps_s) != len(records) or not np.isfinite(timestamps_s).all():
            raise ValueError('Provide one finite timestamp per record')

    destination = Path(output_dir)

    if destination.exists():
        raise FileExistsError(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='.segmentation-', dir=destination.parent) as temporary:
        staging = Path(temporary) / 'results'
        staging.mkdir()
        frames = []

        for index, record in enumerate(records):
            path = Path(record['image_path'])
            image = cv2.imread(str(path))

            if image is None:
                raise ValueError(f'Cannot decode source image: {path}')

            masks = np.asarray(record['masks'])
            scores = np.asarray(record['scores'])
            boxes = np.asarray(record['boxes'])

            if masks.dtype != np.bool_ or masks.shape != (len(scores), *image.shape[:2]):
                raise ValueError('Masks must be boolean instances at source resolution')
            if boxes.shape != (len(scores), 4) or scores.ndim != 1:
                raise ValueError('Detection scores and boxes have inconsistent dimensions')
            if not np.isfinite(scores).all() or not np.isfinite(boxes).all():
                raise ValueError('Non-finite detection scores or boxes')

            mask_file = f'frame-{index:06d}.npz'
            np.savez_compressed(staging / mask_file, masks=masks, scores=scores, boxes=boxes)
            frames.append(
                dict(
                    image_path=str(path.resolve()),
                    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    height=image.shape[0],
                    width=image.shape[1],
                    instances_file=mask_file,
                    instances_sha256=hashlib.sha256((staging / mask_file).read_bytes()).hexdigest(),
                    prompt=record['prompt'],
                    parameters=record['parameters'],
                    detections=len(scores),
                    status='processed',
                    timestamp_s=None if timestamps_s is None else float(timestamps_s[index]),
                )
            )

        manifest = dict(version=MANIFEST_VERSION, source_id=source_id, frames=frames)
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        staging.rename(destination)

    return destination / 'manifest.json'


def load_segmentation(manifest_path, frame_index, image_path=None):
    """Load one result, refusing missing/corrupt masks or mismatched source files."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())

    if manifest['version'] != MANIFEST_VERSION:
        raise ValueError('Unsupported segmentation manifest version')

    frame = manifest['frames'][frame_index]

    if frame['status'] != 'processed':
        raise ValueError('Frame was not successfully processed')

    image_path = Path(image_path or frame['image_path'])

    if hashlib.sha256(image_path.read_bytes()).hexdigest() != frame['source_sha256']:
        raise ValueError('Source image does not match segmentation provenance')

    name = frame['instances_file']

    if Path(name).name != name:
        raise ValueError('Invalid instances file path')

    path = manifest_path.parent / name

    if hashlib.sha256(path.read_bytes()).hexdigest() != frame['instances_sha256']:
        raise ValueError('Corrupt segmentation instances file')

    with np.load(path, allow_pickle=False) as arrays:
        masks = arrays['masks']
        scores = arrays['scores']
        boxes = arrays['boxes']

    if masks.dtype != np.bool_ or masks.shape != (
        frame['detections'],
        frame['height'],
        frame['width'],
    ):
        raise ValueError('Invalid instance mask dimensions')
    if scores.shape != (frame['detections'],) or boxes.shape != (frame['detections'], 4):
        raise ValueError('Invalid detection dimensions')

    return dict(masks=masks, scores=scores, boxes=boxes, metadata=frame)
