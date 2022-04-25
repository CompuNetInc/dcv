"""dcv.domain_validator"""
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx


class DomainValidator:
    """Digicert Domain Validations"""

    def __init__(self, key: str) -> None:
        """
        Instance of DomainValidator (DigiCert API)

        Args:
            key: DigiCert API Key

        Returns:
            None/Class Instance

        Raises:
            N/A
        """
        self.key = key
        self.headers = {"X-DC-DEVKEY": self.key, "Content-Type": "application/json"}
        self.session = {}
        sess = httpx.AsyncClient()
        self.session[self.key] = sess

    async def get_domains(
        self, limit: Optional[int] = None, domain_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all domains and return list of domains expiring within num_days

        Args:
            limit: optional max records to return
            domain_name: optional fqdn, only return this domain

        Returns:
            List of DigiCert domains in json

        Raises:
            N/A
        """

        url = (
            "https://www.digicert.com/services/v2/domain"
            if not domain_name and not limit
            else f"https://www.digicert.com/services/v2/domain?filters[search]={domain_name}"
            if not limit
            else f"https://www.digicert.com/services/v2/domain?limit={str(limit)}"
        )

        try:
            response = await self.session[self.key].get(url=url, headers=self.headers)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            sys.exit(1)

        domains = response.json().get("domains")

        return domains

    async def get_expiring_domains(
        self,
        domains: Optional[List[Dict[str, Any]]] = None,
        num_days: Optional[int] = 90,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all domains and return list of domains expiring within num_days

        Args:
            domains: list of domains retrieved from the api elsewhere
            num_days: default 90, number of days in the future deemed 'soon'

        Returns:
            List[Dict] (digicert domains in json)

        Raises:
            N/A
        """

        domains = await self.get_domains() if not domains else domains

        exp_date = datetime.now() + timedelta(
            float(num_days)
        )  # expires 180 days from now
        exp_domains = []

        for domain in domains:
            dcv_expiration = domain.get(
                "dcv_expiration"
            )  # Some domains don't have this

            if dcv_expiration:
                ev_exp_str = dcv_expiration["ev"]
                ov_exp_str = dcv_expiration["ov"]
            elif "not found!" in domain["name"]:
                # print(f"Error: domain {domain['name']} Check spelling.")
                continue
            else:
                print(
                    f"Info: domain has never been validated, will be ignored: {domain['name']}."
                )
                continue

            ev_exp = datetime.strptime(ev_exp_str, "%Y-%m-%d")
            ov_exp = datetime.strptime(ov_exp_str, "%Y-%m-%d")
            min_exp = ev_exp if ev_exp < ov_exp else ov_exp  # Get lowest date

            if min_exp < exp_date:
                exp_domains.append(domain)

        return exp_domains

    async def get_domain_status(self, domain: Dict[str, Any]) -> Tuple[str, str]:
        """
        Separate case for 'dcv check -d domain.com'

        Args:
            domain: domain api object

        Returns:
            dcv_status and expiration date (ov only)

        Raises:
            N/A
        """
        url = f"https://www.digicert.com/services/v2/domain/{domain['id']}?include_dcv=true"

        try:
            response = await self.session[self.key].get(url=url, headers=self.headers)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            sys.exit(1)

        dcv_expiration = response.json().get(
            "dcv_expiration"
        )  # Some domains don't have this

        if not dcv_expiration:
            return (
                "Failed",
                f"Info/Ignored domain: no expiration date on: {domain['name']}",
            )

        ov_exp = dcv_expiration["ov"]
        ev_exp = dcv_expiration["ev"]

        validations = response.json().get("validations")
        if not validations:
            return ("Failed", f"Failed to retrieve validations from {domain['name']}")
        ov_status = validations[0]["status"]
        ev_status = validations[1]["status"]
        dcv_status = f"{ov_status}/{ev_status}"

        return dcv_status, ov_exp

    async def get_dcv_values(self, domain: Dict[str, Any]) -> Tuple[str, str]:
        """
        Get dcv_token and verification_value from domain, to use for cname creation.

        Args:
            domain: domain api object

        Returns:
            dcv_token
            verification_value

        Raises:
            N/A
        """

        if domain["dcv_method"] != "dns-cname-token":
            print(
                "Error: Attempting to get dcv token when method is NOT set to dns-cname-token."
            )
            sys.exit(1)

        url = f"https://www.digicert.com/services/v2/domain/{domain['id']}?include_dcv=true"

        try:
            response = await self.session[self.key].get(url=url, headers=self.headers)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            sys.exit(1)

        if not response.json().get("dcv_token"):
            print(f"API Error getting values from domain {domain['name']}")
            sys.exit(1)

        token = response.json()["dcv_token"]["token"]
        verification_value = response.json()["dcv_token"]["verification_value"]

        return token, verification_value

    async def change_dcv_method(
        self, domain: Dict[str, Any], dcv_type: str = "dns‑cname‑token"
    ) -> Tuple[str, str]:
        """
        Update Domain Control Validation method to `dcv_type`

        Args:
            domain: domain details from api
            dcv_type: type of validation, should be dns_cname

        Returns:
            List[Dict] (temp)

        Raises:
            N/A
        """
        url = f"https://www.digicert.com/services/v2/domain/{domain['id']}/dcv/method"
        payload = json.dumps({"dcv_method": dcv_type})

        try:
            response = await self.session[self.key].put(
                url=url, headers=self.headers, data=payload
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            sys.exit(1)

        # Actual token values
        if not response.json().get("dcv_token"):
            return (
                "failed",
                f"API Error getting DCV values from domain {domain['name']}",
            )
        token = response.json()["dcv_token"]["token"]
        verification_value = response.json()["dcv_token"]["verification_value"]

        return token, verification_value

    async def submit_for_validation(self, domain: Dict[str, Any]) -> Tuple[str, str]:
        """
        Submit domain for validation

        Args:
            domain: domain details from api

        Returns:
            dcv_token &
            verification_value
            or Error Message

        Raises:
            N/A
        """
        url = f"https://www.digicert.com/services/v2/domain/{domain['id']}/validation"
        payload = json.dumps(
            {
                "validations": [{"type": "ov"}, {"type": "ev"}],
                "dcv_method": "dns-cname-token",
            }
        )

        try:
            response = await self.session[self.key].post(
                url=url, headers=self.headers, data=payload
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            sys.exit(1)

        if response.status_code != 201 or not response.json().get("dcv_token"):
            return (
                "Failed",
                f"Failed to submit {domain['name']} for validation. Response was: {response}.",
            )

        token = response.json()["dcv_token"]["token"]
        verification_value = response.json()["dcv_token"]["verification_value"]
        return token, verification_value

    async def check_for_validation(self, domain: Dict[str, Any]) -> bool:
        """
        Check domain for validation

        Args:
            domain: domain details from api

        Returns:
            true/false

        Raises:
            N/A
        """

        url = f"https://www.digicert.com/services/v2/domain/{domain['id']}/validation"
        try:
            response = await self.session[self.key].get(url=url, headers=self.headers)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            sys.exit(1)

        valid_ov = response.json()["validations"][0]["status"]
        valid_ov_dcv = response.json()["validations"][0]["dcv_status"]
        valid_ev = response.json()["validations"][1]["status"]
        valid_ev_dcv = response.json()["validations"][1]["dcv_status"]

        if (
            valid_ov_dcv == "complete"
            and valid_ev_dcv == "complete"
            and valid_ov == "active"
            and valid_ev == "active"
        ):
            print(f"{valid_ov}")
            return True

        print(f"{valid_ov}")
        return False
