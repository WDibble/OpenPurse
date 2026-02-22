import glob
import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

from lxml import etree

from openpurse.models import (
    Camt004Message,
    Camt029Message,
    Camt052Message,
    Camt053Message,
    Camt054Message,
    Camt056Message,
    Pacs008Message,
    Pain001Message,
    Pain002Message,
    Pain008Message,
    PaymentMessage,
    Fxtr014Message,
    Sese023Message,
    Pacs004Message,
    Pacs009Message,
    Setr004Message,
    Setr010Message,
    Acmt007Message,
    Acmt015Message,
    Camt086Message,
    PostalAddress,
)

if TYPE_CHECKING:
    from openpurse.models import ValidationReport


class OpenPurseParser:
    """
    Core parser for flattening ISO 20022 XML messages.
    Dynamically maps supported XSD schemas from the docs/ folder.
    """

    _SUPPORTED_NAMESPACES: Set[str] = set()  # Legacy backwards compatibility
    _SCHEMA_REGISTRY: Dict[str, str] = {}  # New mapping of targetNamespace -> filepath
    _SCHEMAS_LOADED = False

    @classmethod
    def _load_namespaces(cls) -> None:
        if cls._SCHEMAS_LOADED:
            return

        # 1. Search in local app schemas (preferred for distribution)
        internal_schemas = os.path.join(os.path.dirname(__file__), "schemas")
        
        # 2. Search in docs directory (legacy/development location)
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        if not os.path.exists(docs_dir):
            docs_dir = "docs/"  # fallback

        all_dirs = [internal_schemas, docs_dir]
        
        for base_dir in all_dirs:
            if not os.path.exists(base_dir):
                continue
                
            xsds = glob.glob(f"{base_dir}/**/*.xsd", recursive=True)
            for xsd in xsds:
                try:
                    # We use string manipulation to find targetNamespace to avoid full parsing overhead if large
                    with open(xsd, "r", encoding="utf-8") as f:
                        # Read more to ensure we catch targetNamespace even in large headers
                        content = f.read(2048)
                        if 'targetNamespace="' in content:
                            ns = content.split('targetNamespace="')[1].split('"')[0]
                            cls._SUPPORTED_NAMESPACES.add(ns)
                            # internal schemas override docs (if duplicates exist)
                            cls._SCHEMA_REGISTRY[ns] = os.path.abspath(xsd)
                except Exception:
                    pass

        cls._SCHEMAS_LOADED = True

    def __init__(self, message_data: bytes):
        OpenPurseParser._load_namespaces()
        self.message_data = message_data.strip()
        self.is_mt = self.message_data.startswith(b"{1:")

        self.tree = None
        self.ns = {}
        self.bah_data: Dict[str, Optional[str]] = {}

        if not self.is_mt:
            try:
                self.tree = etree.fromstring(self.message_data)
                self.nsmap = self.tree.nsmap

                # Extract default namespace if exists
                self.default_ns = (
                    self.nsmap.get(None)
                    if self.nsmap.get(None)
                    else (self.nsmap[list(self.nsmap.keys())[0]] if self.nsmap else None)
                )

                if self.default_ns:
                    self.ns = {"ns": self.default_ns}

                # --- BAH (head.001) Integration ---
                # Detect if the root is a BAH or a wrapper containing a BAH
                is_bah = "head.001" in (self.default_ns or "")
                app_hdr_nodes = self.tree.xpath(".//*[local-name()='AppHdr']")

                if is_bah or app_hdr_nodes:
                    app_hdr = (
                        self.tree
                        if is_bah and self.tree.tag.endswith("AppHdr")
                        else (app_hdr_nodes[0] if app_hdr_nodes else None)
                    )
                    if app_hdr is not None:
                        self.bah_data = self._parse_bah(app_hdr)

                    # Pivot context to the Document if it exists
                    doc_nodes = self.tree.xpath(".//*[local-name()='Document']")
                    if doc_nodes:
                        self.tree = doc_nodes[0]
                        self.nsmap = self.tree.nsmap
                        self.default_ns = self.nsmap.get(None)
                        if self.default_ns:
                            self.ns = {"ns": self.default_ns}
                        else:
                            self.ns = {}

            except (etree.XMLSyntaxError, ValueError, TypeError):
                self.tree = None

    def _parse_bah(self, app_hdr: Any) -> Dict[str, Optional[str]]:
        """
        Extracts core routing information from an ISO 20022 Business Application Header.
        """

        def find_text(xpath: str) -> Optional[str]:
            res = app_hdr.xpath(xpath)
            if res:
                if isinstance(res[0], str):
                    return res[0].strip()
                return res[0].text.strip() if hasattr(res[0], "text") and res[0].text else None
            return None

        # Optimized explicitly defined paths to prevent O(N) full tree scanning
        return {
            "sender_bic": find_text("./*[local-name()='Fr']/*[local-name()='FIId']/*[local-name()='FinInstnId']/*[local-name()='BICFI']/text()"),
            "receiver_bic": find_text("./*[local-name()='To']/*[local-name()='FIId']/*[local-name()='FinInstnId']/*[local-name()='BICFI']/text()"),
            "message_id": find_text("./*[local-name()='BizMsgIdr']/text()"),
        }

    def validate_schema(self) -> "ValidationReport":
        """
        Performs strict structural validation of the initialized XML message against
        its authoritative XSD schema registered from the docs/ directory.

        Returns:
            ValidationReport: A report indicating `is_valid` status and a list of specific XSD validation errors.
        """
        from openpurse.models import ValidationReport

        if self.is_mt:
            return ValidationReport(
                is_valid=False,
                errors=["Schema validation is not applicable to SWIFT MT block formats."],
            )

        if self.tree is None:
            return ValidationReport(
                is_valid=False,
                errors=[
                    "Empty or fundamentally malformed XML document. Cannot determine namespace."
                ],
            )

        if not self.default_ns:
            return ValidationReport(
                is_valid=False, errors=["Document is missing a defined targetNamespace."]
            )

        xsd_path = self._SCHEMA_REGISTRY.get(self.default_ns)
        if not xsd_path:
            return ValidationReport(
                is_valid=False,
                errors=[
                    f"Unsupported namespace '{self.default_ns}'. No matching XSD found in registry."
                ],
            )

        try:
            with open(xsd_path, "rb") as f:
                schema_root = etree.XML(f.read())
                schema = etree.XMLSchema(schema_root)

            if schema.validate(self.tree):
                return ValidationReport(is_valid=True, errors=[])
            else:
                errors = [str(err) for err in schema.error_log]
                return ValidationReport(is_valid=False, errors=errors)

        except etree.XMLSchemaParseError as e:
            return ValidationReport(
                is_valid=False,
                errors=[f"Internal Error: Failed to parse registered XSD '{xsd_path}': {e}"],
            )
        except Exception as e:
            return ValidationReport(
                is_valid=False, errors=[f"Unexpected error validating schema: {e}"]
            )

    def _get_text_from(self, element: Any, xpath_expr: str) -> Optional[str]:
        if element is None:
            return None

        try:
            if not self.default_ns:
                xpath_expr = xpath_expr.replace("ns:", "")
                result = element.xpath(xpath_expr)
            else:
                result = element.xpath(xpath_expr, namespaces=self.ns)
            return result[0].strip() if result else None
        except IndexError:
            return None

    def _get_text(self, xpath_expr: str) -> Optional[str]:
        if self.tree is None:
            return None
        try:
            if not self.default_ns:
                xpath_expr = xpath_expr.replace("ns:", "")
                el = self.tree.xpath(xpath_expr)
            else:
                el = self.tree.xpath(xpath_expr, namespaces=self.ns)

            if el:
                # If the result of xpath is a string (like from /text() or /@attr), return it directly
                if isinstance(el[0], str):
                    return el[0].strip()
                # Otherwise if it's an element, get text
                text_val = el[0].text if hasattr(el[0], "text") else str(el[0])
                return text_val.strip() if text_val else None
            return None
        except Exception:
            return None

    def _parse_mt(self) -> PaymentMessage:
        """
        Parses SWIFT MT format (like MT103, MT202).
        """
        import re

        text = self.message_data.decode("utf-8", errors="ignore")

        # Helper to extract from tags like :20:
        def extract_tag(tag: str) -> Optional[str]:
            # Match from the tag until the next tag (newline followed by colon and 2-3 alphanumeric chars and a colon) or the end block '-'
            # We must use DOTALL and we MUST ensure it matches across newlines for things like :50K:
            match = re.search(
                rf"^{tag}(.*?)(?=\r?\n:[0-9A-Z]{{2,3}}:|\r?\n-|\Z)", text, re.MULTILINE | re.DOTALL
            )
            return match.group(1).strip() if match else None

        # 1. Header parsing (Sender / Receiver BIC)
        # Block 1 Basic Header: {1:F01<BIC12><Session4><Seq6>}
        # MT Sender BICs are typically 12 characters, but can occasionally be 14.
        sender = None
        
        # Extract 12 to 14 characters for the Sender BIC, trimming trailing zero-padding if present.
        b1_match = re.search(r"\{1:F01([A-Z0-9]{12,14})", text)
        if b1_match:
            sender = b1_match.group(1)[:14]
            if sender.endswith("00"):
                sender = sender[:-2]

        # Fallback extract for 8-14 chars avoiding sequence numbers
        b1_match = re.search(r"\{1:F01([A-Z0-9]{8,14}?)(?=[0-9]{10}\})", text)
        if b1_match:
            sender = b1_match.group(1)
        else:  # fallback
            b1_match2 = re.search(r"\{1:F01([A-Z0-9]{8,14})", text)
            if b1_match2:
                sender = b1_match2.group(1)[:12]

        # Block 2: {2:I103[Receiver BIC 12 chars]...} or O format
        # receiver BIC is 12 chars, followed by message priority 'N', 'U', 'S'.
        receiver = None
        mt_type = None
        b2_match = re.search(r"\{2:[IO]([0-9]{3})([A-Z0-9]{12})", text)
        if b2_match:
            mt_type = b2_match.group(1)
            receiver = b2_match.group(2)
        else:
            b2_match2 = re.search(r"\{2:[IO]([0-9]{3})([A-Z0-9]{8,14})", text)
            if b2_match2:
                mt_type = b2_match2.group(1)
                receiver = b2_match2.group(2)[:12]

        # Block 3: {3:{121:[UUIDv4 UETR]}}
        uetr = None
        b3_match = re.search(r"\{3:.*\{121:(.*?)\}.*?\}", text)
        if b3_match:
            uetr = b3_match.group(1).strip()

        # 2. Body parsing
        msg_id = extract_tag(":20:")

        if mt_type == "101":
            from openpurse.models import Pain001Message

            initiating_party = extract_tag(":50H:") or extract_tag(":50C:") or extract_tag(":50L:")
            if initiating_party and "\\n" in initiating_party:
                initiating_party = initiating_party.replace("\\n", " ")

            transactions = []
            amount = None
            currency = None

            tag_32b = extract_tag(":32B:")
            if tag_32b and len(tag_32b) >= 3:
                currency = tag_32b[:3]
                amount = tag_32b[3:].replace(",", ".")

            end_to_end_id = extract_tag(":21:")
            creditor_name = extract_tag(":59:") or extract_tag(":59A:")
            if creditor_name and "\\n" in creditor_name:
                creditor_name = creditor_name.replace("\\n", " ")

            tx_info = {
                "end_to_end_id": end_to_end_id,
                "amount": amount,
                "currency": currency,
                "creditor_name": creditor_name,
            }
            if end_to_end_id or amount or creditor_name:
                transactions.append(tx_info)

            return Pain001Message(
                message_id=msg_id,
                end_to_end_id=None,
                uetr=uetr,
                amount=amount,
                currency=currency,
                sender_bic=sender,
                receiver_bic=receiver,
                initiating_party=initiating_party,
                payment_information=transactions,
                number_of_transactions=len(transactions),
            )

        if mt_type in ("940", "942", "950"):
            from openpurse.models import Camt052Message, Camt053Message

            account_id = extract_tag(":25:")

            entries = []
            block4_match = re.search(r"\{4:(.*?)-}", text, re.DOTALL)
            if block4_match:
                b4_text = block4_match.group(1)

                # Extract all tag-value pairs
                tag_matches = re.finditer(
                    r"\n:([0-9]{2}[A-Z]?):(.*?)(?=\n:[0-9]{2}[A-Z]?:|\n-\Z|\n-\})",
                    "\n" + b4_text.strip() + "\n-}",
                    re.DOTALL,
                )

                current_entry = None
                for m in tag_matches:
                    tag = m.group(1)
                    val = m.group(2).strip()

                    if tag == "61":
                        if current_entry:
                            entries.append(current_entry)

                        cd_match = re.search(r"([A-Z]{1,2})([0-9]+,[0-9]*)", val)
                        cd_ind = "CRDT"
                        amount_str = "0.00"
                        ref = "NONREF"
                        if cd_match:
                            cd_str = cd_match.group(1)
                            amt_str = cd_match.group(2)
                            if "D" in cd_str:
                                cd_ind = "DBIT"
                            amount_str = amt_str.replace(",", ".")

                            rest = val[cd_match.end() :]
                            if len(rest) >= 4 and rest[:4].isalpha():
                                ref = rest[4:]
                            else:
                                ref = rest

                        current_entry = {
                            "amount": amount_str,
                            "credit_debit_indicator": cd_ind,
                            "reference": ref,
                        }
                    elif tag == "86" and current_entry:
                        current_entry["remittance"] = val.replace("\n", " ")

                if current_entry:
                    entries.append(current_entry)

            if mt_type in ("942",):
                return Camt052Message(
                    message_id=msg_id,
                    account_id=account_id,
                    entries=entries,
                    sender_bic=sender,
                    receiver_bic=receiver,
                )
            else:
                return Camt053Message(
                    message_id=msg_id,
                    account_id=account_id,
                    entries=entries,
                    sender_bic=sender,
                    receiver_bic=receiver,
                )

        amount = None
        currency = None
        tag_32a = extract_tag(":32A:")
        if tag_32a:
            # Format: YYMMDD(3 letter Currency)(Amount with comma decimal)
            # Example: 231024USD1000,50
            if len(tag_32a) >= 9:
                currency = tag_32a[6:9]
                amount = tag_32a[9:].replace(",", ".")

        # Debtor Name (Ordering Customer 50K or 50A)
        debtor = extract_tag(":50K:") or extract_tag(":50A:")
        # Creditor Name (Beneficiary 59 or 59A)
        creditor = extract_tag(":59:") or extract_tag(":59A:")

        if debtor and "\\n" in debtor:
            debtor = debtor.replace("\\n", " ")
        if creditor and "\\n" in creditor:
            creditor = creditor.replace("\\n", " ")

        return PaymentMessage(
            message_id=msg_id,
            end_to_end_id=None,
            uetr=uetr,
            amount=amount,
            currency=currency,
            sender_bic=sender,
            receiver_bic=receiver,
            debtor_name=debtor,
            creditor_name=creditor,
        )

    def parse(self) -> PaymentMessage:
        """
        Parses the XML or MT tree and returns a fully typed PaymentMessage dataclass.
        """
        if self.is_mt:
            return self._parse_mt()

        if self.tree is None:
            return PaymentMessage()

        dbtr_el = self._get_nodes("//ns:Dbtr")
        cdtr_el = self._get_nodes("//ns:Cdtr")

        debtor_address = self._parse_address(dbtr_el[0]) if dbtr_el else None
        creditor_address = self._parse_address(cdtr_el[0]) if cdtr_el else None

        return PaymentMessage(
            message_id=self._get_text("//ns:MsgId/text()") or self.bah_data.get("message_id"),
            end_to_end_id=self._get_text("//ns:EndToEndId/text()"),
            uetr=self._get_text("//ns:UETR/text()"),
            amount=self._get_text("//*[@Ccy][1]/text()"),
            currency=self._get_text("//*[@Ccy][1]/@Ccy"),
            sender_bic=self._get_text(
                "//ns:InstgAgt//ns:BICFI/text() | //ns:InitgPty//ns:AnyBIC/text() | //ns:DbtrAgt//ns:BICFI/text() | //ns:InstgAgt//ns:Othr/ns:Id/text()"
            )
            or self.bah_data.get("sender_bic"),
            receiver_bic=self._get_text(
                "//ns:InstdAgt//ns:BICFI/text() | //ns:CdtrAgt//ns:BICFI/text() | //ns:Svcr//ns:BICFI/text()"
            )
            or self.bah_data.get("receiver_bic"),
            debtor_name=self._get_text("//ns:Dbtr/ns:Nm/text()"),
            creditor_name=self._get_text("//ns:Cdtr/ns:Nm/text()"),
            debtor_address=debtor_address,
            creditor_address=creditor_address,
            debtor_account=self._get_text(
                "//ns:DbtrAcct/ns:Id/ns:IBAN/text() | //ns:DbtrAcct/ns:Id/ns:Othr/ns:Id/text()"
            ),
            creditor_account=self._get_text(
                "//ns:CdtrAcct/ns:Id/ns:IBAN/text() | //ns:CdtrAcct/ns:Id/ns:Othr/ns:Id/text()"
            ),
        )

    def _get_nodes(self, xpath_expr: str) -> list:
        if self.tree is None:
            return []
        if not self.default_ns:
            xpath_expr = xpath_expr.replace("ns:", "")
            return self.tree.xpath(xpath_expr)
        return self.tree.xpath(xpath_expr, namespaces=self.ns)

    def _get_nodes_from(self, element: Any, xpath_expr: str) -> list:
        if element is None:
            return []
        if not self.default_ns:
            xpath_expr = xpath_expr.replace("ns:", "")
            return element.xpath(xpath_expr)
        return element.xpath(xpath_expr, namespaces=self.ns)

    def _parse_address(self, parent_element: Any) -> Optional[PostalAddress]:
        """
        Safely extracts an ISO-compliant PostalAddress block from a parent node (e.g. Dbtr, Cdtr).
        """
        if parent_element is None:
            return None

        addr_nodes = self._get_nodes_from(parent_element, "./ns:PstlAdr")
        if not addr_nodes:
            return None

        adr_el = addr_nodes[0]

        country = self._get_text_from(adr_el, "./ns:Ctry/text()")
        town_name = self._get_text_from(adr_el, "./ns:TwnNm/text()")
        post_code = self._get_text_from(adr_el, "./ns:PstCd/text()")
        street_name = self._get_text_from(adr_el, "./ns:StrtNm/text()")
        building_number = self._get_text_from(adr_el, "./ns:BldgNb/text()")

        address_lines = []
        for line_el in self._get_nodes_from(adr_el, "./ns:AdrLine"):
            line_text = line_el.text.strip() if line_el.text else None
            if line_text:
                address_lines.append(line_text)

        # Return a PostalAddress only if at least one field contains data
        if any([country, town_name, post_code, street_name, building_number, address_lines]):
            return PostalAddress(
                country=country,
                town_name=town_name,
                post_code=post_code,
                street_name=street_name,
                building_number=building_number,
                address_lines=address_lines if address_lines else None,
            )

        return None

    def parse_detailed(self) -> PaymentMessage:
        """
        Extracts message data into an exhaustive, strictly-typed Python dataclass
        specific to the document's schema (e.g. Camt054Message, Pacs008Message, Camt004Message).

        If the schema does not have a detailed model, returns the base PaymentMessage.
        """
        if self.is_mt:
            return self.parse()

        ns_str = self.default_ns or ""

        # Fallback for XMLs missing namespace attributes
        if not ns_str and self.tree is not None and len(self.tree) > 0:
            root_tag = self.tree[0].tag
            if "}" in root_tag:
                root_tag = root_tag.split("}", 1)[1]
            tag_mapping = {
                "CstmrPmtStsRpt": "pain.002",
                "CstmrCdtTrfInitn": "pain.001",
                "CstmrDrctDbtInitn": "pain.008",
                "BkToCstmrAcctRpt": "camt.052",
                "BkToCstmrStmt": "camt.053",
                "BkToCstmrDbtCdtNtfctn": "camt.054",
                "FIToFICstmrCdtTrf": "pacs.008",
                "RtrAcct": "camt.004",
                "FXTradInstr": "fxtr.014",
                "SctiesSttlmTxInstr": "sese.023",
                "PmtRtr": "pacs.004",
                "FICdtTrf": "pacs.009",
                "RedOrdr": "setr.004",
                "SbcptOrdr": "setr.010",
                "AcctOpngReq": "acmt.007",
                "AcctExcldMndtMntncReq": "acmt.015",
                "BkSrvcsBllgStmt": "camt.086",
            }
            ns_str = tag_mapping.get(root_tag, "")

        base_msg = self.parse()

        if "camt.054" in ns_str:
            return self._parse_camt054_detailed(base_msg)
        elif "pacs.008" in ns_str:
            return self._parse_pacs008_detailed(base_msg)
        elif "camt.004" in ns_str:
            return self._parse_camt004_detailed(base_msg)
        elif "camt.052" in ns_str or "camt.053" in ns_str:
            return self._parse_camt05X_detailed(base_msg, ns_str)
        elif "pain.001" in ns_str or "pain.008" in ns_str:
            return self._parse_pain00X_detailed(base_msg, ns_str)
        elif "pain.002" in ns_str:
            return self._parse_pain002_detailed(base_msg)

        # Fallback to base
        if "camt.056" in ns_str:
            return self._parse_camt056()

        if "camt.029" in ns_str:
            return self._parse_camt029()

        if "fxtr.014" in ns_str:
            return self._parse_fxtr014(base_msg)

        if "sese.023" in ns_str:
            return self._parse_sese023(base_msg)

        if "pacs.004" in ns_str:
            return self._parse_pacs004(base_msg)

        if "pacs.009" in ns_str:
            return self._parse_pacs009(base_msg)

        if "setr.004" in ns_str:
            return self._parse_setr004(base_msg)

        if "setr.010" in ns_str:
            return self._parse_setr010(base_msg)

        if "acmt.007" in ns_str:
            return self._parse_acmt007(base_msg)

        if "acmt.015" in ns_str:
            return self._parse_acmt015(base_msg)

        if "camt.086" in ns_str:
            return self._parse_camt086(base_msg)

        return base_msg

    def _parse_camt054_detailed(self, base_msg: PaymentMessage) -> Camt054Message:
        entries = []
        for entry_el in self._get_nodes("//ns:Ntry"):
            entry = {
                "reference": self._get_text_from(entry_el, "./ns:NtryRef/text()"),
                "amount": self._get_text_from(entry_el, "./ns:Amt/text()"),
                "currency": self._get_text_from(entry_el, "./ns:Amt/@Ccy"),
                "credit_debit_indicator": self._get_text_from(entry_el, "./ns:CdtDbtInd/text()"),
                "status": self._get_text_from(entry_el, "./ns:Sts/text()"),
                "booking_date": self._get_text_from(
                    entry_el, "./ns:BookgDt/ns:Dt/text() | ./ns:BookgDt/ns:DtTm/text()"
                ),
                "value_date": self._get_text_from(
                    entry_el, "./ns:ValDt/ns:Dt/text() | ./ns:ValDt/ns:DtTm/text()"
                ),
                "bank_transaction_code": self._get_text_from(
                    entry_el,
                    "./ns:BkTxCd/ns:Domn/ns:Fmly/ns:SubFmlyCd/text() | ./ns:BkTxCd/ns:Prtry/ns:Cd/text()",
                ),
                "debtor": self._get_text_from(entry_el, ".//ns:Dbtr/ns:Nm/text()"),
                "creditor": self._get_text_from(entry_el, ".//ns:Cdtr/ns:Nm/text()"),
                "remittance": self._get_text_from(entry_el, ".//ns:RmtInf/ns:Ustrd/text()"),
            }
            entries.append(entry)

        c_entries = self._get_text("//ns:TtlCdtNtries/ns:NbOfNtries/text()")
        d_entries = self._get_text("//ns:TtlDbtNtries/ns:NbOfNtries/text()")

        return Camt054Message(
            **base_msg.to_dict(),
            creation_date_time=self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            notification_id=self._get_text("//ns:Ntfctn/ns:Id/text()"),
            account_id=self._get_text(
                "//ns:Acct/ns:Id/ns:Othr/ns:Id/text() | //ns:Acct/ns:Id/ns:IBAN/text()"
            ),
            account_currency=self._get_text("//ns:Acct/ns:Ccy/text()"),
            account_owner=self._get_text(
                "//ns:Acct/ns:Ownr/ns:Nm/text() | //ns:Acct/ns:Ownr/ns:Id//ns:Id/text()"
            ),
            account_servicer=self._get_text(
                "//ns:Acct/ns:Svcr/ns:FinInstnId/ns:BICFI/text() | //ns:Acct/ns:Svcr/ns:FinInstnId/ns:BIC/text()"
            ),
            total_credit_entries=int(c_entries) if c_entries else None,
            total_credit_amount=self._get_text("//ns:TtlCdtNtries/ns:Sum/text()"),
            total_debit_entries=int(d_entries) if d_entries else None,
            total_debit_amount=self._get_text("//ns:TtlDbtNtries/ns:Sum/text()"),
            entries=entries,
        )

    def _parse_pacs008_detailed(self, base_msg: PaymentMessage) -> Pacs008Message:
        transactions = []
        for tx_el in self._get_nodes("//ns:CdtTrfTxInf"):
            tx = {
                "instruction_id": self._get_text_from(tx_el, "./ns:PmtId/ns:InstrId/text()"),
                "end_to_end_id": self._get_text_from(tx_el, "./ns:PmtId/ns:EndToEndId/text()"),
                "transaction_id": self._get_text_from(tx_el, "./ns:PmtId/ns:TxId/text()"),
                "instructed_amount": self._get_text_from(tx_el, "./ns:InstdAmt/text()"),
                "instructed_currency": self._get_text_from(tx_el, "./ns:InstdAmt/@Ccy"),
                "charge_bearer": self._get_text_from(tx_el, "./ns:ChrgBr/text()"),
                "debtor_name": self._get_text_from(tx_el, "./ns:Dbtr/ns:Nm/text()"),
                "debtor_account": self._get_text_from(
                    tx_el,
                    "./ns:DbtrAcct/ns:Id/ns:IBAN/text() | ./ns:DbtrAcct/ns:Id/ns:Othr/ns:Id/text()",
                ),
                "debtor_address": self._parse_address(
                    self._get_nodes_from(tx_el, "./ns:Dbtr")[0]
                    if self._get_nodes_from(tx_el, "./ns:Dbtr")
                    else None
                ),
                "creditor_name": self._get_text_from(tx_el, "./ns:Cdtr/ns:Nm/text()"),
                "creditor_account": self._get_text_from(
                    tx_el,
                    "./ns:CdtrAcct/ns:Id/ns:IBAN/text() | ./ns:CdtrAcct/ns:Id/ns:Othr/ns:Id/text()",
                ),
                "creditor_address": self._parse_address(
                    self._get_nodes_from(tx_el, "./ns:Cdtr")[0]
                    if self._get_nodes_from(tx_el, "./ns:Cdtr")
                    else None
                ),
                "purpose": self._get_text_from(tx_el, "./ns:Purp/ns:Cd/text()"),
                "remittance_info": self._get_text_from(tx_el, "./ns:RmtInf/ns:Ustrd/text()"),
            }
            transactions.append(tx)

        nb_of_txs = self._get_text("//ns:GrpHdr/ns:NbOfTxs/text()")

        return Pacs008Message(
            **base_msg.to_dict(),
            settlement_method=self._get_text("//ns:GrpHdr/ns:SttlmInf/ns:SttlmMtd/text()"),
            clearing_system=self._get_text(
                "//ns:GrpHdr/ns:SttlmInf/ns:ClrSys/ns:Cd/text() | //ns:GrpHdr/ns:SttlmInf/ns:ClrSys/ns:Prtry/text()"
            ),
            number_of_transactions=int(nb_of_txs) if nb_of_txs else None,
            settlement_amount=self._get_text(
                "//ns:GrpHdr/ns:CtrlSum/text() | //ns:GrpHdr/ns:TtlIntrBkSttlmAmt/text()"
            ),
            settlement_currency=self._get_text("//ns:GrpHdr/ns:TtlIntrBkSttlmAmt/@Ccy"),
            transactions=transactions,
        )

    def _parse_camt004_detailed(self, base_msg: PaymentMessage) -> Camt004Message:
        balances = []
        limits = []
        errors = []

        for bal_el in self._get_nodes("//ns:MulBal | //ns:Bal"):
            bal = {
                "type": self._get_text_from(
                    bal_el, "./ns:Tp/ns:Cd/text() | ./ns:Tp/ns:CdOrPrtry/ns:Cd/text()"
                ),
                "amount": self._get_text_from(bal_el, "./ns:Amt/text()"),
                "currency": self._get_text_from(bal_el, "./ns:Amt/@Ccy"),
                "credit_debit_indicator": self._get_text_from(bal_el, "./ns:CdtDbtInd/text()"),
                "value_date": self._get_text_from(
                    bal_el, "./ns:ValDt/ns:Dt/text() | ./ns:ValDt/ns:DtTm/text()"
                ),
            }
            balances.append(bal)

        for err_el in self._get_nodes("//ns:BizErr | //ns:OprlErr"):
            error = {
                "code": self._get_text_from(
                    err_el, "./ns:Err/ns:Cd/text() | ./ns:Err/ns:Prtry/text()"
                ),
                "description": self._get_text_from(err_el, "./ns:Desc/text()"),
            }
            errors.append(error)

        for limit_el in self._get_nodes("//ns:CurBilLmt | //ns:CurMulLmt | //ns:Lmt"):
            limit = {
                "amount": self._get_text_from(
                    limit_el,
                    "./ns:LmtAmt/ns:AmtWthCcy/text() | ./ns:Amt/ns:AmtWthCcy/text() | ./ns:Amt/text()",
                ),
                "currency": self._get_text_from(
                    limit_el,
                    "./ns:LmtAmt/ns:AmtWthCcy/@Ccy | ./ns:Amt/ns:AmtWthCcy/@Ccy | ./ns:Amt/@Ccy",
                ),
                "credit_debit_indicator": self._get_text_from(limit_el, "./ns:CdtDbtInd/text()"),
            }
            limits.append(limit)

        return Camt004Message(
            **base_msg.to_dict(),
            creation_date_time=self._get_text("//ns:MsgHdr/ns:CreDtTm/text()"),
            original_business_query=self._get_text("//ns:MsgHdr/ns:OrgnlBizQry/ns:MsgId/text()"),
            account_id=self._get_text(
                "//ns:AcctId/ns:IBAN/text() | //ns:AcctId/ns:Othr/ns:Id/text() | //ns:Acct/ns:Id/ns:IBAN/text() | //ns:Acct/ns:Id/ns:Othr/ns:Id/text()"
            ),
            account_owner=self._get_text(
                "//ns:Acct/ns:Ownr/ns:Nm/text() | //ns:Acct/ns:Ownr/ns:Id//ns:Id/text() | //ns:Ownr/ns:Nm/text()"
            ),
            account_servicer=self._get_text(
                "//ns:Svcr/ns:FinInstnId/ns:BICFI/text() | //ns:Svcr/ns:FinInstnId/ns:BIC/text() | //ns:Acct/ns:Svcr/ns:FinInstnId/ns:BICFI/text()"
            ),
            account_status=self._get_text("//ns:Acct/ns:Sts/text() | //ns:Sts/text()"),
            account_currency=self._get_text("//ns:Acct/ns:Ccy/text() | //ns:Ccy/text()"),
            balances=balances,
            limits=limits,
            business_errors=errors,
            number_of_payments=self._get_text(
                "//ns:NbOfPmts/text() | //ns:Acct/ns:NbOfPmts/text()"
            ),
        )

    def _parse_camt05X_detailed(self, base_msg: PaymentMessage, ns_str: str) -> PaymentMessage:
        entries = []
        balances = []
        for entry_el in self._get_nodes("//ns:Ntry"):
            entry = {
                "reference": self._get_text_from(entry_el, "./ns:NtryRef/text()"),
                "amount": self._get_text_from(entry_el, "./ns:Amt/text()"),
                "currency": self._get_text_from(entry_el, "./ns:Amt/@Ccy"),
                "credit_debit_indicator": self._get_text_from(entry_el, "./ns:CdtDbtInd/text()"),
                "status": self._get_text_from(entry_el, "./ns:Sts/text()"),
                "booking_date": self._get_text_from(
                    entry_el, "./ns:BookgDt/ns:Dt/text() | ./ns:BookgDt/ns:DtTm/text()"
                ),
                "value_date": self._get_text_from(
                    entry_el, "./ns:ValDt/ns:Dt/text() | ./ns:ValDt/ns:DtTm/text()"
                ),
                "bank_transaction_code": self._get_text_from(
                    entry_el,
                    "./ns:BkTxCd/ns:Domn/ns:Fmly/ns:SubFmlyCd/text() | ./ns:BkTxCd/ns:Prtry/ns:Cd/text()",
                ),
                "debtor": self._get_text_from(entry_el, ".//ns:Dbtr/ns:Nm/text()"),
                "creditor": self._get_text_from(entry_el, ".//ns:Cdtr/ns:Nm/text()"),
                "remittance": self._get_text_from(
                    entry_el,
                    ".//ns:RmtInf/ns:Strd/ns:RfrdDocInf/ns:Nb/text() | .//ns:RmtInf/ns:Ustrd/text()",
                ),
            }
            entries.append(entry)

        for bal_el in self._get_nodes("//ns:Bal"):
            bal = {
                "type": self._get_text_from(
                    bal_el,
                    "./ns:Tp/ns:CdOrPrtry/ns:Cd/text() | ./ns:Tp/ns:CdOrPrtry/ns:Prtry/text()",
                ),
                "amount": self._get_text_from(bal_el, "./ns:Amt/text()"),
                "currency": self._get_text_from(bal_el, "./ns:Amt/@Ccy"),
                "credit_debit_indicator": self._get_text_from(bal_el, "./ns:CdtDbtInd/text()"),
                "date": self._get_text_from(
                    bal_el, "./ns:Dt/ns:Dt/text() | ./ns:Dt/ns:DtTm/text()"
                ),
            }
            balances.append(bal)

        c_entries = self._get_text("//ns:TxsSummry/ns:TtlCdtNtries/ns:NbOfNtries/text()")
        d_entries = self._get_text("//ns:TxsSummry/ns:TtlDbtNtries/ns:NbOfNtries/text()")

        kwargs = {
            **base_msg.to_dict(),
            "creation_date_time": self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            "account_id": self._get_text(
                "//ns:Acct/ns:Id/ns:Othr/ns:Id/text() | //ns:Acct/ns:Id/ns:IBAN/text()"
            ),
            "account_currency": self._get_text("//ns:Acct/ns:Ccy/text()"),
            "account_owner": self._get_text(
                "//ns:Acct/ns:Ownr/ns:Id//ns:Id/text() | //ns:Acct/ns:Ownr/ns:Nm/text()"
            ),
            "account_servicer": self._get_text(
                "//ns:Acct/ns:Svcr/ns:FinInstnId/ns:BIC/text() | //ns:Acct/ns:Svcr/ns:FinInstnId/ns:BICFI/text()"
            ),
            "total_credit_entries": int(c_entries) if c_entries else None,
            "total_credit_amount": self._get_text("//ns:TxsSummry/ns:TtlCdtNtries/ns:Sum/text()"),
            "total_debit_entries": int(d_entries) if d_entries else None,
            "total_debit_amount": self._get_text("//ns:TxsSummry/ns:TtlDbtNtries/ns:Sum/text()"),
            "entries": entries,
        }
        if "camt.052" in ns_str:
            return Camt052Message(**kwargs, report_id=self._get_text("//ns:Rpt/ns:Id/text()"))
        else:
            return Camt053Message(
                **kwargs, balances=balances, statement_id=self._get_text("//ns:Stmt/ns:Id/text()")
            )

    def _parse_pain00X_detailed(self, base_msg: PaymentMessage, ns_str: str) -> PaymentMessage:
        pmt_infs = []
        for pm_el in self._get_nodes("//ns:PmtInf"):
            txs = []
            # Handle Pain.001 Credit Transfers
            for tx_el in self._get_nodes_from(pm_el, ".//ns:CdtTrfTxInf"):
                tx = {
                    "instruction_id": self._get_text_from(tx_el, "./ns:PmtId/ns:InstrId/text()"),
                    "end_to_end_id": self._get_text_from(tx_el, "./ns:PmtId/ns:EndToEndId/text()"),
                    "instructed_amount": self._get_text_from(tx_el, ".//ns:InstdAmt/text()"),
                    "instructed_currency": self._get_text_from(tx_el, ".//ns:InstdAmt/@Ccy"),
                    "creditor_name": self._get_text_from(tx_el, "./ns:Cdtr/ns:Nm/text()"),
                    "creditor_account": self._get_text_from(
                        tx_el,
                        "./ns:CdtrAcct/ns:Id/ns:IBAN/text() | ./ns:CdtrAcct/ns:Id/ns:Othr/ns:Id/text()",
                    ),
                    "creditor_address": self._parse_address(
                        self._get_nodes_from(tx_el, "./ns:Cdtr")[0]
                        if self._get_nodes_from(tx_el, "./ns:Cdtr")
                        else None
                    ),
                    "remittance_info": self._get_text_from(
                        tx_el,
                        ".//ns:RmtInf/ns:Strd/ns:RfrdDocInf/ns:Nb/text() | .//ns:RmtInf/ns:Ustrd/text()",
                    ),
                }
                txs.append(tx)

            # Handle Pain.008 Direct Debits
            for tx_el in self._get_nodes_from(pm_el, ".//ns:DrctDbtTxInf"):
                tx = {
                    "end_to_end_id": self._get_text_from(tx_el, "./ns:PmtId/ns:EndToEndId/text()"),
                    "instructed_amount": self._get_text_from(tx_el, "./ns:InstdAmt/text()"),
                    "instructed_currency": self._get_text_from(tx_el, "./ns:InstdAmt/@Ccy"),
                    "mandate_id": self._get_text_from(tx_el, ".//ns:MndtId/text()"),
                    "debtor_name": self._get_text_from(tx_el, "./ns:Dbtr/ns:Nm/text()"),
                    "debtor_account": self._get_text_from(
                        tx_el,
                        "./ns:DbtrAcct/ns:Id/ns:IBAN/text() | "
                        "./ns:DbtrAcct/ns:Id/ns:Othr/ns:Id/text()",
                    ),
                    "debtor_address": self._parse_address(
                        self._get_nodes_from(tx_el, "./ns:Dbtr")[0]
                        if self._get_nodes_from(tx_el, "./ns:Dbtr")
                        else None
                    ),
                    "remittance_info": self._get_text_from(
                        tx_el,
                        ".//ns:RmtInf/ns:Strd/ns:RfrdDocInf/ns:Nb/text() | "
                        ".//ns:RmtInf/ns:Ustrd/text()",
                    ),
                }
                txs.append(tx)

            pm = {
                "payment_information_id": self._get_text_from(pm_el, "./ns:PmtInfId/text()"),
                "payment_method": self._get_text_from(pm_el, "./ns:PmtMtd/text()"),
                "debtor_name": (
                    self._get_text_from(pm_el, "./ns:Dbtr/ns:Nm/text()")
                    if "pain.001" in ns_str
                    else self._get_text_from(pm_el, "./ns:Cdtr/ns:Nm/text()")
                ),
                "debtor_account": (
                    self._get_text_from(
                        pm_el,
                        "./ns:DbtrAcct/ns:Id/ns:IBAN/text() | "
                        "./ns:DbtrAcct/ns:Id/ns:Othr/ns:Id/text()",
                    )
                    if "pain.001" in ns_str
                    else self._get_text_from(
                        pm_el,
                        "./ns:CdtrAcct/ns:Id/ns:IBAN/text() | "
                        "./ns:CdtrAcct/ns:Id/ns:Othr/ns:Id/text()",
                    )
                ),
                "transactions": txs,
            }
            pmt_infs.append(pm)

        nb_of_txs = self._get_text("//ns:GrpHdr/ns:NbOfTxs/text()")

        kwargs = {
            **base_msg.to_dict(),
            "creation_date_time": self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            "number_of_transactions": int(nb_of_txs) if nb_of_txs else None,
            "control_sum": self._get_text("//ns:GrpHdr/ns:CtrlSum/text()"),
            "initiating_party": self._get_text(
                "//ns:GrpHdr/ns:InitgPty/ns:Nm/text() | "
                "//ns:GrpHdr/ns:InitgPty/ns:Id//ns:Id/text()"
            ),
            "payment_information": pmt_infs,
        }
        if "pain.001" in ns_str:
            return Pain001Message(**kwargs)
        else:
            return Pain008Message(**kwargs)

    def _parse_pain002_detailed(self, base_msg: PaymentMessage) -> Pain002Message:
        statuses = []
        for tx_el in self._get_nodes("//ns:TxInfAndSts"):
            tx = {
                "original_instruction_id": self._get_text_from(tx_el, "./ns:OrgnlInstrId/text()"),
                "original_end_to_end_id": self._get_text_from(tx_el, "./ns:OrgnlEndToEndId/text()"),
                "transaction_status": self._get_text_from(tx_el, "./ns:TxSts/text()"),
                "status_reason_code": self._get_text_from(
                    tx_el, ".//ns:StsRsnInf/ns:Rsn/ns:Cd/text()"
                ),
                "status_additional_info": self._get_text_from(
                    tx_el, ".//ns:StsRsnInf/ns:AddtlInf/text()"
                ),
                "original_amount": self._get_text_from(tx_el, ".//ns:OrgnlTxRef/ns:Amt//text()"),
            }
            statuses.append(tx)

        return Pain002Message(
            **base_msg.to_dict(),
            creation_date_time=self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            initiating_party=self._get_text(
                "//ns:GrpHdr/ns:InitgPty/ns:Id//ns:BICOrBEI/text() | "
                "//ns:GrpHdr/ns:InitgPty/ns:Nm/text()"
            ),
            original_message_id=self._get_text("//ns:OrgnlGrpInfAndSts/ns:OrgnlMsgId/text()"),
            original_message_name_id=self._get_text(
                "//ns:OrgnlGrpInfAndSts/ns:OrgnlMsgNmId/text()"
            ),
            group_status=self._get_text("//ns:OrgnlGrpInfAndSts/ns:GrpSts/text()"),
            transactions_status=statuses,
        )

    def _parse_camt056(self) -> Camt056Message:
        """
        Parses CAMT.056 FIToFI Customer Credit Transfer Recall.
        """
        base = self.parse()

        original_grp_info = self._get_nodes(".//ns:OrgnlGrpInf")
        orig_msg_id = None
        orig_msg_nm_id = None
        if original_grp_info:
            orig_msg_id = self._get_text_from(original_grp_info[0], "./ns:OrgnlMsgId/text()")
            orig_msg_nm_id = self._get_text_from(original_grp_info[0], "./ns:OrgnlMsgNmId/text()")

        recall_reason = self._get_text(
            ".//ns:OrgnlTxRef/ns:Rsn/ns:Prtry/text() | .//ns:OrgnlTxRef/ns:Rsn/ns:Cd/text()"
        )

        transactions = []
        for tx in self._get_nodes(".//ns:Undrlyg"):
            tx_id = self._get_text_from(tx, ".//ns:OrgnlEndToEndId/text()")
            tx_uetr = self._get_text_from(tx, ".//ns:OrgnlUETR/text()")
            transactions.append({"end_to_end_id": tx_id, "uetr": tx_uetr})

        promoted_uetr = base.uetr or (transactions[0]["uetr"] if transactions else None)
        promoted_e2e = base.end_to_end_id or (
            transactions[0]["end_to_end_id"] if transactions else None
        )

        return Camt056Message(
            message_id=base.message_id,
            end_to_end_id=promoted_e2e,
            uetr=promoted_uetr,
            amount=base.amount,
            currency=base.currency,
            sender_bic=base.sender_bic,
            receiver_bic=base.receiver_bic,
            creation_date_time=self._get_text(".//ns:CreDtTm/text()"),
            assignment_id=self._get_text(".//ns:Assgnmt/ns:Id/text()"),
            case_id=self._get_text(".//ns:Case/ns:Id/text()"),
            original_message_id=orig_msg_id,
            original_message_name_id=orig_msg_nm_id,
            recall_reason=recall_reason,
            underlying_transactions=transactions,
        )

    def _parse_camt029(self) -> Camt029Message:
        """
        Parses CAMT.029 Resolution Of Investigation.
        """
        base = self.parse()

        status_node = self._get_nodes(".//ns:Sts")
        investigation_status = None
        if status_node:
            investigation_status = self._get_text_from(
                status_node[0], "./ns:Conf/text() | ./ns:Prtry/text() | ./ns:Cd/text()"
            )

        cancellation_details = []
        for detail in self._get_nodes(".//ns:CxlDtls"):
            orig_id = self._get_text_from(detail, ".//ns:OrgnlEndToEndId/text()")
            orig_uetr = self._get_text_from(detail, ".//ns:OrgnlUETR/text()")
            cxl_sts = self._get_text_from(detail, ".//ns:TxCxlSts/text()")
            cancellation_details.append(
                {"end_to_end_id": orig_id, "uetr": orig_uetr, "status": cxl_sts}
            )

        promoted_uetr = base.uetr or (
            cancellation_details[0]["uetr"] if cancellation_details else None
        )
        promoted_e2e = base.end_to_end_id or (
            cancellation_details[0]["end_to_end_id"] if cancellation_details else None
        )

        return Camt029Message(
            message_id=base.message_id,
            end_to_end_id=promoted_e2e,
            uetr=promoted_uetr,
            amount=base.amount,
            currency=base.currency,
            sender_bic=base.sender_bic,
            receiver_bic=base.receiver_bic,
            creation_date_time=self._get_text(".//ns:CreDtTm/text()"),
            assignment_id=self._get_text(".//ns:Assgnmt/ns:Id/text()"),
            case_id=self._get_text(".//ns:Case/ns:Id/text()"),
            investigation_status=investigation_status,
            cancellation_details=cancellation_details,
        )

    def _parse_fxtr014(self, base_msg: PaymentMessage) -> Fxtr014Message:
        return Fxtr014Message(
            **base_msg.to_dict(),
            creation_date_time=self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            trade_date=self._get_text("//ns:TradInf/ns:TradDt/text()"),
            settlement_date=self._get_text("//ns:TradAmts/ns:SttlmDt/text()"),
            trading_party=self._get_text(
                "//ns:TradgSdId/ns:SubmitgPty/ns:AnyBIC/ns:AnyBIC/text() | "
                "//ns:TradgSdId/ns:SubmitgPty/ns:NmAndAdr/ns:Nm/text()"
            ),
            counterparty=self._get_text(
                "//ns:CtrPtySdId/ns:SubmitgPty/ns:AnyBIC/ns:AnyBIC/text() | "
                "//ns:CtrPtySdId/ns:SubmitgPty/ns:NmAndAdr/ns:Nm/text()"
            ),
            exchange_rate=self._get_text("//ns:AgrdRate/ns:XchgRate/text()"),
            traded_amount=self._get_text("//ns:TradAmts/ns:TradgSdBuyAmt/ns:Amt/text()"),
            traded_currency=self._get_text("//ns:TradAmts/ns:TradgSdBuyAmt/ns:Amt/@Ccy"),
        )

    def _parse_sese023(self, base_msg: PaymentMessage) -> Sese023Message:
        qty_type = None
        if self._get_text("//ns:QtyAndAcctDtls/ns:SttlmQty/ns:Qty/ns:Unit/text()"):
            qty_type = "Unit"
        elif self._get_text("//ns:QtyAndAcctDtls/ns:SttlmQty/ns:Qty/ns:AmtsdVal/text()"):
            qty_type = "AmortisedValue"

        return Sese023Message(
            **base_msg.to_dict(),
            creation_date_time=self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            trade_date=self._get_text(
                "//ns:TradDtls/ns:TradDt/ns:Dt/ns:Dt/text() | "
                "//ns:TradDtls/ns:TradDt/ns:DtTm/text()"
            ),
            settlement_date=self._get_text(
                "//ns:TradDtls/ns:SttlmDt/ns:Dt/ns:Dt/text() | "
                "//ns:TradDtls/ns:SttlmDt/ns:DtTm/text()"
            ),
            security_id=self._get_text("//ns:FinInstrmId/ns:ISIN/text()"),
            security_id_type="ISIN" if self._get_text("//ns:FinInstrmId/ns:ISIN/text()") else None,
            security_quantity=self._get_text(
                "//ns:QtyAndAcctDtls/ns:SttlmQty/ns:Qty/ns:Unit/text() | "
                "//ns:QtyAndAcctDtls/ns:SttlmQty/ns:Qty/ns:AmtsdVal/text()"
            ),
            security_quantity_type=qty_type,
            settlement_amount=self._get_text("//ns:SttlmAmt/ns:Amt/ns:Amt/text()"),
            settlement_currency=self._get_text("//ns:SttlmAmt/ns:Amt/ns:Amt/@Ccy"),
            delivering_agent=self._get_text(
                "//ns:DlvrgSttlmPties/ns:Pty1/ns:Id/ns:AnyBIC/text() | "
                "//ns:DlvrgSttlmPties/ns:Pty1/ns:Id/ns:NmAndAdr/ns:Nm/text()"
            ),
            receiving_agent=self._get_text(
                "//ns:RcvgSttlmPties/ns:Pty1/ns:Id/ns:AnyBIC/text() | "
                "//ns:RcvgSttlmPties/ns:Pty1/ns:Id/ns:NmAndAdr/ns:Nm/text()"
            ),
        )

    def _parse_pacs004(self, base_msg: PaymentMessage) -> Pacs004Message:
        transactions = []
        for tx_el in self._get_nodes("//ns:TxInf"):
            tx = {
                "return_id": self._get_text_from(tx_el, "./ns:RtrId/text()"),
                "original_end_to_end_id": self._get_text_from(tx_el, "./ns:OrgnlEndToEndId/text()"),
                "original_transaction_id": self._get_text_from(tx_el, "./ns:OrgnlTxId/text()"),
                "original_uetr": self._get_text_from(tx_el, "./ns:OrgnlUETR/text()"),
                "returned_amount": self._get_text_from(tx_el, "./ns:RtrdIntrBkSttlmAmt/text()"),
                "returned_currency": self._get_text_from(tx_el, "./ns:RtrdIntrBkSttlmAmt/@Ccy"),
                "return_reason": self._get_text_from(
                    tx_el, ".//ns:RtrRsnInf/ns:Rsn/ns:Cd/text() | .//ns:RtrRsnInf/ns:Rsn/ns:Prtry/text()"
                ),
            }
            transactions.append(tx)

        # Promote UETR from first transaction if base doesn't have it
        promoted_uetr = base_msg.uetr or (transactions[0].get("original_uetr") if transactions else None)

        return Pacs004Message(
            **{**base_msg.to_dict(), "uetr": promoted_uetr},
            creation_date_time=self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            original_message_id=self._get_text("//ns:OrgnlGrpInf/ns:OrgnlMsgId/text()"),
            original_message_name_id=self._get_text("//ns:OrgnlGrpInf/ns:OrgnlMsgNmId/text()"),
            transactions=transactions,
        )

    def _parse_pacs009(self, base_msg: PaymentMessage) -> Pacs009Message:
        transactions = []
        for tx_el in self._get_nodes("//ns:CdtTrfTxInf"):
            tx = {
                "instruction_id": self._get_text_from(tx_el, "./ns:PmtId/ns:InstrId/text()"),
                "end_to_end_id": self._get_text_from(tx_el, "./ns:PmtId/ns:EndToEndId/text()"),
                "transaction_id": self._get_text_from(tx_el, "./ns:PmtId/ns:TxId/text()"),
                "uetr": self._get_text_from(tx_el, "./ns:PmtId/ns:UETR/text()"),
                "amount": self._get_text_from(tx_el, "./ns:IntrBkSttlmAmt/text()"),
                "currency": self._get_text_from(tx_el, "./ns:IntrBkSttlmAmt/@Ccy"),
                "debtor": self._get_text_from(
                    tx_el,
                    "./ns:Dbtr/ns:BICFI/text() | ./ns:Dbtr/ns:Othr/ns:Id/text()"
                ),
                "creditor": self._get_text_from(
                    tx_el,
                    "./ns:Cdtr/ns:BICFI/text() | ./ns:Cdtr/ns:Othr/ns:Id/text()"
                ),
            }
            transactions.append(tx)

        promoted_uetr = base_msg.uetr or (transactions[0].get("uetr") if transactions else None)
        promoted_e2e = base_msg.end_to_end_id or (transactions[0].get("end_to_end_id") if transactions else None)

        return Pacs009Message(
            **{**base_msg.to_dict(), "uetr": promoted_uetr, "end_to_end_id": promoted_e2e},
            creation_date_time=self._get_text("//ns:GrpHdr/ns:CreDtTm/text()"),
            settlement_method=self._get_text("//ns:GrpHdr/ns:SttlmInf/ns:SttlmMtd/text()"),
            transactions=transactions,
        )

    def _parse_setr004(self, base_msg: PaymentMessage) -> Setr004Message:
        orders = []
        for ordr_el in self._get_nodes("//ns:MltplOrdrDtls/ns:IndvOrdrDtls"):
            order = {
                "order_reference": self._get_text_from(ordr_el, "./ns:OrdrRef/text()"),
                "investment_account_id": self._get_text_from(
                    ordr_el, "./ns:InvstmtAcctDtls/ns:AcctId/text() | ./ns:InvstmtAcctDtls/ns:Id/text()"
                ),
                "financial_instrument_id": self._get_text_from(ordr_el, "./ns:FinInstrmDtls/ns:Id/ns:ISIN/text()"),
                "amount": self._get_text_from(ordr_el, "./ns:OrdrQty/ns:AmtdQty/text()"),
                "currency": self._get_text_from(ordr_el, "./ns:OrdrQty/ns:AmtdQty/@Ccy"),
                "units": self._get_text_from(ordr_el, "./ns:OrdrQty/ns:UnitQty/text()"),
            }
            orders.append(order)

        return Setr004Message(
            **base_msg.to_dict(),
            master_reference=self._get_text("//ns:MltplOrdrDtls/ns:MstrRef/text()") or self._get_text("//ns:MsgId/ns:Id/text()"),
            pool_reference=self._get_text("//ns:PoolRef/ns:Ref/text()"),
            orders=orders,
        )

    def _parse_setr010(self, base_msg: PaymentMessage) -> Setr010Message:
        orders = []
        for ordr_el in self._get_nodes("//ns:MltplOrdrDtls/ns:IndvOrdrDtls"):
            order = {
                "order_reference": self._get_text_from(ordr_el, "./ns:OrdrRef/text()"),
                "investment_account_id": self._get_text_from(
                    ordr_el, "./ns:InvstmtAcctDtls/ns:AcctId/text() | ./ns:InvstmtAcctDtls/ns:Id/text()"
                ),
                "financial_instrument_id": self._get_text_from(ordr_el, "./ns:FinInstrmDtls/ns:Id/ns:ISIN/text()"),
                "amount": self._get_text_from(ordr_el, "./ns:OrdrQty/ns:AmtdQty/text()"),
                "currency": self._get_text_from(ordr_el, "./ns:OrdrQty/ns:AmtdQty/@Ccy"),
                "units": self._get_text_from(ordr_el, "./ns:OrdrQty/ns:UnitQty/text()"),
            }
            orders.append(order)

        return Setr010Message(
            **base_msg.to_dict(),
            master_reference=self._get_text("//ns:MltplOrdrDtls/ns:MstrRef/text()") or self._get_text("//ns:MsgId/ns:Id/text()"),
            pool_reference=self._get_text("//ns:PoolRef/ns:Ref/text()"),
            orders=orders,
        )

    def _parse_acmt007(self, base_msg: PaymentMessage) -> Acmt007Message:
        return Acmt007Message(
            **base_msg.to_dict(),
            process_id=self._get_text("//ns:PrcId/ns:Id/text()"),
            account_id=self._get_text("//ns:Acct/ns:Id/ns:Othr/ns:Id/text() | //ns:Acct/ns:Id/ns:IBAN/text()"),
            account_currency=self._get_text("//ns:Acct/ns:Ccy/text()"),
            organization_name=self._get_text("//ns:Org/ns:FullLglNm/text()"),
            branch_name=self._get_text("//ns:AcctSvcrId/ns:BrnchId/ns:Nm/text()"),
        )

    def _parse_acmt015(self, base_msg: PaymentMessage) -> Acmt015Message:
        return Acmt015Message(
            **base_msg.to_dict(),
            process_id=self._get_text("//ns:PrcId/ns:Id/text()"),
            account_id=self._get_text("//ns:Acct/ns:Id/ns:Othr/ns:Id/text() | //ns:Acct/ns:Id/ns:IBAN/text()"),
            organization_name=self._get_text("//ns:Org//ns:FullLglNm/text()"),
            branch_name=self._get_text("//ns:AcctSvcrId/ns:BrnchId/ns:Nm/text()"),
        )

    def _parse_camt086(self, base_msg: PaymentMessage) -> Camt086Message:
        return Camt086Message(
            **base_msg.to_dict(),
            report_id=self._get_text("//ns:RptHdr/ns:RptId/text()"),
            group_id=self._get_text("//ns:BllgStmtGrp/ns:GrpId/text()"),
            statement_id=self._get_text("//ns:BllgStmtGrp/ns:BllgStmt/ns:StmtId/text()"),
            statement_status=self._get_text("//ns:BllgStmtGrp/ns:BllgStmt/ns:Sts/text()"),
            creation_date_time=self._get_text("//ns:BllgStmtGrp/ns:BllgStmt/ns:CreDtTm/text()"),
        )

    def flatten(self) -> Dict[str, Any]:
        """
        Parses the XML or MT tree and returns a flat dictionary.
        Kept for backward-compatibility.
        """
        return self.parse().to_dict()
