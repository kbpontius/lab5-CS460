import sys
sys.path.append('..')

from src.sim import Sim
from src import node
from src import link
from src import packet

from networks.network import Network

class RoutingTable(object):
    def __init__(self):
        # format for data: {destination_address: [cost, link_address]}
        self.routing_table = dict()

    # distance_vector_message format: {'hostname': hostname, 'routing_table': [[destination_address cost]]}
    def get_routing_table(self):
        distance_vector_message = dict()

        formatted_routing_table = []
        for key, value in self.routing_table.iteritems():
            formatted_routing_table.append([key, value[0]])

        distance_vector_message['routing_table'] = formatted_routing_table
        return distance_vector_message

    def update_routing_table(self, distance_vector_message, link):
        updated_destinations = []
        routing_table_entries = distance_vector_message['routing_table']

        for entry in routing_table_entries:
            updated_destinations += self.upsert_routing_table_entry(entry, link)

        return updated_destinations

    def upsert_routing_table_entry(self, routing_table_entry, link):
        # routing_table_entry format: [destination_address cost]
        # also: see line above self.get_routing_table() for additional information

        updated_destinations = []

        destination_address = routing_table_entry[0]
        new_route_cost = routing_table_entry[1]

        if self.routing_table.get(destination_address) is None \
                or (new_route_cost + 1) < self.routing_table[destination_address][0]:
            self.routing_table[destination_address] = [routing_table_entry[1] + 1, link]
            updated_destinations.append(destination_address)

        return updated_destinations

    # after broadcast is sent, this ensures a distance of 0 is set for this link.
    def check_link_to_self(self, this_node, destination_hostname):
        this_address = this_node.get_address(destination_hostname)
        updated = False

        if self.routing_table.get(this_address) is None:
            self.routing_table[this_address] = [0, None]
            updated = True

        return this_address, updated

    # remove routing_table_entry after the link has gone dead.
    def remove_routing_table_entry(self, link_address):
        for entry, value in self.routing_table.iteritems():
            if value[1] == link_address:
                del self.routing_table[entry]

        # TODO: REMOVE node.forwarding_table entries!!

class DistanceVectorApp(object):
    def __init__(self, node):
        # the format used for the routing table is {address: cost}
        self.routing_table = None
        self.node = node
        self.source_address = None
        self.routing_table = RoutingTable()

    def upsert_forwarding_table(self, routing_table, link):
        updated_destination_addresses = self.routing_table.update_routing_table(routing_table, link)
        updated_routing_table = len(updated_destination_addresses) > 0

        for destination_address in updated_destination_addresses:
            # print "Updated Destination Address:" + str(destination_address) + ", to link: " + str(link)
            self.node.add_forwarding_entry(destination_address, link)

        return updated_routing_table

    def receive_packet(self,received_packet):
        # print Sim.scheduler.current_time(), self.node.hostname, received_packet.ident, received_packet.body
        hostname = received_packet.body['hostname']
        self.source_address, updated_self_link = self.routing_table.check_link_to_self(self.node, hostname)
        link = self.node.get_link(hostname)
        updated_forwarding_table = self.upsert_forwarding_table(received_packet.body, link)

        if updated_forwarding_table or updated_self_link:
            self.broadcast_routing_table()
            print ("%d, %s, Updated Routing Table Values:" + str(self.routing_table.get_routing_table())) % (

        Sim.scheduler.current_time(), self.node.hostname)

    def broadcast_routing_table(self):
        distance_vector_message = self.routing_table.get_routing_table()
        distance_vector_message['hostname'] = self.node.hostname
        routing_table_packet = packet.Packet(destination_address=0, ident=0, ttl=1, protocol='dvrouting', body=distance_vector_message)
        Sim.scheduler.add(delay=0, event=routing_table_packet, handler=self.node.send_packet)

if __name__ == '__main__':
    # parameters
    Sim.scheduler.reset()
    Sim.set_debug(True)

    # setup network
    net = Network('../networks/fifteen-nodes.txt')

    # get nodes
    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    n3 = net.get_node('n3')
    n4 = net.get_node('n4')
    n5 = net.get_node('n5')

    # setup broadcast application
    d1 = DistanceVectorApp(n1)
    n1.add_protocol(protocol="dvrouting",handler=d1)
    d2 = DistanceVectorApp(n2)
    n2.add_protocol(protocol="dvrouting",handler=d2)
    d3 = DistanceVectorApp(n3)
    n3.add_protocol(protocol="dvrouting",handler=d3)
    d4 = DistanceVectorApp(n4)
    n4.add_protocol(protocol="dvrouting",handler=d4)
    d5 = DistanceVectorApp(n5)
    n5.add_protocol(protocol="dvrouting",handler=d5)

    d1.broadcast_routing_table()

    # send a broadcast packet from 1 with TTL 2, so everyone should get it
    # p = packet.Packet(source_address=n1.get_address('n2'),destination_address=0,ident=1,ttl=2,protocol='dvrouting',length=100)
    # Sim.scheduler.add(delay=0, event=p, handler=n1.send_packet)

    # send a broadcast packet from 1 with TTL 1, so just nodes 2 and 3
    # should get it
    # p = packet.Packet(source_address=n1.get_address('n2'),destination_address=0,ident=2,ttl=1,protocol='dvrouting',length=100)
    # Sim.scheduler.add(delay=1, event=p, handler=n1.send_packet)

    # send a broadcast packet from 3 with TTL 1, so just nodes 1, 4, and 5
    # should get it
    # p = packet.Packet(source_address=n3.get_address('n1'),destination_address=0,ident=3,ttl=1,protocol='dvrouting',length=100)
    # Sim.scheduler.add(delay=2, event=p, handler=n3.send_packet)

    # run the simulation
    Sim.scheduler.run()
