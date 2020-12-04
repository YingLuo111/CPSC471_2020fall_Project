import sys
from ftp_client import *
import os

def startClient(client, serverName, serverPort):
    """ Start FTP client instance and accept user commands.

        :param clinet:     <FTPClient> The FTP client instance.
        :param serverName: <string> IP address or hostname of the FTP Server. 
        :param serverPort: <int> FTP server port to listen for client connections. 
    """ 

    #boolean indicate if the client program should quit
    willExit = False

    #accepting user command until quit program
    while willExit != True:
        #ask user for command input
        commandStr = input("\n>ftp ")

        clientLogger.debug("Input command is: %s", commandStr)
        
        #parse user input command
        commandArgs = commandStr.split(' ')

        #skip current command and ask for another command in case
        #of a invalid command
        if validate(commandArgs) == False:
            continue

        #execute FTP client control command
        willExit = client.executeControlCommand(commandArgs)

def validate(commandArgs):
    """ Check if the user input command is valid. 
        Valid commands are 'get', 'put', 'ls', 'quit'.

        :param commandArgs: <list> A list of string contains the command arguments.
        :returns: <boolean> A boolean indicate if the command is valid 
    """

    clientLogger.debug("Validating input command...")

    #check if the command argument length is valid
    if len(commandArgs) > 2:
        clientLogger.error("Command not valid, expecting command args no more than 2. \nUsage: \nget <filename>\nput <filename>\nls\nquit")
        return False

    #check if the command is valid
    if commandArgs[0] not in ['get', 'put', 'ls', 'quit']:
        clientLogger.error("Command not valid, unknown command. \nUsage: \nget <filename>\nput <filename>\nls\nquit")
        return False

    #if there is any argument followed by the command, check if it's valid
    if commandArgs[0] in ['ls', 'quit'] and len(commandArgs) > 1:
        clientLogger.error("Command not valid, ls and quit command don't have arguments. \nUsage: \nget <filename>\nput <filename>\nls\nquit")
        return False

    clientLogger.debug("Input command is valid.")

    return True

if __name__ == "__main__":
    clientLogger.debug("Number of args passed when starting FTP client is: %d", len(sys.argv))
    
    #Check if the command passed in valid number of arguments 
    if len(sys.argv) != 3:
        print("Error: Invalid command. Not all required args passed.")
        print("Usage: python " + sys.argv[0] + " <Server Machine>" + " <Server Port>")
        sys.exit()

    serverName = sys.argv[1]
    serverPort = sys.argv[2]

    #create a FTP client instance
    client = FTPClient(serverName, serverPort)

    try:
        #start the client instance
        startClient(client, serverName, serverPort)

        #stop the client instance after issued quit command
        client.stop()
        print("\nExiting FTP client program...")
    except KeyboardInterrupt:
        clientLogger.debug("Received keyboard inturrupt.")
        try:
            #stop the FTP server on user pressed on Ctrl+C
            client.stop()
            print("\n")
            clientLogger.info("Exiting FTP client program...")
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        clientLogger.error(e)
        #stop the FTP server on exception
        client.stop()
        sys.exit(1)
    
