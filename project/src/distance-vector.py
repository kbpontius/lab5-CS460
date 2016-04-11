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
            if value is None:
                formatted_routing_table.append([key, None])
            else:
                formatted_routing_table.append([key, value[0]])

        distance_vector_message['routing_table'] = formatted_routing_table
        return distance_vector_message

    def update_routing_table(self, distance_vector_message, link):
        # format: {destination_address: action==('Upserted', 'Deleted')}
        updated_destinations = dict()
        routing_table_entries = distance_vector_message['routing_table']

        for entry in routing_table_entries:
            updated_destinations.update(self.upsert_routing_table_entry(entry, link))

        return updated_destinations

    def upsert_routing_table_entry(self, routing_table_entry, link):
        # routing_table_entry format: [destination_address cost]
        # also: see line above self.get_routing_table() for additional information

        # format: {destination_address: action==('Upserted', 'Deleted')}
        updated_destinations = dict()

        destination_address = routing_table_entry[0]
        new_route_cost = routing_table_entry[1]

        if new_route_cost is None:
            if self.routing_table.get(destination_address) is not None:
                routing_table_link = self.routing_table[destination_address][1]

                # if that link is being used
                if link is routing_table_link:
                    deleted_addresses = self.remove_routing_table_entry(routing_table_link)
                    for address in deleted_addresses:
                        updated_destinations[address] = 'Deleted'

            return
        elif self.routing_table.get(destination_address) is None \
                or (new_route_cost + 1) < self.routing_table[destination_address][0]:
            self.routing_table[destination_address] = [routing_table_entry[1] + 1, link]
            updated_destinations[destination_address] = 'Upserted'

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
    def remove_routing_table_entry(self, link):
        deleted_destination_address = []
        for entry, value in self.routing_table.iteritems():
            if value[1] == link:
                self.routing_table[entry] = None
                deleted_destination_address.append(entry)

        return deleted_destination_address

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

        for destination_address, update_type in updated_destination_addresses.iteritems():
            # print "Updated Destination Address:" + str(destination_address) + ", to link: " + str(link)
            if update_type == 'Upserted':
                self.node.add_forwarding_entry(destination_address, link)
            elif update_type == 'Deleted':
                self.node.delete_forwarding_entry(destination_address, link)

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
    net = Network('../networks/five-nodes.txt')

    # get nodes
    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    n3 = net.get_node('n3')
    n4 = net.get_node('n4')
    n5 = net.get_node('n5')
    # n6 = net.get_node('n6')
    # n7 = net.get_node('n7')
    # n8 = net.get_node('n8')
    # n9 = net.get_node('n9')
    # n10 = net.get_node('n10')
    # n11 = net.get_node('n11')
    # n12 = net.get_node('n12')
    # n13 = net.get_node('n13')
    # n14 = net.get_node('n14')
    # n15 = net.get_node('n15')

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
    # d6 = DistanceVectorApp(n6)
    # n6.add_protocol(protocol="dvrouting", handler=d6)
    # d7 = DistanceVectorApp(n7)
    # n7.add_protocol(protocol="dvrouting", handler=d7)
    # d8 = DistanceVectorApp(n8)
    # n8.add_protocol(protocol="dvrouting", handler=d8)
    # d9 = DistanceVectorApp(n9)
    # n9.add_protocol(protocol="dvrouting", handler=d9)
    # d10 = DistanceVectorApp(n10)
    # n10.add_protocol(protocol="dvrouting", handler=d10)
    # d11 = DistanceVectorApp(n11)
    # n11.add_protocol(protocol="dvrouting", handler=d11)
    # d12 = DistanceVectorApp(n12)
    # n12.add_protocol(protocol="dvrouting", handler=d12)
    # d13 = DistanceVectorApp(n13)
    # n13.add_protocol(protocol="dvrouting", handler=d13)
    # d14 = DistanceVectorApp(n14)
    # n14.add_protocol(protocol="dvrouting", handler=d14)
    # d15 = DistanceVectorApp(n15)
    # n15.add_protocol(protocol="dvrouting", handler=d15)

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
