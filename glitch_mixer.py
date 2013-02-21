#!/usr/bin/python
#
# Mixer for minimalist algorithmic compositions
# (a la http://countercomplex.blogspot.com/2011/10/algorithmic-symphonies-from-one-line-of.html)
#
# Requires ALSA
# DO NOT run as superuser, and never use untrusted oneliners, as they can
# execute arbitrary code. Be safe.

import os
import subprocess as sub
import time
import traceback
import signal

FNULL = open(os.devnull, 'w')

def run(command):
	parts = command.split(' ')
	func = parts[0]

	if func == '#':
		# comment
		pass

	elif func == 'start':
		# play specified oneliner
		name = parts[1]
		process = sub.Popen('%s/_temp_%s' % (os.getcwd(), name), stdout=sub.PIPE)
		aplay_process = sub.Popen('aplay -q', stdin=process.stdout, shell=True, preexec_fn=os.setsid)
		running.setdefault(name, []).append((process, aplay_process))

	elif func == 'stop':
		# stop specified oneliner
		name = parts[1]
		processes = running[name].pop()
		processes[0].terminate() # kill program
		os.killpg(processes[1].pid, signal.SIGTERM) # kill aplay (running in spawned shell)

	elif func == 'sleep':
		# delay X secs
		duration = parts[1]
		time.sleep(float(duration))

	elif func == 'add':
		# add oneliner to library
		oneliner = (parts[1], parts[2])
		add_oneliner(oneliner)

	elif func == 'import':
		# add contents of libfile to library
		libfile = parts[1]
		import_library(libfile)

	elif func == 'list':
		# list contents of library
		for entry in library:
			print '%s\t%s' % entry

	elif func == 'exec':
		# execute mixfile
		mixfile = parts[1]
		for line in open(mixfile):
			line = line.strip()
			print line
			run(line)

	else:
		print 'Unknown command: %s' % func

def add_oneliner(oneliner):
	name, code = oneliner
	program = "main(t){for(t=0;;t++)putchar(%s);}" % code
	os.system('echo "%s" > _temp.c' % program)
	os.system('gcc _temp.c -o _temp_%s' % name)
	library.append(oneliner)

def import_library(library):
	count = 0
	for line in open(library):
		try:
			line = line.strip()
			if len(line) == 0 or line[0] == '#':
				continue

			parts = line.split('\t')
			oneliner = (parts[0], parts[1])
			add_oneliner(oneliner)
			count += 1
		except Exception:
			continue
	print 'Imported %d oneliners' % count

running = {}
library = []

import_library('builtins.lib')
while True:
	try:
		command = raw_input('>')
		if command == 'exit' or command == 'quit':
			break
		else:
			run(command)
	except Exception:
		traceback.print_exc()
	except KeyboardInterrupt:
		print
		break

print 'Cleaning up ...'
os.system('killall aplay > /dev/null 2>&1')
for entry in library:
	os.system('killall _temp_%s > /dev/null 2>&1' % entry[0])
os.system('rm _temp* > /dev/null 2>&1')
