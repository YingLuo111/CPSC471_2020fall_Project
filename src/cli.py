import sys
from ftp_client import *

def startClient(client, serverName, serverPort):
    client.start()  

    willExit = False

    while willExit != True:
        commandStr = input(">ftp ")

        clientLogger.debug("Input command is: %s", commandStr)
        
        #parse user input command
        commandArgs = commandStr.split(' ')

        if validate(commandArgs) == False:
            continue

        willExit = client.executeControlCommand(commandArgs)
        
        if willExit == True:
            client.stop()

def validate(commandArgs):
    clientLogger.debug("Validating input command...")
    if len(commandArgs) > 2:
        clientLogger.error("Command not valid, expecting command args no more than 2. \nUsage: \nget <filename>\nput <filename>\nls\nquit")
        return False

    if commandArgs[0] not in ['get', 'put', 'ls', 'quit']:
        clientLogger.error("Command not valid, unknown command. \nUsage: \nget <filename>\nput <filename>\nls\nquit")
        return False

    if commandArgs[0] in ['ls', 'quit'] and len(commandArgs) > 1:
        clientLogger.error("Command not valid, ls and quit command don't have arguments. \nUsage: \nget <filename>\nput <filename>\nls\nquit")
        return False

    clientLogger.debug("Input command is valid.")

    return True

if __name__ == "__main__":
    clientLogger.debug("Number of args passed when starting FTP client is: %d", len(sys.argv))
    # Command line checks 
    if len(sys.argv) != 3:
        print("Error: Invalid command. Not all required args passed.")
        print("Usage: python " + sys.argv[0] + " <Server Machine>" + " <Server Port>")
        sys.exit()

    serverName = sys.argv[1]
    serverPort = sys.argv[2]

    client = FTPClient(serverName, serverPort)

    try:
        startClient(client, serverName, serverPort)
        print("Exiting FTP client program...")
    except KeyboardInterrupt:
        clientLogger.debug("Received keyboard inturrupt.")
        try:
            client.stop()
            clientLogger.info("Exiting FTP client program...")
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception:
        client.stop()
        sys.exit(1)
    
