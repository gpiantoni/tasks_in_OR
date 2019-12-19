MICROPHONE TASK
===============

Installation
------------

```bash
git clone https://github.com/gpiantoni/tasks_in_OR.git
git checkout mic
pip install -e .
```

Run it
------

```bash
qttasks syllables
```


Parameters
----------

Parameters are defined in `default.json`. 
You can edit this file to pass parameters to the program.

Codec
-----

Depending on the installation / operative system, you might need to change the codec used.
To list the codecs currently available, run this code in python:

```python
from PyQt5.QtWidgets import QApplication
from PyQt5.QtMultimedia import QAudioRecorder

app = QApplication([])
print(QAudioRecorder().supportedAudioCodecs())
```

and select one of the available codecs.
