
taggedFile = "data/MSRA/trainFormatBIE.txt"
resultFileV = "sohuv1.txt"
outputFile = "hcTrainData.txt"

confidenceThreshold = 0.975

with open(outputFile,"w") as fw:
    with open(resultFileV,"r") as fr:
        highConfidence = True
        for line in fr.xreadlines():
            if line[0]=="#":
                if float(line.split()[-1]) >= confidenceThreshold:
                    highConfidence = True
                else:
                    highConfidence = False
            else:
                if highConfidence:
		    if line!="\n":
			[char,tag] = line.split()
			tag = tag[0:tag.find('/')].replace('_','-').replace('o','0').upper()
                    	fw.write(char + "\t" + tag + "\n")
		    else:
			fw.write("\n")
    with open(taggedFile,"r") as fr:
	for line in fr.xreadlines():
	    fw.write(line)


