"""dcv.utils"""
import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from dcv.dns_updater import DNSUpdater
from dcv.domain_validator import DomainValidator

# Logging
logger = logging.getLogger("utils")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
try:
    file_handler = logging.FileHandler("dcv.log")
except PermissionError:
    print("Permission denied creating dcv.log, check folder permissions.")
    sys.exit(1)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


@dataclass
class DCVResponse:
    """DCV Response Object"""

    domain_name: str
    valid: bool
    cleanup: bool
    message: str


def print_final_results(results: List[DCVResponse]) -> None:
    """
    Print the final results

    Args:
        results: List of DCVResponses

    Returns:
        None

    Raises:
        N/A
    """
    message = "\nDomain Validation complete:\n---------------------------\n"
    print(message)
    logger.info(message)

    for result in results:
        valid = "validated" if result.valid else "NOT VALIDATED"
        cleanup = "been cleaned up" if result.cleanup else "NOT BEEN CLEANED UP"

        message = (
            f"Domain {result.domain_name} is {valid}"
            f"and the cname has {cleanup}, with message: {result.message}"
        )
        print(message)
        logger.info(message)


def print_expiring_domains(domains: List[Dict[str, Any]]) -> None:
    """
    Print out all domains and expiration date

    Args:
        domains: List of domains to be printed

    Returns:
        None

    Raises:
        N/A
    """

    if not domains:
        print("None!")

    else:
        for domain in domains:
            try:
                ov_exp = domain["dcv_expiration"]["ov"]
                ev_exp = domain["dcv_expiration"]["ev"]
                ev_exp_d = datetime.strptime(ev_exp, "%Y-%m-%d")
                ov_exp_d = datetime.strptime(ov_exp, "%Y-%m-%d")
                exp_date_d = (
                    ev_exp_d if ev_exp_d < ov_exp_d else ov_exp_d
                )  # Get lowest date
                print(f"{domain['name']:<30} {f'Expiration: {exp_date_d.date()}':>30}")
            except KeyError:
                print(f"{domain['name']:<30} No expiration found, must be a new domain.")


def read_domains_from_file(filename: str) -> Dict[str, None]:
    """
    Read domain list from a file, one fqdn per line

    Args:
        filename: filename or path to filename

    Returns:
        Dict of domain names as key

    Raises:
        N/A
    """
    try:
        with open(filename, "r", encoding="utf8") as fin:
            domains = {d.rstrip("\n"): None for d in fin.readlines() if d != "\n"}
    except IOError as e:
        print(f"Error loading file: {filename}:")
        print(e)
        sys.exit(1)

    return domains


async def get_domains_from_file(
    dv_obj: DomainValidator, filename: str, num_days: int = 90
) -> List[Dict[str, Any]]:
    """
    Get domain list from a file, then populate with API domain info

    Args:
        dv_obj: DigiCert API Objct
        filename: filename or path to filename
        num_days: default 90, number of days in the future deemed 'soon'

    Returns:
        List of domain api objects

    Raises:
        N/A
    """
    all_domains = await dv_obj.get_domains()
    domains = []
    domain_names = read_domains_from_file(filename)

    # Loop through and build list of domains that actually exist
    for domain in all_domains:
        fqdn = domain["name"]
        if fqdn in domain_names:
            domains.append(domain)
            domain_names.pop(fqdn)  # We found it, don't look for it again

    # Print anything not found
    if domain_names:
        for domain in domain_names:
            message = f"Warning: domain {domain} not found! Check spelling."
            print(message)
            logger.warning(message)

    # Return any expiring domains
    return await dv_obj.get_expiring_domains(domains=domains, num_days=num_days)


async def check_single(key: str, domain_name: str) -> None:
    """
    Check a single domain status

    Args:
        key: DigiCert API Key
        domain_name: fqdn of the domain

    Returns:
        None

    Raises:
        N/A
    """
    dv_obj = DomainValidator(key=key)
    domain = await dv_obj.get_domains(domain_name=domain_name)
    if not domain:
        print(f"Error: Domain {domain_name} not found, exiting...")
        sys.exit(1)

    dcv_status, exp_date = await dv_obj.get_domain_status(domain=domain[0])

    if dcv_status == "Failed":
        print(f"Error retrieving status on domain {domain_name}")
        print(exp_date)  # Actually an error in this case
        sys.exit(1)

    print(f"Domain {domain_name} DCV status: {dcv_status}, Expiration: {exp_date}\n")
    sys.exit(0)


async def check(key: str, num_days: int = 90) -> None:
    """
    Check all domains

    Args:
        key: DigiCert API Key
        num_days: number of days till expired

    Returns:
        None

    Raises:
        N/A
    """
    dv_obj = DomainValidator(key=key)
    # Get all domains expiring 'soon'
    domains = await dv_obj.get_expiring_domains(num_days=num_days)

    # Output
    print("\nList of Domains expiring soon:\n")
    print_expiring_domains(domains)


async def validate_single(
    key: str, username: str, password: str, domain_name: str, timeout: int
) -> None:
    """
    Validate a single domain

    Args:
        key: DigiCert API Key
        username: Neustar/UltraDNS Username
        password: Neustar/UltraDNS Password
        domain_name: fqdn of the domain
        timeout: How many seconds to wait/check for validation

    Returns:
        None

    Raises:
        N/A
    """
    dv_obj = DomainValidator(key=key)
    dns_obj = DNSUpdater(username=username, password=password)
    await dns_obj.login()

    # Validate this single domain (DigiCert) exists
    domain = await dv_obj.get_domains(domain_name=domain_name)
    if not domain:  # Grab only the domain out of the list
        print(f"\nDomain {domain_name} not found in DigiCert, exiting..\n")
        sys.exit(1)

    # Validate zone (dns) exists, domain is List so use first(only) item in list
    zone = await dns_obj.get_zones(domain[0]["name"])
    if not zone:
        print(f"\nDNS Zone{zone} not found in UltraDNS, exiting...\n")
        sys.exit(1)

    # Async validate one domains!
    await runall(
        key=key,
        username=username,
        password=password,
        expiring_domains=domain,
        timeout=timeout,
    )


async def runall(
    key: str,
    username: str,
    password: str,
    file: str = None,
    num_days: int = 90,
    timeout: int = 240,
    expiring_domains: List[Dict[str, Any]] = None,
) -> None:
    """
    Validate the Domains!

    Args:
        key: DigiCert API Key
        username: Neustar/UltraDNS Username
        password: Neustar/UltraDNS Password
        timeout: Optional int, length of timeout on validation check
        file: filename
        num_days: num days
        expiring_domains: List of domains to validate, expiring 'soon' or manually validating

    Returns:
        None

    Raises:
        N/A
    """
    logger.info("")
    logger.info(
        "------------------------------------------------------"
        "--------DCV: Beginning new run------------------------"
        "------------------------------------------------------"
    )
    logger.info("")

    dv_obj = DomainValidator(key=key)
    dns_obj = DNSUpdater(username=username, password=password)
    await dns_obj.login()

    # Get/print all expiring 'soon' domains
    if file:
        expiring_domains = await get_domains_from_file(
            dv_obj=dv_obj, filename=file, num_days=num_days
        )
    elif not expiring_domains:
        expiring_domains = await dv_obj.get_expiring_domains(num_days=num_days)

    # Prompt user with list of domains we're about to validate
    print("\n\nList of Domains expiring soon:\n")
    print_expiring_domains(expiring_domains)

    if not expiring_domains:
        print("\nNo expiring domains found, exiting...\n")
        sys.exit(0)

    yesno = ""
    while yesno.lower() not in ("y", "n"):
        yesno = input("\nThe above domains will be validated, continue? [y/n]")
    if yesno.lower() == "n":
        print("Aborting validation steps.\n")
        sys.exit(0)

    # DigiCert API has rate-limit of 100 calls per 5 seconds.
    if len(expiring_domains) >= 40:
        limit = asyncio.Semaphore(value=20)
    else:
        limit = None

    print("\nValidating..\n")
    # Async validate em all
    coroutines = [
        validate_domain_limiter(
            dv_obj=dv_obj, dns_obj=dns_obj, domain=domain, limit=limit, timeout=timeout
        )
        for domain in expiring_domains
    ]
    results = await asyncio.gather(*coroutines)

    print_final_results(results)


async def validate_domain_limiter(
    dv_obj: DomainValidator,
    dns_obj: DNSUpdater,
    domain: Dict[str, Any],
    limit: Optional[asyncio.Semaphore],
    timeout: int = 240,
) -> DCVResponse:
    """
    Validate Domain Wrapper / Limit if necessary.

    DigiCert API has rate-limit of 100 calls per 5 seconds.
    Limit jobs in batches, if <40 jobs, don't do the unnecessary sleep at the end.
    """
    if not limit:
        return await validate_domain(
            dv_obj=dv_obj, dns_obj=dns_obj, domain=domain, timeout=timeout
        )
    async with limit:
        result = await validate_domain(
            dv_obj=dv_obj, dns_obj=dns_obj, domain=domain, timeout=timeout
        )
        # print("Waiting 6 seconds for next batch so DigiCert doesn't block us...")
        # await asyncio.sleep(6)
        return result


async def validate_domain(
    dv_obj: DomainValidator,
    dns_obj: DNSUpdater,
    domain: Dict[str, Any],
    timeout: int = 240,
) -> DCVResponse:
    """
    DCV - Meat and Potatoes

    Args:
        dv_obj: DigiCert API Instance
        dns_obj: Neustar/UltraDNS Instance
        domain: domain to be validated
        timeout: Optional int, length of timeout on validation check

    Returns:
        None

    Raises:
        N/A
    """
    response = DCVResponse(domain["name"], False, False, "Success")

    # Change DCV_Method to dns-cname-token if needed, get dcv_token if not.
    if domain["dcv_method"] != "dns-cname-token":
        print(
            f"Changing DCV method to dns-cname-token for domain {domain['name']}: ",
            end="",
        )
        dcv_token, err = await dv_obj.change_dcv_method(
            domain=domain, dcv_type="dns-cname-token"
        )
        if dcv_token == "Failed":
            response.message = err
            return response

        print("DCV method updated.\n")

    # Submit for validation and get dcv_token and verification_value
    dcv_token, err = await dv_obj.submit_for_validation(domain=domain)
    if dcv_token == "Failed":
        response.message = err
        return response

    verification_value = err  # Not an error at this point, just renaming
    print(f"\nSubmitted {domain['name']} for validation.")

    # Create DNS CNAME record w/ token
    api_response = await dns_obj.create_cname_record(
        domain_name=domain["name"], cname=dcv_token, rdata=verification_value
    )
    if api_response != "Successful":
        response.message = api_response
        return response
    message = f"CNAME: {dcv_token}.{domain['name']} created."
    print(message)
    logger.info(message)

    # Check for validation every 240 seconds for up to timeout value (default 240 seconds)
    attempts = 1
    max_attempts = timeout / 240
    response.message = (
        "Timeout is 0, not checking statuses, use dcv check -d and cleanup DNS manually."
        if not max_attempts
        else "Success"
    )

    while not response.valid and max_attempts > 0:
        if attempts == 1:
            print("Beginning check validation period, please wait..")
        elif attempts > max_attempts:
            message = f"Giving up on {domain['name']} after too many retries. "
            print(message)
            logging.warning(message)
            break
        await asyncio.sleep(timeout)
        print(f"Checking {domain['name']} for validation, attempt #{attempts}.")
        response.valid = await dv_obj.check_for_validation(domain=domain)
        attempts += 1

    if response.valid:
        message = f"Domain {domain['name']} successfully validated!"
        print(message)
        logger.info(message)
        response.cleanup = True

    else:
        logger.error(f"Error, {domain['name']} was not validated.")

    # DNS Cleanup
    api_response = await dns_obj.delete_cname_record(
        domain_name=domain["name"], cname=dcv_token
    )
    if api_response == "Successful":
        response.cleanup = True
        message = f"DNS for {domain['name']} cleaned up."
        print(message)
        logger.info(message)
    else:
        response.message = api_response
        print(response.message)
        logger.error(response.message)
        logger.error(f"Error, {dcv_token}.{domain['name']} was not cleaned up.")
        return response

    return response
