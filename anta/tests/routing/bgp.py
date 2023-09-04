# Copyright (c) 2023 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
BGP test functions
"""
# Mypy does not understand AntaTest.Input typing
# mypy: disable-error-code=attr-defined
from __future__ import annotations

from typing import Any, Dict

from anta.decorators import check_bgp_family_enable
from anta.models import AntaCommand, AntaTemplate, AntaTest


def _check_bgp_vrfs(bgp_vrfs: dict[str, Any]) -> dict[str, Any]:
    """Parse the output of 'show bgp [ADDR FAMILY] summary vrf [VRF]'
    and returns a dictionary with the following structure:
    {
        "VRF_NAME": {
            "PEER":
                {
                    "peerState": BGP_STATE,
                    "inMsgQueue": MSG_COUNT,
                    "outMsgQueue": MSG_COUNT,
                }
        }
    }

    Args:
        bgp_vrfs: output of 'show bgp [ADDR FAMILY] summary vrf [VRF]'
    """
    state_issue: dict[str, Any] = {}
    for vrf in bgp_vrfs:
        for peer in bgp_vrfs[vrf]["peers"]:
            if (
                (bgp_vrfs[vrf]["peers"][peer]["peerState"] != "Established")
                or (bgp_vrfs[vrf]["peers"][peer]["inMsgQueue"] != 0)
                or (bgp_vrfs[vrf]["peers"][peer]["outMsgQueue"] != 0)
            ):
                vrf_dict = state_issue.setdefault(vrf, {})
                vrf_dict.update(
                    {
                        peer: {
                            "peerState": bgp_vrfs[vrf]["peers"][peer]["peerState"],
                            "inMsgQueue": bgp_vrfs[vrf]["peers"][peer]["inMsgQueue"],
                            "outMsgQueue": bgp_vrfs[vrf]["peers"][peer]["outMsgQueue"],
                        }
                    }
                )

    return state_issue


class VerifyBGPIPv4UnicastState(AntaTest):
    """
    Verifies all IPv4 unicast BGP sessions are established (for all VRF)
    and all BGP messages queues for these sessions are empty (for all VRF).

    * self.result = "skipped" if no BGP vrf are returned by the device
    * self.result = "success" if all IPv4 unicast BGP sessions are established (for all VRF)
                         and all BGP messages queues for these sessions are empty (for all VRF).
    * self.result = "failure" otherwise.
    """

    name = "VerifyBGPIPv4UnicastState"
    description = "Verifies all IPv4 unicast BGP sessions are established (for all VRF) and all BGP messages queues for these sessions are empty (for all VRF)."
    categories = ["routing", "bgp"]
    commands = [AntaCommand(command="show bgp ipv4 unicast summary vrf all")]

    @check_bgp_family_enable("ipv4")
    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        state_issue = _check_bgp_vrfs(command_output["vrfs"])
        if not state_issue:
            self.result.is_success()
        else:
            self.result.is_failure(f"Some IPv4 Unicast BGP Peer are not up: {state_issue}")


class VerifyBGPIPv4UnicastCount(AntaTest):
    """
    Verifies all IPv4 unicast BGP sessions are established
    and all BGP messages queues for these sessions are empty
    and the actual number of BGP IPv4 unicast neighbors is the one we expect
    in all VRFs specified as input.

    * self.result = "success" if all IPv4 unicast BGP sessions are established
                         and if all BGP messages queues for these sessions are empty
                         and if the actual number of BGP IPv4 unicast neighbors is equal to `number
                         in all VRFs specified as input.
    * self.result = "failure" otherwise.
    """

    name = "VerifyBGPIPv4UnicastCount"
    description = (
        "Verifies all IPv4 unicast BGP sessions are established and all their BGP messages queues are empty and "
        " the actual number of BGP IPv4 unicast neighbors is the one we expect."
    )
    categories = ["routing", "bgp"]
    commands = [AntaTemplate(template="show bgp ipv4 unicast summary vrf {vrf}")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        vrfs: Dict[str, int]
        """VRFs associated with neighbors count to verify"""

    def render(self, template: AntaTemplate) -> list[AntaCommand]:
        return [template.render(vrf=vrf) for vrf in self.inputs.vrfs]

    @check_bgp_family_enable("ipv4")
    @AntaTest.anta_test
    def test(self) -> None:
        self.result.is_success()
        for command in self.instance_commands:
            if command.params and "vrf" in command.params:
                vrf = command.params["vrf"]
                count = self.inputs.vrfs[vrf]
                if vrf not in command.json_output["vrfs"]:
                    self.result.is_failure(f"VRF {vrf} is not configured")
                    return
                peers = command.json_output["vrfs"][vrf]["peers"]
                state_issue = _check_bgp_vrfs(command.json_output["vrfs"])
                if len(peers) != count:
                    self.result.is_failure(f"Expecting {count} BGP peer(s) in vrf {vrf} but got {len(peers)} peer(s)")
                if state_issue:
                    self.result.is_failure(f"The following IPv4 peer(s) are not established: {state_issue}")


class VerifyBGPIPv6UnicastState(AntaTest):
    """
    Verifies all IPv6 unicast BGP sessions are established (for all VRF)
    and all BGP messages queues for these sessions are empty (for all VRF).

    * self.result = "skipped" if no BGP vrf are returned by the device
    * self.result = "success" if all IPv6 unicast BGP sessions are established (for all VRF)
                         and all BGP messages queues for these sessions are empty (for all VRF).
    * self.result = "failure" otherwise.
    """

    name = "VerifyBGPIPv6UnicastState"
    description = "Verifies all IPv6 unicast BGP sessions are established (for all VRF) and all BGP messages queues for these sessions are empty (for all VRF)."
    categories = ["routing", "bgp"]
    commands = [AntaCommand(command="show bgp ipv6 unicast summary vrf all")]

    @check_bgp_family_enable("ipv6")
    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        state_issue = _check_bgp_vrfs(command_output["vrfs"])
        if not state_issue:
            self.result.is_success()
        else:
            self.result.is_failure(f"Some IPv4 Unicast BGP Peer are not up: {state_issue}")


class VerifyBGPEVPNState(AntaTest):
    """
    Verifies all EVPN BGP sessions are established (default VRF).

    * self.result = "skipped" if no BGP EVPN peers are returned by the device
    * self.result = "success" if all EVPN BGP sessions are established.
    * self.result = "failure" otherwise.
    """

    name = "VerifyBGPEVPNState"
    description = "Verifies all EVPN BGP sessions are established (default VRF)."
    categories = ["routing", "bgp"]
    commands = [AntaCommand(command="show bgp evpn summary")]

    @check_bgp_family_enable("evpn")
    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        bgp_vrfs = command_output["vrfs"]
        peers = bgp_vrfs["default"]["peers"]
        non_established_peers = [peer for peer, peer_dict in peers.items() if peer_dict["peerState"] != "Established"]
        if not non_established_peers:
            self.result.is_success()
        else:
            self.result.is_failure(f"The following EVPN peers are not established: {non_established_peers}")


class VerifyBGPEVPNCount(AntaTest):
    """
    Verifies all EVPN BGP sessions are established (default VRF)
    and the actual number of BGP EVPN neighbors is the one we expect (default VRF).

    * self.result = "success" if all EVPN BGP sessions are Established and if the actual
                         number of BGP EVPN neighbors is the one we expect.
    * self.result = "failure" otherwise.
    """

    name = "VerifyBGPEVPNCount"
    description = "Verifies all EVPN BGP sessions are established (default VRF) and the actual number of BGP EVPN neighbors is the one we expect (default VRF)."
    categories = ["routing", "bgp"]
    commands = [AntaCommand(command="show bgp evpn summary")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        number: int
        """The expected number of BGP EVPN neighbors in the default VRF"""

    @check_bgp_family_enable("evpn")
    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        peers = command_output["vrfs"]["default"]["peers"]
        non_established_peers = [peer for peer, peer_dict in peers.items() if peer_dict["peerState"] != "Established"]
        if not non_established_peers and len(peers) == self.inputs.number:
            self.result.is_success()
        else:
            self.result.is_failure()
            if len(peers) != self.inputs.number:
                self.result.is_failure(f"Expecting {self.inputs.number} BGP EVPN peers and got {len(peers)}")
            if non_established_peers:
                self.result.is_failure(f"The following EVPN peers are not established: {non_established_peers}")


class VerifyBGPRTCState(AntaTest):
    """
    Verifies all RTC BGP sessions are established (default VRF).

    * self.result = "skipped" if no BGP RTC peers are returned by the device
    * self.result = "success" if all RTC BGP sessions are established.
    * self.result = "failure" otherwise.
    """

    name = "VerifyBGPRTCState"
    description = "Verifies all RTC BGP sessions are established (default VRF)."
    categories = ["routing", "bgp"]
    commands = [AntaCommand(command="show bgp rt-membership summary")]

    @check_bgp_family_enable("rtc")
    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        bgp_vrfs = command_output["vrfs"]
        peers = bgp_vrfs["default"]["peers"]
        non_established_peers = [peer for peer, peer_dict in peers.items() if peer_dict["peerState"] != "Established"]
        if not non_established_peers:
            self.result.is_success()
        else:
            self.result.is_failure(f"The following RTC peers are not established: {non_established_peers}")


class VerifyBGPRTCCount(AntaTest):
    """
    Verifies all RTC BGP sessions are established (default VRF)
    and the actual number of BGP RTC neighbors is the one we expect (default VRF).

    * self.result = "success" if all RTC BGP sessions are Established and if the actual
                         number of BGP RTC neighbors is the one we expect.
    * self.result = "failure" otherwise.
    """

    name = "VerifyBGPRTCCount"
    description = "Verifies all RTC BGP sessions are established (default VRF) and the actual number of BGP RTC neighbors is the one we expect (default VRF)."
    categories = ["routing", "bgp"]
    commands = [AntaCommand(command="show bgp rt-membership summary")]

    class Input(AntaTest.Input):  # pylint: disable=missing-class-docstring
        number: int
        """The expected number of BGP RTC neighbors in the default VRF"""

    @check_bgp_family_enable("rtc")
    @AntaTest.anta_test
    def test(self) -> None:
        command_output = self.instance_commands[0].json_output
        peers = command_output["vrfs"]["default"]["peers"]
        non_established_peers = [peer for peer, peer_dict in peers.items() if peer_dict["peerState"] != "Established"]
        if not non_established_peers and len(peers) == self.inputs.number:
            self.result.is_success()
        else:
            self.result.is_failure()
            if len(peers) != self.inputs.number:
                self.result.is_failure(f"Expecting {self.inputs.number} BGP RTC peers and got {len(peers)}")
            if non_established_peers:
                self.result.is_failure(f"The following RTC peers are not established: {non_established_peers}")
