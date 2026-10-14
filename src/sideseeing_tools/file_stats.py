import os


def get_dir_size(dir_path):
    """Calculate the total size of the directory in GB."""

    if not os.path.exists(dir_path):
        raise ValueError(f"Path '{dir_path}' does not exist.")

    if not os.path.isdir(dir_path):
        raise ValueError(f"Path '{dir_path}' is not a directory.")

    total_size = 0

    for dirpath, dirnames, filenames in os.walk(dir_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)

            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size / (1024**3)
