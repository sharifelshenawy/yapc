##COIN OVS
#
# OVS as switch fabric for COIN
#
# @author ykk
# @date Feb 2011
#
import yapc.local.ovs as ovs
import yapc.interface as yapc
import yapc.jsoncomm as jsoncomm
import yapc.ofcomm as ofcomm
import yapc.output as output
import simplejson

class switch(yapc.component, ovs.switch):
    """Class to implement switch fabric using OVS

    @author ykk
    @date Feb 2011
    """
    def __init__(self, conn):
        """Initialize switch fabric

        @param conn reference to connections
        """
        ovs.switch.__init__(self)
        ##Reference to connections
        self.conn = conn

    def processevent(self, event):
        """Process messages

        @param event event to process
        """
        if isinstance(event, jsoncomm.message):
            self.__process_json(event)
        elif isinstance(event, ofcomm.message):
            pass
        
        return True

    def __process_json(self, event):
        """Process JSON messages

        @param event JSON message event to process
        """
        if (event.sock not in self.conn.jsonconnections.db):
            self.conn.jsonconnections.add(event.sock)
        
        if (event.message["type"] == "coin" and
            event.message["subtype"] == "ovs"):
            reply = self.__process_switch_json(event)
            if (reply != None):
                self.conn.jsonconnections.db[event.sock].send(reply)
        else:
            output.dbg("Receive JSON message "+simplejson.dumps(event.message),
                       self.__class__.__name__)

    def __process_switch_json(self, event):
        """Process JSON messages for switch

        @param event JSON message event for switch
        """
        reply = {}
        reply["type"] = "coin"
        reply["subtype"] = "ovs"

        if (event.message["command"] == "add_dp"):
            self.add_dp(event.message["name"])
            reply["executed"] = True
        elif (event.message["command"] == "del_dp"):
            self.del_dp(event.message["name"])
            reply["executed"] = True
        else:
            reply["error"] = "Unknown command"

        return reply

    
