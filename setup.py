from setuptools import setup


setup(
    name='spiderpig',
    version='2.4.0-dev',
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
        'html2text',
        'PyYAML',
    ],
    license='MIT',
)
