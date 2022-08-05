"""dcv.domain_validator"""
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("utils")


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

        exp_date = datetime.now() + timedelta(num_days)  # expires 180 days from now
        exp_domains = []

        for domain in domains:
            dcv_expiration = domain.get(
                "dcv_expiration"
            )  # Some domains don't have this

            if dcv_expiration:
                ev_exp_str = dcv_expiration["ev"]
                ov_exp_str = dcv_expiration["ov"]
            else:
                message = (
                    f"Info: No expiration, domain has likely never been validated, "
                    f"Use dcv validate -d {domain['name']} "
                    "to manually validate if desired."
                )
                print(message)
                logger.info(message)
                exp_domains.append(domain)
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

        validations = response.json().get("validations")
        if not validations:
            return "Failed", f"Failed to retrieve validations from {domain['name']}"
        ov_status = validations[0]["status"]
        ev_status = validations[1]["status"]
        dcv_status = f"{ov_status}/{ev_status}"

        return dcv_status, ov_exp

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
        err_message = (
            "Failed",
            f"API Error getting DCV values from domain {domain['name']}",
        )

        try:
            response = await self.session[self.key].put(
                url=url, headers=self.headers, data=payload
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            logger.exception(err_message)
            return err_message
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            logger.exception(err_message)
            return err_message

            # Actual token values
        if not response.json().get("dcv_token"):
            return err_message

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
        err_message = (
            "Failed",
            f"Failed to submit {domain['name']} for validation.",
        )

        try:
            response = await self.session[self.key].post(
                url=url, headers=self.headers, data=payload
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"{url=}, {self.headers=}")
            print("Request error: ", e)
            logger.exception(err_message)
            return err_message
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            logger.exception(err_message)
            return err_message

        if response.status_code != 201 or not response.json().get("dcv_token"):
            return err_message

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
            logger.exception(f"Check for Validation failed on domain {domain['name']}.")
            return False
        except httpx.HTTPStatusError as e:
            print(f"{url=}, {self.headers=}")
            print("HTTP Status error: ", e)
            logger.exception(f"Check for Validation failed on domain {domain['name']}.")
            return False

        validations = response.json().get("validations")
        if not validations:
            logger.exception(f"Check for Validation failed on domain {domain['name']}.")
            return False

        valid_ov = validations[0]["status"]
        valid_ov_dcv = validations[0]["dcv_status"]
        valid_ev = validations[1]["status"]
        valid_ev_dcv = validations[1]["dcv_status"]

        if (
            valid_ov_dcv == "complete"
            and valid_ev_dcv == "complete"
            and valid_ov == "active"
            and valid_ev == "active"
        ):
            return True

        return False
