import os
import re
try:
    import ujson as json  
except:
    import json
from dateutil import parser as dateparser

from operator import itemgetter
from xml.etree import cElementTree as etree
from collections import defaultdict


filename = "posts.xml"
filename_filtered = "filtered.tsv"

q_creation = {}  
q_accepted = {}  

meta = defaultdict(list)

code_match = re.compile('<pre>(.*?)</pre>', re.MULTILINE | re.DOTALL)
link_match = re.compile(
    '<a href="http://.*?".*?>(.*?)</a>', re.MULTILINE | re.DOTALL)
img_match = re.compile('<img(.*?)/>', re.MULTILINE | re.DOTALL)
tag_match = re.compile('<[^>]*>', re.MULTILINE | re.DOTALL)


def filter_html(s):
    num_code_lines = 0
    link_count_in_code = 0
    code_free_s = s

    num_images = len(img_match.findall(s))

    for match_str in code_match.findall(s):
        num_code_lines += match_str.count('\n')
        code_free_s = code_match.sub("", code_free_s)
        link_count_in_code += len(link_match.findall(match_str))

    anchors = link_match.findall(s)
    link_count = len(anchors)

    link_count -= link_count_in_code

    html_free_s = re.sub(
        " +", " ", tag_match.sub('', code_free_s)).replace("\n", "")

    link_free_s = html_free_s
    for anchor in anchors:
        if anchor.lower().startswith("http://"):
            link_free_s = link_free_s.replace(anchor, '')

    num_text_tokens = html_free_s.count(" ")

    return link_free_s, num_text_tokens, num_code_lines, link_count, num_images

years = defaultdict(int)
num_questions = 0
num_answers = 0

def parsexml(filename):
    global num_questions, num_answers

    counter = 0

    it = map(itemgetter(1),
             iter(etree.iterparse(filename, events=('start',))))
    root = next(it) 

    for elem in it:
        if counter % 100000 == 0:
            print(counter)

        counter += 1

        if elem.tag == 'row':
            creation_date = dateparser.parse(elem.get('CreationDate'))
            Id = int(elem.get('Id'))
            PostTypeId = int(elem.get('PostTypeId'))
            Score = int(elem.get('Score'))

            if PostTypeId == 1:
                num_questions += 1
                years[creation_date.year] += 1
                ParentId = -1
                TimeToAnswer = 0
                q_creation[Id] = creation_date
                accepted = elem.get('AcceptedAnswerId')
                if accepted:
                    q_accepted[Id] = int(accepted)
                IsAccepted = 0

            elif PostTypeId == 2:
                num_answers += 1
                ParentId = int(elem.get('ParentId'))
                if not ParentId in q_creation:
                    continue
                TimeToAnswer = (creation_date - q_creation[ParentId]).seconds
                if ParentId in q_accepted:
                    IsAccepted = int(q_accepted[ParentId] == Id)
                else:
                    IsAccepted = 0
                meta[ParentId].append((Id, IsAccepted, TimeToAnswer, Score))
            else:
                continue

            Text, NumTextTokens, NumCodeLines, LinkCount, NumImages = filter_html(
                elem.get('Body'))

            values = (Id, ParentId,
                      IsAccepted,
                      TimeToAnswer, Score,
                      Text,
                      NumTextTokens, NumCodeLines, LinkCount, NumImages)

            yield values
            
            root.clear() 

with open(filename_filtered, "w") as f:
    for item in parsexml(filename):
        line = "\t".join(map(str, item))
        f.write(line+ "\n")

with open("filtered-meta.json", "w") as f:
    json.dump(meta, f)

print("years:", years)
print("#qestions: %i" % num_questions)
print("#answers: %i" % num_answers)
