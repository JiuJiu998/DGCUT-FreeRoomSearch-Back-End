# 全自动获取roomBase_with_schedule.json
import base64
import configparser
import os
import shutil
import time
import urllib
from datetime import datetime

import ddddocr
import requests
from lxml import etree

from CourseTableParser import CourseTableParser
from ScheduleParser import ClassScheduleProcessor
from utils import read_class_room_data, convert_to_json, save_json_to_file


# 1、登录并获取全校课表 kebiao.html
# 2、根据“七号楼教室一览表.xlsx"生成roomBase.json
# 3、解析kebiao.html为table.json
# 4、结合roomBase.json和table.json生成roomBase_with_schedule.json
# Tips:将kebiao.html,roomBase.json,kebiao.html,table.json,roomBase_with_schedule.json添加日期后放入文件夹备份

# 1、使用parseClassRoomBaseData.py解析.xlsx教室信息（示例：七号楼教室一览表.xlsx），程序生成roomBase.json
# 2、下教务系统下载总课表html保存为result.html，使用dsParser1.py解析table.json。再使用getFreeTable.py生成roomBase_with_schedule.json（结合roomBase.json生成的空课表数据
# 3、appFlask.py读取roomBase_with_schedule.json返回空置数据

class GetSchedule:
    account = None
    password = None
    roomFileName = None
    baseUrl = "http://10.20.208.51/jsxsd"
    session = None
    kbFileName = None
    roomJsonSaveName = None
    tableJsonSaveName = None
    scheduleJsonSaveName = None

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')

        self.account = config['account']['userAccount']
        self.password = config['account']['password']
        self.session = requests.session()
        self.cookieStr = None
        self.kbFileName = config['fileName']['kbInfoSaveTo']
        self.roomFileName = config['fileName']['roomFileXlsx']
        self.roomJsonSaveName = config['fileName']['roomInfoSaveTo']
        self.tableJsonSaveName = config['fileName']['tableInfoSaveTo']
        self.scheduleJsonSaveName = config['fileName']['scheduleInfoSaveTo']

    def login(self):
        # TODO: 登录并获取cookies
        account_encoded = base64.b64encode(self.account.encode('utf-8'))
        password_encoded = base64.b64encode(self.password.encode('utf-8'))
        encoded = account_encoded.decode('utf-8') + "%%%" + password_encoded.decode('utf-8')

        # 初始化ddddocr识别验证码
        ocr = ddddocr.DdddOcr(show_ad=False)
        # 获取验证码图片
        captchaResponse = self.session.get(self.baseUrl + "/verifycode.servlet")

        image_bytes = captchaResponse.content

        # 使用ddddocr识别
        captchaResult = ocr.classification(image_bytes)

        data = {
            'loginMethod': "LoginToXk",
            'userAccount': self.account,
            'userPassword': self.password,
            "RANDOMCODE": captchaResult,
            "encoded": encoded
        }

        # 请求登录
        self.session.post(self.baseUrl + "/xk/LoginToXk", data=data)
        # 访问主页
        response = self.session.post(self.baseUrl + "/framework/xsMain.jsp")
        html = etree.HTML(response.text)
        # 校验登录结果
        if "个人中心" in response.text:
            # 成功,保存Cookie记录个人信息
            self.cookieStr = '; '.join([f'{k}={v}' for k, v in self.session.cookies.items()])
            print("登录成功:" + self.cookieStr)
            return True, self.cookieStr
        else:
            # 失败
            msgElem = html.xpath('//*[@id="showMsg"]')  # 定位错误原因
            # print(response.text)
            if msgElem:
                errorMsg = msgElem[0].text.strip()
            else:
                errorMsg = "未知错误，可能为页面结构变化导致未读取到错误信息"
            if "验证码错误" in msgElem or "请先登录系统" == msgElem:
                print("预料之内的异常:", msgElem)
                time.sleep(2)
                return self.login()

            return False, "请尝试重新登陆或检查账号密码是否正确"

    def downloadKb(self):
        # TODO: 下载课表
        print("开始下载课表并保存为:" + self.kbFileName)
        downUrl = self.baseUrl + "/kbcx/kbxx_xzb_ifr"
        headers = {
            'referer': 'http://jwn.ccdgut.edu.cn/jsxsd/kbcx/kbxx_xzb',
            'cookie': self.cookieStr,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.52'
        }
        response = self.session.post(url=downUrl, headers=headers)

        content = response.text  # 自动解码成 str
        # 或者 content = response.content.decode('utf-8')

        with open(self.kbFileName, 'w', encoding='utf-8') as fp:
            fp.write(content)

    def getRoomBase(self):
        # TODO: 结合教室一览表生成roomBase.json保存为roomJsonSaveName
        print("开始解析教室数据:" + self.roomFileName, "  并转为JSON数据保存为:" + self.roomJsonSaveName)
        res = read_class_room_data(self.roomFileName)
        save_json_to_file(convert_to_json(res), self.roomJsonSaveName)

    def getTableInfo(self):
        # TODO: 根据总课表HTML解析出每个课程的数据保存为tableJsonSaveName
        print("开始解析总课表:" + self.kbFileName, "  并转为JSON数据保存为:" + self.tableJsonSaveName)
        parser = CourseTableParser(self.kbFileName, self.tableJsonSaveName)
        parser.run()

    def getTotalSchedule(self):
        # TODO: 根据总课表tableInfo.json和教室数据roomInfo.json生成totalSchedule总空闲情况数据
        processor = ClassScheduleProcessor(
            room_base_file=self.roomJsonSaveName,
            schedule_file=self.tableJsonSaveName,
            output_file=self.scheduleJsonSaveName,
            debug_excel="process_log.xlsx"
        )
        processor.run()

    def backup_files(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup/{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)

        for fname in [self.kbFileName, self.roomJsonSaveName, self.tableJsonSaveName, self.scheduleJsonSaveName,
                      "process_log.xlsx"]:
            if os.path.exists(fname):
                shutil.move(fname, os.path.join(backup_dir, os.path.basename(fname)))
                print(f"已备份 {fname} → {backup_dir}")


if __name__ == "__main__":
    GetSchedule = GetSchedule()
    GetSchedule.login()
    GetSchedule.downloadKb()
    GetSchedule.getRoomBase()
    GetSchedule.getTableInfo()
    GetSchedule.getTotalSchedule()
    # 移动所有产生的文件到备份文件夹，文件夹命名为留档时间
    GetSchedule.backup_files()