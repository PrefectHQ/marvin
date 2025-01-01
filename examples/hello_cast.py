from typing import Literal

import marvin
from pydantic import BaseModel, Field


class AllergyFormatA(BaseModel):
    substance: str = Field(description="Name of the allergic substance")
    severity: str = Field(description="Severity level (mild, moderate, severe)")
    reaction: str = Field(description="Type of allergic reaction")
    dateIdentified: str = Field(description="Date allergy was identified (YYYY-MM-DD)")


class AllergyFormatB(BaseModel):
    agent: str = Field(description="Name of the allergic substance")
    riskLevel: Literal["low", "medium", "high"] = Field(description="Risk level")
    manifestations: list[str] = Field(
        description="List of observed reactions", alias="clinicalManifestations"
    )
    documentation_date: str = Field(
        description="Date allergy was documented (YYYY-MM-DD)",
        alias="documentationDate",
    )


if __name__ == "__main__":
    allergy_record_a = AllergyFormatA(
        substance="penicillin",
        severity="severe",
        reaction="anaphylaxis",
        dateIdentified="2020-01-01",
    )

    allergy_record_b = marvin.cast(
        allergy_record_a,
        AllergyFormatB,
        instructions="Convert Epic allergy record to Cerner format. Map 'severe' severity to 'high' risk. Format reaction as a list.",
    )
    print(f"Converted to format B: {allergy_record_b}")
"""
» python examples/hello_cast.py
╭─ Marvin ─────────────────────────────────────────────────────────────────────────────────────────╮
│ ⠋   Final Result                                                                                 │
│     Input:   {                                                                                   │
│                'response': {                                                                     │
│                  'task_id': '895be677-29f6-4642-ac99-d63171a46444',                              │
│                  'result': {                                                                     │
│                    'agent': 'penicillin',                                                        │
│                    'riskLevel': 'high',                                                          │
│                    'clinicalManifestations': [                                                   │
│                      'anaphylaxis'                                                               │
│                    ],                                                                            │
│                    'documentationDate': '2020-01-01'                                             │
│                  }                                                                               │
│                }                                                                                 │
│              }                                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────── 12:23:47 AM ─╯
Converted to format B: agent='penicillin' riskLevel='high' manifestations=['anaphylaxis'] documentation_date='2020-01-01'
"""
