# client.py

import json
import socket
import sys
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit, QLabel, QInputDialog

class ChatClientWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.setGeometry(100, 100, 300, 200)
        self.setWindowTitle('게임방')

        chat1_btn = QPushButton('홀짝 게임방', self)
        chat1_btn.clicked.connect(lambda: self.create_client_window('Room 1', 12345))

        chat2_btn = QPushButton('로또 게임방', self)
        chat2_btn.clicked.connect(lambda: self.create_client_window('Room 2', 12346))

        layout = QVBoxLayout(self)
        layout.addWidget(chat1_btn)
        layout.addWidget(chat2_btn)

    def create_client_window(self, room_name, port):
        nickname, ok = QInputDialog.getText(self, '닉네임 입력:', '닉네임', QLineEdit.Normal, '테스트')
        if not ok:
            return

        client_window = ClientWindow(room_name, nickname, port)  # 포트 번호를 전달
        client_window.show()

        self.close()

class ClientWindow(QWidget):
    active_windows = []

    def __init__(self, room_name, nickname, port):
        super().__init__()

        self.room_name = room_name
        self.nickname = nickname
        self.money = 10000
        self.remaining_time = 1000
        self.last_message = ""
        self.port = port  # 새로운 포트 속성 추가
        self.rule_text = ''
        self.first = True
        self.init_ui()

    def init_ui(self):
        self.setGeometry(100, 80, 400, 420)
        self.setWindowTitle(f'Client - {self.nickname} - {self.room_name}')

        if self.room_name == 'Room 1':
            self.rule_text = "                                 *** 홀짝게임 ***\n\n1. '홀', '짝' 중 입력합니다.\n2. 가장 마지막 입력한 텍스트 기준으로 체크합니다.\n3. 맞추면 + 4000, 틀리면 - 2000"
        else:
            self.rule_text = "                                 *** 로또게임 ***\n\n1. 1~10 중 다른 6개의 숫자를 입력합니다.(형식 : '2 10 7 3 1 8')\n2. 1번의 형식에 맞지 않은 경우 틀린 것으로 간주(ex. 중복, 5개)\n3. 가장 마지막 입력한 텍스트 기준으로 체크합니다.\n4. 맞추면 + 100000, 틀리면 - 2000"

        self.rule_label = QLabel(self.rule_text, self)
        self.rule_label.setGeometry(10, 10, 380, 120)

        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(10, 120+10, 380, 200)

        self.money_label = QLineEdit(f'잔고: {self.money}', self)
        self.money_label.setGeometry(10, 340, 150, 30)
        self.money_label.setReadOnly(True)

        self.timer_label = QLineEdit(f'시간(초): {self.remaining_time}', self)
        self.timer_label.setGeometry(150, 340, 150, 30)
        self.timer_label.setReadOnly(True)

        self.input_line = QLineEdit(self)
        self.input_line.setGeometry(10, 380, 280, 30)

        self.send_btn = QPushButton('Send', self)
        self.send_btn.setGeometry(300, 380, 90, 30)
        self.send_btn.clicked.connect(self.send_message)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('34.16.137.62', self.port))
        # self.client_socket.connect(('localhost', self.port))

        self.client_socket.send(f'{self.room_name}:{self.nickname}:{str(self.money)}'.encode())

        data = {} # 프로토콜 데이터
        data['status'] = 'success'
        data['ip'] = socket.gethostbyname(socket.gethostname())
        data['message'] = 'CONNECT'
        data['nickname'] = self.nickname
        data['money'] = str(self.money)
        self.client_socket.send(json.dumps(data).encode())
        self.first = True
        self.input_line.returnPressed.connect(self.send_message)

        threading.Thread(target=self.receive_messages).start()
        self.active_windows.append(self)

    def send_message(self):
        message = f'{self.room_name}:{self.nickname}:{int(self.money)}:{self.input_line.text()}'

        self.client_socket.send(message.encode())
        self.text_edit.append(f'{self.nickname}(나) : {self.input_line.text()}')  # 대화창에 내용 추가
        self.last_message = self.input_line.text()
        self.input_line.clear()

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                message = data.decode()

                if message.startswith("TIMER:"):
                    _, remaining_time = message.split(":")
                    self.remaining_time = int(remaining_time)
                    # 남아 있는 시간 20초 이상일 경우만 다음 게임 참여
                    if self.remaining_time > 20:
                        self.first = False
                    self.timer_label.setText(f'시간(초): {self.remaining_time}')
                elif message.startswith("Money:"):
                    self.money_label.setText(message)
                elif message.startswith("RESULT1:"):
                    result = message.split(':')[1]
                    self.text_edit.append('**********')
                    self.text_edit.append(f'**   {result}   **')
                    self.text_edit.append('**********')
                    self.append_text('')
                    if not self.first:
                        if result == self.last_message:
                            self.money += 4000
                        else:
                            self.money -= 2000
                            if self.money < 0 :
                                self.money = 0

                        self.money_label.setText(f'잔고 : {self.money}')
                        self.last_message = ""

                    self.first = False
                    if self.money <= 0:
                        self.client_socket.send(f'END:{self.room_name}:{self.nickname}:{self.money}'.encode())
                        self.close()
                    self.client_socket.send(f'UPDATE'.encode())
                elif message.startswith("RESULT2:"):
                    result = message.split(':')[1].strip().split(',')
                    result_list = []

                    for re in result:
                        result_list.append(int(re))
                    result_list.sort()

                    self.text_edit.append('*******************************')
                    self.text_edit.append(f'**   {str(result_list)}    **')
                    self.text_edit.append('*******************************')

                    if not self.first:
                        if not self.chk_lotto(result_list, self.last_message):
                            self.money -= 2000 # 틀렸을 때
                            if self.money < 0:
                                self.money = 0
                        else:
                            self.money += 100000

                        self.money_label.setText(f'잔고 : {self.money}')
                        self.last_message = ""

                    self.first = False
                    if self.money <= 0:
                        self.client_socket.send(f'END:{self.room_name}:{self.nickname}:{self.money}'.encode())
                        self.close()
                    self.client_socket.send(f'UPDATE'.encode())
                elif message.startswith('OUT:'):
                    print('접속 프로토콜 형식이 맞지 않습니다.')
                    name = message.split(':')[1]

                    if name == self.nickname:
                        self.close()
                elif not message.startswith(f'{self.room_name}:{self.nickname}'):
                    # 자신이 보낸 메시지가 아닌 경우에만 출력
                    self.text_edit.append(message)

            except Exception as e:
                print(e)
                break

    def chk_lotto(self, result_list, message):
        num_list = [int(num) for num in message.split()]

        result_list.sort()
        num_list.sort()

        if len(num_list) != 6:
            return False

        if not result_list == num_list:
            return False
        else:
            return True

    def update_timer(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.timer_label.setText(f'시간(초): {self.remaining_time}')
            if self.remaining_time == 0:
                self.client_socket.send(f'{self.room_name}:{self.nickname} 입력 완료.'.encode())

    def append_text(self, text):
        # 텍스트를 추가하고 스크롤을 가장 아래로 이동
        self.text_edit.append(text)
        scroll_bar = self.text_edit.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def closeEvent(self, event):
        self.client_socket.send(f'{self.room_name}:{self.nickname}:{self.money} 님이 나가셨습니다.'.encode())
        self.active_windows.remove(self)
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    chat_client_window = ChatClientWindow()
    chat_client_window.show()
    sys.exit(app.exec_())
