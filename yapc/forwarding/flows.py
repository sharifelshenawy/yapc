##Definition of flows
#
# Some generic definition of flows
#
# @author ykk
# @date Feb 2011
#
import dpkt
import yapc.openflowutil as ofutil
import yapc.pyopenflow as pyof
import yapc.output as output

UDP_BOOTPS = 67
UDP_BOOTPC = 68
UDP_SUNRPC = 111
UDP_NETBIOS = 137
UDP_NETBIOS_DGM = 138
UDP_MS_LICENSE = 2223
UDP_MDNS = 5353

UNBUFFERED_ID = 4294967295
DEFAULT_TIMEOUT = 5

class actions:
    """Class to provide management of ofp_actions list
    
    @author ykk
    @date Feb 2011
    """
    def __init__(self, buffer_id=UNBUFFERED_ID):
        """Initialize
        """
        ##List of actions
        self.actions = []
        ##Buffer id
        self.buffer_id = buffer_id

    def add(self, action):
        """Add more actions to flow entry
        """
        self.actions.append(action)

class flow_entry(actions):
    """Class to provide some pre-formed flow entry

    @author ykk
    @date Feb 2011
    """
    NONE = 0
    DROP = 0
    GET = 1
    FLOOD = 2
    def __init__(self, action=NONE):
        """Initialize
        """
        actions.__init__(self)
        ##Match
        self.match = pyof.ofp_match()
        ##Idle timeout
        self.idle_timeout = DEFAULT_TIMEOUT
        ##Hard timeout
        self.hard_timeout = DEFAULT_TIMEOUT
        ##Priority
        self.priority = pyof.OFP_DEFAULT_PRIORITY
        ##Out port
        self.out_port = pyof.OFPP_NONE
        ##Flags
        self.flags = 0

        oao = pyof.ofp_action_output()
        oao.max_len = pyof.OFP_DEFAULT_MISS_SEND_LEN
        if (action == flow_entry.GET):
            oao.port = pyof.OFPP_CONTROLLER
        elif (action == flow_entry.FLOOD):
            oao.port = pyof.OFPP_FLOOD

        if (action != flow_entry.DROP):
            self.actions.append(oao)

    def set_priority(self, priority):
        """Set priority of flow entry

        Priority can be expressed as number or 
        one of the following string expressed in yapc.openflowutil
       
        @param priority expression of priority
        @return success
        """
        if (isinstance(priority, int)):
            self.priority = priority
        elif (priority in ofutil.PRIORITY):
            self.priority = ofutil.PRIORITY[priority]
        else:
            output.warn("Unknown expression of priority "+str(priority),
                        self.__class__.__name__)
            return False

        return True

    def get_flow_mod(self, command=pyof.OFPFC_ADD, 
                     cookie=0):
        """Function to return flow_entry in terms of flow mod.

        @return ofp_flow_mod
        """
        fm = pyof.ofp_flow_mod()
        fm.match = self.match
        fm.cookie = cookie
        fm.command = command
        fm.idle_timeout = self.idle_timeout
        fm.hard_timeout = self.hard_timeout
        fm.priority = self.priority
        fm.buffer_id = self.buffer_id
        fm.out_port = self.out_port
        fm.flags = self.flags
        
        fm.actions = self.actions[:]
        fm.header.xid = ofutil.get_xid()
        return fm

class exact_entry(flow_entry):
    """Flow entry with exact match

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 match,
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOWEST'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        flow_entry.__init__(self, action)

        self.match = match
        self.priority = priority
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout

class all_entry(flow_entry):
    """Flow entry for all packets

    Uses as a low priority default

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOWEST'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        flow_entry.__init__(self, action)

        self.match.wildcards = pyof.OFPFW_ALL
        self.priority = priority
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout

class ethertype_entry(flow_entry):
    """Flow entry that is based Ethertype

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 ethertype,
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOW'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        flow_entry.__init__(self, action)

        self.match.wildcards = pyof.OFPFW_ALL - pyof.OFPFW_DL_TYPE
        self.match.dl_type = ethertype
        self.priority = priority
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout

class arp_entry(ethertype_entry):
    """Flow entry for ARP packets

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOW'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        ethertype_entry.__init__(self, dpkt.ethernet.ETH_TYPE_ARP, action,
                                 priority, idle_timeout, hard_timeout)

class ip_proto_entry(flow_entry):
    """Flow entry that is based IP Protocol number

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 ip_proto,
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOW'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        flow_entry.__init__(self,action)
       
        self.match.wildcards = pyof.OFPFW_ALL-\
            pyof.OFPFW_DL_TYPE - pyof.OFPFW_NW_PROTO
        self.match.dl_type = dpkt.ethernet.ETH_TYPE_IP
        self.match.nw_proto = ip_proto
        self.priority = priority
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout


class icmp_entry(ip_proto_entry):
    """Flow entry to handle ICMP packets

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOW'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        ip_proto_entry.__init__(self, dpkt.ip.IP_PROTO_ICMP, action,
                                priority, idle_timeout, hard_timeout)
       
class igmp_entry(ip_proto_entry):
    """Flow entry to handle IGMP

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOW'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        ip_proto_entry.__init__(self, dpkt.ip.IP_PROTO_IGMP, action,
                                priority, idle_timeout, hard_timeout)

class udp_entry(ip_proto_entry):
    """Flow entry for UDP packets

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 portno = None,
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOW'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        ip_proto_entry.__init__(self, dpkt.ip.IP_PROTO_UDP, action,
                                priority, idle_timeout, hard_timeout)

        if (portno != None):
            self.match.wildcards -= pyof.OFPFW_TP_DST
            self.match.tp_dst = portno

class tcp_entry(ip_proto_entry):
    """Flow entry for TCP packets

    @author ykk
    @date Feb 2011
    """
    def __init__(self, 
                 portno = None,
                 action=flow_entry.NONE,
                 priority = ofutil.PRIORITY['LOW'],
                 idle_timeout = pyof.OFP_FLOW_PERMANENT,
                 hard_timeout = pyof.OFP_FLOW_PERMANENT):
        """Initialize
        """
        flow_entry.__init__(self, action)

        ip_proto_entry.__init__(self, dpkt.ip.IP_PROTO_TCP, action,
                                priority, idle_timeout, hard_timeout)       

        if (portno != None):
            self.match.wildcards -= pyof.OFPFW_TP_DST
            self.match.tp_dst = portno
