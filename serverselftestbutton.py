import socket, threading, queue, time
HOST = ''
PORT = 50007
playerdata = {}  # addr:(conn,name,team)
readqueue = queue.Queue()
chatqueue = queue.Queue()
readlock = threading.Lock()
chatlock = threading.Lock()
sendlock = threading.Lock()
playerlock = threading.RLock()


def connecter(host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(10)
        s.settimeout(1.0)
        while not start_game.is_set() and not end_game.is_set():
            try:
                conn, addr = s.accept()
                data = conn.recv(4096)
                name, team = data.split(b'\n', 1)
                name = name.decode('utf-8').strip()
                team = team.decode('utf-8').strip()
                with playerlock:
                    with sendlock:
                        conn.sendall("你加入了游戏\n".encode('utf-8'))
                        if len(playerdata) > 0:
                            msg = "房间中还有："
                            for i in playerdata.values():
                                msg += f"{i[1]}，"
                            conn.sendall((msg.rstrip('，').strip() + "\n").encode('utf-8'))
                    playerdata[addr] = (conn, name, team)
                writeall(f"队伍 {team} 的 {name} 加入了游戏\n")
                print(f"队伍 {team} 的 {name} 加入了游戏")
                readerthr = threading.Thread(target=reader, args=(conn, addr), name=f"{name}readerthr")
                readerthr.start()
            except socket.timeout:
                pass





def reader(conn, addr):
    buf = b''
    while True:
        try:
            data = conn.recv(4096)
        except (ConnectionResetError, ConnectionAbortedError):
            break
        if not data:
            break
        buf += data
        while b'\n' in buf:
            line, buf = buf.split(b'\n', 1)
            msg = line.decode('utf-8').strip()
            if msg.startswith("/q") or msg.startswith("/d"):
                with chatlock:
                    chatqueue.put((addr, msg))
            else:
                with readlock:
                    readqueue.put((addr, msg))
    if not end_game.is_set():
        with playerlock:
            playerdata[addr][0].close()
            name = playerdata[addr][1]
            team = playerdata[addr][2]
            del playerdata[addr]
        writeall(f"队伍 {team} 的 {name} 离开了游戏\n")
        print(f"队伍 {team} 的 {name} 离开了游戏")






def write(addr, msg):
    msg = msg.strip() + "\n"
    with playerlock:
        conn = playerdata[addr][0]
    with sendlock:
        conn.sendall(msg.encode('utf-8'))
    print(f"向{addr}发送了{msg}")


def writeall(msg):
    with playerlock:
        addrs = list(playerdata.keys())
    for i in addrs:
        write(i, msg)

def writeteam(msg, team):
    addrs = []
    with playerlock:
        for i in playerdata.keys():
            if playerdata[i][2] == team:
                addrs.append(i)
    for i in addrs:
        write(i, msg)

def writebutton(addr, buttonlist):
    msg = "/b "
    for i in buttonlist:
        msg += i[0] + ";" + i[1] + ";"
    write(addr, msg)

def chatserver():
    while True:
        chat = ()
        while not end_game.is_set():
            try:
                with chatlock:
                    chat = chatqueue.get(block=False)
                break
            except queue.Empty:
                time.sleep(1)
        if end_game.is_set():
            break
        with playerlock:
            name = playerdata[chat[0]][1]
        if chat[1].startswith("/q"):  # 全体消息
            msg = f"/q 【全部】{name}：{chat[1][2:].strip()}\n"
            writeall(msg)
        else:  # 队伍消息
            team = playerdata[chat[0]][2]
            msg = f"/d 【队伍】{name}：{chat[1][2:].strip()}\n"
            writeteam(msg, team)
        print(msg, end="")



def isint012(msg):
    try:
        return int(msg) in {0, 1, 2}
    except ValueError:
        return False

# def gameserver():
#     quan = ["剪刀", "石头", "布"]
#     while start_game.is_set():
#         chuquan = {}
#         with playerlock:
#             for i in playerdata.keys():
#                 chuquan[i] = [0, 1]
#         gameover = False
#         while not gameover:
#             for i in chuquan.keys():
#                 if chuquan[i][1] == 1:
#                     write(i, "请出拳：\n")
#             count = 0
#             playernum = 0
#             for i in chuquan.values():
#                 if i[1] == 1:
#                     playernum += 1
#             while count < playernum:
#                 read = ()
#                 while start_game.is_set():
#                     try:
#                         with readlock:
#                             read = readqueue.get(block=False)
#                         break
#                     except queue.Empty:
#                         time.sleep(1)
#                 if end_game.is_set():
#                     break
#                 addr = read[0]
#                 msg = read[1]
#                 if not isint012(msg):
#                     write(addr, "出拳无效！\n")
#                     continue
#                 if chuquan[addr][1] == -1:
#                     write(addr, "您无法出拳！\n")
#                     continue
#                 elif chuquan[addr][1] == 0:
#                     write(addr, "您已经出过拳了！\n")
#                     continue
#                 chuquan[addr] = [int(msg), 0]
#                 count += 1
#                 write(addr, f"您出{quan[int(msg)]}\n")
#                 with playerlock:
#                     print(f"{playerdata[addr][1]} 出{quan[chuquan[addr][0]]}")
#             if end_game.is_set():
#                 break
#             chuquanall = set()
#             for i in chuquan.keys():
#                 if chuquan[i][1] == 0:
#                     with playerlock:
#                         writeall(f"{playerdata[i][1]} 出{quan[chuquan[i][0]]}\n")
#                     chuquanall.add(chuquan[i][0])
#             if len(chuquanall) != 2:
#                 writeall("平手！\n")
#                 for i in chuquan.keys():
#                     if chuquan[i][1] == 0:
#                         chuquan[i][1] = 1
#             else:
#                 if 0 not in chuquanall:
#                     win = 2
#                     lose = 1
#                 elif 1 not in chuquanall:
#                     win = 0
#                     lose = 2
#                 else:
#                     win = 1
#                     lose = 0
#                 wincount = 0
#                 winner = ""
#                 for i in chuquan.keys():
#                     if chuquan[i] == [win, 0]:
#                         with playerlock:
#                             winner += playerdata[i][1] + "，"
#                         chuquan[i][1] = 1
#                         wincount += 1
#                     elif chuquan[i] == [lose, 0]:
#                         chuquan[i][1] = -1
#                         write(i, "您输了，请等待本轮结束\n")
#                 winner = winner.rstrip("，")
#                 writeall(f"{winner} 胜\n")
#                 if wincount == 1:
#                     gameover = True
#                     writeall(f"{winner} 获胜！\n")
#                     writeall("下一局开始\n")

def gameserver():
    numbers = {}
    with playerlock:
        for i in playerdata.keys():
            numbers[i] = 4
    buttonlist = []
    for i in range(4):
        buttonlist.append((f"b{i + 1}", f"{i + 1}"))
    for i in numbers.keys():
        writebutton(i, buttonlist)
    while start_game.is_set():
        while start_game.is_set():
            try:
                with readlock:
                    read = readqueue.get(block=False)
                break
            except queue.Empty:
                time.sleep(1)
        if end_game.is_set():
            break
        numbers[read[0]] = int(read[1]) * 2
        buttonlist = []
        for i in range(numbers[read[0]]):
            buttonlist.append((f"b{i + 1}", f"{i + 1}"))
        writebutton(read[0],buttonlist)








if __name__ == '__main__':
    start_game = threading.Event()
    end_game = threading.Event()
    try:
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
    finally:
        writeall("游戏结束！\n")
        print("游戏结束！")
        start_game.clear()
        end_game.set()
        with playerlock:
            for i in playerdata.values():
                i[0].close()
