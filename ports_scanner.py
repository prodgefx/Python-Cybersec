#!/bin/python3

import sys
import socket
import datetime

if len(sys.argv) == 2:
	target = socket.gethostbyname(sys.argv[1])
else:
	print("Invalid amount of arguments")


#add a pretty banner

print("*" * 50)
print(f"[scanning target] {target} for open ports")
print("*" * 50)

try:
	for port in range(1,65535):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	
		socket.setdefaulttimeout(3)
		result = s.connect_ex((target, port))
		if result == 0:
			print(f"port {port} is open")
		s.close()
		
except KeyboardInterrupt:
	print("\n Exiting program")


except socket.gaierror:
	print("Hostname could not be resolved")
	
except socket.error:
	print("Couldn't connect to server")
