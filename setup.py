from pip.download import PipSession
from pip.req import parse_requirements
from setuptools import find_packages, setup

from goomba import __version__ as goomba_version

reqs = parse_requirements('requirements.txt', session=PipSession())
requirements = [str(req.req) for req in reqs]

setup(
    name='goomba',
    author='Casey Weed',
    author_email='cweed@caseyweed.com',
    version=goomba_version,
    description='Refresh Kibana mappings for cluster',
    url='https://github.com/battleroid/goomba',
    py_modules=['goomba'],
    install_requires=requirements,
    tests_require=['pytest'],
    extras_require={'test': ['pytest']},
    entry_points="""
        [console_scripts]
        goomba=goomba:main
    """
)
