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

- Install the dependencies

```bash
pip install -r requirements.txt
```

- Configure NGINX to act as a proxy to the gunicorn server.

```nginx
server {
    listen [::]:443 ssl ipv6only=on;
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/tmpweb.net/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/tmpweb.net/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
    server_name tmpweb.net;
    root /src/tmpweb/www;
    index index.html index.htm index;
    location / {
        # Send requests to gunicorn server.
        proxy_pass http://localhost:8000;
    }
}
server {
    listen [::]:80 ;
    listen 80 ;
    server_name tmpweb.net;

    if ($host = tmpweb.net) {
        return 301 https://$host$request_uri;
    }
    return 404;
}
```

- Configure `tmpweb_config.toml`.

- Copy static files into hosting directory.

```bash
mkdir -p /srv/tmpweb/www
cp -r static/* /srv/tmpweb/www/
```

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

- Run with gunicorn.

```bash
cd src
gunicorn tmpweb:app 8000
```

## Roadmap/To Do

- [ ] Add tests.
- [ ] Get NGINX to handle all GET requests.
- [ ] Improve front page, including adding a web uploader.

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
