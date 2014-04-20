
#
# wycliffe -- Clean room implementation of Dante protocol
#
# Copyright (C) 2014 Jeff Sharkey, http://jsharkey.org/
# All Rights Reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


# apt-get install python-dev python-pip
# pip install urwid

import sys, struct, re, threading, time
import socket
from socket import *
import urwid

def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()

palette = [
    ('banner', 'black', 'light gray'),
    ('streak', 'black', 'dark red'),
    ('level', 'black', 'dark red'),
    ]


labels = []
levels = []
rows = []

for i in range(1,128):
	label = urwid.Text(('label', u"CH%d" % (i)), align='right')
	level = urwid.ProgressBar('', 'level', 0, 255)
	row = urwid.Columns([('weight', 0.2, label), level], dividechars=1)
	labels.append(label)
	levels.append(level)
	rows.append(row)

page = urwid.ListBox(urwid.SimpleFocusListWalker(rows))


# spwan thread to watch for updates

#exit(0)

DANTE = "10.35.37.22"
CTL_PORT = 8800
INFO_PORT = 4440
RMS_PORT = 8751

#LOCAL_IDENT = "001c25be39850000"
LOCAL_IDENT = "CAFECAFECAFE0000"
LOCAL_IP = "10.35.0.21"

class InfoPacket():
	# t3=0000 send
	# t3=0001 recv
	
	def __init__(self, t1, length, cookie, t2, t3, data):
		self.t1 = t1
		self.length = length
		self.cookie = cookie
		self.t2 = t2
		self.t3 = t3
		self.data = data
	
	@classmethod
	def outgoing(cls, t1, cookie, t2, t3):
		return cls(t1=t1, length=10, cookie=cookie, t2=t2, t3=t3, data=[])
		
	@classmethod
	def incoming(cls, data):
		t1, length, cookie, t2, t3 = struct.unpack("!5H", data[0:10])
		return cls(t1=t1, length=length, cookie=cookie, t2=t2, t3=t3, data=data[10:])
	
	def append_hex(self, data):
		self.append_raw(data.replace(" ", "").decode("hex"))
	
	def append_raw(self, data):
		self.data.append(data)
		self.length += len(data)
	
	def pack(self):
		out = struct.pack("!5H", self.t1, self.length, self.cookie, self.t2, self.t3)
		for d in self.data:
			out += d
		return out




# request tx channel details
#p = InfoPacket.outgoing(0x2712, 0xeeee, 0x2010, 0x0000)
#p.append_hex("0001 0001 0080")


# parse tx channel details
data = "271201bf000920100001201e00010001010c00020002011100030003011a00040004012300050005012700060006012b00070007013000080008013500090011013c000a00120141000b00130146000c0014014d000d00150152000e00160159000f0017015e00100018016300110021016800120022016e00130023017400140024017a00150025018400160026018c00170027019100180028019800190031019d001a003201a2001b003301a7001c003401ae001d003701b5001e003801ba003a000e016801ab014f01ae0000000100000000003b000e016801b1014f01b40000000100000000003c000e016801b7014f01ba0000000100000000003d000e016801bd014f01c0000000014b49434b00534e415245544f5000534e41524542544d004f484c004f485200544f4d3100544f4d320044434c49434b0041475431004547543100574c564f5831004147543200574c564f583200424756310042475632004247563300504c564f43004d4944494c004d49444952004d494449434c49434b004d494449564f580042415353004b4559564f58004b45594c004b4559520045475432004d494449324c004d494449325200464f484c00464f485200".decode("hex")

p = InfoPacket.incoming(data)
total, ret = struct.unpack("!BB", p.data[0:2])
channels = {}

for n in range(ret):
	ptr = 2+(n*6)
	n, target, label_ptr = struct.unpack("!3H", p.data[ptr:ptr+6])
	label_ptr -= 10
	label = p.data[label_ptr:p.data.index("\0", label_ptr)]
	channels[target] = label
	labels[target-1].set_text(label)
	#print target, label




# parse rms
#data = "ffff009b3ca00000001dc10412e20000417564696e617465024040bfc9c4b8bcbcb8a9bfc9c4b8bcbcb8a9a7a88bac88afb1afa7a88bac88afb1afb0cccbcdb29ca6c0b0cccbcdb29ca6c0c4b1cccafefee3e2c4b1cccafefee3e2fefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefe".decode("hex")


csock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
csock.bind(('', CTL_PORT))

rsock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
rsock.bind(('', RMS_PORT))


# request rms stream
p = InfoPacket.outgoing(0x1200, 0xeeee, 0x3010, 0x0000)
p.append_hex("0000")
p.append_hex(LOCAL_IDENT)
p.append_hex("0004 0018 0001 0020 000a")
p.append_raw("DN965x-0412e2\0test-PC\0")
p.append_hex("0001 0026 0001")
p.append_raw(struct.pack("!H", RMS_PORT))
p.append_hex("0001 0000")
p.append_raw(inet_pton(AF_INET, LOCAL_IP))
p.append_raw(struct.pack("!H", RMS_PORT))
p.append_hex("0000")

csock.sendto(p.pack(), (DANTE, CTL_PORT))



class RmsThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True
		
	def run(self):
		while True:
			data, addr = rsock.recvfrom(1024)
			p = InfoPacket.incoming(data)
			
			rms = struct.unpack("!128B", p.data[14+3:])
			for i in range(len(rms)):
				ch = i+1
				if ch in channels:
					#print ch, channels[ch], rms[i]
					levels[i].set_completion(255-rms[i])

			#data = data[24+3:]
			#for i in range(0,len(levels)):
			#	val = 255-ord(data[i])
			#	levels[i].set_completion(val)

t = RmsThread()
t.start()


def refresh(loop=None, user_data=None):
	loop.set_alarm_in(0.01, refresh)

loop = urwid.MainLoop(page, palette, unhandled_input=exit_on_q)
refresh(loop, None)

loop.run()
exit(0)
