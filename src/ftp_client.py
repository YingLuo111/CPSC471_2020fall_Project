import socket
import os
import sys
from util import *

clientLogger = setup_logger()

class FTPClient():

    def __init__(self, serverName, serverPort):
        self.__serverName    = serverName
        self.__serverPort    = int(serverPort)
        self.__sendSocket    = None
        self.__receiveSocket = None
        self.__receivePort   = None

    def __sendData(self, dataStr, commandStr, filenameStr):
        clientLogger.info("Sending data to FTP server for command %s", commandStr)

		# Prepend spaces to the command string
		# until the size is 5 bytes
        commandLen = len(commandStr)
        while commandLen < 5:
            commandStr = " " + commandStr
            commandLen = len(commandStr)    
        clientLogger.debug("CommandStr to send is \"%s\"", commandStr)

        filenameStr = ""
        if commandStr.trim() == "get" or commandStr.trim() == "put":
            # Prepend spaces to the filename string
            # until the size is 30 bytes
            filenameLen = len(filenameStr)

            if filenameLen > 50:
                print("Error: filename too long, maximum filename length is 50")
                return

            while filenameLen < 50:
                filenameStr = " " + filenameStr
                filenameLen = len(filenameStr)
            
            clientLogger.debug("filenameLen is: %d", filenameLen)

		# Prepend 0's to the size string
		# until the size is 10 bytes
        dataLen = len(dataStr)
        dataLenStr = str(dataLen)
        clientLogger.debug("dataLenStr is: %d", dataLenStr)
        while len(dataLenStr) < 10:
            dataLenStr = "0" + dataLenStr
        
        if commandStr.trim() == "ls":
            dataStr = commandStr
        elif commandStr.trim() == "get":
            dataStr = commandStr + filenameStr
        elif commandStr.trim() == "put":
            dataStr = commandStr + filenameStr + dataLenStr + dataStr

        sentDataLen = 0
        clientLogger.debug("Size of total data to send to FTP server: %d", len(dataStr))
        while sentDataLen < len(dataStr):
            clientLogger.debug("Begin to send data to FTP server")
            try:
                sentDataLen += self.__sendSocket.send(dataStr[sentDataLen:])
            except Exception as e:
                clientLogger.error(e)
                return
            clientLogger.debug("Size of data sent to FTP server: %d", sentDataLen)

    def __receiveData(self):
            
        print("Waiting for connections...")
            
        # Accept connections
        serverSock, addr = self.__receiveSocket.accept()
        
        print("Accepted connection from server: ", addr)
        print("\n")
        
        # The buffer to all data received from the
        # the client.
        fileData = ""
        
        # The size of the incoming file
        fileSize = 0	
        
        # The buffer containing the file size
        fileSizeBuff =  self.__recvAll(10)
            
        # Get the file size
        fileSize = int(fileSizeBuff)
        
        print("The file size is ", fileSize)
        
        # Get the file data
        fileData = self.__recvAll(fileSize)
        
        print("All file data received.")

        return fileData

    def __recvAll(self, receiveByteLen):

        # The buffer
        recvBuff = ""
        
        # The temporary buffer
        tmpBuff = ""
        
        # Keep receiving till all is received
        while len(recvBuff) < receiveByteLen:
            
            # Attempt to receive bytes
            tmpBuff =  self.__receiveSocket.recv(receiveByteLen)
            
            # The other side has closed the socket
            if not tmpBuff:
                break
            
            # Add the received bytes to the buffer
            recvBuff += tmpBuff
        
        return recvBuff

    def __uploadFile(self, filename):
        with open("./ClientFiles/upload/" + filename, 'r') as file:
            data = file.read()
            self.__sendData(data, "put", filename)   


    def __downloadFile(self, filename):
        self.__sendData("", "get", filename)
        data = self.__receiveData()

        with open("./ClientFiles/download/" + filename, 'w') as file:
            file.write(data)   

    def __listServerFiles(self):
        self.__sendData("", "ls", "")
        serverFileInfo = self.__receiveData()

        print(serverFileInfo)

    def __createSocket(self):
        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return so

    def __initSendSocket(self):
        self.__sendSocket = self.__createSocket()
        self.__sendSocket.connect((self.__serverName, self.__serverPort))
        clientLogger.debug("Client send socket created.")

    def __initReceiveSocket(self):
        self.__receiveSocket = self.__createSocket()
        clientLogger.debug("Client receiving socket created.")

        host = socket.gethostbyname(socket.gethostname())
        self.__receiveSocket.bind((host, 0))
        self.__receivePort = self.__receiveSocket.getsockname()[1]
        clientLogger.debug("Client receiving socket binded to port %d",  self.__receivePort)

        self.__receiveSocket.listen(1)

    def __destroySendSocket(self):
        self.__sendSocket.close()
        self.__sendSocket = None 
        clientLogger.debug("Client send socket destroyed.") 

    def __destroyReceiveSocket(self):
        self.__receiveSocket.close()
        self.__receiveSocket = None
        self.__receivePort   = None
        clientLogger.debug("Client receive socket destroyed.")

    def executeControlCommand(self, command):
        willStopClient = False

        if self.__sendSocket == None:
            clientLogger.debug("Creating client send socket.")
            self.__sendSocket = self.__createSocket()
        elif self.__receiveSocket == None:
            clientLogger.debug("Creating client receive socket.")
            self.__receiveSocket = self.__createSocket()

        operation = command[0]
        clientLogger.debug("Received client command: %s", operation)

        if len(command) == 2:
            filename = command[1]
            if operation == "get":
                self.__downloadFile(filename)
            elif operation == "put":
                self.__uploadFile(filename)
        else:
            if operation == "ls":
                self.__listServerFiles()
            elif operation == "quit":
                self.stop()
                willStopClient = True

        return willStopClient

    def start(self):
        if self.__sendSocket == None:
            self.__initSendSocket()
        
        if self.__receiveSocket == None:
            self.__initReceiveSocket()

    def stop(self):
        if self.__sendSocket != None:
            self.__destroySendSocket()

        if self.__receiveSocket != None:
            self.__destroyReceiveSocket()