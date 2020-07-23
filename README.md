# MIMIC-III_FHIR_Transformation

Python package to transform the MIMIC-III dataset into a flat scalable, hierarchical FHIR format.

## Setup
1. Download this repository to your machine.
2. Navigate to the base directory 'MIMIC-III_FHIR_Transformation'.
3. Create a new virtual environment with virtualenv or conda, or from an already existing virtual environment run 
```bash
pip install -e .
```
4. Try it out and transform MIMIC-III to the FHIR format!
From within your script import the package and run mimic_fhir_transformation.transform_table(source_mimic_table_path, output_table path, (depending on table add auxiliary table path))
