#!/usr/bin/env python3
"""Convert this session's captured web.run declaration to a Responses tool."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent


def scalar(source):
    source = source.removesuffix(";")
    if source in {"string", "number", "boolean"}:
        return {"type": source}
    if source.startswith("Array<") and source.endswith(">"):
        return {"type": "array", "items": scalar(source[6:-1])}
    if re.fullmatch(r'"[^"]+"(?: \| "[^"]+")*', source):
        return {"type": "string", "enum": re.findall(r'"([^"]+)"', source)}
    raise ValueError(f"Unrecognized declaration type: {source}")


def parameters(declaration):
    """Parse the small declaration subset present in the captured source.

    Fail on unsupported syntax rather than silently changing the interface.
    Preserve optional fields, enum order, property order, and field comments.
    """
    body = declaration.split("web__run(args: {", 1)[1].split(
        "}): Promise<unknown>;", 1
    )[0]
    lines = iter(line.strip() for line in body.splitlines() if line.strip())

    def parse_object(nested=False):
        properties, required, description = {}, [], []
        for line in lines:
            if line == "}>;":
                if not nested or description:
                    raise ValueError("Unexpected object terminator")
                break
            if line.startswith("// "):
                description.append(line[3:])
                continue
            match = re.fullmatch(r"(\w+)(\?)?: (.+)", line)
            if not match:
                raise ValueError(f"Unrecognized declaration line: {line}")
            name, optional, kind = match.groups()
            field_description = " ".join(description)
            description = []
            if kind == "Array<{":
                schema = {"type": "array", "items": parse_object(nested=True)}
            else:
                schema = scalar(kind)
            if field_description:
                schema["description"] = field_description
            if name in properties:
                raise ValueError(f"Duplicate field: {name}")
            properties[name] = schema
            if not optional:
                required.append(name)
        else:
            if nested:
                raise ValueError("Unterminated object")
        if description:
            raise ValueError("Unattached field comment")
        return {"type": "object", "properties": properties,
                "required": required, "additionalProperties": False}

    result = parse_object()
    if next(lines, None) is not None:
        raise ValueError("Unparsed declaration content")
    return result


def build():
    source = (ROOT / "web-run.source.txt").read_text()
    prose, declaration = source.split("exec tool declaration:\n", 1)
    namespace_description, function_description = prose.split("\n\n", 1)
    return {
        "type": "namespace", "name": "web",
        "description": namespace_description,
        "tools": [{
            "type": "function", "name": "run",
            "description": function_description.rstrip(),
            # Strict mode would change optional fields to required fields.
            "strict": False, "parameters": parameters(declaration),
        }],
    }


if __name__ == "__main__":
    destination = ROOT / "web-run.tool.json"
    tool = build()
    destination.write_text(json.dumps(tool, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {destination}: {len(tool['tools'][0]['parameters']['properties'])} top-level fields")
