# NER - Algorithm

## Overview

Here in the project I tried CRF as well as rule-based system. 

We use MSRA `06 as the dataset, which is also the official dataset for SIGHAN 06.

The regex for constructing PER/LOC/ORG are borrowed from "Learning Pattern Rules for Chinese Named Entity Extraction", 02'AAAI.

## CRF Baseline

The CRF template are borrowed from "Using Non-Local Features to Improve Named Entity Recognition Recall" in the 06'SIGHAN competition. 

In this project, both the baseline template and so-called two-stage CRF as described in the paper are implemented. 

The core function of two-stage CRF is implemented in `util.py`  @ `read_write` (it reads external source for CRF) to transform input dataset to two-stage features for CRF++.

You can write a bash to pipeline the whole process into one.

Generally, the baseline performance is consistent with the paper (F1: 87.5), but two-staged is not (F1: 88.5, but in the paper, it's 89.6). It's suspicious whether the paper reported it right, because several papers pointed out this inconsistencies.

Note that the CRF baseline uses no external resources, which is refered to as `closed-track`.

## Rule-based System

talk about how 

## Architecture

data/: All training/testing data.
dict/: All external resources.
model/: Save all valid models.
CRF/: CRF++ source code and templates.

- util.py: All utility functions. e.g.: function to convert the original MSRA data to CRF++ format.
- preprocessing.py: Convert OntoNotes5.0 format to CRF++ format.
- rule.py: Constrcut rules to extract NEs (with the possible aid of external dict.)


## TODO:

upload the transcript to evaluate results.