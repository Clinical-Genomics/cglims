# CGLims [![Build Status][travis-image]][travis-url]

_cglims_ is a tool to interface with our instance of Genologics Clarity LIMS.

## Background

We have an instance of Clarity LIMS that we mainly use for tracking lab work. However, this is the true source of information for all samples. We use the information extensively also in the downstream bioinformatics tools.

Therefore, it's good to have a single interface that implements our internal conventions such as how to mark a sample as cancelled or how to parse the application tag correctly.

We have also found the web interface a little to cumbersome to get and update small pieces of information. Sometimes it's more convenient to be able to do this from the command line or as part of a script. This is what the package is aiming to do.

## Documentation

A brief documentation of intended usage.

### Installation

You can install `cglims` from source:

```bash
$ git clone https://github.com/Clinical-Genomics/cglims && cd cglims
$ pip install --editable .
```

You also need a YAML config file describing how to connect to the LIMS instance. It should contain information like this:

```yaml
---
host: https://genologics.mycompany.com
username: apiuser
password: somepassword
```

### Getting information

You can quickly get information about samples. For a single sample:

```bash
$ cglims get --pretty ADM342341
# or for an old Clinical Genomics ID
$ cglims get 000043T
```

The `--pretty` flag will simply print the information in a more readable format.

You can also get information about all samples in a case. For that you need the case id or "<customer>-<family>":

```bash
$ cglims get cust003-16105
```

This will print the same output but for each sample consecutively.

### Updating information

It's possible to update a single UDF for a single sample using the CLI. For this you _need_ to use the sample LIMS id - you can't use the old Clinical Genomics ID.

```bash
$ cglims update ADM342341 familyID 16106
```

The tool will print both the old and new value of the field so if you integrate it in a script you will have a log of what has been updated in the LIMS.

### Generating pedigree files

You can generate a pedigree file for a family in LIMS. All you need is to supply the customer and family ids.

```bash
$ cglims pedigree cust003 16105 > /path/to/16105_pedigree.txt
```

N.B. If a sample is marked as cancelled (UDF: "cancelled", value: "yes") it will not show up in the pedigree.


[travis-url]: https://travis-ci.org/Clinical-Genomics/cglims
[travis-image]: https://img.shields.io/travis/Clinical-Genomics/cglims.svg?style=flat-square
