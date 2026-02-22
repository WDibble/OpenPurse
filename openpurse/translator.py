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
        if mt_type != "103":
            raise NotImplementedError(f"Translation to MT{mt_type} is not yet supported.")
            
        # Basic defaults
        sender = (message.sender_bic or "XXXXXXXXXXXX").ljust(12, 'X')[:12]
        receiver = (message.receiver_bic or "XXXXXXXXXXXX").ljust(12, 'X')[:12]
        
        # Block 1: {1:F01[Sender 12][Session 4][Seq 6]}
        block_1 = f"{{1:F01{sender}0000000000}}"
        
        # Block 2: {2:I103[Receiver 12]N}
        block_2 = f"{{2:I103{receiver}N}}"
        
        # Block 4: Body
        msg_id = message.message_id or "NONREF"
        curr = message.currency or "USD"
        amt = (message.amount or "0.00").replace(".", ",")
        date_str = datetime.now().strftime("%y%m%d")
        
        debtor = message.debtor_name or "N/A"
        creditor = message.creditor_name or "N/A"
        
        block_4 = (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":32A:{date_str}{curr}{amt}\n"
            f":50K:/{sender}\n"
            f"{debtor}\n"
            f":59:/{receiver}\n"
            f"{creditor}\n"
            f"-}}"
        )
        
        return f"{block_1}{block_2}{block_4}".encode('utf-8')

    @staticmethod
    def to_mx(message: PaymentMessage, mx_type: str = "pacs.008") -> bytes:
        """
        Translates a PaymentMessage into an ISO 20022 MX (XML) byte string.
        Currently supports pacs.008 mapped elements.
        """
        if mx_type not in ("pacs.008", "camt.052", "camt.004"):
            raise NotImplementedError(f"Translation to {mx_type} is not yet supported.")
            
        msg_id = message.message_id or "NONREF"
        e2e = message.end_to_end_id or msg_id
        amt = message.amount or "0.00"
        curr = message.currency or "USD"
        sender = message.sender_bic or "UNKNOWN"
        receiver = message.receiver_bic or "UNKNOWN"
        debtor = message.debtor_name or "UNKNOWN"
        creditor = message.creditor_name or "UNKNOWN"
        
        # Basic pacs.008 structure wrapper mapped to the standard output format
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
            <Dbtr><Nm>{debtor}</Nm></Dbtr>
            <Cdtr><Nm>{creditor}</Nm></Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>"""

        return xml_template.encode('utf-8')
