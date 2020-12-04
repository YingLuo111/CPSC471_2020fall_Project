import sys
from ftp_server import *

if __name__ == "__main__":
    serverLogger.debug("Number of args passed when starting FTP server is: %d", len(sys.argv))

    #Check if the command passed in valid number of arguments
    if len(sys.argv) < 2:
        print("Error: invalid command.")
        print("USAGE: python " + sys.argv[0] + " <Server Port>")
        sys.exit()

    serverPort = sys.argv[1]
    serverLogger.debug("Server port number is: %s", serverPort)

    #create a FTP server instance
    server = FTPServer(serverPort)
    
    try:
        #start the FTP server
        server.start()
    except KeyboardInterrupt:
        serverLogger.debug("Received keyboard inturrupt.")
        try:
            #stop the FTP server on user pressed on Ctrl+C
            server.stop()
            print("\n")
            serverLogger.info("Exiting FTP server program...")
            sys.exit(0)
        except SystemExit:
            sys.exit(0)
    except Exception as e:
        serverLogger.error(e)
        serverLogger.error("Error occured. Exiting server program...")
        #stop the FTP server on exception
        server.stop()
        sys.exit(1)