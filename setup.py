from setuptools import setup


VERSION = '1.0.0'


setup(
    name='spiderpig',
    version=VERSION,
    description='Caching and execution library for data analysis.',
    author='Jan Papousek',
    author_email='jan.papousek@gmail.com',
    include_package_data=True,
    packages=[
        'spiderpig',
        'spiderpig.commands',
        'spiderpig.commands.common',
    ],
    install_requires=[
        'argcomplete==1.1.1',
        'pandas==0.17.1',
    ],
    license='MIT',
)
