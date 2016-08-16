#encoding=utf-8
import re, os
import jieba
import dawg # C++ based Trie-tree implementation
import argparse, time
import collections, copy, cPickle, operator, string

nr_file = "data/person.txt"
ns_file = "data/place.txt"
nt_file = "data/org.txt"
ne_save = "data/ne.save"
ne_list = {}
ne_idx = {"nr":0, "ns":1, "nt":2}
ne_list_rev = ["PER", "LOC", "ORG"]
ne_char = {"PER": u'\u1111', "LOC": u'\u1112', "ORG": u'\u1113'}
stopword_file = "data/stopwords.txt"
kw_file1 = "kw0.out"
kw_file2 = "kw1.out"
rule_file = "rule.out"
surname_file = "data/surname.txt"
surname_save = "data/surname.save"
place_file = "data/place_surf.txt"
place_save = "data/place_surf.save"
org_file = "data/org_surf.txt"
org_save = "data/org_surf.save"

surname_list = {"single": [], "double": []}
place_list = []
org_list = []
stopwords_list = []
rule_list = []
exclude_ne = [[], [], []]
group_dict = {}
rule = None
org_rule = None
trie = None
place_trie = None
org_trie = None
person_trie = None
num_list = string.digits + u"一二三四五六七八九十两零几多"
punct_list = string.punctuation + "be" + u"。”‘’“、—"
sw_list = u"些仅不个乎也了仍们你我他她但借假像再在几别既即却又另只的"\
	u"叫各吓吗嘛否吧吱呀呃哦呗呢呵呜呸咋咦咧咱咳哇哈哎哒哟哦噢哪哼唉啥啦啪"\
	u"喂喏喔喽嗡嗬嗯嗳嘎嘘嘻嘿里是还到"\
	u"它就很得怎么打把某死每没而虽被谁说贼这俄"
debug = False

kw_list1 = []
kw_list2 = []
p1 = {} # c-1_ne
p2 = {}	# ne_c1
p3 = {} # c-1_ne_c1
p4 = {} # c-2c-1_ne
p5 = {} # ne_c1c2

def init():
	global ne_list, surname_list, place_list, org_list, trie, place_trie, org_trie, person_trie
	global kw_list1, kw_list2, rule_list
	if os.path.exists(ne_save):
		ne_list = cPickle.load(open(ne_save, "r"))
	else:
		get_ne(ns_file, "ns")
		get_ne(nr_file, "nr")
		get_ne(nt_file, "nt")
		ne_list = collections.OrderedDict(sorted(ne_list.items()))
		# save NEs:
		cPickle.dump(ne_list, open(ne_save, "w"))

	print len(ne_list.keys())
	trie = dawg.IntDAWG(zip(ne_list.keys(), ne_list.values()))
	# trie = dawg.IntCompletionDAWG(zip(ne_list.keys(), ne_list.values()))
	place_ne = {k:v for k,v in ne_list.items() if v == 1}
	place_trie = dawg.IntDAWG(zip(place_ne.keys(), place_ne.values()))
	org_ne = {k:v for k,v in ne_list.items() if v == 2}
	org_trie = dawg.IntDAWG(zip(org_ne.keys(), org_ne.values()))
	person_ne = {k:v for k,v in ne_list.items() if v == 0}
	person_trie = dawg.IntDAWG(zip(person_ne.keys(), person_ne.values()))
	# load second-phase dicts.
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

	if os.path.exists(place_save):
		place_list = cPickle.load(open(place_save, "r"))
		# print place_list
	else:
		f = open(place_file, "r")
		for line in f.readlines():
			seg = line.strip().decode("utf8").split()
			if not seg:
				continue
			place = seg[0]
			place_list.append(place)
		f.close()
		cPickle.dump(place_list, open(place_save, "w"))

	if os.path.exists(org_save):
		org_list = cPickle.load(open(org_save, "r"))
	else:
		f = open(org_file, "r")
		for line in f.readlines():
			seg = line.strip().decode("utf8").split()
			if not seg:
				continue
			org = seg[0]
			org_list.append(org)
		f.close()
		cPickle.dump(org_list, open(org_save, "w"))

	sw = open(stopword_file, "r")
	for line in sw.readlines():
		stopwords_list.append(line.strip())
	sw.close()

	kw = open(kw_file1, "r")
	for line in kw.readlines():
		kw_list1.append(line.strip().decode("utf8"))
	kw.close()
	
	kw = open(kw_file2, "r")
	for line in kw.readlines():
		kw_list2.append(line.strip().decode("utf8"))
	kw.close()

	return trie

def get_stat(fname):
	global p1, p2, p3, p4, p5
	f = open(fname, "r")
	cnt = 0
	for line in f.readlines():
		print cnt
		cnt += 1
		ne_list = []
		sent = "bb"
		if line.strip() == "":
			continue
		for seg in line.strip().decode("utf8").split():
			sList = seg.split("/")
			i = 1
			if sList[1] != "o":
				ne_type = ne_list_rev[ne_idx[sList[1]]]
				sList[0] = ne_char[ne_type]
			sent += sList[0]
		sent += "ee"
		sent = strQ2B(sent)
		for i in range(2, len(sent)-2):
			if sent[i] not in ne_char.values():
				continue
			p1[sent[i-1:i+1]] = p1.get(sent[i-1:i+1], 0) + 1
			p2[sent[i:i+2]] = p2.get(sent[i:i+2], 0) + 1
			p3[sent[i-1:i+2]] = p3.get(sent[i-1:i+2], 0) + 1
			p4[sent[i-2:i+3]] = p4.get(sent[i-2:i+3], 0) + 1
			p5[sent[i:i+3]] = p5.get(sent[i:i+3], 0) + 1
	p1 = {k:v for k, v in p1.items() if v > 3}
	p2 = {k:v for k, v in p2.items() if v > 3}
	p3 = {k:v for k, v in p3.items() if v > 3}
	p4 = {k:v for k, v in p4.items() if v > 3}
	p5 = {k:v for k, v in p5.items() if v > 3}
	sp1 = sorted(p1.items(), key=operator.itemgetter(1), reverse=True)
	sp2 = sorted(p2.items(), key=operator.itemgetter(1), reverse=True)
	sp3 = sorted(p3.items(), key=operator.itemgetter(1), reverse=True)
	sp4 = sorted(p4.items(), key=operator.itemgetter(1), reverse=True)
	sp5 = sorted(p5.items(), key=operator.itemgetter(1), reverse=True)
	f = open("p1.out", "w")
	i = 0
	for (k, v) in sp1:
		if i > 300:
			break
		i += 1
		print k, v
		f.write(k.encode("utf8") + "\t" + str(v) + "\n")
	f.close()
	f = open("p2.out", "w")
	i = 0
	for (k, v) in sp2:
		if i > 300:
			break
		i += 1
		print k, v
		f.write(k.encode("utf8") + "\t" + str(v) + "\n")
	f.close()
	f = open("p3.out", "w")
	for (k, v) in sp3:
		print k, v
		f.write(k.encode("utf8") + "\t" + str(v) + "\n")
	f.close()
	f = open("p4.out", "w")
	for (k, v) in sp4:
		print k, v
		if k[4] in ne_char.values() or k[1] in ne_char.values() or  k[3] in ne_char.values() or k[0] in ne_char.values():
			continue
		f.write(k.encode("utf8") + "\t" + str(v) + "\n")
	f.close()
	f = open("p5.out", "w")
	for (k, v) in sp5:
		print k, v
		f.write(k.encode("utf8") + "\t" + str(v) + "\n")
	f.close()

	f1 = open("sw.out", "w")	# b/e, puncts, letters and stopwords
	f2 = open("comb.out", "w")	# contains other nes
	f3 = open("num.out", "w")	# contains numbers or dates
	f4 = open("other.out", "w")	# other

	sw_list = "".join(stopwords_list) + string.punctuation + string.ascii_letters
	sw_list = sw_list.decode("utf8")
	for (k, v) in sp4:
		flag = False
		if k[0] in sw_list or k[1] in sw_list:
			f1.write(k.encode("utf8") + "\n")
			flag = True
		if k[0] in ne_char.values() or k[1] in ne_char.values():
			f2.write(k.encode("utf8") + "\n")
			flag = True
		if k[0] in num_list or k[1] in num_list:
			f3.write(k.encode("utf8") + "\n")
			flag = True
		if not flag:
			f4.write(k.encode("utf8") + "\n")
	for (k, v) in sp5:
		flag = False
		if k[2] in sw_list or k[1] in sw_list:
			f1.write(k.encode("utf8") + "\n")
			flag = True
		if k[2] in ne_char.values() or k[1] in ne_char.values():
			f2.write(k.encode("utf8") + "\n")
			flag = True
		if k[2] in num_list or k[1] in num_list:
			f3.write(k.encode("utf8") + "\n")
			flag = True
		if not flag:
			f4.write(k.encode("utf8") + "\n")
	f1.close()
	f2.close()
	f3.close()
	f4.close()

def extend_rules():
	f = open("p4.out", "r")
	num_list = string.digits + u"一二三四五六七八九十两零"
	punct_list = string.punctuation + "be" + u"。”‘’“、"
	rule = set()
	for l in f.readlines():
		l = l.split()[0].decode("utf8")
		if l[1] in punct_list and l[3] in punct_list:
			continue
		for i in range(len(l)):
			if l[i] in num_list:
				l = l.replace(l[i], "N")
			if l[i] in punct_list:
				l = l.replace(l[i], "P")
		rule.add(l)
	f.close()
	f = open("rule.out", "w")
	for r in rule:
		f.write(r.encode("utf8") + "\n")
	f.close()

def extend_words():
	f = open("p4.out", "r")
	words = {}
	filter_list = string.punctuation + "be" + u"。”‘’“、" + string.digits + u"一二三四五六七八九十两零"
	for l in f.readlines():
		l = l.split()[0]
		l = l.strip().decode("utf8")
		if l[0] in filter_list:
			if l[1] not in filter_list:
				words[l[1]] = set()
		else:
			if l[1] in filter_list:
				words[l[0]] = set()
			else:
				words[l[:2]] = set()

		if l[4] in filter_list:
			if l[3] not in filter_list:
				words[l[3]] = set()
		else:
			if l[3] in filter_list:
				words[l[4]] = set()
			else:
				words[l[3:]] = set()
	f.close()

	syn_sets = []
	f = open("syn.txt", "r")
	for l in f.readlines():
		syn_list = l.decode("utf8").split()[1:]
		temp_set = set()
		for w in syn_list:
			if len(w) < 3:
				temp_set.add(w)
		if temp_set:
			syn_sets.append(temp_set)

	for w in words:
		words[w].add(w)
		for s in syn_sets:
			if w in s:
				# print w
				# print s
				words[w] = words[w].union(s)

	is_end = False
	print len(words)
	comb_list = [
		["记者","同志","总统","教练","先生","女士","主席","主任","委员","部长","副委","秘书","客人","副部","领导","院士","员长","上将","学家","院长","团长","市长","总书"\
		,"主任","董事","经理","校长","首相","总裁"],
		["报道","说","指出","表示","强调","要求","介绍","认为","告诉","还说","代表","希望","感谢"],
		["会见","举行","访问","进行"]
	]
	for c in comb_list:
		ccc = c[0]
		ccc = ccc.decode("utf8")
		for cc in c[1:]:
			cc = cc.decode("utf8")
			print cc
			words[ccc] = words[ccc].union(words[cc])
			words[cc] = set()
	while not is_end:
		print "in!"
		is_end = True
		for w1 in words:
			for w2 in words:
				if w2 == w1:
					 continue
				if words[w1].intersection(words[w2]):
					words[w1] = words[w1].union(words[w2])
					words[w2] = set()
					flag = False
		words = {k:v for k,v in words.items() if v}
	print len(words)
	f = open("set.out", "w")
	for w in words:
		if len(words[w]) < 2:
			continue
		info = w + "\t: "
		for w0 in words[w]:
			info += w0 + " "
		f.write(info.encode("utf8") + "\n")
	f.close()

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

def get_ne(fname, ne_type):
	f = open(fname, "r")
	for line in f.readlines():
		seg = line.strip().split()
		if not seg:
			continue
		ne_list[seg[0]] = ne_idx[ne_type]
	f.close()

def match_rule(sent, i, e, t):
	if t == 0 and sent[i:i+e] in exclude_ne[t]:
		return False
	if t == 1 and sent[i-1:i+e+1] in exclude_ne[t]:
		return False
	test_ne = sent[i-2:i] + ne_char[ne_list_rev[t]] + sent[i+e:i+e+2]
	for w in test_ne:
		if w in num_list:
			test_ne = test_ne.replace(w, "N")
		if w in punct_list:
			test_ne = test_ne.replace(w, "P")
	pre = group_dict.get(test_ne[:2], test_ne[:2])
	suf = group_dict.get(test_ne[3:], test_ne[3:])
	if len(pre) > 1:
		pre = group_dict.get(test_ne[0], test_ne[0]) + group_dict.get(test_ne[1], test_ne[1])
	if len(suf) > 1:
		suf = group_dict.get(test_ne[3], test_ne[3]) + group_dict.get(test_ne[4], test_ne[4])
	test_ne = pre + ne_char[ne_list_rev[t]] + suf
	if debug and t == 1:
		print test_ne
	return rule.match(test_ne)

def rough_match(sent):
	if debug:
		print sent
	ne_map = {}
	prev_inc = [1] * (len(sent))
	new_inc = []
	_sent = sent
	# get ORGs
	# i = 2
	# j = 2
	# # print "ORG begin"
	# while True:
	# 	if i == len(sent)-2:
	# 		break
	# 	step = prev_inc[i]
	# 	prefixes = org_trie.prefixes(_sent[j:-2])
	# 	if prefixes:
	# 		e = len(prefixes[-1])
	# 		ne_map[i] = [e, 2]
	# 		_sent = _sent[:j] + u"\u1113" + _sent[j+e:]
	# 		step += e-1
	# 	i += step
	# 	j += 1
	# 	new_inc.append(step)
	# # get LOCs
	# prev_inc = [1, 1] + new_inc + [1, 1]
	# # new_inc = []
	# i = 2
	# j = 2
	# k = 2
	# print "LOC begin"
	# print _sent
	# print prev_inc
	# while True:
	# 	if i == len(sent)-2:
	# 		break
	# 	step = prev_inc[k]
	# 	prefixes = place_trie.prefixes(_sent[j:-2])
	# 	if prefixes:
	# 		e = len(prefixes[-1])
	# 		# if match_rule(_sent, j, e, 1):
	# 			ne_map[i] = [e, 1]
	# 			_sent = _sent[:j] + u"\u1112" + _sent[j+e:]
	# 			step += e-1
	# 			k += e-1
	# 	k += 1
	# 	i += step
	# 	j += 1
	# 	new_inc.append(step)

	# # get PERs:
	# prev_inc = [1, 1] + new_inc + [1, 1]
	# new_inc = []
	i = 2
	j = 2
	k = 2
	date_list = u"年月日号"
	name_sw = sw_list + u"说摄地会使委市" + u"\u1111\u1112\u1113"
	forbid_name = string.ascii_letters + string.digits + punct_list + name_sw
	# print "PER begin"

	while True:
		# print i, k, j
		if i == len(sent)-2:
			break
		step = prev_inc[k]
		prefixes = person_trie.prefixes(_sent[j:-2])
		if prefixes:
			e = len(prefixes[-1])
			if match_rule(_sent, j, e, 0):
				ne_map[i] = [e, 0]
				_sent = _sent[:j] + u"\u1111" + _sent[j+e:]
				step += e-1
				k += e-1
		# if _sent[j] in surname_list["single"]:
		# 	if _sent[j+1] not in forbid_name:
		# 		if _sent[j+2] not in forbid_name and match_rule(_sent, j, 3, 0):
		# 			ne_map[i] = [3, 0]
		# 			_sent = _sent[:j] + u"\u1111" + _sent[j+3:]
		# 			step += 3-1
		# 			k += 3-1
		# 		elif match_rule(_sent, j, 2, 0):
		# 			ne_map[i] = [2, 0]
		# 			_sent = _sent[:j] + u"\u1111" + _sent[j+2:]
		# 			step += 2-1
		# 			k += 2-1
		k += 1
		j += 1
		i += step
		new_inc.append(step)
	
	# if debug:
	# 	print _sent
	# # get other ORGs
	# prev_inc = [1, 1] + new_inc + [1, 1]
	# new_inc = []
	# i = 2
	# j = 2
	# k = 2
	# # print prev_inc
	# while True:
	# 	if debug:
	# 		print i, k, j
	# 		print _sent[j:-2]
	# 	if i == len(sent)-2:
	# 		break
	# 	step = prev_inc[k]
	# 	m = re.match(org_rule, _sent[j:])
	# 	if m:
	# 		e = 0
	# 		step -= prev_inc[k]
	# 		for c in m.group():
	# 			# print k, e
	# 			if i+e not in ne_map:
	# 				e += 1
	# 			else:
	# 				t = ne_map[i+e][0]
	# 				del ne_map[i+e]
	# 				e += t
	# 		ne_map[i] = [e, 2]
	# 		l = len(m.group())-1
	# 		k += l
	# 		# print sent[i:i+e]
	# 		# k -= 1
	# 		_sent = _sent[:j] + u"\u1113" + _sent[j+l+1:]
	# 		step += e
	# 	k += 1
	# 	i += step
	# 	j += 1
	# 	new_inc.append(step)

	return ne_map

def extract_ne(sent):
	global ne_list, trie
	cur_idx = 0
	new_sent = ''
	if sent[cur_idx] == u"\ufeff":
		sent = sent[1:]
	sent = strQ2B(sent)
	sent = "bb" + sent + "ee"
	ne_map = rough_match(sent)

	pred_list = ["o"] * (len(sent)-4)
	for i, (e, t) in ne_map.items():
		if debug:
			print sent[i:i+e],t
		for idx in range(i, i+e):
			if idx == i:
				pref = "b_"
			elif idx == i+e-1:
				pref = "e_"
			else:
				pref = 'i_'
			pred_list[idx-2] = pref + ne_idx.keys()[t]
	# print pred_list
	return pred_list

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

def read_write(fname, oname, isTest=False):
	f = open(fname, "r")
	out = open(oname, "w")
	cnt = 0
	for line in f.readlines():
		# print cnt
		cnt += 1
		ne_list = []
		sent = ""
		if line.strip() == "":
			continue
		if not isTest:
			for seg in line.strip().decode("utf8").split():
				sList = seg.split("/")
				i = 0
				new_s = strQ2B(sList[0])
				for s in new_s:
					# ne_type = "o"
					if sList[1] == "o":
						ne_type = "o"
					elif i == 0:
						ne_type = "b_"+sList[1]
					elif i == len(new_s)-1:
						ne_type = "e_"+sList[1]
					else:
						ne_type = "i_"+sList[1]
					ne_list.append(ne_type)
					sent += s
					i += 1
			feat_list = compile_features(sent)
			pred_list = extract_ne(sent)
			for i in range(len(ne_list)):
				info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + ne_list[i] + "\t" + pred_list[i]
				out.write(info.encode("utf8") + "\n")
		else:
			sent = line.strip().decode("utf8")
			feat_list = compile_features(sent)
			for i in range(len(ne_list)):
				info = sent[i] + "\t" + "\t".join(feat_list[i]) + "\t" + ne_list[i]
				out.write(info.encode("utf8") + "\n")
		out.write("\n")
	f.close()
	out.close()

def compile_rules():
	global rule, exclude_ne, group_dict, org_rule
	# r = open(rule_file, "r")
	# for line in r.readlines():
	# 	rule_list.append(line.strip().decode("utf8"))
	# r.close()
	group = [
		u"A: 宣布 表示 认为 指出 报道 说到 说道 强调 要求 介绍 告诉 还说 感谢 会见 发言",
		u"B: 代表 秘书 院士 院长 同志 教练 先生 女士 习生 讯员 言人 主任 常委 副委 董事 校长 军官 "\
			u"委员 员长 副部 部长 主席 记者 经理 会长 行长 局长 省长 市长 县长 首相 总裁 总统 总理 "\
			u"大使 事长 导员 选手 所长"\
			u"总书 司机 教授 学生 作者 "\
			u"下士 中士 上士 准尉 少尉 中尉 上尉 大尉 准校 少校 中校 上校 大校 准将 少将 中将 上将 ",
		u"C: 以及 和 还有 与 由 陪同 等 其中 是 同 ",
		u"D: 当年 去年 今年 明年 近日 日前 今日 今天 昨日 昨天 明天 后天 N日 N月 N日 N号",
		u"E: 想起 想到 发现 欢迎 迎接",
		u"F: 包括 了 有 ",
		u"G: 地处 抵达 撤出 离开 逃离 撤回 返回 ", # mostly surfix
		u"H: 在 从 到 驻 来 去 回 向 对 为 于 沿 离 至 到达 前往 回到 到了 来到 ", # only used as prefix
		u"I: 首都 省会 景点 城市 小镇 ",
		u"J: 景区 县城 城区 市区 境内 政府 地区 国家 国际 郊外",
		u"K: 东 西 南 北 上 下 左 右 ",
		u"L: 举行 召开 进行 访问 开幕 互访 交流 举办 宣布 正式 设立 建立 确立 投资 实施 指出 实行 "\
			u"制裁 畅销 提供 入侵 派遣",
		u"X: \u1111",
		u"Y: \u1112",
		u"Z: \u1113"
	]
	for g in group:
		tag = g.strip().split(":")[0]
		for d in g.strip().split(":")[1].split():
			group_dict[d] = group_dict.get(d, "") + tag
	rule_list = []
	# for person
	# rule_list = [u".?Pᄑ[ADB].?",]
	# rule_list += [u"Bᄑ[PACD].?",u"Bᄑ[说摄H].?", u"EᄑB",u".Pᄑ[说摄].?"]
	# rule_list += [u".?了ᄑ的P.?",u".?[C]ᄑ[AB]"]
	# rule_list += [u"XCᄑ..?"]

	rule_list += [u".?Pᄑ[ADB说摄].?",u"BᄑP.?",u"ᄑPᄑP.?",]

	# for location
	# rule_list += [u".?[DHGIP]ᄒ[JKLD].?"]
	# rule_list += [u".?[PCFHG]ᄒ[PACFHGKNJIN]",u"N[位个]ᄒ[人].?",u"PCᄒJ"]
	# rule_list += [u"YCᄒ..?",u"..ᄒ[XYZ].",u".[XYZ]ᄒ.?.?"]
	# rule_list += [u".[PCF]ᄒ..",]
	# rule_list += [u".?[DPGHF]ᄒ.?.?",u".?.?ᄒ[FH].?",u".?.?ᄒ[JKL].?"]
	rule_list += [u".?Pᄒ[JKLDH].?", u".?[GHI]ᄒP.?"]

	org_sw = sw_list + u"对和" + punct_list + num_list
	org_rule = []
	# print u"国际贸易公司" in org_list
	for o in org_list:
		# org_rule.append(u"(ᄒ*[ᄑᄓ])+[^"+org_sw+"]{0,4}"+o)
		org_rule.append(u"([ᄒᄑᄓ])+[^"+org_sw+"]{0,4}"+o)
	org_rule.append(u"ᄒ—ᄒ[^"+org_sw+u"]{0,4}协会") 
	org_rule.append(u"ᄒᄒ[^"+org_sw+u"]{0,4}协会") 
	# org_rule.append(u"[ᄒᄓ]ᄑ?[^"+org_sw+u"]{0,4}ᄓ")
	org_rule.append(u"ᄒᄓ")
	org_rule = "|".join(org_rule)

	exclude_ne[0] += [u"白皮书",u"时强调",u"海协",u"强调",u"相当于",u"双方",u"时指出",u"海协为",u"国务院",\
		u"和夫人",u"贺辞",u"贺词",u"贺信",u"相识",u"文章",u"高兴地",u"应该",u"党中央",u"明确",u"单位",\
		u"曾指出",u"祖国",u"时",u"原来",u"宿舍",u"曾",u"信任",u"严",u"于今年",u"美国",u"常委会",u"保守党",\
		u"文化",u"纪律",u"基本",u"华人",u"谈到"
	]
	exclude_ne[0] += [u""]
	rule = '|'.join(rule_list)
	rule = re.compile(rule)

def test_case():
	global debug
	debug = True	
	test_case = [
		u",习近平昨日会见xxx",
		u"：汇款请寄：湖北省广水市天童新技术开发部（气象局院内）",
		u"，瑞士特联投资集团投资二千万美元与宝日希勒煤矿联合建立六十万千瓦的电站，美国环球集团有限公司与满洲里国际贸易公司联合改组了，",
		u"，为珠江、邯郸、包头三家烟厂",

	]
	for t in test_case:
		extract_ne(t)
		print compile_features(t)

init()

def main():
	compile_rules()
	# read_write("data/train.txt", "data/train_new.out")
	start = time.time()
	read_write("data/testright.txt", "../testright_new.out")
	print time.time() - start
	# test_case()
	# get_stat("data/train.txt")
	# f = open("data/place.txt", "r")
	# o = open("data/temp_pl.txt", "w")
	# for line in f.readlines():
	# 	line = line.strip().decode("utf8")
	# 	for place in place_list:
	# 		if line[-len(place):] == place:
	# 			o.write(line.encode("utf8") + "\n")
	# 			break
	# f.close()
	# o.close()

if __name__ == '__main__':
	main()
