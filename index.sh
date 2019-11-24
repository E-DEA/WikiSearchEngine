#!/usr/bin/env bash

help_user(){
	echo -e "\nQuery Format:"
	echo -e "A) Single line general query: 'Search: <query>'"
	echo -e "B) Section based queries: 'Search: <section_tag>:<query> <section_tag>:<query> ...'"
	echo -e "\t Various tags that can be used are:"
	echo -e "\t 1) 't' to search in Page title"
	echo -e "\t 2) 'b' to search in Page body"
	echo -e "\t 3) 'i' to search in Page infobox"
	echo -e "\t 4) 'r' to search in Page references"
	echo -e "\t 5) 'l' to search in External links of a page"
	echo -e "\t 4) 'c' to search in Page categories"
	echo -e "\n"
}

echo -e "Hello! Welcome to Wikipedia Search Engine.\n"
echo "To leave the search engine, type: \exit"
help_user

while true
do
 	read -p "Search: " -r query
 	if [ "$query" == "\exit" ]; then
 		python engine.py "$query"
 		exit 0
 	fi
 	python2 engine.py $query
done 
