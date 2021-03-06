import ConfigParser
import errno
import os
import util


CONFIG_FILE = os.path.expanduser("~/.seaflowpy/config")


def get_config(config_path=CONFIG_FILE):
    config = ConfigParser.SafeConfigParser()
    config.read(config_path)
    return config


def get_ssh_config(config=None, config_path=CONFIG_FILE):
    # Get input for SSH section
    section = "ssh"
    dirty = False

    if not config:
        config = get_config(config_path=config_path)

    if not config.has_section(section):
        config.add_section(section)
        dirty = True
    if not config.has_option(section, "ssh-key-file"):
        response = raw_input("SSH private key location: ")
        config.set(section, "ssh-key-file", response)
        dirty = True
    if not config.has_option(section, "user"):
        response = raw_input("Remote Linux user: ")
        config.set(section, "user", response)
        dirty = True

    if dirty:
        save_config(config, config_path)

    return config

def get_aws_config(config=None, config_path=CONFIG_FILE, s3_only=False):
    section = "aws"
    dirty = False

    if not config:
        config = get_config(config_path=config_path)

    if not config.has_section(section):
        config.add_section(section)
        dirty = True

    options = ["s3-bucket"]
    if not s3_only:
        options.extend(["key-name", "security-group", "image-id"])

    for o in options:
        if not config.has_option(section, o):
            response = raw_input("{}: ".format(o))
            config.set(section, o, response)
            dirty = True

    if dirty:
        save_config(config, config_path)

    return config


def save_config(config, config_path=CONFIG_FILE):
    # Write config data to disk
    util.mkdir_p(os.path.dirname(config_path))
    with open(config_path, "w") as fh:
        config.write(fh)
