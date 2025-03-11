# read ines from stdin and calculate the size of the input
# each line looks like this:
# [   ] AST_L1T_00301292025000337_20250311065724_2860944.hdf           2025-03-11 06:59  119M
# the size is found in the last column, and the size is in B, M, K, G, or T
# the output should be the sum of all sizes in B
# if the input is empty the output should be 0

import sys
from typing import Union


def humanize_bytes(num_bytes: Union[int, float]) -> str:
    """
    Convert a number of bytes into a human-readable format (e.g., KB, MB, GB).

    Args:
        num_bytes: Number of bytes

    Return:
        Human-readable string
    """
    if num_bytes < 1024:
        return f"{num_bytes} bytes"
    elif num_bytes < 1024**2:
        return f"{num_bytes / 1024:.2f} Kb"
    elif num_bytes < 1024**3:
        return f"{num_bytes / 1024**2:.2f} Mb"
    elif num_bytes < 1024**4:
        return f"{num_bytes / 1024**3:.2f} Gb"
    else:
        return f"{num_bytes / 1024**4:.2f} Tb"


def calculate_size():
    size = 0
    for line in sys.stdin:
        size += convert_to_bytes(line)
    print(humanize_bytes(size))


def convert_to_bytes(line):
    size = line.split()[-1]
    value = float(size[:-1])
    unit = size[-1]
    if unit == "B":
        return value
    elif unit == "K":
        return value * 1024
    elif unit == "M":
        return value * 1024 * 1024
    elif unit == "G":
        return value * 1024 * 1024 * 1024
    elif unit == "T":
        return value * 1024 * 1024 * 1024 * 1024
    else:
        raise ValueError(f"Unknown unit: {unit}")


if __name__ == "__main__":
    calculate_size()
