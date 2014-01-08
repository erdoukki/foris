# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from foris import gettext as _
from form import Password, Textbox, Dropdown, Checkbox, Hidden, Radio
import fapi
from nuci import client, filters
from nuci.modules.uci_raw import Uci, Config, Section, Option, List, Value
from validators import LenRange
import validators
import bottle


class BaseConfigHandler(object):
    def __init__(self, data=None):
        self.data = data
        self.__form_cache = None

    @property
    def form(self):
        if self.__form_cache is None:
            self.__form_cache = self.get_form()
        return self.__form_cache

    def call_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        raise NotImplementedError()

    def get_form(self):
        """Get form for this wizard. MUST be a single-section form.

        :return:
        :rtype: fapi.ForisForm
        """
        raise NotImplementedError()

    def save(self, extra_callbacks=None):
        """

        :param extra_callbacks: list of extra callbacks to call when saved
        :return:
        """
        form = self.form
        form.validate()
        if extra_callbacks:
            for cb in extra_callbacks:
                form.add_callback(cb)
        if form.valid:
            form.save()
            return True
        else:
            return False


class PasswordHandler(BaseConfigHandler):
    """
    Setting the password
    """
    
    # {{ _("Password") }} - for translation
    userfriendly_title = "Password"
    
    def get_form(self):
        # form definitions
        pw_form = fapi.ForisForm("password", self.data)
        pw_main = pw_form.add_section(name="set_password", title=_(self.userfriendly_title),
                                      description=_("Set your password for this administation site."
                                                    " The password must be at least 6 charaters long."))
        pw_main.add_field(Password, name="password", label=_("Password"), required=True,
                          validators=LenRange(6, 60))
        pw_main.add_field(Password, name="password_validation", label=_("Password (repeat)"))
        pw_main.add_field(Checkbox, name="set_system_pw", label=_("Use this password for advanced configuration"),
                          hint=_("Same password would be used for accessing this administration "
                                 "site, for root user in LuCI web interface and for SSH login. "
                                 "Use a strong password!"))
        pw_form.add_validator(validators.FieldsEqual("password", "password_validation",
                                                     _("Passwords are not equal.")))

        def pw_form_cb(data):
            from beaker.crypto import pbkdf2
            # use 48bit pseudo-random salt internally generated by pbkdf2
            password = pbkdf2.crypt(data['password'], iterations=1000)

            uci = Uci()
            foris = Config("foris")
            uci.add(foris)
            auth = Section("auth", "config")
            foris.add(auth)
            auth.add(Option("password", password))

            return "edit_config", uci

        def pw_form_system_pw_cb(data):
            if data['set_system_pw'] is True:
                client.set_password("root", data['password'])

            return "none", None

        pw_form.add_callback(pw_form_cb)
        pw_form.add_callback(pw_form_system_pw_cb)
        return pw_form


class WanHandler(BaseConfigHandler):
    # {{ _("WAN") }} - for translation
    userfriendly_title = "WAN"
    
    def get_form(self):
        # WAN
        wan_form = fapi.ForisForm("wan", self.data, filter=filters.uci)
        wan_main = wan_form.add_section(name="set_wan", title=_(self.userfriendly_title),
                                        description=_("Here you specify your WAN port settings. "
                "Usualy you can leave this options untouched unless explicitly specified otherwise by your "
                "internet service provider. And even in that case change it only if Turris is connected "
                "directly to your ISP and not through a cable or DSL modem."))

        WAN_DHCP = "dhcp"
        WAN_STATIC = "static"
        WAN_PPPOE = "pppoe"
        WAN_OPTIONS = (
            (WAN_DHCP, _("DHCP")),
            (WAN_STATIC, _("Static IP address")),
            (WAN_PPPOE, _("PPPoE")),
        )
        
        # protocol
        wan_main.add_field(Dropdown, name="proto", label=_("Protocol"),
                           nuci_path="uci.network.wan.proto",
                           args=WAN_OPTIONS, default=WAN_DHCP)
        
        # static ipv4
        wan_main.add_field(Textbox, name="ipaddr", label=_("IP address"),
                           nuci_path="uci.network.wan.ipaddr",
                           required=True, validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="netmask", label=_("Network mask"),
                           nuci_path="uci.network.wan.netmask",
                           required=True, validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="gateway", label=_("Gateway"),
                           nuci_path="uci.network.wan.gateway",
                           validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="dns", label=_("DNS server"),
                           nuci_path="uci.network.wan.dns",
                           required=True, validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)

        # static ipv6
        wan_main.add_field(Checkbox, name="static_ipv6", label=_("Use IPv6"),
                           nuci_path="uci.network.wan.ip6addr",
                           nuci_preproc=lambda val: bool(val.value))\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="ip6addr", label=_("IPv6 address"),
                           nuci_path="uci.network.wan.ip6addr",
                           required=True)\
            .requires("proto", WAN_STATIC)\
            .requires("static_ipv6", True)
        wan_main.add_field(Textbox, name="ip6gw", label=_("IPv6 gateway"),
                           nuci_path="uci.network.wan.ip6gw")\
            .requires("proto", WAN_STATIC)\
            .requires("static_ipv6", True)
        wan_main.add_field(Textbox, name="ip6prefix", label=_("IPv6 prefix"),
                           nuci_path="uci.network.wan.ip6prefix")\
            .requires("proto", WAN_STATIC)\
            .requires("static_ipv6", True)

        wan_main.add_field(Textbox, name="username", label=_("PAP/CHAP username"),
                           nuci_path="uci.network.wan.username")\
            .requires("proto", WAN_PPPOE)
        wan_main.add_field(Textbox, name="password", label=_("PAP/CHAP password"),
                           nuci_path="uci.network.wan.password")\
            .requires("proto", WAN_PPPOE)
        wan_main.add_field(Checkbox, name="ppp_ipv6", label=_("Enable IPv6"),
                           nuci_path="uci.network.wan.ipv6",
                           nuci_preproc=lambda val: bool(int(val.value)))\
            .requires("proto", WAN_PPPOE)

        wan_main.add_field(Checkbox, name="custom_mac", label=_("Custom MAC address"),
                           nuci_path="uci.network.wan.macaddr",
                           nuci_preproc=lambda val: bool(val.value),
                           hint=_("Useful in cases, when a specific MAC address is required by "
                                  "your internet service provider."))

        wan_main.add_field(Textbox, name="macaddr", label=_("MAC address"),
                           nuci_path="uci.network.wan.macaddr",
                           validators=validators.MacAddress())\
            .requires("custom_mac", True)
        
        def wan_form_cb(data):
            uci = Uci()
            config = Config("network")
            uci.add(config)

            wan = Section("wan", "interface")
            config.add(wan)
            
            wan.add(Option("proto", data['proto']))
            if data['custom_mac'] is True:
                wan.add(Option("macaddr", data['macaddr']))
            else:
                wan.add_removal(Option("macaddr", None))
            
            ucollect_ifname = "eth2"

            if data['proto'] == WAN_PPPOE:
                wan.add(Option("username", data['username']))
                wan.add(Option("password", data['password']))
                wan.add(Option("ipv6", data['ppp_ipv6']))
                ucollect_ifname = "pppoe-wan"
            elif data['proto'] == WAN_STATIC:
                wan.add(Option("ipaddr", data['ipaddr']))
                wan.add(Option("netmask", data['netmask']))
                wan.add(Option("gateway", data['gateway']))
                if data.get("static_ipv6") is True:
                    wan.add(Option("ip6addr", data['ip6addr']))
                    wan.add(Option("ip6gw", data['ip6gw']))
                    wan.add(Option("ip6prefix", data['ip6prefix']))
                else:
                    wan.add_removal(Option("ip6addr", None))
                    wan.add_removal(Option("ip6gw", None))
                    wan.add_removal(Option("ip6prefix", None))

            # set interface for ucollect to listen on
            ucollect = Config("ucollect")
            # FIXME: replacing whole config is... an ugly work-around
            uci.add_replace(ucollect)
            interface = Section(None, "interface", True)
            ucollect.add(interface)
            interface.add(Option("ifname", ucollect_ifname))

            return "edit_config", uci

        wan_form.add_callback(wan_form_cb)

        return wan_form


class TimeHandler(BaseConfigHandler):
    # {{ _("Time") }} - for translation
    userfriendly_title = "Time"
    
    def _action_ntp_update(self):
        return client.ntp_update()

    def call_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        if action == "ntp_update":
            ntp_ok = self._action_ntp_update()
            return dict(success=ntp_ok)
        elif action == "time_form":
            if hasattr(self, 'render') and callable(self.render):
                # only if the subclass implements render
                return dict(success=True, form=self.render(is_xhr=True))
        raise ValueError("Unknown Wizard action.")

    def get_form(self):
        time_form = fapi.ForisForm("time", self.data, filter=filters.time)
        time_main = time_form.add_section(name="set_time", title=_(self.userfriendly_title),
                                          description=_(
            "We could not synchronize the time with our timeserver, probably due to a loss of connection. "
            "It is necessary for the router to have the exact time in order to function properly. Please, "
            "synchronize it with your computer's time, or set it manually."
            ))

        time_main.add_field(Textbox, name="time", label=_("Time"), nuci_path="time",
                            nuci_preproc=lambda v: v.local)

        def time_form_cb(data):
            client.set_time(data['time'])
            return "none", None

        time_form.add_callback(time_form_cb)

        return time_form


class LanHandler(BaseConfigHandler):
    # {{ _("LAN") }} - for translation
    userfriendly_title = "LAN"
    
    def get_form(self):
        lan_form = fapi.ForisForm("lan", self.data, filter=filters.uci)
        lan_main = lan_form.add_section(name="set_lan", title=_(self.userfriendly_title),
                                        description=_("This section specifies the settings of the local network. "
            "Under normal conditions you can keep this settings as they are. Moreover, changing the router IP "
            "address has one caveat. If you do it the computers in local network will not obtain new addresses "
            "automatically; you will have to do it manually for each connected device. And as you submit "
            "your changes, the next page will not load until you obtain a new IP from DHCP (if DHCP enabled)."))

        lan_main.add_field(Textbox, name="dhcp_subnet", label=_("Router IP address"),
                           nuci_path="uci.network.lan.ipaddr",
                           hint=_("Router's IP address in inner network. Also defines the range of "
                                  "assigned IP addresses."))
        lan_main.add_field(Checkbox, name="dhcp_enabled", label=_("Enable DHCP"),
                           nuci_path="uci.dhcp.lan.ignore",
                           nuci_preproc=lambda val: not bool(int(val.value)), default=True,
                           hint=_("Enable this option to automatically assign IP addresses to "
                                  "the devices connected to the router."))
        lan_main.add_field(Textbox, name="dhcp_min", label=_("DHCP start"),
                           nuci_path="uci.dhcp.lan.start")\
            .requires("dhcp_enabled", True)
        lan_main.add_field(Textbox, name="dhcp_max", label=_("DHCP max leases"),
                           nuci_path="uci.dhcp.lan.limit")\
            .requires("dhcp_enabled", True)

        def lan_form_cb(data):
            uci = Uci()
            config = Config("dhcp")
            uci.add(config)

            dhcp = Section("lan", "dhcp")
            config.add(dhcp)
            # FIXME: this would overwrite any unrelated DHCP options the user might have set.
            # Maybe we should get the current values, scan them and remove selectively the ones
            # with 6 in front of them? Or have some support for higher level of stuff in nuci.
            options = List("dhcp_option")
            options.add(Value(0, "6," + data['dhcp_subnet']))
            dhcp.add_replace(options)
            network = Config("network")
            uci.add(network)
            interface = Section("lan", "interface")
            network.add(interface)
            interface.add(Option("ipaddr", data['dhcp_subnet']))
            if data['dhcp_enabled']:
                dhcp.add(Option("ignore", "0"))
                dhcp.add(Option("start", data['dhcp_min']))
                dhcp.add(Option("limit", data['dhcp_max']))
            else:
                dhcp.add(Option("ignore", "1"))

            return "edit_config", uci

        lan_form.add_callback(lan_form_cb)

        return lan_form


class WifiHandler(BaseConfigHandler):
    # {{ _("Wi-Fi") }} - for translation
    userfriendly_title = "Wi-Fi"
    
    def get_form(self):
        wifi_form = fapi.ForisForm("wifi", self.data, filter=filters.uci)
        wifi_main = wifi_form.add_section(name="set_wifi", title=_(self.userfriendly_title),
                                          description=_(
            "If you want to make from your router a Wi-Fi access point, enable the WiFi here and "
            "fill in an SSID (the name of the wifi access point) and the corresponding password. "
            "To set up a mobile device, you can scan the QR code shown next to the form."))
        wifi_main.add_field(Hidden, name="iface_section", nuci_path="uci.wireless.@wifi-iface[0]",
                            nuci_preproc=lambda val: val.name)
        wifi_main.add_field(Checkbox, name="wifi_enabled", label=_("Enable Wi-Fi"), default=True,
                            nuci_path="uci.wireless.@wifi-iface[0].disabled",
                            nuci_preproc=lambda val: not bool(int(val.value)))
        wifi_main.add_field(Textbox, name="ssid", label=_("SSID"),
                            nuci_path="uci.wireless.@wifi-iface[0].ssid",
                            required=True, validators=validators.LenRange(1, 32))\
            .requires("wifi_enabled", True)
        wifi_main.add_field(Checkbox, name="ssid_hidden", label=_("Hide SSID"), default=False,
                            nuci_path="uci.wireless.@wifi-iface[0].hidden",
                            hint=_("If set, network is not visible when scanning for available networks."))\
            .requires("wifi_enabled", True)

        def wifi_mode_preproc(channel):
            try:
                if int(channel.value) > 13:
                    return "5g"
            except ValueError:
                pass
            # channel <= 12 and fallback for "auto" channel
            return "2g4"

        wifi_main.add_field(Radio, name="wifi_mode", label=_("Wi-Fi mode"), default="2g4",
                            args=(("2g4", "2.4 GHz (g+n)"), ("5g", "5 GHz (a+n)")),
                            nuci_path="uci.wireless.radio0.channel", nuci_preproc=wifi_mode_preproc)\
            .requires("wifi_enabled", True)
        # 2.4G channels
        wifi_main.add_field(Dropdown, name="channel2g4", label=_("Network channel"), default="1",
                            args=(("auto", _("auto")),) + tuple((str(i), str(i)) for i in range(1, 12)),
                            nuci_path="uci.wireless.radio0.channel")\
            .requires("wifi_mode", "2g4")
        # 5G channels
        wifi_main.add_field(Dropdown, name="channel5g", label=_("Network channel"), default="36",
                            args=((str(i), str(i)) for i in range(36, 50, 4)),
                            nuci_path="uci.wireless.radio0.channel")\
            .requires("wifi_mode", "5g")
        wifi_main.add_field(Password, name="key", label=_("Network password"),
                            nuci_path="uci.wireless.@wifi-iface[0].key",
                            required=True,
                            hint=_("WPA2 preshared key, that is required to connect to the network."))\
            .requires("wifi_enabled", True)

        def wifi_form_cb(data):
            uci = Uci()
            wireless = Config("wireless")
            uci.add(wireless)

            iface = Section(data['iface_section'], "wifi-iface")
            wireless.add(iface)
            device = Section("radio0", "wifi-device")
            wireless.add(device)
            # we must toggle both wifi-iface and device
            iface.add(Option("disabled", not data['wifi_enabled']))
            device.add(Option("disabled", not data['wifi_enabled']))
            if data['wifi_enabled']:
                iface.add(Option("ssid", data['ssid']))
                iface.add(Option("hidden", data['ssid_hidden']))
                iface.add(Option("encryption", "psk2+tkip+aes"))
                iface.add(Option("key", data['key']))
                if data['wifi_mode'] == "2g4":
                    channel = data['channel2g4']
                    hwmode = "11ng"
                else:
                    channel = data['channel5g']
                    hwmode = "11ag"
                # channel is in wifi-device section
                device.add(Option("hwmode", hwmode))
                device.add(Option("channel", channel))
            else:
                pass  # wifi disabled

            return "edit_config", uci

        wifi_form.add_callback(wifi_form_cb)

        return wifi_form


class SystemPasswordHandler(BaseConfigHandler):
    """
    Setting the password of a system user (currently only root's pw).
    """
    
    # {{ _("Advanced administration") }} - for translation
    userfriendly_title = "Advanced administration"
    
    def get_form(self):
        system_pw_form = fapi.ForisForm("system_password", self.data)
        system_pw_main = system_pw_form.add_section(name="set_password",
                                                    title=_(self.userfriendly_title),
                                                    description=_(
            "In order to access the advanced configuration possibilities which are not present "
            "here, you must set the root user's password. The advanced configuration options can "
            "be managed either through the <a href=\"http://%(ip)s:%(port)d/\">LuCI web interface"
            "</a> or over SSH.") % {'ip': bottle.request.get_header('host'), 'port': 8080})
        system_pw_main.add_field(Password, name="password", label=_("Password"), required=True,
                                 validators=LenRange(6, 60))
        system_pw_main.add_field(Password, name="password_validation", label=_("Password (repeat)"))
        system_pw_form.add_validator(validators.FieldsEqual("password", "password_validation",
                                                            _("Passwords are not equal.")))

        def system_pw_form_cb(data):
            client.set_password("root", data["password"])
            return "none", None

        system_pw_form.add_callback(system_pw_form_cb)
        return system_pw_form
