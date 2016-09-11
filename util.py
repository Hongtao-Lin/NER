# coding:utf-8
import re, os, sys, time, codecs
import collections, copy, cPickle, operator
import math, string

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

num_list = string.digits + u"一二三四五六七八九十两零几多"
punct_list = string.punctuation + "be" + u"。”’、—"
sw_list = u"些仅不个乎也了仍们你我他她但借假再几别既即却又另只的"\
	u"叫各吓吗嘛否吧吱呀呃哦呗呢呵呜呸咋咦咧咱咳哇哈哎哒哟哦噢哪哼唉啥啦啪"\
	u"喂喏喔喽嗡嗬嗯嗳嘎嘘嘻嘿里是还到"\
	u"它就很得怎么打把某死每没而虽被谁说贼这俄"
org_sw = u"些仅不个乎也了仍们你我他她但再几别既即却又另只的"\
	u"叫各吓吗嘛否吧吱呀呃哦呗呢呵呜呸咋咦咧咱咳哇哈哎哒哟哦噢哪哼唉啥啦啪"\
	u"喂喏喔喽嗡嗬嗯嗳嘎嘘嘻嘿里是还到"\
	u"它很得怎么把某每没而虽被谁说贼这"
org_sw += punct_list
name_sw = sw_list + u"说摄地会使委市" + u"\u1111\u1112\u1113"

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
def read_write(fname, oname, isTest=False, extract_ne=None):
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
				if seg[0] == u"\ufeff":
					seg = seg[1:]
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
			if extract_ne:
				pred_list = extract_ne(sent)
			for i in range(len(ne_list)):
				# if extract_ne:
				# 	info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + pred_list[i] + "\t" + ne_list[i]
				# else:
				# 	info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + ne_list[i]
				info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + ne_list[i] + "\t" + pred_list[i] 
				# info = sent[i] + "\t" + ne_list[i]
				out.write(info.encode("utf8") + "\n")
		else:
			sent = line.strip().decode("utf8")
			feat_list = compile_features(sent)
			if extract_ne:
				pred_list = extract_ne(sent)
			for i in range(len(ne_list)):
				if extract_ne:
					info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + pred_list[i] + "\t" + ne_list[i]
				else:
					info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + ne_list[i]
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


def is_valid(c, d=[]):
	flag = (c >= u"\u4e00" and c <= u"\u9fa5")
	flag = flag and (c not in org_sw+num_list)
	if d != []:
		flag = flag and (c in d)
	return flag

def get_pmi(fname, dname, k):
	f = open(fname, "r")
	sur = {}
	pre = {}
	with open(dname, "r") as f1:
		for l in f1.readlines():
			l = l.strip().decode("utf8").split()
			if not l:
				continue
			l = l[0]
			pre[l[0]] = pre.get(l[0], 0) + 1
			sur[l[-1]] = sur.get(l[-1], 0) + 1
	sur = sorted(i for i in sur if i >= 5)
	pre = sorted(i for i in pre if i >= 5)
	bi = {}
	uni = {}
	pmi = {}
	for line in f.xreadlines():
		# preprocess
		line = strQ2B(line.decode("utf8").strip())
		for i in range(len(line[:])):
			if is_valid(line[i]):
				uni[line[i]] = uni.get(line[i], 0) + 1
			if i < len(line)-1 and is_valid(line[i]) and is_valid(line[i+1]):
				bi[line[i:i+2]] = bi.get(line[i:i+2], 0) + 1
	f.close()
	temp = sum(bi.values())
	for b in bi:
		bi[b] /= float(temp)
	temp = sum(uni.values())
	for u in uni:
		uni[u] /= float(temp)
	print len(bi)
	for b in bi:
		if uni[b[0]] == 0 or uni[b[1]] == 0 or (b[0] not in sur and b[1] not in pre):
			continue
		pmi[b] = math.log( bi[b]**k / (uni[b[0]]*uni[b[1]]) )
	pmi = sorted(pmi.items(), key=operator.itemgetter(1), reverse=True)[:5000]
	o = open("pmi_res2.out", "w")
	for p, v in pmi:
		o.write(p.encode("utf8") + "\t" + str(v) + "\n")
	o.close()

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
	# read_write(test_file, output_test_file)
	# true_y, pred_y = read_output(test_output_file, testright_file)
	get_pmi("./data/pmi_text.txt", "./dict/all.txt", 10)

if __name__ == '__main__':
	main()