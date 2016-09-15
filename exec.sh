#!/bin/sh
crf/crf_learn -c 4 template data/train.out model/model-1
crf/crf_learn -c 4 -f 3 -a CRF-L1 template data/train.out model/model
crf/crf_learn -c 4 -f 3 MIRA template data/train.out model/model

crf/crf_test -m model/model data/testright.out > data/testoutput.out