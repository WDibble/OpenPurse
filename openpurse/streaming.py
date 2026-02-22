import io
from typing import Generator, Optional, Union
from lxml import etree
from openpurse.models import PaymentMessage, Pacs008Message, Pain001Message, Camt053Message, Camt054Message
from openpurse.parser import OpenPurseParser

class StreamingParser:
    """
    High-performance streaming parser for large ISO 20022 XML files.
    Uses lxml.etree.iterparse to minimize memory footprint by clearing 
    elements as they are processed.
    """

    # Elements that represent individual transactions/entries in common schemas
    INTERESTING_TAGS = {
        "CdtTrfTxInf",  # pacs.008, pain.001
        "Ntry",         # camt.053, camt.054
        "TxInf",        # pacs.004, pacs.009
    }

    def __init__(self, source: Union[bytes, io.BytesIO, str]):
        """
        Initialize with bytes, a file-like object, or a path to a file.
        """
        if isinstance(source, bytes):
            self.source = io.BytesIO(source)
        elif isinstance(source, str):
            self.source = source
        else:
            self.source = source

    def iter_messages(self) -> Generator[PaymentMessage, None, None]:
        """
        Streams records from the XML source.
        Yields specialized PaymentMessage subclasses for each record found.
        """
        try:
            context = etree.iterparse(
                self.source, 
                events=("end",), 
                tag=None  # We check tag inside the loop for flexibility
            )
        except (etree.XMLSyntaxError, ValueError):
            return

        # We need to capture the default namespace to correctly identify tags
        default_ns: Optional[str] = None
        
        try:
            for event, elem in context:
                # Extract namespace on the first element if not already done
                if default_ns is None and "}" in elem.tag:
                    default_ns = elem.tag.split("}", 1)[0].strip("{")

                # Check if this element is one of our interesting transaction/entry tags
                tag_local = elem.tag.split("}", 1)[1] if "}" in elem.tag else elem.tag
                
                if tag_local in self.INTERESTING_TAGS:
                    # To parse this record correctly using existing logic, 
                    # we wrap it in a minimal Document structure if necessary, 
                    # or just use the local element as the tree root for a parser.
                    
                    # In order to reuse the OpenPurseParser logic, we convert the element to bytes
                    # and initialize a standard parser.
                    # Note: For maximum performance, we could refactor OpenPurseParser to 
                    # accept an etree element directly.
                    
                    record_xml = etree.tostring(elem, encoding="utf-8")
                    
                    # We need to preserve the namespace for the local parser
                    if default_ns:
                        ns_decl = f' xmlns="urn:iso:std:iso:20022:tech:xsd:{default_ns}"' if "urn:iso" not in default_ns else f' xmlns="{default_ns}"'
                        # Wrap in Document if needed, or just ensure the tag has the namespace
                        if 'xmlns' not in record_xml.decode("utf-8"):
                            record_xml = record_xml.replace(f"<{tag_local}".encode(), f"<{tag_local}{ns_decl}".encode(), 1)

                    parser = OpenPurseParser(record_xml)
                    # Since we are parsing a fragment, we might need a modified parse logic
                    # For now, we utilize the fragment to extract a base PaymentMessage
                    msg = parser.parse()
                    yield msg
                    
                    # Crucial for memory performance: clear the element and all its predecessors
                    elem.clear()
                    while elem.getprevious() is not None:
                        del elem.getparent()[0]
        except (etree.XMLSyntaxError, ValueError):
            pass
        finally:
            if 'context' in locals():
                del context
