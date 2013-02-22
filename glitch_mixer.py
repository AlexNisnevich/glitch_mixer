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
RESERVED = ['random', 'start', 'stop', 'sleep', 'running', 'add', 'import', 'list',
			'loop', 'sub', 'end', 'exec', 'help', '#']

running = {}
library = []
subroutine = False # name of subroutine currently being defined or False
subroutines = {}
loop = False # number of iterations or False
loop_contents = []
prompt = '> '
mixfile = False # name of currently executing mixfile or False

def run(command):
	global running, library, subroutine, subroutines, loop, loop_contents, mixfile

	if loop and command != 'end':
		# defining a loop - do not execute this command yet
		loop_contents.append(command)
		return
	elif subroutine and command != 'end':
		# defining a subroutine - do not execute this command yet
		subroutines[subroutine].append(command)
		return

	parts = command.split(' ')
	func = parts[0]

	# comment or blank line
	if len(func) == 0 or func == '#':
		pass

	#
	#-- Basic functions --#
	#

	# play specified oneliner
	elif func == 'start':
		name = parts[1]
		if name == 'random':
			name = random.choice(library)[0]

		process = sub.Popen('%s/.temp_%s' % (os.getcwd(), name), stdout=sub.PIPE)
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
			duration = float(parts[1])

		time.sleep(float(duration))

	elif func == 'running':
		for pname in running.keys():
			print "\t%s" % pname

	#
	#-- Library functions --#
	#

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
			print '\t%s\t%s' % entry

	#
	#-- Control flow functions --#
	#

	# begin an loop ("loop X" is a finite loop, "loop" is an infinite loop)
	# no nesting of loops is allowed
	elif func == 'loop':
		if len(parts) > 1:
			iterations = int(parts[1])
		else:
			iterations = 999999 # effectively infinite

		loop_contents = []
		loop = iterations

	# begin a subroutine definition
	# subroutines do not take any parameters
	elif func == 'sub':
		if parts[1] in RESERVED:
			raise Exception('%s is a reserved word!' % parts[1])
		subroutine = parts[1]
		subroutines[subroutine] = []

	# end a loop or subroutine definition
	elif func == 'end':
		if mixfile:
			print "\033[Aend        " # overwrite last "> \t end" to "end"
		else:
			print "\033[A> end      " # overwrite last "> \t end" to "> end"

		if subroutine:
			subroutine = False
		elif loop:
			iterations = loop
			loop = False
			for _ in range(iterations):
				try:
					for command in loop_contents:
						run(command)
				except KeyboardInterrupt:
					print
					break

	#
	#-- Misc functions --#
	#

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
		mixfile = False

	# display help
	elif func == 'help':
		print """Supported commands:
	list              - list all currently loaded oneliners
	add [name] [code] - add a new oneliner to the library
	import [libfile]  - import all oneliners from a file (see builtins.lib for an example)

	start [name]      - start the oneliner with the given name
	start random      - start a random oneliner in the library
	stop              - stop all currently running oneliners
	stop [name]       - stop the currently running oneliner of the given name
	stop random       - stop a random currently running oneliner
	running           - list all currently running oneliners

	sleep [secs]      - pause for the specified number of seconds
	sleep random      - pause for randint(0, 3) seconds
	loop              - begin defining a loop that will run infinitely (break out of it with Ctrl-C)
	loop [num]        - begin defining a loop that will run for the given number of iterations
	sub [name]        - begin defining a subroutine with the given name
	end               - end a loop or subroutine definition
	exec [mixfile]    - execute the commands in the given file
	[name]            - run a subroutine of the given name, if one exists"""

	else:
		if func in subroutines:
			for command in subroutines[func]:
				run(command)
		else:
			print 'Unknown command: %s' % func

def add_oneliner(oneliner):
	name, code = oneliner
	if name in RESERVED:
		raise Exception('%s is a reserved word!' % name)
	program = "main(t,v){for(t=0;;t++)putchar(%s);}" % code
	os.system('echo "%s" > .temp_%s.c' % (program, name))
	os.system('gcc .temp_%s.c -o .temp_%s' % (name, name))
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
	print 'Imported %d oneliners from %s' % (count, library)

import_library('builtins.lib')
while True:
	try:
		prompt = '> \t' if (loop or subroutine) else '> '
		command = raw_input(prompt)
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
	os.system('killall .temp_%s > /dev/null 2>&1' % entry[0])
os.system('rm .temp* > /dev/null 2>&1')
