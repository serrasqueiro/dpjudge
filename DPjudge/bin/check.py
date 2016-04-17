import os, stat, sys, textwrap
import host

from DPjudge import *
from DPjudge.Game import Time

class Check(Status):
	#	----------------------------------------------------------------------
	"""
	This class is invoked by the cron job to check deadlines on all games,
	and handle each when and as necessary.
	The following flags can be added:
		-t	To check the timestamp of the last run, and not run if too much
			time has elapsed (more than an hour).
	This could indicate that the server went down. If this happens, the
	judgekeeper should first make sure that all games are ok and extend the
	deadline of at least all active games. He can then run the check script
	manually once without any flags, or remove the timestamp file in the log
	directory ($JDG/log/check.tim). This will reactivate the cron job.

	Other flags:
		-r	To send only reminders for inactive games
		-a	To check only on active games (opposite of -r)
	If neither -a or -r is specified, the program will check on active games
	and once a day, at the midnight hour, send reminders for inactive games.
	"""
	#	----------------------------------------------------------------------
	def __init__(self, argv = None):
		Status.__init__(self)
		if argv is None: argv = sys.argv
		now = Time('GMT')
		tsf = host.logDir + '/check.tim'
		tsf2 = host.logDir + '/check2.tim'
		if '-t' in argv and os.path.exists(tsf):
			last = os.path.getmtime(tsf)
			curr = now.seconds()
			if last + 3600 < curr:
				# Use a second timestamp file to keep track of subsequent
				# server outages.
				last2, again = 0, False
				if os.path.exists(tsf2):
					last2 = os.path.getmtime(tsf2)
					if last2 > last and last2 + 3600 < curr:
						last, again = last2, True
				hours = int((curr - last) / 3600)
				days, hours = hours / 24, hours % 24
				msg = '\n'.join(map(lambda x: '\n'.join(textwrap.wrap(x, 75)),
					('Attention: ' + ['More than ', 'Once again '][again] +
					(days > 1 and ('%d days ' % days) or
					days == 1 and 'a day ' or '') +
					(days > 0 and hours > 0 and 'and ' or '') +
					(hours > 1 and ('%d hours ' % hours) or hours == 1 and
					'an hour ' or '') + (days + hours > 1 and 'have ' or
					'has ') + 'passed since the last check. ' +
					['This could be due to a server outage or an exception ' +
					'raised during the execution of the check script. ' +
					'As a precaution automatic deadline checking has been ' +
					'disabled. ',
					'This is probably caused by another server outage. ' +
					'Automatic deadline checking is still disabled. '][again] + 
					'\n\nInvestigate, extend deadlines if necessary, ' +
					'and only then run check once more without the ' +
					'-t option to restart the process.').split('\n')))
				print(msg)
				# Warn the judgekeeper.
				if not last2 or again:
					mail = Mail(host.judgekeeper,
						'%s server outage' % host.dpjudgeID)
					mail.write(msg)
					mail.close()
				open(tsf2, 'w').close()
				raise ServerOutageSuspected
		print 'Checking deadlines at %s GMT' % now.cformat()
		flags = [x for x in argv[1:] if x.startswith('-')]
		gameList = [x for x in argv[1:] if not x.startswith('-')]
		for gameName, data in self.dict.items():
			if 'completed' in data or 'held' in data or 'terminated' in data:
				continue
			if gameList and gameName not in gameList: continue
			#print('Checking %s' % gameName)
			try: game = self.load(gameName)
			except:
				print gameName, 'DOES NOT EXIST!'
				continue
			if not game.master or len(game.master) != 3:
				print game.name, 'HAS NO MASTER!'
				continue
			#	-----------------------------------------------------------
			#	At the midnight hour or if the -r flag is set, remind a
			#	Master of any errors or any forming, waiting, or unprepared
			#	games he has.
			#	-----------------------------------------------------------
			if 'NO_DEADLINE' in game.rules: line = None
			else:
				line = game.deadline
				if 'active' in data and not line: game.error += ['NO DEADLINE']
			if '-r' not in flags and (
				'-a' in flags or now[-4:] >= '0020'): pass
			elif game.error:
				print game.name, 'has ERRORS ... notifying the Master'
				for addr in game.master[1].split(',') + [
					host.judgekeeper] * (not game.tester):
					mail = Mail(addr,
						'Diplomacy ERRORS (%s)' % game.name)
					mail.write("The game '%s' on %s has the following "
						'errors in its status file:\n\n%s\n\nLog in at\n'
						'   %s?game=%s\nto correct the errors!\n\n'
						'Thank you,\nThe DPjudge\n' %
						(game.name, host.dpjudgeID, '\n'.join(game.error),
						host.dpjudgeURL, game.name))
					mail.close()
			elif 'active' in data:
				if line and game.deadlineExpired('1W'):
					critical = game.deadlineExpired('4W')
					for addr in game.master[1].split(',') + [
						host.judgekeeper] * (not game.tester and critical):
						mail = Mail(host.judgekeeper,
							'Diplomacy game alert (%s)' % game.name)
						mail.write("%s:\n\nThe %s game '%s' on %s is "
							'past its deadline for more than %s.\n\n'
							'Visit the game at\n'
							'   %s?game=%s\nfor more information.\n\n'
							'Thank you,\nThe DPjudge\n' %
							(addr == host.judgekeeper and 'JudgeKeeper'
							or 'Master', game.private and 'private' or 'public',
							game.name, host.dpjudgeID, critical and '4 weeks'
							or '1 week', host.dpjudgeURL, game.name))
					mail.close()
			elif 'terminated' not in data:
				reason = ''
				if 'waiting' in data:
					state = 'waiting'
					if game.avail:
						reason = ' Need to replace %s.' % ', '.join([
							game.anglify(x[:x.find('-')]) + x[x.find('-'):]
							for x in game.avail])
					if line and game.deadlineExpired('8W'):
						mail = Mail(host.judgekeeper,
							'Diplomacy game alert (%s)' % game.name)
						mail.write("JudgeKeeper:\n\nThe %s game '%s' on %s is "
							'in the %s state for more than 8 weeks.%s\n\n'
							'Visit the game at\n'
							'   %s?game=%s\nfor more information.\n\n'
							'Thank you,\nThe DPjudge\n' %
							(game.private and 'private' or 'public',
							game.name, host.dpjudgeID, state, reason,
							host.dpjudgeURL, game.name))
						mail.close()
				elif 'forming' in data:
					state = 'forming'
					spots = game.avail and int(game.avail[0]) or (
						len(game.map.powers) - len(game.map.dummies))
					reason = ' %d position%s remain%s.' % (
						spots, 's'[spots == 1:], 's'[spots != 1:])
				else: state = data[1]
				print game.name, 'is in the %s state' % state,
				print '... reminding the Master'
				for addr in game.master[1].split(','):
					mail = Mail(addr,
						'Diplomacy game reminder (%s)' % game.name)
					mail.write("GameMaster:\n\nThe game '%s' on %s is "
						'still in the %s state.%s\n\nVisit the game at\n'
						'   %s?game=%s\nfor more information.\n\n'
						'Thank you,\nThe DPjudge\n' %
						(game.name, host.dpjudgeID, state, reason,
						host.dpjudgeURL, game.name))
					mail.close()
			if game.error or 'active' not in data or (
				'-r' in flags and '-a' not in flags): continue
			#	---------------------------------------------------
			#	Check for expired grace periods (auto-CD or RESIGN)
			#	---------------------------------------------------
			graceOver = game.graceExpired() and not game.avail
			if graceOver and 'CIVIL_PREVIEW' not in game.rules: game.delay = 0
			if game.delay:
				game.delay -= 1
				print game.name, 'is delayed, now delay is', game.delay
			elif graceOver: # and game.latePowers()
				if 'CIVIL_DISORDER' in game.rules:
					print game.name, 'will process using CIVIL_DISORDER'
				elif 'CIVIL_PREVIEW' in game.rules:
					game.changeStatus('waiting')
					game.delay, game.preview = 72, 1
					game.save()
					print game.name, 'will preview using CIVIL_PREVIEW'
				else:
					print game.name, 'will RESIGN its late player(s)'
					game.lateNotice()
					game.changeStatus('waiting')
					game.save()
					continue
				game.process(now = 1)
			elif game.ready() and not game.await:
				game.preview = 'PREVIEW' in game.rules
				print (game.name + ' is ready and will be pr%sed now' %
					('ocess', 'eview')[game.preview])
				if game.preview:
					game.delay = 72
					game.save()
				try: game.process(now = 1)
				except: pass
				if game.await:
					mail = Mail(host.judgekeeper,
						'Diplomacy adjudication error! (%s)' % game.name)
					mail.write('JudgeKeeper:\n\nThe game %s on %s\n'
						'encountered an error during adjudication\n'
						'and is still in the AWAIT state.\n' %
						(game.name, host.dpjudgeID))
					mail.close()
			elif line and game.deadlineExpired():
				print game.name, 'is not ready but is past deadline'
				game.lateNotice()
				#	---------------------------------------
				#	Reschedule to check game in eight hours
				#	---------------------------------------
				game.delay = 24
			elif line:
				print game.name, 'is not to deadline yet',
				hey, when = game.latePowers(), game.timing.get('WARN', '4H')
				for warn in when.split(','):
					if warn[:-1] != '0' and hey:
						hit = line.offset('-' + warn)
						#	------------------------------------------
						#	Note that we don't need to change the time
						#	zone for "now", since internally the Time
						#	class compares the timestamps
						#	------------------------------------------
						if hit <= now < hit.offset('20M'):
							print '... sending reminders',
							game.lateNotice()
							break
				print
				continue
			if not game.preview: game.save()
		if os.path.exists(tsf2):
			try: os.unlink(tsf2)
			except: pass
		open(tsf, 'w').close()
	#	----------------------------------------------------------------------
