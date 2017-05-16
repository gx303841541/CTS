#!/usr/bin/python3
import datetime, sys, os

class cprint:

	def __init__(self, value=' '):

		STYLE = {
			'fore': {
				'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
				'blue': 34, 'purple': 35, 'cyan': 36, 'white': 37,
			},
	
			'back': {
				'black': 40, 'red': 41, 'green': 42, 'yellow': 43,
				'blue': 44, 'purple': 45, 'cyan': 46, 'white': 47,
			},
	
			'mode': {
				'default': 0, 'bold': 1, 'underline': 4, 'blink': 5, 'invert': 7,
			},
	
			'default': {
				'end': 0,
			}
		}
		self.style = STYLE
		self.name = value

	def common_p(self, string, mode='defult', fore='blue', back=''):
		mode = '%s' % self.style['mode'][mode] if mode in self.style['mode'] else self.style['mode']['default']
		fore = '%s' % self.style['fore'][fore] if fore in self.style['fore'] else ''
		back = '%s' % self.style['back'][back] if back in self.style['back'] else ''
		style = ';'.join([s for s in [mode, fore, back] if s])
		style = '\033[%sm' % style
		end = '\033[%sm' % self.style['default']['end']
	
		print ("%s%s%s" % (style, string, end))

	def notice_p(self, string, mode='defult', fore='yellow', back=''):
		mode = '%s' % self.style['mode'][mode] if mode in self.style['mode'] else self.style['mode']['default']
		fore = '%s' % self.style['fore'][fore] if fore in self.style['fore'] else ''
		back = '%s' % self.style['back'][back] if back in self.style['back'] else ''
		style = ';'.join([s for s in [mode, fore, back] if s])
		style = '\033[%sm' % style
		end = '\033[%sm' % self.style['default']['end']
	
		print ("%s%s%s" % (style, string, end))
		
	def debug_p(self, string, mode='defult', fore='green', back=''):
		mode = '%s' % self.style['mode'][mode] if mode in self.style['mode'] else self.style['mode']['default']
		fore = '%s' % self.style['fore'][fore] if fore in self.style['fore'] else ''
		back = '%s' % self.style['back'][back] if back in self.style['back'] else ''
		style = ';'.join([s for s in [mode, fore, back] if s])
		style = '\033[%sm' % style
		end = '\033[%sm' % self.style['default']['end']

		try:
		    raise Exception
		except:
		    f = sys.exc_info()[2].tb_frame.f_back	
		print ("%s%s [%s line:%s] %s%s" % (style, datetime.datetime.now(), repr(os.path.abspath(sys.argv[0])), f.f_lineno, self.name + string, end))
			
	def error_p(self, string, mode='defult', fore='red', back=''):
		mode = '%s' % self.style['mode'][mode] if mode in self.style['mode'] else self.style['mode']['default']
		fore = '%s' % self.style['fore'][fore] if fore in self.style['fore'] else ''
		back = '%s' % self.style['back'][back] if back in self.style['back'] else ''
		style = ';'.join([s for s in [mode, fore, back] if s])
		style = '\033[%sm' % style
		end = '\033[%sm' % self.style['default']['end']

		try:
		    raise Exception
		except:
		    f = sys.exc_info()[2].tb_frame.f_back
		print ("%s%s [%s line:%s] %s%s" % (style, datetime.datetime.now(), repr(os.path.abspath(sys.argv[0])), f.f_lineno, self.name + string, end))


		
	def warning_p(self, string, mode='blink', fore='red', back='black'):
		mode = '%s' % self.style['mode'][mode] if mode in self.style['mode'] else self.style['mode']['default']
		fore = '%s' % self.style['fore'][fore] if fore in self.style['fore'] else ''
		back = '%s' % self.style['back'][back] if back in self.style['back'] else ''
		style = ';'.join([s for s in [mode, fore, back] if s])
		style = '\033[%sm' % style
		end = '\033[%sm' % self.style['default']['end']
	
		print ("%s%s%s" % (style, string, end))		
				

if __name__ == '__main__':
	
	p = cprint('test')
	p.debug_p("this is ok?")
	p.error_p("this is ok?")
	p.warning_p("this is ok?")
	p.notice_p("this is ok?")
	p.common_p("this is ok?")



	



