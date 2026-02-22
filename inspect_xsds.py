import os
import glob
import xml.etree.ElementTree as ET

def analyze_xsds():
    docs_dir = '/Users/dibble/Documents/GitHub/OpenPurse/docs'
    xsds = glob.glob(f'{docs_dir}/**/*.xsd', recursive=True)
    
    namespaces = set()
    for xsd in xsds:
        try:
            tree = ET.parse(xsd)
            root = tree.getroot()
            target_ns = root.get('targetNamespace')
            if target_ns:
                namespaces.add(target_ns)
        except Exception as e:
            pass
            
    print(f"Found {len(xsds)} XSD files.")
    print(f"Found {len(namespaces)} unique namespaces.")
    print("Sample namespaces:")
    for ns in list(namespaces)[:10]:
        print(" -", ns)

if __name__ == '__main__':
    analyze_xsds()
