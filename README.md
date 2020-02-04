<!--
IMPORTANT:
  This file is generated from the template at 'scripts/templates/README.md'.
  Please update the template instead of this file.
-->

# mvodb
[![pipeline status](https://gitlab.com/pawamoy/mvodb/badges/master/pipeline.svg)](https://gitlab.com/pawamoy/mvodb/pipelines)
[![coverage report](https://gitlab.com/pawamoy/mvodb/badges/master/coverage.svg)](https://gitlab.com/pawamoy/mvodb/commits/master)
[![documentation](https://img.shields.io/readthedocs/mvodb.svg?style=flat)](https://mvodb.readthedocs.io/en/latest/index.html)
[![pypi version](https://img.shields.io/pypi/v/mvodb.svg)](https://pypi.org/project/mvodb/)

Rename and move files using metadata from online databases.

## Requirements
mvodb requires Python 3.6 or above.

<details>
<summary>To install Python 3.6, I recommend using <a href="https://github.com/pyenv/pyenv"><code>pyenv</code></a>.</summary>

```bash
# install pyenv
git clone https://github.com/pyenv/pyenv ~/.pyenv

# setup pyenv (you should also put these three lines in .bashrc or similar)
export PATH="${HOME}/.pyenv/bin:${PATH}"
export PYENV_ROOT="${HOME}/.pyenv"
eval "$(pyenv init -)"

# install Python 3.6
pyenv install 3.6.8

# make it available globally
pyenv global system 3.6.8
```
</details>

## Installation
With `pip`:
```bash
python3.6 -m pip install mvodb
```

With [`pipx`](https://github.com/cs01/pipx):
```bash
python3.6 -m pip install --user pipx

pipx install --python python3.6 mvodb
```

## Usage (as a library)
TODO

## Usage (command-line)
```
usage: mvodb [-h] [-y] FILE [FILE ...]

positional arguments:
  FILE              Files to move/rename.

optional arguments:
  -h, --help        show this help message and exit
  -y, --no-confirm  Do not ask confirmation.

```


