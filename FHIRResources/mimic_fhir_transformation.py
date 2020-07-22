#!/usr/bin/env python
# coding: utf-8
# Author: Leopold Franz (ETH Zürich)

from pathlib import Path
import pandas as pd
import numpy as  np


def transform_table(table_file_path, output_path, auxiliary_table_path=''):
    """
    Transforms a MIMIC-III CSV table into a collection of FHIR resources, that are saved as a JSON file. If the input
    path or the output path have '' at the end the file read directly from a compressed file or saved to a compressed
    file.

    :param table_file_path: str File path of Original MIMIC-III table with '.csv' or '.csv' as extension
    :param auxiliary_table_path: str Path of auxiliary table if needed.
    :param output_path: str Output path where FHIR collection should be saved. If you pass a folder path then the
     corresponding fhir resource name will be used as a file name and the file will be saved with a gzip extension.
    :return: pd.DataFrame Dataframe with flat FHIR resources as entries.
    """

    if Path(table_file_path).suffix == '':
        file_path = Path(table_file_path).stem

    if Path(file_path).name == 'ADMISSIONS.csv':
        df = transform_admissions(table_file_path, output_path)
    elif Path(file_path).name == 'CAREGIVERS.csv':
        df = transform_caregivers(table_file_path, output_path)
    elif Path(file_path).name == 'CHARTEVENTS.csv':
        df = transform_chartevents(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'CPTEVENTS.csv':
        df = transform_cptevents(table_file_path, output_path)
    elif Path(file_path).name == 'DATETIMEEVENTS.csv':
        df = transform_datetimeevents(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'ICUSTAYS.csv':
        df = transform_icustays(table_file_path, output_path)
    elif Path(file_path).name == 'INPUTEVENTS_CV.csv':
        df = transform_inputevents_cv(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'INPUTEVENTS_MV.csv':
        df = transform_inputevents_mv(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'LABEVENTS.csv':
        df = transform_labevents(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'MICROBIOLOGYEVENTS.csv':
        df = transform_microbiologyevents(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'NOTEEVENTS.csv':
        df = transform_noteevents(table_file_path, output_path)
    elif Path(file_path).name == 'OUTPUTEVENTS.csv':
        df = transform_outputevents(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'PATIENTS.csv':
        df = transform_patients(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'PRESCRIPTIONS.csv':
        df = transform_prescriptions(table_file_path, output_path)
    elif Path(file_path).name == 'PROCEDUREEVENTS_MV.csv':
        df = transform_procedurevents_mv(table_file_path, auxiliary_table_path, output_path)
    elif Path(file_path).name == 'PROCEDURES_ICD.csv':
        df = transform_procedures_icd(table_file_path, output_path)
    elif Path(file_path).name == 'SERVICES.csv':
        df = transform_services(table_file_path, output_path)
    else:
        AssertionError("Unknown input file")

    return df


# # Create each FHIR resource type table individually

# ## fhir.patients table
#
# #### MAPPING:<br>
#
# - As soon as this table is joineed with another table the identifier column needs to be renamed to 'subject'
# - We could add the deathtime from the admissions table, which could be more accurate.
# - Check https://www.hl7.org/fhir/valueset-languages.html for language codes(probably easiest to just create a bigger
# version defining the language the language name is in and the language name itself)
# - Using MARITIAL_STATUS from last encounter
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.patients.SUBJECT_ID | fhir.patient.identifier|
# |2|mimic.patients.GENDER | fhir.patient.gender|
# |3|mimic.patients.DOB | fhir.patient.birthDate|
# |4|mimic.patients.DOD | fhir.patient.deceasedDateTime|
# |5|mimic.admissions.LANGUAGE | fhir.patient.communication_language|
# |6|mimic.admissions.MARITIAL_STATUS | fhir.patient.maritialStatus|


def transform_patients(patients_file_path, admissions_file_path, output_path):
    patients = pd.read_csv(patients_file_path, usecols=['SUBJECT_ID', 'GENDER', 'DOB', 'DOD'])
    admissions = pd.read_csv(admissions_file_path, usecols=['SUBJECT_ID', 'LANGUAGE', 'MARITAL_STATUS'])

    # Add the marital status and language information from the admissions dataframe by using the information from the
    # last admission.
    ad_temp = admissions.groupby('SUBJECT_ID').tail(1)
    patients = pd.merge(patients, ad_temp, on='SUBJECT_ID')

    # Rename columns to FHIR names
    patients.rename(columns={'SUBJECT_ID': 'identifier',
                             'GENDER': 'gender',
                             'DOB': 'birthDate',
                             'DOD': 'deceasedDateTime',
                             'LANGUAGE': 'communication_language',
                             'MARITAL_STATUS': 'maritalStatus'}, inplace=True)

    # Output to csv
    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('patient.csv.gz')
    patients.to_csv(output_path, index=False)
    return patients


# ## fhir.encounter table
#
# #### ADMISSIONS MAPPING:<br>
#
# - location column (add all interim locations and periods)
# - - Could add location field by using Transfer and SERVICES mimictables
# - - Combine both mimic.admissions.EDREGTIME and mimic.admissions.EDOUTTIME to add time period for
# fhir.encounter.locations list
# - mimic.admissions.INSURANCE - Might be better placed in claims fhir table
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.admissions.SUBJECT_ID|fhir.encounter.subject|
# |2|mimic.admissions.HADM_ID|fhir.encounter.identifier|
# |3|'admission'|fhir.encounter.serviceType|
# |4|mimic.admissions.ADMITTIME|fhir.encounter.period_start|
# |5|mimic.admissions.DISCHTIME|fhir.encounter.period_end|
# |6|mimic.admissions.(DISCHTIME - ADMITTIME)|fhir.encounter.length|
# |7|mimic.admissions.ADMISSION_TYPE|fhir.encounter.type|
# |8|mimic.admissions.ADMISSION_LOCATION|fhir.encounter.hospitalization_origin|
# |9|mimic.admissions.DISCHARGE_LOCATION|fhir.encounter.hospitalization_destination|
# |10|mimic.admissions.INSURANCE|fhir.encounter.serviceProvider|
# |11|mimic.DIAGNOSES_ICD.ICD9_CODE|fhir.encounter.diagnosis_condition|
# |12|mimic.DIAGNOSES_ICD.SEQ_NUM|fhir.encounter.diagnosis_condition|
# |13|mimic.admissions.DIAGNOSIS|fhir.encounter.diagnosis_description|
#
# #### ICUSTAYS MAPPING:<br>
#
# - Could improve location field by using Transfer table
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.icustays.SUBJECT_ID|fhir.encounter.subject|
# |2|mimic.icustays.HADM_ID|fhir.encounter.partOf|
# |3|mimic.icustays.ICUSTAY_ID|fhir.encounter.identifier|
# |4|'icustay'|fhir.encounter.serviceType|
# |5|mimic.icustays.INTIME|fhir.encounter.period_start|
# |6|mimic.icustays.OUTTIME|fhir.encounter.period_end|
# |7|mimic.icustays.(OUTTIME - INTIME)|fhir.encounter.length|
# |8|mimic.icustays.DBSOURCE|fhir.encounter.type|
# |9|mimic.icustays.FIRST_CAREUNIT|fhir.encounter.location|
# |10|mimic.icustays.LAST_CAREUNIT|fhir.encounter.location|
# |11|mimic.icustays.FIRST_WARDID|fhir.encounter.location_id|
# |12|mimic.icustays.LAST_WARDID|fhir.encounter.location_id|


def transform_admissions(admissions_file_path, diagnoses_icd_file_path, output_path):
    admissions = pd.read_csv(admissions_file_path, usecols=['SUBJECT_ID', 'HADM_ID', 'ADMITTIME', 'DISCHTIME',
                                                            'ADMISSION_TYPE', 'ADMISSION_LOCATION',
                                                            'DISCHARGE_LOCATION', 'INSURANCE', 'DIAGNOSIS'])
    diagnoses_icd = pd.read_csv(diagnoses_icd_file_path)

    # Convert times to datetime formats and add length column
    admissions.ADMITTIME = pd.to_datetime(admissions.ADMITTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    admissions.DISCHTIME = pd.to_datetime(admissions.DISCHTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    admissions['length'] = admissions['DISCHTIME'] - admissions['ADMITTIME']

    # Add diagnoses icd list. Icd codes automatically in the order of priority (descending priority), which is important
    # for billing.
    diagnoses_icd_list = diagnoses_icd.groupby('HADM_ID')['ICD9_CODE'].apply(list).reset_index(
        name='diagnosis_condition')
    admissions = pd.merge(admissions, diagnoses_icd_list, on='HADM_ID')

    # Define encounter service type
    admissions['serviceType'] = 'admission'

    # Rename columns to FHIR names
    admissions.rename(columns={'SUBJECT_ID': 'subject',
                               'HADM_ID': 'identifier',
                               'ADMITTIME': 'period_start',
                               'DISCHTIME': 'period_end',
                               'ADMISSION_TYPE': 'type',
                               'ADMISSION_LOCATION': 'hospitalization_origin',
                               'DISCHARGE_LOCATION': 'hospitalization_destination',
                               'INSURANCE': 'serviceProvider',
                               'DIAGNOSIS': 'diagnosis_description'}, inplace=True)

    admissions = admissions.reindex(columns=['subject',
                                             'identifier',
                                             'period_start',
                                             'period_end',
                                             'length',
                                             'type',
                                             'hospitalization_origin',
                                             'hospitalization_destination',
                                             'serviceProvider',
                                             'diagnosis_condition',
                                             'diagnosis_description'], copy=False)

    # Output to csv
    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('encounter.csv.gz')
    admissions.to_csv(output_path, index=False)
    return admissions


def transform_icustays(icustays_file_path, output_path):
    icustays = pd.read_csv(icustays_file_path)

    # Convert times to datetime formats and add length column
    icustays.INTIME = pd.to_datetime(icustays.INTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    icustays.OUTTIME = pd.to_datetime(icustays.OUTTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    icustays['length'] = icustays['OUTTIME'] - icustays['INTIME']

    # Combine ADMISSION_LOCATION and DISCHARGE_LOCATION to location list
    icustays['location'] = icustays[['FIRST_CAREUNIT', 'LAST_CAREUNIT']].values.tolist()
    icustays.drop(['FIRST_CAREUNIT', 'LAST_CAREUNIT'], axis=1, inplace=True)
    icustays['location_id'] = icustays[['FIRST_WARDID', 'LAST_WARDID']].values.tolist()
    icustays.drop(['FIRST_WARDID', 'LAST_WARDID'], axis=1, inplace=True)

    # Define encounter service type
    icustays['serviceType'] = 'icustay'

    # Rename columns to FHIR names
    icustays.rename(columns={'SUBJECT_ID': 'subject',
                             'HADM_ID': 'partOf',
                             'ICUSTAY_ID': 'identifier',
                             'DBSOURCE': 'type',
                             'INTIME': 'period_start',
                             'OUTTIME': 'period_end'}, inplace=True)

    icustays = icustays.reindex(columns=['subject',
                                         'partOf',
                                         'identifier',
                                         'period_start',
                                         'period_end',
                                         'length',
                                         'type',
                                         'serviceType',
                                         'location',
                                         'location_id'], copy=False)

    # Output to csv
    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('encounter_icustays.csv.gz')
    icustays.to_csv(output_path, index=False)
    return icustays


# ## fhir.claim table
#
# #### MAPPING: <br>
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.cptevents.ROW_ID|fhir.claim.identifier|
# |2|mimic.cptevents.SUBJECT_ID|fhir.claim.subject|
# |3|mimic.cptevents.HADM_ID|fhir.claim.encounter|
# |4|mimic.cptevents.COSTCENTER|fhir.claim.provider|
# |5|mimic.cptevents.CHARTDATE|fhir.claim.created|
# |6|mimic.cptevents.CPT_NUMBER|fhir.claim.item_category_cpt_num|
# |7|mimic.cptevents.CPT_SUFFIX|fhir.claim.item_category_cpt_str|
# |8|mimic.cptevents.TICKET_ID_SEQ|fhir.claim.item_sequence|
# |9|mimic.cptevents.DESCRIPTION|fhir.claim.item_detail|
# |10|mimic.cptevents.SECTIONHEADER|fhir.claim.type|
# |11|mimic.cptevents.SUBSECTIONHEADER|fhir.claim.subType|
#


def transform_cptevents(cptevents_file_path, output_path):
    cptevents = pd.read_csv(cptevents_file_path)
    cptevents.CHARTDATE = pd.to_datetime(cptevents.CHARTDATE, format='%Y-%m-%d', errors='coerce')

    # Drop extra columns
    cptevents.drop(['CPT_CD'], axis=1, inplace=True)

    cptevents.rename(columns={'ROW_ID': 'identifier',
                              'SUBJECT_ID': 'subject',
                              'HADM_ID': 'encounter',
                              'CHARTDATE': 'created',
                              'SECTIONHEADER': 'type',
                              'SUBSECTIONHEADER': 'subType',
                              'COSTCENTER': 'provider',
                              'CPT_NUMBER': 'item_category_cpt_num',
                              'CPT_SUFFIX': 'item_category_cpt_str',
                              'TICKET_ID_SEQ': 'item_sequence',
                              'DESCRIPTION': 'item_detail'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('claim.csv.gz')
    cptevents.to_csv(output_path, index=False)
    return cptevents


# ## fhir.diagnosticReport table
#
# #### MAPPING: <br>
#
# - DESCRIPTION isn't a code but comes closest to the idea of a concept.
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.notevents.ROW_ID|fhir.diagnosticReport.identifier|
# |2|mimic.notevents.SUBJECT_ID|fhir.diagnosticReport.subject|
# |3|mimic.notevents.HADM_ID|fhir.diagnosticReport.encounter|
# |4|mimic.notevents.CHARTDATE|fhir.diagnosticReport.effectiveDateTime|
# |5|mimic.notevents.CGID|fhir.diagnosticReport.performer|
# |6|mimic.notevents.CATEGORY|fhir.diagnosticReport.category|
# |7|mimic.notevents.DESCRIPTION|fhir.diagnosticReport.codeDisplay|
# |8|mimic.notevents.TEXT|fhir.diagnosticReport.presentedForm|
# |9|mimic.notevents.ISERROR| fhir.diagnosticReport.status_error|
#


def transform_noteevents(noteevents_file_path, output_path):
    noteevents = pd.read_csv(noteevents_file_path)

    noteevents.CHARTDATE = pd.to_datetime(noteevents.CHARTDATE, format='%Y-%m-%d', errors='coerce')

    # Drop extra columns
    noteevents.drop(['CHARTTIME', 'STORETIME'], axis=1, inplace=True)

    noteevents.rename(columns={'ROW_ID': 'identifier',
                               'SUBJECT_ID': 'subject',
                               'HADM_ID': 'encounter',
                               'CHARTDATE': 'effectiveDateTime',
                               'CGID': 'performer',
                               'CATEGORY': 'category',
                               'DESCRIPTION': 'codeDisplay',
                               'TEXT': 'presentedForm',
                               'ISERROR': 'status_error'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('diagnosticReport.csv.gz')
    noteevents.to_csv(output_path, index=False)
    return noteevents


# ## fhir.medicationDispense table
#
# #### INPUTEVENTS_CV MAPPING:
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.inputevents_cv.ROW_ID|fhir.medicationDispense.identifier|
# |2|mimic.inputevents_cv.SUBJECT_ID | fhir.medicationDispense.subject|
# |3|mimic.inputevents_cv.HADM_ID | fhir.medicationDispense.encounter|
# |4|mimic.inputevents_cv.ICUSTAY_ID | fhir.medicationDispense.partOf|
# |5|mimic.inputevents_cv.ITEMID | fhir.medicationDispense.medicationCodeableConcept|
# |6|mimic.inputevents_cv.CHARTTIME | fhir.medicationDispense.whenHandedOver|
# |7|mimic.inputevents_cv.AMOUNT | fhir.medicationDispense.valueQuantity|
# |8|mimic.inputevents_cv.AMOUNTUOM | fhir.medicationDispense.unit|
# |9|mimic.inputevents_cv.RATE | fhir.medicationDispense.dosageRate|
# |10|mimic.inputevents_cv.RATEUOM | fhir.medicationDispense.dosageRate_unit|
# |11|mimic.inputevents_cv.CGID | fhir.medicationDispense.performer|
# |12|mimic.inputevents_cv.ORDERID | fhir.medicationDispense.type|
# |13|mimic.inputevents_cv.LINKORDERID | fhir.medicationDispense.type_sub|
# |14|mimic.inputevents_cv.STOPPED | fhir.medicationDispense.status|
# |15|mimic.inputevents_cv.ORIGINALAMOUNT | fhir.medicationDispense.dosageOriginal_amount|
# |16|mimic.inputevents_cv.ORIGINALAMOUNTUOM|fhir.medicationDispense.dosageOriginal_amountUnit|
# |17|mimic.inputevents_cv.ORIGNALROUTE | fhir.medicationDispense.dosageOriginal_route|
# |18|mimic.inputevents_cv.ORIGINALRATE | fhir.medicationDispense.dosageOriginal_rate|
# |19|mimic.inputevents_cv.ORIGINALRATEUOM | fhir.medicationDispense.dosageOriginal_rateUnit|
# |20|mimic.inputevents_cv.ORIGINALSITE | fhir.medicationDispense.dosageOriginal_site|
# |21|mimic.inputevents_cv.NEWBOTTLE | fhir.medicationDispense.note|
# |22|mimic.d_items.(LABEL+DBSOURCE+PARAM_TYPE) | fhir.medicationDispense.note|
# |23|mimic.d_items.CATEGORY | fhir.medicationDispense.category|
#
# #### INPUTEVENTS_MV MAPPING:
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.inputevents_mv.ROW_ID|fhir.medicationDispense.identifier|
# |2|mimic.inputevents_mv.SUBJECT_ID|fhir.medicationDispense.subject|
# |3|mimic.inputevents_mv.HADM_ID|fhir.medicationDispense.encounter|
# |4|mimic.inputevents_mv.ICUSTAY_ID|fhir.medicationDispense.partOf|
# |5|mimic.inputevents_mv.ITEMID|fhir.medicationDispense.medicationCodeableConcept|
# |6|mimic.inputevents_mv.STARTTIME|fhir.medicationDispense.whenHandedOver_start|
# |7|mimic.inputevents_mv.ENDTIME|fhir.medicationDispense.whenHandedOver_end|
# |8|mimic.inputevents_mv.AMOUNT|fhir.medicationDispense.valueQuantity|
# |9|mimic.inputevents_mv.AMOUNTUOM|fhir.medicationDispense.unit|
# |10|mimic.inputevents_mv.RATE|fhir.medicationDispense.dosageRate|
# |11|mimic.inputevents_mv.RATEUOM|fhir.medicationDispense.dosageRate_unit|
# |12|mimic.inputevents_mv.CGID|fhir.medicationDispense.performer|
# |13|mimic.inputevents_mv.ORDERID|fhir.medicationDispense.type|
# |14|mimic.inputevents_mv.LINKORDERID|fhir.medicationDispense.type_sub|
# |15|mimic.inputevents_mv.ORDERCATEGORYNAME|fhir.medicationDispense.supportingInformation_order_catName|
# |16|mimic.inputevents_mv.SECONDARYORDERCATEGORYNAME|fhir.medicationDispense.supportingInformation_order_secCatName|
# |17|mimic.inputevents_mv.ORDERCOMPONENTTYPEDESCRIPTION|fhir.medicationDispense.supportingInformation_order_desc_componentTyped|
# |18|mimic.inputevents_mv.ORDERCATEGORYDESCRIPTION|fhir.medicationDispense.supportingInformation_order_desc_cat|
# |19|mimic.inputevents_mv.PATIENTWEIGHT|fhir.medicationDispense.supportingInformation_patientWeight|
# |20|mimic.inputevents_mv.ORIGINALAMOUNT|fhir.medicationDispense.dosageInstruction_original_amount|
# |21|mimic.inputevents_mv.ORIGINALRATE|fhir.medicationDispense.dosageInstruction_original_rate|
# |22|mimic.inputevents_mv.TOTALAMOUNT|fhir.medicationDispense.dosageInstruction_total_amount|
# |23|mimic.inputevents_mv.TOTALAMOUNTUOM|fhir.medicationDispense.dosageInstruction_total_unit|
# |24|mimic.inputevents_mv.ISOPENBAG|fhir.medicationDispense.dosageInstruction_openBag|
# |25|mimic.inputevents_mv.CONTINUEINNEXTDEPT|fhir.medicationDispense.eventHistory_contExtDep|
# |26|mimic.inputevents_mv.CANCELREASON|fhir.medicationDispense.detectedIssue_code|
# |27|mimic.inputevents_mv.STATUSDESCRIPTION|fhir.medicationDispense.status|
# |28|mimic.inputevents_mv.COMMENTS_EDITEDBY|fhir.medicationDispense.performer_comment_edit|
# |29|mimic.inputevents_mv.COMMENTS_CANCELEDBY|fhir.medicationDispense.performer_comment_cancel|
# |30|mimic.inputevents_mv.COMMENTS_DATE|fhir.medicationDispense.detectedIssue_date|
# |31|mimic.d_items.(LABEL+DBSOURCE+PARAM_TYPE)|fhir.medicationDispense.note|


def transform_inputevents_cv(inputevents_cv_file_path, d_items_file_path, output_path):
    inputevents_cv = pd.read_csv(inputevents_cv_file_path)
    d_items = pd.read_csv(d_items_file_path, index_col=0)

    medicationDispense = pd.merge(inputevents_cv, d_items, on='ITEMID')
    medicationDispense.CHARTTIME = pd.to_datetime(medicationDispense.CHARTTIME, format='%Y-%m-%d %H:%M:%S',
                                                  errors='coerce')

    medicationDispense['NEWBOTTLE'].replace(np.NaN, 0, inplace=True)
    medicationDispense['PARAM_TYPE'].replace(np.NaN, '', regex=True, inplace=True)
    medicationDispense['note'] = medicationDispense['LABEL'] + ' ' + medicationDispense['DBSOURCE'] + ' ' + \
                                 medicationDispense['PARAM_TYPE'] + ' ' + medicationDispense['NEWBOTTLE'].astype(str) + \
                                 ' new bottle'

    medicationDispense.rename(columns={'ROW_ID': 'identifier',
                                       'SUBJECT_ID': 'subject',
                                       'HADM_ID': 'encounter',
                                       'ICUSTAY_ID': 'partOf',
                                       'CHARTTIME': 'whenHandedOver',
                                       'ITEMID': 'medicationCodeableConcept',
                                       'AMOUNT': 'valueQuantity',
                                       'AMOUNTUOM': 'unit',
                                       'RATE': 'dosageRate',
                                       'RATEUOM': 'dosageRate_unit',
                                       'CGID': 'performer',
                                       'ORDERID': 'type',
                                       'LINKORDERID': 'type_sub',
                                       'STOPPED': 'status',
                                       'ORIGINALAMOUNT': 'dosageOriginal_amount',
                                       'ORIGINALAMOUNTUOM': 'dosageOriginal_amountUnit',
                                       'ORIGINALROUTE': 'dosageOriginal_route',
                                       'ORIGINALRATE': 'dosageOriginal_rate',
                                       'ORIGINALRATEUOM': 'dosageOriginal_rateUnit',
                                       'ORIGINALSITE': 'dosageOriginal_site',
                                       'CATEGORY': 'category'}, inplace=True)

    medicationDispense.drop(
        ['LABEL', 'PARAM_TYPE', 'STORETIME', 'ABBREVIATION', 'DBSOURCE', 'LINKSTO', 'CONCEPTID', 'UNITNAME',
         'NEWBOTTLE'], axis=1, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('medicationDispense.csv.gz')
    medicationDispense.to_csv(output_path, index=False)

    return medicationDispense


def transform_inputevents_mv(inputevents_mv_file_path, d_items_file_path, output_path):
    inputevents_mv = pd.read_csv(inputevents_mv_file_path)
    d_items = pd.read_csv(d_items_file_path, index_col=0)

    medicationDispense = pd.merge(inputevents_mv, d_items, on='ITEMID')

    medicationDispense.STARTTIME = pd.to_datetime(medicationDispense.STARTTIME, format='%Y-%m-%d %H:%M:%S',
                                                  errors='coerce')
    medicationDispense.ENDTIME = pd.to_datetime(medicationDispense.ENDTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    medicationDispense.COMMENTS_DATE = pd.to_datetime(medicationDispense.COMMENTS_DATE, format='%Y-%m-%d',
                                                      errors='coerce')

    medicationDispense['PARAM_TYPE'].replace(np.NaN, '', regex=True, inplace=True)
    medicationDispense['note'] = medicationDispense['LABEL'] + ' ' + medicationDispense['DBSOURCE'] + ' ' + \
                                 medicationDispense['PARAM_TYPE']

    medicationDispense.drop(
        ['STORETIME', 'LABEL', 'PARAM_TYPE', 'ABBREVIATION', 'DBSOURCE', 'LINKSTO', 'CONCEPTID', 'UNITNAME'], axis=1,
        inplace=True)

    medicationDispense.rename(columns={'ROW_ID': 'identifier',
                                       'SUBJECT_ID': 'subject',
                                       'HADM_ID': 'encounter',
                                       'ICUSTAY_ID': 'partOf',
                                       'STARTTIME': 'whenHandedOver_start',
                                       'ENDTIME': 'whenHandedOver_end',
                                       'ITEMID': 'medicationCodeableConcept',
                                       'AMOUNT': 'valueQuantity',
                                       'AMOUNTUOM': 'unit',
                                       'RATE': 'dosageRate',
                                       'RATEUOM': 'dosageRate_unit',
                                       'CGID': 'performer',
                                       'ORDERID': 'type',
                                       'LINKORDERID': 'type_sub',
                                       'ORDERCATEGORYNAME': 'supportingInformation_order_catName',
                                       'SECONDARYORDERCATEGORYNAME': 'supportingInformation_order_secCatName',
                                       'ORDERCOMPONENTTYPEDESCRIPTION':
                                           'supportingInformation_order_desc_componentTyped',
                                       'ORDERCATEGORYDESCRIPTION': 'supportingInformation_order_desc_cat',
                                       'PATIENTWEIGHT': 'supportingInformation_patientWeight',
                                       'TOTALAMOUNT': 'dosageInstruction_total_amount',
                                       'TOTALAMOUNTUOM': 'dosageInstruction_total_unit',
                                       'ISOPENBAG': 'dosageInstruction_openBag',
                                       'CONTINUEINNEXTDEPT': 'eventHistory_contExtDep',
                                       'CANCELREASON': 'detectedIssue_code',
                                       'STATUSDESCRIPTION': 'status',
                                       'COMMENTS_EDITEDBY': 'performer_comment_edit',
                                       'COMMENTS_CANCELEDBY': 'performer_comment_cancel',
                                       'COMMENTS_DATE': 'detectedIssue_date',
                                       'ORIGINALAMOUNT': 'dosageInstruction_original_amount',
                                       'ORIGINALRATE': 'dosageInstruction_original_rate',
                                       'CATEGORY': 'category'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('medicationDispense_mv.csv.gz')
    medicationDispense.to_csv(output_path, index=False)
    return medicationDispense


# ## fhir.medicationRequest table
#
# #### MAPPING: <br>
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.prescriptions.ROW_ID | fhir.medicationRequest.identifier|
# |2|mimic.prescriptions.SUBJECT_ID | fhir.medicationRequest.subject|
# |3|mimic.prescriptions.HADM_ID| fhir.medicationRequest.encounter|
# |4|mimic.prescriptions.ICUSTAY_ID | fhir.medicationRequest.partOf|
# |5|mimic.prescriptions.STARTDATE | fhir.medicationRequest.dispenseRequest_start|
# |6|mimic.prescriptions.ENDDATE | fhir.medicationRequest.dispenseRequest_end|
# |7|mimic.prescriptions.DRUG_TYPE | fhir.medicationRequest.category|
# |8|mimic.prescriptions.DRUG | fhir.medicationRequest.medication_name|
# |9|mimic.prescriptions.DRUG_NAME_GENERIC | fhir.medicationRequest.medication_genericName|
# |10|mimic.prescriptions.FORMULARY_DRUG_CD | fhir.medicationRequest.medication_code_CD|
# |11|mimic.prescriptions.GSN | fhir.medicationRequest.medication_code_GSN|
# |12|mimic.prescriptions.NDC | fhir.medicationRequest.medication_code_NDC|
# |13|mimic.prescriptions.DOSE_VAL_RX | fhir.medicationRequest.dosageInstruction_value|
# |14|mimic.prescriptions.DOSE_UNIT_RX | fhir.medicationRequest.dosageInstruction_unit|
# |15|mimic.prescriptions.FORM_VAL_DISP | fhir.medicationRequest.dispenseRequest_value|
# |16|mimic.prescriptions.FORM_UNIT_DISP | fhir.medicationRequest.dispenseRequest_unit|
# |17|mimic.prescriptions.ROUTE | fhir.medicationRequest.courseOfTherapyType|


def transform_prescriptions(prescriptions_file_path, output_path):
    prescriptions = pd.read_csv(prescriptions_file_path)

    prescriptions.STARTDATE = pd.to_datetime(prescriptions.STARTDATE, format='%Y-%m-%d', errors='coerce')
    prescriptions.ENDDATE = pd.to_datetime(prescriptions.ENDDATE, format='%Y-%m-%d', errors='coerce')

    # Drop extra columns
    prescriptions.drop(['DRUG_NAME_POE', 'PROD_STRENGTH'], axis=1, inplace=True)

    prescriptions.rename(columns={'ROW_ID': 'identifier',
                                  'SUBJECT_ID': 'subject',
                                  'HADM_ID': 'encounter',
                                  'ICUSTAY_ID': 'partOf',
                                  'STARTDATE': 'dispenseRequest_start',
                                  'ENDDATE': 'dispenseRequest_end',
                                  'DRUG_TYPE': 'category',
                                  'DRUG': 'medication_name',
                                  'DRUG_NAME_GENERIC': 'medication_genericName',
                                  'FORMULARY_DRUG_CD': 'medication_code_CD',
                                  'GSN': 'medication_code_GSN',
                                  'NDC': 'medication_code_NDC',
                                  'DOSE_VAL_RX': 'dosageInstruction_value',
                                  'DOSE_UNIT_RX': 'dosageInstruction_unit',
                                  'FORM_VAL_DISP': 'dispenseRequest_value',
                                  'FORM_UNIT_DISP': 'dispenseRequest_unit',
                                  'ROUTE': 'courseOfTherapyType'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('medicationRequest.csv.gz')
    prescriptions.to_csv(output_path, index=False)
    return prescriptions


# ## fhir.observation table
#
# #### CHARTEVENTS MAPPING:<br>
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# ||mimic.chartevents.ROW_ID| fhir.observation.identifier|
# ||mimic.chartevents.SUBJECT_ID | fhir.observation.subject|
# ||mimic.chartevents.HADM_ID | fhir.observation.encounter|
# ||mimic.chartevents.ICUSTAY_ID | fhir.observation.partOf|
# ||mimic.chartevents.ITEMID | fhir.observation.code|
# ||mimic.chartevents.CHARTTIME | fhir.observation.effectiveDateTime|
# ||mimic.chartevents.CGID | fhir.observation.performer|
# ||mimic.chartevents.VALUE | fhir.observation.value|
# ||mimic.chartevents.VALUENUM | fhir.observation.value_quantity|
# ||mimic.chartevents.VALUEUOM | fhir.observation.unit|
# ||mimic.chartevents.WARNING | fhir.observation.interpretation|
# ||mimic.chartevents.RESULTSTATUS | fhir.observation.status|
# ||mimic.d_items.(LABEL+DBSOURCE+PARAM_TYPE) | fhir.observation.note|
# ||mimic.d_items.CATEGORY | fhir.observation.category_sub|
# ||'chartevents' | fhir.observation.category|
#
#
# #### DATETIMEEVENTS MAPPING:<br>
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# ||mimic.datetimeevents.ROW_ID| fhir.observation.identifier|
# ||mimic.datetimeevents.SUBJECT_ID | fhir.observation.subject|
# ||mimic.datetimeevents.HADM_ID | fhir.observation.encounter|
# ||mimic.datetimeevents.ICUSTAY_ID | fhir.observation.partOf|
# ||mimic.datetimeevents.ITEMID | fhir.observation.code|
# ||mimic.datetimeevents.CHARTTIME | fhir.observation.effectiveDateTime|
# ||mimic.datetimeevents.CGID | fhir.observation.performer|
# ||mimic.datetimeevents.VALUE | fhir.observation.value|
# ||mimic.datetimeevents.VALUEUOM | fhir.observation.unit|
# ||mimic.datetimeevents.WARNING | fhir.observation.interpretation|
# ||mimic.datetimeevents.RESULTSTATUS | fhir.observation.status|
# ||mimic.d_items.(LABEL+DBSOURCE+PARAM_TYPE) | fhir.observation.note|
# ||mimic.d_items.CATEGORY | fhir.observation.category_sub|
# ||'datetimeevents' | fhir.observation.category|
#
#
# #### LABEVENTS MAPPING:<br>
#
# - Consider assigning loinc_code to code not to method. LOINC_CODE would first need to be assigned, which isn't
# straightforward.
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# ||mimic.labevents.ROW_ID|fhir.observation.identifier|
# ||mimic.labevents.SUBJECT_ID|fhir.observation.subject|
# ||mimic.labevents.HADM_ID|fhir.observation.encounter|
# ||mimic.labevents.CHARTTIME|fhir.observation.effectiveDateTime|
# ||mimic.labevents.ITEMID | fhir.observation.code|
# ||mimic.d_labitems.LOINC_CODE | fhir.observation.code_loinc|
# ||mimic.labevents.VALUE | fhir.observation.value|
# ||mimic.labevents.VALUENUM | fhir.observation.value_quantity|
# ||mimic.labevents.VALUEUOM | fhir.observation.unit|
# ||mimic.labevents.FLAG | fhir.observation.interpretation|
# ||mimic.d_labitems.(LABEL+FLUID) | fhir.observation.note|
# ||mimic.d_labitems.CATEGORY | fhir.observation.category_sub|
# ||'labevents' | fhir.observation.category|


def transform_chartevents(chartevents_file_path, d_items_file_path, output_path):
    chartevents = pd.read_csv(chartevents_file_path)
    d_items = pd.read_csv(d_items_file_path, index_col=0)

    observation_ce = pd.merge(chartevents, d_items, on='ITEMID')

    observation_ce.CHARTTIME = pd.to_datetime(observation_ce.CHARTTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')

    observation_ce['PARAM_TYPE'].replace(np.NaN, '', regex=True, inplace=True)
    observation_ce['note'] = observation_ce['LABEL'] + ' ' + observation_ce['DBSOURCE'] + ' ' + observation_ce[
        'PARAM_TYPE']

    observation_ce.loc[observation_ce.STOPPED == "D/C'd", 'RESULTSTATUS'] = 'discharged'
    observation_ce.loc[observation_ce.ERROR == 1, 'RESULTSTATUS'] = 'Error'
    # New columns to adapt to Chartevents observations
    observation_ce['category'] = 'chartevents'

    observation_ce.drop(
        ['LABEL', 'PARAM_TYPE', 'STORETIME', 'ERROR', 'ABBREVIATION', 'DBSOURCE', 'LINKSTO', 'CONCEPTID', 'STOPPED',
         'UNITNAME'], axis=1, inplace=True)

    observation_ce.rename(columns={'ROW_ID': 'identifier',
                                   'SUBJECT_ID': 'subject',
                                   'HADM_ID': 'encounter',
                                   'ICUSTAY_ID': 'partOf',
                                   'ITEMID': 'code',
                                   'CGID': 'performer',
                                   'CHARTTIME': 'effectiveDateTime',
                                   'VALUE': 'value',
                                   'VALUENUM': 'value_quantity',
                                   'VALUEUOM': 'unit',
                                   'WARNING': 'interpretation',
                                   'RESULTSTATUS': 'status',
                                   'CATEGORY': 'category_sub'}, inplace=True)

    observation_ce = observation_ce.reindex(columns=['identifier',
                                                     'subject',
                                                     'encounter',
                                                     'partOf',
                                                     'code',
                                                     'effectiveDateTime',
                                                     'performer',
                                                     'value',
                                                     'value_quantity',
                                                     'unit',
                                                     'interpretation',
                                                     'status',
                                                     'note',
                                                     'category_sub',
                                                     'category'], copy=False)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('observation_ce.csv.gz')
    observation_ce.to_csv(output_path, index=False)
    return observation_ce


def transform_datetimeevents(datetimeevents_file_path, d_items_file_path, output_path):
    datetimeevents = pd.read_csv(datetimeevents_file_path)
    d_items = pd.read_csv(d_items_file_path, index_col=0)

    observation_dte = pd.merge(datetimeevents, d_items, on='ITEMID')
    observation_dte.CHARTTIME = pd.to_datetime(observation_dte.CHARTTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')

    observation_dte['PARAM_TYPE'].replace(np.NaN, '', regex=True, inplace=True)
    observation_dte['note'] = observation_dte['LABEL'] + ' ' + observation_dte['DBSOURCE'] + ' ' + observation_dte[
        'PARAM_TYPE']

    observation_dte.loc[observation_dte.STOPPED == "D/C'd", 'RESULTSTATUS'] = 'Final'
    observation_dte.loc[observation_dte.ERROR == 1, 'RESULTSTATUS'] = 'Error'
    # New columns to adapt to DateTimeEvents observations
    observation_dte['category'] = 'datetimeevents'

    observation_dte.drop(
        ['LABEL', 'PARAM_TYPE', 'STORETIME', 'ERROR', 'ABBREVIATION', 'DBSOURCE', 'LINKSTO', 'CONCEPTID', 'STOPPED',
         'UNITNAME'], axis=1, inplace=True)

    observation_dte.rename(columns={'ROW_ID': 'identifier',
                                    'SUBJECT_ID': 'subject',
                                    'HADM_ID': 'encounter',
                                    'ICUSTAY_ID': 'partOf',
                                    'ITEMID': 'code',
                                    'CGID': 'performer',
                                    'CHARTTIME': 'effectiveDateTime',
                                    'VALUE': 'value',
                                    'VALUEUOM': 'unit',
                                    'WARNING': 'interpretation',
                                    'RESULTSTATUS': 'status',
                                    'CATEGORY': 'category_sub'}, inplace=True)

    observation_dte = observation_dte.reindex(columns=['identifier',
                                                       'subject',
                                                       'encounter',
                                                       'partOf',
                                                       'code',
                                                       'effectiveDateTime',
                                                       'performer',
                                                       'value',
                                                       'unit',
                                                       'interpretation',
                                                       'status',
                                                       'note',
                                                       'category_sub',
                                                       'category'], copy=False)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('observation_dte.csv.gz')
    observation_dte.to_csv(output_path, index=False)
    return observation_dte


def transform_labevents(labevents_file_path, d_labitems_file_path, output_path):
    labevents = pd.read_csv(labevents_file_path)
    d_labitems = pd.read_csv(d_labitems_file_path, index_col=0)

    observation_le = pd.merge(labevents, d_labitems, on='ITEMID')
    observation_le.CHARTTIME = pd.to_datetime(observation_le.CHARTTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')

    observation_le['note'] = observation_le['LABEL'] + ' ' + observation_le['FLUID']
    observation_le.drop(['LABEL', 'FLUID'], axis=1, inplace=True)

    # Add observation type
    observation_le['category'] = 'labevents'

    observation_le.rename(columns={'ROW_ID': 'identifier',
                                   'SUBJECT_ID': 'subject',
                                   'HADM_ID': 'encounter',
                                   'ITEMID': 'code',
                                   'LOINC_CODE': 'code_loinc',
                                   'CHARTTIME': 'effectiveDateTime',
                                   'VALUE': 'value',
                                   'VALUENUM': 'value_quantity',
                                   'VALUEUOM': 'unit',
                                   'FLAG': 'interpretation',
                                   'CATEGORY': 'category_sub'}, inplace=True)

    observation_le = observation_le.reindex(columns=['identifier',
                                                     'subject',
                                                     'encounter',
                                                     'effectiveDateTime',
                                                     'code',
                                                     'code_loinc',
                                                     'value',
                                                     'value_quantity',
                                                     'unit',
                                                     'interpretation',
                                                     'note',
                                                     'category_sub',
                                                     'category'], copy=False)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('observation_le.csv.gz')
    observation_le.to_csv(output_path, index=False)
    return observation_le


# ## fhir.practitioner table
#
# #### MAPPING:
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.caregivers.CGID|fhir.practitioner.identifier|
# |2|mimic.caregivers.LABEL|fhir.practitioner.qualification_category|
# |3|mimic.caregivers.DESCRIPTION|fhir.practitioner.qualification_label|


def transform_caregivers(caregivers_file_path, output_path):
    caregivers = pd.read_csv(caregivers_file_path)

    caregivers.drop(['ROW_ID'], axis=1, inplace=True)

    caregivers.rename(columns={'CGID': 'identifier',
                               'LABEL': 'qualification_label',
                               'DESCRIPTION': 'qualification_category'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('practitioner.csv.gz')
    caregivers.to_csv(output_path, index=False)
    return caregivers


# ## fhir.procedure table
#
# #### PROCEDURES_ICD MAPPING:<br>
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.procedures_icd.ROW_ID | fhir.procedure.identifier|
# |2|mimic.procedures_icd.SUBJECT_ID | fhir.procedure.subject|
# |3|mimic.procedures_icd.HADM_ID | fhir.procedure.encounter|
# |4|mimic.procedures_icd.ICD9_CODE | fhir.procedure.code_icd9|
#
# #### PROCEDUREEVENTS_MV MAPPING:<br>
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.procedureevents_mv.ROW_ID | fhir.procedure.identifier|
# |2|mimic.procedureevents_mv.SUBJECT_ID | fhir.procedure.subject|
# |3|mimic.procedureevents_mv.HADM_ID | fhir.procedure.encounter|
# |4|mimic.procedureevents_mv.ICUSTAY_ID| fhir.procedure.partOf|
# |5|mimic.procedureevents_mv.STARTTIME| fhir.procedure.performedRange_start|
# |6|mimic.procedureevents_mv.ENDTIME| fhir.procedure.performedRange_end|
# |7|mimic.procedureevents_mv.ITEMID| fhir.procedure.code|
# |8|mimic.procedureevents_mv.VALUE| fhir.procedure.outcome_value|
# |9|mimic.procedureevents_mv.VALUEOM | fhir.procedure.outcome_unit|
# |10|mimic.procedureevents_mv.LOCATION| fhir.procedure.location_name|
# |11|mimic.procedureevents_mv.LOCATIONCATEGORY| fhir.procedure.location_category|
# |12|mimic.procedureevents_mv.CGID|fhir.procedure.performer|
# |13|mimic.procedureevents_mv.ORDERID| fhir.procedure.basedOn|
# |14|mimic.procedureevents_mv.LINKORDERID|fhir.procedure.basedOn_linked|
# |15|mimic.procedureevents_mv.ORDERCATEGORYNAME| fhir.procedure.category_order_name|
# |16|mimic.procedureevents_mv.SECONDARYORDERCATEGORYNAME|fhir.procedure.category_secOrder_name|
# |17|mimic.procedureevents_mv.ORDERCATEGORYDESCRIPTION|fhir.procedure.category_order_description|
# |18|mimic.procedureevents_mv.ISOPENBAG| fhir.procedure.usedReference_openBag|
# |19|mimic.procedureevents_mv.CONTINUEINEXTDEPT| fhir.procedure.report_contExtDep|
# |20|mimic.procedureevents_mv.CANCELREASON| fhir.procedure.report_cancelReason|
# |21|mimic.procedureevents_mv.STATUSDESCRIPTION| fhir.procedure.status|
# |22|mimic.procedureevents_mv.COMMENTS_EDITEDBY| fhir.procedure.report_editedBy|
# |23|mimic.procedureevents_mv.COMMENTS_CANCELEDBY| fhir.procedure.report_canceledBy|
# |24|mimic.procedureevents_mv.COMMENTS_DATE| fhir.procedure.report_canceledDate|
# |25|mimic.d_items.(LABEL+DBSOURCE+PARAM_TYPE)|mimic.procedure.note|
# |26|mimic.d_items.CATEGORY|mimic.procedure.category|


def transform_procedures_icd(procedures_icd_file_path, output_path):
    procedures_icd = pd.read_csv(procedures_icd_file_path)
    procedures_icd['followUp'] = procedures_icd.groupby('HADM_ID')['ROW_ID'].shift(-1)
    procedures_icd.rename(columns={'ROW_ID': 'identifier',
                                   'SUBJECT_ID': 'subject',
                                   'HADM_ID': 'encounter',
                                   'ICD9_CODE': 'code'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('procedure_icd9.csv.gz')
    procedures_icd.to_csv(output_path, index=False)
    return procedures_icd


def transform_procedurevents_mv(procedureevents_file_path, d_items_file_path, output_path):
    procedurevents_mv = pd.read_csv(procedureevents_file_path)
    d_items = pd.read_csv(d_items_file_path, index_col=0)

    procedurevents_mv = pd.merge(procedurevents_mv, d_items, on='ITEMID')

    procedurevents_mv.STARTTIME = pd.to_datetime(procedurevents_mv.STARTTIME, format='%Y-%m-%d %H:%M:%S',
                                                 errors='coerce')
    procedurevents_mv.ENDTIME = pd.to_datetime(procedurevents_mv.ENDTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    procedurevents_mv.COMMENTS_DATE = pd.to_datetime(procedurevents_mv.COMMENTS_DATE, format='%Y-%m-%d',
                                                     errors='coerce')

    procedurevents_mv['note'] = procedurevents_mv['LABEL'] + ' ' + procedurevents_mv['DBSOURCE'] + ' ' + \
                                procedurevents_mv['PARAM_TYPE']

    procedurevents_mv.drop(
        ['LABEL', 'PARAM_TYPE', 'STORETIME', 'ABBREVIATION', 'DBSOURCE', 'LINKSTO', 'CONCEPTID', 'UNITNAME'], axis=1,
        inplace=True)

    procedurevents_mv.rename(columns={'ROW_ID': 'identifier',
                                      'SUBJECT_ID': 'subject',
                                      'HADM_ID': 'encounter',
                                      'ICUSTAY_ID': 'partOf',
                                      'STARTTIME': 'performedRange_start',
                                      'ENDTIME': 'performedRange_end',
                                      'ITEMID': 'code',
                                      'VALUE': 'outcome_value',
                                      'VALUEUOM': 'outcome_unit',
                                      'LOCATION': 'location_name',
                                      'LOCATIONCATEGORY': 'location_category',
                                      'CGID': 'performer',
                                      'ORDERID': 'basedOn',
                                      'LINKORDERID': 'basedOn_linked',
                                      'ORDERCATEGORYNAME': 'category_order_name',
                                      'SECONDARYORDERCATEGORYNAME': 'category_secOrder_name',
                                      'ORDERCATEGORYDESCRIPTION': 'category_order_description',
                                      'ISOPENBAG': 'usedReference_openBag',
                                      'CONTINUEINNEXTDEPT': 'report_contNextDep',
                                      'CANCELREASON': 'report_cancelReason',
                                      'STATUSDESCRIPTION': 'status',
                                      'COMMENTS_EDITEDBY': 'report_editedBy',
                                      'COMMENTS_CANCELEDBY': 'report_canceledBy',
                                      'COMMENTS_DATE': 'report_canceledDate',
                                      'CATEGORY': 'category'
                                      }, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('procedure_mv.csv.gz')
    procedurevents_mv.to_csv(output_path, index=False)
    return procedurevents_mv


# ## fhir.specimen table
#
# #### OUTPUTEVENTS MAPPING:<br>
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.outputevents:ROW_ID | fhir.specimen.identifier|
# |2|mimic.outputevents.SUBJECT_ID | fhir.specimen.subject|
# |3|mimic.outputevents.HADM_ID | fhir.specimen.request_encounter_admission|
# |4|mimic.outputevents.ICUSTAY_ID | fhir.specimen.request_encounter_icustay|
# |5|mimic.outputevents.ITEMID | fhir.specimen.type_code|
# |6|mimic.d_items.CATEGORY | fhir.specimen.type_category|
# |7|mimic.outputevents.CGID | fhir.specimen.collection_collector|
# |8|mimic.outputevents.CHARTTIME | fhir.specimen.collection_dateTime|
# |9|mimic.outputevents.VALUE | fhir.specimen.collection_quantity|
# |10|mimic.outputevents.VALUEUOM | fhir.specimen.collection_unit|
# |11|mimic.outputevents.NEWBOTTLE | fhir.specimen.collection_newBottle|
# |12|mimic.outputevents.(STOPPED+ISERROR) | fhir.specimen.status|
# |13|mimic.d_items.(LABEL+DBSOURCE+PARAM_TYPE) | fhir.specimen.note|
#
# #### MICROBIOLOGYEVENTS MAPPING:<br>
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.microbiologyevents.ROW_ID| fhir.specimen.identifier|
# |2|mimic.microbiologyevents.SUBJECT_ID | fhir.specimen.subject|
# |3|mimic.microbiologyevents.HADM_ID | fhir.specimen.request_encounter_admission|
# |4|mimic.microbiologyevents.CHARTTIME | fhir.specimen.collection_dateTime|
# |5|mimic.microbiologyevents.SPEC_ITEMID | fhir.specimen.type_code|
# |6|mimic.microbiologyevents.SPEC_TYPE_DESC | fhir.specimen.type_name|
# |7|mimic.d_items(on SPEC).CATEGORY | fhir.specimen.type_category|
# |8|mimic.microbiologyevents.ORG_ITEMID | fhir.specimen.method_bact_code|
# |9|mimic.microbiologyevents.ORG_NAME | fhir.specimen.method_bact_name|
# |10|mimic.microbiologyevents.ISOLATE_NUM | fhir.specimen.method_colNum|
# |11|mimic.microbiologyevents.AB_ITEMID | fhir.specimen.method_antibiotic_code|
# |12|mimic.microbiologyevents.AB_NAME | fhir.specimen.method_antibiotic_name|
# |13|mimic.microbiologyevents.DILUTION_TEXT | fhir.specimen.method_dilution_description|
# |14|mimic.microbiologyevents.DILUTION_COMPARISON | fhir.specimen.method_dilution_comp|
# |15|mimic.microbiologyevents.DILUTION_VALUE | fhir.specimen.method_dilution_value|
# |16|mimic.microbiologyevents.INTERPRETATION | fhir.specimen.note_interpretation|
# |17|mimic.d_items_(SPEC/ORG/AB).(LABEL+PARAM_TYPE+DBSOURCE) | fhir.specimen.note|


def transform_outputevents(outputevents_file_path, d_items_file_path, output_path):
    outputevents = pd.read_csv(outputevents_file_path)
    d_items = pd.read_csv(d_items_file_path, index_col=0)

    specimen_oe = pd.merge(outputevents, d_items, on='ITEMID')
    specimen_oe.CHARTTIME = pd.to_datetime(specimen_oe.CHARTTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')

    # Replace NaN in columns with empty strings so that concatenation in notes works
    specimen_oe['PARAM_TYPE'].replace(np.NaN, '', regex=True, inplace=True)
    specimen_oe['note'] = specimen_oe['LABEL'] + ' ' + specimen_oe['DBSOURCE'] + ' ' + specimen_oe['PARAM_TYPE']

    # Combine STOPPED and ISERROR column, Errorneous notes entries will be eliminated later on
    specimen_oe.loc[specimen_oe.ISERROR == 1, 'STOPPED'] = 'Error'

    # Drop Columns not needed anymore
    specimen_oe.drop(
        ['LABEL', 'PARAM_TYPE', 'STORETIME', 'ISERROR', 'ABBREVIATION', 'DBSOURCE', 'LINKSTO', 'CONCEPTID', 'UNITNAME'],
        axis=1, inplace=True)

    specimen_oe.rename(columns={'ROW_ID': 'identifier',
                                'SUBJECT_ID': 'subject',
                                'HADM_ID': 'request_encounter_admission',
                                'ICUSTAY_ID': 'request_encounter_icustay',
                                'ITEMID': 'type_code',
                                'CATEGORY': 'type_category',
                                'CGID': 'collector',
                                'CHARTTIME': 'collected_dateTime',
                                'VALUE': 'collection_quantity',
                                'VALUEUOM': 'collection_unit',
                                'NEWBOTTLE': 'collection_newBottle',
                                'STOPPED': 'status'}, inplace=True)

    specimen_oe = specimen_oe.reindex(columns=['identifier',
                                               'subject',
                                               'request_encounter_admission',
                                               'request_encounter_icustay',
                                               'type_code',
                                               'type_category',
                                               'collection_collector',
                                               'collection_dateTime',
                                               'collection_quantity',
                                               'collection_unit',
                                               'collection_newBottle',
                                               'status',
                                               'note'], copy=False)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('specimen_oe.csv.gz')
    specimen_oe.to_csv(output_path, index=False)
    return specimen_oe


def transform_microbiologyevents(mb_file_path, d_items_file_path, output_path):
    microbiologyevents = pd.read_csv(mb_file_path)
    d_items = pd.read_csv(d_items_file_path, index_col=0)

    specimen_mbe = pd.merge(microbiologyevents, d_items[['ITEMID', 'LABEL', 'DBSOURCE', 'PARAM_TYPE', 'CATEGORY']],
                            left_on='SPEC_ITEMID', right_on='ITEMID')
    specimen_mbe = pd.merge(specimen_mbe, d_items[['ITEMID', 'LABEL', 'DBSOURCE', 'PARAM_TYPE']], left_on='ORG_ITEMID',
                            right_on='ITEMID', suffixes=('', '_org'))
    specimen_mbe = pd.merge(specimen_mbe, d_items[['ITEMID', 'LABEL', 'DBSOURCE', 'PARAM_TYPE']], left_on='AB_ITEMID',
                            right_on='ITEMID', suffixes=('', '_ab'))

    specimen_mbe.CHARTTIME = pd.to_datetime(specimen_mbe.CHARTTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')

    # Replace NaN in columns with empty strings so that concatenation in notes works
    specimen_mbe['PARAM_TYPE'].replace(np.NaN, '', regex=True, inplace=True)
    specimen_mbe['PARAM_TYPE_org'].replace(np.NaN, '', regex=True, inplace=True)
    specimen_mbe['PARAM_TYPE_ab'].replace(np.NaN, '', regex=True, inplace=True)

    specimen_mbe['note'] = specimen_mbe['LABEL'] + ' ' + specimen_mbe['DBSOURCE'] + ' ' + specimen_mbe[
        'PARAM_TYPE'] + ' ' + specimen_mbe['LABEL_org'] + ' ' + specimen_mbe['DBSOURCE_org'] + ' ' + specimen_mbe[
                               'PARAM_TYPE_org'] + ' ' + specimen_mbe['LABEL_ab'] + ' ' + specimen_mbe[
                               'DBSOURCE_ab'] + ' ' + specimen_mbe['PARAM_TYPE_ab']

    # Drop columns combined to note field
    specimen_mbe.drop(['CHARTDATE'], axis=1, inplace=True)
    specimen_mbe.drop(['ITEMID', 'LABEL', 'PARAM_TYPE', 'DBSOURCE'], axis=1, inplace=True)
    specimen_mbe.drop(['ITEMID_org', 'LABEL_org', 'PARAM_TYPE_org', 'DBSOURCE_org'], axis=1, inplace=True)
    specimen_mbe.drop(['ITEMID_ab', 'LABEL_ab', 'PARAM_TYPE_ab', 'DBSOURCE_ab'], axis=1, inplace=True)

    specimen_mbe.rename(columns={'ROW_ID': 'identifier',
                                 'SUBJECT_ID': 'subject',
                                 'HADM_ID': 'request_encounter_admission',
                                 'CHARTTIME': 'collection_dateTime',
                                 'SPEC_ITEMID': 'type_code',
                                 'SPEC_TYPE_DESC': 'type_name',
                                 'CATEGORY': 'type_category',
                                 'ORG_ITEMID': 'method_bact_code',
                                 'ORG_NAME': 'method_bact_name',
                                 'ISOLATE_NUM': 'method_colNum',
                                 'AB_ITEMID': 'method_antibiotic_code',
                                 'AB_NAME': 'method_antibiotic_name',
                                 'DILUTION_TEXT': 'method_dilution_description',
                                 'DILUTION_COMPARISON': 'method_dilution_comp',
                                 'DILUTION_VALUE': 'method_dilution_value',
                                 'INTERPRETATION': 'note_interpretation'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('specimen_mbe.csv.gz')
    specimen_mbe.to_csv(output_path, index=False)
    return specimen_mbe


# ## fhir.serviceRequest table
#
# #### MAPPING:<br>
#
# ||Original format | FHIR resource format|
# |------|:-----|:-----|
# |1|mimic.services.ROW_ID | fhir.serviceRequest.identifier|
# |2|mimic.services.SUBJECT_ID | fhir.serviceRequest.subject|
# |3|mimic.services.HADM_ID | fhir.serviceRequest.encounter|
# |4|mimic.services.TRANSFERTIME | fhir.serviceRequest.occuranceDateTime|
# |5|mimic.services.PREV_SERVICE | fhir.serviceRequest.replaces|
# |6|mimic.services.CURR_SERVICE | fhir.serviceRequest.code_name|


def transform_services(services_file_path, output_path):
    services = pd.read_csv(services_file_path)

    services.TRANSFERTIME = pd.to_datetime(services.TRANSFERTIME, format='%Y-%m-%d %H:%M:%S', errors='coerce')

    services.rename(columns={'ROW_ID': 'identifier',
                             'SUBJECT_ID': 'subject',
                             'HADM_ID': 'encounter',
                             'TRANSFERTIME': 'occuranceDateTime',
                             'PREV_SERVICE': 'replaces',
                             'CURR_SERVICE': 'code_name'}, inplace=True)

    if Path(output_path).is_dir():
        output_path = Path(output_path) + Path('services.csv.gz')
    services.to_csv(output_path, index=False)
    return services