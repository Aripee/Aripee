# -*- coding: utf-8 -*-
# CiscoSAPCAPマクロ

import time
import csCom
import sys
import os

if __name__ == '__main__':
    submitData = ''
    noInventory = False
    csCom.modelType = 'AP'

    # 引数1:デバイス
    if len(sys.argv) > 1:
        csCom.ciscoInit(sys.argv[1])
    else:
        csCom.ciscoInit('/dev/ttyUSB0')
    # 引数2:案件名
    if len(sys.argv) > 2:
        caseName = sys.argv[2]
    else:
        caseName = 'unknown'
    csCom.addCaseName(caseName)
    # 引数3:部署
    if len(sys.argv) > 3:
        if sys.argv[3] == 'chotatsu2':
            techType = 'chotatsu'
            csCom.isPortCheck = True
        elif sys.argv[3] == 'houjin':
            techType = sys.argv[3]
            csCom.isPortCheck = True
        else:
            techType = sys.argv[3]
    else:
        techType = 'chotatsu'
    csCom.setTechType(techType)
    # 引数4:モード
    if len(sys.argv) > 4:
        csCom.actionMode = sys.argv[4]
    csCom.setStatus('wait')
    # 案件名がdebugの場合はブートローダをスキップ
    if (caseName != 'debug') and (csCom.actionMode != 'fast'):
        print("\n\n\n-----Waiting AP-----")
        csCom.eraserCommon.serialOutMode = True
        readData, readRes = csCom.ciscoWaitStr('button to be released')
        csCom.ciscoWaitStr('ap:', csCom.startWaitTime)
        csCom.setStatus('erase')
        print("------Start erase-----")
        csCom.eraserCommon.serialOutMode = True
        flashInit = True
        while(flashInit):
            csCom.ciscoSend('flash_init')
            readData, readRes = csCom.ciscoWaitStr('The flash is already initialized')
            time.sleep(1)
            if 'interrupted' in readData:
                flashInit = True
            else:
                flashInit = False
            csCom.ciscoSend('dir flash:')
            csCom.ciscoRead()
            csCom.ciscoSend('reset')
            csCom.ciscoWaitStr('(y/n)?', 10)
            csCom.ciscoSend('y')  
            print("-----Booting IOS-----")
            readData, readRes = csCom.ciscoWaitStr('Press RETURN', csCom.bootWaitTime)
    if readRes == 'TO':
        print("!!!---Bootエラー検知---!!!")
        csCom.setStatusErr('err04')
    elif caseName == 'debug':
        csCom.setStatus('erase')
        csCom.setDebugMode(True)
        csCom.eraserCommon.serialOutMode = True
        csCom.ciscoSend('\r\n')
    if csCom.actionMode == 'fast':
        csCom.eraserCommon.serialOutMode = True
        print("-----Boot Waiting...-----")
        readData, readRes = csCom.ciscoWaitStr('Press RETURN', csCom.startWaitTime)
        if readRes == 'TO':
            print("!!!---Bootエラー検知---!!!")
            csCom.setStatusErr('err04')
            exit(4)
    time.sleep(10)
    csCom.ciscoSend('\r\n')
    csCom.ciscoRead()
    if csCom.entersapcapLogin():
        pass
    else:
        print('!!!---Loginすることができませんでした---!!!')
        csCom.setStatusErr('err04')
        exit(4)
    if csCom.entersapcapEnable():
        pass
    else:    
        print('!!!---Enableにすることができませんでした---!!!')
        csCom.setStatusErr('err04')
        exit(4)
    csCom.ciscoRead()
    csCom.ciscoSend('terminal length 0')
    csCom.ciscoRead()
    csCom.ciscoSend('clear capwap private-config')
    csCom.ciscoWaitStr('#', 10)
    csCom.ciscoSend('\r\n')
    csCom.ciscoRead()
    csCom.ciscoSend('dir all')
    time.sleep(5)
    dirAllData, dirAllRes = csCom.ciscoWaitStr('flash:/', 10)
    if dirAllRes:
        fileList = csCom.getFileList(dirAllData)
        csCom.fileErasure(fileList)
    csCom.ciscoSend('delete /f /r flash:env_vars')
    csCom.ciscoWaitStr('#', 10)
    csCom.ciscoSend('delete /f /r flash:capwap-saved-config')
    csCom.ciscoWaitStr('#', 10)
    csCom.ciscoSend('delete /f /r flash:capwap-saved-config-bak')
    csCom.ciscoWaitStr('#', 10)
    csCom.flashCheck(dirAllData)
    time.sleep(10)
    csCom.ciscoSend('\r\n')
    csCom.ciscoRead()
    csCom.failCheck()
    csCom.ciscoSend('reload')
    csCom.ciscoWaitStr('?')
    csCom.ciscoRead()
    csCom.ciscoSend('\r\n')
    print("------Reload Router-----")
    csCom.ciscoWaitStr('Press RETURN', csCom.bootWaitTime)
    time.sleep(10)
    csCom.ciscoSend('\r\n')
    csCom.ciscoRead()
    if csCom.entersapcapLogin():
        pass
    else:
        print('!!!---Loginすることができませんでした---!!!')
        csCom.setStatusErr('err04')
        exit(4)
    if csCom.entersapcapEnable():
        pass
    else:    
        print('!!!---Enableにすることができませんでした---!!!')
        csCom.setStatusErr('err04')
        exit(4)
    csCom.ciscoRead()
    csCom.ciscoSend('terminal length 0')
    csCom.ciscoRead()
    print("------Collecting data-----")
    csCom.ciscoSend('show inventory')
    invData, invRes = csCom.ciscoWaitStr('#', 10)
    if  (invRes == 'OK') and ('Invalid' and ':' not in invData):
        print('!!!---show inventoryへのレスポンスがありません---!!!')
        csCom.setStatusErr('err04')
        exit(4)
    elif (invRes == 'OK') and ('Invalid' not in invData):
        csCom.ciscoGetInfo(invData)
        invDicList = csCom.shapeInvData(invData)
        invPid = csCom.extDicList(invDicList, 'NAME', 'AP', 'PID')
        invSn = csCom.extDicList(invDicList, 'NAME', 'AP', 'SN')
        if (invPid != '') and (invSn != ''):
            csCom.modelNum = invPid
            csCom.serialNum = invSn
        else:
            noInventory = True
    else:
        noInventory = True
    submitData = submitData + invData
    csCom.ciscoSend('show version')
    verData, verRes = csCom.ciscoWaitStr('#', 50)
    submitData = submitData + verData
    csCom.genRawLogName()
    csCom.ciscoSend('dir all')
    readData, readRes = csCom.ciscoWaitStr('#', 10)
    submitData = submitData + readData
    csCom.ciscoSend('show boot')
    readData, readRes = csCom.ciscoWaitStr('#', 10)
    submitData = submitData + readData
    csCom.ciscoSend('show interfaces')
    readData, readRes = csCom.ciscoWaitStr('#', 10)
    submitData = submitData + readData
    csCom.ciscoSend('show running-config')
    readData, readRes = csCom.ciscoWaitStr('\nend', 60)
    submitData = submitData + readData
    csCom.getInterface(readData)
    time.sleep(5)
    csCom.ciscoRead()
    csCom.ciscoSend('clear logging')
    csCom.ciscoRead()
    csCom.ciscoSend('\r\n')
    csCom.ciscoRead()
    csCom.failCheck()
    csCom.checkTermRes()
    if noInventory:
        print('!!!---IOSバージョンが古いため手動でPID,SNを入力てください---!!!')
        modNum = input('PID> ')
        serNum = input('SN> ')
        csCom.changeLogName(modNum, serNum)
    if len(csCom.modelNum) > 0:
        submitDir = 'submit/' + caseName
        if not os.path.exists(submitDir):
            os.makedirs(submitDir)
        with open(submitDir + '/' + csCom.modelNum + '#' + csCom.serialNum + ".txt", 'w') as submitFile:
            submitFile.write(submitData)
        if len(csCom.errorList) == 0:
            csCom.setStatusComp()
            print("#############################################")
            print("#############   Complete!  ##################")
            print("#############################################")
        else:
            print('!!!### Error Detect ###!!!')
            csCom.setStatusErr('err05')
            exit(5)
        if csCom.getDebugMode():
            csCom.setStatusErr('normal', 'complete')
            exit(-1)
    else:
        print("!!!---正常にデータを取得できていません---!!!")
        csCom.setStatusErr('err03')
        exit(3)
