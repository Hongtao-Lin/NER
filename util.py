# coding:utf-8
import re, os, sys, time, codecs
import collections, copy, cPickle, operator

train_file = "data/MSRA/train.txt"
output_train_file = "data/MSRA/train.out"
test_file = "data/MSRA/testright.txt"
output_test_file = "data/MSRA/testright.out"
test_output_file = "data/MSRA/testoutput_char_e_85.out"
testright_file = "dict/testright.txt"
surname_file = "dict/surname.txt"
surname_save = "dict/surname.save"
place_file = "dict/place_surf.txt"
place_save = "dict/place_surf.save"
org_file = "dict/org_surf.txt"
org_save = "dict/org_surf.save"

surname_list = {"single": [], "double": []}
place_list = []
org_list = []

# convert full-mode into half mode
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

def read_output(fname, rname):
	f = open(fname, "r")
	f2 = open(rname, "r")
	true_y = []
	pred_y = []
	while(True):
		true_list = {}
		pred_list = {}
		test = f2.readline().decode("utf8", "ignore")
		seg2 = test.split()
		if not seg2:
			break
		sent = ""
		for s in seg2:
			sent += s.split("/")[0]
		# get true NEs.
		cur_idx = 0
		for i in range(len(seg2)):
			s = seg2[i]
			if s[-1] == "o":
				continue
			else:
				ne = s.split("/")[0]
				idx = sent.find(ne, cur_idx)
				cur_idx = idx+len(ne)	
				ne = ne + "_" + str(idx)
				true_list[ne] = s.split("/")[-1]
		# integrate predicted output.
		ne_type = ""
		ne = ""
		cur_idx = 0
		is_end = False
		while True:
			tmp_ne = ""
			tmp_ne_type = ""
			line = f.readline().strip().decode("utf8")
			l = line.split()
			if not line:
				# print "break"
				break
			tag = l[-1]
			if tag == "o":
				if ne:
					is_end = True
			elif ne_type and tag[2:] != ne_type:
				is_end = True
				tmp_ne = l[0]
				tmp_ne_type = tag.split('_')[-1]
			elif tag[0] == "b":
				if ne:
					is_end = True
					tmp_ne = l[0]
					tmp_ne_type = tag.split('_')[-1]
				else:
					ne = l[0]
					ne_type = tag.split('_')[-1]
			else:
				ne += l[0]
			if is_end and ne:
				idx = sent.find(ne, cur_idx)
				cur_idx = idx + len(ne)
				ne = ne + "_" + str(idx)
				# emit NE!
				pred_list[ne] = ne_type
				is_end = False
				ne = ""
				ne_type = ""
			if tmp_ne:
				ne = tmp_ne
				ne_type = tmp_ne_type

		total_ne = set(true_list.items()) | set(pred_list.items())
		if total_ne == set(true_list.items()):
			continue
		print test
		for item in set(pred_list.items()) - set(true_list.items()):
		# for item in total_ne:
			print item[0], item[1]
			# if item[0] in true_list:
			# 	true_y.append(item[1])
			# else:
			# 	true_y.append(u"o")
			# if item[0] in pred_list:
			# 	pred_y.append(item[1])
			# else:
			# 	pred_y.append(u"o")
		print "\n\n"
		true_list = {}
		pred_list = {}
		# print "\n"
	f.close()
	return true_y, pred_y

# given texts with format: xxx/nr xx...
# output as format: x 	0	b_nr
def read_write(fname, oname, isTest=False):
	f = open(fname, "r")
	out = open(oname, "w")
	cnt = 0
	for line in f.readlines():
		print cnt
		cnt += 1
		ne_list = []
		sent = ""
		if line.strip() == "":
			continue
		if not isTest:
			for seg in line.strip().decode("utf8").split():
				sList = seg.split("/")
				i = 0
				sent += strQ2B(sList[0])
				l = len(sList[0])
				for i in range(l):
					if sList[1] == "o":
						ne_type = "o"
					elif i == 0:
						ne_type = "b_"+sList[1]
					elif i == l-1:
						ne_type = "e_"+sList[1]
					else:
						ne_type = "i_"+sList[1]
					ne_list.append(ne_type)
			feat_list = compile_features(sent)
			# pred_list = extract_ne(sent)
			for i in range(len(ne_list)):
				# info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + pred_list[i] + "\t" + ne_list[i]
				info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + ne_list[i]
				# info = sent[i] + "\t" + ne_list[i]
				out.write(info.encode("utf8") + "\n")
		else:
			sent = line.strip().decode("utf8")
			feat_list = compile_features(sent)
			pred_list = extract_ne(sent)
			for i in range(len(ne_list)):
				info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + pred_list[i]
				out.write(info.encode("utf8") + "\n")
		out.write("\n")
	f.close()
	out.close()

def load_ne_from_file(fname, sname, tag):
	if os.path.exists(sname):
		temp_trie = cPickle.load(open(sname, "r"))
	else:
		temp_ne = get_ne(fname, tag)
		temp_trie = dawg.IntDAWG(zip(temp_ne.keys(), temp_ne.values()))
		cPickle.dump(temp_trie, open(sname, "w"))
	return temp_trie

def load_suf_from_file(fname, sname):
	temp_list = []
	if os.path.exists(sname):
		temp_list = cPickle.load(open(sname, "r"))
	else:
		f = open(fname, "r")
		for line in f.readlines():
			seg = line.strip().decode("utf8").split()
			if not seg:
				continue
			temp_list.append(seg[0])
		f.close()
		cPickle.dump(temp_list, open(sname, "w"))
	return temp_list

def init():
	global surname_list, place_list, org_list

	if os.path.exists(surname_save):
		surname_list = cPickle.load(open(surname_save, "r"))
	else:
		f = open(surname_file, "r")
		for line in f.readlines():
			seg = line.strip().decode("utf8").split()
			if not seg:
				continue
			surname = seg[0]
			if len(surname) == 1:
				surname_list["single"].append(surname)
			else:
				surname_list["double"].append(surname)
		f.close()
		cPickle.dump(surname_list, open(surname_save, "w"))

	place_list = load_suf_from_file(place_file, place_save)
	org_list = load_suf_from_file(org_file, org_save)

init()

def main():
	# read_write(train_file, output_train_file)
	read_write(test_file, output_test_file)
	# true_y, pred_y = read_output(test_output_file, testright_file)
	return

if __name__ == '__main__':
	main()