import os
import re
import subprocess
from math import ceil
from .cstar_environment import _CSTAR_CONFIG_FILE

def _write_to_config_file(config_file_str):
    if not os.path.exists(_CSTAR_CONFIG_FILE):
        base_conf_str="# This file was generated by C-Star and is specific to your machine. "+\
            "# It contains environment information related to your cases & their dependencies. "+\
            "# You can safely delete this file, but C-Star may prompt you to re-install things if so."

        base_conf_str+='\nimport os\n'
        config_file_str=base_conf_str+config_file_str

    with open(_CSTAR_CONFIG_FILE,'a') as f:
        f.write(config_file_str)


def _get_repo_remote(local_root):
    """Take a local repository path string (local_root) and return as a string the remote URL"""
    return subprocess.run(
        f"git -C {local_root} remote get-url origin",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _get_repo_head_hash(local_root):
    """Take a local repository path string (local_root) and return as a string the commit hash of HEAD"""
    return subprocess.run(
        f"git -C {local_root} rev-parse HEAD",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _get_hash_from_checkout_target(repo_url, checkout_target):
    """
    Take a git checkout target (any `arg` accepted by `git checkout arg`) and a commit hash.

    If the target is a 7 or 40 digit hexadecimal string, it is assumed `checkout_target`
    is already a git hash, so `checkout_target` is returned.

    Otherwise, `git ls-remote` is used to obtain the hash associated with `checkout_target`.

    Parameters:
    -----------
    repo_url: str
        URL pointing to a git-controlled repository
    checkout_target: str
        Any valid argument that can be supplied to `git checkout`

    Returns:
    --------
    git_hash: str
        A git commit hash associated with the checkout target
    """

    # First check if the checkout target is a 7 or 40 digit hexadecimal string
    is_potential_hash = bool(re.match(r"^[0-9a-f]{7}$", checkout_target)) or bool(
        re.match(r"^[0-9a-f]{40}$", checkout_target)
    )

    # Then try ls-remote to see if there is a match
    # (no match if either invalid target or a valid hash):
    ls_remote = subprocess.run(
        "git ls-remote " + repo_url + " " + checkout_target,
        shell=True,
        capture_output=True,
        text=True,
    ).stdout

    if len(ls_remote) == 0:
        if is_potential_hash:
            # just return the input target assuming a hash, but can't validate
            return checkout_target
        else:
            raise ValueError(
                "supplied checkout_target does not appear "
                + "to be a valid reference for this repository"
            )
    else:
        return ls_remote.split()[0]


def _calculate_node_distribution(n_cores_required, tot_cores_per_node):
    """
    Determine how many nodes and cores per node to request from a job scheduler.

    For example, if requiring 192 cores for a job on a system with 128 cores per node,
    this method advises requesting 2 nodes with 96 cores each.

    Parameters:
    -----------
    n_cores_required: int
        The number of cores required for the job
    tot_cores_per_node: int
        The number of cores per node on the target system

    Returns:
    --------
    n_nodes_to_request: int
        The number of nodes to request from the scheduler
    cores_to_request_per_node: int
        The number of cores per node to request from the scheduler

    """
    n_nodes_to_request = ceil(n_cores_required / tot_cores_per_node)
    cores_to_request_per_node = ceil(
        tot_cores_per_node
        - ((n_nodes_to_request * tot_cores_per_node) - n_cores_required)
        / n_nodes_to_request
    )

    return n_nodes_to_request, cores_to_request_per_node


def _replace_text_in_file(file_path, old_text, new_text):
    """
    Find and replace a string in a text file.

    This function creates a temporary file where the changes are written, then
    overwrites the original file.

    Parameters:
    -----------
    file_path: str
        The local path to the text file
    old_text: str
        The text to be replaced
    new_text: str
        The text that will replace `old_text`
    """

    temp_file_path = file_path + ".tmp"

    with open(file_path, "r") as read_file, open(temp_file_path, "w") as write_file:
        for line in read_file:
            new_line = line.replace(old_text, new_text)
            write_file.write(new_line)

    os.remove(file_path)
    os.rename(temp_file_path, file_path)
