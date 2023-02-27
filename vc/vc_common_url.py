HEAD = "https://%s"
SESSION = HEAD + "/%s/com/vmware/cis/session"

VM_QUERY = HEAD+"/%s/vcenter/vm"
CLONE_VM = HEAD+"/%s/vcenter/vm?action=clone"


VM_HARDWARE = HEAD + "/%s/vcenter/vm/%s/hardware"
NETWORK = HEAD + "/%s/vcenter/network"

GUEST_NETWORK = HEAD+"/%s/vcenter/vm/%s/guest/networking"
VM_IP = HEAD+"/%s/vcenter/vm/%s/guest/identity"

ETHENET = VM_HARDWARE + "/ethernet"
ETHENET_ADAPTER = ETHENET + "/%s"



TEMPLATE = HEAD + "/%s/vcenter/vm-template/library-items"
