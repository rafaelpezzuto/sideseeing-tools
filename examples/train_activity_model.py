"""Train the activity CNN with capture-separated ST HAR partitions.

Architecture adapted from the STMicroelectronics HAR example (BSD-3-Clause).
Copyright (c) 2020, STMicroelectronics. See licenses/ST-HAR-BSD-3-Clause.txt.
"""

import argparse
import hashlib
import json
import io
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.model_selection import train_test_split
import tensorflow as tf

from sideseeing_tools.analysis.activity import (
    LABELS,
    WINDOW_SAMPLES,
    TRAINING_SCALE_MG,
    SAMPLE_RATE_HZ,
    MAX_SAMPLE_GAP_S,
    MIN_CONFIDENCE,
)

SEED = 42
TRAIN_STEP = 13
EPOCHS = 30
BATCH_SIZE = 128


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset_zip')
    parser.add_argument('output_dir')
    parser.add_argument('--center-windows', action='store_true')
    args = parser.parse_args()
    source = Path(args.dataset_zip)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)

    tf.config.threading.set_intra_op_parallelism_threads(2)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    tf.keras.utils.set_random_seed(SEED)
    tf.config.experimental.enable_op_determinism()

    with ZipFile(source) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.endswith('.csv') and Path(name).parent.name in LABELS
        )
        captures = [
            np.loadtxt(io.BytesIO(archive.read(name)), delimiter=',', dtype=np.float32)
            for name in names
        ]
        (output / 'DATASET_LICENSE.txt').write_bytes(archive.read('dataset/LICENSE'))
        (output / 'DATASET_README.md').write_bytes(archive.read('dataset/README.md'))

    if any(
        data.ndim != 2 or data.shape[1] != 3 or not np.isfinite(data).all() for data in captures
    ):
        raise ValueError('Invalid training captures')

    labels = np.array([LABELS.index(Path(name).parent.name) for name in names])
    train, test = train_test_split(
        np.arange(len(names)), test_size=0.25, stratify=labels, random_state=SEED
    )
    train, validation = train_test_split(
        train, test_size=0.2, stratify=labels[train], random_state=SEED
    )
    splits = {'train': train, 'validation': validation, 'test': test}
    features, targets = {}, {}

    for split, indexes in splits.items():
        windows, classes = [], []
        step = TRAIN_STEP if split == 'train' else WINDOW_SAMPLES

        for index in indexes:
            capture = captures[index]

            for start in range(0, len(capture) - WINDOW_SAMPLES + 1, step):
                window = capture[start : start + WINDOW_SAMPLES]

                if args.center_windows:
                    window = window - window.mean(axis=0, keepdims=True)

                windows.append(window / TRAINING_SCALE_MG)
                classes.append(labels[index])

        features[split] = np.asarray(windows, dtype=np.float32)
        targets[split] = np.asarray(classes)

    if any(
        set(splits[a]) & set(splits[b])
        for a, b in [('train', 'test'), ('train', 'validation'), ('test', 'validation')]
    ):
        raise ValueError('Capture leakage between splits')

    options = tf.data.Options()
    options.threading.private_threadpool_size = 1
    datasets = {}

    for split in splits:
        dataset = tf.data.Dataset.from_tensor_slices((features[split], targets[split]))

        if split == 'train':
            dataset = dataset.shuffle(len(targets[split]), seed=SEED)

        datasets[split] = dataset.batch(BATCH_SIZE).with_options(options)

    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(WINDOW_SAMPLES, 3)),
            tf.keras.layers.Conv1D(16, 3, activation='relu'),
            tf.keras.layers.Conv1D(8, 3, activation='relu'),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(len(LABELS), activation='softmax'),
        ]
    )
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    history = model.fit(
        datasets['train'],
        validation_data=datasets['validation'],
        epochs=EPOCHS,
        callbacks=[
            tf.keras.callbacks.ModelCheckpoint(
                str(output / 'activity.keras'), monitor='val_loss', save_best_only=True
            )
        ],
        verbose=2,
    )
    model = tf.keras.models.load_model(output / 'activity.keras', compile=False)
    predicted = np.argmax(model.predict(datasets['test'], verbose=0), axis=1)
    metrics = classification_report(
        targets['test'],
        predicted,
        labels=range(len(LABELS)),
        target_names=LABELS,
        output_dict=True,
        zero_division=0,
    )
    manifest = dict(
        model_file='activity.keras',
        model_sha256=hashlib.sha256((output / 'activity.keras').read_bytes()).hexdigest(),
        dataset_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_revision='26d649a95b1ce0f3bdc333b37777edb486620ba7',
        seed=SEED,
        epochs=EPOCHS,
        best_epoch=int(np.argmin(history.history['val_loss'])) + 1,
        tensorflow_version=tf.__version__,
        numpy_version=np.__version__,
        input_shape=[WINDOW_SAMPLES, 3],
        inference=dict(
            sample_rate_hz=SAMPLE_RATE_HZ,
            window_samples=WINDOW_SAMPLES,
            labels=list(LABELS),
            normalization_scale_mg=TRAINING_SCALE_MG,
            max_sample_gap_s=MAX_SAMPLE_GAP_S,
            min_confidence=MIN_CONFIDENCE,
            center_window=args.center_windows,
        ),
        splits={
            split: dict(captures=[names[index] for index in indexes], windows=len(targets[split]))
            for split, indexes in splits.items()
        },
        test_metrics=metrics,
        test_confusion_matrix=confusion_matrix(
            targets['test'], predicted, labels=range(len(LABELS))
        ).tolist(),
        history=history.history,
        limitations=[
            'Educational baseline; validate it for the intended application.',
            'Capture-separated evaluation; subject independence unknown.',
            'Training locations: wrist, hand, arm, pocket; chest transfer unvalidated.',
            'Stationary includes resting device on desk.',
        ],
    )
    (output / 'model.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('MODEL SAVED', output, 'test_accuracy', metrics['accuracy'], flush=True)


if __name__ == '__main__':
    main()
