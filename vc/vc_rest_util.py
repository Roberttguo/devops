"""
VMware vsphere access utility via REST APIs
refer: https://developer.vmware.com/apis/191/vsphere-automation
"""
import time
import uuid

import requests
import urllib3
from requests import Response

from util.vc import vc_common_url as url
from util.network import network_tool
from util.custom_logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class VCRestUtil():

    def __init__(self, host, username, password, new_api=False):
        self.session = requests.Session()
        self.session.verify = False

        self.is_new_api = new_api
        _url = ""
        if not new_api:
            _url = url.SESSION % (host, 'rest')
        else:
            _url = url.SESSION % (host, 'api')
        self.session.post(_url, auth=(username, password))
        self.host = host

    def _get_vc_session(self, vcip, username, password):
        return self.session

    def cloneVM(self, from_vm_id, to_vm_name, placement={}, power_on=False):
        """
        clone a VM from existing VM
        from_vm_id: string, vm id instead of vm name.
        to_vm_name: name of target VM.
        placement: dict, if empty, use the same resource as source VM to clone the VM
        power_on: boolean. True- power on the cloned VM, False- do not power on
        """

        if not self.is_new_api:
            _url = url.CLONE_VM % (self.host, 'rest')
        else:
            _url = url.CLONE_VM % (self.host, 'api')

        data = {"spec": {"name": to_vm_name, "source": from_vm_id, "power_on": True}}
        if len(placement) > 0:
            data["spec"]["placement"] = placement

        return self.session.post(_url, json=data, headers={"Content-Type": "application/json"})

    def get_vc_network(self):
        if not self.is_new_api:
            _url = url.NETWORK % (self.host, 'rest')
        else:
            _url = url.NETWORK % (self.host, 'api')

        return self.session.get(_url)

    def get_vms(self):
        if not self.is_new_api:
            _url = url.VM_QUERY % (self.host, 'rest')
        else:
            _url = url.VM_QUERY % (self.host, 'api')
        return self.session.get(_url)

    def get_vm_id(self, vmname):
        res = self.get_vms()
        if res.ok:
            vm_arr = res.json()["value"]
            for vm_entity in vm_arr:
                if vm_entity["name"] == vmname:
                    return vm_entity["vm"]
        return ""

    def get_vm_ethernet(self, vm_id):
        """
        return given vm's ethernet info
        """
        if not self.is_new_api:
            _url = url.ETHENET % (self.host, 'rest', vm_id)
        else:
            _url = url.ETHENET % (self.host, 'api', vm_id)
        return self.session.get(_url)

    def get_vm_ethernet_adapter(self, vm_id, nic_id):
        """
        return given vm's ethernet nic info
        """
        if not self.is_new_api:
            _url = url.ETHENET_ADAPTER % (self.host, 'rest', vm_id, nic_id)
        else:
            _url = url.ETHENET_ADAPTER % (self.host, 'api', vm_id, nic_id)
        return self.session.get(_url)

    def get_vm_guest_networks(self, vm_id):
        """
        return given vm's guest network
        """
        if not self.is_new_api:
            _url = url.GUEST_NETWORK % (self.host, 'rest', vm_id)
        else:
            _url = url.GUEST_NETWORK % (self.host, 'api', vm_id)
        return self.session.get(_url)

    def get_vm_template(self):
        """
        return vm template list from vcenter
        """

        if not self.is_new_api:
            _url = url.TEMPLATE % (self.host, 'rest')
        else:
            _url = url.TEMPLATE % (self.host, 'api')
        return self.session.get(_url)

    def get_ethernet_nic(self, vm_id, nic_id):
        """
        return given ethernet nic's info
        """
        if not self.is_new_api:
            _url = url.ETHENET_ADAPTER % (self.host, 'rest', vm_id, nic_id)
        else:
            _url = url.ETHENET_ADAPTER % (self.host, 'api', vm_id, nic_id)
        return self.session.get(_url)

    def get_vm_ip(self, vm_id):
        """
        return given ethernet nic's info
        """
        if not self.is_new_api:
            _url = url.VM_IP % (self.host, 'rest', vm_id)
        else:
            _url = url.VM_IP % (self.host, 'api', vm_id)
        res = self.session.get(_url)
        logger.info("response for querying VM IP: %s" % res.json())
        if res.status_code == 200 and "ip_address" in res.json()["value"]:
            return res.json()["value"]["ip_address"]
        else:
            return None

    def get_vm_first_connected_network(self, vm_id):
        """
        
        Args:
            vm_id: 

        Returns: vm first connected network's type, network id, mac address if there is a network connected,
                otherwise, return None,None, None
        
        """

        eth: Response = self.get_vm_ethernet(vm_id)
        if eth.status_code == 200:
            for i in range(len(eth.json()["value"])):
                nic_info: Response = self.get_ethernet_nic(vm_id, eth.json()["value"][i]["nic"])
                if nic_info.json()["value"]["start_connected"]:
                    obj = nic_info.json()["value"]["backing"]
                    return obj["type"], obj["network"], nic_info.json()["value"]["mac_address"]
        return None, None, None

    def get_vm_first_network_mac(self, vm_id):
        mac_add = self.get_vm_first_connected_network(vm_id)[2]
        if mac_add:
            return mac_add

        eth = self.get_vm_ethernet(vm_id)
        logger.info("ethernet info: %s" % eth.json())
        if isinstance(eth.json()["value"], list):
            nic_info = self.get_ethernet_nic(vm_id, eth.json()["value"][0]["nic"])
            return nic_info.json()["value"]["mac_address"]
        else:
            if eth.status_code != 200 or not eth.json():
                logger.error("Unable to get ethernet info!")
                return None
            nic_info = self.get_ethernet_nic(vm_id, eth.json()["value"]["nic"])
            return nic_info.json()["value"]["mac_address"]

    def change_vm_network(self, vm_name, nic_index, network_name):
        if not self.exists_byname(vm_name):
            logger.error("VM %s does not exist." % vm_name)
            return
        vm_id = self.get_vm_id(vm_name)
        ethernet_list = self.get_vm_ethernet(vm_id).json()["value"]
        if len(ethernet_list) < nic_index + 1:
            logger.error("No ethernet nic configured.")
            return
        nic_id = ethernet_list[nic_index]["nic"]
        network_list = self.get_vc_network().json()["value"]
        network_type, network_id = None, None
        for it in network_list:
            if it["name"] == network_name:
                network_type, network_id = it["type"], it["network"]

        if not network_type or not network_id:
            logger.error("Specified network not found.")
            return

        if not self.is_new_api:
            _url = url.ETHENET_ADAPTER % (self.host, 'rest', vm_id, nic_id)
        else:
            _url = url.ETHENET_ADAPTER % (self.host, 'api', vm_id, nic_id)

        data = {"spec": {"backing": {"type": network_type, "network": network_id}}}
        return self.session.patch(_url, json=data, headers={"Content-Type": "application/json"})

    def exists_byname(self, vmname):
        """
        check if vm exists by its name
        vmname: str
        return: bool
        """
        res = self.get_vms()
        if res.ok:
            vm_arr = res.json()["value"]
            for vm_entity in vm_arr:
                if vm_entity["name"] == vmname:
                    return True
        return False

    def wait_for_ip_assignment(self, vmid, timeout, sleep=10):

        time_lapsed = 0
        while time_lapsed < timeout:
            ip = self.get_vm_ip(vmid)
            if ip is not None and network_tool.is_valid_ip(ip):
                return ip
            time.sleep(sleep)
            time_lapsed += sleep

        return ""


if __name__ == '__main__':
    vc = VCRestUtil("10.49.67.7", "administrator@vsphere.local", "Admin!23")
    vm_id = vc.get_vm_id("hcxaas_vm_ba1712dd")
    print("vm_id=%s" % vm_id)
    ip_info = vc.get_vm_guest_networks(vm_id)
    print("ips: %s" % ip_info.json())
    eth = vc.get_vm_ethernet(vm_id)
    print("ethernet: %s" % eth.json())
    nic_info = vc.get_ethernet_nic(vm_id, eth.json()["value"][0]["nic"])
    print("nic info: %s" % nic_info.json())
    t = vc.get_vm_first_connected_network(vm_id)
    print("Expected first connected net: %s, %s, %s" % (t[0], t[1], t[2]))
    print("Expecte mac address: %s" % vc.get_vm_first_network_mac(vm_id))
    print("VM IP = %s" % vc.get_vm_ip(vm_id))
    exit(0)
    ethernet_info_ = vc.get_ethernet_nic(vm_id, 4000)
    print("hcxaas_vm_c46511df ethernet 0: %s" % ethernet_info_.json())
    # vc.change_vm_network("hcxaas_vm38b86333",0, "stretch3001")
    print("vm list: ", vc.get_vms().json())
    exit(0)

    r = vc.get_vms()
    print("VMs: ", r.json())
    print("Customcentos exists? ", vc.exists_byname("Customcentos"))
    from_vm = vc.get_vm_id("hcxaas_vm38b86333")
    print("from VM id:", from_vm)
    print("guest network: ", vc.get_vm_guest_networks(from_vm).json())

    ethernet = vc.get_vm_ethernet(from_vm)
    print("hcxaas_vm38b86333 ethernet? ", ethernet, ethernet.ok, ethernet.json())

    print("guest network: ", vc.get_vm_guest_networks(from_vm).json())

    print("Nic info: ", vc.get_ethernet_nic(from_vm, '4000').json())
    print("VC networks: ", vc.get_vc_network().json())
    exit(0)
    for it in ethernet.json()["value"]:
        print("nic info:", vc.get_ethernet_nic(from_vm, it["nic"]).json())

    print("vm template list: ", vc.get_vm_template().json())
