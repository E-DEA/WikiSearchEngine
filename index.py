#!usr/bin/env python2

import os
import sys
import re
import Stemmer
import random

from StringIO import StringIO
from string import digits
from nltk.tokenize import TweetTokenizer
from nltk.corpus import stopwords
from xml.sax import make_parser
from xml.sax.handler import ContentHandler, feature_namespaces
from heapq import heappush, heappop

STOP_WORDS = set(stopwords.words('english'))
SYMBOLS = ["(", ")", "[", "]",".", "-", "_", "#", "!", "$", ">", "<", '"', "%", "@", "=", '\\', "&", "*", "+", "|", "'", ",", ";" "/", "?"]

WIKI_DICT = {}
DOC_DICT = {}

MAX_PAGES = 12000
MAX_LINES = 400000
FILE_CTR = 0

class WikiHandler(ContentHandler):
	def __init__(self):
		self.inTitle = False
		self.inId = False
		self.inRevision = False
		self.inText = False

		self.data ={"ID":StringIO(),
		"Title":StringIO(),
		"Text":StringIO()}

	def startElement(self, name, attributes):
		if name == "title":
			self.inTitle = True
		elif name == "revision":
			self.inRevision = True
		elif name == "id" and self.inRevision == False:
			self.inId = True
		elif name == "text":
			self.inText = True

	def characters(self, content):
		if self.inTitle:
			self.data["Title"].write(content)
		elif self.inId:
			self.data["ID"].write(content)
		elif self.inText:
			self.data["Text"].write(content)

	def endElement(self, name):
		if name == "title" and self.inTitle:
			self.inTitle = False
		elif name == "revision" and self.inRevision:
			wiki_page = (WikiPage(self.data["ID"].getvalue(), self.data["Title"].getvalue(), self.data["Text"].getvalue()))
			wiki_page.process_page()
			del wiki_page
			
			self.inRevision = False

			self.data["Text"].close()
			self.data["ID"].close()
			self.data["Title"].close()

			self.data["Text"] = StringIO();
			self.data["ID"] = StringIO();
			self.data["Title"] = StringIO();

		elif name == "id" and not self.inRevision and self.inId:
			self.inId = False
		elif name == "text" and self.inText:
			self.inText = False


class WikiPage(object):
	__numPages = 0
	__slots__ = ['id', 'title', 'body', 'info', 'categs', 'links', 'refs', 'tokens']

	def __init__(self, ID, Title, Text):
		self.id = ID.encode('utf-8')
		self.title = Title.encode('utf-8')
		self.body = Text
		self.info = ""
		self.categs = ""
		self.links = ""
		self.refs = ""

		self.tokens = []
		self.__class__.__numPages += 1

		if self.__class__.__numPages > MAX_PAGES:
			write_to_indexfile()
			self.__class__.__numPages = 0

	def __preProcess(self, data):
		data = data.replace("\n", " \n ")
		
		data = data.encode('utf-8').translate(None, digits)

		data = re.sub(r"http\S+", " ", data)

		data = self.__removeSymbols(data)

		ref_tokens = data.split("References")

		del data

		try:
			self.info = re.findall("{{Infobox(.*?)}}", ref_tokens[0], flags=re.DOTALL)[0]
		except IndexError:
			pass

		self.body = ref_tokens[0]

		try:
			token = ref_tokens[1]

			ref_tokens = token.split("External links")
			self.refs = ref_tokens[0]

			link_tokens = ref_tokens[1]
			ref_tokens = link_tokens.split("Category:")

			self.links = ref_tokens[0]

			for tkn in ref_tokens[1:]:
				self.categs += tkn + " "
			
			del ref_tokens

		except IndexError:
			pass

	def __tknize(self, data):
		tkzr = TweetTokenizer(preserve_case=False)
		self.tokens = tkzr.tokenize(data)

	def __checkSword(self, word):
		global STOP_WORDS

		if word.lower() in STOP_WORDS or word.isalpha() == False:
			return True
		else:
			return False

	def __stemToken(self, word):
		stemmer = Stemmer.Stemmer("english")
		return stemmer.stemWord(word.lower())
		
	def __removeSymbols(self, text):	
		for symbol in SYMBOLS:
			if symbol in text:
				text = text.replace(symbol, " ")

		return text

	def process_page(self):
		for attr in self.__slots__:
			if(attr!="id" and attr!="tokens"):
				data = getattr(self, attr)
				if attr == "body":
					self.__preProcess(data)
					data = self.body
				elif attr == "title":
					if self.id not in DOC_DICT:
						DOC_DICT.update({self.id:self.title})
					else:
						pass

				self.__tknize(data)
				del data

				for idx, token in enumerate(self.tokens):
					if self.__checkSword(token):
						del token
						continue
					token = self.__stemToken(token)

					if token not in WIKI_DICT:
						WIKI_DICT.update({token:{self.id:[0,0,0,0,0,0]}})
					else:
						if self.id not in WIKI_DICT[token]:
							WIKI_DICT[token].update({self.id:[0,0,0,0,0,0]})
						else:
							pass
					if attr == "title":
						WIKI_DICT[token][self.id][0] += 1
					elif attr == "body":
						WIKI_DICT[token][self.id][1] += 1
					elif attr == "info":
						WIKI_DICT[token][self.id][2] += 1
					elif attr == "categs":
						WIKI_DICT[token][self.id][3] += 1
					elif attr == "links":
						WIKI_DICT[token][self.id][4] += 1
					elif attr == "refs":
						WIKI_DICT[token][self.id][5] += 1
			elif attr == "tokens":
				del self.tokens

def update_stopwords():
	global STOP_WORDS

	with open("./Data/stopwords.txt", "r") as f:
		words = f.readlines()

		for word in words:
			word = word.strip()
			if word not in STOP_WORDS:
				STOP_WORDS.add(word)

			del word
		del words

def write_to_indexfile(indexfile="./WikiIndex/tempindex"):
	global FILE_CTR, WIKI_DICT

	words = WIKI_DICT.keys()
	words.sort()

	with open(indexfile + "_" + str(FILE_CTR) + ".txt", "w") as f:
		for token in words:
			f.write(token.encode("utf-8"))
			docs = WIKI_DICT[token].keys()
			docs.sort()
			for doc in docs:
				f.write("|{}".format(str(doc)))
				for val in WIKI_DICT[token][doc]:
					if val>0:
						f.write("-{}".format(str(val)))
					else:
						f.write("-" + "")

			f.write("\n")
			del docs
			WIKI_DICT[token].clear()
		del words
		FILE_CTR += 1
		WIKI_DICT.clear()

def merge_indexfiles(folder="./WikiIndex/"):
	global FILE_CTR, MAX_LINES

	FILE_CTR = 0
	lines = 0

	index_files = os.listdir(folder)
	for j, filex in enumerate(index_files):
		index_files[j] = folder+filex

	open_files = []
	index_heap = []
	[open_files.append(open(idx_file, "r")) for idx_file in index_files]

	for fp in open_files:
		line = fp.readline()
		word = line.split("|")[0]
		line = "|".join(line.split("|")[1:])
		heappush(index_heap, (word, line, fp))

	filename = folder + output_file.split(".")[0] + str(FILE_CTR) + ".txt"

	f = open(filename, "w")
	fp = open("./secondary_index.txt", "w")
	previous = ""

	while index_heap:
		smallest = heappop(index_heap)
		word = smallest[0]
		line = smallest[1]
		if(word==previous):
			f.write("|" + line.rstrip("\n"))
		else:
			if(lines>0):
				f.write("\n")
			lines += 1

			if lines > MAX_LINES:
				fp.write(previous+":"+filename+"\n")
				f.close()
				
				FILE_CTR += 1
				lines = 1

				filename = folder + output_file.split(".")[0] + str(FILE_CTR) + ".txt"
				f = open(filename, "w")

			f.write(word+"|"+line.rstrip("\n"))
		
		del previous
		previous = word

		nextline = smallest[2].readline()
		if len(nextline)>0:
			word = nextline.split("|")[0]
			nextline = "|".join(nextline.split("|")[1:])
			heappush(index_heap, (word, nextline, smallest[2]))

		del nextline
		del word
		del line
		del smallest

	f.write("\n")
	fp.write(previous+":"+filename+"\n")

	f.close()
	fp.close()
	[fp.close() for fp in open_files]
	[os.remove(idx_file) for idx_file in index_files]


def write_to_docfile(docfile="./docmapping.txt"):
	global DOC_DICT

	with open(docfile, "w") as f:
		doc_ids = DOC_DICT.keys()
		doc_ids.sort(key=int)
		for doc_id in doc_ids:
			f.write("{}:{}\n".format(doc_id, DOC_DICT[str(doc_id)]))

	del doc_ids
	DOC_DICT.clear()

def main():
	#Store program name, and arguments as global variables.
	global prog_name, args, num_args, output_file

	prog_name = sys.argv[0]
	args = sys.argv[1:]
	num_args = len(args)

	source_file = args[0]
	output_file = args[1]

	parser = make_parser()
	parser.setFeature(feature_namespaces, 0)

	update_stopwords()

	handler = WikiHandler()
	parser.setContentHandler(handler)

	parser.parse(source_file)

	write_to_indexfile()
	merge_indexfiles()
	write_to_docfile()

if __name__ == "__main__":
	main()
