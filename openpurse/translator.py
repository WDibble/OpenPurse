import uuid
from datetime import datetime
from typing import Any

from openpurse.models import PaymentMessage


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
        if mt_type not in ("101", "103", "202", "900", "910", "940", "942", "950"):
            raise NotImplementedError(f"Translation to MT{mt_type} is not yet supported.")

        # Basic defaults
        sender = (message.sender_bic or "XXXXXXXXXXXX").ljust(12, "X")[:12]
        receiver = (message.receiver_bic or "XXXXXXXXXXXX").ljust(12, "X")[:12]

        # Block 1: {1:F01[Sender 12][Session 4][Seq 6]}
        block_1 = f"{{1:F01{sender}0000000000}}"

        # Block 2: {2:I[Type][Receiver 12]N}
        block_2 = f"{{2:I{mt_type}{receiver}N}}"

        # Block 3: {3:{121:[UUIDv4 UETR]}}
        msg_uetr = message.uetr or str(uuid.uuid4())
        block_3 = f"{{3:{{121:{msg_uetr}}}}}"

        # Block 4: Body
        msg_id, curr, amt_str, date_str = Translator._get_mt_common_fields(message)

        if mt_type == "101":
            block_4 = Translator._build_mt101_block4(
                message, msg_id, curr, amt_str, date_str, sender, receiver
            )
        elif mt_type == "103":
            block_4 = Translator._build_mt103_block4(
                message, msg_id, curr, amt_str, date_str, sender, receiver
            )
        elif mt_type == "202":
            block_4 = Translator._build_mt202_block4(msg_id, curr, amt_str, date_str, receiver)
        elif mt_type == "900":
            block_4 = Translator._build_mt900_block4(
                message, msg_id, curr, amt_str, date_str, sender
            )
        elif mt_type == "910":
            block_4 = Translator._build_mt910_block4(
                message, msg_id, curr, amt_str, date_str, sender
            )
        elif mt_type == "940":
            block_4 = Translator._build_mt940_block4(
                message, msg_id, curr, amt_str, date_str, sender
            )
        elif mt_type == "942":
            block_4 = Translator._build_mt942_block4(
                message, msg_id, curr, amt_str, date_str, sender
            )
        elif mt_type == "950":
            block_4 = Translator._build_mt950_block4(
                message, msg_id, curr, amt_str, date_str, sender
            )

        return f"{block_1}{block_2}{block_3}{block_4}".encode("utf-8")

    @staticmethod
    def _get_mt_common_fields(message: PaymentMessage) -> tuple[str, str, str, str]:
        msg_id = message.message_id or "NONREF"
        curr = message.currency or "USD"

        # Clean amount string to use comma for decimals (as per SWIFT MT standard)
        amt_str = message.amount or "0.00"
        if "." in amt_str:
            amt_str = amt_str.replace(".", ",")
        else:
            amt_str += ","

        date_str = datetime.now().strftime("%y%m%d")
        return msg_id, curr, amt_str, date_str

    @staticmethod
    def _build_mt101_block4(
        message: PaymentMessage,
        msg_id: str,
        curr: str,
        amt_str: str,
        date_str: str,
        sender: str,
        receiver: str,
    ) -> str:
        initiating_party = getattr(message, "initiating_party", "N/A")
        if not initiating_party:
            initiating_party = "N/A"

        block4 = (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":50H:/{sender}\n"
            f"{initiating_party}\n"
            f":30:{date_str}\n"
        )

        transactions = getattr(message, "payment_information", [])
        if not transactions:
            end_to_end = message.end_to_end_id or "NONREF"
            creditor = message.creditor_name or "N/A"
            block4 += (
                f":21:{end_to_end}\n" f":32B:{curr}{amt_str}\n" f":59:/{receiver}\n" f"{creditor}\n"
            )
        else:
            for tx in transactions:
                end_to_end = tx.get("end_to_end_id") or "NONREF"
                tx_amt = tx.get("amount") or "0.00"
                if "." in tx_amt:
                    tx_amt = tx_amt.replace(".", ",")
                else:
                    tx_amt += ","
                tx_curr = tx.get("currency") or curr
                creditor = tx.get("creditor_name") or "N/A"

                block4 += (
                    f":21:{end_to_end}\n"
                    f":32B:{tx_curr}{tx_amt}\n"
                    f":59:/{receiver}\n"
                    f"{creditor}\n"
                )

        block4 += "-}"
        return block4

    @staticmethod
    def _build_mt103_block4(
        message: PaymentMessage,
        msg_id: str,
        curr: str,
        amt_str: str,
        date_str: str,
        sender: str,
        receiver: str,
    ) -> str:
        debtor = message.debtor_name or "N/A"
        creditor = message.creditor_name or "N/A"
        return (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":32A:{date_str}{curr}{amt_str}\n"
            f":50K:/{sender}\n"
            f"{debtor}\n"
            f":59:/{receiver}\n"
            f"{creditor}\n"
            f"-}}"
        )

    @staticmethod
    def _build_mt202_block4(
        msg_id: str, curr: str, amt_str: str, date_str: str, receiver: str
    ) -> str:
        return (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":32A:{date_str}{curr}{amt_str}\n"
            f":58A:/{receiver}\n"
            f"-}}"
        )

    @staticmethod
    def _build_mt900_block4(
        message: PaymentMessage, msg_id: str, curr: str, amt_str: str, date_str: str, sender: str
    ) -> str:
        debtor = message.debtor_name or "N/A"
        return (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":52A:/{sender}\n"
            f"{debtor}\n"
            f":32A:{date_str}{curr}{amt_str}\n"  # Value date, currency, amount
            f"-}}"
        )

    @staticmethod
    def _build_mt910_block4(
        message: PaymentMessage, msg_id: str, curr: str, amt_str: str, date_str: str, sender: str
    ) -> str:
        creditor = message.creditor_name or "N/A"
        return (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":52A:/{sender}\n"
            f"{creditor}\n"
            f":32A:{date_str}{curr}{amt_str}\n"
            f"-}}"
        )

    @staticmethod
    def _build_mt940_block4(
        message: PaymentMessage, msg_id: str, curr: str, amt_str: str, date_str: str, sender: str
    ) -> str:
        statements_loop = ""
        open_bal = f":60F:C{date_str}{curr}{amt_str}"
        close_bal = f":62F:C{date_str}{curr}{amt_str}"

        if hasattr(message, "entries") and isinstance(message.entries, list):
            for entry in message.entries:
                e_amt = str(entry.get("amount", "0.00")).replace(".", ",")
                e_cd = "C" if entry.get("credit_debit_indicator") == "CRDT" else "D"
                e_ref = entry.get("reference", "NONREF")

                # Construct an MT940 :61: statement line
                # Format: ValueDate[6]EntryDate[4]CR/DR[1]Amount[15]...
                statements_loop += f":61:{date_str}{date_str[2:]}{e_cd}{e_amt}NTRF{e_ref}\n"

                e_remit = entry.get("remittance")
                if e_remit:
                    statements_loop += f":86:{e_remit}\n"

        return (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":25:/{sender}\n"
            f":28C:1/1\n"
            f"{open_bal}\n"
            f"{statements_loop}"
            f"{close_bal}\n"
            f"-}}"
        )

    @staticmethod
    def _build_mt942_block4(
        message: PaymentMessage, msg_id: str, curr: str, amt_str: str, date_str: str, sender: str
    ) -> str:
        statements_loop = ""
        interim_bal = f":34F:C{curr}{amt_str}"

        if hasattr(message, "entries") and isinstance(message.entries, list):
            for entry in message.entries:
                e_amt = str(entry.get("amount", "0.00")).replace(".", ",")
                e_cd = "C" if entry.get("credit_debit_indicator") == "CRDT" else "D"
                e_ref = entry.get("reference", "NONREF")

                statements_loop += f":61:{date_str}{date_str[2:]}{e_cd}{e_amt}NTRF{e_ref}\n"

                e_remit = entry.get("remittance")
                if e_remit:
                    statements_loop += f":86:{e_remit}\n"

        return (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":25:/{sender}\n"
            f"{interim_bal}\n"
            f"{statements_loop}"
            f"-}}"
        )

    @staticmethod
    def _build_mt950_block4(
        message: PaymentMessage, msg_id: str, curr: str, amt_str: str, date_str: str, sender: str
    ) -> str:
        statements_loop = ""
        open_bal = f":60F:C{date_str}{curr}{amt_str}"
        close_bal = f":62F:C{date_str}{curr}{amt_str}"

        if hasattr(message, "entries") and isinstance(message.entries, list):
            for entry in message.entries:
                e_amt = str(entry.get("amount", "0.00")).replace(".", ",")
                e_cd = "C" if entry.get("credit_debit_indicator") == "CRDT" else "D"
                e_ref = entry.get("reference", "NONREF")

                statements_loop += f":61:{date_str}{date_str[2:]}{e_cd}{e_amt}NTRF{e_ref}\n"

        return (
            f"{{4:\n"
            f":20:{msg_id}\n"
            f":25:/{sender}\n"
            f"{open_bal}\n"
            f"{statements_loop}"
            f"{close_bal}\n"
            f"-}}"
        )

    @staticmethod
    def to_mx(message: PaymentMessage, mx_type: str = "pacs.008") -> bytes:
        """
        Translates a PaymentMessage into an ISO 20022 MX (XML) byte string.
        Currently supports pacs.008, pacs.009, camt.054, and camt.053 mapped elements.
        """
        if mx_type not in ("pacs.008", "pacs.009", "camt.053", "camt.054", "camt.052", "camt.004"):
            raise NotImplementedError(f"Translation to {mx_type} is not yet supported.")

        # Common fields
        (msg_id, e2e, uetr, amt, curr, sender, receiver, debtor, creditor) = (
            Translator._get_mx_common_fields(message)
        )

        dbtr_addr_xml = Translator._build_addr_xml(getattr(message, "debtor_address", None))
        cdtr_addr_xml = Translator._build_addr_xml(getattr(message, "creditor_address", None))

        xml_template = ""

        if mx_type == "pacs.008":
            xml_template = Translator._build_mx_pacs008(
                msg_id,
                sender,
                receiver,
                e2e,
                uetr,
                curr,
                amt,
                debtor,
                dbtr_addr_xml,
                creditor,
                cdtr_addr_xml,
            )
        elif mx_type == "pacs.009":
            xml_template = Translator._build_mx_pacs009(
                msg_id, sender, receiver, e2e, uetr, curr, amt
            )
        elif mx_type == "camt.054":
            xml_template = Translator._build_mx_camt054(msg_id, receiver, curr, amt, e2e)
        elif mx_type == "camt.053":
            xml_template = Translator._build_mx_camt053(message, msg_id, receiver, curr, amt)

        return xml_template.encode("utf-8")

    @staticmethod
    def _get_mx_common_fields(message: PaymentMessage) -> tuple[str, str, str, str, str, str, str, str, str]:
        msg_id = message.message_id or "NONREF"
        e2e = message.end_to_end_id or msg_id

        # UETR is strongly associated with the E2E block in XML
        # (often right beside it, e.g. <UETR> UUID </UETR>)
        uetr = message.uetr or str(uuid.uuid4())

        amt = message.amount or "0.00"
        curr = message.currency or "USD"
        sender = message.sender_bic or "UNKNOWN"
        receiver = message.receiver_bic or "UNKNOWN"
        debtor = message.debtor_name or "UNKNOWN"
        creditor = message.creditor_name or "UNKNOWN"
        return msg_id, e2e, uetr, amt, curr, sender, receiver, debtor, creditor

    @staticmethod
    def _build_addr_xml(addr: Any) -> str:
        if not addr:
            return ""
        inner = ""
        if getattr(addr, "country", None):
            inner += f"<Ctry>{addr.country}</Ctry>"
        if getattr(addr, "town_name", None):
            inner += f"<TwnNm>{addr.town_name}</TwnNm>"
        if getattr(addr, "post_code", None):
            inner += f"<PstCd>{addr.post_code}</PstCd>"
        if getattr(addr, "street_name", None):
            inner += f"<StrtNm>{addr.street_name}</StrtNm>"
        if getattr(addr, "building_number", None):
            inner += f"<BldgNb>{addr.building_number}</BldgNb>"
        lines = getattr(addr, "address_lines", None)
        if lines:
            for line in lines:
                inner += f"<AdrLine>{line}</AdrLine>"

        return f"<PstlAdr>{inner}</PstlAdr>" if inner else ""

    @staticmethod
    def _build_mx_pacs008(
        msg_id: str,
        sender: str,
        receiver: str,
        e2e: str,
        uetr: str,
        curr: str,
        amt: str,
        debtor: str,
        dbtr_addr_xml: str,
        creditor: str,
        cdtr_addr_xml: str,
    ) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
            <InstgAgt><FinInstnId><BICFI>{sender}</BICFI></FinInstnId></InstgAgt>
            <InstdAgt><FinInstnId><BICFI>{receiver}</BICFI></FinInstnId></InstdAgt>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>{e2e}</EndToEndId>
                <UETR>{uetr}</UETR>
            </PmtId>
            <IntrBkSttlmAmt Ccy="{curr}">{amt}</IntrBkSttlmAmt>
            <Dbtr><Nm>{debtor}</Nm>{dbtr_addr_xml}</Dbtr>
            <Cdtr><Nm>{creditor}</Nm>{cdtr_addr_xml}</Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>"""

    @staticmethod
    def _build_mx_pacs009(msg_id: str, sender: str, receiver: str, e2e: str, uetr: str, curr: str, amt: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.009.001.08">
    <FICdtTrf>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
            <InstgAgt><FinInstnId><BICFI>{sender}</BICFI></FinInstnId></InstgAgt>
            <InstdAgt><FinInstnId><BICFI>{receiver}</BICFI></FinInstnId></InstdAgt>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>{e2e}</EndToEndId>
                <UETR>{uetr}</UETR>
            </PmtId>
            <IntrBkSttlmAmt Ccy="{curr}">{amt}</IntrBkSttlmAmt>
            <Dbtr><FinInstnId><BICFI>{sender}</BICFI></FinInstnId></Dbtr>
            <Cdtr><FinInstnId><BICFI>{receiver}</BICFI></FinInstnId></Cdtr>
        </CdtTrfTxInf>
    </FICdtTrf>
</Document>"""

    @staticmethod
    def _build_mx_camt054(msg_id: str, receiver: str, curr: str, amt: str, e2e: str) -> str:
        c_d_ind = "CRDT" if float(amt) > 0 else "DBIT"
        abs_amt = str(abs(float(amt)))

        return f"""<?xml version="1.0" encoding="UTF-8"?>
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

    @staticmethod
    def _build_mx_camt053(message: PaymentMessage, msg_id: str, receiver: str, curr: str, amt: str) -> str:
        entries_xml = ""
        if hasattr(message, "entries") and isinstance(message.entries, list):
            for entry in message.entries:
                e_amt = str(entry.get("amount", "0.00"))
                e_cd = entry.get("credit_debit_indicator", "CRDT")
                e_ref = entry.get("reference", "NONREF")
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

        return xml_template
