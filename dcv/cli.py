"""dcv.cli"""
import asyncio
import platform
from typing import Optional

import typer

import dcv.utils as dcv

app = typer.Typer(
    name="dcv",
    add_completion=False,
    help="DCV: DigiCert/Neustar (UltraDNS) Domain Control Validator.",
)


@app.command("check", help="Check domains for expiring 'soon' validations.")
def check(
    key: Optional[str] = typer.Option(
        None,
        envvar="DIGICERT_KEY",
        prompt="DigiCert Key (hidden): ",
        hide_input=True,
    ),
    num_days: Optional[int] = typer.Option(
        90, help="Number of days till considered 'expiring soon'."
    ),
    domain_name: Optional[str] = typer.Option(
        None,
        "--domain",
        "-d",
        help="Domain Name (FQDN) for the domain you want to check.",
    ),
) -> None:
    """
    Check for domains expiring soon

    Args:
        key: DigiCert API Key
        domain_name: Check ONLY this domain/report expiration date
        num_days: Number of days till considered 'expiring soon'

    Returns:
        None

    Raises:
        N/A
    """

    if domain_name:
        print(f"Checking status and expiration of {domain_name}..\n\n")
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(dcv.check_single(key=key, domain_name=domain_name))
    else:
        print(f"Checking for expiring domains within {num_days} from now..\n")
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(dcv.check(key=key, num_days=num_days))

    print("\nThank you for using DCV.\n")


@app.command(
    "validate", help="Validate single domain manually, irregardless of expiration date."
)
def validate(
    key: Optional[str] = typer.Option(
        None,
        envvar="DIGICERT_KEY",
        prompt="DigiCert Key (hidden): ",
        hide_input=True,
    ),
    username: Optional[str] = typer.Option(
        None, envvar="NEU_USERNAME", prompt="Neustar/UltraDNS username: "
    ),
    password: Optional[str] = typer.Option(
        None,
        envvar="NEU_PASSWORD",
        prompt="Neustar/UltraDNS password: ",
        hide_input=True,
    ),
    domain_name: Optional[str] = typer.Option(
        None,
        "--domain",
        "-d",
        help="Domain Name (FQDN) for the domain you want to validate.",
        prompt="Domain name (FQDN): ",
    ),
    timeout: Optional[int] = typer.Option(
        180, help="Timeout length (in seconds) waiting for validation"
    ),
) -> None:
    """
    Validate a SINGLE domain via commandline

    Args:
        key: DigiCert API Key
        username: Neustar/UltraDNS Username
        password: Neustar/UltraDNS Password
        domain_name: Domain Name (FQDN) to validate
        timeout: Optional int, length of timeout in seconds on validation check

    Returns:
        None

    Raises:
        N/A
    """

    print(f"Validating expiring domain {domain_name} manually..\n\n")
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(
        dcv.validate_single(
            key=key,
            username=username,
            password=password,
            domain_name=domain_name,
            timeout=timeout,
        )
    )
    print("\nThank you for using DCV.\n")


@app.command("runall", help="Find all expiring domains and validate them.")
def run_all(
    key: Optional[str] = typer.Option(
        None,
        envvar="DIGICERT_KEY",
        prompt="DigiCert Key (hidden): ",
        hide_input=True,
    ),
    username: Optional[str] = typer.Option(
        None, envvar="NEU_USERNAME", prompt="Neustar/UltraDNS username: "
    ),
    password: Optional[str] = typer.Option(
        None,
        envvar="NEU_PASSWORD",
        prompt="Neustar/UltraDNS password: ",
        hide_input=True,
    ),
    num_days: Optional[int] = typer.Option(
        90,
        help="Number of days till considered 'expiring soon'.",
    ),
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Filename/Path to filename containing list of domains. One domain per line.",
    ),
    timeout: Optional[int] = typer.Option(
        180, help="Timeout length (in seconds) to wait for validation."
    ),
) -> None:
    """
    Run all the things

    Check for all domains expiring 'soon'
    Validate all of these domains
    Cleanup DNS (if validation happens soon enough)

    Args:
        key: DigiCert API Key
        username: Neustar/UltraDNS Username
        password: Neustar/UltraDNS Password
        num_days: Number of days till considered 'expiring soon'
        file: Filename/path to filename containing list of domains, one domain per line
        timeout: Optional int, length of timeout in seconds to wait for validaton

    Returns:
        None

    Raises:
        N/A
    """

    print(
        f"Checking for and Validating expiring domains within {num_days} from now..\n\n"
    )
    # Async validate dem mains!
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(
        dcv.runall(
            key=key,
            username=username,
            password=password,
            timeout=timeout,
            file=file,
            num_days=num_days,
        )
    )
    print("\nThank you for using DCV.)\n")


@app.callback()
def begin() -> None:
    """
    Print the opening banner

    Args:
    Returns:
        None

    Raises:
        N/A
    """

    print("")
    print("DCV - Domain Control Validation using Digicert and Nuestar/UltraDNS API's")
    print("")


if __name__ == "__main__":
    app()
