import sys
sys.path.append('..')

from src.sim import Sim
from src import node
from src import link
from src import packet

from networks.network import Network

class RoutingTable(object):
    def __init__(self, self_address):
        # format for data: {destination_address: [cost, link_address]}
        self.data = dict()
        self.data[self_address] = [0, self_address]
        self.broadcast_routing_table()

        print self.data

    def upsert_routing_table_entry(self, routing_table_entry, link):
        print "to do"
        # TODO: Update routing table for new values.

    def remove_routing_table_entry(self, destination_address):
        print "to do"
        # TODO: Remove routing table entries once they've expired.

    def broadcast_routing_table(self):
        formatted_routing_table = []
        for key, value in self.data.iteritems():
            formatted_routing_table += [key, value[0]]

        return formatted_routing_table

class DistanceVectorApp(object):
    def __init__(self, node, node_address):
        # the format used for the routing table is {address: cost}
        self.routing_table = None
        self.node = node
        self.routing_table = RoutingTable(node_address)

    def receive_packet(self,packet):
        print Sim.scheduler.current_time(),self.node.hostname,packet.ident

if __name__ == '__main__':
    # parameters
    Sim.scheduler.reset()
    Sim.set_debug(True)

    # setup network
    net = Network('../networks/five-nodes.txt')

    # get nodes
    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    n3 = net.get_node('n3')
    n4 = net.get_node('n4')
    n5 = net.get_node('n5')

    # setup broadcast application
    d1 = DistanceVectorApp(n1, n1.get_address('n2'))
    n1.add_protocol(protocol="broadcast",handler=d1)
    d2 = DistanceVectorApp(n2, n2.get_address('n1'))
    n2.add_protocol(protocol="broadcast",handler=d2)
    d3 = DistanceVectorApp(n3, n3.get_address('n1'))
    n3.add_protocol(protocol="broadcast",handler=d3)
    d4 = DistanceVectorApp(n4, n4.get_address('n3'))
    n4.add_protocol(protocol="broadcast",handler=d4)
    d5 = DistanceVectorApp(n5, n5.get_address('n3'))
    n5.add_protocol(protocol="broadcast",handler=d5)

    # send a broadcast packet from 1 with TTL 2, so everyone should get it
    p = packet.Packet(source_address=n1.get_address('n2'),destination_address=0,ident=1,ttl=2,protocol='broadcast',length=100)
    Sim.scheduler.add(delay=0, event=p, handler=n1.send_packet)

    # send a broadcast packet from 1 with TTL 1, so just nodes 2 and 3
    # should get it
    p = packet.Packet(source_address=n1.get_address('n2'),destination_address=0,ident=2,ttl=1,protocol='broadcast',length=100)
    Sim.scheduler.add(delay=1, event=p, handler=n1.send_packet)

    # send a broadcast packet from 3 with TTL 1, so just nodes 1, 4, and 5
    # should get it
    p = packet.Packet(source_address=n3.get_address('n1'),destination_address=0,ident=3,ttl=1,protocol='broadcast',length=100)
    Sim.scheduler.add(delay=2, event=p, handler=n3.send_packet)

    # run the simulation
    Sim.scheduler.run()
