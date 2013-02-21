#! /usr/local/bin/python3
# -*- coding:utf-8 -*-

#Created by : yanghua 
#Date       : 13-01-30

#import system modules
import os, smtplib, mimetypes, time, sys, subprocess, re, fileinput

#import customized modules
from utility import warn
from utility import notice

INSTALL_VERSION_PORT = \
{
    'VERSION_NUM' : "2.6.9",        #default version
    'PORT_NUM'    : "6379"      #default port
}

PRE_PROCESSING_EXPRESSION = \
(
    ('^VAR/'                ,   '/var/'),
    ('^ETC/'                ,   '/etc/'),
    ('^VAR_LOG/'            ,   '/var/log/'),
    ('^VAR_RUN/'            ,   '/var/run/'),
    ('^USR/'                ,   '/usr/'),
    ('^USR_LOCAL/'          ,   '/usr/local/'),
    ('^USR_LOCAL_BIN/'      ,   '/usr/local/bin/'),
)

PRE_PROCESSING_PATHS = {
    'VAR_RUN'               : '/var/run',
    'USR_LOCAL'             : '/usr/local',
    'VAR_REDIS'             : 'VAR/redis',
    'ETC_REDIS'             : 'ETC/redis',
    'VAR_LOG_REDIS'         : 'VAR_LOG/redis',
    'INSTALL_HOME_DIR'      : 'USR_LOCAL/redis-{VERSION_NUM}',
    'USR_LOCAL_BIN_REDIS'   : 'USR_LOCAL_BIN/redis-{VERSION_NUM}',
    'ETC_PROFILE'           : '/etc/profile',
    'ETC_REDIS'             : '/etc/redis',
    'ETC_INITD'             : '/etc/init.d',
    'LOGFILE_PATH'          : '/home/uninstall_log.log'
}

PROCESSED_PATHS = {}

#regex expression
REG_PATTERN_FILE_CMD        = "^file "
REG_PATTERN_CONFIG_CMD      = "^config "
REG_PATTERN_PATH            = "\{[^\{\}]*\}"


#file mode option
MODE_WRITE                  = "w"
MODE_APPEND                 = "a"
MODE_READWRITE              = "rw"

#file operate mode (for customized cmd:'file') 
APPEND_OPERATE              = "append"
REPLACE_OPERATE             = "replace"
REMOVE_OPERATE              = "remove"

#unstall commands
UNINSTALL_COMMANDS=\
[
    'sudo rm -r {INSTALL_HOME_DIR}*',                  #CMD_RM_INSTALL_HOME_DIR
    'sudo rm -r {USR_LOCAL_BIN_REDIS}',                #CMD_RM_USR_LOCAL_BIN_REDIS
    'file remove [] [redis] [{ETC_PROFILE}]',          #PYTHON_RM_PATH
    'sudo rm -r {ETC_REDIS}',                          #CMD_RM_ETC_REDIS
    'sudo rm -r {VAR_REDIS}',                          #CMD_RM_VAR_REDIS
    'sudo rm -r {VAR_REDIS}/{PORT_NUM}',               #CMD_RM_VAR_REDIS_PORT
    'sudo rm -r {VAR_LOG_REDIS}/',                     #CMD_RM_VAR_LOG_REDIS
    'sudo rm -r {ETC_REDIS}/{PORT_NUM}.conf',          #CMD_RM_REDIS_CONF
    'sudo rm -r {ETC_INITD}/redis_{PORT_NUM}'          #CMD_RM_REDIS_RUNSCRIPT

    #date:2013-02-21
    #problem: first install failure, run the uninstall script 
    #         then run install script again, at last the log reported 
    #         /var/run/redis_{port}.pid has exist. so here remove it 
    #         the problem was found in CentOS 6.3
    'sudo rm -r {VAR_RUN}/redis_{PORT_NUM}.pid'        #CMD_RM_VAR_RUN_REDIS_{PORTNUM}.pid
]

#================================Methods=====================================#

def cmd_parser(cmdStr):

    #parse file (customize) command
    if re.search(REG_PATTERN_FILE_CMD, cmdStr) is not None:
        splitedCmdParts=cmdStr.split(None)      #splited with ' '
        fileCMD_parser(splitedCmdParts)
        return

    #parse config (customize) command
    if re.search(REG_PATTERN_CONFIG_CMD, cmdStr) is not None:
        splitedCmdParts=cmdStr.split(None)      #splited with ' '
        configCMD_parser(splitedCmdParts)
        return

    #parse normal command
    normalCMD_parser(cmdStr)


def pathOfCmd_parser(cmdStr):
    global PROCESSED_PATHS, REG_PATTERN_PATH, INSTALL_VERSION_PORT

    #merged the two index dictionary
    mergedDic  = dict(PROCESSED_PATHS, **INSTALL_VERSION_PORT)

    matchedArr = re.findall(REG_PATTERN_PATH, cmdStr)
    
    if matchedArr is not None:
        for matchItem in matchedArr:
            path_key = matchItem[1:-1]
            cmdStr   = cmdStr.replace(matchItem, mergedDic[path_key])

    return cmdStr

def normalCMD_parser(cmdStr):
    parseredCmdStr =pathOfCmd_parser(cmdStr)
    print("[executing cmd] is : %s" % parseredCmdStr)
    logtoFile("[executing cmd] is : %s \n" % parseredCmdStr,MODE_APPEND)
    execute_cmd_sync(parseredCmdStr)


def fileCMD_parser(splitedCmdParts):
    '''
    the origin cmd str just like: file append [source] [target] [path] --5 parts
    '''
    parsedPath =''
    sourceTxt  =''
    targetTxt  =''

    if len(splitedCmdParts[4]) > 2:
        path       = splitedCmdParts[4][1:-1]
        parsedPath = pathOfCmd_parser(path)
    else:
        return

    logtoFile("[executing cmd] is : %s %s [%s] [%s] [%s] \n" % (splitedCmdParts[0], splitedCmdParts[1], sourceTxt, targetTxt, parsedPath), MODE_APPEND)

    if len(splitedCmdParts[2]) > 2:
        sourceTxt = splitedCmdParts[2][1:-1]

    if len(splitedCmdParts[3]) > 2:
        targetTxt = splitedCmdParts[3][1:-1]

    #handle file command
    if splitedCmdParts[1]==APPEND_OPERATE:
        with open(parsedPath, encoding='utf-8', mode=MODE_APPEND) as tmp_file:
            tmp_file.write(targetTxt)
            return

    if splitedCmdParts[1]==REPLACE_OPERATE:
        fileLines=[]
        with open(parsedPath, encoding='utf-8', mode='r+') as tmp_file:
            for line in tmp_file:
                if line.find(sourceTxt) !=-1:
                    line = line.replace(sourceTxt, targetTxt)
                fileLines.append(line)

        with open(parsedPath, encoding='utf-8', mode='w') as new_file:
            for l in fileLines:
                new_file.write(l)

        return

    if splitedCmdParts[1]==REMOVE_OPERATE:
        fileLines =[]
        with open(parsedPath, encoding='utf-8', mode='r+') as tmp_file:
            for line in tmp_file:
                if line.find(targetTxt) ==-1:
                    fileLines.append(line)
                

        with open(parsedPath, encoding='utf-8', mode='w') as new_file:
            for l in fileLines:
                new_file.write(l)
        return

def uninstall():
    [cmd_parser(cmd) for cmd in UNINSTALL_COMMANDS]


def execute_cmd_sync(cmdStr):
    global PROCESSED_PATHS
    with open(PROCESSED_PATHS['LOGFILE_PATH'], encoding='utf-8', mode=MODE_APPEND) as tmp_logfile:
        process=subprocess.Popen(cmdStr, shell=True, universal_newlines=True, stdout=tmp_logfile)
        process.wait()
    

def logtoFile(str,modeOption):
    global PROCESSED_PATHS
    with open(PROCESSED_PATHS['LOGFILE_PATH'], encoding='utf-8', mode=modeOption) as logFile:
        logFile.write(str)


def preProcessPaths():
    global PRE_PROCESSING_PATHS
    return {k:replaceStrWithRegexExpression(v) for k,v in PRE_PROCESSING_PATHS.items()}

        
def replaceStrWithRegexExpression(sourceStr):
    global PRE_PROCESSING_EXPRESSION,INSTALL_VERSION_PORT


    #match/replace the paths
    for (reg_Expression, replaceingStr) in PRE_PROCESSING_EXPRESSION:
        if re.search(reg_Expression, sourceStr) is not None:
            sourceStr =re.sub(reg_Expression, replaceingStr, sourceStr)

    #match/replace the version and port
    for k,v in INSTALL_VERSION_PORT.items():
        warppedKey='{%s}' % k
        if re.search(warppedKey, sourceStr) is not None:
            sourceStr =re.sub(warppedKey, v, sourceStr)
    return sourceStr


def environmentCheck():
    #TO DO: check the install environment 
    #here we think this is ok
    logtoFile('the environment is OK. \n',MODE_APPEND)
    return True


if __name__ == '__main__':

    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("+                      redis-automatic uninstall script (python)                              +")
    print("+------------------------------------------------------------————-----------------------------+")
    print("+ you may support sereval params (if you choosed customize mode when you installed the redis):+")
    print("+ (1) version num: the version number which you downloaded(2.6.9 as a default)                +")
    print("+ (2) port: the port which the redis-server run at(6379 as a default)                         +")
    print("+ Are you ready? here we go!                                                                  +")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print()

    while True:
        stepContinue =input("make sure you will uninstall the redis. Entner (y/n) to continue:  ")
        if stepContinue   == 'y':
            break
        elif stepContinue == 'n':
            warn("the uninstall has been stoped")
            exit(0)         #return 0:normal        1:error
            

    global INSTALL_VERSION_PORT

    while True:             #do .. while
        installMode =input("default install mode or customize install mode when installed redis? Enter (d/c) to continue:  ")
        if installMode   == 'c':
            INSTALL_VERSION_PORT['VERSION_NUM'] =input("please enter the version number(format like X.X.X):")
            INSTALL_VERSION_PORT['PORT_NUM']    =input("please enter the port :")
            break
        elif installMode == 'd':
            break


    #pre-process paths
    global PROCESSED_PATHS
    PROCESSED_PATHS = preProcessPaths()

    logtoFile('redis has been uninstalled %s \n' % time.strftime(' at %c'),MODE_WRITE)
    if environmentCheck():
        notice("the uninstall script is running. please wait several minutes")
        uninstall()
        notice("the uninstall script has run. Everything has log at path: %s" % PRE_PROCESSING_PATHS['LOGFILE_PATH'])
    else:
        warn("the environment has some problem. the uninstall script can not run.")


