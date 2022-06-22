from setuptools import setup

setup(name='mimic_fhir_transfrom',
      version='0.0.1',
      description='Python package to transform MIMIC-III tables to FHIR format',
      url='https://github.com/leopold-franz/MIMIC-III_FHIR_Transformation',
      packages=['mimic_fhir_transform'],
      python_requires='>=3.7.7',
      install_requires=[
          "numpy==1.22.0",
          "pandas==1.0.4",
      ],
      extras_requires={
          'dev': ['jupyter'],
      },
      entry_points={
      },
      zip_safe=False)
