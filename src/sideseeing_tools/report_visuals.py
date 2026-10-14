"""Prepare report galleries from validated segmentation and redaction results."""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import cv2
import numpy as np

from sideseeing_tools.vision.results import load_segmentation

OVERLAY_COLOR = (255, 220, 0)
OVERLAY_ALPHA = 0.35


def prepare_visual_gallery(segmentation_manifest, redaction_files, output_dir):
    """Build overlays from redacted frames matched to segmentation source hashes.

    Every source needs a redaction record; originals are never embedded.
    """
    redactions = {}

    for filename in redaction_files:
        path = Path(filename)
        record = json.loads(path.read_text())

        if record['status'] != 'processed-not-privacy-validated':
            raise ValueError('Invalid redaction processing status')
        if record['source_sha256'] in redactions:
            raise ValueError('Multiple redactions supplied for the same source')

        redactions[record['source_sha256']] = (path, record)

    manifest_path = Path(segmentation_manifest)
    manifest = json.loads(manifest_path.read_text())
    output_dir = Path(output_dir)

    if output_dir.exists():
        raise FileExistsError(output_dir)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    gallery = []

    with tempfile.TemporaryDirectory(prefix='.gallery-', dir=output_dir.parent) as temporary:
        staging = Path(temporary) / 'visual'
        staging.mkdir()

        for index, frame in enumerate(manifest['frames']):
            result = load_segmentation(manifest_path, index)
            match = redactions.get(frame['source_sha256'])

            if match is None:
                raise ValueError('Missing redaction for segmentation source')

            record_path, record = match
            name = record['output']

            if Path(name).name != name:
                raise ValueError('Invalid redacted image path')

            source = record_path.parent / name

            if hashlib.sha256(source.read_bytes()).hexdigest() != record.get('output_sha256'):
                raise ValueError('Redacted image does not match its provenance')

            image = cv2.imread(str(source))

            if image is None or image.shape[:2] != (frame['height'], frame['width']):
                raise ValueError('Invalid redacted frame')

            image_name = f'frame-{index:04d}.png'
            overlay_name = f'overlay-{index:04d}.png'
            shutil.copy2(source, staging / image_name)
            mask = np.any(result['masks'], axis=0)
            overlay = image.copy()
            overlay[mask] = (
                image[mask] * (1 - OVERLAY_ALPHA) + np.array(OVERLAY_COLOR) * OVERLAY_ALPHA
            ).astype(np.uint8)

            if not cv2.imwrite(str(staging / overlay_name), overlay):
                raise OSError('Cannot write segmentation overlay')

            gallery.append(
                dict(
                    image=f'data/visual/{image_name}',
                    overlay=f'data/visual/{overlay_name}',
                    timestamp_s=frame['timestamp_s'],
                    prompt=frame['prompt'],
                    source_id=manifest.get('source_id'),
                    detections=frame['detections'],
                )
            )

        staging.rename(output_dir)

    return gallery
