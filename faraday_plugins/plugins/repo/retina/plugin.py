#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

'''
from __future__ import absolute_import
from __future__ import print_function

from __future__ import with_statement
from faraday.client.plugins import core
import re
import os
import sys

try:
    import xml.etree.cElementTree as ET
    import xml.etree.ElementTree as ET_ORIG
    ETREE_VERSION = ET_ORIG.VERSION
except ImportError:
    import xml.etree.ElementTree as ET
    ETREE_VERSION = ET.VERSION

ETREE_VERSION = [int(i) for i in ETREE_VERSION.split(".")]

current_path = os.path.abspath(os.getcwd())

__author__ = "Francisco Amato"
__copyright__ = "Copyright (c) 2013, Infobyte LLC"
__credits__ = ["Francisco Amato"]
__license__ = ""
__version__ = "1.0.0"
__maintainer__ = "Francisco Amato"
__email__ = "famato@infobytesec.com"
__status__ = "Development"


class RetinaXmlParser(object):
    """
    The objective of this class is to parse an xml file generated by the retina tool.

    TODO: Handle errors.
    TODO: Test retina output version. Handle what happens if the parser doesn't support it.
    TODO: Test cases.

    @param retina_xml_filepath A proper xml generated by retina
    """

    def __init__(self, xml_output):
        tree = self.parse_xml(xml_output)
        if tree:
            self.items = [data for data in self.get_items(tree)]
        else:
            self.items = []

    def parse_xml(self, xml_output):
        """
        Open and parse an xml file.

        TODO: Write custom parser to just read the nodes that we need instead of
        reading the whole file.

        @return xml_tree An xml tree instance. None if error.
        """
        try:
            tree = ET.fromstring(xml_output)
        except SyntaxError as err:
            print("SyntaxError: %s. %s" % (err, xml_output))
            return None

        return tree

    def get_items(self, tree):
        """
        @return items A list of Host instances
        """
        for node in tree.findall("hosts/host"):
            yield Item(node)


class Item(object):
    """
    An abstract representation of a Item


    @param item_node A item_node taken from an retina xml tree
    """

    def __init__(self, item_node):
        self.node = item_node
        self.ip = self.get_text_from_subnode("ip")
        self.hostname = "" if self.get_text_from_subnode(
            "dnsName") == "unknown" else self.get_text_from_subnode("dnsName")
        self.netbiosname = self.get_text_from_subnode("netBIOSName")
        self.netbiosdomain = self.get_text_from_subnode("netBIOSDomain")
        self.os = self.get_text_from_subnode("os")
        self.mac = self.get_text_from_subnode("mac")

        self.vulns = self.getResults(item_node)
        self.ports = {}
        for v in self.vulns:
            if not v.port in self.ports:
                self.ports[v.port] = []
            self.ports[v.port].append(v)

    def getResults(self, tree):
        """
        :param tree:
        """
        for self.issues in tree.findall("audit"):
            yield Results(self.issues)

    def get_text_from_subnode(self, subnode_xpath_expr):
        """
        Finds a subnode in the host node and the retrieves a value from it.

        @return An attribute value
        """
        sub_node = self.node.find(subnode_xpath_expr)
        if sub_node is not None:
            return sub_node.text

        return None


class Results():

    def __init__(self, issue_node):
        self.node = issue_node
        self.name = self.get_text_from_subnode('name')

        self.description = self.get_text_from_subnode('description')
        self.solution = self.get_text_from_subnode('fixInformation')
        self.severity = self.get_text_from_subnode('risk')
        self.cve = "" if self.get_text_from_subnode(
            'cve') == 'N/A' else self.get_text_from_subnode('cve')
        self.cce = self.get_text_from_subnode('cce')
        self.date = self.get_text_from_subnode('date')
        self.pciLevel = self.get_text_from_subnode('pciLevel')
        self.pciReason = self.get_text_from_subnode('pciReason')
        self.pciPassFail = self.get_text_from_subnode('pciPassFail')
        self.cvssScore = self.get_text_from_subnode('cvssScore')
        self.exploit = self.get_text_from_subnode('exploit')
        self.context = self.get_text_from_subnode('context')
        val = self.context.split(":")
        self.port = ""
        self.protocol = ""
        if len(val) == 2:
            if val[0] in ['TCP', 'UDP']:
                self.protocol = val[0]
                self.port = val[1]

        self.desc = self.get_text_from_subnode('description')
        self.solution = self.solution if self.solution else ""
        self.desc += "\nExploit: " + self.exploit if self.exploit else ""
        self.desc += "\ncvssScore: " + self.cvssScore if self.cvssScore else ""
        self.desc += "\nContext: " + self.context if self.context else ""

        self.ref = []
        if self.cve:
            self.ref = self.cve.split(",")

    def get_text_from_subnode(self, subnode_xpath_expr):
        """
        Finds a subnode in the host node and the retrieves a value from it.

        @return An attribute value
        """
        sub_node = self.node.find(subnode_xpath_expr)
        if sub_node is not None:
            return sub_node.text

        return None


class RetinaPlugin(core.PluginBase):
    """
    Example plugin to parse retina output.
    """

    def __init__(self):
        core.PluginBase.__init__(self)
        self.id = "Retina"
        self.name = "Retina XML Output Plugin"
        self.plugin_version = "0.0.1"
        self.version = "Retina Network 5.19.2.2718"
        self.framework_version = "1.0.0"
        self.options = None
        self._current_output = None
        self._command_regex = re.compile(r'^(sudo retina|\.\/retina).*?')

        global current_path
        self._output_file_path = os.path.join(self.data_path,
                                              "retina_output-%s.xml" % self._rid)

    def parseOutputString(self, output, debug=False):

        parser = RetinaXmlParser(output)
        for item in parser.items:
            h_id = self.createAndAddHost(item.ip, item.os)
            hostname = item.hostname if item.hostname else item.ip
            i_id = self.createAndAddInterface(
                h_id, item.ip, ipv4_address=item.ip, hostname_resolution=[hostname])

            if not item.netbiosname == 'N/A':
                self.createAndAddNoteToHost(
                    h_id, "netBIOSName", item.netbiosname)

            if not item.netbiosdomain == 'N/A':
                self.createAndAddNoteToHost(
                    h_id, "netBIOSDomain", item.netbiosdomain)

            a = {}
            a.iteritems
            for k, vulns in item.ports.iteritems():
                if k:
                    for v in vulns:
                        web = False
                        s_id = self.createAndAddServiceToInterface(h_id, i_id, 'unknown',
                                                                   v.protocol.lower(),
                                                                   ports=[str(v.port)],
                                                                   status="open")

                        if v.port in ['80', '443'] or re.search("ssl|http", v.name.lower()):
                            web = True
                        else:
                            web = False

                        if web:
                            v_id = self.createAndAddVulnWebToService(h_id, s_id, v.name.encode(
                                "utf-8"), ref=v.ref, website=hostname, severity=v.severity, resolution=v.solution.encode("utf-8"), desc=v.desc.encode("utf-8"))
                        else:
                            v_id = self.createAndAddVulnToService(h_id, s_id, v.name.encode(
                                "utf-8"), ref=v.ref, severity=v.severity, resolution=v.solution.encode("utf-8"), desc=v.desc.encode("utf-8"))
                else:
                    for v in vulns:
                        v_id = self.createAndAddVulnToHost(h_id, v.name.encode(
                            "utf-8"), ref=v.ref, severity=v.severity, resolution=v.solution.encode("utf-8"), desc=v.desc.encode("utf-8"))
        del parser

    def processCommandString(self, username, current_path, command_string):
        return None

    def setHost(self):
        pass


def createPlugin():
    return RetinaPlugin()

if __name__ == '__main__':
    parser = RetinaXmlParser(sys.argv[1])
    for item in parser.items:
        if item.status == 'up':
            print(item)


# I'm Py3
