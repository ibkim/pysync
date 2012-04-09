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

save_path = config.get("server", "dir")
os_type = config.get("server", "os")
path_delimeter = "/"

mkdir_cmd = "mkdir -p "
if os_type == "win":
    mkdir_cmd = "mkdir "

if os.access(save_path, os.F_OK | os.W_OK) == False:
    print "Make Download directory. %s" % save_path
    os.system("mkdir -p " + save_path)

if os_type == "win":
    path_delimeter = "\\"

HOST = None               # Symbolic name meaning all available interfaces
PORT = 50007              # Arbitrary non-privileged port
s = None
for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC,
                              socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
    af, socktype, proto, canonname, sa = res
    try:
        s = socket.socket(af, socktype, proto)
    except socket.error as msg:
        s = None
        continue
    try:
        s.bind(sa)
        s.listen(1)
    except socket.error as msg:
        s.close()
        s = None
        continue
    break
if s is None:
    print('could not open socket')
    sys.exit(1)
conn, addr = s.accept()
print('Connected by', addr)

# Getting HELLO with nodes pickle size from client
data = conn.recv(1024)
if not data:
    print "Client has abnormal message."
    conn.close()
    exit(1)
    
msg = str(data)
if msg.split(':')[0] != "HELLO":
    print "Client has abnormal message."
    conn.close()
    exit(1)

pickle_size = int(msg.split(':')[1])
print "Receive HELLO: pickle size %d" % pickle_size
print "Send READY ack"
conn.send("READY")

# Loads nodes dictionaries from pickle
node_pickle = conn.recv(pickle_size)
nodes = pickle.loads(node_pickle)

# check file
print ""
print "Checking file for transfering..."
need_files = []
for path in nodes.keys():
    filename = path.split(path_delimeter)[-1]
    file_path = save_path + path_delimeter + filename
    
    # We need file, If we don't have.
    if os.access(file_path, os.F_OK) == False:
        print "Need(New): %s" % path
        need_files.append(path)
    else:
        # Let's compare file size and md5 checksum, if we have.
        if nodes[path][0] != os.stat(file_path).st_size:
            print "Need(Size): %s" % path
            need_files.append(path)
        #elif nodes[path][1] != os.stat(file_path).st_mtime:
        #    print "Need(Mtime): %s" % path
        #    need_files.append(path)
        elif nodes[path][2] != makemd5sum(file_path):
            print "Need(MD5): %s" % path
            need_files.append(path)
        else:
            print "Ignore: %s" % path
            
print "Checking Done."

print ""
if need_files:
    print "File Synchronize Start..."

# Now, Transfer Request about files
for path in need_files:
    filesize = nodes[path][0]
    filename = path.split(path_delimeter)[-1]
    local_path = save_path + path_delimeter + filename
    md5sum = nodes[path][2]
    f = open(local_path, "w")
    
    conn.send("READY:" + path)
    
    print "%s Transfer Start." % local_path
    recv_num = 0
    while True:
        data = conn.recv(1024*8)
        recv_num += len(data)
        f.write(data)
        if recv_num == filesize:
            break
    f.close()
    
    if md5sum != makemd5sum(local_path):
        print "%s transfer failed, md5 checksum missmatch." % local_path
        os.unlink(local_path)
        continue
    
    print "%s Transfer Done. OK" % local_path

print "Synchronization Complete."

conn.send("DONE")

conn.close()





