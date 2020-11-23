import socket
import os
from util import *

serverLogger = setup_logger()

class FTPServer():
    
    def __init__(self, serverPort):
        self.__receiveSocket = None
        self.__receivePort = int(serverPort)

    def __sendData(self, dataStr, sendSocket):
		# Prepend 0's to the size string
		# until the size is 10 bytes
        dataLen = len(dataStr)
        dataLenStr = str(dataLen)

        serverLogger.debug("The length of data to send is: %s bytes", dataLenStr)

        while len(dataLenStr) < 10:
            dataLenStr = "0" + dataLenStr
        
        dataStr = dataLenStr + dataStr

        sentDataLen = 0
        while sentDataLen < len(dataStr):
            sentDataLen += sendSocket.send(dataStr[sentDataLen:])
            serverLogger.debug("The sent data length is: %s bytes", sentDataLen)

        sendSocket.close()

    def __receiveData(self):
            
        serverLogger.info("Waiting for connections...")
            
        # Accept connections
        clientSocket, clientAddr = self.__receiveSocket.accept()
        serverLogger.debug("Accepted connection from server: ", clientAddr)	
        
        command = self.__recvAll(5)
        serverLogger.debug("Command reveived from FTP client is: \"%s\"", command)
        if command == "get":
            filename = self.__recvAll(50)
            print("Received downloading file request. File to download: %s", filename)
            self.__sendFile(filename, clientSocket)
        elif command == "put":
            filename = self.__recvAll(50)
            print("Received uploading file request. File to upload: %s", filename)
            fileSizeStr =  self.__recvAll(10)
            serverLogger.debug("The length of data to upload is: %s bytes", fileSizeStr)
            fileSize = int(fileSizeStr)
            self.__receiveFile(filename, fileSize)
        elif command == "ls":
            print("Received list server files request.")
            self.__sendServerFileList(clientSocket)

    def __recvAll(self, receiveByteLen):
        # The buffer
        recvBuff = ""
        # The temporary buffer
        tmpBuff = ""
        
        # Keep receiving till all is received
        while len(recvBuff) < receiveByteLen:
            serverLogger.debug("About to receiving data...")
            # Attempt to receive bytes
            try:
                tmpBuff =  self.__receiveSocket.recv(receiveByteLen)
            except Exception as e:
                serverLogger.error(e)
            serverLogger.debug("Received data...")
            # The other side has closed the socket
            if not tmpBuff:
                serverLogger.debug("Connection closed from client side.")
                break
            
            # Add the received bytes to the buffer
            recvBuff += tmpBuff

            serverLogger.debug("Data received %d bytes.", len(recvBuff))
        
        return recvBuff

    def __sendFile(self, filename, clientSocket):
        with open("./ServerFiles/" + filename, 'r') as file:
            serverLogger.debug("Reading data from file: %s", filename)
            data = file.read()
            serverLogger.debug("Finished writing to file.") 

            serverLogger.debug("Sending data from file: %s", filename)
            self.__sendData(data, clientSocket) 
            serverLogger.debug("All data has been sent to client.")  


    def __receiveFile(self, filename, fileSize):
        # Get the file data
        fileData = self.__recvAll(fileSize)
        
        print("All file data received.")

        with open("./ServerFiles/" + filename, 'w') as file:
            serverLogger.debug("Writing data to file: %s", filename)
            file.write(fileData)
            serverLogger.debug("Finished writing to file.")  

    def __sendServerFileList(self, clientSocket):
        fileListStr = os.system("ls ./ServerFiles")
        serverLogger.debug("File list on server is: %s", fileListStr)

        serverLogger.debug("Sending file list to client.")
        self.__sendData(fileListStr, clientSocket)
        serverLogger.debug("Finished sending file list to client.")

    def __createSocket(self):
        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return so

    def __initReceiveSocket(self):
        serverLogger.debug("Current hostname is: %s", socket.gethostname())
        self.__receiveSocket = self.__createSocket()
        serverLogger.debug("Server receiving socket created.")

        host = socket.gethostbyname(socket.gethostname())
        self.__receiveSocket.bind((host, self.__receivePort))
        serverLogger.debug("Server receiving socket binded to port %d",  self.__receivePort)

        self.__receiveSocket.listen(1)

    def __destroyReceiveSocket(self):
        self.__receiveSocket.close()
        self.__receiveSocket = None
        self.__receivePort   = None
        serverLogger.debug("Server receiving socket destroyed.")

    def start(self):        
        if self.__receiveSocket == None:
            self.__initReceiveSocket()

        while True:
            self.__receiveData()

    def stop(self):
        if self.__receiveSocket != None:
            self.__destroyReceiveSocket()
