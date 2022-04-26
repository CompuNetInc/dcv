"""dcv.dns_updater"""
import json
import logging
import sys
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("utils")


class DNSUpdater:
    """Neustar/UltraDNS Object"""

    def __init__(self, username: str, password: str) -> None:
        """
        Instance of DNS Updater (Neustar/UltraDNS API)

        Args:
            username: Neustar/UltraDNS Username
            password: Neustar/UltraDNS Password

        Returns:
            None/Class Instance

        Raises:
            N/A
        """

        self.username = username
        self.password = password
        self.session: Dict[str, Any] = {}
        self.key = ""

    async def login(self) -> None:
        """
        Login to API & get token

        Args:
            N/A

        Returns:
            None

        Raises:
            N/A
        """
        sess = httpx.AsyncClient()

        url = "https://api.ultradns.com/authorization/token"
        payload = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = await sess.post(url=url, headers=headers, data=payload)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {headers=}, {payload=}")
            print("Request error: ", e)
            sys.exit()
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {headers=}, {payload=}")
            print("HTTP Status error: ", e)
            sys.exit()

        self.key = response.json().get("access_token")
        if not self.key:
            print(
                "Unknown Error logging into Neustar/UltraDNS, could not get access_token."
            )
            sys.exit(1)

        self.session[self.key] = sess

    async def get_zones(self, zone_name: Optional[str]) -> List[Dict[str, Any]]:
        """
        Get zone or zones

        Args:
            zone_name: fqdn of domain

        Returns:
            List of all (or single) zone

        Raises:
            N/A
        """

        url = (
            "https://api.ultradns.com/zones"
            if not zone_name
            else f"https://api.ultradns.com/zones/{zone_name}"
        )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {self.key}",
        }
        try:
            response = await self.session[self.key].get(url=url, headers=headers)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {headers=}")
            print("Request error: ", e)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {headers=}")
            print("HTTP Status error: ", e)
            sys.exit(1)

        if zone_name:
            return response.json()

        return response.json().get("zones")

    async def create_cname_record(
        self, domain_name: str, cname: str, rdata: str
    ) -> str:
        """
        Create CNAME Record

        Args:
            domain_name: fqdn of domain
            cname: cname to create
            rdata: cname value (normally dcv.digicert.com)

        Returns:
            Successful or failure message

        Raises:
            N/A
        """

        url = f"https://api.ultradns.com/zones/{domain_name}./rrsets/cname/{cname}"
        rdata += "."
        payload = json.dumps({"rdata": [rdata]})
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }
        err_message = f"Creating CNAME record {cname}.{domain_name} Failed, moving to next domain."

        try:
            response = await self.session[self.key].post(
                url=url, headers=headers, data=payload
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {headers=}, {payload=}")
            print("Request error: ", e)
            logger.exception(err_message)
            return err_message
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {headers=}, {payload=}")
            print("HTTP Status error: ", e)
            logger.exception(err_message)
            return err_message

        if response.json().get("message") != "Successful":
            return err_message

        return "Successful"

    async def delete_cname_record(self, domain_name: str, cname: str) -> str:
        """
        Delete CNAME Record

        Args:
            domain_name: fqdn of domain
            cname: cname to create

        Returns:
            Successful or failure message

        Raises:
            N/A
        """

        url = f"https://api.ultradns.com/zones/{domain_name}./rrsets/cname/{cname}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {self.key}",
        }
        err_message = f"Failed to delete cname {cname}.{domain_name}."

        try:
            response = await self.session[self.key].delete(url=url, headers=headers)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {headers=}")
            print("Request error: ", e)
            logger.exception(err_message)
            return err_message
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {headers=}")
            print("HTTP Status error: ", e)
            logger.exception(err_message)
            return err_message

        if response.status_code != 204:
            return err_message

        return "Successful"
