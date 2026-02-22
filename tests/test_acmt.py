
from openpurse.parser import OpenPurseParser
from openpurse.models import Acmt007Message, Acmt015Message

MOCK_ACMT_007 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:acmt.007.001.05">
    <AcctOpngReq>
        <Refs>
            <MsgId><Id>MSG-111</Id><CreDtTm>2023-11-06T14:32:00Z</CreDtTm></MsgId>
            <PrcId><Id>PRC-777</Id><CreDtTm>2023-11-06T14:32:00Z</CreDtTm></PrcId>
        </Refs>
        <Acct>
            <Id><Othr><Id>ACC-123</Id></Othr></Id>
            <Ccy>USD</Ccy>
        </Acct>
        <AcctSvcrId>
            <FinInstnId>
                <BICFI>BANKDEF</BICFI>
            </FinInstnId>
            <BrnchId><Nm>Downtown Branch</Nm></BrnchId>
        </AcctSvcrId>
        <Org>
            <FullLglNm>Acme Corp</FullLglNm>
            <CtryOfOpr>US</CtryOfOpr>
            <LglAdr></LglAdr>
            <OrgId></OrgId>
        </Org>
    </AcctOpngReq>
</Document>"""

MOCK_ACMT_015 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:acmt.015.001.04">
    <AcctExcldMndtMntncReq>
        <Refs>
            <MsgId><Id>MSG-222</Id><CreDtTm>2023-11-06T14:32:00Z</CreDtTm></MsgId>
            <PrcId><Id>PRC-888</Id><CreDtTm>2023-11-06T14:32:00Z</CreDtTm></PrcId>
        </Refs>
        <Acct>
            <Id><IBAN>AA11222233334444555566667777</IBAN></Id>
            <Ccy>EUR</Ccy>
        </Acct>
        <AcctSvcrId>
            <FinInstnId>
                <BICFI>BANKABC</BICFI>
            </FinInstnId>
            <BrnchId><Nm>Uptown Branch</Nm></BrnchId>
        </AcctSvcrId>
        <Org>
            <FullLglNm><FullLglNm>Globex Inc</FullLglNm></FullLglNm>
            <CtryOfOpr>UK</CtryOfOpr>
            <LglAdr></LglAdr>
            <OrgId></OrgId>
        </Org>
    </AcctExcldMndtMntncReq>
</Document>"""


def test_parse_detailed_acmt_007():
    parser = OpenPurseParser(MOCK_ACMT_007)
    msg = parser.parse_detailed()

    assert isinstance(msg, Acmt007Message)
    assert msg.process_id == "PRC-777"
    assert msg.account_id == "ACC-123"
    assert msg.account_currency == "USD"
    assert msg.organization_name == "Acme Corp"
    assert msg.branch_name == "Downtown Branch"


def test_parse_detailed_acmt_015():
    parser = OpenPurseParser(MOCK_ACMT_015)
    msg = parser.parse_detailed()

    assert isinstance(msg, Acmt015Message)
    assert msg.process_id == "PRC-888"
    assert msg.account_id == "AA11222233334444555566667777"
    assert msg.organization_name == "Globex Inc"
    assert msg.branch_name == "Uptown Branch"


if __name__ == "__main__":
    test_parse_detailed_acmt_007()
    test_parse_detailed_acmt_015()
    print("ACMT Tests passed! 🚀")
