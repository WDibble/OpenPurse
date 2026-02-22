#!/usr/bin/env python3
import os
import sys
import argparse
from openpurse.exporter import Exporter

def main():
    parser = argparse.ArgumentParser(description="Export OpenPurse models as OpenAPI or JSON Schema.")
    parser.add_argument("--format", choices=["json", "yaml"], default="json", help="Export format (default: json)")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    try:
        if args.format == "yaml":
            if args.output:
                Exporter.export_yaml(args.output)
                print(f"Exported OpenAPI YAML to {args.output}")
            else:
                import yaml
                print(yaml.dump(Exporter.to_openapi(), sort_keys=False))
        else:
            import json
            if args.output:
                Exporter.export_json(args.output)
                print(f"Exported OpenAPI JSON to {args.output}")
            else:
                print(json.dumps(Exporter.to_openapi(), indent=2))
    except ImportError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
