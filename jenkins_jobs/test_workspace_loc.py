import os

dev_user = os.environ['DEV_USER']
vdp_profile = os.environ['VDP_PROFILE']
jfrog_api = os.environ['JFROG_APIKEY']
host = os.environ['DEPLOYMENT_HOST']
dev_namespace = os.environ['DEV_USERNAME']
jenkins_password = os.environ['JENKINS_PASSWORD']
csp_token = os.environ['CSP_TOKEN']
jenkins_user = "jenkins"
cur_workspace= os.environ['WORKSPACE']
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
    "stack_deployer": "~/workspace/hcx_saas/easley-developer-stack-tool/devStackDeployer.sh",
    "cur_workspace": cur_workspace
}

print( "current wprospce is %s " % NON_SYS_COMMANDS["cur_workspace"])