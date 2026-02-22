import pytest
import io
import os
from openpurse.streaming import StreamingParser
from openpurse.models import PaymentMessage

def test_streaming_pacs008_batch():
    """
    Tests that the streaming parser can iterate through multiple transactions 
    in a pacs.008 batch file without loading the entire tree.
    """
    # Create a batch pacs.008 with 3 transactions
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>BATCH_001</MsgId>
            <CreDtTm>2026-02-22T22:00:00</CreDtTm>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>TX_1</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="USD">100.00</IntrBkSttlmAmt>
            <Dbtr><Nm>Sender 1</Nm></Dbtr>
            <Cdtr><Nm>Receiver 1</Nm></Cdtr>
        </CdtTrfTxInf>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>TX_2</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="EUR">200.00</IntrBkSttlmAmt>
            <Dbtr><Nm>Sender 2</Nm></Dbtr>
            <Cdtr><Nm>Receiver 2</Nm></Cdtr>
        </CdtTrfTxInf>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>TX_3</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="GBP">300.00</IntrBkSttlmAmt>
            <Dbtr><Nm>Sender 3</Nm></Dbtr>
            <Cdtr><Nm>Receiver 3</Nm></Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""
    parser = StreamingParser(xml_content)
    messages = list(parser.iter_messages())
    
    assert len(messages) == 3
    assert all(isinstance(m, PaymentMessage) for m in messages)
    
    assert messages[0].end_to_end_id == "TX_1"
    assert messages[0].amount == "100.00"
    assert messages[0].currency == "USD"
    
    assert messages[1].end_to_end_id == "TX_2"
    assert messages[1].amount == "200.00"
    assert messages[1].currency == "EUR"
    
    assert messages[2].end_to_end_id == "TX_3"
    assert messages[2].amount == "300.00"
    assert messages[2].currency == "GBP"

def test_streaming_camt054_entries():
    """
    Tests streaming for camt.054 Bank-to-Customer Debit/Credit Notification entries.
    """
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.054.001.08">
    <BkToCstmrDbtCdtNtfctn>
        <Ntfctn>
            <Id>NTF_1</Id>
            <Ntry>
                <Amt Ccy="USD">50.00</Amt>
                <CdtDbtInd>DBIT</CdtDbtInd>
                <NtryDtls>
                    <TxDtls>
                        <Refs><EndToEndId>REF_1</EndToEndId></Refs>
                        <RltdPties><Dbtr><Nm>User A</Nm></Dbtr></RltdPties>
                    </TxDtls>
                </NtryDtls>
            </Ntry>
            <Ntry>
                <Amt Ccy="USD">75.50</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <NtryDtls>
                    <TxDtls>
                        <Refs><EndToEndId>REF_2</EndToEndId></Refs>
                        <RltdPties><Cdtr><Nm>User B</Nm></Cdtr></RltdPties>
                    </TxDtls>
                </NtryDtls>
            </Ntry>
        </Ntfctn>
    </BkToCstmrDbtCdtNtfctn>
</Document>
"""
    parser = StreamingParser(xml_content)
    messages = list(parser.iter_messages())
    
    assert len(messages) == 2
    assert messages[0].end_to_end_id == "REF_1"
    assert messages[0].amount == "50.00"
    
    assert messages[1].end_to_end_id == "REF_2"
    assert messages[1].amount == "75.50"

def test_streaming_empty_file():
    """
    Tests that an empty file yields no messages.
    """
    parser = StreamingParser(b"")
    messages = list(parser.iter_messages())
    assert len(messages) == 0

def test_streaming_large_file_simulation():
    """
    Simulates a larger file by generating many transactions and iterating through them.
    This verifies that the iterator pattern holds for repeated elements.
    """
    tx_count = 100
    tx_template = """
        <CdtTrfTxInf>
            <PmtId><EndToEndId>TX_{i}</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="USD">{amount}.00</IntrBkSttlmAmt>
        </CdtTrfTxInf>"""
    
    xml_start = b'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><FIToFICstmrCdtTrf>'
    xml_end = b'</FIToFICstmrCdtTrf></Document>'
    
    # We use a generator to simulate streaming even for the source if needed, 
    # but here we just build a somewhat large bytes object.
    txs = b"".join([tx_template.format(i=i, amount=i+1).encode() for i in range(tx_count)])
    full_xml = xml_start + txs + xml_end
    
    parser = StreamingParser(full_xml)
    count = 0
    for i, msg in enumerate(parser.iter_messages()):
        assert msg.end_to_end_id == f"TX_{i}"
        assert msg.amount == f"{i+1}.00"
        count += 1
    
    assert count == tx_count
