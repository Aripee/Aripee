# -*- coding: utf8 -*-
'''
自動データ消去プログラム
    Cisco共通ライブラリ
'''

# 標準ライブラリ
import atexit
import time
import random, string
import re
import sys
import socket
import csv
import os

# 共通ライブラリ
import eraserCommon
import readchar

# グローバル変数
modelNum = ''
serialNum = ''
modelType = 'SW'
modelSeries = ''
stackNumber = 1
errorList = []
orgModelNum = ''
startWaitTime = 90000
bootWaitTime = 420
interfaceList = []
actionMode = ''
isPortCheck = False

# 初期化関数
def ciscoInit(portName):
    #global serialPort

    eraserCommon.setStartTime()
    if not eraserCommon.initializeCommon(portName, 9600, False):
        print("Error(Cisco): Initialize error.")
        setStatusErr('err01')
        exit(1)

    atexit.register(eraserCommon.endProcess)
    print("Open serial port %s." % (portName))

# 受信関数
def ciscoRead():
    readData, readRes = eraserCommon.readSerialPort()
    if not readRes:
        return '', False
    moreLoop = True
    moreRead = readData
    moreRes = readRes
    while(moreLoop):
        if '-- MORE --' in moreRead or '--More--' in moreRead:
            ciscoSend(' ')
            time.sleep(0.5)
            moreRead, moreRes = eraserCommon.readSerialPort()
            readData = readData + moreRead
            if not readRes:
                return '', False
        else:
            moreLoop = False
    # Error Check
    if errorDetect(readData):
        print('!!!---Error検知---!!!')

    return readData, True

# コマンド送信
def ciscoSend(command):
    eraserCommon.writeSerialPort(command)
    time.sleep(0.2)
    return True

# 文字列待機関数
def ciscoWaitStr(waitStr, timeout=100, blink_led = False):
    readData = ''
    for readCnt in range(timeout):
        if blink_led:
            blink_blue()
        readBuff, readRes = ciscoRead()
        readData = readData + readBuff
        if not readRes:
            return '', 'Err'
        if waitStr in readData:
            break
        else:
            time.sleep(1)
    if readCnt == (timeout-1):
        waitRes = 'TO'
    else:
        waitRes = 'OK'
    return readData, waitRes

# rommon待機関数
def routerWait(waitStr, timeout=5000, sendKey = ''):
    readData = ''
    for readCnt in range(timeout):
        if sendKey == '':
            eraserCommon.sendBreak()
            eraserCommon.sendLowData(' ')
        else:
            eraserCommon.sendLowData(sendKey)
        blink_blue()
        readBuff, readRes = ciscoRead()
        readData = readData + readBuff
        if not readRes:
            return '', 'Err'
        if waitStr in readData:
            break
        else:
            time.sleep(1)
    if readCnt == (timeout-1):
        waitRes = 'TO'
    else:
        waitRes = 'OK'
        lit_blue()
    return readData, waitRes

# キーを入力するまで受診を続ける
def readAndBreak(waitKey):
    readData = ''
    inputKey = 0
    while 1:
        if inputKey == -1:
            readBuff = ''
            readRes = True
        else:
            readBuff, readRes = ciscoRead()
            readData = readData + readBuff
        if '#' not in readBuff and inputKey != -1:
            ciscoSend('\r\n')
            time.sleep(0.5)
            ciscoSend('\r\n')
            time.sleep(0.5)
            ciscoSend('\r\n')
            time.sleep(0.5)
            enterEnable()
        if not readRes:
            return '', 'Err'
        try:
            inputKey = ord(readchar.readkey())
        except:
            inputKey = -1
        if inputKey == waitKey:
            break
        elif inputKey == 115:
            ciscoSend('\n')
            time.sleep(0.1)
            readBuff, readRes = ciscoRead()
            readData = readData + readBuff
            time.sleep(0.1)
            ciscoSend('show interface status')
        elif inputKey == -1:
            pass
        else:
            ciscoSend(' ')
            if actionMode == 'c4900':
                ciscoSend('\n')
                time.sleep(0.5)
                readBuff, readRes = ciscoRead()
                readData = readData + readBuff
                time.sleep(0.5)
                ciscoSend('show interfaces status | include connected')
    return readData, 'OK'


# APlogin関数
def entersapcapLogin():
    global modelType
    APloginComplete = False
    
    for cnt in range(5):
        ciscoSend('\r\n')
        ciscoRead()
        ciscoSend('\r\n')
        ciscoWaitStr('Username:', 10)
        print("----------Login----------")
        ciscoSend('Cisco')
        ciscoWaitStr('Password:', 10)
        ciscoSend('Cisco')
        ciscoSend('\r\n')
        readData, readRes = ciscoWaitStr('>', 5)
        if readRes == 'OK':
            APloginComplete = True
            break
    return APloginComplete


# APenable遷移関数Pass入力
def entersapcapEnable():
    global modelType
    APenableComplete = False
    
    for cnt in range(5):
        ciscoWaitStr('>', 10)
        print("----------Enable----------")
        ciscoSend('enable')
        ciscoWaitStr('Password:', 10)
        ciscoSend('Cisco')
        ciscoSend('\r\n')
        readData, readRes = ciscoWaitStr('#', 5)
        if readRes == 'OK':
            APenableComplete = True
            break
    return APenableComplete


# enable遷移関数
def enterEnable():
    global modelType
    isComplete = False

    for cnt in range(5):
        ciscoSend('enable')
        ciscoSend('\r\n')
        readData, readRes = ciscoWaitStr('#', 5)
        if readRes == 'OK':
            isComplete = True
            break
    return isComplete


# ターミナルからのレスポンスがあるかの確認
def checkTermRes():
    ciscoRead()
    ciscoSend('\n')
    read_data, read_res = ciscoRead()
    if "#" in read_data:
        return
    if enterEnable():
        pass
    else:
        print('!!!---Enableにすることができませんでした---!!!')
        setStatusErr('err04')
        exit(4)


# 機器情報取得関数
def ciscoGetInfo(data):
    global modelNum
    global serialNum
    global modelType
    global orgModelNum
    existProductNum = False
    existSerialNum = False
    modelDecsStr = 'model number'
    serialDecsStr = 'system serial number'
    oldModelNum = ''

    if modelType == 'RT':
        modelDecsStr = 'pid:'
        serialDecsStr = 'sn:'

    if modelDecsStr in data.lower():
        existProductNum = True
    if serialDecsStr in data.lower():
        existSerialNum = True

    if existProductNum or existSerialNum:
        dataLists = data.splitlines()
        for dataList in dataLists:
            if 'model number' in dataList.lower():
                productList = dataList.split(':')
                orgModelNum = productList[1].strip()
                modelNum = re.sub('[/;:,*?<>|]', '_', productList[1].strip())
            if 'system serial number' in dataList.lower():
                serialList = dataList.split(':')
                serialNum = serialList[1].strip()
            if 'PID:' in dataList:
                productList = re.split('\s{1,}', dataList)
                if len(productList[1]) > 2:
                    oldModelNum = modelNum
                    orgModelNum = productList[1].strip()
                    modelNum = re.sub('[/;:,*?<>|]', '_', productList[1].strip())
                if 'CHASSIS' in oldModelNum:
                    if '39' in modelNum:
                        if 'SPE250' in modelNum:
                            oldModelNum = re.sub('[0-9]{4}', '3945E', oldModelNum)
                        elif 'SPE200' in modelNum:
                            oldModelNum = re.sub('[0-9]{4}', '3925E', oldModelNum)
                        elif 'SPE150' in modelNum:
                            oldModelNum = re.sub('[0-9]{4}', '3945', oldModelNum)
                        elif 'SPE100' in modelNum:
                            oldModelNum = re.sub('[0-9]{4}', '3925', oldModelNum)
                    if 'K9' in modelNum:
                        modelNum = oldModelNum.replace('-CHASSIS', '_K9')
                    elif 'K8' in modelNum:
                        modelNum = oldModelNum.replace('-CHASSIS', '_K8')
                if ('CISCO' in modelNum) or ('Cisco' in modelNum):
                    pass
                elif (oldModelNum != ''):
                    modelNum = oldModelNum.replace('C', 'CISCO')
            if 'SN:' in dataList:
                serialList = re.split('\s{1,}', dataList)
                if (len(serialList)-1) >= serialList.index('SN:'):
                    extractSerNum = serialList[serialList.index('SN:')+1].strip()
                    serialNum = extractSerNum
                else:
                    extractSerNum = ''
            if (modelNum != '') and (serialNum != ''):
                if 'CHASSIS' in modelNum:
                    pass
                else:
                    break

# rawLogName生成
def genRawLogName():
    if (modelNum == '') and (serialNum == ''):
        eraserCommon.rawLogName = eraserCommon.rawLogName + '_Unknown' + randomname(5)
    elif modelNum == '':
        eraserCommon.rawLogName = eraserCommon.rawLogName + '_Unknown' + randomname(5) + '#' + serialNum
    elif serialNum == '':
        eraserCommon.rawLogName = eraserCommon.rawLogName + '_' + modelNum + '#Unknown' + randomname(5)
    else:
        eraserCommon.rawLogName = eraserCommon.rawLogName + '_' + modelNum + '#' + serialNum

# ファイルシステム情報取得関数
def getFileList(dirAllRes):
    fileList = []
    fileSysName = ''
    dirAllList = dirAllRes.splitlines()
    for data in dirAllList:
        tmpList = re.split('\s{1,}', data)
        if ':/' in data:
            fileSysName = tmpList[-1]
        if len(tmpList) >= 7:
            tmpList[0] = fileSysName.replace('/', '')
            fileList.append(tmpList)
    return fileList

# ライセンス情報取得
def ciscoGetLicense(data):
    licenseList = []
    licenseName = ''
    licenseCnt = -1
    dataList = data.splitlines()
    for line in dataList:
        tmpList = line.split(":")
        if 'Feature' in line:
            licenseCnt = licenseCnt + 1
            licenseName = tmpList[-1].strip()
            licenseList.append({'Feature': licenseName})
        elif 'Router#' in line:
            break
        elif len(line) < 1:
            pass
        elif len(tmpList) > 1:
            licenseList[licenseCnt].setdefault(tmpList[0].strip(), tmpList[1].strip())
        else:
            pass
    return licenseList

# ライセンスによる型番変更
def changeProductNum(lists):
    global modelNum
    global orgModelNum
    instNum = ''
    for licenseDic in lists:
        if 'License Type' in licenseDic:
            if ('39' in modelNum) | ('29' in modelNum) | ('19' in modelNum):
                if ('securityk9' in licenseDic['Feature']) and (licenseDic['License Type'] == 'Permanent'):
                    if instNum == '-V':
                        instNum = '-VSEC'
                    else:
                        instNum = '-SEC'
                if ('hseck9' in licenseDic['Feature']) and (licenseDic['License Type'] == 'Permanent'):
                    instNum = '-HSEC+'
            if ('39' in modelNum) | ('29' in modelNum):
                if ('cme-srst' in licenseDic['Feature']) and (licenseDic['License Type'] == 'Permanent'):
                    instNum = '-CME-SRST'
                if ('uck9' in licenseDic['Feature']) and (licenseDic['License Type'] == 'Permanent'):
                    if instNum == '-SEC':
                        instNum = '-VSEC'
                    else:
                        instNum = '-V'
    #print(instNum)
    if instNum != '':
        if 'K9' in modelNum:
            instIndex = eraserCommon.rawLogName.find('K9') - 1
        if 'K8' in modelNum:
            instIndex = eraserCommon.rawLogName.find('K8') - 1
        eraserCommon.rawLogName = eraserCommon.rawLogName[:instIndex] + instNum + eraserCommon.rawLogName[instIndex:]
        orgModelNum = eraserCommon.rawLogName.replace('_', '/')

# show inventoryの中身を成形
def shapeInvData(data):
    splitData = data.splitlines()
    invInfo = []
    invDicList = []
    for line in splitData:
        elements = line.split(',')
        for element in elements:
            invInfo.append(element.replace('\"', '').split(":"))
    dicElem = {}
    for invElem in invInfo:
        if len(invElem) > 1:
            dicElem.update([(invElem[0].strip(), invElem[1].strip())])
        elif len(invElem) == 1:
            if invElem[0] == '':
                invDicList.append(dicElem)
                dicElem = {}
    return invDicList

# dicListから指定情報を抽出
def extDicList(dicList, searchKey, searchValue, outKey):
    for listElem in dicList:
        if searchKey in listElem:
            if searchValue.lower() in listElem[searchKey].lower():
                return listElem[outKey]
    return ''


# BundleMode check
def is_bundle_mode(str_showver):
    is_bundle, os_ver = check_bundle_and_ver(str_showver)
    if is_bundle:
        return True
    else:
        return False


def check_bundle_and_ver(data):
    data_lines = data.splitlines()
    bundle_data_list = [data_line for data_line in data_lines if 'bundle' in data_line.lower()]
    is_bundle = False
    os_ver = 'other'
    for bundle_data in bundle_data_list:
        if '03.' in bundle_data:
            is_bundle = True
            os_ver = '03.'
        else:
            is_bundle = True
    return is_bundle, os_ver


# BundleMode to InstallMode
def bundle_to_install(os_ver = '03.', ver_data = ''):
    global errorList
    if enterEnable():
        if os_ver == '03.':
            osfile_path = get_osfile_path(ver_data)
            ciscoSend('software expand running to flash:')
        else:
            osfile_path = get_osfile_path(ver_data)
            if len(osfile_path) >= 0:
                ciscoSend('dir ' + osfile_path)
                ciscoRead()
                ciscoSend('request platform software package expand switch all file ' + osfile_path)
                #ciscoSend('req p s pac e s all f ' + osfile_path)
        ciscoWaitStr('Switch#', 12000)
        ciscoSend('dir flash:/packages.conf')
        dirData, dirRes = ciscoWaitStr('Switch#', 10)
        if '%%Error' in dirData:
            print('!!!ERROR. Not Exist packages.conf!!!')
            errorList.append("Not exist packages.conf")
            return False
        ciscoSend('configure terminal')
        ciscoRead()
        ciscoSend('no boot system')
        ciscoRead()
        ciscoSend('boot system flash:/packages.conf')
        ciscoRead()
        ciscoSend('exit')
        ciscoWaitStr('Switch#', 10)
        ciscoSend('write memory')
        ciscoWaitStr('Switch#', 10)
        time.sleep(10)
        ciscoSend('reload')
        ciscoSend('\n')
        readData, readRes = ciscoWaitStr('System Serial Number', startWaitTime)
        time.sleep(10)
        ciscoSend('no')
        ciscoRead()
        time.sleep(5)
        ciscoSend('no')
        ciscoRead()
        if readRes == 'TO':
            print("!!!---Bootエラー検知---!!!")
            setStatusErr('err04')
            exit(4)
        time.sleep(10)
        ciscoSend('\r\n')
        #ciscoWaitStr('? [y', 10)
        #ciscoSend('no')
        #ciscoWaitStr('? [y', 10)
        #ciscoSend('no')
        if enterEnable():
            ciscoSend('terminal length 0')
            return True
        else:
            print('!!!--Can not enter Enable Mode!!--!!!')
            setStatusErr('err04')
            exit(4)
    else:
        print('!!!--Can not enter Enable Mode!--!!!')
        setStatusErr('err04')
        exit(4)


def get_osfile_path(ver_data):
    data_lines = ver_data.splitlines()
    osfile_data_list = [data_line for data_line in data_lines if 'system image file' in data_line.lower()]
    osfile_path = re.search(r'"(.+)"',osfile_data_list[0]).group(1)
    return osfile_path


# ログ名変更
def changeLogName(modNum, serNum):
    global modelNum
    global orgModelNum
    global serialNum
    modelNum = re.sub('[/;:,*?<>|]', '_', modNum)
    orgModelNum = modNum
    serialNum = serNum
    eraserCommon.rawLogName = eraserCommon.rawLogName + '_' + modelNum + '#' + serialNum

# ファイル消去関数
def fileErasure(fileList):
    if len(fileList) <= 0:
        return False

    delCondList =  [
        ['flash', 'vlan.dat'],
        ['flash', '.backup$'],
        ['flash', '.log$'],
        ['flash', '.old$'],
        ['flash', '.debug$'],
        ['flash', '.renamed$'],
        ['flash', '_config'],
        ['flash', 'Archive'],
        ['flash', '.txt'],
        ['flash', '_recovery'],
        ['flash', '^pnp-tech'],
        ['flash', '^crashinfo'],
        ['flash', '.cfg$']
    ]

    for delCond in delCondList:
        for fileInfo in fileList:
            searchRes1 = re.search(delCond[0], fileInfo[0])
            searchRes2 = re.search(delCond[1], fileInfo[-1])
            if searchRes1 and searchRes2:
                if "d" in fileInfo[2]:
                    ciscoSend('delete /f /r ' + fileInfo[0] + fileInfo[-1])
                else:
                    ciscoSend('delete /f ' + fileInfo[0] + fileInfo[-1])
                ciscoSend('\r\n')
                ciscoWaitStr('Switch#', 10)
    return True

# flashチェック関数
def flashCheck(resDirAll):
    global errorList
    if '%%error' in resDirAll.lower():
        eraserCommon.rawLogName = eraserCommon.rawLogName + '-ERR'
        errorList.append("Flash Failed")
        setStatusErr('err05')
        print('!!!---Flashエラー検知---!!!')
        exit(5)

# stack-numberの取得
def getStackNumber(showRunRes):
    global stackNumber
    showRunList = showRunRes.splitlines()
    for data in showRunList:
        if 'switch' in data:
            tmpList = re.split('\s{1,}', data)
            if tmpList[0] == "switch":
                if int(tmpList[1]) > 1 :
                    stackNumber = tmpList[1]
                    break
    return stackNumber


# show verからライセンスを確認する関数
def get_license_from_showver(showver_res):
    license_dict = {"license level":"unknown", "license type":"unknown", "next reload license level":"unknown"}
    showver_list = showver_res.splitlines()
    for data in showver_list:
        if 'license level' in data.lower():
            data_current_license = data.split(': ')
            license_dict['license level'] = data_current_license[1]
        if 'license type' in data.lower():
            data_current_license = data.split(': ')
            license_dict['license type'] = data_current_license[1]
        if 'next reload license level' in data.lower():
            data_current_license = data.split(': ')
            license_dict['next reload license level'] = data_current_license[1]
    if license_dict['license level'] == "unknown":
        for data in showver_list:
            if 'lanbase' in data.lower():
                license_dict['license level'] = 'lanbase'
            elif 'ipbase' in data.lower():
                license_dict['license level'] = 'ipbase'
            elif 'ipservices' in data.lower():
                license_dict['license level'] = 'ipservices'
    return license_dict


# 型番とライセンスの一致を確認する関数(3750,3560用)
def check_license_match(license_dict):
    global modelNum
    model_base_license = "unknown"
    if "L" == modelNum[-1]:
        model_base_license = "lanbase"
    elif "S" == modelNum[-1]:
        model_base_license = "ipbase"
    elif "E" == modelNum[-1]:
        model_base_license = "ipservices"
    if model_base_license == license_dict['license level'].lower():
        return True
    else:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!!!!!!!!!!Caution!!!!!!!!!!!!!!")
        print("!!!ライセンスが一致していません!!!!")
        print("型番:"+modelNum+" に対しライセンス:"+license_dict['license level'])
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("Enterを押して続行")
        input("")
        enterEnable()
        return False


# Switch用のライセンス情報確認（旧Ver.）
def checkSwitchLicense(showVerRes):
    global modelNum
    global actionMode
    insertModelNum = ''
    showVerList = showVerRes.splitlines()
    lowerShowVer = showVerRes.lower()
    if actionMode == 'c4900':
        if ('cat4500-ipbase' in lowerShowVer) or ('cat4000-i9' in lowerShowVer):
            insertModelNum = '-S'
        elif ('cat4500-entservices' in lowerShowVer) or ('cat4000-i5' in lowerShowVer):
            insertModelNum = '-E'
    else:
        for data in showVerList:
            if 'lanbase' in data.lower():
                insertModelNum = 'L'
            elif 'ipbase' in data.lower():
                insertModelNum = 'S'
            elif 'ipservices' in data.lower():
                insertModelNum = 'E'
    if insertModelNum != '':
        if ('3750X' in modelNum) or ('3560X' in modelNum):
            modelNum = modelNum[:-1] + insertModelNum
            endOfModelNum = eraserCommon.rawLogName.find("#") - 1
        elif ('3850' in modelNum) or ('3650' in modelNum):
            modelNum = modelNum + '-' + insertModelNum
            endOfModelNum = eraserCommon.rawLogName.find("#")
        if actionMode == 'c4900':
            modelNum = modelNum + insertModelNum
            endOfModelNum = eraserCommon.rawLogName.find("#")

# interface一覧取得関数
def getInterface(showRunRes):
    global interfaceList
    showRunList = showRunRes.splitlines()
    for data in showRunList:
        if 'interface' in data:
            tmpList = re.split('\s{1,}', data)
            interfaceList.append(tmpList[1])
    return interfaceList

# interfaceポート状態一括変更関数
def changeInterfaceState(shutState, mdixState = ''):
    global interfaceList
    ciscoSend('config terminal')
    ciscoWaitStr('(config)', 10)
    for interface in interfaceList:
        ciscoSend('interface ' + interface)
        ciscoSend(shutState)
        if mdixState != '':
            ciscoSend(mdixState)
        ciscoSend('exit')
        ciscoWaitStr('(config)', 10)
    ciscoSend('exit')
    time.sleep(1)
    ciscoRead()

# Config確認関数

# 提出用ログ生成関数

# 生ログファイルの案件名追加
def addCaseName(caseName):
    if caseName != "":
        eraserCommon.rawLogName = eraserCommon.rawLogName + "_" + caseName

# Failチェック関数
def failCheck():
    global errorList
    if ('POST Failed' in eraserCommon.rawLog) or ('Status Failed' in eraserCommon.rawLog):
        ciscoSend('show version')
        verData, verRes = ciscoWaitStr('Configuration register', 30)
        if verRes == 'OK':
            ciscoGetInfo(verData)
            genRawLogName()
        eraserCommon.rawLogName = eraserCommon.rawLogName + '-ERR'
        errorList.append("Post Failed")
        setStatusErr('err05')
        print('!!!---Postエラー検知---!!!')
        exit(5)
    if ('mbist failed' in eraserCommon.rawLog.lower()):
        eraserCommon.rawLogName += '-MBISTERR'
        print('!!!---MBIST Fail検知---!!!')
        errorList.append("MBIST Failed")
        setStatusErr('err05')
    if 'Battery Failed' in eraserCommon.rawLog:
        eraserCommon.rawLogName = eraserCommon.rawLogName + '-BTRYERR'
        print('!!!---Battery Fail検知---!!!')
        errorList.append("Battery Failed")
        eraserCommon.setState('ErrorList', errorList)

# ダンダムな文字列生成
def randomname(n):
    randlst = [random.choice(string.ascii_letters + string.digits) for i in range(n)]
    return ''.join(randlst)

# エラー検知
def errorDetect(data):
    global errorList
    if 'Error loading' in data:
        errorList.append('Error loading')
        return True
    return False

# デバッグモード設定
def setDebugMode(mode):
    if mode == True:
        eraserCommon.debugMode = True
    elif mode == False:
        eraserCommon.debugMode = False

# デバッグモード状態取得
def getDebugMode():
    return eraserCommon.debugMode

# 技術モード設定
def setTechType(setStr):
    if setStr != '':
        eraserCommon.techType = setStr

# ステータス変更
def setStatus(crrStat):
    eraserCommon.setState("CurrentStatus", crrStat)
    if crrStat == "erase":
        lit_blue()

# 正常終了時のステータス変更
def setStatusComp():
    eraserCommon.setState('CurrentStatus', 'complete')
    eraserCommon.setState('EndStatus', 'normal')
    unlit_led()

# エラー時のステータス変更
def setStatusErr(endStat, crrStat = "error"):
    global errorList
    eraserCommon.setState('ErrorList', errorList)
    eraserCommon.setState('CurrentStatus', crrStat)
    eraserCommon.setState('EndStatus', endStat)
    lit_red()
    time.sleep(10)


# プログラム終了関数
def exit_prog(error_code):
    if error_code != 0:
        print("エラーが発生しました。Ctrl+cでプログラムを終了させてください。")
        while True:
            # ここの処理考える
            pass
    exit(error_code)


# LEDインジケータ
# 青点灯
def lit_blue():
    eraserCommon.led_control(False, True)


# 赤点灯
def lit_red():
    eraserCommon.led_control(True,False)


# 消灯
def unlit_led():
    eraserCommon.led_control(True, True)


# 青点滅
def blink_blue():
    lit_blue()
    time.sleep(0.5)
    unlit_led()

