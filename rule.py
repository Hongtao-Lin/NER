#encoding=utf-8
import re, os
import dawg # C++ based Trie-tree implementation
import time
import collections, copy, cPickle, operator, string

__dir__ = "./dict/"

nr_file = __dir__ + "person.txt"
nr_save = __dir__ + "person.save"
ns_file = __dir__ + "place.txt"
ns_save = __dir__ + "place_trie.save"
nt_file = __dir__ + "org.txt"
nt_save = __dir__ + "org_trie.save"
surname_file = __dir__ + "surname.txt"
surname_save = __dir__ + "surname.save"
place_file = __dir__ + "place_surf.txt"
place_save = __dir__ + "place_surf.save"
org_file = __dir__ + "org_surf.txt"
org_save = __dir__ + "org_surf.save"

num_list = string.digits + u"一二三四五六七八九十两零几多"
punct_list = string.punctuation + "be" + u"。”‘’“、—"
sw_list = u"些仅不个乎也了仍们你我他她但借假像再在几别既即却又另只的"\
	u"叫各吓吗嘛否吧吱呀呃哦呗呢呵呜呸咋咦咧咱咳哇哈哎哒哟哦噢哪哼唉啥啦啪"\
	u"喂喏喔喽嗡嗬嗯嗳嘎嘘嘻嘿里是还到"\
	u"它就很得怎么打把某死每没而虽被谁说贼这俄"
name_sw = sw_list + u"说摄地会使委市" + u"\u1111\u1112\u1113"
date_list = u"年月日号"
forbid_name = string.ascii_letters + string.digits + punct_list + name_sw
ne_idx = {"PER":0, "LOC":1, "ORG":2}
ne_list_rev = ["PER", "LOC", "ORG"]
ne_char = {"PER": u'\u1111', "LOC": u'\u1112', "ORG": u'\u1113'}
rule_file = "rule.out"
surname_list = {"single": [], "double": []}
place_list = []
org_list = []
exclude_ne = [[], [], []]
group_dict = {}

rule = None
org_rule = None
place_trie = None
org_trie = None
person_trie = None
custom_trie = None
debug = False

def get_ne(fname, ne_type):
	ne_list = {}
	f = open(fname, "r")
	for line in f.readlines():
		seg = line.strip().split()
		if not seg:
			continue
		ne_list[seg[0]] = ne_idx[ne_type]
	f.close()
	return ne_list

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
	if sent[cur_idx] == u"\ufeff":
		sent = sent[1:]
	sent = "bb" + sent + "ee"
	ne_map = rough_match(sent)
	# print sent
	# for i in ne_map:
	# 	print i
	
	new_sent = ''
	new_map = {}
	_i = 2
	pred_list = ["o"] * (len(sent)-4)
	for i, (e, t) in sorted(ne_map.items()):
		if debug:
			print sent[i:i+e],t
		new_sent += sent[_i:i] + ne_char[ne_list_rev[t]]
		_i = i+e
		new_map[len(new_sent)-1] = sent[i:_i].encode("utf8")
	new_sent += sent[_i:]
	new_sent = new_sent[:-2]

	# for i in new_map:
	# 	print i, new_map[i]
	return new_sent, new_map

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

def add_dict(dic):
	global custom_trie
	custom_list = {}
	for k in dic:
		for v in dic[k]:
			custom_list[v] = ne_idx[k]
	custom_list[u"12"] = 0
	custom_list[u"中国"] = 1
	custom_trie = dawg.IntDAWG(zip(custom_list.keys(), custom_list.values()))
	return True

def test_case():
	global debug
	debug = True	
	test_case = [
		u",想趁假期跟我去中国玩玩儿",

	]
	for t in test_case:
		extract_ne(t)

def load_ne_from_file(fname, sname, tag):
	if os.path.exists(sname):
		temp_trie = cPickle.load(open(sname, "r"))
	else:
		temp_ne = get_ne(fname, tag)
		temp_trie = dawg.IntDAWG(zip(temp_ne.keys(), temp_ne.values()))
		cPickle.dump(temp_trie, open(sname, "w"))
	return temp_trie

def load_suf_from_file(fname, sname):
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
	global surname_list, place_list, org_list, place_trie, org_trie, person_trie

	person_trie = load_ne_from_file(nr_file, nr_save, "PER")
	place_trie = load_ne_from_file(ns_file, ns_save, "LOC")
	org_trie = load_ne_from_file(nt_file, ns_save, "ORG")

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
compile_rules()
add_dict({})

def main():
	# read_write("data/testright.txt", "../testright_new.out")
	test_case()

if __name__ == '__main__':
	main()
