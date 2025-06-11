from setuptools import setup, find_packages

setup(
    name = 'bank_statement_converter',
    version = '0.1.4',
    package_dir = {'':'src'},
    packages = find_packages('src'),
    install_requires = [
        'pymupdf>=1.26.0',
        'python-dateutil>=2.9.0.post0',
        'PySide6==6.9.1',
        'PySide6_Addons==6.9.1',
        'PySide6_Essentials==6.9.1',
        'shiboken6==6.9.1',
        'QtPy==2.4.3'
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