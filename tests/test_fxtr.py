import pytest
from openpurse.parser import OpenPurseParser
from openpurse.models import Fxtr014Message


def test_parse_fxtr_014_foreign_exchange_trade():
    """Test extracting detailed fields from an FXTR.014 Foreign Exchange Trade Instruction."""
    xml_data = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:fxtr.014.001.06">
        <FXTradInstr>
            <TradInf>
                <TradDt>2023-11-01</TradDt>
                <OrgtrRef>FX-102938</OrgtrRef>
            </TradInf>
            <TradgSdId>
                <SubmitgPty>
                    <AnyBIC>
                        <AnyBIC>CITIUS33</AnyBIC>
                    </AnyBIC>
                </SubmitgPty>
            </TradgSdId>
            <CtrPtySdId>
                <SubmitgPty>
                    <NmAndAdr>
                        <Nm>DEUTSCHE BANK AG</Nm>
                    </NmAndAdr>
                </SubmitgPty>
            </CtrPtySdId>
            <TradAmts>
                <TradgSdBuyAmt>
                    <Amt Ccy="EUR">1500000.00</Amt>
                </TradgSdBuyAmt>
                <TradgSdSellAmt>
                    <Amt Ccy="USD">1650000.00</Amt>
                </TradgSdSellAmt>
                <SttlmDt>2023-11-03</SttlmDt>
            </TradAmts>
            <AgrdRate>
                <XchgRate>1.1000</XchgRate>
            </AgrdRate>
        </FXTradInstr>
    </Document>
    """
    
    parser = OpenPurseParser(xml_data)
    parsed = parser.parse_detailed()
    
    assert isinstance(parsed, Fxtr014Message)
    assert parsed.trade_date == "2023-11-01"
    assert parsed.settlement_date == "2023-11-03"
    assert parsed.trading_party == "CITIUS33"  # or AnyBIC
    assert parsed.counterparty == "DEUTSCHE BANK AG"
    assert parsed.exchange_rate == "1.1000"
    assert parsed.traded_amount == "1500000.00"
    assert parsed.traded_currency == "EUR"

def test_fxtr_edge_cases():
    missing_doc = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:fxtr.014.001.06">
        <FXTradInstr>
            <TradAmts></TradAmts>
        </FXTradInstr>
    </Document>
    """
    parser = OpenPurseParser(missing_doc)
    parsed = parser.parse_detailed()
    assert isinstance(parsed, Fxtr014Message)
    assert parsed.trade_date is None
    assert parsed.trading_party is None
    assert parsed.counterparty is None
    assert parsed.exchange_rate is None
    assert parsed.traded_amount is None
    assert parsed.traded_currency is None

if __name__ == "__main__":
    test_parse_fxtr_014_foreign_exchange_trade()
    test_fxtr_edge_cases()
    print("FXTR Tests passed! 🚀")
