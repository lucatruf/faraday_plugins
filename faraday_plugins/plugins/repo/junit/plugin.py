"""
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

"""
import os
from lxml import etree
from faraday_plugins.plugins.plugin import PluginBase


try:
    import xml.etree.cElementTree as ET
    import xml.etree.ElementTree as ET_ORIG
    ETREE_VERSION = ET_ORIG.VERSION
except ImportError:
    import xml.etree.ElementTree as ET
    ETREE_VERSION = ET.VERSION

ETREE_VERSION = [int(i) for i in ETREE_VERSION.split(".")]

current_path = os.path.abspath(os.getcwd())

__author__ = "Thierry Beauquier"
__license__ = ""
__version__ = "1.0.0"
__maintainer__ = "Thierry Beauquier"
__email__ = "thierry.beauquier@ericsson.com"
__status__ = "Development"

"""
This plugin has been designed to be used with python-unittest2/paramiko script to perform security compliancy verification. It enables to have displayed both security scans results (nmap,
nessus, ..) and security verification compliancy (CIS-CAT, compagny's product security requirement) by Faraday-IPE

This plugin requires that a element "host" is added to <testcase/> (sed -i 's/<testcase/<testcase host=\"192.168.1.1\"/' junit.xml) 

 <testsuite errors="0" failures="1" name="AccountsWithSuperuserPrivilegesShallBeDisabledByDefault-20170118090010" skipped="0" tests="1" time="0.144">
                <testcase host="192.168.1.1" classname="AccountsWithSuperuserPrivilegesShallBeDisabledByDefault" name="test_sshdRootLogin" time="0.144">
                        <failure message="SSH for root account is not disabled: '' matches '' in ''" type="AssertionError">
<![CDATA[Traceback (most recent call last):
  File "bsr-ci.py", line 514, in test_sshdRootLogin
    self.assertNotRegexpMatches(_ssh('cat /etc/ssh/sshd_config | egrep "^PermitRootLogin" | awk \'{print $2}\' | egrep "no|No|NO"',host),'', 'SSH for root account is not disabled')
AssertionError: SSH for root account is not disabled: '' matches '' in ''
]]>                     </failure>
                </testcase>
                <system-out>
<![CDATA[]]>            </system-out>
                <system-err>
<![CDATA[]]>            </system-err>
  </testsuite>


"""


class JunitXmlParser:
    """
    The objective of this class is to parse an xml file generated by the junit.

    @param junit_xml_filepath A proper xml generated by junit
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

        @return xml_tree An xml tree instance. None if error.
        """
        try:
            tree = etree.fromstring(xml_output)
        except SyntaxError as err:
            print("SyntaxError: %s. %s" % (err, xml_output))
            return None
        return tree

    def get_items(self, tree):
        """
        @return items A list of Failure instances
        """

        for node in tree.findall('testsuite/testcase/failure'):
            yield Testsuite(node)


class Testsuite:

    def __init__(self, testsuite_node):
        self.node = testsuite_node

        self.parent = self.node.getparent()
        self.name = self.parent.get('name')
        self.host = self.parent.get('host')
        if self.host is None:
            print('host element is missing')
            self.host = ''

        self.message = self.get_text_from_subnode('message')

    def get_text_from_subnode(self, subnode_xpath_expr):
        """
        Finds a subnode in the host node and the retrieves a value from it.

        @return An attribute value
        """
        sub_node = self.node.get(subnode_xpath_expr)
        if sub_node is not None:
            return sub_node

        return None


class JunitPlugin(PluginBase):
    """
    Example plugin to parse junit output.
    """

    def __init__(self):
        super().__init__()
        self.id = "Junit"
        self.name = "Junit XML Output Plugin"
        self.plugin_version = "0.0.1"
        self.version = ""
        self.framework_version = "1.0.0"
        self.options = None
        self._current_output = None
        self._command_regex = None 

    def parseOutputString(self, output, debug=False):

        parser = JunitXmlParser(output)
        for item in parser.items:
            h_id = self.createAndAddHost(item.host, os="Linux")
            i_id = self.createAndAddInterface(h_id, item.host, ipv4_address=item.host)
            self.createAndAddVulnToHost(h_id, name=item.name, desc=item.message, ref=[], severity="High")
        del parser


def createPlugin():
    return JunitPlugin()


if __name__ == "__main__":
    import sys
    import os
    if len(sys.argv) == 2:
        report_file = sys.argv[1]
        if os.path.isfile(report_file):
            plugin = createPlugin()
            plugin.processReport(report_file)
            print(plugin.get_json())
        else:
            print(f"Report not found: {report_file}")
    else:
        print(f"USAGE {sys.argv[0]} REPORT_FILE")
