# topo

TYPE = "type"
NODE = "node"
INTERFACE = "interface"
EDGE = "edge"
IP = "ip"
INTERNAL_EDGE = "internal_edge"
LINK_EDGE = "link_edge"
LINK_COLOR = 'link_color'
POS = '+'
NEG = '!'

# policy protocol
ISIS = 'ISIS'
SRv6 = 'SRv6'
BGP = 'BGP'
ODN = 'SRv6.odn'
AS = 'SRv6.as'
LAT = 'SRv6.lat'

ANN = 'ann'
EXC = 'exc'

# segment

PREFIX_SID = 'Prefix_SID'
ADJ_SID = 'Adj_SID'

# ospf policy type

ECMP = 'ecmp'
ORDER = 'order'
SIMPLE = 'simple'

# SRv6 Policy Info


Head_Ip = 'Head_Ip'
End_Ip = 'End_Ip'
Policy_Type = 'Policy_Type'
Dynamic = 'dynamic'
Explicit = 'explicit'
Priority = 'Priority'
Mertric_Type = 'Mertric_Type'
Flex_Algo = 'Flex_Algo'
Can_Paths = "Can_Paths"
CONS = 'constraints'
SRv6_ODN = 'SRv6_odn'

# constraints
Exclude_Any = 'Exclude_Any'
Include_Any = 'Include_Any'
Include_All = 'Include_All'
# EXC = 'exc'

# candidate-paths
Seg_List = 'Seg_List'
Weight = 'Weight'
# Priority = 'Priority'


MAX_OSPF_COST = 17

MULT = 'multi'
SINGLE = 'single'




INTEGER_CONSTANT = 'INTEGER'
STRING_CONSTANT = 'STRING'
NODE_CONSTANT = 'NODE'
INTERFACE_CONSTANT = 'INTERFACE'
NETWORK_CONSTANT = 'NET'

# Keys for annotations used in nx graphs  在图中需要用到的键值
NODE_TYPE = "node"
INTERFACE_TYPE = "interface"
NETWORK_TYPE = "network"

VERTEX_TYPE = 'type'
EDGE_TYPE = 'type'
ANNOUNCEMENT_EDGE = 'annoucement_edge'
ANNOUNCED_NETWORK = 'announced_network'
PEER_TYPE = "peer"
ORIGIN_TYPE = "as_origin"
AS_NUM = 'AS'
