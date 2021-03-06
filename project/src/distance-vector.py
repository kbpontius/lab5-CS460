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
        self.broadcast_count = 0

        # format: {hostname: last_update_time}
        self.last_contact_list = dict()

    def upsert_forwarding_table(self, routing_table, link):
        updated_destination_addresses = self.routing_table.update_routing_table(routing_table, link)
        updated_routing_table = len(updated_destination_addresses) > 0

        for destination_address, update_type in updated_destination_addresses.iteritems():
            # print "Updated Destination Address:" + str(destination_address) + ", to link: " + str(link)
            if update_type == 'Upserted':
                self.node.add_forwarding_entry(destination_address, link)
                print "Upserted (%s), DA: %s, Link_Start: %s, Link_End: %s" % (self.node.hostname, destination_address, link.startpoint.hostname, link.endpoint.hostname)
            elif update_type == 'Deleted':
                self.node.delete_forwarding_entry(destination_address, link)

        return updated_routing_table

    def receive_packet(self,received_packet):
        # print Sim.scheduler.current_time(), self.node.hostname, received_packet.ident, received_packet.body
        hostname = received_packet.body['hostname']
        self.source_address, updated_self_link = self.routing_table.check_link_to_self(self.node, hostname)
        link = self.node.get_link(hostname)
        self.check_for_inactive_links(hostname)
        updated_forwarding_table = self.upsert_forwarding_table(received_packet.body, link)

        if updated_forwarding_table or updated_self_link:
            print ("%d, %s, Updated Routing Table Values:" + str(self.routing_table.get_routing_table())) % (Sim.scheduler.current_time(), self.node.hostname)

    def check_for_inactive_links(self, hostname):
        current_time = Sim.scheduler.current_time()

        self.last_contact_list[hostname] = current_time
        print "Node: %s; Updated Hostname: %s" % (self.node.hostname, hostname)

        for contact_hostname, last_contact_time in self.last_contact_list.iteritems():
            if current_time - self.last_contact_list[hostname] >= 90:
                print "ERROR!"
            print "---->   %d: Node: %s; Hostname: %s; Last_Contact: %d seconds ago" % (current_time, self.node.hostname, contact_hostname, current_time - self.last_contact_list[hostname])

        # links_to_remove = []
        #
        # for link, last_heartbeat in self.link_tracker.iteritems():
        #     if current_time - last_heartbeat >= 90:
        #         links_to_remove.append(self.link_tracker[link])
        #         self.routing_table.remove_routing_table_entry(link)
        #         self.node.delete_forwarding_entry(self.source_address, link)
        #         print "** REMOVED FORWARDING ENTRY**"
        #
        # for link in links_to_remove:
        #     del self.link_tracker[link]

    def broadcast_routing_table(self,event):
        distance_vector_message = self.routing_table.get_routing_table()
        distance_vector_message['hostname'] = self.node.hostname
        routing_table_packet = packet.Packet(destination_address=0, ident=0, ttl=1, protocol='dvrouting', body=distance_vector_message)

        if self.broadcast_count < 100:
            Sim.scheduler.add(delay=0, event=routing_table_packet, handler=self.node.send_packet)
            Sim.scheduler.add(delay=30, event="", handler=self.broadcast_routing_table)
            self.broadcast_count += 1
        else:
            print "----------> ENDING <----------"

        if self.node.hostname == 'n1':
            Sim.scheduler.add(delay=0, event=None, handler=n1.get_link('n2').down)
            Sim.scheduler.add(delay=0, event=None, handler=n1.get_link('n3').down)
            print "---> Deactivated link <---"



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

    d1.broadcast_routing_table("")
    d2.broadcast_routing_table("")
    d3.broadcast_routing_table("")
    d4.broadcast_routing_table("")
    d5.broadcast_routing_table("")
    # d6.broadcast_routing_table("")
    # d7.broadcast_routing_table("")
    # d8.broadcast_routing_table("")
    # d9.broadcast_routing_table("")
    # d10.broadcast_routing_table("")
    # d11.broadcast_routing_table("")
    # d12.broadcast_routing_table("")
    # d13.broadcast_routing_table("")
    # d14.broadcast_routing_table("")
    # d15.broadcast_routing_table("")

    # run the simulation
    Sim.scheduler.run()
