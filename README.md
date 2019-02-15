# Backup Tool

TKTK

Usage
```
backup.py configfilepath.json
```

Config file should contain:
```
{
  "token": "XXX"
}
```

# TODO

* Add pruning of definitions older than a timestamp
* Add restoration of entity @ timestamp
* Detectors
* Docs

# Storage

## Dashboard Groups, Dashboards and Charts

Dashboards must be in Dashboard Groups, and Charts in Dashboards. To reflect that a directory structure like this is used (assumes a target directory of `backups`):

```
backups                   
├── DzYcoMDAcAE
│   ├── 1550165452744.json
│   ├── DzYc06kAgAA
│   │   ├── 1550165475470.json
│   │   ├── DzYc1WxAcAA
│   │   │   └── 1550165476002.json
│   │   ├── DzYc2L4AYAA
│   │   │   └── 1550165475710.json
│   │   ├── DzYc40KAYAA
│   │   │   └── 1550165475818.json
│   │   ├── DzYc44UAgAA
│   │   │   └── 1550165476352.json
│   │   ├── DzYc52eAcAA
│   │   │   └── 1550165476165.json
│   │   └── DzYc80NAYAA
│   │       └── 1550165476441.json
```

Each JSON file is a timestamp, containing the definition of the entity at that time. The directory structure is:
```
"dashboard group id" -> "dashboard id" -> "chart id"
```

As changes happen new JSON files will appear, containing the definition at that point in time.
