gifprime
========

GIF codec in Python

Dependencies:
```
pip install -r requirements.txt
```

Running tests also requires the ImageMagick and exiftool utilities to be available.

Encoding:
```
$ python -m gifprime encode --help
usage: gifprime encode [-h] [--output OUTPUT] images [images ...]

positional arguments:
  images                image frame for gif

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        output filename
```

Decoding:
```
$ python -m gifprime decode --help
usage: gifprime decode [-h] filename

positional arguments:
  filename

optional arguments:
  -h, --help  show this help message and exit
```


Test:
```
py.test
```
