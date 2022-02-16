import os, sys
import locale
import subprocess
import time
import socket
from datetime import datetime


def deploy():
    cur_time = get_now()
    path = get_setting_path()
    # 초기 실행 변수
    init = False

    # 꼭 본인의 경로에 맞게 수정해주세요!
    requirements_path = "requirements.txt"

    image_name = "python__2"
    deploy_con_name = "python__2"
    test_con_name = "python__2_test"
    test_port = "8001"
    deploy_port = "8000"
    execute_file = "manage.py"
    deploy_setting_file = "base.settings.prod"
    cur_image_name = f"{image_name}:{cur_time}"

    revise_dockerfile(execute_file, requirements_path)
    try:
        print("1.get_prev_con")
        prev_con = Container(get_specific_container(f"{deploy_con_name}"))
    except:
        init = True
    try:
        print("2.shutdown_cached_container")
        shut_con = Container(get_specific_container(f"{test_con_name}"))
        os.system(f"docker rm -f {test_con_name}")
        os.system(f"docker rmi -f {shut_con.image_name}")
    except:
        pass
    print("3.make_Test_Image")
    os.system("docker pull python:3.10")
    os.system(f"docker build -t {cur_image_name} .")
    print("4.make_Test_Con_And_Test")
    os.system(
        f"docker run -d -p {test_port}:{test_port} --name {test_con_name} {cur_image_name} gunicorn --bind 0:{test_port} {path}.wsgi")
    print("5.get_Test_Con_Info")
    con_info = get_specific_container(f"{test_con_name}")
    try:
        test_con = Container(con_info)
    except:
        os.system(f"docker rmi -f {cur_image_name}")
        raise Exception("ImageBuildFailed Please Check tests.py files or Requirements Setting")
    if connection_checker(test_con) == False:
        os.system(f"docker rm -f {test_con.container_name}")
        os.system(f"docker rmi -f {cur_image_name}")
        raise Exception("Connection Failed")
    else:  ##connection check success
        os.system(f"docker rm -f {test_con.container_name}")
        if init == False:  ##첫실행이 아닐시
            os.system(f"docker rm -f {prev_con.container_name}")
            os.system(f"docker rmi -f {prev_con.image_name}")
        os.system(
            f"docker run -d -p {deploy_port}:{deploy_port} --name {deploy_con_name} {cur_image_name} gunicorn --bind 0:{deploy_port} {path}.wsgi")
        os.system(f"docker exec {deploy_con_name} python3 {execute_file} migrate --settings {deploy_setting_file}")
        # messagr success##
        print(" ")  #
        print("Build Succeed")
        print("Container Info")
        get_specific_container(f"{deploy_con_name}")


class Container:
    def __init__(self, con):
        self.container_name = con[0]
        self.image_name = con[2]
        self.ip = con[-1]
        self.port = con[-2]


def get_sys():
    """
    get_os_name
    """
    global os_encoding
    os_encoding = locale.getpreferredencoding()
    if os_encoding.upper() == 'cp949'.upper():
        return "Win"
    elif os_encoding.upper() == 'UTF-8'.upper():
        return "Lin"


def get_logs(cmd):
    """
    get_logs_from_command
    """
    os_encoding = locale.getpreferredencoding()
    if os_encoding.upper() == 'cp949'.upper():  # Windows
        return subprocess.Popen(
            cmd, stdout=subprocess.PIPE).stdout.read().decode('utf-8').strip()
    elif os_encoding.upper() == 'UTF-8'.upper():  # Mac&Linux
        return os.popen(cmd).read()
    else:
        print("None matched")
        exit()


def get_ports_from_strings(_result, words):
    """
    parse_ports_from_logs
    """
    try:
        tcp = words[-2].split("->")
        _tcp = ""
        for strings in tcp:
            if "tcp" in strings:
                _tcp = strings
                break
        return _tcp.split("/")[0]
    except:
        return ""


def get_docker_containers():
    """
    parse_containers_informations
    """
    cmd = "docker ps -a"
    logs = get_logs(cmd).split("\n")
    column = logs.pop(0)
    result = []
    if logs:
        for line in logs:
            words = line.split("  ")

            while '' in words:
                words.remove('')

            for i in range(len(words)):
                words[i] = words[i].strip().strip()
            try:
                status = words[4].strip().split(" ")[0]
                # print(f"C Name :: {words[-1]}, C ID :: {words[0]}, Img Name :: {words[1]} , Status :: {status}")
                _result = [words[-1], words[0], words[1], status]
                # get ports
                _result.append(get_ports_from_strings(_result, words))
                # get ip
                _result.append(get_logs(
                    "docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' " + words[0]).strip(
                    "'").strip("\n"))
            except:
                pass
            result.append(_result)
    else:
        print("No Containers")
    return result


def get_specific_container(cmd):
    """
    get_specific_container
    """
    a = get_docker_containers()
    for i in a:
        if i[0] == cmd:
            print(f"컨테이너이름 : {i[0]}")
            print(f"이미지이름   : {i[2]}")
            print(f"내부ip주소   : {i[5]}")
            print(f"포트주소     : {i[4]}")
            print(f"현재상태     : {i[3]}")
            return i
    return []


def get_now():
    """
    make a string by current time
    """
    now = datetime.now()
    nows = [now.year, now.month, now.day, now.hour, now.minute, now.second]
    nowtime = ""
    for i in nows:
        nowtime = nowtime + str(i).zfill(2)
    return nowtime


def connection_checker(test_con):
    """
    check container's network
    put container instance
    """
    osType = get_sys()
    print(f"현재 os 타입 :{osType}")
    if osType == "Lin":
        myip = test_con.ip
    else:
        myip = socket.gethostbyname(socket.gethostname())
    print(f"로컬IP주소   :{myip}")
    print(f"포트주소     :{test_con.port}")
    server_address = (myip, int(test_con.port))
    fail_counter = 0
    for i in range(10):
        time.sleep(1)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(server_address)
            sock.close()
            print(f"{i + 1} Connection Succeed")
        except:
            print(f"{i + 1} Connection Failed")
            fail_counter += 1
    sock.close()
    if fail_counter:
        return False
    else:
        return True


def get_setting_path():
    """
    find the setting.py's directory
    """
    setting_path = ""
    for path, dirs, files in os.walk(os.getcwd()):
        for i in files:
            if i == 'wsgi.py':
                setting_path = path
                break
    osType = get_sys()
    if osType == "Win":
        return setting_path.split("\\")[-1]
    else:
        return setting_path.split("/")[-1]


def revise_dockerfile(execute_file, requirements_path):
    """
    dockerfile의 test 를 실행 할 때 사용할 설정 파일을 수정해줍니다.
    Args:
        execute_file ([파일이름]])
    """
    context = f"FROM python:3.10\nENV PYTHONUNBUFFERED 1\nWORKDIR /usr/src/app\nCOPY . .\n#deploy.py에서 requirements_path를 수정해주세요\n#다른 폴더에 있다면 폴더이름/텍스트파일.txt 의 형식입니다.\nRUN pip3 install -r {requirements_path}\nRUN python3 {execute_file} test"
    f = open("dockerfile", 'w', encoding='UTF-8')
    f.write(context)
    f.close()


def main():
    deploy()


if __name__ == "__main__":
    main()  #