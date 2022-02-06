from setuptools import setup, find_packages


setup(
    name='ec2_exercise',
    extras_require=dict(tests=['pytest']),
    packages=find_packages(where='project'),
    package_dir={'': "project"}
)
