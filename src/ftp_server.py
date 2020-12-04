import os
import socket
import subprocess
from util import *

# logger for FTP servrer program
serverLogger = setup_logger()

class FTPServer():
    """ Implementation for FTP server. The command accepted are:
        get, put and ls. FTP server has two sockets: control
        socket is used for control channel, data socket is used for
        data channel. Commands are received from FTP client by control 
        channel, data are sent to and received from FTP client by
        data channel.
    """

    def __init__(self, serverPort):
        self.__serverPort = int(serverPort)
        self.__controlChannelSocket = None
        self.__dataChannelSocket = None
        self.__clientDataChannelPort = None
        self.__clientAddr = None

    def __sendControlResponse(self, statusCode, msg, clientSocket):
        """ Send control response to FTP client with statusCode and message.
            The control response format is: 
            statusCode(3 bytes) + messageLength(5 bytes) + responseMessage

            :param statusCode:  <int> An integer indicate the FTP server status for client request.
            :param msg: <string> The response message send to FTP client
        """

		# Prepend 0's to the statusCode
		# until the length is 3 bytes
        statusCodeStr = str(statusCode)
        serverLogger.debug("The statusCode to send is: %s", statusCodeStr)

        while len(statusCodeStr) < 3:
            statusCodeStr = "0" + statusCodeStr

		# Prepend 0's to the msg size string
		# until the size is 5 bytes
        msgLen = len(msg)
        msgLenStr = str(msgLen)
        serverLogger.debug("The length of message to send is: %s bytes", msgLenStr)

        while len(msgLenStr) < 5:
            msgLenStr = "0" + msgLenStr
        
        #assemble response data
        dataStr = statusCodeStr + msgLenStr + msg

        #send response data via control channel
        dataBytes = dataStr.encode()
        sentDataLen = 0
        while sentDataLen < len(dataBytes):
            sentDataLen += clientSocket.send(dataBytes[sentDataLen:])
            serverLogger.debug("The sent data length is: %s bytes", sentDataLen)

    def __sendFileData(self, dataStr):
        """ In a client download request, send file data to client
            The data format is: 
            dataSize(10 bytes) + data

            :param dataStr:  <string> The string of data to send to FTP client.
        """

		# Prepend 0's to the size string
		# until the size is 10 bytes
        dataLen = len(dataStr)
        dataLenStr = str(dataLen)

        serverLogger.debug("The length of data to send is: %s bytes", dataLenStr)

        while len(dataLenStr) < 10:
            dataLenStr = "0" + dataLenStr
        
        #assemble data to send to FTP client
        dataStr = dataLenStr + dataStr

        #send data to FTP client via data channel
        dataBytes = dataStr.encode()
        sentDataLen = 0
        while sentDataLen < len(dataBytes):
            sentDataLen += self.__dataChannelSocket.send(dataBytes[sentDataLen:])
            serverLogger.debug("The sent data length is: %s bytes", sentDataLen)

    def __receiveClientRequests(self):
        """ Receive FTP client requests and handle the requests. Valid requests are
            get, put and ls.
            The request format is: 
            command(5 bytes) + clientDataChannelPort(5 bytes) + filenameLength(5 bytes, optional) + filename(optional)
        """

        serverLogger.info("Waiting for connections...")
            
        # Accept connections
        clientSocket = None
        clientAddr = None
        try:
            clientSocket,clientAddr = self.__controlChannelSocket.accept()
        except Exception as e:
            clientSocket.close()
            serverLogger.error(e)
            return

        serverLogger.debug("Accepted connection from server %s at port %d", clientAddr[0], clientAddr[1])
        self.__clientAddr = clientAddr[0]

        #receive client command
        command = self.__recvAll(5, clientSocket)
        command = command.strip()

        #receive client data channel port
        self.__clientDataChannelPort = int(self.__recvAll(5, clientSocket))

        #handle client requests based on request command
        serverLogger.debug("Command reveived from FTP client is: \"%s\"", command)
        if command == "get":
            #receive filename length
            filenameSize = int(self.__recvAll(5, clientSocket))
            #receive filename to download
            filename = self.__recvAll(filenameSize, clientSocket)
            serverLogger.info("Received downloading file request from client %s. File to download: %s", clientAddr[0], filename)
            #check if the request file is existing on FTP server
            if self.__validateFilename(filename) == True:
                #send control response to indicate the request is accepted
                self.__sendControlResponse(0, "Download request accepted by FTP Server.", clientSocket)
                try:
                    #send file to FTP client
                    self.__sendFile(filename)
                    #send control response to indicate completed handle the client request
                    self.__sendControlResponse(0, "Download request Completed.", clientSocket)
                    serverLogger.info("SUCCESS: Finished processing client download request.")
                except Exception as e:
                    self.__sendControlResponse(1, "Download request failed when receiving file data from client.", clientSocket)
                    serverLogger.error("FAILURE: Download request failed when receiving file data from client with error:")
                    serverLogger.error(e)  
                    clientSocket.close() 
            else:
                #send control response to indicate the request failed
                self.__sendControlResponse(2, "Download request refused by FTP Server, file not existing on server.", clientSocket)
                serverLogger.error("FAILURE: Failed to process FTP client download request, file %s not existing on Server.", filename)

        elif command == "put":
            #receive filename length
            filenameSize = int(self.__recvAll(5, clientSocket))
            #receive filename to upload
            filename = self.__recvAll(filenameSize, clientSocket)
            serverLogger.info("Received uploading file request from client %s. File to upload: %s", clientAddr[0], filename)
            #send control response to indicate the request is accepted
            self.__sendControlResponse(0, "Upload request accepted by FTP Server.", clientSocket)
            try:
                self.__receiveFile(filename)
                #send control response to indicate completed handle the client request
                self.__sendControlResponse(0, "Upload request Completed.", clientSocket)
                serverLogger.info("SUCCESS: Finished processing client upload request. Uploaded file stored at directory /ServerFiles.")
            except Exception as e:
                self.__sendControlResponse(3, "Upload request failed when sending file data to client.", clientSocket)
                serverLogger.error("FAILURE: Upload request failed when sending file data to client with error:")
                serverLogger.error(e)
                clientSocket.close()
        elif command == "ls":
            #send control response to indicate the request is accepted
            self.__sendControlResponse(0, "List server file request accepted by FTP Server.", clientSocket)
            serverLogger.info("Received list server files request from client %s.", clientAddr[0])
            try: 
                self.__sendServerFileList()
                #send control response to indicate completed handle the client request
                self.__sendControlResponse(0, "List server file request Completed.", clientSocket)
                serverLogger.info("SUCCESS: Finished processing client list files request.")
            except Exception as e:
                self.__sendControlResponse(4, "List server file failed when sending file lists to client.", clientSocket)
                serverLogger.error("FAILURE: List server file request failed when sending file list data to client with error:")
                serverLogger.error(e)
                clientSocket.close()

        clientSocket.close()

    def __recvAll(self, receiveByteLen, socket):
        """ Receive data from the given socket, the socket can be 
            either control channel socket or data channel socket.
        """

        # The buffer
        recvBuff = ""
        # The temporary buffer
        tmpBuff = ""
        
        # Keep receiving till all is received
        while len(recvBuff) < receiveByteLen:
            serverLogger.debug("About to receiving data...")
            # Attempt to receive bytes
            try:
                tmpBuff = socket.recv(receiveByteLen).decode()
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

    def __validateFilename(self, filename):
        """ Check if the given filename is existing.

            :param filename:  <string> The filename to check.

            :returns <Boolean>: Return True if the file exists, otherwise return False.
        """
        proc = subprocess.Popen(["ls ./ServerFiles"], shell=True, stdout=subprocess.PIPE)
        fileListStr = proc.stdout.read().decode()

        return True if filename in fileListStr else False

    def __sendFile(self, filename):
        """ Send file to FTP client via data channel

            :param filename:  <string> The filename of file to send to client.
        """

        #open file, read data in file and send to client
        with open("./ServerFiles/" + filename, 'r') as file:
            serverLogger.debug("Reading data from file: %s", filename)
            #read data in file
            data = file.read()
            serverLogger.debug("Finished writing to file.") 

            serverLogger.debug("Sending data from file: %s", filename)
            self.__initDataSocket()
            #send file data to FTP client
            self.__sendFileData(data) 
            self.__destroyDataSocket()
            serverLogger.debug("All data has been sent to client.") 


    def __receiveFile(self, filename):
        """ Receive file from FTP client via data channel

            :param filename:  <string> The filename of file to receive from client.
        """

        self.__initDataSocket()
        fileDataSize = int(self.__recvAll(10, self.__dataChannelSocket))
        #receive file data from client
        fileData = self.__recvAll(fileDataSize, self.__dataChannelSocket)
        self.__destroyDataSocket()
        
        serverLogger.debug("All file data received.")

        #open file and write the received data
        with open("./ServerFiles/" + filename, 'w') as file:
            serverLogger.debug("Writing data to file: %s", filename)
            file.write(fileData)
            serverLogger.debug("Finished writing to file.") 

    def __sendServerFileList(self):
        """ Send the list of files on FTP server to client via data channel
        """

        #run command to get the list of files available on server
        proc = subprocess.Popen(["ls ./ServerFiles"], shell=True, stdout=subprocess.PIPE)
        fileListStr = proc.stdout.read().decode()
        serverLogger.debug("File list on server is: \n%s", fileListStr)

        serverLogger.debug("Sending file list to client.")
        self.__initDataSocket()
        #send list of files on server via data channel
        self.__sendFileData(fileListStr)
        self.__destroyDataSocket()
        serverLogger.debug("Finished sending file list to client.")

    def __createSocket(self):
        """ Creating a TCP socket.
        """

        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return so

    def __initControlSocket(self):
        """ Create and initialize the client control channel socket.
        """

        serverLogger.debug("Current hostname is: %s", socket.gethostname())
        #create data channel socket
        self.__controlChannelSocket = self.__createSocket()
        serverLogger.debug("Server control channel socket created.")

        #bind the data channel socket to server port
        self.__controlChannelSocket.bind(("localhost", self.__serverPort))
        serverLogger.debug("Server control channel socket binded to port %d",  self.__serverPort)

        #data channel socket listen for connection
        self.__controlChannelSocket.listen(1)

    def __initDataSocket(self):
        """ Create and initialize the client data channel socket.
        """

        #create data channel socket
        self.__dataChannelSocket = self.__createSocket()
        #connect the data channel socket to FTP client
        self.__dataChannelSocket.connect((self.__clientAddr, self.__clientDataChannelPort))
        serverLogger.debug("Data socket created.")

    def __destroyControlSocket(self):
        """ Destroy the server control channel socket.
        """

        self.__controlChannelSocket.close()
        self.__controlChannelSocket = None
        self.__serverPort   = None
        serverLogger.debug("Control channel socket destroyed.")

    def __destroyDataSocket(self):
        """ Destroy the server data channel socket.
        """

        self.__dataChannelSocket.close()
        self.__dataChannelSocket = None 
        self.__clientDataChannelPort = None
        self.__clientAddr = None
        serverLogger.debug("Data channel socket destroyed.")

    def start(self): 
        """ Start the FTP server and wait for FTP client requests.
        """

        if self.__controlChannelSocket == None:
            self.__initControlSocket()

        while True:
            self.__receiveClientRequests()

    def stop(self):
        """ Stop the FTP server.
        """

        if self.__controlChannelSocket != None:
            self.__destroyControlSocket()

        if self.__dataChannelSocket != None:
            self.__destroyDataSocket()
