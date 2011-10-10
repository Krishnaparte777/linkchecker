# -*- coding: iso-8859-1 -*-
# Copyright (C) 2000-2011 Bastian Kleineidam
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""Parse configuration files"""

import ConfigParser
import re
from .. import LinkCheckerError, get_link_pat


def read_multiline (value):
    """Helper function reading multiline values."""
    for line in value.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield line


class LCConfigParser (ConfigParser.RawConfigParser, object):
    """
    Parse a LinkChecker configuration file.
    """

    def __init__ (self, config):
        """Initialize configuration."""
        super(LCConfigParser, self).__init__()
        self.config = config

    def read (self, files):
        """Read settings from given config files.

        @raises: LinkCheckerError on syntax errors in the config file(s)
        """
        try:
            super(LCConfigParser, self).read(files)
            # Read all the configuration parameters from the given files.
            self.read_output_config()
            self.read_checking_config()
            self.read_authentication_config()
            self.read_filtering_config()
        except Exception, msg:
            raise LinkCheckerError(
              _("Error parsing configuration: %s") % unicode(msg))

    def read_output_config (self):
        """Read configuration options in section "output"."""
        section = "output"
        from ..logger import Loggers
        for key in Loggers.iterkeys():
            if self.has_section(key):
                for opt in self.options(key):
                    self.config[key][opt] = self.get(key, opt)
                if self.has_option(key, 'parts'):
                    val = self.get(key, 'parts')
                    parts = [f.strip().lower() for f in val.split(',')]
                    self.config[key]['parts'] = parts
        if self.has_option(section, "warnings"):
            self.config["warnings"] = self.getboolean(section, "warnings")
        if self.has_option(section, "verbose"):
            if self.getboolean(section, "verbose"):
                self.config["verbose"] = True
                self.config["warnings"] = True
        if self.has_option(section, "complete"):
            if self.getboolean(section, "complete"):
                self.config["complete"] = True
                self.config["verbose"] = True
                self.config["warnings"] = True
        if self.has_option(section, "quiet"):
            if self.getboolean(section, "quiet"):
                self.config['output'] = 'none'
                self.config['quiet'] = True
        if self.has_option(section, "debug"):
            val = self.get(section, "debug")
            parts = [f.strip().lower() for f in val.split(',')]
            self.config.set_debug(parts)
        if self.has_option(section, "status"):
            self.config["status"] = self.getboolean(section, "status")
        if self.has_option(section, "log"):
            val = self.get(section, "log").strip().lower()
            self.config['output'] = val
        if self.has_option(section, "fileoutput"):
            loggers = self.get(section, "fileoutput").split(",")
            # strip names from whitespace
            loggers = (x.strip().lower() for x in loggers)
            # no file output for the blacklist and none Logger
            loggers = (x for x in loggers if x in Loggers and
                       x not in ("blacklist", "none"))
            for val in loggers:
                output = self.config.logger_new(val, fileoutput=1)
                self.config['fileoutput'].append(output)

    def read_checking_config (self):
        """Read configuration options in section "checking"."""
        section = "checking"
        if self.has_option(section, "threads"):
            num = self.getint(section, "threads")
            self.config['threads'] = max(0, num)
        if self.has_option(section, "timeout"):
            num = self.getint(section, "timeout")
            if num < 0:
                raise LinkCheckerError(
                    _("invalid negative value for timeout: %d\n") % num)
            self.config['timeout'] = num
        if self.has_option(section, "anchors"):
            self.config["anchors"] = self.getboolean(section, "anchors")
        if self.has_option(section, "recursionlevel"):
            num = self.getint(section, "recursionlevel")
            self.config["recursionlevel"] = num
        if self.has_option(section, "warningregex"):
            val = self.get(section, "warningregex")
            if val:
                self.config["warningregex"] = re.compile(val)
        if self.has_option(section, "warnsizebytes"):
            val = self.get(section, "warnsizebytes")
            self.config["warnsizebytes"] = int(val)
        if self.has_option(section, "nntpserver"):
            self.config["nntpserver"] = self.get(section, "nntpserver")
        if self.has_option(section, "useragent"):
            self.config["useragent"] = self.get(section, "useragent")
        self.read_check_options(section)

    def read_check_options (self, section):
        """Read check* options."""
        if self.has_option(section, "checkhtml"):
            self.config["checkhtml"] = self.getboolean(section, "checkhtml")
        if self.has_option(section, "checkcss"):
            self.config["checkcss"] = self.getboolean(section, "checkcss")
        if self.has_option(section, "checkhtmlw3"):
            self.config["checkhtmlw3"] = \
               self.getboolean(section, "checkhtmlw3")
        if self.has_option(section, "checkcssw3"):
            self.config["checkcssw3"] = self.getboolean(section, "checkcssw3")
        if self.has_option(section, "scanvirus"):
            self.config["scanvirus"] = self.getboolean(section, "scanvirus")
        if self.has_option(section, "clamavconf"):
            self.config["clamavconf"] = self.getboolean(section, "clamavconf")
        if self.has_option(section, "cookies"):
            self.config["sendcookies"] = self.config["storecookies"] = \
                self.getboolean(section, "cookies")

    def read_authentication_config (self):
        """Read configuration options in section "authentication"."""
        section = "authentication"
        if self.has_option(section, "entry"):
            for val in read_multiline(self.get(section, "entry")):
                auth = val.split()
                if len(auth) == 3:
                    self.config.add_auth(pattern=auth[0], user=auth[1],
                                         password=auth[2])
                elif len(auth) == 2:
                    self.config.add_auth(pattern=auth[0], user=auth[1])
                else:
                    raise LinkCheckerError(
                       _("missing auth part in entry %(val)r") % {"val": val})
        # read login URL and field names
        if self.has_option(section, "loginurl"):
            val = self.get(section, "loginurl").strip()
            if not (val.lower().startswith("http:") or
                    val.lower().startswith("https:")):
                raise LinkCheckerError(_("invalid login URL `%s'. Only " \
                  "HTTP and HTTPS URLs are supported.") % val)
            self.config["loginurl"] = val
            self.config["storecookies"] = self.config["sendcookies"] = True
        for key in ("loginuserfield", "loginpasswordfield"):
            if self.has_option(section, key):
                self.config[key] = self.get(section, key)
        # read login extra fields
        if self.has_option(section, "loginextrafields"):
            for val in read_multiline(self.get(section, "loginextrafields")):
                name, value = val.split(":", 1)
                self.config["loginextrafields"][name] = value

    def read_filtering_config (self):
        """
        Read configuration options in section "filtering".
        """
        section = "filtering"
        if self.has_option(section, "ignorewarnings"):
            self.config['ignorewarnings'] = [f.strip() for f in \
                 self.get(section, 'ignorewarnings').split(',')]
        if self.has_option(section, "ignore"):
            for line in read_multiline(self.get(section, "ignore")):
                pat = get_link_pat(line, strict=1)
                self.config["externlinks"].append(pat)
        if self.has_option(section, "nofollow"):
            for line in read_multiline(self.get(section, "nofollow")):
                pat = get_link_pat(line, strict=0)
                self.config["externlinks"].append(pat)
        if self.has_option(section, "internlinks"):
            pat = get_link_pat(self.get(section, "internlinks"))
            self.config["internlinks"].append(pat)
