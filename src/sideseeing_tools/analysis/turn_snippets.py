"""Export candidate intervals without modifying the loaded source recording."""

import json
from pathlib import Path
import tempfile

import numpy as np

from sideseeing_tools.analysis.timing import video_reference


def extract_turn_snippets(instance, events, output_dir):
    """Export UTC-aligned candidates to source_id/turn-NNNN with provenance.

    Publish each complete snippet from staging; refuse existing destinations.
    """
    if events.attrs.get('source_id') != instance.name:
        raise ValueError('Events do not identify this source instance')
    if (
        not instance.name
        or Path(instance.name).name != instance.name
        or instance.name in ('.', '..')
    ):
        raise ValueError('Source identifier must be a single directory name')

    origin, duration = video_reference(instance)

    if events.attrs.get('reference_time') != origin.isoformat():
        raise ValueError('Event and source recording references differ')

    ids = events['event_id'].tolist()

    if len(set(ids)) != len(ids) or any(
        not isinstance(i, (int, np.integer)) or i <= 0 for i in ids
    ):
        raise ValueError('Event identifiers must be unique positive integers')

    for row in events.to_dict('records'):
        start, end = row['start_s'], row['end_s']

        if not np.isfinite([start, end]).all() or not 0 <= start < end <= duration:
            raise ValueError('Event interval lies outside the recording')

    parent = Path(output_dir) / instance.name
    destinations = [parent / f'turn-{i:04d}' for i in ids]

    if any(path.exists() for path in destinations):
        raise FileExistsError('A candidate snippet destination already exists')
    if events.empty:
        return []

    parent.mkdir(parents=True, exist_ok=True)

    for row, destination in zip(events.to_dict('records'), destinations):
        with tempfile.TemporaryDirectory(prefix='.turn-', dir=parent) as temporary:
            staging = Path(temporary) / 'recording'
            instance.extract_snippet(row['start_s'], row['end_s'], str(staging))
            provenance = dict(
                events.attrs,
                event=row,
                method='gyroscope-window-integration',
                status='candidate-not-validated',
            )

            with (staging / 'turn.json').open('w') as stream:
                json.dump(provenance, stream, indent=2)

            staging.rename(destination)

    return destinations
