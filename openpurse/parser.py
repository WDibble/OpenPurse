from lxml import etree

class OpenPurseParser:
    """
    Core parser for flattening ISO 20022 XML messages.
    The Antigravity agent will implement the logic here based on the rules.
    """
    
    def __init__(self, xml_data: bytes):
        self.tree = etree.fromstring(xml_data)
        # Agent: Implement dynamic namespace extraction here
        
    def flatten(self) -> dict:
        """
        Parses the XML tree and returns a flat dictionary.
        """
        # Agent: Implement XPath extraction logic here
        pass