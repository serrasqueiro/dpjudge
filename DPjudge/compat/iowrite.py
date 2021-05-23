#-*- coding: utf-8 -*-
# iowrite  (c)2021  Henrique Moreira

"""
stdin/ stdout/ stderr Python3 compatibility
"""

# pylint: disable=missing-function-docstring

import sys

debug = 0

class IOStream():
    """ Generic IO stream """
    _python2_compat = False
    _stream = None
    _encoding = ""

    def flush(self):
        self._stream.flush()

    def close(self) -> bool:
        return True

class StdOutput(IOStream):
    """ Standard Output class """
    def __init__(self, encoding:str="", old=False):
        """ Initializer """
        self._stream = sys.stdout
        self._encoding = encoding
        self._python2_compat = old

    def write(self, msg):
        if not self._python2_compat:
            self._stream.write(msg)
            return
        if isinstance(msg, bytes):
            astr = msg.decode(self._encoding)
        else:
            astr = msg
        self._stream.write(astr)

class StdError(StdOutput):
    """ Standard Error class """
    def __init__(self, encoding: str = "", old=False):
        """ Initializer """
        super().__init__(encoding, old)
        self._stream = sys.stderr

class Output(IOStream):
    """ Output class """
    def __init__(self, path:str, encoding:str=""):
        """ Initializer """
        assert isinstance(path, str)
        assert path, "Output() empty path"
        self._python2_compat = False
        self._stream = open(path, "wb")
        self._encoding = encoding

    def write(self, msg):
        if isinstance(msg, bytes):
            self._stream.write(msg)
            return
        if isinstance(msg, str):
            self.write(msg.encode(self._encoding))
            return
        assert False, f"Output(): unexpected msg type: {type(msg)}"

def dprint(*args, end='\n') -> bool:
    """ Debug print """
    if not debug:
        return False
    print(*args, end=end)
    return True
