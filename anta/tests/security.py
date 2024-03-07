# Copyright (c) 2023-2024 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Test functions related to the EOS various security settings
"""
from __future__ import annotations

# Mypy does not understand AntaTest.Input typing
# mypy: disable-error-code=attr-defined
from datetime import datetime
from ipaddress import IPv4Address
from typing import List, Optional, Union

from pydantic import BaseModel, Field, conint, model_validator

from anta.custom_types import EcdsaKeySize, EncryptionAlgorithm, RsaKeySize
from anta.models import AntaCommand, AntaTemplate, AntaTest
from anta.tools.get_item import get_item
from anta.tools.get_value import get_value
from anta.tools.utils import get_failed_logs


class VerifySSHStatus(AntaTest):
    """
    Verifies if the SSHD agent is disabled in the default VRF.

    Expected Results:
        * success: The test will pass if the SSHD agent is disabled in the default VRF.
        * failure: The test will fail if the SSHD agent is NOT disabled in the default VRF.
    """

    name = "VerifySSHStatus"
    description = "Verifies if the SSHD agent is disabled in the default VRF."
    categories = ["security"]
    commands = [AntaCommand(command="show management ssh", ofmt="text")]

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].text_output

        line = [line for line in command_output.split("\n") if line.startswith("SSHD status")][0]
        status = line.split("is ")[1]

        if status == "disabled":
            self.result.is_success()
        else:
            self.result.is_failure(line)


class VerifySSHIPv4Acl(AntaTest):
    """
    Verifies if the SSHD agent has the right number IPv4 ACL(s) configured for a specified VRF.

    Expected results:
        * success: The test will pass if the SSHD agent has the provided number of IPv4 ACL(s) in the specified VRF.
        * failure: The test will fail if the SSHD agent has not the right number of IPv4 ACL(s) in the specified VRF.
    """

    name = "VerifySSHIPv4Acl"
    description = "Verifies if the SSHD agent has IPv4 ACL(s) configured."
    categories = ["security"]
    commands = [AntaCommand(command="show management ssh ip access-list summary")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        number: conint(ge=0)  # type:ignore
        """The number of expected IPv4 ACL(s)"""
        vrf: str = "default"
        """The name of the VRF in which to check for the SSHD agent"""

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        ipv4_acl_list = command_output["ipAclList"]["aclList"]
        ipv4_acl_number = len(ipv4_acl_list)
        not_configured_acl_list = []
        if ipv4_acl_number != self.inputs.number:
            self.result.is_failure(f"Expected {self.inputs.number} SSH IPv4 ACL(s) in vrf {self.inputs.vrf} but got {ipv4_acl_number}")
            return
        for ipv4_acl in ipv4_acl_list:
            if self.inputs.vrf not in ipv4_acl["configuredVrfs"] or self.inputs.vrf not in ipv4_acl["activeVrfs"]:
                not_configured_acl_list.append(ipv4_acl["name"])
        if not_configured_acl_list:
            self.result.is_failure(f"SSH IPv4 ACL(s) not configured or active in vrf {self.inputs.vrf}: {not_configured_acl_list}")
        else:
            self.result.is_success()


class VerifySSHIPv6Acl(AntaTest):
    """
    Verifies if the SSHD agent has the right number IPv6 ACL(s) configured for a specified VRF.

    Expected results:
        * success: The test will pass if the SSHD agent has the provided number of IPv6 ACL(s) in the specified VRF.
        * failure: The test will fail if the SSHD agent has not the right number of IPv6 ACL(s) in the specified VRF.
    """

    name = "VerifySSHIPv6Acl"
    description = "Verifies if the SSHD agent has IPv6 ACL(s) configured."
    categories = ["security"]
    commands = [AntaCommand(command="show management ssh ipv6 access-list summary")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        number: conint(ge=0)  # type:ignore
        """The number of expected IPv6 ACL(s)"""
        vrf: str = "default"
        """The name of the VRF in which to check for the SSHD agent"""

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        ipv6_acl_list = command_output["ipv6AclList"]["aclList"]
        ipv6_acl_number = len(ipv6_acl_list)
        not_configured_acl_list = []
        if ipv6_acl_number != self.inputs.number:
            self.result.is_failure(f"Expected {self.inputs.number} SSH IPv6 ACL(s) in vrf {self.inputs.vrf} but got {ipv6_acl_number}")
            return
        for ipv6_acl in ipv6_acl_list:
            if self.inputs.vrf not in ipv6_acl["configuredVrfs"] or self.inputs.vrf not in ipv6_acl["activeVrfs"]:
                not_configured_acl_list.append(ipv6_acl["name"])
        if not_configured_acl_list:
            self.result.is_failure(f"SSH IPv6 ACL(s) not configured or active in vrf {self.inputs.vrf}: {not_configured_acl_list}")
        else:
            self.result.is_success()


class VerifyTelnetStatus(AntaTest):
    """
    Verifies if Telnet is disabled in the default VRF.

    Expected Results:
        * success: The test will pass if Telnet is disabled in the default VRF.
        * failure: The test will fail if Telnet is NOT disabled in the default VRF.
    """

    name = "VerifyTelnetStatus"
    description = "Verifies if Telnet is disabled in the default VRF."
    categories = ["security"]
    commands = [AntaCommand(command="show management telnet")]

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        if command_output["serverState"] == "disabled":
            self.result.is_success()
        else:
            self.result.is_failure("Telnet status for Default VRF is enabled")


class VerifyAPIHttpStatus(AntaTest):
    """
    Verifies if eAPI HTTP server is disabled globally.

    Expected Results:
        * success: The test will pass if eAPI HTTP server is disabled globally.
        * failure: The test will fail if eAPI HTTP server is NOT disabled globally.
    """

    name = "VerifyAPIHttpStatus"
    description = "Verifies if eAPI HTTP server is disabled globally."
    categories = ["security"]
    commands = [AntaCommand(command="show management api http-commands")]

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        if command_output["enabled"] and not command_output["httpServer"]["running"]:
            self.result.is_success()
        else:
            self.result.is_failure("eAPI HTTP server is enabled globally")


class VerifyAPIHttpsSSL(AntaTest):
    """
    Verifies if eAPI HTTPS server SSL profile is configured and valid.

    Expected results:
        * success: The test will pass if the eAPI HTTPS server SSL profile is configured and valid.
        * failure: The test will fail if the eAPI HTTPS server SSL profile is NOT configured, misconfigured or invalid.
    """

    name = "VerifyAPIHttpsSSL"
    description = "Verifies if the eAPI has a valid SSL profile."
    categories = ["security"]
    commands = [AntaCommand(command="show management api http-commands")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        profile: str
        """SSL profile to verify"""

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        try:
            if command_output["sslProfile"]["name"] == self.inputs.profile and command_output["sslProfile"]["state"] == "valid":
                self.result.is_success()
            else:
                self.result.is_failure(f"eAPI HTTPS server SSL profile ({self.inputs.profile}) is misconfigured or invalid")

        except KeyError:
            self.result.is_failure(f"eAPI HTTPS server SSL profile ({self.inputs.profile}) is not configured")


class VerifyAPIIPv4Acl(AntaTest):
    """
    Verifies if eAPI has the right number IPv4 ACL(s) configured for a specified VRF.

    Expected results:
        * success: The test will pass if eAPI has the provided number of IPv4 ACL(s) in the specified VRF.
        * failure: The test will fail if eAPI has not the right number of IPv4 ACL(s) in the specified VRF.
    """

    name = "VerifyAPIIPv4Acl"
    description = "Verifies if eAPI has the right number IPv4 ACL(s) configured for a specified VRF."
    categories = ["security"]
    commands = [AntaCommand(command="show management api http-commands ip access-list summary")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        number: conint(ge=0)  # type:ignore
        """The number of expected IPv4 ACL(s)"""
        vrf: str = "default"
        """The name of the VRF in which to check for eAPI"""

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        ipv4_acl_list = command_output["ipAclList"]["aclList"]
        ipv4_acl_number = len(ipv4_acl_list)
        not_configured_acl_list = []
        if ipv4_acl_number != self.inputs.number:
            self.result.is_failure(f"Expected {self.inputs.number} eAPI IPv4 ACL(s) in vrf {self.inputs.vrf} but got {ipv4_acl_number}")
            return
        for ipv4_acl in ipv4_acl_list:
            if self.inputs.vrf not in ipv4_acl["configuredVrfs"] or self.inputs.vrf not in ipv4_acl["activeVrfs"]:
                not_configured_acl_list.append(ipv4_acl["name"])
        if not_configured_acl_list:
            self.result.is_failure(f"eAPI IPv4 ACL(s) not configured or active in vrf {self.inputs.vrf}: {not_configured_acl_list}")
        else:
            self.result.is_success()


class VerifyAPIIPv6Acl(AntaTest):
    """
    Verifies if eAPI has the right number IPv6 ACL(s) configured for a specified VRF.

    Expected results:
        * success: The test will pass if eAPI has the provided number of IPv6 ACL(s) in the specified VRF.
        * failure: The test will fail if eAPI has not the right number of IPv6 ACL(s) in the specified VRF.
        * skipped: The test will be skipped if the number of IPv6 ACL(s) or VRF parameter is not provided.
    """

    name = "VerifyAPIIPv6Acl"
    description = "Verifies if eAPI has the right number IPv6 ACL(s) configured for a specified VRF."
    categories = ["security"]
    commands = [AntaCommand(command="show management api http-commands ipv6 access-list summary")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        number: conint(ge=0)  # type:ignore
        """The number of expected IPv6 ACL(s)"""
        vrf: str = "default"
        """The name of the VRF in which to check for eAPI"""

    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        ipv6_acl_list = command_output["ipv6AclList"]["aclList"]
        ipv6_acl_number = len(ipv6_acl_list)
        not_configured_acl_list = []
        if ipv6_acl_number != self.inputs.number:
            self.result.is_failure(f"Expected {self.inputs.number} eAPI IPv6 ACL(s) in vrf {self.inputs.vrf} but got {ipv6_acl_number}")
            return
        for ipv6_acl in ipv6_acl_list:
            if self.inputs.vrf not in ipv6_acl["configuredVrfs"] or self.inputs.vrf not in ipv6_acl["activeVrfs"]:
                not_configured_acl_list.append(ipv6_acl["name"])
        if not_configured_acl_list:
            self.result.is_failure(f"eAPI IPv6 ACL(s) not configured or active in vrf {self.inputs.vrf}: {not_configured_acl_list}")
        else:
            self.result.is_success()


class VerifyAPISSLCertificate(AntaTest):
    """
    Verifies the eAPI SSL certificate expiry, common subject name, encryption algorithm and key size.

    Expected Results:
        * success: The test will pass if the certificate's expiry date is greater than the threshold,
                   and the certificate has the correct name, encryption algorithm, and key size.
        * failure: The test will fail if the certificate is expired or is going to expire,
                   or if the certificate has an incorrect name, encryption algorithm, or key size.
    """

    name = "VerifyAPISSLCertificate"
    description = "Verifies the eAPI SSL certificate expiry, common subject name, encryption algorithm and key size."
    categories = ["security"]
    commands = [AntaCommand(command="show management security ssl certificate"), AntaCommand(command="show clock")]

    class Input(AntaTest.Input):
        """
        Input parameters for the VerifyAPISSLCertificate test.
        """

        certificates: List[APISSLCertificates]
        """List of API SSL certificates"""

        class APISSLCertificates(BaseModel):
            """
            This class defines the details of an API SSL certificate.
            """

            certificate_name: str
            """The name of the certificate to be verified."""
            expiry_threshold: int
            """The expiry threshold of the certificate in days."""
            common_name: str
            """The common subject name of the certificate."""
            encryption_algorithm: EncryptionAlgorithm
            """The encryption algorithm of the certificate."""
            key_size: Union[RsaKeySize, EcdsaKeySize]
            """The encryption algorithm key size of the certificate."""

            @model_validator(mode="after")
            def validate_inputs(self: BaseModel) -> BaseModel:
                """
                Validate the key size provided to the APISSLCertificates class.

                If encryption_algorithm is RSA then key_size should be in {2048, 3072, 4096}.

                If encryption_algorithm is ECDSA then key_size should be in {256, 384, 521}.
                """

                if self.encryption_algorithm == "RSA" and self.key_size not in RsaKeySize.__args__:
                    raise ValueError(f"`{self.certificate_name}` key size {self.key_size} is invalid for RSA encryption. Allowed sizes are {RsaKeySize.__args__}.")

                if self.encryption_algorithm == "ECDSA" and self.key_size not in EcdsaKeySize.__args__:
                    raise ValueError(
                        f"`{self.certificate_name}` key size {self.key_size} is invalid for ECDSA encryption. Allowed sizes are {EcdsaKeySize.__args__}."
                    )

                return self

    @AntaTest.anta_test
    def test(self) -> None:
        # Mark the result as success by default
        self.result.is_success()

        # Extract certificate and clock output
        certificate_output = self.instance_commands[0].json_output
        clock_output = self.instance_commands[1].json_output
        current_timestamp = clock_output["utcTime"]

        # Iterate over each API SSL certificate
        for certificate in self.inputs.certificates:
            # Collecting certificate expiry time and current EOS time.
            # These times are used to calculate the number of days until the certificate expires.
            if not (certificate_data := get_value(certificate_output, f"certificates..{certificate.certificate_name}", separator="..")):
                self.result.is_failure(f"SSL certificate '{certificate.certificate_name}', is not configured.\n")
                continue

            expiry_time = certificate_data["notAfter"]
            day_difference = (datetime.fromtimestamp(expiry_time) - datetime.fromtimestamp(current_timestamp)).days

            # Verify certificate expiry
            if 0 < day_difference < certificate.expiry_threshold:
                self.result.is_failure(f"SSL certificate `{certificate.certificate_name}` is about to expire in {day_difference} days.\n")
            elif day_difference < 0:
                self.result.is_failure(f"SSL certificate `{certificate.certificate_name}` is expired.\n")

            # Verify certificate common subject name, encryption algorithm and key size
            keys_to_verify = ["subject.commonName", "publicKey.encryptionAlgorithm", "publicKey.size"]
            actual_certificate_details = {key: get_value(certificate_data, key) for key in keys_to_verify}

            expected_certificate_details = {
                "subject.commonName": certificate.common_name,
                "publicKey.encryptionAlgorithm": certificate.encryption_algorithm,
                "publicKey.size": certificate.key_size,
            }

            if actual_certificate_details != expected_certificate_details:
                failed_log = f"SSL certificate `{certificate.certificate_name}` is not configured properly:"
                failed_log += get_failed_logs(expected_certificate_details, actual_certificate_details)
                self.result.is_failure(f"{failed_log}\n")


class VerifyBannerLogin(AntaTest):
    """
    Verifies the login banner of a device.

    Expected results:
        * success: The test will pass if the login banner matches the provided input.
        * failure: The test will fail if the login banner does not match the provided input.
    """

    name = "VerifyBannerLogin"
    description = "Verifies the login banner of a device."
    categories = ["security"]
    commands = [AntaCommand(command="show banner login")]

    class Input(AntaTest.Input):
        """Defines the input parameters for this test case."""

        login_banner: str
        """Expected login banner of the device."""

    @AntaTest.anta_test
    def test(self) -> None:
        login_banner = self.instance_commands[0].json_output["loginBanner"]

        # Remove leading and trailing whitespaces from each line
        cleaned_banner = "\n".join(line.strip() for line in self.inputs.login_banner.split("\n"))
        if login_banner != cleaned_banner:
            self.result.is_failure(f"Expected `{cleaned_banner}` as the login banner, but found `{login_banner}` instead.")
        else:
            self.result.is_success()


class VerifyBannerMotd(AntaTest):
    """
    Verifies the motd banner of a device.

    Expected results:
        * success: The test will pass if the motd banner matches the provided input.
        * failure: The test will fail if the motd banner does not match the provided input.
    """

    name = "VerifyBannerMotd"
    description = "Verifies the motd banner of a device."
    categories = ["security"]
    commands = [AntaCommand(command="show banner motd")]

    class Input(AntaTest.Input):
        """Defines the input parameters for this test case."""

        motd_banner: str
        """Expected motd banner of the device."""

    @AntaTest.anta_test
    def test(self) -> None:
        motd_banner = self.instance_commands[0].json_output["motd"]

        # Remove leading and trailing whitespaces from each line
        cleaned_banner = "\n".join(line.strip() for line in self.inputs.motd_banner.split("\n"))
        if motd_banner != cleaned_banner:
            self.result.is_failure(f"Expected `{cleaned_banner}` as the motd banner, but found `{motd_banner}` instead.")
        else:
            self.result.is_success()


class VerifyIPv4ACL(AntaTest):
    """
    Verifies the configuration of IPv4 ACLs.

    Expected results:
        * success: The test will pass if an IPv4 ACL is configured with the correct sequence entries.
        * failure: The test will fail if an IPv4 ACL is not configured or entries are not in sequence.
    """

    name = "VerifyIPv4ACL"
    description = "Verifies the configuration of IPv4 ACLs."
    categories = ["security"]
    commands = [AntaTemplate(template="show ip access-lists {acl}")]

    class Input(AntaTest.Input):
        """Inputs for the VerifyIPv4ACL test."""

        ipv4_access_lists: List[IPv4ACL]
        """List of IPv4 ACLs to verify"""

        class IPv4ACL(BaseModel):
            """Detail of IPv4 ACL"""

            name: str
            """Name of IPv4 ACL"""

            entries: List[IPv4ACLEntries]
            """List of IPv4 ACL entries"""

            class IPv4ACLEntries(BaseModel):
                """IPv4 ACL entries details"""

                sequence: int = Field(ge=1, le=4294967295)
                """Sequence number of an ACL entry"""
                action: str
                """Action of an ACL entry"""

    def render(self, template: AntaTemplate) -> list[AntaCommand]:
        return [template.render(acl=acl.name, entries=acl.entries) for acl in self.inputs.ipv4_access_lists]

    @AntaTest.anta_test
    def test(self) -> None:
        self.result.is_success()
        for command_output in self.instance_commands:
            # Collecting input ACL details
            acl_name = command_output.params["acl"]
            acl_entries = command_output.params["entries"]

            # Check if ACL is configured
            ipv4_acl_list = command_output.json_output["aclList"]
            if not ipv4_acl_list:
                self.result.is_failure(f"{acl_name}: Not found")
                continue

            # Check if the sequence number is configured and has the correct action applied
            failed_log = f"{acl_name}:\n"
            for acl_entry in acl_entries:
                acl_seq = acl_entry.sequence
                acl_action = acl_entry.action
                if (actual_entry := get_item(ipv4_acl_list[0]["sequence"], "sequenceNumber", acl_seq)) is None:
                    failed_log += f"Sequence number `{acl_seq}` is not found.\n"
                    continue

                if actual_entry["text"] != acl_action:
                    failed_log += f"Expected `{acl_action}` as sequence number {acl_seq} action but found `{actual_entry['text']}` instead.\n"

            if failed_log != f"{acl_name}:\n":
                self.result.is_failure(f"{failed_log}")


class VerifyIPSecConnHealth(AntaTest):
    """
    Verifies all IP security connections

    Expected results:
        * success: The test will pass if all the IP security connections are established in all vrf.
        * failure: The test will fail if IP security is not configured or any of ip security connections are not established in any vrf.
    """

    name = "VerifyIPSecConnHealth"
    description = "Verifies all IP security connections."
    categories = ["security"]
    commands = [AntaCommand(command="show ip security connection vrf all")]

    @AntaTest.anta_test
    def test(self) -> None:
        self.result.is_success()
        failure_conn = []
        command_output = self.instance_commands[0].json_output["connections"]

        # Check if IP security connection is configured
        if not command_output:
            self.result.is_failure("IP security connection are not configured.")
            return

        # Iterate over all ip sec connection
        for connection, conn_data in command_output.items():
            state = list(conn_data["pathDict"].values())[0]
            if state != "Established":
                failure_conn.append(connection)
        if failure_conn:
            failure_msg = "\n".join(failure_conn)
            self.result.is_failure(f"Following IP security connections are not establised:\n{failure_msg}.")


class VerifySpecificIPSecConn(AntaTest):
    """
    Verifies IP security connections for a peer.

    Expected results:
        * success: The test passes if the IP security connection for a peer is established in the specified VRF.
        * failure: The test fails if IP security is not configured, a connection is not found for a peer, or the connection is not established in the specified VRF.
    """

    name = "VerifySpecificIPSecConn"
    description = "Verifies IP security connections for a peer."
    categories = ["security"]
    commands = [AntaTemplate(template="show ip security connection vrf {vrf} path peer {peer}")]

    class Input(AntaTest.Input):
        """
        This class defines the inputs for the VerifySpecificIPSecConn test.
        """

        ip_sec_conn: List[IPSecPeer]
        """List of IP security peers."""

        class IPSecPeer(BaseModel):
            """
            Details of IP security peers.
            """

            peer: IPv4Address
            """IPv4 address of the peer."""

            vrf: str = "default"
            """This is the optional VRF for the IP security peer. It defaults to `default` if not provided."""

            connection: Optional[List[IPSecConn]] = None
            """List of IP security connections of a peer."""

            class IPSecConn(BaseModel):
                """
                Details of IP security connections for a peer.
                """

                source_address: IPv4Address
                """Source address of the connection."""
                destination_address: IPv4Address
                """Destination address of the connection."""

    def render(self, template: AntaTemplate) -> list[AntaCommand]:
        """
        This method renders the template with the provided inputs.
        """
        return [template.render(peer=conn.peer, vrf=conn.vrf, connections=conn.connection) for conn in self.inputs.ip_sec_conn]

    @AntaTest.anta_test
    def test(self) -> None:
        self.result.is_success()
        for command_output in self.instance_commands:
            conn_output = command_output.json_output["connections"]
            peer = command_output.params["peer"]
            connections = command_output.params["connections"]

            # Check if IP security connection is configured
            if not conn_output:
                self.result.is_failure(f"IP security connections are not configured for peer `{peer}`.")
                return

            # If connection details are not provided then check all connection of a peer
            if connections is None:
                for connection, conn_data in conn_output.items():
                    state = list(conn_data["pathDict"].values())[0]
                    if state != "Established":
                        self.result.is_failure(
                            f"Expected state of IP security connection `{connection}` for peer `{peer}` is `Established` " f"but found `{state}` instead."
                        )
                continue

            # Create a dictionary of existing connections for faster lookup
            existing_connections = {(conn_data.get("saddr"), conn_data.get("daddr")): list(conn_data["pathDict"].values())[0] for conn_data in conn_output.values()}
            for connection in connections:
                source = str(connection.source_address)
                destination = str(connection.destination_address)

                if (source, destination) in existing_connections:
                    existing_state = existing_connections[(source, destination)]
                    if existing_state != "Established":
                        self.result.is_failure(
                            f"Expected state of IP security connection `{source}-{destination}` for peer `{peer}` is `Established` "
                            f"but found `{existing_state}` instead."
                        )
                else:
                    self.result.is_failure(f"IP security connection `{source}-{destination}` for peer `{peer}` is not found.")
