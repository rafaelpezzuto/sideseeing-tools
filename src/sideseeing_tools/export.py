import argparse
import importlib.resources
import json
import os
import shutil
from datetime import datetime
from urllib.parse import urlsplit

from jinja2 import Environment, PackageLoader

from sideseeing_tools import (
    report_geo,
    report_sensors,
    report_summary,
    report_visuals,
    report_wifi,
    sideseeing,
)

DEFAULT_TEMPLATE_PACKAGE = "sideseeing_tools.templates"
DEFAULT_TEMPLATE_NAME = "report.html"


class Report:

    def __init__(self):
        env = Environment(
            loader=PackageLoader(
                DEFAULT_TEMPLATE_PACKAGE.split('.')[0], DEFAULT_TEMPLATE_PACKAGE.split('.', 1)[1]
            )
        )
        env.filters['tojson'] = json.dumps
        self.template = env.get_template(DEFAULT_TEMPLATE_NAME)

    def generate_report(
        self,
        input_dir,
        output_dir,
        title=None,
        generate_metadata=False,
        google_api_key=None,
        version="1",
        anonymous=False,
        segmentation_manifest=None,
        redaction_files=None,
        viewer_url=None,
    ):
        """Generate an HTML report and its assets from a recording dataset."""
        if viewer_url and urlsplit(viewer_url).scheme not in ('', 'http', 'https'):
            raise ValueError('Viewer URL must be relative, HTTP or HTTPS')

        print(f"Loading directory: {input_dir}")
        ds = sideseeing.SideSeeingDS(
            root_dir=input_dir, generate_metadata=generate_metadata, google_api_key=google_api_key
        )

        os.makedirs(output_dir, exist_ok=True)

        output_html = os.path.join(output_dir, "index.html")
        output_dir_data = os.path.join(output_dir, "data")
        os.makedirs(output_dir_data, exist_ok=True)

        summary = report_summary.create_summary(ds, input_dir, google_api_key)
        gallery = []

        if segmentation_manifest is not None:
            gallery = report_visuals.prepare_visual_gallery(
                segmentation_manifest,
                redaction_files or [],
                os.path.join(output_dir_data, 'visual'),
            )

        sections = {
            'sensor': report_sensors.process_sensors_data(ds, output_dir_data),
            'wifi': report_wifi.process_wifi_data(ds, output_dir_data),
            'geo': report_geo.process_geo_data(ds, output_dir_data),
        }

        processed_sections = {key: value or {} for key, value in sections.items()}

        if not title:
            title = f"{'XYZ' if anonymous else 'SideSeeing'} Report - {os.path.basename(os.path.normpath(input_dir))}"

        context = {
            "title": title,
            "anonymous": anonymous,
            "visual_gallery": gallery,
            "viewer_url": viewer_url,
            "sections": processed_sections,
            "summary": summary,
            "generation_date": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
            "version": version,
        }

        html_data = self.template.render(context)

        with open(output_html, 'w', encoding='utf-8') as f:
            f.write(html_data)

        print(f"Report generated successfully at: {output_html}")

        self._copy_static_assets(output_dir)

    def _copy_static_assets(self, output_dir):
        """Copy the template's static assets next to the generated report."""
        destination = os.path.join(output_dir, "static")

        static_resources = importlib.resources.files(DEFAULT_TEMPLATE_PACKAGE) / "static"

        with importlib.resources.as_file(static_resources) as static_path:
            shutil.copytree(static_path, destination, dirs_exist_ok=True)

        print(f"Static assets copied to: {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate SideSeeing HTML report from dataset directory."
    )

    parser.add_argument(
        "-i", "--input_dir", help="Path to the SideSeeing dataset directory.", required=True
    )
    parser.add_argument(
        "-o", "--output_dir", help="Path to save the generated HTML report.", default="output"
    )
    parser.add_argument("-t", "--title", help="Report title.", default=None)
    parser.add_argument("-v", "--version", help="Version number", default="1")
    parser.add_argument(
        "-g",
        "--generate_metadata",
        help="Generate metadata.csv if not present.",
        action="store_true",
    )
    parser.add_argument("-k", "--google_api_key", help="Google API key")

    args = parser.parse_args()

    r = Report()
    r.generate_report(
        args.input_dir,
        args.output_dir,
        args.title,
        args.generate_metadata,
        args.google_api_key,
        args.version,
    )
