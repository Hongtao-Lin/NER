#encoding=utf8

import numpy as np
import os
import math
from scipy.sparse import csc_matrix

templateFile = "template.txt"
labeledFile = "labeled.txt"
unlabeledFile = "unlabeled.txt"
modelFile = "model.txt"
trainFile = "train.txt"
resultFile = "result.txt"
concatFile = "concat.txt"
finalResultFile = "final.txt"
testFile = "test.txt"
step = 5

alpha = 0.6

tokenTemplate = [(-1, 0), (0, 0), (1, 0)]

NUM_OF_LABEL = 10

NUM_OF_TAG = 1

label2Idx = dict()
idx2Label = list()



def getFeatureTemplate(templateFile):
    featureTemplates = list()
    with open(templateFile, "r") as f:
        for line in f.readlines():
            if line == "\n" or line[0] == "#":
                continue
            if line[0] == "B":
                break
            no, feature = line.split(':')
            feature = feature.replace("%x[", "(").replace("]", ")")
            featureTemplate = list()
            featureTemplate.append(no)
            for tag in feature.split('/'):
                featureTemplate.append(eval(tag))
            featureTemplates.append(featureTemplate)
    return featureTemplates


def preprocess():
    global label2Idx, idx2Label
    with open(modelFile+".txt", "r") as f:
        contentMode = 0
        Idx = 0
        for line in f.xreadlines():
            if line.isspace():
                contentMode += 1
                continue
            if contentMode == 1:
                label2Idx[line[-1]] = Idx
                idx2Label.append(line[-1])
                Idx += 1
            elif contentMode >= 2:
                break


def constructGraph(labledFile, unlabledFile, featureTemplate):
    global label2Idx

    K = 5

    # Extract all the features
    featureOccurence = dict()
    tokenOccurence = dict()
    token2Feature = dict()
    feature2Token = dict()

    token2Label = dict()
    token2Idx = dict()

    tokenIdx = 0
    tokenCount = 0

    with open(concatFile, "w") as fw:
        with open(labeledFile, "r") as f1:
            for line in f1.xreadlines():
                fw.write(line)
        with open(unlabeledFile, "r") as f2:
            for line in f2.xreadlines():
                fw.write(line)

    with open(concatFile, "r") as f:
        labels = list()
        sentence = list()
        for line in f.readlines():
            if line != "\n":
                tags = line.split()
                if len(tags) != NUM_OF_TAG:
                    label = tags.pop()
                else:
                    label = None
                labels.append(label)
                sentence.append(tags)
            else:
                for i in range(len(sentence)):
                    tagList = list()
                    for fIdx in tokenTemplate:
                        if i + fIdx[0] < 0:
                            tag = "_B-1"
                        elif i + fIdx[0] >= len(sentence):
                            tag = "_B-2"
                        else:
                            tag = sentence[i + fIdx[0]][0 + fIdx[1]]
                        tagList.append(tag)
                    token = "/".join(tagList)
                    tokenCount += 1
                    label = labels[i]

                    if tokenOccurence.has_key(token):
                        tokenOccurence[token] += 1
                        token2Idx[token] = tokenIdx
                        tokenIdx += 1
                    else:
                        tokenOccurence[token] = 1
                        token2Label[token] = [0] * NUM_OF_LABEL

                    if label != None:
                        token2Label[token][label2Idx[label]] += 1

                    for fIdxList in featureTemplate:
                        tagList = list()
                        for fIdx in fIdxList[1:]:
                            if i + fIdx[0] < 0:
                                tag = "_B-1"
                            elif i + fIdx[0] >= len(sentence):
                                tag = "_B-2"
                            else:
                                tag = sentence[i + fIdx[0]][0 + fIdx[1]]
                            tagList.append(tag)
                        feature = fIdxList[0] + ":" + "/".join(tagList)
                        if featureOccurence.has_key(feature):
                            feature2Token[feature].add(token)
                            featureOccurence[feature] = featureOccurence[feature] + 1
                        else:
                            feature2Token[feature] = {token}
                            featureOccurence[feature] = 1
                        # ......
                        if token2Feature.has_key(token):
                            token2Feature[token][feature] = token2Feature[token].get(feature, 0) + 1
                        else:
                            token2Feature[token] = {feature: 1}

        # calculate R
        for token in token2Label.keys():
            token2Label[token] = np.array(token2Label[token])
            if np.sum(token2Label[token]) != 0:
                token2Label[token] /= np.sum(token2Label[token])
        r = np.array([token2Label[token] for (token, idx) in sorted(token2Idx.items(), key=lambda item: item[1])])

        # calculate PMI vector
        pmiDict = dict()
        normOfPMI = dict()
        for token in tokenOccurence.keys():
            features = token2Feature[token]
            pmiDict[token] = dict()
            normOfPMI[token] = 0
            for feature in features:
                pmiDict[token][feature] = np.log2(
                    (float(token2Feature[token][feature]) * tokenCount * len(featureTemplate))
                    / (float(tokenOccurence[token]) * float(featureOccurence[feature])))
                normOfPMI[token] += pmiDict[token][feature] ** 2
            normOfPMI[token] = np.sqrt(normOfPMI[token])

        # construct graph matrix W
        W = csc_matrix((tokenIdx, tokenIdx))
        for token in tokenOccurence.keys():
            features = token2Feature[token]
            nonZeroToken = set()
            knnDict = dict()
            for feature in features:
                nonZeroToken |= feature2Token[feature]
            for token2 in nonZeroToken:
                dist = 0
                for feature in pmiDict[token]:
                    if feature in pmiDict[token2]:
                        dist += pmiDict[token][feature] * pmiDict[token2][feature]
                dist /= normOfPMI[token] * normOfPMI[token2]
                knnDict[token2] = dist

            knnlist = sorted(knnDict.items(), key=lambda item: item[1], reverse=True)
            for i in range(K):
                W[token2Idx[token], token2Idx[knnlist[i][0]]] = knnlist[i][1]

    return r, W, token2Idx, tokenIdx


def crfTrain(labeledFile, unlabeledFile):
    if unlabeledFile != None:
        with open(trainFile, "w") as fTrain:
            with open(labeledFile, "r") as fLabel:
                for line in fLabel.xreadlines():
                    fTrain.write(line)
        with open(trainFile, "a") as fTrain:
            with open(unlabeledFile, "r") as fUnlabel:
                for line in fUnlabel.xreadlines():
                    fTrain.write(line)
                    # crf_train with trainFile
	os.system("../CRF/CRF++-0.58/crf_learn -c 8 -f 5 -t " + templateFile + " " + trainFile + " " + modelFile)
    else:
	os.system("../CRF/CRF++-0.58/crf_learn -c 8 -f 5 -t " + templateFile + " " + labeledFile + " " + modelFile)
        # crf_train with labeledFile


    transProb = np.zeros((NUM_OF_LABEL, NUM_OF_LABEL))
    idx = 0
    with open(modelFile+".txt", "r") as fm:
        contentMode = 0
        lines = fm.readlines()
        for line in lines:
            if contentMode != 4 and line.isspace():
                contentMode += 1
                continue
            if contentMode == 4:
                if idx == NUM_OF_LABEL ** 2:
                    break
                transProb[idx / NUM_OF_LABEL][idx % NUM_OF_LABEL] = float(line)
                idx += 1
    return transProb


def postDecode():
    # run crf_test
    with open(resultFile,"w") as _:
	pass
    os.system("../CRF/CRF++-0.58/crf_test -m " + modelFile + " " +  unlabeledFile + " >" + resultFile)
    with open(resultFile,"a") as fw:
	with open(labeledFile,"r") as f1:
	    for line in f1.readlines():
		fw.write(line)
    # resultFile include labeled and unlabeled data
    with open(resultFile, "r") as f:
        lines = f.readlines()
        p = np.zeros(len(lines), NUM_OF_LABEL)
        idx = 0
        for line in lines:
            if line == "\n" or line[0] == "#":
                continue
            y = 0
            for probStr in reversed(line.split()):
                [_, prob] = probStr.split('/')
                p[idx, y] = float(prob)
                y += 1
                if (y == NUM_OF_LABEL):
                    break
            idx += 1

    return p


def tokenToType(NUM_OF_TYPES, token2Idx):
    q = np.zeros((NUM_OF_TYPES, NUM_OF_LABEL))
    with open(resultFile, "r") as f:
        sentence = list()
        marginalList = list()
        for line in f.readlines():
            if line[0] == "#":
                continue
            elif line != "\n":
                splitLine = line.split()
                tags = splitLine[:NUM_OF_TAG]
                marginals = splitLine[-NUM_OF_LABEL:]
                for i in range(len(marginals)):
                    marginals[i] = float(marginals[i][marginals[i].find('/') + 1:])
                marginalList.append(np.array(marginals))
                sentence.append(tags)
            else:
                for i in range(len(sentence)):
                    tagList = list()
                    for fIdx in tokenTemplate:
                        if i + fIdx[0] < 0:
                            tag = "_B-1"
                        elif i + fIdx[0] >= len(sentence):
                            tag = "_B-2"
                        else:
                            tag = sentence[i + fIdx[0]][0 + fIdx[1]]
                        tagList.append(tag)
                    token = "/".join(tagList)
                    q[token2Idx[token]:] += marginalList[i]

                sentence, marginalList = list(), list()

    rowSum = np.sum(q, axis=1)
    q /= rowSum.reshape(q.shape[0], 1)

    return q


def graphPropagate(q):
    p = q
    return p


def viterbiDecode(transProb, p, q, token2Idx):
    pv = alpha * p + (1 - alpha) * q
    
    tempFile = "temp.txt"
    with open(unlabeledFile, "r") as fr:
        rlines = fr.readlines()
        with open(tempFile, "w") as fw:
            labels = list()
            sentence = list()
            wlines = list()
            for rline in rlines:
                if rline != "\n":
                    tags = rline.split()
                    if len(tags) != NUM_OF_TAG:
                        label = tags.pop()
                    else:
                        label = None
                    labels.append(label)
                    sentence.append(tags)
                    wlines.append(rline)
                else:
                    tokens = list()
                    for i in range(len(sentence)):
                        tagList = list()
                        for fIdx in tokenTemplate:
                            if i + fIdx[0] < 0:
                                tag = "_B-1"
                            elif i + fIdx[0] >= len(sentence):
                                tag = "_B-2"
                            else:
                                tag = sentence[i + fIdx[0]][0 + fIdx[1]]
                            tagList.append(tag)
                        token = "/".join(tagList)
                        tokens.append(token)
                    pi = np.zeros((len(tokens), NUM_OF_LABEL))
                    prev = np.zeros((len(tokens), NUM_OF_LABEL))
                    for i in range(NUM_OF_LABEL):
                        pi[0, i] = pv[token2Idx[tokens[0]]][i]

                    for j in range(1, len(tokens)):
                        for i in range(NUM_OF_LABEL):
                            for k in range(NUM_OF_LABEL):
                                tmp = pi[j - 1, k] * pv[token2Idx[tokens[j]]][i] * transProb[k, i]
                                if tmp > pi[j, i]:
                                    pi[j, i] = tmp
                                    prev[j, i] = k
                    outLabels = list()
                    maxIdx = np.argmax(pi[len(tokens) - 1])
                    for j in range(len(tokens) - 1, -1, -1):
                        outLabels.insert(0, maxIdx)
                        maxIdx = prev[j, maxIdx]

                    for j in range(len(tokens)):
                        wline = wlines[j][:-1] + idx2Label[outLabels[j]] + "\n"
                        fw.write(wline)
                    labels = list()
                    sentence = list()
                    wlines = list()
    with open(unlabeledFile,"w") as fw:
	with open(tempFile,"r") as fr:
	    lines = fr.readlines()
	    for line in lines:
		fw.write(lines)


if __name__ == '__main__':
    featureTemplate = getFeatureTemplate(templateFile)
    transProb = crfTrain(labeledFile, None)
    preprocess()
    r, W, token2Idx, NUM_OF_TYPES = constructGraph(labeledFile, unlabeledFile, featureTemplate)
    for i in xrange(step):
        p = postDecode()
        q = tokenToType(NUM_OF_TYPES, token2Idx)
        newp = graphPropagate(q)
        viterbiDecode(transProb, p, newp, token2Idx)
        transProb = crfTrain(labeledFile, unlabeledFile)
