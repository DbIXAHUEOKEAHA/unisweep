# atto-device-python

Python API for interactions with Attocube devices

## Installation

Preferrably, install the library using a Git branch tag to ensure it's not going to change unexpectedly. For this, look at the most recent version in the right sidebar, and use that, e.g. for `v1.0.1`:

```shell
pip install git+ssh://git@github.com/attocube-systems/atto-device-python.git@1.0.1
```

or, to install from `master` (which might break at any point):

```shell
pip install git+ssh://git@github.com/attocube-systems/atto-device-python.git
```

## Usage

```python
from atto_device import AMC

machine = AMC("192.168.53.12")
```
