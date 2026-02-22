
from openpurse.parser import OpenPurseParser
from openpurse.models import Setr004Message, Setr010Message

# A precise slice of a SETR.004 payload
MOCK_SETR_004 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:setr.004.001.04">
    <RedOrdr>
        <MsgId>
            <Id>MSG-RED-8899</Id>
            <CreDtTm>2023-11-06T14:32:00Z</CreDtTm>
        </MsgId>
        <PoolRef>
            <Ref>POOL-009</Ref>
        </PoolRef>
        <MltplOrdrDtls>
            <MstrRef>MSTR-RED-8899</MstrRef>
            <IndvOrdrDtls>
                <OrdrRef>ORD-8899-1</OrdrRef>
                <InvstmtAcctDtls>
                    <AcctId>ACCT-12345</AcctId>
                </InvstmtAcctDtls>
                <FinInstrmDtls>
                    <Id>
                        <ISIN>US0378331005</ISIN>
                    </Id>
                </FinInstrmDtls>
                <OrdrQty>
                    <UnitQty>150.5</UnitQty>
                </OrdrQty>
            </IndvOrdrDtls>
            <IndvOrdrDtls>
                <OrdrRef>ORD-8899-2</OrdrRef>
                <InvstmtAcctDtls>
                    <AcctId>ACCT-67890</AcctId>
                </InvstmtAcctDtls>
                <FinInstrmDtls>
                    <Id>
                        <ISIN>US5949181045</ISIN>
                    </Id>
                </FinInstrmDtls>
                <OrdrQty>
                    <AmtdQty Ccy="USD">50000.00</AmtdQty>
                </OrdrQty>
            </IndvOrdrDtls>
        </MltplOrdrDtls>
    </RedOrdr>
</Document>"""

# A precise slice of a SETR.010 payload
MOCK_SETR_010 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:setr.010.001.04">
    <SbcptOrdr>
        <MsgId>
            <Id>MSG-SUB-7766</Id>
            <CreDtTm>2023-11-07T09:15:00Z</CreDtTm>
        </MsgId>
        <PoolRef>
            <Ref>POOL-SUB-001</Ref>
        </PoolRef>
        <MltplOrdrDtls>
            <MstrRef>MSTR-SUB-7766</MstrRef>
            <IndvOrdrDtls>
                <OrdrRef>ORD-SUB-7766-1</OrdrRef>
                <InvstmtAcctDtls>
                    <AcctId>ACCT-99999</AcctId>
                </InvstmtAcctDtls>
                <FinInstrmDtls>
                    <Id>
                        <ISIN>US9026811099</ISIN>
                    </Id>
                </FinInstrmDtls>
                <OrdrQty>
                    <AmtdQty Ccy="EUR">25000.00</AmtdQty>
                </OrdrQty>
            </IndvOrdrDtls>
        </MltplOrdrDtls>
    </SbcptOrdr>
</Document>"""


def test_parse_detailed_setr_004():
    parser = OpenPurseParser(MOCK_SETR_004)
    msg = parser.parse_detailed()

    assert isinstance(msg, Setr004Message)
    assert msg.master_reference == "MSTR-RED-8899"
    assert msg.pool_reference == "POOL-009"
    assert len(msg.orders) == 2

    # Order 1 Checks
    assert msg.orders[0]["order_reference"] == "ORD-8899-1"
    assert msg.orders[0]["investment_account_id"] == "ACCT-12345"
    assert msg.orders[0]["financial_instrument_id"] == "US0378331005"
    assert msg.orders[0]["units"] == "150.5"
    assert msg.orders[0]["amount"] is None

    # Order 2 Checks
    assert msg.orders[1]["order_reference"] == "ORD-8899-2"
    assert msg.orders[1]["investment_account_id"] == "ACCT-67890"
    assert msg.orders[1]["financial_instrument_id"] == "US5949181045"
    assert msg.orders[1]["units"] is None
    assert msg.orders[1]["amount"] == "50000.00"
    assert msg.orders[1]["currency"] == "USD"


def test_parse_detailed_setr_010():
    parser = OpenPurseParser(MOCK_SETR_010)
    msg = parser.parse_detailed()

    assert isinstance(msg, Setr010Message)
    assert msg.master_reference == "MSTR-SUB-7766"
    assert msg.pool_reference == "POOL-SUB-001"
    assert len(msg.orders) == 1

    # Order 1 Checks
    assert msg.orders[0]["order_reference"] == "ORD-SUB-7766-1"
    assert msg.orders[0]["investment_account_id"] == "ACCT-99999"
    assert msg.orders[0]["financial_instrument_id"] == "US9026811099"
    assert msg.orders[0]["amount"] == "25000.00"
    assert msg.orders[0]["currency"] == "EUR"
    assert msg.orders[0]["units"] is None

if __name__ == "__main__":
    test_parse_detailed_setr_004()
    test_parse_detailed_setr_010()
    print("All tests passed! 🚀")
