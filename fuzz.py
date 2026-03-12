#!/bin/python3

import requests
import sys

base_url = "http://10.10.11.161"

def loop():
	for word in sys.stdin:
	    complete_url = f"{base_url}/{word}"	    
	    response = requests.get(url=complete_url)
		
	    if response.status_code == 404:
	    	loop()
	    	
	    else:	
	    	data = response.json()
	    	print(word)
	    	print(res.status_code)    
	    	print("Response data:", data)

loop()