"""Mask-driven visual redaction, independent of the segmentation model."""

import hashlib
import json
from pathlib import Path
import tempfile

import cv2
import numpy as np

BLUR_KERNEL = 31
PIXEL_BLOCK_SIZE = 16
MODES = ('blur', 'pixel', 'solid')
MIN_REGION_DIMENSION = 3


def redact_image(
    image, masks, mode='blur', blur_kernel=BLUR_KERNEL, pixel_block_size=PIXEL_BLOCK_SIZE
):
    """Transform only masked BGR pixels using boolean HxW or NxHxW masks.

    Regions narrower than three pixels use solid fill; empty stacks are valid.
    Mask completeness requires review before treating output as anonymous.
    """
    if (
        not isinstance(image, np.ndarray)
        or image.dtype != np.uint8
        or image.ndim != 3
        or image.shape[2] != 3
        or min(image.shape[:2]) < 1
    ):
        raise ValueError('Image must be a non-empty uint8 BGR image')

    masks = np.asarray(masks)

    if masks.dtype != np.bool_:
        raise ValueError('Masks must be boolean, not missing or numeric probabilities')
    if masks.ndim == 3 and masks.shape[1:] == image.shape[:2]:
        mask = np.any(masks, axis=0)
    elif masks.ndim == 2 and masks.shape == image.shape[:2]:
        mask = masks
    else:
        raise ValueError('Masks must match the image resolution')
    if mode not in MODES:
        raise ValueError(f'Mode must be one of {MODES}')
    if (
        isinstance(blur_kernel, bool)
        or not isinstance(blur_kernel, int)
        or blur_kernel < 3
        or blur_kernel % 2 == 0
    ):
        raise ValueError('Blur kernel must be an odd integer of at least three')
    if (
        isinstance(pixel_block_size, bool)
        or not isinstance(pixel_block_size, int)
        or pixel_block_size < 2
    ):
        raise ValueError('Pixel block size must be an integer of at least two')

    result = image.copy()
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))

    for label in range(1, count):
        x, y, width, height, _ = stats[label]
        region = image[y : y + height, x : x + width]

        if mode == 'solid' or min(width, height) < MIN_REGION_DIMENSION:
            transformed = np.zeros_like(region)
        elif mode == 'blur':
            transformed = cv2.GaussianBlur(region, (blur_kernel, blur_kernel), 0)
        else:
            small = cv2.resize(
                region,
                (max(1, width // pixel_block_size), max(1, height // pixel_block_size)),
                interpolation=cv2.INTER_AREA,
            )
            transformed = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)

        selection = labels[y : y + height, x : x + width] == label
        result[y : y + height, x : x + width][selection] = transformed[selection]

    return result


def save_redacted_image(image_path, masks, output_path, segmentation_provenance=None, **parameters):
    """Publish a lossless PNG and provenance together in a new directory."""
    image_path = Path(image_path)
    output_path = Path(output_path)

    if output_path.suffix.lower() != '.png':
        raise ValueError('Use lossless PNG to preserve unmasked pixels')
    if output_path.parent.exists():
        raise FileExistsError('Use a new output directory for image and provenance')

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError('Cannot decode source image')

    result = redact_image(image, masks, **parameters)
    output_path.parent.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix='.redaction-', dir=output_path.parent.parent
    ) as temporary:
        staging = Path(temporary) / 'result'
        staging.mkdir()

        if not cv2.imwrite(str(staging / output_path.name), result):
            raise OSError('Could not write redacted image')

        record = dict(
            source=str(image_path.resolve()),
            source_sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
            output=output_path.name,
            output_sha256=hashlib.sha256((staging / output_path.name).read_bytes()).hexdigest(),
            status='processed-not-privacy-validated',
            parameters=dict(
                mode='blur', blur_kernel=BLUR_KERNEL, pixel_block_size=PIXEL_BLOCK_SIZE
            ),
            segmentation_provenance=segmentation_provenance,
            masked_pixels=int(
                np.count_nonzero(np.any(masks, axis=0) if np.asarray(masks).ndim == 3 else masks)
            ),
            masks_sha256=hashlib.sha256(np.asarray(masks).tobytes()).hexdigest(),
            masks_shape=list(np.asarray(masks).shape),
        )
        record['parameters'].update(parameters)
        (staging / 'redaction.json').write_text(json.dumps(record, indent=2) + '\n')
        staging.rename(output_path.parent)

    return output_path
