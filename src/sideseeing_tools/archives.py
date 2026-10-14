import os
import zipfile


def extract_zip_archive(archive_path, output_dir):
    output_root = os.path.realpath(output_dir)

    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = os.path.realpath(os.path.join(output_root, member.filename))

            if os.path.commonpath([output_root, member_path]) != output_root:
                raise ValueError(f"Unsafe path in ZIP archive: {member.filename}")

        archive.extractall(output_root)


def extract_dataset_archive(archive_path, output_root, relative_parent=None):
    archive_name = os.path.splitext(os.path.basename(archive_path))[0]
    output_root = os.path.realpath(output_root)
    output_parts = [output_root]

    if relative_parent and relative_parent != os.curdir:
        output_parts.append(relative_parent)

    output_parts.append(archive_name)
    output_dir = os.path.realpath(os.path.join(*output_parts))

    if os.path.commonpath([output_root, output_dir]) != output_root:
        raise ValueError(f"Unsafe archive destination: {relative_parent}")

    os.makedirs(output_dir, exist_ok=True)
    extract_zip_archive(archive_path, output_dir)

    return output_dir


def find_zip_archives(root_dir):
    archive_paths = []

    for root, _, files in os.walk(root_dir):
        for file_name in files:
            if not file_name.lower().endswith('.zip'):
                continue

            archive_path = os.path.join(root, file_name)

            if zipfile.is_zipfile(archive_path):
                archive_paths.append(archive_path)

    return sorted(archive_paths)


def extract_dataset_archives(root_dir, output_root, archive_paths=None):
    output_dirs = []

    if archive_paths is None:
        archive_paths = find_zip_archives(root_dir)

    for archive_path in archive_paths:
        relative_parent = os.path.relpath(os.path.dirname(archive_path), root_dir)
        output_dir = extract_dataset_archive(archive_path, output_root, relative_parent)
        output_dirs.append(output_dir)

    return output_dirs
