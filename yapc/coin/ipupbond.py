##COIN IP based uplink bonding mode
#
# Create IP based uplink bonding driver using COIN
#
# @author ykk
# @date Oct 2010
#
import yapc.interface as yapc
import yapc.output as output
import yapc.jsoncomm as jsoncomm
import yapc.ofcomm as ofcomm
import yapc.pyopenflow as pyopenflow
import yapc.parseutil as parser
import commands

class handler(yapc.component):
    """Class to handle commands for IP based uplink bonding driver using COIN
    
    @author ykk
    @date Oct 2010
    """
    def __init__(self, connections):
        """Initialize
        """
        ##Reference to connections
        self.conn = connections
        ##Dictionary of bond interface and status
        self.bondinterfaces = {}
        ##Reference to OpenFlow switch connection
        self.__conn = None
        ##Dictionary OpenFlow switch ports
        self.__ports = {}

    def processevent(self, event):
        """Process messages
        """
        if isinstance(event, jsoncomm.message):
            if (event.message["type"] == "coin" and
                event.message["subtype"] == "ipupbond"):
                reply = self.__processmsg(event)
                self.conn.jsonconnections.db[event.sock].send(reply)

        elif isinstance(event, ofcomm.message):
            if (event.header.type == pyopenflow.OFPT_FEATURES_REPLY):
                self.__conn = self.conn.connections.db[event.sock]
                self.__ports = {}
                osf = pyopenflow.ofp_switch_features()
                portmsg = osf.unpack(event.message)
                opp = pyopenflow.ofp_phy_port()
                while portmsg != "":
                    portmsg = opp.unpack(portmsg)
                    self.__ports[opp.name] = opp.port_no
                output.dbg("Switch "+hex(osf.datapath_id)+" has ports "+str(self.__ports),
                           self.__class__.__name__)

            elif (event.header.type == pyopenflow.OFPT_PORT_STATUS):
                ops = pyopenflow.ofp_port_status()
                ops.unpack(event.message)
                if (ops.reason == pyopenflow.OFPPR_MODIFY) or \
                        (ops.reason == pyopenflow.OFPPR_DELETE):
                    del self.__ports[ops.desc.name]
                    output.dbg("Remove port "+ops.desc.name+" to have ports "+str(self.__ports),
                               self.__class__.__name__)
                    
                if (ops.reason == pyopenflow.OFPPR_MODIFY) or \
                        (ops.reason == pyopenflow.OFPPR_ADD):
                    self.__ports[ops.desc.name] = ops.desc.port_no
                    output.dbg("Add port "+ops.desc.name+" to have ports "+str(self.__ports),
                               self.__class__.__name__)

        return True

    def listofinterfaces(self):
        """Get list of interfaces
        """
        out = []
        for i in commands.getoutput("ifconfig -a | grep Link | grep encap ").split("\n"):
            out.append(i[:i.index(" ")].strip())
        return out

    def __processmsg(self, event):
        """Process json commands
        """
        reply = {}
        reply["type"] = "coin"
        reply["subtype"] = "ipupbond"

        bondi = None
        intf = None
        ip = None
        if event.message["command"] != "create":
            bondi = event.message["bond-interface"]
            if bondi not in self.bondinterfaces:
                reply["command"] = "error"
                reply["status"] = "Unknown bond-interface "+bondi
                return reply
        else:
            ipaddr = parser.ipv4addr(event.message["ip-address"])
            ip = ipaddr.value()
            if (ip == None):
                reply["command"] = "error"
                reply["status"] = "Unknown IP address "+event.message["ip-address"]
                return reply

        if ((event.message["command"] != "create") and
            (event.message["command"] != "delete") and
            (event.message["command"] != "get-active-slave")):
            intf = event.message["interface"]
            if intf not in self.listofinterfaces():
                reply["command"] = "error"
                reply["status"] = "Unknown interface "+intf
                return reply

        if event.message["command"] == "create":
            #Create interface
            bondinterface = bondstate(ip, self.__ports, self.__conn)
            reply["command"] = "created"
            reply["interface"] = str(bondinterface.interface)
            self.bondinterfaces[bondinterface.interface] = bondinterface
            
        elif event.message["command"] == "delete":
            #Delete interface
            reply["command"] = "deleted"
            reply["status"] =\
                self.bondinterfaces[bondi].delete()
            del self.bondinterfaces[bondi]
      
        elif event.message["command"] == "enslave":
            #Enslave
            reply["command"] = "enslaved"
            if intf in self.bondinterfaces[bondi].slaves:
                reply["status"] = "already enslaved, no action done"
            else:
                self.bondinterfaces[bondi].enslave(intf)
                reply["status"] = 0

        elif event.message["command"] == "liberate":
            #Liberate
            reply["command"] = "liberated"
            if intf not in self.bondinterfaces[bondi].slaves:
                reply["status"] = "not enslaved, no action done"
            else:
                self.bondinterfaces[bondi].liberate(intf)
                reply["status"] = 0

        elif event.message["command"] == "get-active-slave":
            #Get-active-slave
            reply["command"] = "got-active-slave"
            reply["status"] = str(self.bondinterfaces[bondi].activeslave)

        elif event.message["command"] == "set-active-slave":
            #Set-active-slave
            reply["command"] = "set-active-slave"
            if intf not in self.bondinterfaces[bondi].slaves:
                reply["status"] = str(intf)+" is not slave of "+str(bondi)+", make active slave"
            elif intf == self.bondinterfaces[bondi].activeslave:
                reply["status"] = "already active slave, no action done"
            else:
                self.bondinterfaces[bondi].setactiveslave(intf)
                reply["status"] = 0

        else:
            reply["command"] = "error"
            reply["status"] = "Unknown command "+event.message["command"]

        return reply

class bondstate:
    """State of bonding interface

    @author ykk
    @date 2010
    """
    def __init__(self, ip, ports, conn):
        """Create bond interface state
        """
        ##Reference to ports
        self.__ports = ports
        ##Reference to connection
        self.__conn = conn
        ##Name of datapath
        self.dp = "dp0"
        ##Interface create
        self.interface = self.__create()
        commands.getoutput("ovs-dpctl add-if "+self.dp+" "+self.interface)
        ##Interfaces enslaved
        self.slaves = []
        ##Active slave (i.e., who to receive from)
        self.activeslave = None
        ##IP to create uplink bonding driver for
        self.ip = ip

    def setactiveslave(self, interface):
        """Set active slave interface
        """
        if (self.activeslave != None):
            #Remove OpenFlow rule (down)
            ofm = pyopenflow.ofp_flow_mod()
            ofm.match = self.__getmatch(self.activeslave, True)
            ofm.command = pyopenflow.OFPFC_DELETE_STRICT
            ofm.out_port = self.__ports[self.interface]
            ofm.buffer_id = 4294967295
            ofm.flags = pyopenflow.OFPFF_SEND_FLOW_REM
            self.__conn.send(ofm.pack())

            #Remove OpenFlow rule (up)
            ofm = pyopenflow.ofp_flow_mod()
            ofm.match = self.__getmatch(self.interface, True)
            ofm.command = pyopenflow.OFPFC_DELETE_STRICT
            ofm.out_port = self.__ports[self.activeslave]
            ofm.buffer_id = 4294967295
            ofm.priority = 0
            ofm.flags = pyopenflow.OFPFF_SEND_FLOW_REM
            self.__conn.send(ofm.pack())

        if (interface != None):
            #Set OpenFlow rule (down)
            ofm = pyopenflow.ofp_flow_mod()
            ofm.match = self.__getmatch(interface, True)
            ofm.command = pyopenflow.OFPFC_ADD
            ofm.buffer_id = 4294967295
            ofm.flags = pyopenflow.OFPFF_SEND_FLOW_REM
            oao = pyopenflow.ofp_action_output()
            oao.len = len(oao)
            oao.port = self.__ports[self.interface]
            ofm.actions.append(oao)
            self.__conn.send(ofm.pack())

            #Set OpenFlow rule (up)
            ofm = pyopenflow.ofp_flow_mod()
            ofm.match = self.__getmatch(self.interface, True)
            ofm.command = pyopenflow.OFPFC_ADD
            ofm.buffer_id = 4294967295
            ofm.priority = 0
            ofm.flags = pyopenflow.OFPFF_SEND_FLOW_REM
            oao = pyopenflow.ofp_action_output()
            oao.len = len(oao)
            oao.port = self.__ports[interface]
            ofm.actions.append(oao)
            self.__conn.send(ofm.pack())

        self.activeslave = interface

    def enslave(self, interface):
        """Enslave interface
        """
        #Add to slave list
        self.slaves.append(interface)

        #Set OpenFlow rule
        ofm = pyopenflow.ofp_flow_mod()
        ofm.match = self.__getmatch(self.interface)
        ofm.command = pyopenflow.OFPFC_ADD
        ofm.buffer_id = 4294967295
        ofm.flags = pyopenflow.OFPFF_SEND_FLOW_REM
        for i in self.slaves:
            oao = pyopenflow.ofp_action_output()
            oao.len = len(oao)
            oao.port = self.__ports[i]
            ofm.actions.append(oao)
        self.__conn.send(ofm.pack())
        
    def liberate(self, interface):
        """Liberate interface
        """
        #Add to slave list
        self.slaves.remove(interface)
        if self.activeslave == interface:
            self.setactiveslave(None)

        ofm = pyopenflow.ofp_flow_mod()
        ofm.match = self.__getmatch(self.interface)
        ofm.buffer_id = 4294967295
        ofm.flags = pyopenflow.OFPFF_SEND_FLOW_REM
        if (len(self.slaves) == 0):
            #Remove OpenFlow rule
            ofm.command = pyopenflow.OFPFC_DELETE_STRICT
            ofm.out_port = self.__ports[interface]
        else:
            #Change rule
            ofm.command = pyopenflow.OFPFC_ADD
            for i in self.slaves:
                oao = pyopenflow.ofp_action_output()
                oao.len = len(oao)
                oao.port = self.__ports[i]
                ofm.actions.append(oao)
        self.__conn.send(ofm.pack())
            
    def __getmatch(self, interface, skipip=False):
        """Return ofp_matc for bonding interface
        """
        om = pyopenflow.ofp_match()
        om.in_port = self.__ports[interface]
        om.wildcards = pyopenflow.OFPFW_ALL - pyopenflow.OFPFW_IN_PORT
        if not skipip:
            om.nw_dst = self.ip
            om.wildcards -= pyopenflow.OFPFW_NW_DST_ALL
        return om

    def delete(self):
        """Delete bond interface if no more slaves
        """
        if len(self.slaves) == 0:  
            commands.getoutput("ovs-dpctl del-if "+self.dp+" "+self.interface)
            (status, out) = commands.getstatusoutput("ip link del "+self.interface)
            return status
        else:
            return "Err: Bond interface has slaves "+str(self.slaves)

    def __create(self):
        """Create interface
        """
        startinterfaces = self.listofinterfaces()
        commands.getstatusoutput("ip link add type veth")
        endinterfaces = self.listofinterfaces()
        
        for i in endinterfaces:
            if i not in startinterfaces:
                return i
        return None

    def listofinterfaces(self):
        """Get list of interfaces
        """
        out = []
        for i in commands.getoutput("ifconfig -a | grep Link | grep encap ").split("\n"):
            out.append(i[:i.index(" ")].strip())
        return out
    
