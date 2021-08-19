# mvodb

[![ci](https://github.com/pawamoy/mvodb/workflows/ci/badge.svg)](https://github.com/pawamoy/mvodb/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-mkdocs%20material-blue.svg?style=flat)](https://pawamoy.github.io/mvodb/)
[![pypi version](https://img.shields.io/pypi/v/mvodb.svg)](https://pypi.org/project/mvodb/)
[![gitter](https://badges.gitter.im/join%20chat.svg)](https://gitter.im/mvodb/community)

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
pyenv install 3.6.12

# make it available globally
pyenv global system 3.6.12
```
</details>

## Installation

With `pip`:
```bash
python3.6 -m pip install mvodb
```

With [`pipx`](https://github.com/pipxproject/pipx):
```bash
python3.6 -m pip install --user pipx

pipx install --python python3.6 mvodb
```

## Usage (as a library)

TODO

## Usage (command-line)

```console
$ mvodb -h
usage: mvodb [-h] [-y] FILE [FILE ...]

positional arguments:
  FILE              Files to move/rename.

optional arguments:
  -h, --help        show this help message and exit
  -y, --no-confirm  Do not ask confirmation.
```
