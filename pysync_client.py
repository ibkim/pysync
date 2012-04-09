import socket
import sys
import ConfigParser, os
import glob
import hashlib
import pickle
from cStringIO import StringIO

def makemd5sum(path):
    md5 = hashlib.md5()
    f = open(path,'rb')
    for chunk in iter(lambda: f.read(128*md5.block_size), b''):
        md5.update(chunk)

    f.close()
    return md5.hexdigest()

# Parse Configuration file
config = ConfigParser.ConfigParser()
config.readfp(open("pysync.cfg"))

server = config.get("client", "server")
port = config.get("client", "peer_port")
dirs = config.get("client", "dirs").splitlines()
ignore_files = config.get("client", "ignores").splitlines()
exts = config.get("client", "extensions").split()

# Gethering files
files = []
for path in dirs:
    for extension in exts:
        item = glob.glob(path + "/*." + extension)
        if item != []:
            for file in item:
                files.append(file)

# Make nodes dictionaries
nodes = {}
for path in files:
    try:
        index = ignore_files.index(path)
    except:
        filesize = os.stat(path).st_size
        mtime = os.stat(path).st_mtime
        sum = makemd5sum(path)
        nodes[path] = [filesize, mtime, sum]

node_pickle = pickle.dumps(nodes)

HOST = server    # The remote host
PORT = int(port)              # The same port as used by the server
s = None
for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
    af, socktype, proto, canonname, sa = res
    try:
        s = socket.socket(af, socktype, proto)
    except socket.error as msg:
        s = None
        continue
    try:
        s.connect(sa)
    except socket.error as msg:
        s.close()
        s = None
        continue
    break
if s is None:
    print('could not open socket')
    sys.exit(1)

# Start Handshake proto
s.send("HELLO: " + str(len(node_pickle)))
data = s.recv(1024)
if data != "READY":
    print "Server is not ready."
    s.close()
    exit(1)

# Now, We send nodes pickle data
s.send(node_pickle)

# Send file by transfer request
while True:
    data = s.recv(2048)
    msg = str(data).split(':')[0]
    if msg == "DONE":
        print "Recv DONE msg from server. Quit Transfer."
        break

    file = str(data).split(':')[1]

    if msg == "READY" and file == "":
        print "Server has abnormal message."
        s.close()
        exit(1)

    print "Request file %s" % file
    f = open(file, "r")
    while True:
        data = f.read(1024*8)
        if len(data):
            s.send(data)
        else:
            break

    print "Sended %s" % file

s.close()


