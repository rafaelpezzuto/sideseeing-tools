from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import pandas as pd

from sideseeing_tools import report_summary

from sideseeing_tools.export import Report
from sideseeing_tools.report_visuals import prepare_visual_gallery
from sideseeing_tools.vision.results import save_segmentations
from sideseeing_tools.privacy.redaction import save_redacted_image


def test_gallery_requires_matching_redaction_and_uses_redacted_frame(tmp_path):
    image = np.full((12, 16, 3), 200, dtype=np.uint8)
    source = tmp_path / 'source.png'
    cv2.imwrite(str(source), image)
    masks = np.ones((1, 12, 16), dtype=bool)
    records = [dict(image_path=str(source), masks=masks, scores=np.array([.9]),
                    boxes=np.array([[0, 0, 16, 12]]), prompt='sidewalk', parameters={})]
    manifest = save_segmentations(records, tmp_path / 'segmentation',
                                  source_id='route', timestamps_s=[8])
    with pytest.raises(ValueError, match='Missing redaction'):
        prepare_visual_gallery(manifest, [], tmp_path / 'missing')
    output = tmp_path / 'redacted' / 'image.png'
    save_redacted_image(source, masks, output, mode='solid')
    gallery = prepare_visual_gallery(manifest, [output.parent / 'redaction.json'], tmp_path / 'gallery')
    assert gallery[0]['timestamp_s'] == 8
    assert cv2.imread(str(tmp_path / 'gallery' / 'frame-0000.png')).max() == 0

    with pytest.raises(FileExistsError):
        prepare_visual_gallery(manifest, [output.parent / 'redaction.json'], tmp_path / 'gallery')
    cv2.imwrite(str(output), image)
    with pytest.raises(ValueError, match='provenance'):
        prepare_visual_gallery(manifest, [output.parent / 'redaction.json'], tmp_path / 'changed')
    assert not (tmp_path / 'changed').exists()
    assert not (tmp_path / 'missing').exists()


def test_anonymous_template_preserves_menu_and_removes_identity():
    report = Report()
    text = report.template.render(title='XYZ Hospitals Dataset', anonymous=True,
                                   visual_gallery=[], viewer_url='viz/', generation_date='2026-10-13', version='1',
                                   summary=dict(total_instances=0, total_duration_human='00:00:00',
                                                total_size_gb=0, total_distance_km=0,
                                                sample_details=[], geo_centers_map=[]),
                                   sections=dict(sensor={}, geo={}, wifi={}))
    assert 'SideSeeing' not in text
    assert 'IME/USP' not in text
    assert 'id="sidebar"' in text
    assert 'id="anonymization-section"' in text
    assert 'Visual Results Viewer' in text
    assert 'href="viz/"' in text
    assert 'sidewalk-assessment-section' not in text


def test_report_summary_does_not_persist_source_metadata(monkeypatch):

    class Dataset:
        size = 0
        iterator = []
        def metadata(self, **kwargs):
            raise AssertionError('Must not persist source metadata')

    monkeypatch.setattr(report_summary.metadata, 'generate_metadata', lambda *args: pd.DataFrame())
    assert report_summary.create_summary(Dataset(), 'unused')['total_instances'] == 0


def test_viewer_link_rejects_script_url():
    with pytest.raises(ValueError, match='Viewer URL'):
        Report().generate_report('unused', 'unused', viewer_url='javascript:alert(1)')


def test_summary_uses_available_video_not_inherited_recording_duration(monkeypatch):

    instance = SimpleNamespace(name='cropped-route', geolocation_center=None,
                               calculate_sample_distance_traveled=lambda: 0)
    dataset = SimpleNamespace(size=1, iterator=[instance])
    metadata = pd.DataFrame([dict(name=instance.name, video_frames=50, video_fps=25,
                                 media_total_time=100, media_start_time='2024-01-01',
                                 video_resolution='16x12')])
    monkeypatch.setattr(report_summary.metadata, 'generate_metadata', lambda *args: metadata)
    monkeypatch.setattr(report_summary.file_stats, 'get_dir_size', lambda *args: 0)
    summary = report_summary.create_summary(dataset, 'unused')
    assert summary['total_duration_human'] == '00:00:02'
    assert summary['sample_details'][0]['duration'] == '00:00:02'
