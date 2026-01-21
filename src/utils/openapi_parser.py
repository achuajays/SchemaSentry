"""
OpenAPI specification parser utility.
Parses OpenAPI/Swagger specs into structured format for comparison.
"""

import yaml
import json
from pathlib import Path
from typing import Any, Optional


class OpenAPIParser:
    """Parse OpenAPI/Swagger specifications."""
    
    def __init__(self, spec_path: Optional[str] = None, spec_content: Optional[dict] = None):
        """
        Initialize parser with either a file path or spec content.
        
        Args:
            spec_path: Path to OpenAPI spec file (YAML or JSON)
            spec_content: Pre-loaded spec dictionary
        """
        self.spec: dict = {}
        
        if spec_content:
            self.spec = spec_content
        elif spec_path:
            self.load_from_file(spec_path)
    
    def load_from_file(self, path: str) -> dict:
        """Load spec from file (YAML or JSON)."""
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"OpenAPI spec not found: {path}")
        
        content = path.read_text(encoding="utf-8")
        
        if path.suffix in [".yaml", ".yml"]:
            self.spec = yaml.safe_load(content)
        else:
            self.spec = json.loads(content)
        
        return self.spec
    
    def load_from_string(self, content: str, format: str = "yaml") -> dict:
        """Load spec from string content."""
        if format == "yaml":
            self.spec = yaml.safe_load(content)
        else:
            self.spec = json.loads(content)
        return self.spec
    
    def get_version(self) -> str:
        """Get OpenAPI version."""
        if "openapi" in self.spec:
            return self.spec["openapi"]
        elif "swagger" in self.spec:
            return self.spec["swagger"]
        return "unknown"
    
    def get_endpoints(self) -> list[dict]:
        """
        Extract all endpoints from spec.
        
        Returns:
            List of endpoint definitions with path, method, and schema info
        """
        endpoints = []
        paths = self.spec.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": self._extract_parameters(details),
                        "request_body": self._extract_request_body(details),
                        "responses": self._extract_responses(details),
                    }
                    endpoints.append(endpoint)
        
        return endpoints
    
    def get_endpoint_schema(self, path: str, method: str) -> Optional[dict]:
        """
        Get the response schema for a specific endpoint.
        
        Args:
            path: API path (e.g., "/users/{id}")
            method: HTTP method (e.g., "GET")
            
        Returns:
            Schema definition or None if not found
        """
        paths = self.spec.get("paths", {})
        
        if path not in paths:
            return None
        
        method_lower = method.lower()
        if method_lower not in paths[path]:
            return None
        
        endpoint = paths[path][method_lower]
        responses = endpoint.get("responses", {})
        
        # Get 200/201 response schema
        for status in ["200", "201", 200, 201]:
            if status in responses:
                return self._extract_response_schema(responses[status])
        
        return None
    
    def _extract_parameters(self, endpoint: dict) -> list[dict]:
        """Extract parameters from endpoint definition."""
        params = []
        for param in endpoint.get("parameters", []):
            params.append({
                "name": param.get("name"),
                "in": param.get("in"),
                "required": param.get("required", False),
                "schema": param.get("schema", {}),
            })
        return params
    
    def _extract_request_body(self, endpoint: dict) -> Optional[dict]:
        """Extract request body schema."""
        request_body = endpoint.get("requestBody", {})
        if not request_body:
            return None
        
        content = request_body.get("content", {})
        for content_type in ["application/json", "application/x-www-form-urlencoded"]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                return self._resolve_schema(schema)
        
        return None
    
    def _extract_responses(self, endpoint: dict) -> dict:
        """Extract all response schemas."""
        responses = {}
        for status_code, response in endpoint.get("responses", {}).items():
            responses[str(status_code)] = {
                "description": response.get("description", ""),
                "schema": self._extract_response_schema(response),
            }
        return responses
    
    def _extract_response_schema(self, response: dict) -> Optional[dict]:
        """Extract schema from response definition."""
        content = response.get("content", {})
        
        if "application/json" in content:
            schema = content["application/json"].get("schema", {})
            return self._resolve_schema(schema)
        
        # OpenAPI 2.x format
        if "schema" in response:
            return self._resolve_schema(response["schema"])
        
        return None
    
    def _resolve_schema(self, schema: dict) -> dict:
        """Resolve $ref references in schema."""
        if "$ref" in schema:
            ref_path = schema["$ref"]
            return self._resolve_ref(ref_path)
        
        # Handle arrays
        if schema.get("type") == "array" and "items" in schema:
            resolved_items = self._resolve_schema(schema["items"])
            return {**schema, "items": resolved_items}
        
        # Handle object properties
        if "properties" in schema:
            resolved_props = {}
            for prop_name, prop_schema in schema["properties"].items():
                resolved_props[prop_name] = self._resolve_schema(prop_schema)
            return {**schema, "properties": resolved_props}
        
        return schema
    
    def _resolve_ref(self, ref_path: str) -> dict:
        """Resolve a $ref path to its schema."""
        if not ref_path.startswith("#/"):
            return {"$ref": ref_path}  # External ref, can't resolve
        
        parts = ref_path[2:].split("/")
        current = self.spec
        
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return {}
        
        return self._resolve_schema(current) if isinstance(current, dict) else current
    
    def get_schema_fields(self, schema: dict, prefix: str = "") -> dict[str, dict]:
        """
        Flatten a schema into a dict of field paths to field info.
        
        Args:
            schema: Schema definition
            prefix: Current path prefix
            
        Returns:
            Dict mapping field paths to their type info
        """
        fields = {}
        
        if not schema:
            return fields
        
        schema_type = schema.get("type", "object")
        
        if schema_type == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            for prop_name, prop_schema in properties.items():
                field_path = f"{prefix}.{prop_name}" if prefix else prop_name
                prop_type = prop_schema.get("type", "any")
                
                fields[field_path] = {
                    "type": prop_type,
                    "required": prop_name in required,
                    "nullable": prop_schema.get("nullable", False),
                    "format": prop_schema.get("format"),
                }
                
                # Recurse into nested objects
                if prop_type == "object":
                    nested = self.get_schema_fields(prop_schema, field_path)
                    fields.update(nested)
                elif prop_type == "array" and "items" in prop_schema:
                    items_schema = prop_schema["items"]
                    if items_schema.get("type") == "object":
                        nested = self.get_schema_fields(items_schema, f"{field_path}[]")
                        fields.update(nested)
        
        elif schema_type == "array" and "items" in schema:
            items_fields = self.get_schema_fields(schema["items"], f"{prefix}[]")
            fields.update(items_fields)
        
        return fields
