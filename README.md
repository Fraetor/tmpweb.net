[![tmpweb.net](static/logo.svg)](https://tmpweb.net)

A temporary website hosting service, usable programmatically.

## Installation

- Clone this git repository.

```bash
git clone https://github.com/Fraetor/tmpweb.net.git
```

- Create a venv (optional, but highly recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

- Install the dependencies: `pip install -r requirements.txt`

- Configure NGINX to act as a proxy to the gunicorn server. See
  [nginx.conf](nginx.conf) and [tmpweb.net.conf](tmpweb.net.conf) for example
  configurations.

- Configure `src/config.toml`.

- Copy static files into hosting directory: `python3 install.py`

- Reload NGINX

```bash
nginx -s reload
```

### Requirements

- Recent [Python 3](https://www.python.org/) (developed with 3.11, but may work with some older versions)
- gunicorn
- NGINX web server

### Development Requirements

- [PyTest](https://docs.pytest.org/)

## Usage

Once NGINX is configured correctly, simply run `./run-tmpweb.sh`.

To delete expired sites pass a DELETE request from a loopback address.

I'd recommend adding this to the crontab:

```bash
# Run tmpweb.net application server on startup.
@reboot cd /var/www/tmpweb/tmpweb.net ; ./run-tmpweb.sh

# Delete expired websites for tmpweb.net.
0 0 * * * perl -e 'sleep rand(18000)' ; curl -X DELETE http://127.0.0.1:8000
```

## Roadmap/To Do

- [ ] Add tests.
- [ ] Improve front page, including adding terms of use.
- [x] Migrate to shared infrastructure.
- [x] Add better installation instructions.

<!-- ## Contributing

State if you are open to contributions and what your requirements are for
accepting them.

For people who want to make changes to your project, it's helpful to have some
documentation on how to get started. Perhaps there is a script that they should
run or some environment variables that they need to set. Make these steps
explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help
to ensure high code quality and reduce the likelihood that the changes
inadvertently break something. Having instructions for running tests is
especially helpful if it requires external setup, such as starting a Selenium
server for testing in a browser. -->

<!-- ## Acknowledgements

Show your appreciation to those who have contributed to the project. -->

## Licence

This software is available under the [MIT Licence](LICENCE.md).
