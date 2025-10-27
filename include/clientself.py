import socket
import threading
HOST = 'frp-oil.com'
PORT = 63867
closed = threading.Event()


def reader(s):
    with s.makefile('r', encoding='utf-8') as f:
        while True:
            msg = f.readline().strip()
            if not msg:
                break
            print(msg)
    print("服务端断开连接！按换行键结束……")
    closed.set()


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    name = str(input("请输入昵称：")).strip()
    s.sendall((name + "\n").encode('utf-8'))
    t = threading.Thread(target=reader, args=(s,))
    t.start()
    while True:
        msg = str(input()).strip()
        if closed.is_set():
            break
        s.sendall((msg + "\n").encode('utf-8'))
