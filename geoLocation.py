import threading
import sys, os
from time import gmtime, strftime
import time
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap
from PyQt5 import QtGui, QtCore, QtWidgets
import urllib.request

class serialMonitor(QMainWindow):
	reader = pyqtSignal(str)
	maplink = pyqtSignal(str)
	reading = False
	logging = False
	first_conn = True
	current_port = ''
	current_baud = 9600
	lat = 0
	long = 0
	logging_dir = "serialMonitorLogs"
	filename = ''+logging_dir +'/' + strftime("%a-%d-%b-%Y-%H-%M-%S", gmtime()) + '.txt'
	baudrates = ["9600", "115200", "300", "1200", "2400", "4800", "14400", "19200", "31250", "38400", "57600"]
	apikey = "" # Google Maps Static API Key

	def __init__(self):
		super(serialMonitor, self).__init__()
		if not os.path.exists(self.logging_dir):
			os.makedirs(self.logging_dir)
		font = QtGui.QFont()
		font.setPointSize(10)
		self.startReadingPorts()
		self.portLabel = QtWidgets.QLabel()
		self.portLabel.setText("Serial port:")
		self.portLabel.move(10, 10)
		self.baudLabel = QtWidgets.QLabel()
		self.baudLabel.setText("Baud rate:")
		self.portBox = QtWidgets.QComboBox()

		self.baudBox = QtWidgets.QComboBox()
		for i in self.baudrates:
			self.baudBox.addItem(i)
		self.buttonStart = QPushButton()
		self.buttonStart.setText('Start')
		self.buttonStart.clicked.connect(self.startReading)
		self.buttonStop = QPushButton()
		self.buttonStop.setText('Stop')
		self.buttonStop.clicked.connect(self.stopReading)
		self.buttonOpen = QPushButton()
		self.buttonOpen.setText('Open map in web browser')
		self.buttonOpen.clicked.connect(self.openMap)

		self.scroll_button = QCheckBox('Autoscroll')
		self.scroll_button.setCheckState(Qt.Checked)
		self.scroll_button.stateChanged.connect(self.enableScroll)
		self.logging_button = QCheckBox('Enable logging')
		self.logging_button.stateChanged.connect(self.enableLogging)
		self.textEdit = QTextEdit(self)
		self.textEdit.setFontPointSize(10)
		self.reader.connect(self.textEdit.append)
		self.reader.connect(self.writeToFile)
		
		self.label = QtWidgets.QLabel()
		self.label.setAlignment(Qt.AlignCenter)
		self.statusbar = QStatusBar()
		self.statusbar.showMessage(" ")
		self.setGeometry(100, 100, 860, 640)
		self.setWindowTitle('ESP8266 geoLocation')
		self.layoutH = QHBoxLayout()
		self.layoutV = QVBoxLayout()

		self.layoutH.addWidget(self.portLabel)
		self.layoutH.addWidget(self.portBox)
		self.layoutH.addWidget(self.baudLabel)
		self.layoutH.addWidget(self.baudBox)
		self.layoutH.addWidget(self.scroll_button)
		self.layoutH.addWidget(self.logging_button)
		self.layoutV.addLayout(self.layoutH)

		self.layoutV.addWidget(self.buttonStart)
		self.layoutV.addWidget(self.buttonStop)
		self.layoutV.addWidget(self.label)
		self.layoutV.addWidget(self.buttonOpen)
		self.layoutV.addWidget(self.textEdit)
		self.setStatusBar(self.statusbar)
		self.widget = QWidget()
		self.widget.setLayout(self.layoutV)
		self.widget.setFont(font)
		self.setCentralWidget(self.widget)
		self.refreshMap()

	def convLat(self, latitude):
		if latitude > 0:
			dirr = "N"
			pre = ""
		else:
			dirr = "S"
			pre = "-"
		latitude = abs(latitude)
		degrees = int(latitude)
		minutes = int((latitude - degrees) * 60)
		seconds = round((latitude - degrees - minutes/60)*3600, 2)
		return(pre + "" +str(degrees)+"\xb0 "+ str(minutes)+"' " +str(seconds)+"'' " +str(dirr)+"")

	def convLon(self, longitude):
		if longitude > 0:
			dirr = "E"
			pre = ""
		else:
			dirr = "W"
			pre = "-"
		longitude = abs(longitude)
		degrees = int(longitude)
		minutes = int((longitude - degrees) * 60)
		seconds = round((longitude - degrees - minutes/60)*3600, 2)
		return(pre + "" +str(degrees)+"\xb0 "+ str(minutes)+"' " +str(seconds)+"'' " +str(dirr)+"")

	def serial_ports(self):
		ports = ['COM%s' % (i + 1) for i in range(256)]
		result = []
		while True:
			for port in ports:
				if port in result:
					try:
						s = serial.Serial(port)
						s.close()
					except(OSError, serial.SerialException):
						if port != self.current_port:
							result.remove(port)
							self.portBox.removeItem(self.portBox.findText(port))
				else:
					try:
						s = serial.Serial(port)
						s.close()
						if (self.portBox.findText(port) == -1):
							result.append(port)
							self.portBox.addItem(str(port))
					except (OSError, serial.SerialException):
						pass
			time.sleep(2)

	def enableScroll(self, state):
		if state == Qt.Checked:
			self.textEdit.moveCursor(QtGui.QTextCursor.End)
		else:
			self.textEdit.moveCursor(QtGui.QTextCursor.Start)

	def mapRefresh(self, lat, long):
		url = "http://maps.googleapis.com/maps/api/staticmap?center="+str(lat)+","+str(long)+"&markers=color:blue%7Clabel:X%7C"+str(lat)+","+str(long)+"&zoom=15&size=800x600&maptype=roadmap&key="+self.apikey+""
		data = urllib.request.urlopen(url).read()
		pixmap = QPixmap()
		pixmap.loadFromData(data)
		self.label.setPixmap(pixmap)

	def startReading(self):
		if not self.reading:
			self.reading = True
			thread = threading.Thread(target=self.read)
			thread.start()

	def startReadingPorts(self):
		thread2 = threading.Thread(target=self.serial_ports)
		thread2.start()

	def refreshMap(self):
		thread3 = threading.Thread(target=self.mapRefresh("0","0"))
		thread3.start()

	def read(self):
		self.current_port = str(self.portBox.currentText())
		self.current_baud = int(self.baudBox.currentText())
		if self.first_conn == True:
			arduino = serial.Serial(self.current_port, self.current_baud)
		else:
			self.statusbar.showMessage("Reconnecting. Waiting 20s before next connection.")
			time.sleep(20)
			arduino = serial.Serial(self.current_port, self.current_baud)
		self.statusbar.showMessage("Connected")
		while self.reading == True:
			try:
				data = arduino.readline()[:-1].decode("utf-8", "ignore")
				data2 = data.split()
				if len(data2) != 0: 
					if data2[0] == "Latitude":
						self.lat = data2[2]
					if data2[0] == "Longitude":
						self.long = data2[2]
					if data2[0] == "Accuracy":
						acc = data2[2]
						self.statusbar.showMessage("Current location: Latitude: "+self.convLat(float(self.lat))+", Longitude: "+self.convLon(float(self.long))+", Accuracy: "+acc+"")
						self.mapRefresh(self.lat, self.long)
				self.reader.emit(str(data))
			except serial.SerialException as e:
				# There is no new data from serial port
				self.reader.emit("Disconnect of USB->UART occured. \nRestart needed!")
				self.statusbar.showMessage("Disconnected")
				quit()
		arduino.close()

	def stopReading(self):
		self.reading = False
		self.first_conn = False
		self.statusbar.showMessage("Disconnected")

	def enableLogging(self, state):
		if state == Qt.Checked:
			self.logging = True
			file = open(str(self.filename), 'w')
			file.write("serialMonitor log file, created: " + strftime("%a %d %b %Y %H:%M:%S", gmtime()) + "\n")
			file.write("Selected port: " + self.current_port + ", baud rate: " + str(self.current_baud) + "\n")
			file.write("---------------------------------------------------------\n")
			file.close()

	def openMap(self):
		os.startfile('https://www.google.com/maps/search/?api=1&query='+str(self.lat)+','+str(self.long)+"")

	def writeToFile(self, data):
		if self.logging == True:
			file = open(str(self.filename), 'a', encoding='utf-8')
			file.write("" + strftime("%a %d %b %Y %H:%M:%S", gmtime()) + " : ")
			file.write(str(data))
			file.write("\n")
			file.close()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	window = serialMonitor()
	window.show()
	sys.exit(app.exec_())