from setuptools import setup, find_packages

VERSION = '1.0.0.dev0'


install_requires = [
    'django>=1.8.4,<1.9',
    'django-arcutils>=1.1.1',
    'django-cloak',
    'django-local-settings>=1.0a7',
    'django-perms',
    'elasticmodels',
    'elasticsearch',
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
