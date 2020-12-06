import socket
import subprocess
from util import *

# logger for FTP client program
clientLogger = setup_logger()

class FTPClient():
    """ Implementation for FTP client. The command accepted are:
        get, put, ls and quit. FTP client has two sockets: control
        socket is used for control channel, data socket is used for
        data channel. Commands are sent to FTP server by control 
        channel, data are sent to and received from FTP server by
        data channel.
    """

    def __init__(self, serverName, serverPort):
        self.__serverName      = serverName
        self.__serverPort      = int(serverPort)
        self.__dataChannelPort = None
        self.__dataChannelSocket    = None
        self.__controlChannelSocket = None

    def __sendControlData(self, commandStr, filenameStr):
        """ Send control request with data to FTP server.
            The control request format is: 
            command(5 bytes) + clientDataChannelPort(5 bytes) + filenameLength(5 bytes) + filename(optional)

            :param commandStr:  <string> Command send to FTP server.
            :param filenameStr: <string> The filename to upload or download from FTP server
                                for ls command, the filename is an empty string. 

            :returns <boolean>: return True if successfully send control data to FTP server, 
                                otherwise return False
        """

        clientLogger.debug("Sending control data to FTP server...")

		# Prepend spaces to the command string
		# until the size is 5 bytes
        commandLen = len(commandStr)
        while commandLen < 5:
            commandStr = " " + commandStr
            commandLen = len(commandStr)    
        clientLogger.debug("Command will send to server is \"%s\"", commandStr)

        # Prepend 0's to the data channel port
        # until the size is 5 bytes
        dataChannelPortStr = str(self.__dataChannelPort)
        clientLogger.debug("FTP client data channel port is: %s", dataChannelPortStr)
        while len(dataChannelPortStr) < 5:
            dataChannelPortStr = "0" + dataChannelPortStr

        # Prepend 0's to the filename size string
        # until the size is 5 bytes
        filenameLen = len(filenameStr)
        filenameLenStr = str(filenameLen)
        clientLogger.debug("Filename length is: %s", filenameLenStr)
        while len(filenameLenStr) < 5:
            filenameLenStr = "0" + filenameLenStr
        
        #assemble control data send to FTP server
        controlDataStr = ""
        if commandStr.strip() == "ls":
            controlDataStr = commandStr + dataChannelPortStr
        elif commandStr.strip() == "get" or commandStr.strip() == "put":
            controlDataStr = commandStr + dataChannelPortStr + filenameLenStr + filenameStr

        #send control data to FTP server
        dataToSend = controlDataStr.encode()
        sentDataLen = 0
        clientLogger.debug("Total size of control data will send to FTP server is: %d", len(dataToSend))
        while sentDataLen < len(dataToSend):
            clientLogger.debug("Sending control data to FTP server...")
            try:
                sentDataLen += self.__controlChannelSocket.send(dataToSend[sentDataLen:])
            except Exception as e:
                clientLogger.error(e)
                return False
            clientLogger.debug("Size of data sent to FTP server: %d", sentDataLen)

        return True

    def __sendFileData(self, dataStr, serverSocket):
        """ Send file data to FTP server in a upload request.
            The file request format is: filesize(10 bytes) + filedata

            :param dataStr: <string> The file data send to FTP server. 

            :returns <tuple>: return a tuple of (True, dataSizeSent) if successfully send file data to FTP server, 
                                otherwise return (False, dataSizeSend)
        """

        clientLogger.debug("Sending file data to FTP server...")

		# Prepend 0's to the size string
		# until the size is 10 bytes
        dataLen = len(dataStr)
        dataLenStr = str(dataLen)
        clientLogger.debug("Size of data to send to FTP server is: %s", dataLenStr)
        while len(dataLenStr) < 10:
            dataLenStr = "0" + dataLenStr
        
        #assemble data to send to FTP server
        dataStr = dataLenStr + dataStr

        #send data to FTP server
        dataToSend = dataStr.encode()
        sentDataLen = 0
        clientLogger.debug("Size of total data to send to FTP server: %d", len(dataToSend))
        while sentDataLen < len(dataToSend):
            try:
                sentDataLen += serverSocket.send(dataToSend[sentDataLen:])
            except Exception as e:
                clientLogger.error(e)
                return False, sentDataLen
            clientLogger.debug("Size of data sent to FTP server: %d", sentDataLen)

        return True, len(dataToSend)

    def __receiveControlData(self):
        """ Receive control response from FTP server.
            The control response format is:
            statusCode(3 bytes) + messageSize(5 bytes) + message

            :returns <tuple>: a tuple of response status code and server message.
        """
        serverMsg = ""	
        
        # The buffer containing the request status code from FTP server
        statusCodeStr =  self.__recvAll(3, self.__controlChannelSocket)
            
        # Get the status
        statusCode = int(statusCodeStr)
        
        clientLogger.debug("The FTP server response status code is %d", statusCode)
        
        # The buffer containing the server response message size
        msgSizeStr =  self.__recvAll(5, self.__controlChannelSocket)
            
        # Get the server response message size
        msgSize = int(msgSizeStr.strip())
        
        clientLogger.debug("The FTP server response message size is %d", msgSize)
        
        # Get the server response message
        serverMsg = self.__recvAll(msgSize, self.__controlChannelSocket)

        return statusCode, serverMsg

    def __receiveFileData(self, serverSocket):
        """ Receive file data from FTP server in a download request.

            :returns <tuple>: A tuple contains the downloaded file data and download data size.
        """

        receivedData = ""	
        
        # The buffer containing the file size
        dataSize =  self.__recvAll(10, serverSocket)
            
        # Get the file size
        dataSize = int(dataSize.strip())
        
        clientLogger.debug("The file size is %d", dataSize)
        
        # Get the file data
        receivedData = self.__recvAll(dataSize, serverSocket)
        
        clientLogger.debug("All file data received.")

        return receivedData, dataSize

    def __recvAll(self, receiveByteLen, socket):
        """ Receive data from the given socket.

            :returns <string>: the decoded received data.
        """

        # The buffer
        recvBuff = ""
        
        # The temporary buffer
        tmpBuff = ""
        
        # Keep receiving till all is received
        while len(recvBuff) < receiveByteLen:
            
            # Attempt to receive bytes
            tmpBuff = socket.recv(receiveByteLen).decode()
            
            # The other side has closed the socket
            if not tmpBuff:
                break
            
            # Add the received bytes to the buffer
            recvBuff = recvBuff + tmpBuff
        
        return recvBuff

    def __uploadFile(self, filename, serverSocket):
        """ Upload file to FTP server.

            :param filename: <string> the filename of the file to be uploaded to 
                             FTP server.

            :returns <boolean>: return True if successfully uploaded file to FTP server, 
                                otherwise return False
        """

        try:
            print("\nUploading file \"" + filename + "\" to FTP server...")
            #open file, read the content of file and send to FTP server
            with open("./ClientFiles/upload/" + filename, 'r') as file:
                #read file
                data = file.read()
                #send file to FTP server
                isFileDataSent, dataSizeSent = self.__sendFileData(data, serverSocket)
                if isFileDataSent == True:
                    print("\nSUCCESS: File {} uploaded. Sent {} bytes to FTP server total.".format(filename, dataSizeSent)) 
                    return True
                else:
                    print("File data failed to upload to FTP server.")
                    return False
        except Exception as e:
            clientLogger.error(e)
            return False



    def __downloadFile(self, filename, serverSocket):
        """ Download file from FTP server.

            :param filename: <string> the filename of the file to be downlowded from 
                             FTP server.

            :returns <boolean>: return True if successfully download file from FTP server, 
                                otherwise return False
        """

        try:
            print("\nDownloading file \"" + filename + "\" from FTP server...")
            #receive file data from FTP server
            fileData, fileDataSize = self.__receiveFileData(serverSocket)
            #create a file and write the downloaded file data
            with open("./ClientFiles/download/" + filename, 'w') as file:
                file.write(fileData) 
            print("\nSUCCESS: File {} downloaded. Received {} bytes total from FTP server. File stored at directory /ClientFiles/download.".format(filename, fileDataSize)) 
            return True 
        except Exception as e:
            clientLogger.error(e)
            return False

    def __listServerFiles(self, serverSocket):
        """ Print the list of files available on FTP server.
    
            :returns <boolean>: return True if successfully retrieved file list on FTP server, 
                                otherwise return False
        """

        try:
            #retrieve file list on FTP server
            serverFileInfo, _ = self.__receiveFileData(serverSocket)
            print("\nSUCCESS: Files on FTP server are")
            print(serverFileInfo)
            return True
        except Exception as e:
            print(e)
            return False

    def __validateFilename(self, filename):
        """ Check if the given filename is existing.

            :param filename:  <string> The filename to check.

            :returns <Boolean>: Return True if the file exists, otherwise return False.
        """
        proc = subprocess.Popen(["ls ./ClientFiles/upload"], shell=True, stdout=subprocess.PIPE)
        fileListStr = proc.stdout.read().decode()
    
        fileList = fileListStr.split("\n")

        return True if filename in fileList else False

    def executeControlCommand(self, command):
        """ Execute the command from user input.
    
            :param command: <string> the user input command.
            :returns <boolean>: return True if FTP client need to be stopped, 
                                otherwise return False
        """

        #flag indicate if the FTP client need to be quit
        willStopClient = False

        try: 
            #get user input command
            operation = command[0].strip()
            clientLogger.debug("Received client command: %s", operation)

            if self.__controlChannelSocket == None and operation != "quit":
                self.__initControlSocket()

            if len(command) == 2:
                #get user input filename
                filename = command[1]

                #create data channel socket
                self.__initDataSocket()

                #execute get command and download file from FTP server
                if operation == "get":

                    #send control data to control channel
                    isControlDataSent = self.__sendControlData(operation, filename)
                    if isControlDataSent == True:
                        #get FTP server response
                        statusCode, msg = self.__receiveControlData()
                        if statusCode == 0:
                            print("\nFTP server response: {}".format(msg))

                            # Accept server connections to data channel
                            serverSocket = None
                            serverAddr = None
                            try:
                                serverSocket,serverAddr = self.__dataChannelSocket.accept()
                                clientLogger.debug("Accepted connection from server %s at port %d", serverAddr[0], serverAddr[1])

                                #download file from FTP server
                                isDownloadSucceed = self.__downloadFile(filename, serverSocket)

                                #if download success, get response message from FTP server
                                if isDownloadSucceed == True:
                                    statusCode, msg = self.__receiveControlData()
                                    if statusCode == 0:
                                        print("\nFTP server response: {}".format(msg))
                                    else:
                                        print("\nFTP server response: {}".format(msg))

                                serverSocket.close()
                            except Exception as e:
                                serverSocket.close()
                                if self.__controlChannelSocket != None:
                                    self.__destroyControlSocket()
                                if self.__dataChannelSocket != None:
                                    self.__destroyDataSocket()
                                clientLogger.error(e)
                                return
                        else:
                            print("\nFTP server response: {}".format(msg))

                    else:
                        print("\nFailed to send control data of command {} to FTP server.".format(operation))

                #execute put command and upload file to FTP server
                elif operation == "put":
                    #check if the filename to upload is valid
                    if self.__validateFilename(filename) == False:
                        print("\nError: could not upload, file /ClientFiles/{} doesn't exist".format(filename))
                        if self.__controlChannelSocket != None:
                            self.__destroyControlSocket()
                        if self.__dataChannelSocket != None:
                            self.__destroyDataSocket()
                        return

                    #send control data to control channel
                    isControlDataSent = self.__sendControlData(operation, filename)
                    if isControlDataSent == True:
                        #get FTP server response
                        statusCode, msg = self.__receiveControlData()
                        if statusCode == 0:
                            print("\nFTP server response: {}".format(msg))

                            # Accept server connections to data channel
                            serverSocket = None
                            serverAddr = None
                            try:
                                serverSocket,serverAddr = self.__dataChannelSocket.accept()
                                clientLogger.debug("Accepted connection from server %s at port %d", serverAddr[0], serverAddr[1])

                                #upload file to FTP server
                                isUploadSucceed = self.__uploadFile(filename, serverSocket)

                                #if download success, get response message from FTP server
                                if isUploadSucceed == True:
                                    statusCode, msg = self.__receiveControlData()
                                    if statusCode == 0:
                                        print("\nFTP server response: {}".format(msg))
                                    else:
                                        print("\nFTP server response: {}".format(msg))

                                serverSocket.close()
                            except Exception as e:
                                serverSocket.close()
                                if self.__controlChannelSocket != None:
                                    self.__destroyControlSocket()
                                if self.__dataChannelSocket != None:
                                    self.__destroyDataSocket()
                                clientLogger.error(e)
                                return
                        else:
                            print("\nFTP server response: {}".format(msg))
                    else:
                        print("\nFailed to send control data of command {} to FTP server.".format(operation))

                #destroy data channel socket
                self.__destroyDataSocket()
            
            #execute ls command and get file list on FTP server
            else:
                if operation == "ls":
                    #create data channel socket
                    self.__initDataSocket()

                    #send control data to control channel
                    isControlDataSent = self.__sendControlData(operation, "")
                    if isControlDataSent == True:
                        #get FTP server response
                        statusCode, msg = self.__receiveControlData()
                        if statusCode == 0:
                            print("\nFTP server response: {}".format(msg))

                            # Accept server connections to data channel
                            serverSocket = None
                            serverAddr = None
                            try:
                                serverSocket,serverAddr = self.__dataChannelSocket.accept()
                                clientLogger.debug("Accepted connection from server %s at port %d", serverAddr[0], serverAddr[1])

                                #get file list from FTP server
                                isListFileSucceed = self.__listServerFiles(serverSocket)

                                #if download success, get response message from FTP server
                                if isListFileSucceed == True:
                                    statusCode, msg = self.__receiveControlData()
                                    if statusCode == 0:
                                        print("FTP server response: {}".format(msg))
                                    else:
                                        print("FTP server response: {}".format(msg))

                                serverSocket.close()
                            except Exception as e:
                                serverSocket.close()
                                if self.__controlChannelSocket != None:
                                    self.__destroyControlSocket()
                                if self.__dataChannelSocket != None:
                                    self.__destroyDataSocket()
                                clientLogger.error(e)
                                return
                        else:
                            print("\nFTP server response: {}".format(msg))
                    else:
                        print("\nFailed to send control data of command {} to FTP server.".format(operation))

                    #destroy data channel socket
                    self.__destroyDataSocket()

                #execute quit command and terminate the FTP client
                elif operation == "quit":
                    self.stop()
                    willStopClient = True

            if self.__controlChannelSocket != None:
                self.__destroyControlSocket()

        except Exception as e:
            clientLogger.error(e)
            if self.__controlChannelSocket != None:
                self.__destroyControlSocket()
            if self.__dataChannelSocket != None:
                self.__destroyDataSocket()
            return willStopClient

        return willStopClient

    def __createSocket(self):
        """ Creating a TCP socket.
        """

        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return so

    def __initControlSocket(self):
        """ Create and initialize the client control channel socket.
        """

        #create control channel socket
        self.__controlChannelSocket = self.__createSocket()
        #connect the control channel socket to FTP server
        self.__controlChannelSocket.connect((self.__serverName, self.__serverPort))
        clientLogger.debug("Control socket created.")

    def __initDataSocket(self):
        """ Create and initialize the client data channel socket.
        """

        #create data channel socket
        self.__dataChannelSocket = self.__createSocket()
        clientLogger.debug("Data channel socket created.")

        #bind the data channel socket to a ephemeral port
        self.__dataChannelSocket.bind(("localhost", 0))
        #get the ephemeral port
        self.__dataChannelPort = self.__dataChannelSocket.getsockname()[1]
        clientLogger.debug("Data channel socket binded to port %d",  self.__dataChannelPort)

        #data channel socket listen for connection
        self.__dataChannelSocket.listen(1)

    def __destroyControlSocket(self):
        """ Destroy the client control channel socket.
        """

        self.__controlChannelSocket.close()
        self.__controlChannelSocket = None 
        clientLogger.debug("Control channel socket destroyed.") 

    def __destroyDataSocket(self):
        """ Destroy the client data channel socket.
        """

        self.__dataChannelSocket.close()
        self.__dataChannelSocket = None 
        clientLogger.debug("Data channel socket destroyed.")

    def stop(self):
        """ Stop the FTP client.
        """

        if self.__controlChannelSocket != None:
            self.__destroyControlSocket()

        if self.__dataChannelSocket != None:
            self.__destroyDataSocket()