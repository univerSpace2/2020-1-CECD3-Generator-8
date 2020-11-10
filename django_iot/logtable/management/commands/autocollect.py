'''
File: autocollect.py
Project: 2020-1-CECD3-GENERATOR-8
File Created: Thursday, 17th September 2020 12:32:58 am
Author: Jongyeon Yoon (0417yjy@naver.com)
-----
Last Modified: Wednesday, 14th October 2020 12:29:45 am
Modified By: Jongyeon Yoon (0417yjy@naver.com>)
-----
Copyright 2020 Jongyeon Yoon
'''

import json
import requests
import os
import time
from django.core.management.base import BaseCommand
from logtable.models import Sensor, Level, Log, Building, DeviceModel
from datetime import datetime, timedelta
from logtable.analyzer import SimpleAnalyzer
from logtable.valuesaver import *

def check_prerequisite():
    try:
        # Building 모델에 N/A 가 있는지 확인
        na_building = Building.objects.get(building_name='N/A')
    except Building.DoesNotExist:
        # 없으면 새로 만듦
        na_building = Building(building_name='N/A', levels=0)
        na_building.save()

    try:
        # Level 모델에 Unknown 이 있는지 확인
        unknown_level = Level.objects.get(level_num='Unknown')
    except Level.DoesNotExist:
        # 없으면 새로 만듦
        unknown_level = Level(level_num='Unknown',
                              img_file_path='N/A', building_id=na_building)
        unknown_level.save()

def delete_operational_oldvalues_sme20u(present_time):
    op_sensors = Sensor.objects.filter(sensor_status='OP')
    for each in op_sensors:
        THRESHOLD_DAYS = 10
        threshold_time = present_time - timedelta(days=THRESHOLD_DAYS)

        # log와 value 들을 불러옴
        print('Deleting logs of ' + str(each) + ' older than ' + str(threshold_time) + '..')
        deleting_logs = Log.objects.filter(sensor=each).filter(updated_time__lt=threshold_time).delete()
        deleting_values = SME20U_Value.objects.filter(sensor=each).filter(updated_time__lt=threshold_time).delete()
        

def is_log_generated(device, call_time):
    # DGU 0004, 07, 08, 12만 데이터를 가져올 수 있슴
    # scode : 장치 코드(DGU~)
    # seq : 장치 일련번호
    # send_time : 마지막으로 정보를 전송받은 시각
    # smodel : 장치 모델명(현재는 SME20u만 있슴)
    scode = device['DEVICE_SCODE']
    smodel = device['DEVICE_MODEL']
    generated_flag = False

    try:
        current_sensor = Sensor.objects.get(sensor_code=scode)
    except Sensor.DoesNotExist:
        # 찍힌 로그에 해당하는 센서가 존재하지 않으면, 새로 생성
        try:
            model = DeviceModel.objects.get(name=smodel)
        except DeviceModel.DoesNotExist:
            # 모델이 없으면, 새 모델을 생성
            new_model = DeviceModel(name=smodel, period=None)
            new_model.save()
            model = DeviceModel.objects.get(name=smodel)
        finally:
            new_sensor = Sensor(sensor_code=scode, sensor_model=model, sensor_type='UK',
                            sensor_status='ND', level=Level.objects.get(level_num='Unknown'))
            new_sensor.save()
            current_sensor = Sensor.objects.get(sensor_code=scode)
    finally:
        # 로그가 찍힌 시간을 체크
        send_time = datetime.strptime(
            device['DEVICE_DATA_REG_DTM'], '%Y-%m-%d %H:%M:%S')
        # 이미 존재하는 로그인지 확인
        try:
            existing_log = Log.objects.filter(sensor__exact=current_sensor).get(updated_time=send_time)
        except Log.DoesNotExist:
            new_log = Log(sensor=current_sensor,
                                updated_time=send_time)
            new_log.save()
            current_sensor.updated_time=send_time; # 센서의 updated_time에도 적용
            current_sensor.save()
            print('New log is generated: ' + str(new_log))
            existing_log = new_log
            generated_flag = True
        finally:
            analyzer = SimpleAnalyzer()
            analyzer.update(existing_log, call_time)

    return generated_flag

def save_into_db(device):
    if(device['DEVICE_MODEL'] == 'SME20U'):
        IntegratedSensorSaver.store_to_db(device)

def run(call_time):
    #print('run() called')
    url = "http://115.68.37.90/api/logs/latest"
    payload = {}
    headers = {
        'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImIxM2M3YzhmMzYwMDAzNGExZDVhNDkzZWI5NWVkZGY4MDIwMzI4YzU4ZGM1ODMxY2JhYWI5YTU1ZTE2YTA4YTk5YWUyNzVmYmVlM2NlYTc2In0.eyJhdWQiOiIxIiwianRpIjoiYjEzYzdjOGYzNjAwMDM0YTFkNWE0OTNlYjk1ZWRkZjgwMjAzMjhjNThkYzU4MzFjYmFhYjlhNTVlMTZhMDhhOTlhZTI3NWZiZWUzY2VhNzYiLCJpYXQiOjE1NzI0Mjc0NTAsIm5iZiI6MTU3MjQyNzQ1MCwiZXhwIjoxNTg4MjM4NjUwLCJzdWIiOiIxMDAwMDAwMDAwMSIsInNjb3BlcyI6W119.IQj7AjsyRpX9Y8jJI2HJJOL221m95YRbbbX_VpvH-Nfb2NjF6w1E43qbv7tzLJqOPlsz0OkzmEDbp0405FMMan8K8Z1NdBhjaRPFDAdCaosudMUZXsovOP0buJWtoR-pcaG5MQ46wVbjBeSBJFqMzDgSrFQyjf_71Tk0MH4JLVPQVyVuTKdh_a3AWYi0BOAf6Mu31erd7i0ArkOSXeRvGnsh64qWHMuoLThy83wN7D2eTnKqHeOAbhXIJhRYWJrLI0pEzsQTy1-TC0oftKntAVVJIFx2HTOyHnCacgA2MVv8SKDu_Y6ZAoFkDv9t0KjsB7ZQKesoGUA5VHDOVdyQvtivCaNBJRLqF6r6DJhM8qP4AyDooZ5x9kfBV607MeKGm6dSFx-2EBKyqB9HSyjEBq-kD5S_iJ4Vw7MGHsh8qHjivUNXMYXcY70jktfk-OMeQ4EZz1J5WMur1jsU4rTaVFipWaF7l4-Q4kfsnBS4nMt6Gq3mCFgjEkgF0QfhpPYiNEUcpmUqG61wfgl1TQ6q2OPvYtpsxVff89TLvXriV0CfBePlw6rfr3hg8wZnkH0P7BirGA6RfTHDlXOG6432528pgZeowYpJtQBmey1iP7P1aQGmIeeeWrI2RbM8Eat_oQMoT0RShx66lmKlg8zxaXsDDSWcfdYlRC53s_0RfNE'
    }
    # 동국대 센서 api 연결 정보
    response = requests.request("GET", url, headers=headers, data=payload)
    # response: request 모듈을 이용해서 api에 연결을 요청해서 JSON데이터를 가져옴

    writeFile = open('result.json', 'w')
    writeFile.write(response.text)
    # writeFile : 요청해서 받아온 데이터가 json인데 text형태라서 json 파일로 만듦
    writeFile.close()

    with open('result.json', 'r') as f:
        # result.json을 f로 하여 열고 json_data에 json파일 내용을 로드함
        #print('Opening result.json')
        json_data = json.load(f)

    # json파일 내에 result에 있는 IoT 센서 정보를 IoTDevices 배열에 저장
    IoTDevices = json_data['result']

    for i in IoTDevices:
        if is_log_generated(i, call_time):
            # 센서 값은 로그가 생성됐을 때만 저장함
            save_into_db(i)
    delete_operational_oldvalues_sme20u(call_time)
                   
    os.remove('result.json')  # 가져왔던 reuslt.json 삭제


class Command(BaseCommand):
    help = 'Automatically get data from api in json format, store them in the database'

    def add_arguments(self, parser):
        # period 매개변수. 기본값은 300
        parser.add_argument('period', type=int, nargs='?', default=300, help='Indicates the number of period between current and next running')

    def handle(self, *args, **kwargs):
        check_prerequisite()  # 필요한 N/A 값 이 DB에 있는지 확인 후 없을 시 추가

        while True:
            SLEEP_PERIOD = kwargs['period']
            self.stdout.write("Collecting Logs...")
            run(datetime.now())
            self.stdout.write(
                "Complete, Next collecting starts in " + str(SLEEP_PERIOD))
            time.sleep(SLEEP_PERIOD)
