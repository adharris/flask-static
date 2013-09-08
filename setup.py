from setuptools import setup

setup(
  name='Flask-Static',
  version='0.1.0',
  long_description=__doc__,
  packages=['flask_static'],
  include_package_data=True,
  zip_safe=False,
  install_requires=['Flask', 'Flask-SQLAlchemy', 'Frozen-Flask', 'inflection',
    'PyYAML', 'Markdown']
)