##OVS Local Control
#
# OVS local control
#
# @author ykk
# @date Feb 2011
#
import yapc.interface as yapc
import yapc.output as output
import yapc.commands as cmd
import simplejson

DPCTL="ovs-dpctl"
OFCTL="ovs-ofctl"
CONNECT="ovs-openflowd"

class switch(yapc.cleanup):
    """Class to implement local control for OVS

    @author ykk
    @date Feb 2011
    """
    def __init__(self):
        """Initialize switch fabric
        """
        ##Dictionary of datapath
        self.datapaths = {}

    def __del__(self):
        """Clean up all datapath
        """
        output.dbg("Cleaning up datapaths",
                   self.__class__.__name__)
        for name,dp in self.datapaths.items():
            self.del_dp(name)

    def cleanup(self):
        """Clean up all datapath
        """
        self.__del__()

    def add_dp(self, name):
        """Add datapath with name

        @param name name of datapath
        """
        output.dbg("Add datapath "+name,
                   self.__class__.__name__)
        self.datapaths[name] = datapath(name)

    def del_dp(self, name):
        """Delete datapath with name

        @param name name of datapath
        """
        if (name in self.datapaths):
            output.dbg("Delete datapath "+name,
                       self.__class__.__name__)
            self.datapaths.pop(name)
        else:
            output.err("No datapath of name "+name)

class datapath:
    """Class to represent and manage datapath
    
    @author ykk
    @date Feb 2011
    """
    def __init__(self, name):
        """Initialize datapath
        
        @param name name of datapath
        """
        ##Name of datapath
        self.name = name
        cmd.run_cmd(DPCTL+" add-dp "+name,
                    self.__class__.__name__)
        ##List of interfaces
        self.interfaces = []
        ##Connected to controller or not
        self.connected = False

    def __del__(self):
        """Clean up datapath
        """
        output.dbg("Clean up datapath "+self.name,
                   self.__class__.__name__)
        if (self.connected):
            self.disconnect()
        for i in self.interfaces:
            self.del_if(i)
        cmd.run_cmd(DPCTL+" del-dp "+self.name,
                    self.__class__.__name__)
        
    def add_if(self, intf):
        """Add interface to datapath

        @param intf name of interface
        @return command's exit status
        """
        self.interfaces.append(intf)
        return cmd.run_cmd(DPCTL+" add-if "+self.name+" "+intf,
                           self.__class__.__name__)

    def del_if(self, intf):
        """Remove interface to datapath

        @param intf name of interface
        @return command's exit status
        """
        self.interfaces.remove(intf)
        return cmd.run_cmd(DPCTL+" del-if "+self.name+" "+intf,
                           self.__class__.__name__)

    def connect(self, controller, port=6633):
        """Connect datapath to controller
        
        @param controller controller's IP address
        @param port port number
        """
        self.connected = True
        return cmd.run_cmd_screen("coin-ovs-"+self.name, 
                                  CONNECT+" tcp:"+controller+":"+port,
                                  self.__class__.__name__)

    def disconnect(self):
        """Disconnect datapath from controller
        """
        self.connected = False
        return cmd.run_cmd("screen -d -r coin-ovs-"+self.name+\
                               " -X quit")
    
