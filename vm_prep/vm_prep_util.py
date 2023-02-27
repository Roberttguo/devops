import uuid

from test.lib.testbed_parser import TBParser
from util.custom_logger import logger
from util.vc.vc_rest_util import VCRestUtil


class VMPrep:

    def __init__(self, testbed, migration_type):
        self.tb = testbed
        self.migration_type = migration_type
        self.vms = []

    def prepare_VMs(self, vc_name, vm_prefix, connect_net, num_vms, vm_template_name):
        """

        Args:
            vc_name: vc name in testbed
            vm_prefix: vm prefix to create
            connect_net: str, network name that first network adapter of created vm is to connect
            num_vms: int, number of vms to create with the same vm prefix
            vm_template_name: vm template based to clone

        Returns: list of created vms with name, vm id, ip, mac addr, network type, network id, migration type

        """

        tb = TBParser(self.tb)
        vchost = tb.get_host_info(vc_name)
        logger.info("vc host: %s, base vm: %s" % (vchost, vm_template_name))
        src_vc = VCRestUtil(vchost["ip"], vchost["username"], vchost["password"])
        if src_vc.exists_byname(vm_template_name):
            logger.info("VM %s exists in src site." % vm_template_name)
        else:
            raise Exception("template %s does not exist on VC %s" %(vm_template_name, vchost["ip"]))

        vm_id = src_vc.get_vm_id(vm_template_name)
        logger.debug("template VM ID: %s" % vm_id)
        for i in range(num_vms):
            migration_vm = vm_prefix + uuid.uuid4().hex[:8]
            logger.info("VM to migrate: %s" % migration_vm)
            src_vc.cloneVM(vm_id, migration_vm)
            src_vc.change_vm_network(migration_vm, 0, connect_net)
            self.vms.append({"name": migration_vm, "migration_type": self.migration_type})

            mb_vm_id = src_vc.get_vm_id(self.vms[-1]["name"])
            ip = src_vc.wait_for_ip_assignment(mb_vm_id, timeout=240)
            if not ip:
                raise Exception("No VM ip assigned: ")
            logger.info("VM ip assigned: %s" % ip)
            self.vms[-1]["vm_id"] = mb_vm_id
            self.vms[-1]["ip"] = ip
            mac_add = src_vc.get_vm_first_network_mac(mb_vm_id)
            self.vms[-1]["mac_add"] = mac_add

            t = src_vc.get_vm_first_connected_network(mb_vm_id)
            if not any(t):
                raise Exception("No VM with connected network.")
            self.vms[-1]["network_type"] = t[0]
            self.vms[-1]["network_id"] = t[1]
            logger.info("VMs created: %s" % self.vms)
        return self.vms

