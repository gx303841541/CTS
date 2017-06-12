#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""log tool
by Kobe Gong. 2017-4-28
"""

import logging
from  logging.handlers import RotatingFileHandler
import coloredlogs



class my_logging:
    def __init__(self, path, clevel=logging.INFO, flevel=logging.INFO):
        coloredlogs.install(level=clevel)

        self.p = logging.getLogger(path)
        #self.p.setLevel(clevel)
        fmt = logging.Formatter('[%(asctime)s] [%(filename)s line:%(lineno)d] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

        #设置CMD日志
        #sh = logging.StreamHandler()
        #sh.setFormatter(fmt)
        #sh.setLevel(clevel)
        #self.p.addHandler(sh)
        
        #设置文件日志
        #fh = logging.FileHandler(path)
        #fh.setFormatter(fmt)
        #fh.setLevel(flevel)    
        #self.p.addHandler(fh)

        #定义一个RotatingFileHandler，最多备份5个日志文件，每个日志文件最大1M
        rh = RotatingFileHandler('system.log', maxBytes=10 * 1024 * 1024, backupCount=5)
        rh.setFormatter(fmt)
        rh.setLevel(logging.INFO)
        self.p.addHandler(rh)

    def debug(self,message):
        self.p.debug(message)

    def info(self,message):
        self.p.info(message)

    def warn(self,message):
        self.p.warn(message)

    def error(self,message):
        self.p.error(message)

    def critical(self,message):
        self.p.critical(message)

if __name__ =='__main__':
    mylog = my_logging('yyx.log',logging.ERROR,logging.DEBUG)
    mylog.p.info("11111")
    mylog.p.warn("2222222")
    mylog.p.info("11111")
    mylog.p.warn("3333333")
    mylog.p.info("11111")
    mylog.p.warn("4444444")
    

