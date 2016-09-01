# CGHQ LIMS service [![Build Status](https://travis-ci.org/CGHQ/qc.svg)](https://travis-ci.org/CGHQ/qc) [![Coverage Status](https://coveralls.io/repos/CGHQ/qc/badge.svg?branch=master&service=github)](https://coveralls.io/github/CGHQ/qc?branch=master)
Interface with genologics LIMS.

## Install
```bash
$ git clone https://github.com/CGHQ/qc
$ cd qc
$ pip install -e .
```

### Docker
To build a Docker image you need to provide a `.genologicsrc` file in the root of the repository. Since it contains sensitive data it is gitignored by default.

```bash
$ docker build -t "cghq:lims" .
$ docker run -it -p 8080:8080 "cghq:lims"
```

You can specify additional options to *gunicorn* like the number of processes of the service you want to spin up:

```bash
$ docker run -it -p 8080:8080 "cghq:lims" -w 4
```
