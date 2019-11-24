#!usr/bin/env python2

import os
import sys
import re
import Stemmer
import linecache
import time
import math

from itertools import (takewhile,repeat)
from bisect import bisect_left
from string import digits
from nltk.tokenize import TweetTokenizer
from nltk.corpus import stopwords

#TOTAL_DOCS = 5311
TOTAL_DOCS = 17640866

FIELDS = ["t", "b", "i", "c", "l", "r"]
DOC_DICT = {}
STOP_WORDS = set(stopwords.words('english'))
SYMBOLS = ["{", "}", "(", ")", "[", "]",".", "-", "_", "#", "!", "$", ">", "<", '"', "%", "@", "=", "\\", "&", "*", "+", "|"]

def Bsearch(token, filename, flag=False):
	left = 0
	if flag:
		right = TOTAL_DOCS
	else:
		right = 400000

	while(right >= left):
		mid = left + (right - left)/2

		line = linecache.getline(filename, mid).strip("\n")
		
		if not line:
			print filename
			os.system("wc -l " + filename + " > temp.txt")
			with open("temp.txt", "r") as f:
				right = int(f.readline().split()[0])
			os.system("rm temp.txt")
			continue
			
		if flag:
			word = int(line.split(":")[0])
		else:
			word = line.split("|")[0].decode('utf-8')

		if word == token:
			return mid
		elif word > token:
			right = mid-1
			del word
			del line
		else:
			left = mid+1
			del word
			del line
	
	return -1

def update_stopwords():
	global STOP_WORDS

	with open("../Data/stopwords.txt", "r") as f:
		for word in f:
			word = word.strip()
			if word not in STOP_WORDS:
				STOP_WORDS.add(word)

class WikiQuery(object):
	
	__slots__ = ["text", "terms", "spcl", "results"]
	
	def __init__(self, query):
		self.text = query
		self.terms = []
		self.spcl = False
		self.results = {}

	def __checkFormat(self):
		spcl_format = re.compile("[tbirlc]:.+")
		if re.search(spcl_format, self.text):
			self.spcl = True
		else:
			self.spcl = False

	def __checkSword(self, word):
		global STOP_WORDS

		if word.lower() in STOP_WORDS:
			return True
		else:
			return False

	def __stemToken(self, word):
		stemmer = Stemmer.Stemmer("english")
		return stemmer.stemWord(word)

	def __removeSymbols(self, text):
		for symbol in SYMBOLS:
			if symbol in text:
				text = text.replace(symbol, " ")

		return text


	def __tknize(self, data):
		tkzr = TweetTokenizer(preserve_case=False)
		self.terms = tkzr.tokenize(data)

	def __searchFiles(self, token, sec_index = "./secondary_index.txt"):
		f = open(sec_index, "r")
		line = f.readline().strip()

		while(line):
			if(token > line.split(":")[0].decode('utf-8')):
				line = f.readline().strip()
			else:
				break

		return line.split(":")[1]

	def __getDocuments(self, token, idx_file, field=""):
		
		#idx = Bsearch(token, idx_file)
		
		with open(idx_file, "r") as f:
			for line in f:
				word = line.split("|")[0].decode('utf-8')
				if word == token:
					idx = 1
					line = line.strip()
					break
		
		if idx > 0:
			#line = linecache.getline(idx_file, idx).strip("\n")
			if field == "": 
				documents = line.split("|")[1:]
			else:
				field_id = FIELDS.index(field)
				tempdocuments = line.split("|")[1:]
				documents = []

				for i, doc in enumerate(tempdocuments):
					fieldvals = doc.split("-")[1:]
					if(fieldvals[field_id]!=''):
						documents.append(doc)
					else:
						del doc
				del tempdocuments
		else:
				documents = []
		
		return documents

	def __calculateScores(self, docs):
		numdocs = len(docs)
		if numdocs:
			idf = math.log10(float(TOTAL_DOCS)/numdocs)
			for doc in docs:
				docid = doc.split("-")[0]
				freqs = doc.split("-")[1:]
				total_freq = 0

				for freq in freqs:
					if freq == '':
						freq = 0
					total_freq += int(freq)

				tf = 1.0 + math.log10(float(total_freq))

				tfidf = tf*idf

				if docid not in self.results:
					self.results[docid] = tfidf
				else:
					self.results[docid] += tfidf
			del docs

	def process_query(self):
		start_time = time.time()

		self.__checkFormat()
		if(self.spcl):
			newquery = {}
			querytokens = self.text.split(":")[1:]
			field = self.text.split(":")[0]

			for token in querytokens[:-1]:
				currentquery = ' '.join(token.split()[:-1])
				newquery[field] = currentquery
				field = token.split()[-1]

			newquery[field] = querytokens[-1]

			for field in newquery:
				query = newquery[field]
				query = self.__removeSymbols(query)
				self.__tknize(query)

				for idx,token in enumerate(self.terms):
					if self.__checkSword(token) and len(self.terms) > 1:
						del self.terms[idx]
						del token
						continue

					token = self.__stemToken(token)
					idx_file = self.__searchFiles(token)

					docs = self.__getDocuments(token, idx_file, field)
					self.__calculateScores(docs)
					del docs
		else:
			query = self.__removeSymbols(self.text)
			self.__tknize(query)

			for idx, token in enumerate(self.terms):
				if self.__checkSword(token) and len(self.terms) > 1:
					del token
					continue

				token = self.__stemToken(token)
				#print "Preprocessing time: ", time.time()-start_time
				idx_file = self.__searchFiles(token)
				#print "index file found: ", time.time()-start_time

				docs = self.__getDocuments(token, idx_file)
				#print "documents gathered: ", time.time()-start_time

				self.__calculateScores(docs)
				#print "scores calculated: ", time.time()-start_time
				del docs

		maxlen = min(10, len(self.results))
		ans = sorted(self.results, key=self.results.__getitem__, reverse=True)[:maxlen]
		#print "scores sorted: ", time.time()-start_time
		self.results.clear()

		for docid in ans:
			idx = Bsearch(int(docid), "docmapping.txt", True)
			if idx > 0:
				line = linecache.getline("docmapping.txt", idx).strip("\n")
				print ':'.join(line.split(":")[1:])
			else:
				print "document not found in mapping"

		#print "result output: ", time.time()-start_time
		del ans

def help_user():
	print "Query Format:"
	print "A) Single line general query: 'Search: <query>'"
	print "B) Section based queries: 'Search: <section_tag>:<query> <section_tag>:<query> ...'"
	print "\t Various tags that can be used are:"
	print "\t 1) 't' to search in Page title"
	print "\t 2) 'b' to search in Page body"
	print "\t 3) 'i' to search in Page infobox"
	print "\t 4) 'r' to search in Page references"
	print "\t 5) 'l' to search in External links of a page"
	print "\t 4) 'c' to search in Page categories"

def main():
	prog_name = sys.argv[0]
	update_stopwords()
	inp = ' '.join(sys.argv[1:])
	inp = inp.lower()

	if(inp=="\help"):
		help_user()
	elif(inp=="\exit"):
		print "Bye!"
	else:
		start_time = time.time()
		query = WikiQuery(inp)
		query.process_query()
		del query
		del inp
		print "\n*** Time taken to process query:", time.time() - start_time, " ***\n"

if __name__=="__main__":
	main()
