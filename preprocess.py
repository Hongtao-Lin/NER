# coding:utf-8
import os, re
from util import strQ2B

# Preprocess the data in the original ontonotes5.0, specifically, we:
# 1. remove the irrelavant string in ontonotes.
# 2. leave out only three types of NE: PER, ORG, LOC.
# 3. convert full-mode(全角) to half-mode(半角)



tagDict = {"GPE":"/ns","ORG":"/nt","PERSON":"/nr"}

__dir__ = "ontonotes-release-5.0/data/files/data/chinese/annotations/"
corp = ["bc", "bn", "mz", "tc", "nw", "wb"]

def replace_exclude(m):
		# print m.group()
	if "ENAMEX" in m.group():
		return m.group()
	return ""

def replace_include(m):
	return "".join(m.group().split())

def extract_ne_from_onto(fname, o):
	f = open(fname, "r")
	a = f.readline()
	print a
	print fname
	for line in f.readlines():
		sent = line.strip().decode("utf8")
		if sent == "</DOC>":
			continue
		sent = strQ2B(sent)
		sent = re.sub(r"<( /)?/? ([^<]+) >", replace_exclude, sent)
		sent = re.sub(r"<ENAMEX ([^<]+)</ENAMEX>", replace_include, sent)
		# print sent
		sent = sent.split() 
		sList = []
		i = 0
		while True:
			if i == len(sent):
				break
			s = sent[i]
			if s[:7] == "<ENAMEX":
				tag = tagDict.get(s.split("\"")[1], "/o")
				temp = s.split(">")[1].split("<")[0]
				sList.append(temp+tag)
			elif s[0] != "<":
				sList.append(s+"/o")
			else:
				a = 1
				print line
				for p in sent:
					print p
				# print "".join(sent)	
				# print fname
			i += 1
		sent_write = " ".join(sList)
		o.write(sent_write.encode("utf8") + "\n")
	f.close()

def ontonotes_ne():
	for c in corp:
		f = open("data/Onto/ne_" + c + ".out", "w")
		path = __dir__+c+"/"
		for root, dirs, files in os.walk(path):
			for file in files:
				# print root, file
				if file[-5:] == ".name":
					extract_ne_from_onto(root+'/'+file, f)
		f.close()

if __name__ == '__main__':
	ontonotes_ne()