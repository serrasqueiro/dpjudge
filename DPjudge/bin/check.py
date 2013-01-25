import os, time, datetime
import host

import DPjudge

class Check(DPjudge.Status):
	#	----------------------------------------------------------------------
	"""
	This class is invoked by the cron job to check deadlines on all games,
	and handle each when and as necessary.
	"""
	#	----------------------------------------------------------------------
	def __init__(self, gameList = None):
		DPjudge.Status.__init__(self)
		os.putenv('TZ', 'GMT')
		now = DPjudge.Game.Time()
		print 'Checking deadlines at %s GMT' % time.ctime()
		for gameName, data in self.dict.items():
			if 'completed' in data or 'held' in data: continue
			if gameList and gameName not in gameList: continue
			try: game = self.load(gameName)
			except:
				print gameName, 'DOES NOT EXIST!'
				continue
			if not game.master or len(game.master) != 3:
				print game.name, 'HAS NO MASTER!'
				continue
			#	-------------------------------------------------------------
			#	On Monday at the midnight hour, remind a Master of any errors
			#	or any forming, waiting, or unprepared games he has.
			#	-------------------------------------------------------------
			line = game.deadline
			if 'active' in data and not line: game.error += ['NO DEADLINE']
			if game.error or 'active' not in data:
				if now[-4:] >= '0020' or datetime.date(
					int(now[:4]), int(now[4:6]), int(now[6:8])).weekday(): pass
				elif game.error:
					print game.name, 'has ERRORS ... notifying the Master'
					for addr in game.master[1].split(','):
						mail = DPjudge.Mail(addr,
							'Diplomacy ERRORS (%s)' % game.name)
						mail.write("The game '%s' on %s has the following "
							'errors in its status file:\n\n%s\n\nLog in at\n'
							'   %s?game=%s\nto correct the errors!\n\n'
							'Thank you,\nThe DPjudge\n' %
							(game.name, host.dpjudgeID, '\n'.join(game.error),
							host.dpjudgeURL, game.name))
						mail.close()
				elif 'terminated' not in data:
					reason = ''
					if 'waiting' in data:
						state = 'waiting'
						if game.avail:
							reason = 'Need to replace %s.' % ', '.join([
								game.anglify(x[:x.find('-')]) + x[x.find('-'):]
								for x in game.avail])
					elif 'forming' in data:
						state = 'forming'
						spots = int(game.avail[0]) or (
							len(game.map.powers) - len(game.map.dummies))
						reason = '%d position%s remain%s.' % (
							spots, 's'[spots == 1:], 's'[spots != 1:])
					else: state = 'preparation'
					print game.name, 'is in the %s state' % state,
					print '... reminding the Master'
					for addr in game.master[1].split(','):
						mail = DPjudge.Mail(addr,
							'Diplomacy game reminder (%s)' % game.name)
						mail.write("GameMaster:\n\nThe game '%s' on %s is "
							'still in the %s state.%s\n\nVisit the game at\n'
							'   %s?game=%s\nfor more information.\n\n'
							'Thank you,\nThe DPjudge\n' %
							(game.name, host.dpjudgeID, state, reason,
							host.dpjudgeURL, game.name))
						mail.close()
				continue
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
					mail = DPjudge.Mail(host.judgekeeper,
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
						hit = (time.mktime(map(int,
							(line[:4], line[4:6], line[6:8], line[8:10],
							line[10:], 0, 0, 0, -1))) - int(warn[:-1]) *
							{ 'M': 60, 'H': 3600, 'D': 86400, 'W': 604800 }
							.get(warn[-1], 1))
						start = time.localtime(hit)[:5]
						end = time.localtime(hit + 1200)[:5]
						if start <= time.localtime()[:5] < end:
							print '... sending reminders',
							game.lateNotice()
							break
				print
				continue
			if not game.preview: game.save()
	#	----------------------------------------------------------------------

#	---------------
#	Check all games
#	---------------
if __name__ == '__main__':
	Check()
