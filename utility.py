#! /usr/local/bin/python3
# -*- coding:utf-8 -*-

#Created by : yanghua 
#Date       : 13-02-04


def printWithColor(color,meg):
    '''
        @desc:
            print 'msg' with 'color'

        @args:
            color   -   the front color
            msg     -   the msg want to print

        @return:
            None
    '''
    if color == 'r':
        fore = 31
    elif color == 'g':
        fore = 32
    elif color == 'b':
        fore = 36
    elif color == 'y':
        fore = 33
    else:
        fore = 37
    color = "\x1B[%d;%dm" % (1,fore)
    print("%s %s\x1B[0m" % (color,meg))

def warn(msg):
    printWithColor('r', msg)

def notice(msg):
    printWithColor('g', msg)