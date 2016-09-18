# NER

## Overview

Here in the project I tried CRF as well as rule-based system. 

We use MSRA `06 as the dataset, which is also the official dataset for SIGHAN 06.

## Architecture

- data/: All training/testing data. 
- dict/: All external resources.
- model/: Save all valid models.
- CRF/: CRF++ source code and templates.
- demo/: NER web system.
- exec.sh: bash script for CRF running.
- colleval.pl: official evaluation code (in perl) for directly evaluating CRF++ output. 
- util.py: All utility functions. e.g.: function to convert the original MSRA data to CRF++ format.
- preprocessing.py: Convert OntoNotes5.0 format to CRF++ format.
- rule.py: Constrcut rules to extract NEs (with the possible aid of external dict.)

## CRF Baseline

The CRF template are borrowed from "Using Non-Local Features to Improve Named Entity Recognition Recall" in the 06'SIGHAN competition. 

In this project, both the baseline template and so-called two-stage CRF as described in the paper are implemented. 

The core function of two-stage CRF is implemented in `util.py`  @ `read_write` (it reads external source for CRF) to transform input dataset to two-stage features for CRF++.

You can write a bash to pipeline the whole process into one.

Generally, the baseline performance is consistent with the paper (F1: 87.5), but two-staged is not (F1: 88.5, but in the paper, it's 89.6). It's suspicious whether the paper reported it right, because several papers pointed out this inconsistencies.

Note that the CRF baseline uses no external resources, which is refered to as `closed-track`.

## Rule-based System

This rule based system aims at doing quick look up for obvious entities, using rules that are encoded from human intuitions (sounds hard.)

But currently I implemented another rule algorithm: first extract all possible entities using dictionaries and simple consistency rules (such as the occurance of "先生" may follows a person name.) Then use a ruleset to **reject** some of them with possible sign of error.


This ruleset uses word boundary (gathered using statistics) as the possible rejection. Currently the word boundary infomation is also a gathered dictionary from web. A possible improvement is to use large set of web data to extract possible two-word combinations by point-wise mutual information, which I roughly implemented it in `util.py`. 

Also, note that the external dictionary (person.txt, org.txt, etc) may not be clean enough. 

The regex for constructing PER/LOC/ORG are borrowed from "Learning Pattern Rules for Chinese Named Entity Extraction", 02'AAAI.

## NER Webapp

Front: bootstrap, react, jquery (use webpack for packing)

Back: flask

Run:
use virtualenv  
```bash  
$ virtualenv env  
$ source env/bin/activate  
$ pip install -r requirenments.txt

$ python run.py  
```

Javascript:

Need node and webpack if change in js is needed.
```bash  
$ cd app/static/js  
$ npm install  
$ npm install -g webpack  
$ webpack --watch
```

To change the NER core function, consider the `view.py` and python codes in `src/*.py`. To change the webpage front-end or function, consider the  `static/js/`.
