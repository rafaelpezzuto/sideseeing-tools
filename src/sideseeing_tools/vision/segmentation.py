"""SAM3 inference. Frame extraction remains in sideseeing_tools.media."""

import importlib
from pathlib import Path

import numpy as np

MODEL_ID = 'facebook/sam3'
MODEL_REVISION = '3c879f39826c281e95690f02c7821c4de09afae7'
SCORE_THRESHOLD = 0.5
MASK_THRESHOLD = 0.5
BATCH_SIZE = 1


class Sam3Segmenter:
    """Load one model for repeated segmentation calls, with optional dependencies."""

    def __init__(
        self, model_id=MODEL_ID, revision=MODEL_REVISION, device=None, local_files_only=False
    ):
        if not revision or revision in ('main', 'latest'):
            raise ValueError('Provide a fixed model revision')
        if not Path(model_id).is_dir() and (
            len(revision) != 40 or any(char not in '0123456789abcdef' for char in revision)
        ):
            raise ValueError('Remote model revision must be a commit hash')

        try:
            self.torch = importlib.import_module('torch')
            transformers = importlib.import_module('transformers')
            self.image_module = importlib.import_module('PIL.Image')
            model_class = transformers.Sam3Model
            processor_class = transformers.Sam3Processor
        except (ImportError, AttributeError) as error:
            raise ImportError('Install sideseeing-tools[vision] with SAM3 support') from error

        self.device = device or ('cuda' if self.torch.cuda.is_available() else 'cpu')
        self.model = model_class.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
        self.model.to(self.device).eval()
        self.processor = processor_class.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
        self.provenance = dict(
            model_id=str(model_id),
            revision=revision,
            transformers_version=transformers.__version__,
            torch_version=self.torch.__version__,
            device=self.device,
        )

    def segment(
        self,
        image_paths,
        prompt,
        batch_size=BATCH_SIZE,
        threshold=SCORE_THRESHOLD,
        mask_threshold=MASK_THRESHOLD,
    ):
        """Return boolean instance masks, xyxy boxes and scores for every image.

        Empty masks have shape (0, height, width); decoding and inference errors raise.
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError('Prompt must be non-empty text')
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError('Batch size must be a positive integer')
        if any(
            not np.isfinite(value) or not 0 <= value <= 1 for value in (threshold, mask_threshold)
        ):
            raise ValueError('Thresholds must be between zero and one')

        paths = [Path(path) for path in image_paths]

        if len({path.resolve() for path in paths}) != len(paths):
            raise ValueError('Image paths must be unique')

        records = []

        for start in range(0, len(paths), batch_size):
            batch = paths[start : start + batch_size]
            images = []

            for path in batch:
                with self.image_module.open(path) as image:
                    images.append(image.convert('RGB'))

            inputs = self.processor(
                images=images, text=[prompt] * len(images), return_tensors='pt'
            ).to(self.device)

            with self.torch.inference_mode():
                outputs = self.model(**inputs)

            results = self.processor.post_process_instance_segmentation(
                outputs,
                threshold=threshold,
                mask_threshold=mask_threshold,
                target_sizes=[image.size[::-1] for image in images],
            )

            if len(results) != len(batch):
                raise ValueError('Model returned an incomplete batch')

            for path, image, result in zip(batch, images, results):
                masks = result['masks'].detach().cpu().numpy().astype(bool)
                height, width = image.size[::-1]

                if masks.size == 0:
                    masks = np.empty((0, height, width), dtype=bool)

                scores = result['scores'].detach().cpu().numpy()
                boxes = result['boxes'].detach().cpu().numpy().reshape(-1, 4)

                if masks.shape != (len(scores), height, width) or len(boxes) != len(scores):
                    raise ValueError('Inconsistent segmentation result dimensions')
                if not np.isfinite(scores).all() or not np.isfinite(boxes).all():
                    raise ValueError('Non-finite segmentation results')

                records.append(
                    dict(
                        image_path=str(path.resolve()),
                        prompt=prompt,
                        masks=masks,
                        scores=scores,
                        boxes=boxes,
                        parameters=dict(
                            self.provenance, threshold=threshold, mask_threshold=mask_threshold
                        ),
                    )
                )

        return records
