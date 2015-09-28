from setuptools import setup, find_packages

VERSION = '1.0.0'


install_requires = [
    'django',
    'git+https://github.com/PSU-OIT-ARC/django-arcutils.git#egg=django-arcutils',
    'git+https://github.com/PSU-OIT-ARC/arctasks#egg=psu.oit.arc.tasks',
    'django-cloak',
    'git+https://github.com/PSU-OIT-ARC/django-local-settings.git#egg=django_local_settings'
    'django-perms',
    'git+https://github.com/PSU-OIT-ARC/elasticmodels.git#egg=elasticmodels',
    'elasticsearch',
    'elasticsearch-dsl',
    'Markdown',
    'mccabe',
    'mock',
    'mommy-spatial-generators',
    'pbr',
    'pep8',
    'Pillow',
    'psycopg2',
    'pyflakes',
    'python-dateutil',
    'pytz',
    'six',
    'stashward',
    'urllib3',
    'wheel',
]


setup(
    name='psu.oit.arc.oregoninvasiveshotline',
    version=VERSION,
    description='Oregon Invasives Hotline',
    author='PSU - OIT - ARC',
    author_email='consultants@pdx.edu',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        'dev': [
            'bpython',
            'coverage',
            'flake8',
            'isort',
            'model_mommy',
            'psu.oit.arc.tasks',
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
)
