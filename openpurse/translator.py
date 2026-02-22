from openpurse.models import PaymentMessage
from datetime import datetime

class Translator:
    """
    Translates structurally parsed `PaymentMessage` objects back into raw 
    SWIFT MT or ISO 20022 MX (XML) format bytes.
    """

    @staticmethod
    def to_mt(message: PaymentMessage, mt_type: str = "103") -> bytes:
        """
        Translates a PaymentMessage into a SWIFT MT byte string.
        Currently supports MT103 block generation.
        """
        if mt_type not in ("103", "202", "900", "910", "940"):
            raise NotImplementedError(f"Translation to MT{mt_type} is not yet supported.")
            
        # Basic defaults
        sender = (message.sender_bic or "XXXXXXXXXXXX").ljust(12, 'X')[:12]
        receiver = (message.receiver_bic or "XXXXXXXXXXXX").ljust(12, 'X')[:12]
        
        # Block 1: {1:F01[Sender 12][Session 4][Seq 6]}
        block_1 = f"{{1:F01{sender}0000000000}}"
        
        # Block 2: {2:I[Type][Receiver 12]N}
        block_2 = f"{{2:I{mt_type}{receiver}N}}"
        
        # Block 4: Body
        msg_id = message.message_id or "NONREF"
        curr = message.currency or "USD"
        
        # Clean amount string to use comma for decimals (as per SWIFT MT standard)
        amt_str = message.amount or "0.00"
        if '.' in amt_str:
            amt_str = amt_str.replace('.', ',')
        else:
            amt_str += ','
            
        date_str = datetime.now().strftime("%y%m%d")
        
        if mt_type == "103":
            debtor = message.debtor_name or "N/A"
            creditor = message.creditor_name or "N/A"
            block_4 = (
                f"{{4:\n"
                f":20:{msg_id}\n"
                f":32A:{date_str}{curr}{amt_str}\n"
                f":50K:/{sender}\n"
                f"{debtor}\n"
                f":59:/{receiver}\n"
                f"{creditor}\n"
                f"-}}"
            )
        elif mt_type == "202":
            block_4 = (
                f"{{4:\n"
                f":20:{msg_id}\n"
                f":32A:{date_str}{curr}{amt_str}\n"
                f":58A:/{receiver}\n"
                f"-}}"
            )
        elif mt_type == "900":
            # Confirmation of Debit
            debtor = message.debtor_name or "N/A"
            block_4 = (
                f"{{4:\n"
                f":20:{msg_id}\n"
                f":52A:/{sender}\n"
                f"{debtor}\n"
                f":32A:{date_str}{curr}{amt_str}\n" # Value date, currency, amount
                f"-}}"
            )
        elif mt_type == "910":
            # Confirmation of Credit
            creditor = message.creditor_name or "N/A"
            block_4 = (
                f"{{4:\n"
                f":20:{msg_id}\n"
                f":52A:/{sender}\n"
                f"{creditor}\n"
                f":32A:{date_str}{curr}{amt_str}\n" 
                f"-}}"
            )
        elif mt_type == "940":
            # Customer Statement
            # Expecting a detailed message with entries (like Camt053Message). 
            # If not present, generate an empty block.
            statements_loop = ""
            open_bal = f":60F:C{date_str}{curr}{amt_str}"
            close_bal = f":62F:C{date_str}{curr}{amt_str}"
            
            if hasattr(message, 'entries') and isinstance(message.entries, list):
                for entry in message.entries:
                    e_amt = str(entry.get('amount', '0.00')).replace('.', ',')
                    e_cd = "C" if entry.get('credit_debit_indicator') == "CRDT" else "D"
                    e_ref = entry.get('reference', 'NONREF')
                    
                    # Construct an MT940 :61: statement line 
                    # Format: ValueDate[6]EntryDate[4]CR/DR[1]Amount[15]TransactionTypeAndIdentificationCode[4]ReferenceForTheAccountOwner[16]
                    statements_loop += f":61:{date_str}{date_str[2:]}{e_cd}{e_amt}NTRF{e_ref}\n"
                    
                    e_remit = entry.get('remittance')
                    if e_remit:
                        statements_loop += f":86:{e_remit}\n"
            
            block_4 = (
                f"{{4:\n"
                f":20:{msg_id}\n"
                f":25:/{sender}\n"
                f":28C:1/1\n"
                f"{open_bal}\n"
                f"{statements_loop}"
                f"{close_bal}\n"
                f"-}}"
            )
        
        return f"{block_1}{block_2}{block_4}".encode('utf-8')

    @staticmethod
    def to_mx(message: PaymentMessage, mx_type: str = "pacs.008") -> bytes:
        """
        Translates a PaymentMessage into an ISO 20022 MX (XML) byte string.
        Currently supports pacs.008, pacs.009, camt.054, and camt.053 mapped elements.
        """
        if mx_type not in ("pacs.008", "pacs.009", "camt.053", "camt.054", "camt.052", "camt.004"):
            raise NotImplementedError(f"Translation to {mx_type} is not yet supported.")
        # Common fields
        msg_id = message.message_id or "NONREF"
        e2e = message.end_to_end_id or msg_id
        amt = message.amount or "0.00"
        curr = message.currency or "USD"
        sender = message.sender_bic or "UNKNOWN"
        receiver = message.receiver_bic or "UNKNOWN"
        debtor = message.debtor_name or "UNKNOWN"
        creditor = message.creditor_name or "UNKNOWN"
        
        def _build_addr_xml(addr) -> str:
            if not addr:
                return ""
            inner = ""
            if getattr(addr, 'country', None): inner += f"<Ctry>{addr.country}</Ctry>"
            if getattr(addr, 'town_name', None): inner += f"<TwnNm>{addr.town_name}</TwnNm>"
            if getattr(addr, 'post_code', None): inner += f"<PstCd>{addr.post_code}</PstCd>"
            if getattr(addr, 'street_name', None): inner += f"<StrtNm>{addr.street_name}</StrtNm>"
            if getattr(addr, 'building_number', None): inner += f"<BldgNb>{addr.building_number}</BldgNb>"
            lines = getattr(addr, 'address_lines', None)
            if lines:
                for line in lines:
                    inner += f"<AdrLine>{line}</AdrLine>"
            
            return f"<PstlAdr>{inner}</PstlAdr>" if inner else ""

        dbtr_addr_xml = _build_addr_xml(getattr(message, 'debtor_address', None))
        cdtr_addr_xml = _build_addr_xml(getattr(message, 'creditor_address', None))
        
        xml_template = ""
        
        if mx_type == "pacs.008":
            xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:{mx_type}.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
            <InstgAgt><FinInstnId><BICFI>{sender}</BICFI></FinInstnId></InstgAgt>
            <InstdAgt><FinInstnId><BICFI>{receiver}</BICFI></FinInstnId></InstdAgt>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>{e2e}</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="{curr}">{amt}</IntrBkSttlmAmt>
            <Dbtr><Nm>{debtor}</Nm>{dbtr_addr_xml}</Dbtr>
            <Cdtr><Nm>{creditor}</Nm>{cdtr_addr_xml}</Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>"""
        
        elif mx_type == "pacs.009":
            # Financial Institution Credit Transfer (MT202 equivalent)
            xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.009.001.08">
    <FICdtTrf>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
            <InstgAgt><FinInstnId><BICFI>{sender}</BICFI></FinInstnId></InstgAgt>
            <InstdAgt><FinInstnId><BICFI>{receiver}</BICFI></FinInstnId></InstdAgt>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>{e2e}</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="{curr}">{amt}</IntrBkSttlmAmt>
            <Dbtr><FinInstnId><BICFI>{sender}</BICFI></FinInstnId></Dbtr>
            <Cdtr><FinInstnId><BICFI>{receiver}</BICFI></FinInstnId></Cdtr>
        </CdtTrfTxInf>
    </FICdtTrf>
</Document>"""

        elif mx_type == "camt.054":
            # Bank to Customer Debit/Credit Notification (MT900/MT910 equivalent)
            c_d_ind = "CRDT" if float(amt) > 0 else "DBIT"
            abs_amt = str(abs(float(amt)))
            
            xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.054.001.08">
    <BkToCstmrDbtCdtNtfctn>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
        </GrpHdr>
        <Ntfctn>
            <Id>{msg_id}-NTF</Id>
            <Acct>
                <Id><Othr><Id>{receiver}</Id></Othr></Id>
            </Acct>
            <Ntry>
                <Amt Ccy="{curr}">{abs_amt}</Amt>
                <CdtDbtInd>{c_d_ind}</CdtDbtInd>
                <Sts>BOOK</Sts>
                <NtryDtls>
                    <TxDtls>
                        <Refs><EndToEndId>{e2e}</EndToEndId></Refs>
                    </TxDtls>
                </NtryDtls>
            </Ntry>
        </Ntfctn>
    </BkToCstmrDbtCdtNtfctn>
</Document>"""

        elif mx_type == "camt.053":
            # Bank to Customer Statement (MT940 equivalent)
            entries_xml = ""
            if hasattr(message, 'entries') and isinstance(message.entries, list):
                for entry in message.entries:
                    e_amt = str(entry.get('amount', '0.00'))
                    e_cd = entry.get('credit_debit_indicator', 'CRDT')
                    e_ref = entry.get('reference', 'NONREF')
                    entries_xml += f"""
            <Ntry>
                <NtryRef>{e_ref}</NtryRef>
                <Amt Ccy="{curr}">{e_amt}</Amt>
                <CdtDbtInd>{e_cd}</CdtDbtInd>
                <Sts>BOOK</Sts>
                <BkTxCd><Prtry><Cd>NTRF</Cd></Prtry></BkTxCd>
            </Ntry>"""
            
            xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
    <BkToCstmrStmt>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
        </GrpHdr>
        <Stmt>
            <Id>{msg_id}-STMT</Id>
            <Acct>
                <Id><Othr><Id>{receiver}</Id></Othr></Id>
            </Acct>{entries_xml}
        </Stmt>
    </BkToCstmrStmt>
</Document>"""

        return xml_template.encode('utf-8')
