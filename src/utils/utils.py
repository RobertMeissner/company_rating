import pandas as pd


def nan_to_none(value):
    return None if pd.isna(value) else value
