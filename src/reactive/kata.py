import os
import subprocess
from pathlib import Path

from charms.reactive import (
    endpoint_from_flag,
    hook,
    is_flag_set,
    remove_state,
    set_state,
    when,
    when_not,
)

from charmhelpers.core import hookenv
from charms.layer import status


KATA_PATHS = [Path("/opt/kata"), Path("/usr/bin/kata-runtime")]


def check_cpu_virtualization():
    """Check if CPU virtualization is supported."""
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        return "vmx" in cpuinfo or "svm" in cpuinfo
    except Exception as e:
        hookenv.log(f"Error reading /proc/cpuinfo: {e}", hookenv.ERROR)
    return False


def check_kvm_device():
    """Check if the KVM device is available."""
    dev_kvm = Path("/dev/kvm")
    return dev_kvm.exists() and os.access(dev_kvm, os.R_OK | os.W_OK)


def check_kata_runtime():
    """Check if the Kata runtime is installed."""
    try:
        subprocess.check_output(
            ["which", "kata-runtime"], capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        hookenv.log(f"Error checking kata-runtime: {e}", hookenv.ERROR)
        return False
    return True


def check_kata_version() -> str:
    """Check the version of the Kata runtime."""
    try:
        version_str = subprocess.check_output(
            ["kata-runtime", "version"], text=True
        ).splitlines()[0]
        return version_str.split(":")[-1].strip()
    except subprocess.CalledProcessError as e:
        hookenv.log(f"Error checking kata-runtime version: {e}", hookenv.ERROR)
        return ""


@when_not("kata.installed")
@when_not("endpoint.untrusted.departed")
def install_kata():
    """
    Install the Kata container runtime.

    :returns: None
    """
    if not check_cpu_virtualization():
        status.blocked("CPU virtualization not supported")
        return

    if not check_kvm_device():
        status.blocked("KVM device not available")
        return

    kata_manager = hookenv.resource_get("kata-manager")
    if not kata_manager or os.path.getsize(kata_manager) == 0:
        status.blocked("Resource 'kata-manager' not attached")
        return

    status.maintenance("Installing Kata")
    Path(kata_manager).chmod(0o755)
    args = [kata_manager, "-o"]

    archive = hookenv.resource_get("kata-archive")
    if archive and os.path.getsize(archive) != 0:
        status.maintenance("Installing Kata via 'kata-archive'")
        args += ["-K", archive]
    else:
        status.maintenance("Installing Kata via upstream fetch")

    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError:
        status.blocked("Failed to install Kata: see debug-log")
        return

    if not check_kata_runtime():
        status.blocked("Kata runtime not installed")
        return

    if version := check_kata_version():
        if is_flag_set("leadership.is_leader"):
            hookenv.application_version_set(version)
    else:
        status.blocked("Error checking kata-runtime version")
        return

    status.active(f"Kata runtime available ({version})")
    set_state("kata.installed")


@when("endpoint.untrusted.departed")
def purge_kata():
    """
    Purge Kata containers.

    :return: None
    """
    status.maintenance("Purging Kata")

    for path in KATA_PATHS:
        if path.exists():
            path.unlink()

    remove_state("kata.installed")


@when("kata.installed")
@when("endpoint.untrusted.joined")
@when_not("endpoint.untrusted.departed")
def publish_config():
    """
    Pass configuration over the interface.

    :return: None
    """
    endpoint = endpoint_from_flag("endpoint.untrusted.joined")
    endpoint.set_config(name="kata", binary_path=KATA_PATHS[1])


@hook("pre-series-upgrade")
def pre_series_upgrade():
    """Set status during series upgrade."""
    status.blocked("Series upgrade in progress")


@hook("post-series-upgrade")
def post_series_upgrade():
    """Reset status to active after series upgrade."""
    status.active("Kata runtime available")
