import os
import fnmatch
import time

from util.ssh.sshclient import SSH
from util.custom_logger import logger

dev_user = os.getenv('DEV_USER', 'guot')
vdp_profile = os.getenv('VDP_PROFILE', 'guot_profile')
jfrog_api = os.getenv('JFROG_APIKEY', 'AKCp8k8iZx3j9QEY8KyTTiPM8Lx4HkGc6hRiLKwzyPsfxTpmWSvanVuTLZ5zW6i4o9YRTnHwa')
host = os.getenv('DEPLOYMENT_HOST', '10.197.105.13')
dev_namespace = os.getenv('DEV_NAMESPACE', 'guottest')
jenkins_password = os.getenv('JENKINS_PASSWORD', 'ca$hc0w')
hcxaas_token = os.getenv('HCXAAS_TOKEN', '86xfIvvWzYqdgOngZ8LTRXcwpd2tJ56TTenlCTXn263XCatWMlHvbeIbgJFcpOLO')
csp_token = os.getenv('CSP_TOKEN', 'I1Z6EGec5h2PBiR7oQmA0jzviD12aH83IlngXU5AIeVFWfdha3m0Hs0Y2jTiGL6M')
jenkins_user = "jenkins"

# for non system call commands
NON_SYS_COMMANDS = {
    "kubectl": "/usr/local/bin/kubectl",
    "tilt": "~/.local/bin/tilt",
    "vdp": "~/bin/vdp",
    "remote_home": "/home/jenkins",
    "hcxaas_home": "~/workspace/hcx_saas/hcxaas-gitops",
    "log_home": "~/workspace/hcx_saas/logs",
    "cleanup": "~/workspace/hcx_saas/hcxaas-gitops/charts/dev-stack-cleanup/cleanup.sh",
    "cleanup_home": "~/workspace/hcx_saas/hcxaas-gitops/charts/dev-stack-cleanup",
    "stack_deployer_home": "~/workspace/hcx_saas/easley-developer-stack-tool",
    "stack_deployer": "~/workspace/hcx_saas/easley-developer-stack-tool/devStackDeployer.sh"
}

NAMESPACE = "hcx-hcxaas-" + dev_namespace + "-ds"
DSC_CONTEXT = "dsc-" + dev_namespace


class SaasStack():
    def __init__(self, host_ip, user, password):
        logger.info("host_ip = %s, user = %s, password = %s" % (host_ip, user, password))
        self.ssh = SSH(host_ip, user, password)

    def sync_repo(self):
        out, err = self.ssh.run_command("cd " + NON_SYS_COMMANDS["stack_deployer_home"] + " && pwd && git pull")
        logger.info("out: %s" % out)
        out, err = self.ssh.run_command("cd " + NON_SYS_COMMANDS["hcxaas_home"] + " && pwd && git pull")
        logger.info("out: %s" % out)

    def collect_pods_logs(self, log_fname, local_path):

        mkdir = "mkdir -p " + NON_SYS_COMMANDS["log_home"]
        out, err = self.ssh.run_command(mkdir)
        if not err:
            out = self.get_running_stack()
            lines = out.split("\n")
            for line in lines[1:]:
                pod_name = line.split(" ")
                logger.info("pod name: %s" % pod_name[0])
                fname = pod_name[0].replace("-", "_")
                fname += ".log"
                logger.info("Log file name: %s" % fname)
                logcmd = NON_SYS_COMMANDS["kubectl"] + " logs " + pod_name[0] + " > " + NON_SYS_COMMANDS[
                    "log_home"] + "/" + fname
                logger.info("log collect cmd: %s" % logcmd)
                out, err = self.ssh.run_command(logcmd)
                logger.info("collecting log output: %s" % out)
            tar_log_cmd = "tar -zcvf " + log_fname + " " + NON_SYS_COMMANDS["log_home"]
            home_dir, err = self.ssh.run_command("pwd")
            remote_log_path = home_dir + "/" + log_fname
            self.ssh.run_command(tar_log_cmd)
            logger.info(
                "log zip file: %s, remote path: %s, local path: %s" % (log_fname, remote_log_path, local_path))
            self.ssh.get_file(remote_log_path, local_path)

            # cleanup logs
            cleanup = "rm -rf " + NON_SYS_COMMANDS["log_home"]
            self.ssh.run_command(cleanup)
            cleanup = "rm -rf " + log_fname
            self.ssh.run_command(cleanup)

    def delete_ingress(self):
        chk_ingress = "kubectl get ing"
        out, err = self.ssh.run_command(chk_ingress)
        if err:
            logger.error("error out when running command: {}".format(err))
            return
        logger.info("Ingress generated? %s" % out)
        if out:
            lines = out.split("\n")
            for line in lines[1:]:
                groups = line.split()
                logger.info("ingress columns: %s " % groups)
                ingress_name = groups[2]
                logger.info("ingress name: %s and namespace: %s" % (ingress_name, NAMESPACE))
                if NAMESPACE in ingress_name:
                    del_ingress = "kubectl delete %s" % ingress_name
                    out, err = self.ssh.run_command(del_ingress)
                    if err:
                        logger.error("Failed to delete existing ingress.")
                    logger.info("Deleting existing ingress result: %s" % out)
                    time.sleep(60)
                    return
                else:
                    logger.warning("No associated ingress found")
            else:
                logger.info("No ingress running.")

    def shut_down_stack(self):
        if not self.any_pods():
            return
        self.delete_ingress()
        tilt_down = " cd " + NON_SYS_COMMANDS["stack_deployer_home"] + " && tilt down --context dsc-" + dev_namespace
        logger.info("shut down command: %s" % tilt_down)

        out, err = self.ssh.run_command(tilt_down)
        if err:
            raise Exception("error out when running command: {}".format(err))
        logger.info("output: %s for command %s" % (out, tilt_down))
        self.wait_for_pods_killed()
        check_port = "lsof -i tcp:10350|awk 'NR==2 {print $2}'"
        out, err = self.ssh.run_command(check_port)
        if err:
            raise Exception("error out when running command: {}".format(err))
        logger.info("Process id using port 10350: %s" % out)
        if len(out) > 0:
            _out, _err = self.ssh.run_command("kill " + out)
            logger.info("Kill process using port 10350, output: %s error: %s" % (_out, _err))
        time.sleep(300)

    def cleanup_stack_db(self):
        cleanup = "cd " + NON_SYS_COMMANDS["cleanup_home"] + " && ./cleanup.sh " + dev_namespace
        logger.info("stack clean up command: %s" % cleanup)
        out, err = self.ssh.run_command(cleanup)
        if err:
            raise Exception("error out when running command: {}".format(err))
        logger.info("output %s for command: %s" % (out, cleanup))

    def wait_for_pods_killed(self, timeout=10):
        sleep_time = 60
        cnt = 0
        while cnt < timeout:
            if self.any_pods():
                time.sleep(sleep_time)
                cnt += 1
            else:
                logger.info("All pods got tilted down.")
                return

        raise Exception("Time out to wait for stack pods to be killed.")

    def wait_for_all_pods_up(self, timeout=15):
        sleep_time = 60
        cnt = 0
        pod_exist = self.any_pods()
        logger.info("stack pods deployed? %s" % pod_exist)
        while cnt < timeout and pod_exist:
            out = self.get_running_stack()
            lines = out.split("\n")
            logger.info("running stacks: %s" % out)
            num_pods = len(lines) - 1
            if num_pods == 0:
                logger.error("No pods deployed.")
                return
            for line in lines[1:]:
                columns = line.split()
                logger.info("Status columns info: %s and num_pods = %s" % (columns[2], num_pods))
                if columns[2] in ["Running", "running", "Completed", "completed"]:
                    num_pods -= 1
                if num_pods == 0:
                    logger.info("All pods are up now : %s" % out)
                    return

            time.sleep(sleep_time)
            cnt += 1

            logger.info("Waiting for all pods to be up. time elapsed: %s " % cnt * sleep_time)

        raise Exception("Time out to wait for stack pods to be killed.")

    def get_running_stack(self):
        check_running_pods = NON_SYS_COMMANDS["kubectl"] + ' get pods -n ' + NAMESPACE
        logger.info("cmd= %s" % check_running_pods)
        out, err = self.ssh.run_command(check_running_pods)
        logger.info("run command result: out=%s, error = %s" % (out, err))
        if err and not fnmatch.fnmatch(str(err), "No resources found in *" + dev_namespace + "*namespace."):
            raise Exception("error out when running command: {}".format(err))
        logger.info("command %s \n response: %s\n" % (check_running_pods, out))
        if not out and fnmatch.fnmatch(str(err), "No resources found in *" + dev_namespace + "*namespace."):
            return str(err)
        return out

    def any_pods(self):
        out = self.get_running_stack()
        return not fnmatch.fnmatch(out, "No resources found in *" + dev_namespace + "*namespace.")

    def is_vdp_profile_avail(self):
        check_vdp_profile = NON_SYS_COMMANDS["vdp"] + ' profile list'
        logger.info("vdp profilr list command: %s" % check_vdp_profile)
        out, err = self.ssh.run_command(check_vdp_profile)
        if err:
            raise Exception("error out when running command: {}".format(err))
        return vdp_profile in out

    def delete_vdp_profile(self, _vdp_profile):
        del_vdp_profile = NON_SYS_COMMANDS["vdp"] + ' profile delete ' + _vdp_profile
        out, err = self.ssh.run_command(del_vdp_profile)
        logger.info("output for deleting VDP profile: %s" % out)


    def create_vdp_profile(self):
        out, err = None, None
        if self.is_vdp_profile_avail():
            self.delete_vdp_profile(vdp_profile)

        gen_vdp_profile = NON_SYS_COMMANDS[
                              "vdp"] + ' profile set ' + vdp_profile + ' --endpoint https://api.vdp-stg.vmware.com' + \
                          ' --token ' + hcxaas_token + ' --activate'
        logger.info("create vdp profile command: %s" % gen_vdp_profile)
        out, err = self.ssh.run_command(gen_vdp_profile)
        if err:
            raise Exception("error out when running command: {}".format(err))
        logger.info("Output for VDP profile creation: %s" % out)

    def deploy_dev_stack(self, tilt_port=None):
        self.sync_repo()
        self.shut_down_stack()
        self.cleanup_stack_db()
        deployer_file = "deployer.sh"
        cfg_file = NON_SYS_COMMANDS["stack_deployer_home"] + "/config/hcxaas.config"
        deployer = "cd " + NON_SYS_COMMANDS[
            "stack_deployer_home"] + " && ./devStackDeployer.sh --config-file " + cfg_file + " --dev-username " + dev_namespace \
                   + " --csp-token " + csp_token + " --vdp-profile " + vdp_profile + " --destroy false " + " --jfrog-username " \
                   + dev_user + " --jfrog-apiKey " + jfrog_api + " --chart-dir " + \
                   NON_SYS_COMMANDS["hcxaas_home"] + "/charts/unstable-stack --tilt-ci --tilt-down false >deployment.log"
        if tilt_port:
            deployer += " --tilt_port " + tilt_port
        with open(deployer_file, "w") as fp:
            fp.write(deployer)
        local_path = os.path.abspath(".") + "/" + deployer_file
        remot_path = NON_SYS_COMMANDS["remote_home"] + "/" + deployer_file
        self.ssh.put_file(remot_path, local_path)
        logger.info("Command to deploy dev stack: %s" % deployer)
        out, err = self.ssh.run_command("pwd && ls -la")
        logger.info("current folder: %s" % out)
        # make file executable
        cmd = "chmod +x " + deployer_file
        out, err = self.ssh.run_command(cmd)
        if err:
            raise Exception("error out when running command: {}".format(err))

        out, err = self.ssh.run_command(deployer)
        logger.info("out = %s and error = %s for deploy command: %s" % (out, err, deployer))
        time.sleep(30)
        #added retry for webhook error
        cmd = "grep 'admission webhook .webhook\.openpolicyagent\.org. denied the request' " + NON_SYS_COMMANDS[
            "stack_deployer_home"] + "/deployment.log"
        out, err = self.ssh.run_command(cmd)
        if not err:
            self.shut_down_stack()
            out, err = self.ssh.run_command(deployer)
            logger.info("out = %s and error = %s for retrying deployment command: %s" % (out, err, deployer))
            time.sleep(30)

        if self.any_pods():
            self.wait_for_all_pods_up()


if __name__ == '__main__':
    saas = SaasStack(host, jenkins_user, jenkins_password)
    saas.create_vdp_profile()
    logger.info("vdp profile exists? %s" % saas.is_vdp_profile_avail())
    saas.deploy_dev_stack()
