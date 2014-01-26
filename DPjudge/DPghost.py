#!/usr/bin/env python -SO

import sys
import os
from codecs import open

class GhostScript:
	"""
In GhostScript, at least up to version 9.07, execform calls are not cached, but always expanded. As a result such
pdf-files are much bigger than needed. This has been reported as Bug 687561 of the GhostScript Bugzilla bug tracker
("Smaller PDFs when using execform").

This class provides a workaround by injecting a prolog into the ps-file which turns execform calls into pdfmark
calls, as pdfmarks can be turned into Form XObjects, which can be defined once and reused many times.

This can be achieved by either instantiating an object of this class and calling the markForms() method, or from
the command line by providing a number of options (optional), followed by the name of the PS file and optionally
the name of the resulting PDF file. An explanation of the different options can be obtained by specifying "-?" on
the command line.

The actual conversion from PS to PDF is done by calling ps2pdf, which must be on the system path (an explicit path
can be given when instantiating a class object; see the __init__ method for more on this). This is the task of the
ps2pdf() method.
	"""

	markFormCode = b"""
% Render forms either with execform or with pdfmark.
% As this patch is normally injected at the very start of the file, there's
% no risk of operators like systemdict being overwritten yet with procedures
% in userdict (or globaldict for that matter). Binding will take care that
% there are no surprises either when execform's replacement gets executed
% during page rendering.
% $_PDFMark$_
% Note that gsview defines pdfmark in userdict, ps2pdf in systemdict.
systemdict /pdfmark known {
% /$_PDFMark$_
	% Forms are a LanguageLevel 2 feature, just like globaldict, so there's not
	% much risk that this patch will be used on a LanguageLevel 1 file.
	currentglobal true setglobal globaldict begin
	/$_CurrentGlobal$_ exch def
	% Each form requires a unique name when passing it on to pdfmark.
	% Simply indexing the name with the form count will suffice.
	/$_FormCount$_ 0 def
	/$_Marks$_ [] def
% $_NestedForms$_
	/$_InFormPaint$_ false def
	/$_FormPaintDepth$_ 0 def
% /$_NestedForms$_
	% Trying to store a procedure in globaldict, results in invalidaccess.
	% But since these don't have to change their value (and survive save - restore),
	% it doesn't matter.
	$_CurrentGlobal$_ end setglobal
	/$_begin$_ {
		currentglobal true setglobal globaldict begin
		/$_CurrentGlobal$_ exch def
	} bind def
	/$_end$_ {
		$_CurrentGlobal$_ end setglobal
	} bind def
	% With mark and cleartomark, there's a risk that another mark is left on the stack,
	% and the stack is not restored to its previous point. It's better to count items on
	% the stack and pop off any excess. These counts are kept in an array to allow for
	% recursive entry.
	% This procedure takes one argument, the number of items currently on the stack that
	% will be consumed before the call to $_cleartomark$_.
	/$_mark$_ {
		count 1 sub exch sub $_Marks$_ aload length 1 add array astore /$_Marks$_ exch def
		% As these functions are called right before and after executing a user function, we
		% temporarily remove globaldict and systemdict from the dict stack.
		$_end$_
	} bind def
	% This procedure takes one argument, the number of items that should remain on the stack
	% that are a result of the code executed in between.
	/$_cleartomark$_ {
		$_begin$_
		count 1 sub 1 index sub $_Marks$_ 0 get sub
		dup 0 gt {
			dup 2 index 3 add 1 roll 1 add 1 index add exch roll { pop } repeat
		} { pop pop } ifelse
		$_Marks$_ dup length 1 sub 1 exch getinterval /$_Marks$_ exch def
	} bind def
	% Relying on gsave/grestore to restore the graphics state after executing the
	% PaintProc is not advisable, as PaintProc may forget to properly match every
	% gsave with a grestore. Let's use gstate instead.
	/$_GStates$_ [] def
	/$_gsave$_ {
		% Calling gstate in global VM results in invalidaccess, so we temporarily revert
		% to local VM.
		$_end$_ /$_GStates$_ $_GStates$_ aload
		gstate currentgstate
		exch length 1 add array astore def $_begin$_
	} bind def
	/$_grestore$_ {
		$_end$_ /$_GStates$_ $_GStates$_ aload exch
		setgstate
		length 1 sub array astore def $_begin$_
	} bind def
	/$_execform$_ /execform load def
	% Helper function to define the form.
	% Takes the dictionary as argument and a boolean telling whether to replace the dict
	% with the form name and form matrix or leave as is.
	/$_defineform$_ {
% $_NestedForms$_
		/$_FormPaintDepth$_ $_FormPaintDepth$_ 1 add def
		% -- REMOVE THIS LINE IF NESTED FORMS HAVE BEEN PATCHED. --
		/$_InFormPaint$_ true def
		% -- END REMOVAL --
% /$_NestedForms$_
		1 index
		% Surprisingly (Acrobat Reader dictates that) a form XObject is bound by the
		% same clipping path as the page, independent of the fact that the form will
		% be transformed or not before being painted. To counter this the BBox and
		% Matrix must be altered such that it fits on a page.
		% Calculate transformation matrix to fit on a page and apply to BBox.
		dup /BBox get aload 5 1 roll
		% Always translate to the origin to simplify further manipulations.
		4 2 roll matrix translate
		dup 4 1 roll itransform
		currentpagedevice /PageSize get aload pop
		4 3 roll 3 2 roll div 3 1 roll div
		% Only scale if the BBox exceeds the page in either direction (width or height).
		2 copy lt { exch } if pop dup 1 gt {
			dup matrix scale exch matrix concatmatrix
		} { pop } ifelse
		exch aload pop 4 2 roll pop pop 0 0 4 2 roll 4 index itransform 4 array astore
		% The actual form matrix will only be applied when invoking SP, as it may
		% contain rotations and shearing, which would negatively affect the BBox.
		3 2 roll dup /Matrix get 3 index exch matrix concatmatrix
		% Create unique form name by increasing the count.
		$_FormCount$_ 1 add dup /$_FormCount$_ exch def
		% Avoiding 0 for the first index, as log of 0 is not defined.
		dup log cvi 1 add
		exch 1 index string cvs
		1 index 8 add string
		dup 0 ($_Form) putinterval
		dup 6 4 3 roll putinterval
		dup 3 2 roll 6 add ($_) putinterval
		cvn cvx 1 array astore cvx
		dup 3 2 roll
		% Leave a copy of the form name and form matrix on the stack if needed.
		6 index { 2 copy 10 2 roll } if
		2 array astore
		2 index /$_FormSpec$_ 3 2 roll put
		% Render form.
		% Even the invocation of pdfmark is not 100% reliable to properly clear the stack,
		% therefore it's marked and cleared in the same way as any other user function.
		% See also the comment on /SP.
		1 $_mark$_ [ /_objdef 3 2 roll
		/BBox 5 index
		/BP pdfmark 0 $_cleartomark$_
		$_gsave$_
		% Clip according to the BBox.
		exch aload pop exch 3 index sub exch 2 index sub rectclip
		% Transform to fit the form on a page.
		exch matrix invertmatrix concat
		newpath
		% PaintProc should consume the dict object, but may fail to do so.
		1 $_mark$_ dup /PaintProc get exec 0 $_cleartomark$_
		$_grestore$_
		0 $_mark$_ [ /EP pdfmark 0 $_cleartomark$_
		% Make the form dict read-only.
		% Don't do this if the form is handled by defineresource.
		{
% $_NestedForms$_
			% Also not if nested forms are not handled properly, as the dict
			% should still be writable for the first invocation of the original execform.
			$_InFormPaint$_ not {
% /$_NestedForms$_
				readonly
% $_NestedForms$_
			} if
% /$_NestedForms$_
			pop
		} if
% $_NestedForms$_
		$_FormPaintDepth$_ 1 sub dup /$_FormPaintDepth$_ exch def 0 le {
			/$_InFormPaint$_ false def
		} if
% /$_NestedForms$_
	} bind def
	% Everything is in place, let's overrule the function.
	/execform {
		$_begin$_
% $_NestedForms$_
		% Fall back to the original execform if the form is embedded in another form,
		% and if nested forms are not handled properly (see ghostscript bug 689653, with patch,
		% on nested forms).
		$_InFormPaint$_ {
			% If the form is not defined yet and writable, define it.
			dup /$_FormSpec$_ known not 1 index wcheck and {
				false $_defineform$_
			} if false
		} {
% /$_NestedForms$_
			% If the form is already defined, load it, otherwise define it first, provided that
			% it's writable (which it should be, but you never know).
			dup /$_FormSpec$_ known {
				/$_FormSpec$_ get aload pop true
			} {
				dup wcheck {
					true $_defineform$_ true
				} {
					false
				} ifelse
			} ifelse
% $_NestedForms$_
		} ifelse
% /$_NestedForms$_
		{
			% Transform back to the original coordinate system, including applying the
			% original form matrix.
			$_gsave$_ concat
			% At least in gs8.63/GSview4.9 the following code, when tested in ghostview
			% (bypassing the systemdict check) would for some strange reason leave the mark
			% on the stack. To avoid this it's necessary to mark and clear it ourselves.
			% Furthermore, on the first rendering the CTM seems to be ignored, and the form
			% is painted as is, without proper scaling. After moving to the next page and
			% returning to the current page to force a repaint the form will be ok. This
			% may have been fixed in later versions of ghostview.
			1 $_mark$_ [ exch /SP pdfmark 0 $_cleartomark$_
			$_grestore$_
		} {
			% Fall back on the original execform
			1 $_mark$_ $_execform$_ 0 $_cleartomark$_
		} ifelse
		$_end$_
	} bind def
	% Forms may also be defined first as a resource.
	/$_defineresource$_ /defineresource load def
	/defineresource {
		$_begin$_
		dup /Form eq {
			% If the form is not defined yet and writable, define it.
			exch dup /$_FormSpec$_ known not 1 index wcheck and {
				false $_defineform$_
			} if exch
		} if
		3 $_mark$_ $_defineresource$_ 1 $_cleartomark$_
		$_end$_
	} bind def
% $_PDFMark$_
} if
% /$_PDFMark$_
	"""

	# Parameters that can be specified at initialization.
	# in: pdfFileMode - the file mode of the resulting PDF file, None if no change is required.
	# in: ps2pdfDir - the directory where ghostscript's ps2pdf script is installed. By default
	#   this will be determined by scanning the system path.
	# in: ps2pdfName - the file name of the ps2pdf script. By default ps2pdf. On Windows the
	#   .bat extension will be added automatically if no extension is given.
	# in: verbose - to print some information during execution.
	def __init__(self, pdfFileMode = None, ps2pdfDir = None, ps2pdfName = 'ps2pdf', verbose = False):
		self.pdfFileMode = pdfFileMode
		self.ps2pdfDir = ps2pdfDir
		self.ps2pdfName = ps2pdfName
		self.ps2pdfPath = None
		self.verbose = verbose

	# Converts a PostScript file to a PDF file.
	# in: psFileName
	# in: pdfFileName - optional, based on psFileName if omitted.
	# in: pdfParams - optional, a list of (key, val) tuples understood by GhostScript,
	#   whereby key starts with a character designating the data type, such as s or d.
	#   If no value is needed, the tuple should only contain one element, the key.
	# out: pdfFileName
	def ps2pdf(self, psFileName, pdfFileName = None, pdfParams = []):
		if not os.path.isfile(psFileName):
			sys.stderr.write("No such file: '%s'\n" % psFileName)
			return
		# Construct PDF file name from PS file name.
		if not pdfFileName:
			pdfFileName = os.path.splitext(psFileName)[0] + '.pdf'
		elif os.path.isdir(pdfFileName):
			pdfFileName = os.path.join(pdfFileName, os.path.basename(os.path.splitext(psFileName)[0])) + '.pdf'
		# Join together parameters.
		params = ['%s%s' % (type(x) in (tuple, list) and ('-' + x[0], len(x) > 1 and
				(len(x[0]) == 1 and ' "%s"' % x[1] or ((os.name == 'nt' and '#' or '=') +
				(type(x[1]) not in (str, unicode) and ('%' + x[0][0]) % x[1] or x[1])) or '')) or
				(x[0] == '@' and x or '-' + x, '')) for x in pdfParams]
		params = ' '.join(params + [(os.name == 'nt' and '"%s" "%s"' or '%s %s') % (psFileName, pdfFileName)])
		# Determine ps2pdf location.
		if not self.ps2pdfPath:
			if not os.path.splitext(self.ps2pdfName)[1]:
				self.ps2pdfName += (os.name == 'nt' and '.bat' or '')
			for path in (self.ps2pdfDir and [self.ps2pdfDir] or []) + (
					os.environ['PATH'].split(os.name == 'nt' and ';' or ':')):
				self.ps2pdfPath = os.path.join(path, self.ps2pdfName)
				if os.path.exists(self.ps2pdfPath): break
			else:
				sys.stderr.write('No ps2pdf in system path\n')
				return
		# Windows will freak out if both the ps2pdf.bat file and the ps file have spaces in their path.
		# To get around this, let's convert the ps2pdf.bat file path to its 8.3 format.
		self.ps2pdfPath = self.sanitizePath(self.ps2pdfPath)
		# Execute conversion.
		if self.verbose: print(self.ps2pdfPath + ' ' + params)
		os.system(self.ps2pdfPath + ' ' + params)
		# Change file mode.
		if self.pdfFileMode:
			try: os.chmod(pdfFileName, self.pdfFileMode)
			except: pass
		# Return PDF file name.
		return pdfFileName

	# Injects code replacing execform with pdfmark, then converts this file to PDF.
	# in: psFileName
	# in: pdfFileName - optional, based on psFileName if omitted.
	# in: pdfParams - optional, a list of (key, val) tuples understood by GhostScript,
	# out: pdfFileName -or- psMarkFileName
	# The following pseudo PDF parameters are detected:
	# -dDPghostPDFMark=boolean - to remove or keep the pdfmark sanity check. Default: false
	# -dDPghostNestedForms=boolean - to remove or keep the nested forms check. Default: false
	# -dDPghostPatchOnly=boolean - to inject the patch, but not produce a pdf file. Default: False
	# -dDPghostInject=boolean - to inject the code straight into the ps file. Default: False
	def markForms(self, psFileName, pdfFileName = None, pdfParams = []):
		if not os.path.isfile(psFileName):
			sys.stderr.write("No such file: '%s'\n" % psFileName)
			return
		extensionSplits = os.path.splitext(psFileName)
		if not pdfFileName:
			pdfFileName = extensionSplits[0] + '.pdf'
			markFileName = extensionSplits[0] + '.mrk' + extensionSplits[1]
		elif os.path.isdir(pdfFileName):
			pdfFileName = os.path.join(pdfFileName, os.path.basename(extensionSplits[0]))
			markFileName, pdfFileName = pdfFileName + '.mrk' + extensionSplits[1], pdfFileName + '.pdf'
		else:
			pdfExtensionSplits = os.path.splitext(pdfFileName)
			if pdfExtensionSplits[1] == extensionSplits[1]:
				markFileName, pdfFileName = pdfFileName, pdfExtensionSplits[0] + '.pdf'
			else: markFileName = pdfExtensionSplits[0] + '.mrk' + extensionSplits[1]
		try: lines = self.readLines(psFileName)
		except:
			sys.stderr.write("Unable to read PS file: %s\n" % sys.exc_info()[1])
			return
		idx, prolog, blank, newLine = 0, 0, 0, '\n'
		# Remove a previous injection of the same patch.
		lines = self.stripCode(lines, b'DPghost')
		# Insert the setup code inside the prolog (marked by %%BeginProlog and %%EndProlog), or, if there is none,
		# insert a prolog after the top comments (between the PS version and %%EndComments), before %%BeginSetup,
		# %%Page, or the first PS code in the file.
		for line in lines:
			idx += 1
			newLine = line[-2:] == b'\r\n' and line[-2:] or line[-1:] in b'\r\n' and line[-1:] or newLine
			line = line.strip()
			if line == b'': blank = 1; continue
			if line[:1] != b'%': break
			if line[:2] != b'%%': blank = 0; continue
			keyword = line[2:].split(b':')[0]
			if keyword in (b'BeginSetup', b'Page'): break
			elif keyword == b'BeginProlog': prolog = 1; break
		else:
			sys.stderr.write('PS file empty or contains only comments\n')
			return
		#if lines and lines[-1][-1:] not in '\r\n': lines[-1] += newLine
		if not prolog:
			lines = lines[:idx-1] + [b'%%BeginProlog' + newLine, b'%%EndProlog' + newLine] + [newLine] * blank + lines[idx-1:]
		params, markFormCode, stripComments = [], self.markFormCode, True
		for param in pdfParams:
			if type(param) not in (tuple, list): param = (param,)
			if param[0] == 'dDPghostPDFMark':
				if len(param) == 1 or param[1]: markFormCode = self.stripCode(markFormCode, b'PDFMark')
			elif param[0] == 'dDPghostNestedForms':
				if len(param) == 1 or param[1]: markFormCode = self.stripCode(markFormCode, b'NestedForms')
			elif param[0] == 'dDPghostPatchOnly':
				if len(param) == 1 or param[1]: pdfFileName = None
			elif param[0] == 'dDPghostInject':
				if len(param) == 1 or param[1]: markFileName = psFileName
			elif param[0] == 'dDPghostLeaveComments':
				if len(param) == 1 or param[1]: stripComments = False
			else: params += [len(param) != 1 and param or param[0]]
		lines = lines[:idx] + self.embedCode(markFormCode, newLine, stripComments) + lines[idx:]
		discardMarkFile = not os.path.exists(markFileName)
		if self.verbose: print("%satched file: '%s'" % (('P', 'Temporary p')[discardMarkFile], markFileName))
		try: self.writeLines(markFileName, lines)
		except:
			sys.stderr.write("Unable to write PS patch file: %s\n" % sys.exc_info()[1])
			return
		if pdfFileName:
			pdfFileName = self.ps2pdf(markFileName, pdfFileName, params)
			if discardMarkFile:
				try: os.unlink(markFileName)
				except: pass
			return pdfFileName
		else: return markFileName

# 	------------------------------------------------------------------------------------------------------------------
#	# Here's a different approach to the same problem. The idea is to replace the forms with small images, because
#	# GhostScript can turn images of any size to XObjects instead of making them inline. These thumbnail images
#	# contain only a few bits, which can be interpreted as a page number. The forms themselves are turned into pages
#	# of a template file in a separate step. Both are converted to PDF files using GhostScript. In the last step the
#	# image XObjects in the thumbnail PDF file are replaced by the forms in the template file, using the image bits
#	# as a page index to identify the correct form page in the template file.
#
# 	# Puts each form on a single page, discarding all other elements, then converts these to PDF.
# 	# Note that this can be a template file that simply lists all available forms, and may be reused many times
# 	# converting PS files that all make use of the same forms.
# 	# in: file.ps -or- template.ps
# 	# out: file.frm.pdf -or- template.frm.pdf
# 	def pageForms(self, psFileName, pdfParams = []):
# 		extensionSplits = os.path.splitext(psFileName)
# 		formFileName = extensionSplits[0] + '.frm' + extensionSplits[1]
# 		lines, idx, newLine = self.readLines(psFileName), 0, '\n'
# 		# Insert the setup code after the top comments (such as the PS version and initial DCS comments),
# 		# before the first PS code in the file. Note that this may be after the first %%Page DCS comment.
# 		for line in lines:
# 			if line.strip()[:1] not in ('', '%'):
# 				newLine = line[-2:] == '\r\n' and line[-2:] or line[-1:] in '\r\n' and line[-1:] or newLine
# 				break
# 			idx += 1
# 		if lines and lines[-1][-1:] not in '\r\n': lines[-1] += newLine
# 		# For the cleanup code at the end, we can choose to store it at the very end, or before
# 		# the last comments (such as the %%Pages DCS comment). For now we choose the former.
# 		# We should be careful about file operations on the current file, like flushfile or readline.
# 		# Even after erasing the page the PDF stream will still contain drawing instructions,
# 		# so we still should do one real showpage before drawing the first form.
# 		# A save/restore could potentially reset the $_Forms$_ contents, and simply saving it on
# 		# the stack before doing the restore will result in an invalidrestore error. Therefore no
# 		# save/restore.
# 		lines = lines[:idx] + self.embedCode("""
# /$_Forms$_ [] def
# /$_showpage$_ /showpage load def
# /showpage {erasepage initgraphics} bind def
# /$_execform$_ /execform load def
# /execform {dup /$_Index$_ known not {
# 	dup /$_Index$_ $_Forms$_ length 1 add put
# 	/$_Forms$_ [ $_Forms$_ aload length 2 add index ] def
# } if $_execform$_} bind def
# /save {} def /restore {} def
# 			""", newLine) + lines[idx:] + self.embedCode("""
# $_showpage$_
# $_Forms$_ { $_execform$_ $_showpage$_ } forall
# 			""", newLine)
# 		self.writeLines(formFileName, lines)
# 		return self.ps2pdf(formFileName, pdfParams)
#
# 	# Replaces forms with images inside the PS file. then converts these to PDF as image XObjects (not inline).
# 	# in: file.ps
# 	# out: file.tmb.pdf
# 	def thumbForms(self, psFileName, pdfParams = []):
# 		return self.ps2pdf(psFileName, pdfParams + [('dMaxInlineImageSize', 0)])
#
# 	# Replaces all thumb pictures in the thumb PDF file with forms,
# 	# whereby the form contents are taken from the corresponding page in the page PDF file.
# 	# Note that the page file can have a different file name, as it simply serves as a template.
# 	# in: file.tmb.pdf
# 	# in: template.frm.pdf
# 	# out: file.pdf
# 	def formThumbs(self, thumbFormFileName, pageFormFileName, removeImageResource = False):
# 		pass
# 	------------------------------------------------------------------------------------------------------------------

	# Reads a file that may contain binary data and may contain a mixture of
	#  eol's, and splits it into lines leaving the eol markers intact.
	def readLines(self, fileName):
		# Note that the 'U' mode would convert all eol's to '\n', which might
		# mess up some binary code, so we can't use that..
		filePtr = open(fileName, 'rb')
		# Will split on '\n' only, which fortunately also covers Windows-style
		# '\r\n', but not Mac-style '\r'. The latter is handled below.
		lines = filePtr.readlines()
		filePtr.close()
		stripes = []
		for line in lines:
			# Avoid splitting a '\r\n' eol.
			curls = line[:-2].split(b'\r')
			stripes += [curl + b'\r' for curl in curls[:-1]] + [curls[-1] + line[-2:]]
		return stripes

	def writeLines(self, fileName, lines):
		filePtr = open(fileName, 'wb')
		filePtr.writelines(lines)
		filePtr.close()

	def stripCode(self, text, pragma):
		lines, inPragma, isString = [], False, type(text) != list
		pragmas = [b'%% $_' + pragma + b'$_', b'%% /$_' + pragma + b'$_']
		for line in (isString and text.split(b'\n') or text):
			if line.strip() == pragmas[inPragma]: inPragma = not inPragma
			elif not inPragma: lines += [line]
		if inPragma:
			sys.stderr.write('Warning: Unmatched closing pragma: %s\n' % pragmas[True].decode())
			return text
		return (isString and b'\n'.join(lines) or lines)

	def embedCode(self, text, newLine = b'\n', stripComments = True):
		return [x + newLine for x in
				[b"% $_DPghost$_"] +
				[y for y in [x.strip() for x in text.strip().split(b'\n')]
							if not y.startswith(b'% ') or
							not (stripComments and not (y.startswith(b'% --') and y.endswith(b'--'))) and
							not ((y.startswith(b'% $_') or y.startswith(b'% /$_')) and y.endswith(b'$_'))] +
				[b"% /$_DPghost$_"]]

	def sanitizePath(self, path):
		if os.name != 'nt' or not ' ' in path: return path
		p = os.popen('for %I in ("' + path + '") do echo %~sI')
		path = p.readlines()[-1].strip() # last line from for command
		p.close()
		return path

if __name__ == '__main__':
	argv, options, params = sys.argv[1:], '', []
	while argv and argv[0][0] in '-@':
		param = argv.pop(0)
		if param[0] != '-':
			#params += [param]
			#continue
			sys.stderr.write('@ option not supported by ps2pdf. '
							 'Use -p to create a patched ps file, '
							 'then run it through "gs -sDEVICE=pdfwrite ..."\n')
			exit(1)

		param = param[1:]
		if not param or param == '_':
			sys.stderr.write('Unable to read from standard input. Please provide a file name.\n')
			exit(1)
		elif len(param) == 1:
			if param == 'c':
				#code = []
				#while argv and argv[0] != '-f': code += [argv.pop(0)]
				#params += [(param, ' '.join(code))]
				sys.stderr.write('-c option not supported by ps2pdf. '
								 'Use -p to create a patched ps file, '
								 'then run it through "gs -sDEVICE=pdfwrite ..."\n')
				exit(1)
			elif param == 'o':
				#params += [(param, argv.pop(0))]
				sys.stderr.write('-o option not supported by ps2pdf. '
								 'Add the output file name at the end of the command instead.\n')
				exit(1)
			elif param in 'fqh': params += [param]
			else: options += param
		elif param[0] == 'f':
			sys.stderr.write('-f option followed by file name not supported. '
							 'Rename the input file name if needed '
							 'and add it at the end of the command, '
							 'optionally followed by the output file name.\n')
			exit(1)
		else:
			indices = [y for y in [param.find(x) for x in '=#'] if y > -1]
			if indices:
				idx = min(indices)
				params += [(param[:idx], param[idx+1:])]
			else: params += [param]
	if len(argv) == 1: argv += ['']
	if '?' in options or len(argv) == 0 or argv[1][:1] == '-' or len(argv) > 2:
		help = """
Usage: %s [options] <file>.ps [<file>.pdf]
Options:
	-r raw     Convert straight to PDF without applying form patch
	-p patch   Create patch file (default: <file>.mrk.ps), but don't convert to pdf; equivalent to -dDPghostPatchOnly
	-i inject  Inject form patch straight into ps file (no new patch file created); equivalent to -dDPghostInject
	-m mark    Omit the pdfmark check, so that even gsview will use pdfmark instead of execform; equivalent to -dDPghostPDFMark
	-n nest    Allow nested forms; equivalent to -dDPghostNestedForms
	-l leave   Leave comments in the patch; equivalent to -dDPghostLeaveComments
	-v verbose Print information during execution
	-? help    Show this message
Other options are passed on to ps2pdf as is.
		""" % sys.argv[0]
		channel = '?' in options and sys.stdout or sys.stderr
		channel.write(help.strip())
	else:
		gs = GhostScript(verbose='v' in options)
		if 'r' in options: result = gs.ps2pdf(argv[0], argv[1], params)
		else:
			params += (
					['dDPghostPatchOnly'] * ('p' in options) +
					['dDPghostInject'] * ('i' in options) +
					['dDPghostPDFMark'] * ('m' in options) +
					['dDPghostNestedForms'] * ('n' in options) +
					['dDPghostLeaveComments'] * ('l' in options))
			result = gs.markForms(argv[0], argv[1], params)
		if not result: exit(1)
