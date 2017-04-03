from setuptools import setup


setup(
    name='spiderpig',
    version='2.0.0',
    description='Caching and execution library for data analysis.',
    author='Jan Papousek',
    author_email='jan.papousek@gmail.com',
    include_package_data=True,
    packages=[
        'spiderpig',
        'spiderpig.commands',
        'spiderpig.commands.common',
        'spiderpig.tests',
    ],
    install_requires=[
        'argcomplete',
        'clint',
        'filelock',
        'PyYAML',
    ],
    license='MIT',
)
