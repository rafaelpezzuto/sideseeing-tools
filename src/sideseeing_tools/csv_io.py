import csv

import pandas as pd


def load_csv_data(path, fieldnames, delimiter=','):
    """Reads a CSV file using csv.DictReader and a predefined list of fields."""
    data = []

    with open(path) as fin:
        reader = csv.reader(fin, delimiter=delimiter)

        try:
            first_row = next(reader)
        except StopIteration:
            return data

        fin.seek(0)

        if [field.strip().lower() for field in first_row] == [
            field.strip().lower() for field in fieldnames
        ]:
            reader = csv.DictReader(fin, delimiter=delimiter)
        else:
            reader = csv.DictReader(fin, fieldnames=fieldnames, delimiter=delimiter)

        for row in reader:
            new_row = {k.strip().lower(): v.strip().lower() for k, v in row.items()}
            data.append(new_row)

    return data


load_csv_data_with_pandas = pd.read_csv


def save_csv_data_with_pandas(data, path, index=False):
    data.to_csv(path, index=index)
