import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = ('Arche',
            'requests_oauthlib',
            'colander',
            'pyramid>=1.8'
            )


setup(name='arche_pas',
      version='0.1dev',
      description='Arche PAS',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Intended Audience :: Developers",
        ],
      author='Robin Harms Oredsson and contributors',
      author_email='robin@betahaus.net',
      url='https://github.com/ArcheProject/arche_pas',
      keywords='web pyramid pylons arche',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="arche_pas",
      entry_points = """\
      [fanstatic.libraries]
      arche_pas = arche_pas.fanstatic_lib:library
      """,
      )
