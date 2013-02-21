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

library = {
	'alex1': "t>>4|t>>2|t+t/2", # this one's my own
	'tejeez1': "(t*(t>>5|t>>8))>>(t>16)", # credit to tejeez (from viznut's 1st video)
	'viznut1': "(t*5&t>>7)|(t*3&t>>10)" # credit to viznut (from viznut's 3rd video)
}

running = {}

# simple program to test start/stop/sleep functionality
commands = [
	'start alex1',
	'sleep 4',
	'start tejeez1',
	'sleep 3',
	'stop alex1',
	'sleep 5',
	'stop tejeez1',
	'start alex1',
	'start viznut1',
	'sleep 8',
	'start alex1',
	'sleep 3',
	'start alex1',
	'sleep 3',
	'start alex1',
	'sleep 3',
	'start alex1',
	'sleep 2'
]

for key, oneliner in library.iteritems():
	program = "main(t){for(t=0;;t++)putchar(%s);}" % oneliner
	os.system('echo "%s" > temp.c' % program)
	os.system('gcc temp.c -o temp_%s' % key)

try:
	for command in commands:
		print command
		parts = command.split(' ')
		func = parts[0]

		if func == 'start':
			# play specified oneliner
			name = parts[1]
			process = sub.Popen('%s/temp_%s' % (os.getcwd(), name), stdout=sub.PIPE)
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
except Exception:
	traceback.print_exc()

os.system('killall aplay > /dev/null')
for key in library.keys():
	os.system('killall temp_%s > /dev/null' % key)
os.system('rm temp*')
