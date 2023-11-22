# server.py

import socket
import threading
import time
import random
import json

class Server:
    def __init__(self):
        super().__init__()

        self.clients = []
        self.room_timers = {}  # 각 방의 타이머
        self.timer_interval = 1000  # 타이머 갱신 간격 (1초)
        self.init_time = 60 # 초기 타이머 시간 설정
        self.timer_start = False
        self.user_list = []
        self.init_ui()

    def init_ui(self):
        self.start_server(12345, 'Room 1')
        self.start_server(12346, 'Room 2')

    def start_server(self, port, room_name):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('서버 주소', port)) #서버 주소
        # server_socket.bind(('localhost', port))
        server_socket.listen(5)

        if room_name == 'Room 1':
            print(f'홀짝게임 Server - {port} 로 시작되었습니다.')
        else:
            print(f'로또게임 Server - {port} 로 시작되었습니다.')

        self.room_timers[room_name] = self.init_time
        threading.Thread(target=self.accept_connections, args=(server_socket, room_name)).start()

        if not self.timer_start:
            threading.Thread(target=self.update_room_timers).start()
            self.timer_start = True

    def accept_connections(self, server_socket, room_name):
        while True:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, room_name)).start()

    def handle_client(self, client_socket, room_name):
        room, nickname, money_str = client_socket.recv(1024).decode().split(":")
        money = int(money_str)
        self.clients.append((room_name, nickname, money, client_socket))
        client_ip = client_socket.getpeername()[0] # 클라이언트 ip 가져오기

        request = client_socket.recv(1024).decode()
        data = json.loads(request)
        chk = True

        # 프로토콜 데이터 확인
        if not len(data) == 5:
            self.clients.remove((room_name, nickname, money, client_socket))
            self.broadcast(f"OUT:{data['nickname']}", client_socket, room_name)
            client_socket.close()
            chk = False
        elif not data['status'] == 'success':
            self.clients.remove((room_name, nickname, money, client_socket))
            self.broadcast(f"OUT:{data['nickname']}", client_socket, room_name)
            client_socket.close()
            chk = False
        elif not data['message'] == 'CONNECT':
            self.clients.remove((room_name, nickname, money, client_socket))
            self.broadcast(f"OUT:{data['nickname']}", client_socket, room_name)
            client_socket.close()
            chk = False
        elif int(data['money']) < 0:
            self.clients.remove((room_name, nickname, money, client_socket))
            self.broadcast(f"OUT:{data['nickname']}", client_socket, room_name)
            client_socket.close()
            chk = False
        elif data['nickname'] == '':
            self.clients.remove((room_name, nickname, money, client_socket))
            self.broadcast(f"OUT:{data['nickname']}", client_socket, room_name)
            client_socket.close()
            chk = False
        blocked_ips = ['차단할 아이피']
        if client_ip in blocked_ips:
            self.clients.remove((room_name, nickname, money, client_socket))
            self.broadcast(f"OUT:{data['nickname']}", client_socket, room_name)
            client_socket.close()
            chk = False

        if chk:
            print('connect 완료')
            print(f"닉네임 : {data['nickname']}")
            print()

            self.broadcast(f'{nickname} 님이 {room_name}로 입장하였습니다.', client_socket, room_name)
            self.send_timer_data(client_socket, room_name)

        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                parts = data.decode().split(":")
                if len(parts) == 4 and parts[0] == room_name:
                    self.broadcast(f'{parts[1]}:{parts[3]}', client_socket, room_name)
                elif parts[0] == 'TIMER':
                    self.timer_data[room_name] = int(parts[1])  # 클라이언트의 타이머 데이터 업데이트
                    self.send_timer_data(client_socket, room_name)
                elif parts[0] == 'END':
                    self.clients.remove((room_name, parts[2], int(parts[3]), client_socket))
                    self.broadcast(f'{parts[2]}님이 {room_name} 을 나갔습니다.', client_socket, room_name)
                    client_socket.close()
            except Exception as e:
                print(e)
                break

        if (room_name, nickname, money, client_socket) in self.clients:
            self.clients.remove((room_name, nickname, money, client_socket))

        # Notify other clients about the disconnection
        self.broadcast(f'{nickname}님이 나갔습니다.', client_socket, room_name)

    def broadcast(self, message, client_socket=None, room_name=''):
        for r_name, name, money, socket in self.clients:
            if socket != client_socket and r_name == room_name:
                try:
                    socket.send(message.encode())  # 모든 클라이언트에게 메시지 전송
                except Exception as e:
                    print(e)

    def send_timer_data(self, client_socket, room_name):
        try:
            message = f'TIMER:{self.room_timers[room_name]}'
            client_socket.send(message.encode())
        except Exception as e:
            print(e)

    def update_room_timers(self):
        while True:
            time.sleep(1)
            for room, timer in self.room_timers.items():
                self.broadcast(f'TIMER:{timer}', room_name=room)
                if timer > 0:
                    self.room_timers[room] -= 1
                else:
                    self.room_timers[room] = self.init_time  # 타이머가 0이 되면 초기화 (예: 30초)
                    if room == 'Room 1':
                        self.chk_hol_jjak(room)
                    if room == 'Room 2':
                        self.chk_lotto(room)

    def chk_hol_jjak(self, room):
        random_num = random.randint(1, 9)
        result = '홀' if random_num%2 else '짝'
        self.broadcast(f'RESULT1:{result}', room_name=room)

    def chk_lotto(self, room):
        result = self.make_lotto()
        self.broadcast(f'RESULT2:{result}', room_name=room)

    def make_lotto(self):
        random_list = []
        while len(random_list) != 6:
            r_number = random.randrange(1, 11, 1)  # 1 ~ 10 로또 번호 생성
            if r_number not in random_list:
                random_list.append(r_number)
        random_list.sort()
        return str(random_list)[1:-1]


if __name__ == '__main__':
    server_window = Server()