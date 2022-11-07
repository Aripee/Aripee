# -*- coding: utf8 -*-
# 検査自動化ソフト用CUIインターフェース

import subprocess
import os
from serial.tools import list_ports
import re

#subprocess.call('mode 45,8', shell=True)
subprocess.call('title "Waiting input"', shell=True)
caseName = input('案件名入力> ').lower()

#portName = input('Port Name(COMxx or /dev/ttyXXX)> ')
ports = list_ports.comports()
devices = [info.device for info in ports]
devices = sorted(devices, key=lambda s: int(re.search(r'\d+', s).group()))
for i in range(len(devices)):
    print("%3d: open %s" % (i, devices[i]))
print("使用するポートを選択> ")
portNum = int(input())
portName = devices[portNum]

devType = [
    ['CiscoSwitch', 'ciscoMacro.py'],
    ['CiscoSwitch2(C36,38)', 'ciscoMacro.py', 'c3638'],
    ['CiscoSwitch3(C4900)', 'ciscoMacro.py', 'c4900'],
    ['CiscoRouter', 'routerMacro.py'],
    ['CiscoASA', 'ciscoAsa.py'],
    ['CiscoAP(SAP/CAP)', 'ciscoSapcap.py'],
    ['CiscoSwitch(Fast Mode)', 'ciscoMacro.py', 'fast'],
    ['Juniper SRX', 'jnpSeq.py']
]
for i in range(len(devType)):
    print("%3d: open %s" % (i, devType[i][0]))
print("デバイスタイプを選択> ")
devNum = int(input())
exeMacro = devType[devNum][1]
macroMode = ''
if len(devType[devNum]) >= 3:
    macroMode = devType[devNum][2]

techList = ['情報セキュリティ', '品質検査', '情報セキュリティ(ポートチェック有)']
for i in range(len(techList)):
    print(i, techList[i])
print("どの技術？> ")
techStr = input()
if len(techStr) > 0:
    if techStr == '0':
        techType = 'chotatsu'
    elif techStr == '1':
        techType = 'houjin'
    elif techStr == '2':
        techType = 'chotatsu2'
else:
    techType = 'chotatsu'

if os.name == 'nt':
    callProgram = "python " + exeMacro + " " + portName + " " + caseName + " " + techType + " " + macroMode + " 2>> " + portName + "ERR.log"
else:
    callProgram = "python3 " + exeMacro + " "  + portName + " " + caseName + " " + techType + " " + macroMode

while(True):
    cmdTitle = 'title Erasing. Port: ' + portName
    subprocess.call(cmdTitle, shell=True)
    rcp = subprocess.call(callProgram, shell=True)

    if rcp != 0:
        print("--Error!--")
        input("エラーによりプログラムが終了しました。")
    elif macroMode == 'c4900' or macroMode == 'fast':
        print('nを入力してからEnterで次の検査へ ')
        while True:
            keyIn = input()
            if keyIn == 'n':
                break
