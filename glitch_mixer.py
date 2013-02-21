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

	elif func == 'exec':
		# execute mixfile
		mixfile = parts[1]
		for line in open(mixfile):
			line = line.strip()
			print line
			run(line)

	else:
		print 'Unknown command: %s' % func

library = {
	'alex1': "t>>4|t>>2|t+t/2", # this one's my own
	'tejeez1': "(t*(t>>5|t>>8))>>(t>16)", # credit to tejeez (from viznut's 1st video)
	'viznut1': "(t*5&t>>7)|(t*3&t>>10)" # credit to viznut (from viznut's 3rd video)
}

running = {}

for key, oneliner in library.iteritems():
	program = "main(t){for(t=0;;t++)putchar(%s);}" % oneliner
	os.system('echo "%s" > _temp.c' % program)
	os.system('gcc _temp.c -o _temp_%s' % key)

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
for key in library.keys():
	os.system('killall _temp_%s > /dev/null 2>&1' % key)
os.system('rm _temp* > /dev/null 2>&1')
