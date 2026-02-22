from typing import Any, Callable, Type, Union
from fastapi import Request, HTTPException, Depends
from openpurse.parser import OpenPurseParser
from openpurse.validator import Validator
from openpurse.integrations.pydantic import from_dataclass, PydanticPaymentMessage

async def get_openpurse_message(request: Request) -> PydanticPaymentMessage:
    """
    FastAPI dependency that parses an incoming XML or MT payload 
    and returns a validated Pydantic model.
    """
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty payload")

    # 1. Pre-validate schema if it's XML
    report = Validator.validate_schema(body)
    if not report.is_valid:
        raise HTTPException(
            status_code=422, 
            detail={"message": "Schema validation failed", "errors": report.errors}
        )

    # 2. Parse payload
    parser = OpenPurseParser(body)
    try:
        msg = parser.parse_detailed()
        
        # 3. Logical validation
        logic_report = Validator.validate(msg)
        if not logic_report.is_valid:
            raise HTTPException(
                status_code=422,
                detail={"message": "Logic validation failed", "errors": logic_report.errors}
            )
            
        return from_dataclass(msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parsing failed: {str(e)}")
