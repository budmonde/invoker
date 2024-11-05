from setuptools import setup

setup(
    name='invoker',
    version='0.2.0',
    py_modules=['invoker'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        invoker=invoker:cli
    '''
)
