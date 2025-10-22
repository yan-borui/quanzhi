import socket
import threading
import queue
HOST = ''
PORT = 50007
playerdata = {}
readqueue = queue.Queue()
readlock = threading.Lock()
chatqueue = queue.Queue()
chatlock = threading.Lock()
sendlock = threading.Lock()

def connecter(host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(10)
        s.settimeout(1.0)
        while not start_game.is_set():
            try:
                conn, addr = s.accept()
                name = conn.makefile('r', encoding='utf-8').readline().strip()
                sendlock.acquire()
                conn.sendall("你加入了游戏\n".encode('utf-8'))
                if len(playerdata) > 0:
                    msg = "房间中还有："
                    for i in playerdata.values():
                        msg += f"{i[1]}，"
                    conn.sendall((msg.rstrip('，').strip() + "\n").encode('utf-8'))
                sendlock.release()
                playerdata[addr] = (conn, name)
                print(f"{name} 加入了游戏")
                msg = f"{name} 加入了游戏\n"
                writeall(msg)
                readerthr = threading.Thread(target=reader, args=(conn, addr), name=f"{name}readerthr")
                readerthr.start()
            except socket.timeout:
                pass


def reader(conn, addr):
    with conn.makefile('r', encoding='utf-8') as f:
        while True:
            msg = f.readline().strip()
            if msg.startswith("/q") or msg.startswith("/d"):
                chatlock.acquire()
                chatqueue.put((addr, msg))
                chatlock.release()
            else:
                readlock.acquire()
                readqueue.put((addr, msg))
                readlock.release()



def write(addr, msg):
    msg = msg.strip() + "\n"
    conn = playerdata[addr][0]
    sendlock.acquire()
    conn.sendall(msg.encode('utf-8'))
    sendlock.release()


def writeall(msg):
    for i in playerdata.keys():
        write(i, msg)

def chatserver():
    while True:
        chat = chatqueue.get()
        name = playerdata[chat[0]][1]
        if chat[1].startswith("/q"):
            msg = f"【全体】{name}：{chat[1][2:].strip()}\n"
            writeall(msg)
            print(msg, end="")



def isint012(msg):
    try:
        return int(msg) in {0, 1, 2}
    except ValueError:
        return False

def gameserver():
    quan = ["剪刀", "石头", "布"]
    while start_game.is_set():
        chuquan = {}
        for i in playerdata.keys():
            chuquan[i] = [0, 1]
        gameover = False
        while not gameover:
            for i in chuquan.keys():
                if chuquan[i][1] == 1:
                    write(i, "剪刀为0，石头为1，布为2\n")
                    write(i, "请出拳：\n")
            count = 0
            playernum = 0
            for i in chuquan.values():
                if i[1] == 1:
                    playernum += 1
            while count < playernum:
                read = readqueue.get()
                addr = read[0]
                msg = read[1]
                if not isint012(msg):
                    write(addr, "出拳无效！\n")
                    continue
                if chuquan[addr][1] == -1:
                    write(addr, "您无法出拳！\n")
                    continue
                elif chuquan[addr][1] == 0:
                    write(addr, "您已经出过拳了！\n")
                    continue
                chuquan[addr] = [int(msg), 0]
                count += 1
                write(addr, f"您出{quan[int(msg)]}\n")
                print(f"{playerdata[addr][1]} 出{quan[chuquan[addr][0]]}")
            chuquanall = set()
            for i in chuquan.keys():
                if chuquan[i][1] == 0:
                    writeall(f"{playerdata[i][1]} 出{quan[chuquan[i][0]]}\n")
                    chuquanall.add(chuquan[i][0])
            if len(chuquanall) != 2:
                writeall("平手！\n")
                for i in chuquan.keys():
                    if chuquan[i][1] == 0:
                        chuquan[i][1] = 1
            else:
                if 0 not in chuquanall:
                    win = 2
                    lose = 1
                elif 1 not in chuquanall:
                    win = 0
                    lose = 2
                else:
                    win = 1
                    lose = 0
                wincount = 0
                winner = ""
                for i in chuquan.keys():
                    if chuquan[i] == [win, 0]:
                        winner += playerdata[i][1] + "，"
                        chuquan[i][1] = 1
                        wincount += 1
                    elif chuquan[i] == [lose, 0]:
                        chuquan[i][1] = -1
                        write(i, "您输了，请等待本轮结束\n")
                winner = winner.rstrip("，")
                writeall(f"{winner} 胜\n")
                if wincount == 1:
                    gameover = True
                    writeall(f"{winner} 获胜！\n")
                    writeall("下一局开始\n")








if __name__ == '__main__':
    start_game = threading.Event()
    connectthr = threading.Thread(target=connecter, args=(), name="connectthr")
    connectthr.start()
    chatthr = threading.Thread(target=chatserver, args=(), name="chatthr")
    chatthr.start()
    input("按换行键开始……\n")
    writeall("游戏开始！\n")
    print("游戏开始！")
    start_game.set()
    gamethr = threading.Thread(target=gameserver, args=(), name="gamethr")
    gamethr.start()
    input("按换行键结束……\n")
    writeall("游戏结束！\n")
    print("游戏结束！")
    start_game.clear()
