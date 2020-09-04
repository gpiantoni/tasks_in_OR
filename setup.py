from setuptools import setup, find_packages

setup(
    name='qttasks',
    version='0.2',
    description='Tasks to run with QT',
    url='https://github.com/gpiantoni/tasks_in_OR',
    author="Gio Piantoni",
    author_email='qttasks@gpiantoni.com',
    license='GPLv3',
    classifiers=[
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='tasks qt',
    packages=find_packages(exclude=('test', )),
    install_requires=[
        'numpy',
        'pyserial',
        ],
    package_data={
        'qttasks': [
            'images/*.tsv',
            'images/prf/*.png',
            ],
    },
    extras_require={
        'tests': [
            'pytest',
            'pytest-qt',
            ],
    },
    entry_points={
        'console_scripts': [
            'qttasks=qttasks.presentation:main',
            'qt_convert_log2tsv=qttasks.convert_log_to_tsv:main',
        ],
    },
)
