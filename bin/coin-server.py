#!/usr/bin/python
## Client OpenFlow Interface for Networking
# @author ykk
# @date Oct 2010
#
import yapc.core as core
import yapc.interface as yapc
import yapc.ofcomm as ofcomm
import yapc.jsoncomm as jsoncomm
import yapc.events.openflow as ofevents
import yapc.output as output
import yapc.coin.core as coin
import yapc.coin.ovs as coinovs
import yapc.netstate.switches as switches
import yapc.netstate.swhost as switchhost
import yapc.forwarding.default as default
import yapc.debug.openflow as ofdbg
import sys
import getopt

class coin_server(yapc.daemon):
    def __init__(self):
        yapc.daemon.__init__(self)
        ##Force JSON connection or not
        self.forcejson = False
        ##Socket to talk to
        self.sock = coin.SOCK_NAME

    def run(self):
        """Run server
        """
        #Create yapc base
        server = core.core()
        ofconn = ofcomm.ofserver(server)
        jsonconn = jsoncomm.jsonserver(server, file=self.sock, 
                                       forcebind=self.forcejson)

        ofmsg = ofdbg.of_msg_count(server,1)

        #OpenFlow Parser
        ofparse = ofevents.parser(server)
        #COIN main server, maintaining connections
        coinserver = coin.server(server, ofconn.connections,
                                 jsonconn.connections)
        #Network status
        sw = switches.dp_features(server)
        swhost = switchhost.mac2sw_binding(server)
        #OVS fabric manager
        ovs = coinovs.switch(server, 
                             jsonconn.connections)
        coinserver.switch = ovs
        #Drop unhandled flows
        df = default.dropflow(server, ofconn.connections)
        
        server.run()
        
        sys.exit(0)
        
##Print usage guide
def usage():
    """Display usage
    """
    print "Usage "+sys.argv[0]+" [options] command <parameters>"
    print "\tCOIN server"
    print  "Options:"
    print "-h/--help\n\tPrint this usage guide"
    print "-f/--force-json\n\tForced binding for JSON UNIX socket"
    print "-s/--sock\n\tSocket to communicate to (default: "+coin.SOCK_NAME+")"
    print "-v/--verbose\n\tVerbose output"
    print "--vs\n\tVerbose output for selected component"
    print "--very-verbose\n\tVery verbose output"
    print "-d/--daemon\n\tRun as daemon"

coins = coin_server()

#Parse options and arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "hvdfs:",
                               ["help","verbose","daemon", 
                                "very-verbose","vs=",
                                "force-json","sock="])
except getopt.GetoptError:
    print "Option error!"
    usage()
    sys.exit(2)

output.set_mode("INFO")

#Parse options
for opt,arg in opts:
    if (opt in ("-h","--help")):
        usage()
        sys.exit(0)
    elif (opt in ("-v","--verbose")):
        output.set_mode("DBG")
    elif (opt in ("--vs")):
        output.set_mode("DBG", arg)
    elif (opt in ("--very-verbose")):
        output.set_mode("VDBG")
    elif (opt in ("-d","--daemon")):
        coins.daemon=True
    elif (opt in ("-s","--sock")):
        coins.sock = arg
    elif (opt in ("-f","--force-json")):
        coins.forcejson=True
    else:
        print "Unhandled option :"+opt
        sys.exit(2)

if (coins.daemon):
    output.set_logfile('/var/log/coin.log')
coins.start()
