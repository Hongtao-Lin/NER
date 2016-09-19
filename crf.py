# coding:utf-8
import re, os, sys, time, codecs
import collections, copy, cPickle
import CRFPP
from rule import extract_ne


__dir__ = "./"
model_file = __dir__ + "model/char_e_85.model"
tagger = CRFPP.Tagger("-m " + model_file)

custom_file = __dir__ + "data/custom.txt"

ne_list = {}
custom_list = {}
ne_idx = {"PER":0, "LOC":1, "ORG":2}
ne_list_rev = ["PER","LOC","ORG"]
ne_dict = {"nr": "PER", "ns": "LOC", "nt": "ORG"}
ne_char = {"PER": u'\u1112', "LOC": u'\u1111', "ORG": u'\u1113'}

surname_list = {"single": [], "double": []}
place_list = {}
org_list = {}
trie = None
custom_trie = None

def compile_surname(sent, feat_list):
	global surname_list
		
	idx = len(feat_list[0])
	for f in feat_list:
		f.append("0")
	i = 0
	while True:
		if i == len(sent):
			break;
		if sent[i] in surname_list["single"]:
			feat_list[i][idx] = "1"
		if sent[i:i+1] in surname_list["double"]:
			feat_list[i][idx] = "2"
			feat_list[i+1][idx] = "2"
			i += 1
		i += 1

def compile_place(sent, feat_list):
	global place_list
		
	idx = len(feat_list[0])
	for f in feat_list:
		f.append("0")
	i = 0
	while True:
		if i == len(sent):
			break;
		if sent[i] in place_list:
			feat_list[i][idx] = "1"
		elif sent[i:i+2] in place_list:
			feat_list[i][idx] = "1"
			feat_list[i+1][idx] = "1"
			i += 1
		i += 1

def compile_org(sent, feat_list):
	global org_list
		
	idx = len(feat_list[0])
	for f in feat_list:
		f.append("0")
	i = 0
	while True:
		if i == len(sent):
			break;
		if sent[i] in org_list:
			feat_list[i][idx] = "1"
		elif sent[i:i+2] in org_list:
			feat_list[i][idx] = "1"
			feat_list[i+1][idx] = "1"
			i += 1
		elif sent[i:i+3] in org_list:
			feat_list[i][idx] = "1"
			feat_list[i+1][idx] = "1"
			feat_list[i+2][idx] = "1"
			i += 2
		i += 1

def compile_features(sent):
	feat_list = []
	for i in range(len(sent)):
		feat_list.append([])
	compile_surname(sent, feat_list)
	compile_place(sent, feat_list)
	compile_org(sent, feat_list)

	return feat_list

def strQ2B(ustring):
	"""全角转半角"""
	rstring = ""
	for uchar in ustring:
		inside_code=ord(uchar)
		if inside_code == 12288:
			inside_code = 32
		# # ，？！：；（） are not converted
		# elif inside_code in [65292,65311,65281,65307,65306,65288,65289]:
		# 	inside_code = inside_code
		elif (inside_code >= 65281 and inside_code <= 65374):
			inside_code -= 65248
		rstring += unichr(inside_code)
	return rstring

def recover_ne(tagger, ne_map):
	segment = []
	formatted = []
	size = tagger.size()
	xsize = tagger.xsize()
	ne_type = ""
	ne = ""
	cur_idx = 0
	is_end = False
	for i in range(0, size):
		tmp_ne = ""
		tmp_ne_type = ""
		tag = tagger.y2(i)
		char = tagger.x(i, 0)
		# print tag, char
		char = ne_map.get(i, char)
		cur_type = ne_dict.get(tag[2:], "OTHER")

		if tag[0] == "b":
			segment.append(char)
			formatted.append(cur_type)
		else:
			if formatted and cur_type != "" and formatted[-1] == cur_type:
				# print [char], char
				segment[-1] += char
			else:
				segment.append(char)
				formatted.append(cur_type)

	return segment, formatted

def crf_subtargger(tagger):
	segment = []
	formatted = []
	size = tagger.size()
	xsize = tagger.xsize()
	ne_type = ""
	ne = ""
	cur_idx = 0
	is_end = False
	prev_type = None
	for i in range(0, size):
		tmp_ne = ""
		tmp_ne_type = ""
		tag = tagger.y2(i)
		char = tagger.x(i, 0)
		cur_type = ne_dict.get(tag[2:], "o")
		if cur_type != "o":
			cur_type = "2-" + cur_type
		if tag[0] == "b" or cur_type != prev_type:
			segment.append(char)
			formatted.append(cur_type)
		else:
			segment[-1] += char
		prev_type = cur_type
	tagger.clear()
	return segment, formatted

def crf_tagger(sent):
	# sent = re.sub(r"\s+", "", sent, flags=re.UNICODE)
	ne_map = {}
	dict1 = extract_ne(sent, convert=2)
	# for i in ne_map:
	# 	print i, ne_map[i]
	# print dict1["segment"]
	segment, formatted = [], []
	for (f0, seg) in zip(dict1["formatted"], dict1["segment"]):
		if f0 == "o":
			# feat_list = compile_features(seg)
			for s0 in filter(None,re.split(ur'(\s|[\u4e00-\u9fa5])', seg)):
				# info = seg[j] + "\t" + "\t".join(feat_list[j])
				print s0
				tagger.add(s0.encode("utf8"))
			tagger.parse()
			s, f = crf_subtargger(tagger)
			segment += s
			formatted += f
		else:
			segment.append(seg.encode("utf8"))
			formatted.append("1-" + f0) # 1- means first stage

	print segment
	return {"segment": segment, "formatted": formatted}

def test_speed(fname):
	start = time.time()

	f = open(fname, "r")
	for line in f.readlines():
		if line.strip() == "":
			continue
		crf_tagger(line.decode("utf8"))

	print time.time() - start


if __name__ == '__main__':
	# test_speed("data/testright.txt")
	crf_tagger(u",习近平爱我")