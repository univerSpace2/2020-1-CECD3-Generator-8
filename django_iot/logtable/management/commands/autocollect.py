import json
import requests
import os
import time
from django.core.management.base import BaseCommand
from logtable.models import Sensor, Level, Log, Building
from datetime import datetime


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


def run():
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
        # DGU 0004, 07, 08, 12만 데이터를 가져올 수 있슴
        # scode : 장치 코드(DGU~)
        # seq : 장치 일련번호
        # send_time : 마지막으로 정보를 전송받은 시각
        # smodel : 장치 모델명(현재는 SME20u만 있슴)
        scode = i['DEVICE_SCODE']
        try:
            current_sensor = Sensor.objects.get(sensor_code=scode)
        except Sensor.DoesNotExist:
            # 찍힌 로그에 해당하는 센서가 존재하지 않으면, 새로 생성
            new_sensor = Sensor(sensor_code=scode, sensor_name='Unknown', sensor_type='UK',
                                sensor_status='ND', level=Level.objects.get(level_num='Unknown'))
            new_sensor.save()
            current_sensor = Sensor.objects.get(sensor_code=scode)
        finally:
            existing_log = Log.objects.filter(sensor__exact=current_sensor)
            # 로그가 찍힌 시간을 체크
            send_time = datetime.strptime(
                i['DEVICE_DATA_REG_DTM'], '%Y-%m-%d %H:%M:%S')
            if existing_log:
                if not existing_log.filter(updated_time=send_time):
                    new_log = Log(sensor=current_sensor,
                                  updated_time=send_time)
                    new_log.save()
            else:
                # 로그가 아예 없으면 생성
                new_log = Log(sensor=current_sensor,
                              updated_time=send_time)
                new_log.save()
                print('New log is generated: ' + str(new_log))
    os.remove('result.json')  # 가져왔던 reuslt.json 삭제


class Command(BaseCommand):
    help = 'Automatically get data from api in json format, store them in the database'

    def handle(self, *args, **kwargs):
        check_prerequisite()  # 필요한 N/A 값 이 DB에 있는지 확인 후 없을 시 추가

        while True:
            SLEEP_PERIOD = 300  # 5분
            self.stdout.write("Collecting Logs...")
            run()
            self.stdout.write(
                "Complete, Next collecting starts in " + str(SLEEP_PERIOD))
            time.sleep(SLEEP_PERIOD)