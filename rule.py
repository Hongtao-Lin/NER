#encoding=utf-8
import re, os
import dawg # C++ based Trie-tree implementation
import time
import collections, copy, cPickle, operator, string
from util import read_write, strQ2B, get_ne_type

__dir__ = "./dict/"

nr_file = __dir__ + "person.txt"
nr_save = __dir__ + "person.save"
ns_file = __dir__ + "place2.txt"
ns_save = __dir__ + "place_trie2.save"
nt_file = __dir__ + "org2.txt"
nt_save = __dir__ + "org_trie2.save"
exclude_file = "./pmi_res2.out"
# exclude_file = __dir__ + "exclude_word.txt"
exclude_save = __dir__ + "exclude_word.save"
custom_file = __dir__ + "custom.txt"
custom_save = __dir__ + "custom_trie.save"
surname_file = __dir__ + "surname.txt"
surname_save = __dir__ + "surname.save"
place_file = __dir__ + "place_surf.txt"
place_save = __dir__ + "place_surf.save"
org_file = __dir__ + "org_surf.txt"
org_save = __dir__ + "org_surf.save"

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
date_list = u"年月日号"
forbid_name = string.ascii_letters + string.digits + punct_list + name_sw
ne_idx = {"PER":0, "nr": 0, "LOC":1, "ns": 1, "ORG":2, "nt": 2}
ne_list_rev = ["PER", "LOC", "ORG"]
ne_list_rev2 = ["nr", "ns", "nt"]
ne_char = {"PER": u'\u1111', "LOC": u'\u1112', "ORG": u'\u1113'}
rule_file = "rule.out"
surname_list = {"single": [], "double": []}
punct_pairs = [u"\"\"", u"''", u"()", u"<>", u"“”", u"‘’", u"《》", u"「」"]
place_list = []
org_list = []
exclude_list = []
group_dict = {}

rule = None
org_rule = None
place_trie = None
person_trie = None
custom_trie = None
ne_trie = None
debug = False

read_file1 = "./data/MSRA/train.txt"
read_file2 = "./data/Onto/ne_nw.out"
read_file3 = "./data/MSRA/testright.txt"
# out_file = "./data/MSRA/testright_new.out"
out_file1 = "./testright_new1.out"
out_file2 = "./testright_new21.out"
out_file3 = "./testright_new31.out"

# match the sentence with the compiled rules AND causal rules I wrote directly.
# input: sent; i: start idx; e: end_idx; t: (int) type of NE to match.
# sent[i:e] is the possible NE we find. here we also consider the *context*(-2, +2) of the NE.
# output: bool.
def match_rule(sent, i, e, t):
	# if the possible NE is embedded in a unclosed punct.
	if sent[i-1:i+1] in exclude_list or sent[i+e-1:i+e+1] in exclude_list:
		return False
	if (sent[i-1] in u"\"'“‘<[(《" or sent[i+e] in u"\"'”’>)]》") and sent[i-1]+sent[i+e] not in punct_pairs:
		return False
	if sent[i-1] in u"-—·)》" or sent[i+e] in u"-—·(《":
		return False

	# replace the possible NE/punct/number with a symbol.
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

	# using regex to match it.
	return rule.match(test_ne)

# core function of matching in sentence.
# this function receives a sentence, and extract possible PER, LOC and ORGs within it. 
# returns a dict, the key is start_idx, value is a tuple: (end_idx, ne_type).
# note that the idx refer to the original sentence.  
def rough_match(sent):
	if debug:
		print sent
	ne_map = {}
	prev_inc = [1] * (len(sent))
	new_inc = []
	_sent = sent

	# get NEs from dict.
	i, j, k = 2, 2, 2
	while True:
		if i == len(sent)-2:
			break
		step = prev_inc[k]
		is_custom = True
		t = None
		prefixes = custom_trie.prefixes(_sent[j:-2])
		# match custom list first.
		if prefixes:
			for p in prefixes[::-1]:
				e = len(p)
				t = custom_trie[p]
				if match_rule(_sent, j, e, t):
					ne_map[i] = [e, t]
					_sent = _sent[:j] + ne_char[ne_list_rev[t]] + _sent[j+e:]
					step += e-1
					k += e-1
					break
		# then a default one.
		else:
			prefixes = ne_trie.prefixes(_sent[j:-2])
			if prefixes:
				for p in prefixes[::-1]:
					e = len(p)
					t = ne_trie[p]
					if match_rule(_sent, j, e, t):
						ne_map[i] = [e, t]
						_sent = _sent[:j] + ne_char[ne_list_rev[t]] + _sent[j+e:]
						step += e-1
						k += e-1
						break
		j += 1
		i += step
		k += 1
		new_inc.append(step)
	
	if debug:
		print _sent
	# get other ORGs: from possible integration.
	prev_inc = [1, 1] + new_inc + [1, 1]
	new_inc = []
	i, j, k = 2, 2, 2
	# print prev_inc
	while True:
		if debug:
			print i, k, j
			print _sent[j:-2]
		if i == len(sent)-2:
			break
		step = prev_inc[k]
		m = re.match(org_rule, _sent[j:])
		if m:
			if debug:
				print m.group()
			e = 0
			step -= prev_inc[k]
			for c in m.group():
				# print k, e
				if i+e not in ne_map:
					e += 1
				else:
					t = ne_map[i+e][0]
					del ne_map[i+e]
					e += t
			# ne_map[i] = [e, 2]
			l = len(m.group())-1
			k += l
			# print sent[i:i+e]
			# k -= 1
			_sent = _sent[:j] + u"\u1113" + _sent[j+l+1:]
			step += e
		k += 1
		i += step
		j += 1
		new_inc.append(step)

	return ne_map

# input: original sentence. 
# output: 
# if convert=False: return a list of denotation. 
# (eg: "I am Hunter" -> ["o", "o", "o", "b_ns", "i_ns", ..., "e_ns"])
# if convert=True: return a new sentence (symbolize) and the ne_map.
# (eg: "I am Hunter" -> "I am \u1111", {5: (11, 0)} (5: "H", 11： "r", 0: type of PER.)
def extract_ne(_sent, convert=False):
	global ne_list, trie
	cur_idx = 0
	if _sent[cur_idx] == u"\ufeff":
		_sent = _sent[1:]
	_sent = "bb" + _sent + "ee"
	sent = _sent.lower()
	ne_map = rough_match(sent)
	# print sent
	for i, (e,t) in ne_map.items():
		print sent[i:i+e], t

	if not convert:
		pred_list = ["o"] * (len(sent)-4)
		for i, (e, t) in ne_map.items():
			ne_type = ne_list_rev2[t]
			l = i+e-1
			for j in range(i,i+e):
				pred_list[j-2] = get_ne_type(j, l, ne_type)
		# print pred_list
		return pred_list
	else:
		new_sent = ''
		new_map = {}
		_i = 2
		for i, (e, t) in sorted(ne_map.items()):
			if debug:
				print _sent[i:i+e],t
			new_sent += _sent[_i:i] + ne_char[ne_list_rev[t]]
			_i = i+e
			new_map[len(new_sent)-1] = sent[i:_i].encode("utf8")
		new_sent += _sent[_i:-2]

		# for i in new_map:
		# 	print i, new_map[i]
		return new_sent, new_map

def load_ne_from_file(fname, sname, tag):
	if os.path.exists(sname):
		temp_trie = cPickle.load(open(sname, "r"))
	else:
		temp_ne = get_ne(fname, tag)
		temp_trie = dawg.IntDAWG(zip(temp_ne.keys(), temp_ne.values()))
		cPickle.dump(temp_trie, open(sname, "w"))
	return temp_trie

def load_list_from_file(fname, sname):
	if os.path.exists(sname):
		temp_list = cPickle.load(open(sname, "r"))
	else:
		temp_list = []
		f = open(fname, "r")
		for line in f.readlines():
			seg = line.strip().decode("utf8").split()
			if not seg:
				continue
			temp_list.append(seg[0])
		f.close()
		cPickle.dump(temp_list, open(sname, "w"))
	return temp_list

# just a utility function for loading NEs.
def get_ne(fname, ne_type, ne_list = None):
	if ne_list == None:
		ne_list = {}
	f = open(fname, "r")
	for line in f.readlines():
		seg = line.strip().split()
		if not seg:
			continue
		if ne_type not in ne_idx:
			ne_list[seg[0]] = int(seg[-1])
		else:
			ne_list[seg[0]] = ne_idx[ne_type]
	f.close()
	return ne_list

def init():
	global surname_list, place_list, org_list, exclude_list
	global place_trie, org_trie, person_trie, custom_trie, ne_trie

	person_trie = load_ne_from_file(nr_file, nr_save, "PER")
	place_trie = load_ne_from_file(ns_file, ns_save, "LOC")
	org_trie = load_ne_from_file(nt_file, nt_save, "ORG")
	custom_trie = load_ne_from_file(custom_file, custom_save, "ALL")

	ne_list = {}
	get_ne(nr_file, "PER", ne_list)
	get_ne(ns_file, "LOC", ne_list)
	get_ne(nt_file, "ORG", ne_list)
	ne_trie = dawg.IntDAWG(zip(ne_list.keys(), ne_list.values()))
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

	place_list = load_list_from_file(place_file, place_save)
	org_list = load_list_from_file(org_file, org_save)
	exclude_list = load_list_from_file(exclude_file, exclude_save)

# Here hides the mysteries of rules I find (with little theoratical groundings...)
# Also, it compiles the rules for integrating a larger ORG.
def compile_rules():
	global rule, group_dict, org_rule
	# list of groups with similar words in their meaning/functionality.
	# Note that currently I do not allow *DUPLICATED* words in groups, which I know is quite buggy..
	group = [
		# A: inform/announce/say
		u"A:  宣布 表示 认为 指出 报道 说到 说道 强调 要求 介绍 告诉 还说 感谢 会见 发言 "\
			u"举行 召开 进行 访问 开幕 互访 交流 举办 正式 设立 建立 确立 投资 实施 实行 ",
		# B: person titles
		u"B:  代表 秘书 院士 院长 同志 教练 先生 女士 习生 讯员 言人 主任 常委 副委 董事 校长 军官 "\
		    u"委员 员长 副部 部长 主席 记者 经理 会长 行长 局长 省长 市长 县长 首相 总裁 总统 总理 "\
			u"大使 事长 导员 选手 所长 总书 司机 教授 学生 作者 "\
			u"下士 中士 上士 准尉 少尉 中尉 上尉 大尉 准校 少校 中校 上校 大校 准将 少将 中将 上将 ",
		# C: connectives
		u"C:  以及 和 还有 与 由 陪同 等 其中 是 同 ",
		# D: time-related
		u"D:  当年 去年 今年 明年 近日 日前 今日 今天 昨日 昨天 明天 后天 N日 N月 N日 N号",
		# E: used as pre-words in person
		u"E:  想起 想到 发现 欢迎 迎接",
		# F: ..
		u"F:  说 摄",
		# G: indicating places, mostly surfix
		u"G:  地处 抵达 撤出 离开 逃离 撤回 返回 ", 
		# H: indicating places, only used as prefix
		u"H:  在 从 到 驻 来 去 回 向 对 为 于 沿 离 至 到达 前往 回到 到了 来到 ", 
		# I: title of places
		u"I:  首都 省会 景点 城市 小镇 ",
		u"J:  景区 县城 城区 市区 区域 境内 政府 地区 国家 国际 郊外",
		u"K:  东 西 南 北 上 下 左 右 ",
		u"L:  制裁 畅销 提供 入侵 派遣"
		# u"X: \u1111",
		# u"Y: \u1112",
		# u"Z: \u1113"
	]
	for g in group:
		tag = g.strip().split(":")[0]
		for d in g.strip().split(":")[1].split():
			group_dict[d] = group_dict.get(d, "") + tag
	rule_list = []
	# for person
	rule_list = [u".Pᄑ[ADBHF].?",]
	rule_list += [u"Bᄑ[ACDFH].?",u"EᄑB",u"[BD]ᄑP.",]
	rule_list += [u".了ᄑ的P.?",u".?[C]ᄑ[AB]"]
	rule_list += [u"ᄑCᄑ..?"]
	rule_list += [u".?.ᄑ..?"]

	# for location
	# rule_list += [u".?[DHGIP]ᄒ[JKLD].?"]
	# rule_list += [u".?[PCFHG]ᄒ[PACFHGKNJIN]",u"N[位个]ᄒ[人].?",u"PCᄒJ"]
	# rule_list += [u"YCᄒ..?",u"..ᄒ[XYZ].",u".[XYZ]ᄒ.?.?"]
	# rule_list += [u".[PCF]ᄒ..",]
	# rule_list += [u".?[DPGHF]ᄒ.?.?",u".?.?ᄒ[FH].?",u".?.?ᄒ[JKL].?"]
	rule_list += [u".Pᄒ[JBKADH]", u"[AGHI]ᄒP", u"Pᄒᄒ..",u".?.ᄒ..?"]
	
	# rule_list += [u"PPᄓ", u"ᄓPP"]
	rule_list += [u"..ᄓ.."]

	org_rule = []

	# rules in org_list must have a subpart to match!
	for o in org_list:
		# org_rule.append(u"(ᄒ*[ᄑᄓ])+[^"+org_sw+"]{0,4}"+o)
		org_rule.append(u"[ᄒᄑᄓ]+[^"+org_sw+"]{0,4}"+o)
	# org_rule.append(u"ᄒ+([^"+sw_list+u"]){0,4}出版社") 
	# org_rule.append(u"ᄒ+[^"+sw_list+u"]{0,4}出版社") 
	# org_rule.append(u"ᄒᄒ([^"+org_sw+u"]){0,4}协会") 
	# org_rule.append(u"[ᄒᄓ]ᄑ?[^"+org_sw+u"]{0,4}ᄓ")
	org_rule.append(u"[ᄒᄑᄓ]+[^"+org_sw+u"]{0,2}ᄓ")
	org_rule = "|".join(org_rule)
	rule = '|'.join(rule_list)
	rule = re.compile(rule)

def clean_org_dict():
	o1 = open("./dict/org_tmp1.txt", "r")
	o2 = open("./dict/org_tmp2.txt", "r")
	o3 = open("./dict/org_tmp3.txt", "w")
	f = open("./dict/org.txt", "r")
	d = []
	for line in o1.readlines():
		d.append(line.strip().decode("utf8"))
	for line in o2.readlines():
		d.append(line.strip().decode("utf8"))
	for line in f.readlines():
		seg = line.decode("utf8").split()
		if seg[0] in d:
			o3.write(line)
		# if len(seg[0]) <= 5 and seg[0][-2:] != u"政府":
		# 	o1.write(seg[0].encode("utf8") + "\n")
		# else:
		# 	o2.write(seg[0].encode("utf8") + "\n")

	f.close()
	o1.close()
	o2.close()
	o3.close()

def get_all_org_surf(fname):
	f = open(fname, "r")
	o = open("test_suf.out", "w")
	d = {}
	for line in f.readlines():
		segList = line.decode("utf8").split()
		for s in segList:
			if s[-3:] != "/nt":
				continue
			org = s.split("/")[0]
			if len(org) > 6:
				d[org[-6:]] = d.get(org[-6:], 0) + 1
			if len(org) > 5:
				d[org[-5:]] = d.get(org[-5:], 0) + 1
			if len(org) > 4:
				d[org[-4:]] = d.get(org[-4:], 0) + 1
			if len(org) > 3:
				d[org[-3:]] = d.get(org[-3:], 0) + 1
	for k, v in sorted(d.items(), key=operator.itemgetter(1), reverse=True):
		if v < 3:
			continue
		o.write(k.encode("utf8") + "\t" + str(v) + "\n")
	o.close()
	f.close()

def get_all_org_kw(fname):
	f = open(fname, "r")
	o = open("test_kw.out", "w")
	d = {}
	for line in f.readlines():
		s = line.decode("utf8").split()
		if not s:
			continue
		s = s[0]
		for i in [7, 6, 5, 4, 3]:
			if s[-i:] in org_list:
				d[s[-i-2:-i]] = d.get(s[-i-2:-i], 0) + 1
				d[s[-i-3:-i-1]] = d.get(s[-i-3:-i-1], 0) + 1
	for k, v in sorted(d.items(), key=operator.itemgetter(1), reverse=True):
		if v < 3:
			continue
		o.write(k.encode("utf8") + "\t" + str(v) + "\n")
	o.close()
	f.close()

# following three are utility functions to clean words in dicts.
def clean_org_surf(fname):
	f = open(fname, "r")
	o = open("test_suf2.out", "w")
	d = {}
	for line in f.readlines():
		sList = line.decode("utf8").split()
		if not sList:
			continue
		d[sList[0]] = len(sList[0])
	for k, v in sorted(d.items(), key=operator.itemgetter(1), reverse=True):
		o.write(k.encode("utf8") + "\n")
	o.close()
	f.close()

def clean_org_kw(fname):
	f = open(fname, "r")
	o = open("test_kw2.out", "w")
	d = {}
	for line in f.readlines():
		sList = line.decode("utf8").split()
		if not sList:
			continue
		d[sList[0]] = len(sList[0])
	for k, v in sorted(d.items(), key=operator.itemgetter(1), reverse=True):
		o.write(k.encode("utf8") + "\n")
	o.close()
	f.close()

def clean_org(fname):
	f = open(fname, "r")
	o = open("test_org1.out", "w")
	o2 = open("test_org2.out", "w")
	d = []

	for line in open("./dict/place2.txt", "r"):
		sList = line.strip().decode("utf8").split()
		if not sList:
			continue
		if len(sList[0]) <= 3:
			d.append(sList[0])
	d = u"军队 ".split()
	# for line in f.readlines():
	# 	sList = line.decode("utf8").split()
	# 	if not sList:
	# 		break
	# 	o.write(line)
		# if len(sList[0]) <= 3:
			# d.append(sList[0])
	f.close()
	f = open(fname, "r")
	for line in f.readlines():
		sList = line.decode("utf8").split()
		if not sList:
			continue
		# if sList[0][-2:] not in exclude_list and sList[0][-3:-1] not in exclude_list:
		if (sList[0][-2:] not in d and sList[0][-1:] not in d):
			o.write(line.lower())
		else:
			a = 1
			# o2.write(line.lower())
	o.close()
	o2.close()
	f.close()

init()
compile_rules()

# write your test cases here to see results and debug info.
def test_case():
	global debug
	debug = True	
	test_case = [
		u"北京25中学校长",

	]
	for t in test_case:
		t = strQ2B(t)
		extract_ne(t)

def main():
	# read_write(read_file1, out_file1, extract_ne=extract_ne)
	read_write(read_file2, out_file2, extract_ne=extract_ne)
	read_write(read_file3, out_file3, extract_ne=extract_ne)
	# test_case()
	# get_all_org_kw("./dict/org.txt")
	# clean_org("./dict/org2.txt")

if __name__ == '__main__':
	main()
