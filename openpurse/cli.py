import argparse
import sys
import json
from typing import Optional

from openpurse.parser import OpenPurseParser
from openpurse.validator import Validator
from openpurse.integrations.pydantic import from_dataclass
from openpurse.database.repository import MessageRepository
from openpurse.database.models import Base

def handle_parse(args):
    """Handles the 'parse' subcommand: Outputs JSON summary of a message."""
    try:
        with open(args.file, "rb") as f:
            raw_data = f.read()
        
        parser = OpenPurseParser(raw_data)
        msg = parser.parse_detailed()
        
        pydantic_msg = from_dataclass(msg)
        print(pydantic_msg.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        sys.exit(1)

def handle_validate(args):
    """Handles the 'validate' subcommand: Check schema and business logic."""
    try:
        with open(args.file, "rb") as f:
            raw_data = f.read()
        
        # 1. Schema/Structural Validation
        schema_report = Validator.validate_schema(raw_data)
        if not schema_report.is_valid:
            print("❌ Schema Validation Failed:")
            for err in schema_report.errors:
                print(f"  - {err}")
            sys.exit(1)
        
        # 2. Logical/Data Validation
        parser = OpenPurseParser(raw_data)
        msg = parser.parse_detailed()
        logic_report = Validator.validate(msg)
        
        if not logic_report.is_valid:
            print("⚠️ Structural OK, but Data Validation Failed:")
            for err in logic_report.errors:
                print(f"  - {err}")
            sys.exit(1)
            
        print("✅ Validation Successful: Message is valid and compliant.")
        
    except Exception as e:
        print(f"Error validating file: {e}", file=sys.stderr)
        sys.exit(1)

def handle_persist(args):
    """Handles the 'persist' subcommand: Saves message to a database."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        with open(args.file, "rb") as f:
            raw_data = f.read()
            
        parser = OpenPurseParser(raw_data)
        msg = parser.parse_detailed()
        
        engine = create_engine(args.db_url)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            repo = MessageRepository(session)
            record = repo.save(msg)
            session.commit()
            print(f"✅ Successfully persisted message (ID: {record.message_id}) to database.")
            
    except Exception as e:
        print(f"Error persisting message: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        prog="openpurse",
        description="OpenPurse CLI - High-performance financial message processing tool."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: parse
    parse_parser = subparsers.add_parser("parse", help="Parse a file and output JSON summary.")
    parse_parser.add_argument("file", help="Path to the ISO 20022 or SWIFT MT file.")
    parse_parser.set_defaults(func=handle_parse)

    # Subcommand: validate
    validate_parser = subparsers.add_parser("validate", help="Perform schema and business validation.")
    validate_parser.add_argument("file", help="Path to the file to validate.")
    validate_parser.set_defaults(func=handle_validate)

    # Subcommand: persist
    persist_parser = subparsers.add_parser("persist", help="Parse and save a file to a database.")
    persist_parser.add_argument("file", help="Path to the file to persist.")
    persist_parser.add_argument("--db-url", required=True, help="SQLAlchemy database URL (e.g. sqlite:///test.db).")
    persist_parser.set_defaults(func=handle_persist)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
