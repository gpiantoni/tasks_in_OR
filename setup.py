from setuptools import setup, find_packages

setup(
    name='qttasks',
    version='0.1',
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
    packages=find_packages(),
    install_requires=[
        'numpy',
        'PyQt5',
        ],
    package_data={
        'qttasks': [
            'images/*.tsv',
            'images/*/*.png',
            ],
    },
    entry_points={
        'console_scripts': [
            'qttasks=qttasks.presentation:main',
        ],
    },
)
