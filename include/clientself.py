import socket
import threading
HOST = 'frp-oil.com'
PORT = 63867

def reader(s):
    with s.makefile('r', encoding='utf-8') as f:
        while True:
            msg = f.readline().strip()
            print(msg)

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    name = str(input("请输入昵称：")).strip()
    s.sendall((name + "\n").encode('utf-8'))
    t = threading.Thread(target=reader, args=(s,))
    t.start()
    while True:
        msg = str(input()).strip()
        s.sendall((msg + "\n").encode('utf-8'))