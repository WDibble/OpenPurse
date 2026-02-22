import pytest
from openpurse.parser import OpenPurseParser
from openpurse.models import Sese023Message


def test_parse_sese_023_securities_settlement():
    """Test extracting detailed fields from a SESE.023 Securities Settlement Transaction Instruction."""
    xml_data = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:sese.023.001.09">
        <SctiesSttlmTxInstr>
            <TxId>TRAD12345</TxId>
            <TradDtls>
                <TradDt>
                    <Dt>
                        <Dt>2023-10-15</Dt>
                    </Dt>
                </TradDt>
                <SttlmDt>
                    <Dt>
                        <Dt>2023-10-18</Dt>
                    </Dt>
                </SttlmDt>
            </TradDtls>
            <FinInstrmId>
                <ISIN>US0378331005</ISIN>
                <Desc>Apple Inc. Common Stock</Desc>
            </FinInstrmId>
            <QtyAndAcctDtls>
                <SttlmQty>
                    <Qty>
                        <Unit>1000</Unit>
                    </Qty>
                </SttlmQty>
            </QtyAndAcctDtls>
            <SttlmAmt>
                <Amt>
                    <Amt Ccy="USD">175000.00</Amt>
                </Amt>
            </SttlmAmt>
            <DlvrgSttlmPties>
                <Pty1>
                    <Id>
                        <AnyBIC>CHASUS33</AnyBIC>
                    </Id>
                </Pty1>
            </DlvrgSttlmPties>
            <RcvgSttlmPties>
                <Pty1>
                    <Id>
                        <NmAndAdr>
                            <Nm>Vanguard Group</Nm>
                        </NmAndAdr>
                    </Id>
                </Pty1>
            </RcvgSttlmPties>
        </SctiesSttlmTxInstr>
    </Document>
    """
    
    parser = OpenPurseParser(xml_data)
    parsed = parser.parse_detailed()
    
    assert isinstance(parsed, Sese023Message)
    assert parsed.trade_date == "2023-10-15"
    assert parsed.settlement_date == "2023-10-18"
    assert parsed.security_id == "US0378331005"
    assert parsed.security_quantity == "1000"
    assert parsed.security_quantity_type == "Unit"
    assert parsed.settlement_amount == "175000.00"
    assert parsed.settlement_currency == "USD"
    assert parsed.delivering_agent == "CHASUS33"
    assert parsed.receiving_agent == "Vanguard Group"
