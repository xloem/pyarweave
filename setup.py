from distutils.core import setup

setup(
  name="PyArweave",
  packages = ['ar'],
  version="0.1.0",
  description="Tiny Arweave Library",
  url="https://github.com/xloem/pyar",
  keywords=['arweave', 'crypto'],
  classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
    "Operating System :: OS Independent",
  ],
  install_requires=[ # try to reduce these
    'arrow',
    'python-jose',
    'pynacl',
    'pycryptodome',
    'cryptography',
    'requests',
    'psutil'
  ],
)
