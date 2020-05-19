#!/usr/bin/env python
# coding: utf-8
# Author: Leopold Franz (ETH Zürich)

import os
import pandas
import numpy


def transform(input_path, output_path):
    """
    Transforms a MIMIC-III CSV table into a collection of FHIR resources, that are saved as a JSON file. If the input
    path or the output path have '.gz' at the end the file read directly from a compressed file or saved to a compressed
    file.

    :param input_path: str File path of Original MIMIC-III table with '.csv' or '.csv.gz' as extension
    :param output_path: str File path where FHIR collection should be saved. Needs to have '.json' or '.json.gz'
    extension.
    :return: pd.DataFrame Dataframe with flat FHIR resources as entries.
    """
    df = None

    return df