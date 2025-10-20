
# 📌 Needlectl: Needle Command Line Interface  



Needlectl is a command-line tool designed to interact with **Needle**, a system that retrieves and manages visual content. This CLI enables you to efficiently manage directories, perform searches, and control backend services—all through a simple and powerful interface. Checkout the [Documenation](https://uic-indexlab.github.io/Needle/needlectl/index.html) for more details.

---

## ⚙️ Profiles & Configuration

You can use the `--home`/`-H` flag to point needlectl at a custom Needle installation or local checkout, and select a runtime profile (`prod` or `dev`) that auto-configures the compose files and config directory. For advanced scenarios you can override just the configs path with `--config-dir`.

By default, `--profile` is set to **prod**, so omitting it will assume the production profile.

### Examples

#### Development

Spin up services against your local checkout in dev mode (fast configs + hot‑reload compose overrides):

```bash
needlectl --home $(pwd) --profile dev service start
```

This uses:
- `NEEDLE_CONFIG_DIR=$NEEDLE_HOME/configs/fast`
- Infrastructure: `docker/docker-compose.infrastructure.yaml`
- Backend: Virtual environment
- Image Generator: Virtual environment

#### Production

Run against a deployed install (standard configs + prod override):

```bash
needlectl --home /opt/needle --profile prod service start
```

#### Custom config-dir

Only override the configuration directory (compose files follow the selected profile):

```bash
needlectl --home /opt/needle --config-dir /etc/needle/configs service start
```

