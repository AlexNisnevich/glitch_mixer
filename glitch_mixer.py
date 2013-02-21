#!/usr/bin/python
#
# Mixer and sequencer for minimalist algorithmic compositions
# (a la http://countercomplex.blogspot.com/2011/10/algorithmic-symphonies-from-one-line-of.html)
#
# Requires ALSA, so for the moment it will only run on Linux. Sorry!
#
# DO NOT run as superuser, and never use untrusted oneliners, as they can
# execute arbitrary code. Be safe.

import os
import subprocess as sub
import time
import traceback
import signal
import random

FNULL = open(os.devnull, 'w')
RESERVED = ['random']

running = {}
library = []
loop = False # number of iterations or False
loop_contents = []

def run(command):
	global running, library, loop, loop_contents

	if loop and command != 'next':
		# defining a loop - do not execute this command yet
		loop_contents.append(command)
		return

	parts = command.split(' ')
	func = parts[0]

	# comment or blank line
	if len(func) == 0 or func == '#':
		pass

	# play specified oneliner
	elif func == 'start':
		name = parts[1]
		if name == 'random':
			name = random.choice(library)[0]

		process = sub.Popen('%s/_temp_%s' % (os.getcwd(), name), stdout=sub.PIPE)
		aplay_process = sub.Popen('aplay -q', stdin=process.stdout, shell=True, preexec_fn=os.setsid)
		running.setdefault(name, []).append((process, aplay_process))

	# stop the specified oneliner (if none specified, stop all)
	elif func == 'stop':
		if len(parts) == 1:
			for name in running.keys():
				for processes in running[name]:
					processes[0].terminate()
					os.killpg(processes[1].pid, signal.SIGTERM)
			running.clear()
		else:
			if parts[1] == 'random':
				name = random.choice(running.keys())
			else:
				name = parts[1]

			processes = running[name].pop()
			processes[0].terminate() # kill program
			os.killpg(processes[1].pid, signal.SIGTERM) # kill aplay (running in spawned shell)
			if len(running[name]) == 0:
				del running[name]

	# delay X secs
	elif func == 'sleep':
		if parts[1] == 'random':
			duration = random.randint(0, 3)
		else:
			durattion = float(parts[1])

		time.sleep(float(duration))

	# add oneliner to library
	elif func == 'add':
		oneliner = (parts[1], parts[2])
		add_oneliner(oneliner)

	# add contents of libfile to library
	elif func == 'import':
		libfile = parts[1]
		import_library(libfile)

	# list contents of library
	elif func == 'list':
		for entry in library:
			print '%s\t%s' % entry

	# begin an loop ("loop X" is a finite loop, "loop" is an infinite loop)
	# no nesting of loops is allowed
	elif func == 'loop':
		if len(parts) > 1:
			iterations = int(parts[1])
		else:
			iterations = 999999 # effectively infinite

		loop_contents = []
		loop = iterations

	# mark the endpoint of a loop
	elif func == 'next':
		iterations = loop
		loop = False

		for _ in range(iterations):
			try:
				for command in loop_contents:
					run(command)
			except KeyboardInterrupt:
				print
				break

	# execute mixfile
	elif func == 'exec':
		mixfile = parts[1]
		for line in open(mixfile):
			try:
				print line,
				line = line.strip()
				run(line)
			except KeyboardInterrupt:
				print
				break
	else:
		print 'Unknown command: %s' % func

def add_oneliner(oneliner):
	name, code = oneliner
	if name in RESERVED:
		raise Exception('%s is a reserved word!' % name)
	program = "main(t,v){for(t=0;;t++)putchar(%s);}" % code
	os.system('echo "%s" > _temp_%s.c' % (program, name))
	os.system('gcc _temp_%s.c -o _temp_%s' % (name, name))
	library.append(oneliner)

def import_library(library):
	count = 0
	for line in open(library):
		line = line.strip()

		try:
			if len(line) == 0 or line[0] == '#':
				continue
			parts = line.split('\t')
			oneliner = (parts[0], parts[1])
			add_oneliner(oneliner)
			count += 1
		except Exception, e:
			print 'Error importing "%s": %s' % (line, e)
	print 'Imported %d oneliners' % count

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
