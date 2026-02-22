import uuid
from typing import Any, Dict, Optional, Union
from lxml import etree

from openpurse.models import PaymentMessage, Pacs008Message, Pain001Message


class XMLWriter:
    """
    A programmatic engine to compile OpenPurse data models into strict
    ISO 20022 XML formats (lxml byte streams).
    """

    def __init__(self, schema: str = "pacs.008.001.08"):
        """
        Initializes the XML Writer for a target ISO 20022 schema.
        
        Args:
            schema: The full ISO 20022 schema identifier (e.g., 'pacs.008.001.08').
        """
        self.schema = schema
        self.namespace = f"urn:iso:std:iso:20022:tech:xsd:{schema}"
        self.nsmap = {None: self.namespace}

    def to_xml(self, message: Union[PaymentMessage, Pacs008Message, Pain001Message]) -> bytes:
        """
        Parses the unified PaymentMessage model into a strict lxml tree map
        and returns the encoded byte string.
        """
        # Create Root Document
        document = etree.Element("Document", nsmap=self.nsmap)

        if "pacs.008" in self.schema:
            self._build_pacs008(document, message)
        elif "pain.001" in self.schema:
            self._build_pain001(document, message)
        else:
            raise NotImplementedError(f"XML generation for {self.schema} is not yet supported.")

        return etree.tostring(
            document,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        )

    def _build_pacs008(self, root: etree.Element, message: Union[PaymentMessage, Pacs008Message]):
        """Builds the FIToFICstmrCdtTrf node for a pacs.008 payload."""
        fi_to_fi = etree.SubElement(root, "FIToFICstmrCdtTrf")

        # Group Header
        grp_hdr = etree.SubElement(fi_to_fi, "GrpHdr")
        if message.message_id:
            msg_id = etree.SubElement(grp_hdr, "MsgId")
            msg_id.text = message.message_id
            
        if message.number_of_transactions is not None:
            nb_of_txs = etree.SubElement(grp_hdr, "NbOfTxs")
            nb_of_txs.text = str(message.number_of_transactions)

        # Settlement Info
        if getattr(message, "settlement_method", None):
            sttlm_inf = etree.SubElement(grp_hdr, "SttlmInf")
            sttlm_mtd = etree.SubElement(sttlm_inf, "SttlmMtd")
            sttlm_mtd.text = message.settlement_method
            
        # Instructing Agents
        if message.sender_bic:
            instg_agt = etree.SubElement(grp_hdr, "InstgAgt")
            fin_instn_id = etree.SubElement(instg_agt, "FinInstnId")
            bicfi = etree.SubElement(fin_instn_id, "BICFI")
            bicfi.text = message.sender_bic

        if message.receiver_bic:
            instd_agt = etree.SubElement(grp_hdr, "InstdAgt")
            fin_instn_id = etree.SubElement(instd_agt, "FinInstnId")
            bicfi = etree.SubElement(fin_instn_id, "BICFI")
            bicfi.text = message.receiver_bic

        # Credit Transfer Transaction Info
        tx_inf = etree.SubElement(fi_to_fi, "CdtTrfTxInf")
        pmt_id = etree.SubElement(tx_inf, "PmtId")

        if message.end_to_end_id:
            e2e_id = etree.SubElement(pmt_id, "EndToEndId")
            e2e_id.text = message.end_to_end_id

        if message.uetr:
            uetr_el = etree.SubElement(pmt_id, "UETR")
            uetr_el.text = message.uetr

        if message.amount:
            amt = etree.SubElement(tx_inf, "IntrBkSttlmAmt")
            amt.text = message.amount
            if message.currency:
                amt.set("Ccy", message.currency)

        # Debtor
        if message.debtor_name:
            dbtr = etree.SubElement(tx_inf, "Dbtr")
            nm = etree.SubElement(dbtr, "Nm")
            nm.text = message.debtor_name

            if message.debtor_address:
                self._build_postal_address(dbtr, message.debtor_address)

        # Creditor
        if message.creditor_name:
            cdtr = etree.SubElement(tx_inf, "Cdtr")
            nm = etree.SubElement(cdtr, "Nm")
            nm.text = message.creditor_name

            if message.creditor_address:
                self._build_postal_address(cdtr, message.creditor_address)


    def _build_pain001(self, root: etree.Element, message: Union[PaymentMessage, Pain001Message]):
        """Builds the CstmrCdtTrfInitn node for a pain.001 payload."""
        cstmr_cdt = etree.SubElement(root, "CstmrCdtTrfInitn")

        # GrpHdr
        grp_hdr = etree.SubElement(cstmr_cdt, "GrpHdr")
        if message.message_id:
            msg_id = etree.SubElement(grp_hdr, "MsgId")
            msg_id.text = message.message_id

        if getattr(message, "number_of_transactions", None) is not None:
            nb_of_txs = etree.SubElement(grp_hdr, "NbOfTxs")
            nb_of_txs.text = str(message.number_of_transactions)

        if getattr(message, "control_sum", None) is not None:
            ctrl_sum = etree.SubElement(grp_hdr, "CtrlSum")
            ctrl_sum.text = str(message.control_sum)

        if getattr(message, "initiating_party", None):
            initg_pty = etree.SubElement(grp_hdr, "InitgPty")
            nm = etree.SubElement(initg_pty, "Nm")
            nm.text = message.initiating_party

        # PmtInf
        pmt_inf = etree.SubElement(cstmr_cdt, "PmtInf")
        if message.end_to_end_id:
            pmt_inf_id = etree.SubElement(pmt_inf, "PmtInfId")
            pmt_inf_id.text = f"PMTINF-{message.end_to_end_id}"

        if message.debtor_name:
            dbtr = etree.SubElement(pmt_inf, "Dbtr")
            nm = etree.SubElement(dbtr, "Nm")
            nm.text = message.debtor_name
            if message.debtor_address:
                self._build_postal_address(dbtr, message.debtor_address)

        if message.debtor_account:
            dbtr_acct = etree.SubElement(pmt_inf, "DbtrAcct")
            id_node = etree.SubElement(dbtr_acct, "Id")
            iban_node = etree.SubElement(id_node, "IBAN")
            iban_node.text = message.debtor_account

        if message.sender_bic:
            dbtr_agt = etree.SubElement(pmt_inf, "DbtrAgt")
            fin_instn_id = etree.SubElement(dbtr_agt, "FinInstnId")
            bicfi = etree.SubElement(fin_instn_id, "BICFI")
            bicfi.text = message.sender_bic

        # CdtTrfTxInf
        tx_inf = etree.SubElement(pmt_inf, "CdtTrfTxInf")
        pmt_id = etree.SubElement(tx_inf, "PmtId")
        if message.end_to_end_id:
            e2e_id = etree.SubElement(pmt_id, "EndToEndId")
            e2e_id.text = message.end_to_end_id

        if message.amount:
            amt = etree.SubElement(tx_inf, "Amt")
            instd_amt = etree.SubElement(amt, "InstdAmt")
            instd_amt.text = message.amount
            if message.currency:
                instd_amt.set("Ccy", message.currency)

        if message.receiver_bic:
            cdtr_agt = etree.SubElement(tx_inf, "CdtrAgt")
            fin_instn_id = etree.SubElement(cdtr_agt, "FinInstnId")
            bicfi = etree.SubElement(fin_instn_id, "BICFI")
            bicfi.text = message.receiver_bic

        if message.creditor_name:
            cdtr = etree.SubElement(tx_inf, "Cdtr")
            nm = etree.SubElement(cdtr, "Nm")
            nm.text = message.creditor_name
            if message.creditor_address:
                self._build_postal_address(cdtr, message.creditor_address)

        if message.creditor_account:
            cdtr_acct = etree.SubElement(tx_inf, "CdtrAcct")
            id_node = etree.SubElement(cdtr_acct, "Id")
            iban_node = etree.SubElement(id_node, "IBAN")
            iban_node.text = message.creditor_account

    def _build_postal_address(self, parent: etree.Element, address: Any):
        """Builds a PstlAdr node."""
        pstl_adr = etree.SubElement(parent, "PstlAdr")

        if getattr(address, "country", None):
            ctry = etree.SubElement(pstl_adr, "Ctry")
            ctry.text = address.country

        if getattr(address, "town_name", None):
            twn = etree.SubElement(pstl_adr, "TwnNm")
            twn.text = address.town_name

        if getattr(address, "post_code", None):
            pst_cd = etree.SubElement(pstl_adr, "PstCd")
            pst_cd.text = address.post_code

        if getattr(address, "street_name", None):
            strt = etree.SubElement(pstl_adr, "StrtNm")
            strt.text = address.street_name

        if getattr(address, "building_number", None):
            bldg = etree.SubElement(pstl_adr, "BldgNb")
            bldg.text = address.building_number

        if getattr(address, "address_lines", None):
            for line in address.address_lines:
                adr_line = etree.SubElement(pstl_adr, "AdrLine")
                adr_line.text = line
