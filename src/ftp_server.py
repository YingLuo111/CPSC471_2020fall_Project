import socket
import subprocess
from util import *

serverLogger = setup_logger()

class FTPServer():
    
    def __init__(self, serverPort):
        self.__serverSocket = None
        self.__serverPort = int(serverPort)

    def __sendData(self, dataStr, clientSocket):
		# Prepend 0's to the size string
		# until the size is 10 bytes
        dataLen = len(dataStr)
        dataLenStr = str(dataLen)

        serverLogger.debug("The length of data to send is: %s bytes", dataLenStr)

        while len(dataLenStr) < 10:
            dataLenStr = "0" + dataLenStr
        
        dataStr = dataLenStr + dataStr

        dataBytes = dataStr.encode()
        sentDataLen = 0
        while sentDataLen < len(dataBytes):
            sentDataLen += clientSocket.send(dataBytes[sentDataLen:])
            serverLogger.debug("The sent data length is: %s bytes", sentDataLen)

        clientSocket.close()

    def __receiveData(self):
            
        serverLogger.info("Waiting for connections...")
            
        # Accept connections
        clientSocket = None
        clientAddr = None
        try:
            clientSocket,clientAddr = self.__serverSocket.accept()
        except Exception as e:
            serverLogger.error(e)
            return
        serverLogger.debug("Accepted connection from server %s at port %d", clientAddr[0], clientAddr[1])
        
        command = self.__recvAll(5, clientSocket)
        command = command.strip()

        serverLogger.debug("Command reveived from FTP client is: \"%s\"", command)
        if command == "get":
            filename = self.__recvAll(50, clientSocket)
            filename = filename.strip()
            serverLogger.info("Received downloading file request. File to download: %s", filename)
            self.__sendFile(filename, clientSocket)
            serverLogger.info("Finished processing client download request.")
        elif command == "put":
            filename = self.__recvAll(50, clientSocket)
            filename = filename.strip()
            serverLogger.info("Received uploading file request. File to upload: %s", filename)
            fileSize =  self.__recvAll(10, clientSocket)
            fileSize = int(fileSize.strip())
            serverLogger.debug("The length of data to upload is: %s bytes", fileSize)
            self.__receiveFile(filename, fileSize, clientSocket)
            serverLogger.info("Finished processing client upload request. Uploaded file stored at directory /ServerFiles.")
        elif command == "ls":
            serverLogger.info("Received list server files request.")
            self.__sendServerFileList(clientSocket)
            serverLogger.info("Finished processing client list files request.")

    def __recvAll(self, receiveByteLen, clientSocket):
        # The buffer
        recvBuff = ""
        # The temporary buffer
        tmpBuff = ""
        
        # Keep receiving till all is received
        while len(recvBuff) < receiveByteLen:
            serverLogger.debug("About to receiving data...")
            # Attempt to receive bytes
            try:
                tmpBuff = clientSocket.recv(receiveByteLen).decode()
            except Exception as e:
                serverLogger.error(e)
                break
            serverLogger.debug("Received data...")
            # The other side has closed the socket
            if not tmpBuff:
                serverLogger.debug("Connection closed from client side.")
                break
            
            # Add the received bytes to the buffer
            recvBuff = recvBuff + tmpBuff

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

            clientSocket.close() 


    def __receiveFile(self, filename, fileSize, clientSocket):
        # Get the file data
        fileData = self.__recvAll(fileSize, clientSocket)
        
        serverLogger.debug("All file data received.")

        with open("./ServerFiles/" + filename, 'w') as file:
            serverLogger.debug("Writing data to file: %s", filename)
            file.write(fileData)
            serverLogger.debug("Finished writing to file.") 

        clientSocket.close() 

    def __sendServerFileList(self, clientSocket):
        proc = subprocess.Popen(["ls ./ServerFiles"], shell=True, stdout=subprocess.PIPE)
        fileListStr = proc.stdout.read().decode()
        serverLogger.debug("File list on server is: %s", fileListStr)

        serverLogger.debug("Sending file list to client.")
        self.__sendData(fileListStr, clientSocket)
        serverLogger.debug("Finished sending file list to client.")

    def __createSocket(self):
        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return so

    def __initReceiveSocket(self):
        serverLogger.debug("Current hostname is: %s", socket.gethostname())
        self.__serverSocket = self.__createSocket()
        serverLogger.debug("Server receiving socket created.")

        self.__serverSocket.bind(('localhost', self.__serverPort))
        serverLogger.debug("Server receiving socket binded to port %d",  self.__serverPort)

        self.__serverSocket.listen(1)

    def __destroyReceiveSocket(self):
        self.__serverSocket.close()
        self.__serverSocket = None
        self.__serverPort   = None
        serverLogger.debug("Server receiving socket destroyed.")

    def start(self):        
        if self.__serverSocket == None:
            self.__initReceiveSocket()

        while True:
            self.__receiveData()

    def stop(self):
        if self.__serverSocket != None:
            self.__destroyReceiveSocket()
