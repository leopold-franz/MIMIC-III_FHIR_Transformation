# ETL Instructions
To Transform MIMIC-III dataset to a dataframe/CSV FHIR format please run the whole mimic_ETL_FHIR.ipynb Jupyter Notebook. Make sure to modify the data_path folder to the folder with the mimic data files in a csv format not in a gz compression format. This was not yet added as a feature.

Note: the goal of this thesis is to use the mimic data to train a deep learning model, therefore the data was kept in a CSV format and not transformed to JSON/XML. To change the csv's to a JSON format read the csv's and transform each column as a dictionary key (If multiple columns have the same first word, ie itemEncounter, itemRevenue you can create an additional hierarchy first a item key, referring to a new dictionary with Encounter and Revenue as keys.). Lastly you then need to save the dictionaries as a bundle of jsons.

# MIMIC-III equivalent : FHIR Resources
- cptevents + d_cpt : claim
- noteevents : diagnosticReport
- admissions + d_icd_diagnoses : encounter
- inputevents_cv + d_items : medicationDispense
- prescriptions : medicationRequest
- chartevents + d_items, labevents + d_labitems, datetimeevents + d_items : observation
- caregivers : organization
- patients : patient
- procedures_icd  + d_icd_procedures : procedure
- outputevents, microbiologyevents : specimen

Following tables were not transformed from MIMIC-III:
- callout
- drgcodes
- icustays
- inputevents_mv
- procedureevents_mv
- services
- transfer
