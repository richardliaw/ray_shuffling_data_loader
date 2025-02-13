import os

import pandas as pd
import numpy as np
from smart_open import open

import ray

#
# Data generation utilities for the shuffling data loader.
#


def generate_data(num_rows, num_files, num_row_groups_per_file,
                  max_row_group_skew, data_dir):
    assert max_row_group_skew == 0.0
    # TODO(Clark): Generate skewed row groups according to max_row_group_skew.
    results = []
    for file_index, global_row_index in enumerate(
            range(0, num_rows, num_rows // num_files)):
        num_rows_in_file = min(num_rows // num_files,
                               num_rows - global_row_index)
        results.append(
            generate_file.remote(file_index, global_row_index,
                                 num_rows_in_file, num_row_groups_per_file,
                                 data_dir))
    filenames, data_sizes = zip(*ray.get(results))
    return filenames, sum(data_sizes)


@ray.remote
def generate_file(file_index, global_row_index, num_rows_in_file,
                  num_row_groups_per_file, data_dir):
    # TODO(Clark): Generate skewed row groups according to max_row_group_skew.
    # TODO(Clark): Optimize this data generation to reduce copies and
    # progressively write smaller buffers to the Parquet file.
    buffs = []
    for group_index, group_global_row_index in enumerate(
            range(0, num_rows_in_file,
                  num_rows_in_file // num_row_groups_per_file)):
        num_rows_in_group = min(num_rows_in_file // num_row_groups_per_file,
                                num_rows_in_file - group_global_row_index)
        buffs.append(
            generate_row_group(group_index, group_global_row_index,
                               num_rows_in_group))
    df = pd.concat(buffs)
    data_size = df.memory_usage(deep=True).sum()
    filename = os.path.join(data_dir,
                            f"input_data_{file_index}.parquet.snappy")
    df.to_parquet(
        open(filename, "wb"),
        engine="pyarrow",
        compression="snappy",
        row_group_size=num_rows_in_file // num_row_groups_per_file)
    return filename, data_size


DATA_SPEC = {
    "embeddings_name0": (0, 2385, np.int64),
    "embeddings_name1": (0, 201, np.int64),
    "embeddings_name2": (0, 201, np.int64),
    "embeddings_name3": (0, 6, np.int64),
    "embeddings_name4": (0, 19, np.int64),
    "embeddings_name5": (0, 1441, np.int64),
    "embeddings_name6": (0, 201, np.int64),
    "embeddings_name7": (0, 22, np.int64),
    "embeddings_name8": (0, 156, np.int64),
    "embeddings_name9": (0, 1216, np.int64),
    "embeddings_name10": (0, 9216, np.int64),
    "embeddings_name11": (0, 88999, np.int64),
    "embeddings_name12": (0, 941792, np.int64),
    "embeddings_name13": (0, 9405, np.int64),
    "embeddings_name14": (0, 83332, np.int64),
    "embeddings_name15": (0, 828767, np.int64),
    "embeddings_name16": (0, 945195, np.int64),
    "one_hot0": (0, 3, np.int64),
    "one_hot1": (0, 50, np.int64),
    "labels": (0, 1, np.float64),
}


def generate_row_group(group_index, global_row_index, num_rows_in_group):
    buffer = {
        "key": np.array(
            range(global_row_index, global_row_index + num_rows_in_group)),
    }
    for col, (low, high, dtype) in DATA_SPEC.items():
        if dtype in (np.int16, np.int32, np.int64):
            buffer[col] = np.random.randint(
                low, high, num_rows_in_group, dtype=dtype)
        elif dtype in (np.float32, np.float64):
            buffer[col] = (
                (high - low) * np.random.rand(num_rows_in_group) + low)

    return pd.DataFrame(buffer)
