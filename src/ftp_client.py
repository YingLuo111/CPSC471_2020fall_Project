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

    def __sendData(self, dataStr, commandStr, filenameStr):
        clientLogger.debug("Sending data to FTP server for command %s", commandStr)

		# Prepend spaces to the command string
		# until the size is 5 bytes
        commandLen = len(commandStr)
        while commandLen < 5:
            commandStr = " " + commandStr
            commandLen = len(commandStr)    
        clientLogger.debug("CommandStr to send is \"%s\"", commandStr)

        if commandStr.strip() == "get" or commandStr.strip() == "put":
            # Prepend spaces to the filename string
            # until the size is 30 bytes
            filenameLen = len(filenameStr)

            if filenameLen > 50:
                clientLogger.Error("Error: filename too long, maximum filename length is 50")
                return

            while filenameLen < 50:
                filenameStr = " " + filenameStr
                filenameLen = len(filenameStr)
            
            clientLogger.debug("filenameLen is: %d", filenameLen)

		# Prepend 0's to the size string
		# until the size is 10 bytes
        dataLen = len(dataStr)
        dataLenStr = str(dataLen)
        clientLogger.debug("dataLenStr is: %s", dataLenStr)
        while len(dataLenStr) < 10:
            dataLenStr = "0" + dataLenStr
        
        if commandStr.strip() == "ls":
            dataStr = commandStr
        elif commandStr.strip() == "get":
            dataStr = commandStr + filenameStr
        elif commandStr.strip() == "put":
            dataStr = commandStr + filenameStr + dataLenStr + dataStr

        dataToSend = dataStr.encode()
        sentDataLen = 0
        clientLogger.debug("Size of total data to send to FTP server: %d", len(dataStr))
        while sentDataLen < len(dataToSend):
            clientLogger.debug("Begin to send data to FTP server")
            try:
                sentDataLen += self.__sendSocket.send(dataToSend[sentDataLen:])
            except Exception as e:
                self.__sendSocket.close()
                clientLogger.error(e)
                return
            clientLogger.debug("Size of data sent to FTP server: %d", sentDataLen)

    def __receiveData(self):
        fileData = ""	
        
        # The buffer containing the file size
        fileSize =  self.__recvAll(10, self.__sendSocket)
            
        # Get the file size
        fileSize = int(fileSize.strip())
        
        clientLogger.debug("The file size is %d", fileSize)
        
        # Get the file data
        fileData = self.__recvAll(fileSize, self.__sendSocket)
        
        clientLogger.debug("All file data received.")

        return fileData

    def __recvAll(self, receiveByteLen, serverSocket):

        # The buffer
        recvBuff = ""
        
        # The temporary buffer
        tmpBuff = ""
        
        # Keep receiving till all is received
        while len(recvBuff) < receiveByteLen:
            
            # Attempt to receive bytes
            tmpBuff = serverSocket.recv(receiveByteLen).decode()
            
            # The other side has closed the socket
            if not tmpBuff:
                break
            
            # Add the received bytes to the buffer
            recvBuff = recvBuff + tmpBuff
        
        return recvBuff

    def __uploadFile(self, filename):
        try:
            print("Uploading file \"" + filename + "\" to FTP server...")
            with open("./ClientFiles/upload/" + filename, 'r') as file:
                data = file.read()
                self.__sendData(data, "put", filename) 
            print("Upload succeeded.") 
        except Exception as e:
            clientLogger.error(e) 


    def __downloadFile(self, filename):
        try:
            print("Downloading file \"" + filename + "\" from FTP server...", filename)
            self.__sendData("", "get", filename)
            fileData = self.__receiveData()
            with open("./ClientFiles/download/" + filename, 'w') as file:
                file.write(fileData) 
            print("Download succeeded. File stored at directory /ClientFiles/download.")  
        except Exception as e:
            clientLogger.error(e) 

    def __listServerFiles(self):
        self.__sendData("", "ls", "")
        try:
            serverFileInfo = self.__receiveData()
        except Exception as e:
            print(e)
            return

        print("Files on FTP server are:")
        print(serverFileInfo)

    def __createSocket(self):
        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return so

    def __initSendSocket(self):
        self.__sendSocket = self.__createSocket()
        self.__sendSocket.connect((self.__serverName, self.__serverPort))
        clientLogger.debug("Client send socket created.")

    def __destroySendSocket(self):
        self.__sendSocket = None 
        clientLogger.debug("Client send socket destroyed.") 


    def executeControlCommand(self, command):
        willStopClient = False

        operation = command[0]
        clientLogger.debug("Received client command: %s", operation)

        if len(command) == 2:
            filename = command[1]
            if operation == "get":
                self.__initSendSocket()
                self.__downloadFile(filename)
                self.__destroySendSocket()
            elif operation == "put":
                self.__initSendSocket()
                self.__uploadFile(filename)
                self.__destroySendSocket()
        else:
            if operation == "ls":
                self.__initSendSocket()
                self.__listServerFiles()
                self.__destroySendSocket()
            elif operation == "quit":
                self.stop()
                willStopClient = True

        return willStopClient

    def start(self):
        if self.__sendSocket == None:
            self.__initSendSocket()

    def stop(self):
        if self.__sendSocket != None:
            self.__destroySendSocket()