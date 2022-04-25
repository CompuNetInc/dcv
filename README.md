DigiCert & Neustar/UltraDNS Domain Validation
========
Command line tool to check DigiCert for expiring 'soon' domains. If deemed expiring (default 90 days, user configurable),
it will automatically validate the domains via dns cname records (assuming you own the zone in UltraDNS).

Two installation options:
- [Python based](#Python-Based)
- [Docker based](#Docker-Based)

## <a name="Python-Based"></a>Installation

Without Docker, you'll need Python 3.7+, you can install python via https://www.python.org/

Once Python is installed, using DCV is easy:

0. Highly HIGHLY recommended but not required, a virtual environment
   - `python -m venv venv`
     - `source venv/bin/activate` (Linux/Mac)
     - `venv/bin/activate` (Windows)
1. Installing from GitHub
   - `pip install git+https://github.com/compunetinc/dcv.git`

..and you're done!

## Usage

The installation process will install an executable `dcv` on your path. You can confirm this like:

```shell
Usage: dcv [OPTIONS] COMMAND [ARGS]...

  DCV: DigiCert/Neustar (UltraDNS) Domain Control Validator.

Options:
  --help  Show this message and exit.

Commands:
  check     Check domains for expiring 'soon' validations.
  runall    Find all expiring domains and validate them.
  validate  Validate single domain manually, regardless of expiration date.
```

You can also get help for each individual command (check/validate/runall) via `dcv COMMAND --help`

If you get a complaint about "command not found" you maybe installed dcv into a different virtual environment 
or forgot to activate the virtual environment.

- 'check' will find all domains expiring soon (default 90 days out, can be modified with --num-days xyz). 
- 'validate' is for validating a specific domain regardless of expiration status.
- 'runall' will do just what it sounds like, grab all domains expiring 'soon' AND validate them as well, in one step.
    You can send a list of domains (from a file) with the --file/-f flag if you don't want to search 'all' domains.

#### Requirements
A DigiCert API key is required in order to authenticate to DigiCert, and Neustar Username/Password is required for that API. 
These credentials will be prompted for if not given via the appropriate flags, 
however you can also use environment variables to avoid getting prompted on each run if you are doing multiple passes. 
The environment variables are listed below:

  * DIGICERT_KEY
  * NEUSTAR_USER
  * NEUSTAR_PASS

Set these variables appropriately for your operating system (see below), and you won't be prompted anymore!

Linux/Mac:
```shell
export DIGICERT_KEY=abcd123456
```
Windows:
```shell
set DIGICERT_KEY=abcd123456
```

## <a name="Docker-Based"></a> Usage with Docker

You can use this with Docker Desktop (or whatever container runtime, really) and docker-compose so you don't have to 
mess with installing anything (other than Docker Desktop/compose of course). 
Information can be found here: https://docs.docker.com/desktop/.
The advantage to using Docker is that you'll no longer have any Python or Operating System dependencies to worry about!

The simplest way to get started is to run `docker-compose up` while in this directory.
If you have never built the image, it will be built for you, you'll get something like this (first run only):

```text
+] Building 11.2s (9/9) FINISHED                                                                                                                                                               
 => [internal] load build definition from Dockerfile                                                                                                                                       0.0s
 => => transferring dockerfile: 145B                                                                                                                                                       0.0s
 => [internal] load .dockerignore                                                                                                                                                          0.0s
 => => transferring context: 2B                                                                                                                                                            0.0s
 => [internal] load metadata for docker.io/library/python:3.9.7-slim-bullseye                                                                                                              1.2s
 => [1/4] FROM docker.io/library/python:3.9.7-slim-bullseye@sha256:aef632387d994b410de020dfd08fb1d9b648fc8a5a44f332f7ee326c8e170dba                                                        0.0s
 => [internal] load build context                                                                                                                                                          3.2s
 => => transferring context: 105.15MB                                                                                                                                                      3.1s
 => CACHED [2/4] WORKDIR /app                                                                                                                                                              0.0s
 => [3/4] COPY . .                                                                                                                                                                         0.7s
 => [4/4] RUN pip install -e .                                                                                                                                                             5.2s
 => exporting to image                                                                                                                                                                     0.9s 
 => => exporting layers                                                                                                                                                                    0.9s 
 => => writing image sha256:b44ade96cd6cb811686a114c21acab7d11a973884e646077b1e3a9dc93cec9dc                                                                                               0.0s 
 => => naming to docker.io/library/dcv:latest                                                                                                                                       0.0s 
                                                                                                                                                                                                
Use 'docker scan' to run Snyk tests against images to find vulnerabilities and learn how to fix them  
```

Once the container has been built, you can run the commands as normal, 
just prepend 'docker-compose run` to any command, ie:
- `docker-compose run dcv check --num-days 120`
- `docker-compose run dcv runall`

..etc!
