#!/usr/bin/python
#
# Mixer and sequencer for minimalist algorithmic compositions
# (a la http://countercomplex.blogspot.com/2011/10/algorithmic-symphonies-from-one-line-of.html)
#
# DO NOT run as superuser, and never use untrusted oneliners, as they can
# execute arbitrary code. Be safe.

import os
import sys
import subprocess as sub
import time
import traceback
import signal
import random
import signal

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
bg_jobs = []

def cleanup(sig=None, func=None):
	global library;

	print 'Cleaning up ...'

	for name in running.keys():
		for processes in running[name]:
			processes[0].terminate()
			os.killpg(processes[1].pid, signal.SIGTERM)

	if sig == signal.SIGINT:
		for entry in library:
			os.system('killall .temp_%s > /dev/null 2>&1' % entry[0])
		os.system('rm .temp* > /dev/null 2>&1')

	sys.exit(0)

def run(command):
	global running, library, subroutine, subroutines, loop, loop_contents, mixfile, bg_jobs

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
		if sys.platform == 'linux2':
			# Linux - we can just use aplay
			play_command = 'aplay -q'
		else:
			# Not Linux - try to use sox
			play_command = 'sox -traw -r8000 -b8 -u - -tcoreaudio >/dev/null 2>&1'
		play_process = sub.Popen(play_command, stdin=process.stdout, shell=True, preexec_fn=os.setsid)
		running.setdefault(name, []).append((process, play_process))

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
		filename = parts[1]
		execute(filename)

	# execute mixfile in background thread
	elif func == 'thread':
		filename = parts[1]
		job = sub.Popen([__file__, filename], stdout=FNULL)
		print 'Starting background job with PID %d' % job.pid
		bg_jobs.append((job, filename))

	# list background jobs
	elif func == 'bg':
		for job in bg_jobs:
			print '\t%d\t%s' % (job[0].pid, job[1])

	# kill background job of specified PID
	elif func == 'kill':
		pid = int(parts[1])
		jobs = [job for job in bg_jobs if job[0].pid == pid]
		if len(jobs) > 0:
			print 'Killing background job with PID %d' % pid
			jobs[0][0].terminate()
			bg_jobs.remove(jobs[0])

	#
	#-- Misc functions --#
	#

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
	[name]            - run a subroutine of the given name, if one exists

	exec [mixfile]    - execute the commands in the given file
	thread [mixfile]  - execute the commands in the given file in a background thread
	kill [pid]        - kill the background thread with the given process ID
	bg                - list all currently running background threads
	"""

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
	program = "int main(int t, char *v[]){for(t=0;;t++)putchar(%s);}" % code
	os.system('echo "%s" > .temp_%s.c' % (program, name))
	os.system('gcc .temp_%s.c -o .temp_%s >/dev/null 2>&1' % (name, name))
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

def execute(file):
	global mixfile

	mixfile = file
	for line in open(mixfile):
		try:
			print line,
			line = line.strip()
			run(line)
		except KeyboardInterrupt:
			print
			break
	mixfile = False

signal.signal(signal.SIGTERM, cleanup)
import_library('builtins.lib')
if len(sys.argv) > 1:
	print 'Executing mixfile: %s' % sys.argv[1]
	execute(sys.argv[1])
else:
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
cleanup(signal.SIGINT)
