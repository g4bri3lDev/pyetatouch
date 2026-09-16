# pyetatouch

Async Python client for the **ETAtouch RESTful web service** (API ≥ 1.2) of ETA pellet and wood boilers.

- bulk polling through self-healing variable sets (one HTTP request per poll)
- curated, language-independent variable catalog
- discovery that needs nothing but the host

The web service must be enabled: request LAN access on meinETA, then enable it on the touch panel (system settings).

```python
import aiohttp
from pyetatouch import EtaClient, discover

async with aiohttp.ClientSession() as session:
    client = EtaClient(session, "192.0.2.10")
    await client.check_api()
    installation = await discover(client)
    async with client.varset("myapp", [v.address for v in installation.variables]) as varset:
        values = await varset.read_all()
```

CLI: `pyetatouch discover <host>`, `pyetatouch read <host> <address>`, `pyetatouch write <host> <address> <value> --yes`, `pyetatouch dump <host> -o eta-dump.json`.

## Missing a value?

The catalog maps ETA variable ids to well-known roles. If your heater has a value that is not supported yet, create a structure report and open a *Catalog request* issue:

```
pyetatouch dump <heater-ip> -o eta-dump.json
```

The report contains no values, no network addresses and no panel names.
