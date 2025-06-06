from setuptools import setup, find_packages

setup(
    name = 'bank_statement_converter',
    version = '0.1.3',
    package_dir = {'':'src'},
    packages = find_packages('src'),
    install_requires = [
        'pymupdf>=1.26.0',
        'python-dateutil>=2.9.0.post0',
        'PyQt5==5.15.11',
        'PyQt5-Qt5==5.15.2',
        'PyQt5_sip==12.17.0'
    ],
    entry_points = {
        'console_scripts': [
            'bstc = bank_statement_converter.cli:main',
            'bstc-gui = bank_statement_converter.gui:main'
        ]
    },
    extras_require = {
        "build": ["pyinstaller"]
    },
    author = 'jch',
    description = 'Convert various bank PDF statements into CSV and QIF'
)