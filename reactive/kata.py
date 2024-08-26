from urllib.request import urlopen
import os
from subprocess import check_call, check_output

from charmhelpers.core import host

from charms.reactive import (
    when,
    when_not,
    set_state,
    remove_state,
    endpoint_from_flag,
    hook,
)

from charmhelpers.fetch import (
    apt_install,
    apt_update,
    apt_purge,
    apt_autoremove,
    import_key,
)

from charmhelpers.core.hookenv import resource_get

from charms.layer import status


KATA_PACKAGES = ["kata-runtime", "kata-proxy", "kata-shim"]


@when_not("kata.installed")
@when_not("endpoint.untrusted.departed")
def install_kata():
    """
    Install the Kata container runtime.

    :returns: None
    """
    dist = host.lsb_release()
    release = "{}_{}".format(dist["DISTRIB_ID"], dist["DISTRIB_RELEASE"])

    arch = check_output(["arch"]).decode().strip()

    archive = resource_get("kata-archive")

    if not archive or os.path.getsize(archive) == 0:
        status.maintenance("Installing Kata via apt")

        with urlopen(
            "http://download.opensuse.org/repositories/home:/katacontainers:/"
            # wokeignore:rule=master
            "releases:/{}:/master/x{}/Release.key".format(arch, release)
        ) as response:
            gpg_key = response.read().decode()
        import_key(gpg_key)

        with open("/etc/apt/sources.list.d/kata-containers.list", "w") as f:
            f.write(
                "deb http://download.opensuse.org/repositories/home:/"
                # wokeignore:rule=master
                "katacontainers:/releases:/{}:/master/x{}/ /".format(arch, release)
            )

        apt_update()
        apt_install(KATA_PACKAGES)

    else:
        status.maintenance("Installing Kata via resource")
        unpack = "/tmp/kata-debs"

        if not os.path.isdir(unpack):
            os.makedirs(unpack, exist_ok=True)

        check_call(["tar", "-xvf", archive, "-C", unpack])
        check_call("apt-get install -y {}/*.deb".format(unpack), shell=True)

    status.active("Kata runtime available")
    set_state("kata.installed")


@when("endpoint.untrusted.departed")
def purge_kata():
    """
    Purge Kata containers.

    :return: None
    """
    status.maintenance("Purging Kata")

    apt_purge(KATA_PACKAGES, fatal=False)

    source = "/etc/apt/sources.list.d/kata-containers.list"
    if os.path.isfile(source):
        os.remove(source)

    apt_autoremove()

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
    endpoint.set_config(name="kata", binary_path="/usr/bin/kata-runtime")


@hook("pre-series-upgrade")
def pre_series_upgrade():
    """Set status during series upgrade."""
    status.blocked("Series upgrade in progress")


@hook("post-series-upgrade")
def post_series_upgrade():
    """Reset status to active after series upgrade."""
    status.active("Kata runtime available")
