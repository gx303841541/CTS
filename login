#!/usr/bin/python3


import re, os, sys
from time import sleep

from common_tool.common_tool import my_system

def login(user, args):
    dtach_file= "/tmp/dtach-login-%s" % user
    ps_thread = my_system('ps -ef | grep %s' % dtach_file)
    if re.search('CTS.py', ps_thread):
    	os.system('dtach -a %s -e ^q' % dtach_file)
    else:
        os.system('dtach -A %s -e ^q ./CTS.py %s' % (dtach_file, args))


def main( argv = sys.argv[1:] ) :
    if len(argv) > 0:
        user = argv[0]
    else :
        user = 'dog'

    args = ' '
    if len(argv) > 1:
        for arg in argv[1:]:
            args += arg
            args += ' '
    else:
        args = '-r both'
    login(user, args) 

if __name__ == '__main__':
    main(sys.argv[1:])

