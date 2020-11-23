import sys
from ftp_server import *

if __name__ == "__main__":
    serverLogger.debug("Number of args passed when starting FTP server is: %d", len(sys.argv))

    # Command line checks 
    if len(sys.argv) < 2:
        print("Error: invalid command.")
        print("USAGE: python " + sys.argv[0] + " <Server Port>")
        sys.exit()

    serverPort = sys.argv[1]
    serverLogger.debug("Server port number is: %s", serverPort)

    server = FTPServer(serverPort)
    
    try:
        server.start()
    except KeyboardInterrupt:
        serverLogger.debug("Received keyboard inturrupt.")
        try:
            server.stop()
            serverLogger.info("Exiting server program...")
            sys.exit(0)
        except SystemExit:
            sys.exit(0)
    except Exception:
        serverLogger.error("Error occured. Exiting server program...")
        server.stop()
        sys.exit(1)