# -*- coding: utf-8 -*-
"""PUBLIC-ADDRESS GUARD shared by every collector that fetches URLs it did not choose (press text, sign-on letters).

Moved out of fetch_press_text.py (which runs at import and so could not be imported) so there is ONE copy: a weakening here
weakens both, and the press fetcher's HOSTILE-target tests (tests/collect/test_fetch_press_text_public_only.py) pin it.
require_public(url) raises ValueError for anything that is not http(s) to a global unicast address, after resolving the name;
PublicOnlyRedirects re-checks every redirect hop."""
import ipaddress, socket, urllib.parse, urllib.request
from collect.campaign_sites_2026 import private_target_reason


_LOCAL_NAT64 = ipaddress.ip_network('64:ff9b:1::/48')   # RFC 8215 local-use prefix: never a public host


def embedded_ipv4(address):
    """The IPv4 address inside a NAT64 (64:ff9b::/96) or 6to4 (2002::/16) IPv6 address, else None."""
    raw = address.packed
    if raw[:12] == bytes.fromhex('0064ff9b') + bytes(8):
        return ipaddress.IPv4Address(raw[12:])
    if raw[:2] == b'\x20\x02':
        return ipaddress.IPv4Address(raw[2:6])


def is_public(address):
    """Global unicast only. is_global alone passes multicast, site-local fec0::/10 and IPv4-compatible ::a.b.c.d, so
    those are refused here as well. A NAT64 or 6to4 address is only as public as the IPv4 inside it (the wrapper's own
    range reads reserved or private, so it is ignored). Teredo 2001::/32 is refused as a whole range."""
    inner = embedded_ipv4(address) if address.version == 6 else None
    if inner is not None:
        return is_public(inner)
    return address.is_global and address not in _LOCAL_NAT64 and not (
        address.is_multicast or address.is_reserved or address.is_unspecified or address.is_loopback
        or address.is_link_local or address.is_private or getattr(address, 'is_site_local', False))


def require_public(url):
    """The URLs come from a CSV, so refuse any that is not http(s) to a public address.

    Literal private hosts are refused by the campaign-site guard; the DNS answer is checked too, because a
    public-looking name can resolve inward. ponytail: urlopen resolves again after this, so a DNS server that
    answers differently the second time still gets through; pin the checked address if that ever matters."""
    reason = private_target_reason(url)
    if reason:
        raise ValueError(reason)
    parsed = urllib.parse.urlparse(url)
    try:
        answers = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme.lower() == 'https' else 80),
                                     type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError('target host does not resolve: %s' % e)
    for answer in answers:
        address = ipaddress.ip_address(answer[4][0].split('%')[0])
        address = getattr(address, 'ipv4_mapped', None) or address
        if not is_public(address):
            raise ValueError('target host resolves to non-public address %s' % address)


class PublicOnlyRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_public(newurl)   # a public page can still redirect inward
        return super().redirect_request(req, fp, code, msg, headers, newurl)
