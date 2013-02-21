#! /usr/local/bin/python3
# -*- coding:utf-8 -*-

#Created by : yanghua 
#Date       : 13-01-25

#import default modules
import os, smtplib, mimetypes, time, sys, subprocess, re, fileinput

#import customized modules
from utility import warn
from utility import notice

INSTALL_VERSION_PORT = \
{
    'VERSION_NUM' : "2.6.9",        #default version
    'PORT_NUM'    : "6379"          #default port
}

PRE_PROCESSING_EXPRESSION = \
(
    ('^VAR/'                ,   '/var/'),
    ('^ETC/'                ,   '/etc/'),
    ('^VAR_LOG/'            ,   '/var/log/'),
    ('^VAR_RUN/'            ,   '/var/run/'),
    ('^USR/'                ,   '/usr/'),
    ('^USR_LOCAL/'          ,   '/usr/local/'),
    ('^USR_LOCAL_BIN/'      ,   '/usr/local/bin/')
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
    'LOGFILE_PATH'          : '/home/install_log.log'
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


#install commands
CMD_CHMOD_USR_LOCAL_W       = "sudo chmod o+w {USR_LOCAL}"
CMD_CHMOD_USR_LOCAL_X       = "sudo chmod o+x {USR_LOCAL}"
CMD_CHMOD_ETC_PROFILE       = "sudo chmod o+w {ETC_PROFILE}"
CMD_WGET_REDIS_SOURCE       = "wget -P {USR_LOCAL} http://redis.googlecode.com/files/redis-{VERSION_NUM}.tar.gz"
CMD_CHMOD_TAREDFILE_UX      = "sudo chmod u+x {USR_LOCAL}/redis-{VERSION_NUM}.tar.gz"
CMD_CREATE_INSTALLDIR       = "sudo mkdir {INSTALL_HOME_DIR}/"
CMD_TAR                     = "sudo tar -zxvf {USR_LOCAL}/redis-{VERSION_NUM}.tar.gz -C {USR_LOCAL}/"
CMD_REMOVE_TAREDFILE        = "sudo rm {USR_LOCAL}/redis-{VERSION_NUM}.tar.gz"
CMD_MAKE                    = "sudo make  -C {INSTALL_HOME_DIR}/src/"
CMD_MAKETEST                = "sudo make test -C {INSTALL_HOME_DIR}/src/"

#deploy commands
CMD_MAKEDIR_USR_LOCAL_BIN_R = "sudo mkdir {USR_LOCAL_BIN_REDIS}/"
CMD_CP_REDIS_SERVER         = "sudo cp {INSTALL_HOME_DIR}/src/redis-server {USR_LOCAL_BIN_REDIS}/redis-server"
CMD_CP_REDIS_CLI            = "sudo cp {INSTALL_HOME_DIR}/src/redis-cli {USR_LOCAL_BIN_REDIS}/redis-cli"


#file operate format:
#file                       -- file operate identifier
#append / replace / remove  -- operate mode
#[origin]                   -- operate origin content(optional)
#[target]                   -- operate target content(optional)
#[file path]                -- operating file path
PYTHON_CMD_APPEND_PATH      = "file append [] [PATH=$PATH:{USR_LOCAL_BIN_REDIS}/] [{ETC_PROFILE}]"
CMD_MKDIR_ETC_REDIS         = "sudo mkdir {ETC_REDIS}"
CMD_CP_REDISCONF            = "sudo cp {INSTALL_HOME_DIR}/redis.conf {ETC_REDIS}/{PORT_NUM}.conf"
CMD_CHMOD_REDISCNF_OW       = "sudo chmod o+w {ETC_REDIS}/{PORT_NUM}.conf"
CMD_MKDIR_VAR_REDIS         = "sudo mkdir {VAR_REDIS}/"
CMD_MKDIR_VAR_REDIS_PORT    = "sudo mkdir {VAR_REDIS}/{PORT_NUM}/"
CMD_CHMOD_VAR_REDIS_PORT_OW = "sudo chmod o+w {VAR_REDIS}/{PORT_NUM}/ "
CMD_MKDIR_VAR_LOG_REDIS     = "sudo mkdir {VAR_LOG_REDIS}/"
CMD_CHMOD_VAR_LOG_REDIS_OW  = "sudo chmod o+w {VAR_LOG_REDIS}/"
CMD_CP_RUNSCRIPT            = "sudo cp {INSTALL_HOME_DIR}/utils/redis_init_script {ETC_INITD}/redis_{PORT_NUM}"
CMD_CHMOD_RUNSCRIPT_OW      = "sudo chmod o+w {ETC_INITD}/redis_{PORT_NUM}"

PYTHON_CMD_REPLACE_EXEC     = "file replace [EXEC=/usr/local/bin/redis-server] [EXEC={USR_LOCAL_BIN_REDIS}/redis-server] [{ETC_INITD}/redis_{PORT_NUM}]"
PYTHON_CMD_REPLACE_CLIEXEC  = "file replace [CLIEXEC=/usr/local/bin/redis-cli] [CLIEXEC={USR_LOCAL_BIN_REDIS}/redis-cli] [{ETC_INITD}/redis_{PORT_NUM}]"

PYTHON_CMD_REPLACE_PORT     = "file replace [${REDISPORT}] [{PORT_NUM}] [{ETC_INITD}/redis_{PORT_NUM}]"

#edit redis config file
#config operate format:
#config                     --config operate identifier
#[key]                      --modifying key
#[value]                    --new value
#[path]                     --config file path
PYTHON_CMD_CHANGE_DAEMON    = "config [daemonize] [yes] [{ETC_REDIS}/{PORT_NUM}.conf]"
PYTHON_CMD_CHANGE_PIDFILE   = "config [pidfile] [{VAR_RUN}/redis_{PORT_NUM}.pid] [{ETC_REDIS}/{PORT_NUM}.conf]"
PYTHON_CMD_CHANGE_PORT      = "config [port] [{PORT_NUM}] [{ETC_REDIS}/{PORT_NUM}.conf]"
PYTHON_CMD_CHANGE_LOGFILE   = "config [logfile] [{VAR_LOG_REDIS}/redis_{PORT_NUM}.log] [{ETC_REDIS}/{PORT_NUM}.conf]"
PYTHON_CMD_CHANGE_DIR       = "config [dir] [{VAR_REDIS}/{PORT_NUM}] [{ETC_REDIS}/{PORT_NUM}.conf]"
PYTHON_CMD_CHANGE_APPEND    = "config [appendonly] [yes] [{ETC_REDIS}/{PORT_NUM}.conf]"

CMD_PATH_EFFECTIVE_NOW      = ". {ETC_PROFILE}"


#file operate mode (for customized cmd:'file') 
APPEND_OPERATE              = "append"
REPLACE_OPERATE             = "replace"
REMOVE_OPERATE              = "remove"

INSTALL_COMMANDS=[
    CMD_CHMOD_USR_LOCAL_W,
    CMD_CHMOD_USR_LOCAL_X,
    CMD_CHMOD_ETC_PROFILE,
    CMD_WGET_REDIS_SOURCE,
    CMD_CHMOD_TAREDFILE_UX,
    CMD_CREATE_INSTALLDIR,
    CMD_TAR,
    CMD_MAKE,
    CMD_MAKETEST,
    CMD_MAKEDIR_USR_LOCAL_BIN_R,
    CMD_CP_REDIS_SERVER,
    CMD_CP_REDIS_CLI,

    PYTHON_CMD_APPEND_PATH,
    
    CMD_MKDIR_ETC_REDIS,
    CMD_CP_REDISCONF,
    CMD_CHMOD_REDISCNF_OW,
    CMD_MKDIR_VAR_REDIS,
    CMD_MKDIR_VAR_REDIS_PORT,
    CMD_CHMOD_VAR_REDIS_PORT_OW,
    CMD_MKDIR_VAR_LOG_REDIS,
    CMD_CHMOD_VAR_LOG_REDIS_OW,
    CMD_CP_RUNSCRIPT,
    CMD_CHMOD_RUNSCRIPT_OW,

    PYTHON_CMD_REPLACE_EXEC,
    PYTHON_CMD_REPLACE_CLIEXEC,
    PYTHON_CMD_REPLACE_PORT,

    PYTHON_CMD_CHANGE_DAEMON,
    PYTHON_CMD_CHANGE_PIDFILE,
    PYTHON_CMD_CHANGE_PORT,
    PYTHON_CMD_CHANGE_LOGFILE,
    PYTHON_CMD_CHANGE_DIR,
    PYTHON_CMD_CHANGE_APPEND,

    #date:2013-02-21
    #problem the command 'redis-cli' can not be found
    #        so move it's position
    #the proflem was found in CentOS 6.3
    CMD_PATH_EFFECTIVE_NOW
]

RUN_REDIS_SERVER_COMMANDS = \
[
    'sudo update-rc.d redis_{PORT_NUM} defaults',               #CMD_INIT_SCRIPT
    '/etc/init.d/redis_{PORT_NUM} start'                        #CMD_RUN_REDIS_SERVER
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
    parseredCmdStr=pathOfCmd_parser(cmdStr)
    print("[executing cmd] is : %s" % parseredCmdStr)
    logtoFile("[executing cmd] is : %s \n" % parseredCmdStr,MODE_APPEND)
    execute_cmd_sync(parseredCmdStr)


def fileCMD_parser(splitedCmdParts):
    #the origin cmd str just like: file append [source] [target] [path] --5 parts
    parsedPath =''
    sourceTxt  =''
    targetTxt  =''

    if len(splitedCmdParts[4]) > 2:
        path       = splitedCmdParts[4][1:-1]
        parsedPath = pathOfCmd_parser(path)
    else:
        return

    if len(splitedCmdParts[2]) > 2:
        sourceTxt = splitedCmdParts[2][1:-1]

    if len(splitedCmdParts[3]) > 2:
            targetTxt = pathOfCmd_parser(splitedCmdParts[3][1:-1])

    #print and log
    logStr="[executing customized cmd] is : %s [%s] [%s] [%s]" % (splitedCmdParts[0], sourceTxt, targetTxt, parsedPath)
    print(logStr)
    logtoFile(logStr , MODE_APPEND)

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
        return


def configCMD_parser(splitedCmdParts):
    #the origin cmd str just like: config [key] [new value] [path]  --4 parts
    path       = splitedCmdParts[3][1:-1]
    key        = pathOfCmd_parser(splitedCmdParts[1][1:-1])
    newValue   = pathOfCmd_parser(splitedCmdParts[2][1:-1])
    parsedPath = pathOfCmd_parser(path)
    
    fileLines  =[]

    with open(parsedPath, encoding='utf-8', mode='r+') as tmp_file:
            for line in tmp_file:
                if line.find(key) != -1 and line[0:1] != "#":
                    key , oldValue = line.split(None,2)
                    line=line.replace(oldValue, newValue)
                fileLines.append(line)

    with open(parsedPath, encoding='utf-8', mode='w') as new_file:
        for l in fileLines:
            new_file.write(l)


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
    global PRE_PROCESSING_EXPRESSION, INSTALL_VERSION_PORT
    #match/replace the paths
    for (reg_Expression, replaceingStr) in PRE_PROCESSING_EXPRESSION:
        if re.search(reg_Expression, sourceStr) is not None:
            sourceStr = re.sub(reg_Expression, replaceingStr, sourceStr)

    #match/replace the version and port
    for k,v in INSTALL_VERSION_PORT.items():
        warppedKey='{%s}' % k
        if re.search(warppedKey, sourceStr) is not None:
            sourceStr = re.sub(warppedKey, v, sourceStr)

    return sourceStr


def environmentCheck():
    #TO DO: check the install environment 
    #here we think this is ok
    logtoFile('the environment is OK. \n',MODE_APPEND)
    return True


def install():
    for cmd in INSTALL_COMMANDS:
        cmd_parser(cmd)


def runInstance():
    [cmd_parser(cmd) for cmd in RUN_REDIS_SERVER_COMMANDS]
    


if __name__ == '__main__':

    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("+                      redis-automatic install script (python)                        +")
    print("+------------------------------------------------------------————---------------------+")
    print("+ !Warning: you can run the install script to install any version and run at any port +")
    print("+           you must install just an instance per server ***Strongly recommended***   +")
    print("+------------------------------------------------------------————---------------------+")    
    print("+before you run the script,you shold make sure the premise below:                     +")
    print("+ 1: the latest released <gcc> is a must!                                             +")
    print("+ 2: the latest released <make> is a must!                                            +")
    print("+ 3: the latest release <tcl> is a must!                                              +")
    print("+ 4: the <Python3> is a must! and python (3.3.0) is a plus                            +")
    print("+ And you may provide sereval params (if you choose customize mode) which list as:    +")
    print("+ (1) version num: the version number which you want to download(2.6.9 as a default)  +")
    print("+ (2) port: the port which you wish the redis-server run at(6379 as a default)        +")
    print("+ Are you ready? here we go!                                                          +")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print()

    while True:
        stepContinue =input("make sure you will uninstall the redis. Entner (y/n) to continue:  ")
        if stepContinue   == 'y':
            break
        elif stepContinue == 'n':
            warn("the uninstall has been stoped")
            exit(0)         #return 0:normal        1:error

    installMode =input("default install mode or customize install mode? Enter (d/c) to continue:  ")

    global INSTALL_VERSION_PORT
    if installMode == 'c':
        INSTALL_VERSION_PORT['VERSION_NUM'] =input("please enter the version number(format like X.X.X):")
        INSTALL_VERSION_PORT['PORT_NUM']     =input("please enter the port :")

    notice("the log file will write under /home .\nyou must give current user write permission:\n")
    CMD_CHMOD_HOMEDIR_W ="sudo chmod o+w /home"
    process =subprocess.Popen(CMD_CHMOD_HOMEDIR_W, shell=True, universal_newlines=True, stdout=subprocess.PIPE)
    process.wait()

    #pre-process paths
    global PROCESSED_PATHS
    PROCESSED_PATHS = preProcessPaths()

    logtoFile('install redis %s \n' % time.strftime(' at %c'),MODE_WRITE)
    if environmentCheck():
        #install
        notice("the install script is running. please wait several minutes")
        install()
        notice("the install script has run. Everything has log at path: %s" % PRE_PROCESSING_PATHS['LOGFILE_PATH'])

        #run
        runInstanceOrNot = input("would you like to run the redis server now? Enter (y/n) to continue:  ")
        if runInstanceOrNot == 'y':
            runInstance()
            notice("the redis server has run at port: %s." % INSTALL_VERSION_PORT['PORT_NUM'])
            notice("All of things have done. you can enter:redis-cli -p %s  to test! " % INSTALL_VERSION_PORT['PORT_NUM'])
        else:
            exit(0)                     #exit

    else:
        warn("the environment has some problem. the install script can not run.")

