from dataclasses import fields, is_dataclass
from typing import Any, Dict, List, Optional, Union, get_args, get_origin
import json
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
from openpurse import models

class Exporter:
    """
    Utility to export OpenPurse dataclass models as standard OpenAPI 3.0.0 or JSON Schema definitions.
    """

    @staticmethod
    def _map_python_type_to_openapi(py_type: Any) -> Dict[str, Any]:
        """
        Maps a Python type to its OpenAPI schema representation.
        """
        origin = get_origin(py_type)
        args = get_args(py_type)

        # Handle Optional[T] (which is Union[T, NoneType])
        if origin is Union and type(None) in args:
            # OpenAPI 3.0 uses 'nullable: true'
            base_type = next(t for t in args if t is not type(None))
            schema = Exporter._map_python_type_to_openapi(base_type)
            schema["nullable"] = True
            return schema

        if py_type is str:
            return {"type": "string"}
        if py_type is int:
            return {"type": "integer"}
        if py_type is float:
            return {"type": "number"}
        if py_type is bool:
            return {"type": "boolean"}
        
        if origin is list or py_type is list:
            item_type = args[0] if args else Any
            return {
                "type": "array",
                "items": Exporter._map_python_type_to_openapi(item_type)
            }

        if is_dataclass(py_type):
            return {"$ref": f"#/components/schemas/{py_type.__name__}"}

        return {"type": "string"} # Fallback

    @staticmethod
    def generate_schema(model_class: Any) -> Dict[str, Any]:
        """
        Generates a JSON Schema component for a given dataclass.
        """
        if not is_dataclass(model_class):
            raise ValueError(f"{model_class} is not a dataclass")

        properties = {}
        required = []

        for field in fields(model_class):
            properties[field.name] = Exporter._map_python_type_to_openapi(field.type)
            # Check if it's NOT Optional
            origin = get_origin(field.type)
            args = get_args(field.type)
            is_optional = (origin is Union and type(None) in args)
            if not is_optional:
                required.append(field.name)

        schema = {
            "type": "object",
            "properties": properties,
            "description": model_class.__doc__.strip() if model_class.__doc__ else None
        }
        
        if required:
            schema["required"] = required

        return schema

    @staticmethod
    def to_openapi() -> Dict[str, Any]:
        """
        Generates a complete OpenAPI 3.0.0 specification for all OpenPurse models.
        """
        # List of models to include in the spec
        model_classes = [
            models.PostalAddress,
            models.PaymentMessage,
            models.Pacs008Message,
            models.Camt054Message,
            models.Camt004Message,
            models.Camt052Message,
            models.Camt053Message,
            models.Pain001Message,
            models.Pain002Message,
            models.Pain008Message,
            models.ValidationReport
        ]

        schemas = {}
        for model in model_classes:
            schemas[model.__name__] = Exporter.generate_schema(model)

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "OpenPurse Financial Message API",
                "version": "1.0.0",
                "description": "API specification for standardized ISO 20022 and SWIFT MT payment messages."
            },
            "components": {
                "schemas": schemas
            },
            "paths": {} # Path definitions are not applicable for a library, but required for valid OpenAPI
        }

        return spec

    @staticmethod
    def export_json(path: str):
        """
        Saves the OpenAPI spec to a JSON file.
        """
        spec = Exporter.to_openapi()
        with open(path, "w") as f:
            json.dump(spec, f, indent=2)

    @staticmethod
    def export_yaml(path: str):
        """
        Saves the OpenAPI spec to a YAML file.
        """
        if not HAS_YAML:
            raise ImportError("PyYAML is required for YAML export. Install it with 'pip install PyYAML'.")
        spec = Exporter.to_openapi()
        with open(path, "w") as f:
            yaml.dump(spec, f, sort_keys=False)
