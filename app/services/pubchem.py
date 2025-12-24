"""
PubChem Service - Molecule Intelligence
Get CID, CAS, dev codes, synonyms from PubChem
"""
import pubchempy as pcp
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def get_molecule_data(molecule_name: str) -> Dict:
    """
    Get comprehensive molecule data from PubChem
    
    Returns:
    - cid: PubChem CID
    - cas: CAS Registry Number
    - molecular_formula: Formula
    - molecular_weight: Weight
    - iupac_name: IUPAC name
    - smiles: SMILES string
    - inchi: InChI string
    - inchi_key: InChI Key
    - dev_codes: Development codes
    - synonyms: All synonyms
    """
    try:
        # Search for compound
        compounds = pcp.get_compounds(molecule_name, 'name')
        
        if not compounds:
            logger.warning(f"No compounds found for {molecule_name}")
            return _empty_molecule_data()
        
        compound = compounds[0]
        
        # Get basic properties
        data = {
            'cid': compound.cid,
            'cas': _extract_cas(compound),
            'molecular_formula': compound.molecular_formula,
            'molecular_weight': compound.molecular_weight,
            'iupac_name': compound.iupac_name,
            'smiles': compound.canonical_smiles,
            'inchi': compound.inchi,
            'inchi_key': compound.inchikey
        }
        
        # Get synonyms (includes dev codes)
        synonyms = compound.synonyms or []
        
        # Extract dev codes (pattern: XXX-123, XXX123, etc)
        dev_codes = _extract_dev_codes(synonyms)
        
        data['dev_codes'] = dev_codes
        data['synonyms'] = synonyms
        
        logger.info(f"✅ PubChem: Found CID {data['cid']} for {molecule_name}")
        
        return data
        
    except Exception as e:
        logger.error(f"❌ PubChem error: {e}")
        return _empty_molecule_data()


def _extract_cas(compound) -> Optional[str]:
    """Extract CAS number from compound"""
    try:
        # Try to get CAS from synonyms
        for syn in compound.synonyms or []:
            # CAS format: 1234-56-7 or 12345-67-8
            if '-' in syn:
                parts = syn.split('-')
                if len(parts) == 3 and all(p.isdigit() for p in parts):
                    return syn
        return None
    except:
        return None


def _extract_dev_codes(synonyms: List[str]) -> List[str]:
    """
    Extract development codes from synonyms
    
    Patterns:
    - ODM-201, BAY-1841788 (XXX-123)
    - ODM201, BAY1841788 (XXX123)
    - CS-5174, DB12941, etc
    """
    dev_codes = []
    
    for syn in synonyms:
        # Skip very long strings
        if len(syn) > 50:
            continue
        
        # Skip numbers-only
        if syn.isdigit():
            continue
        
        # Pattern: Letters + numbers with optional dash
        # ODM-201, BAY-1841788, CS-5174, DB12941, etc
        if any(c.isalpha() for c in syn) and any(c.isdigit() for c in syn):
            # Filter common non-dev-code patterns
            lower_syn = syn.lower()
            if any(skip in lower_syn for skip in ['name', 'pyrazole', 'phenyl', 'ethyl', 'methyl']):
                continue
            
            # Likely a dev code
            if len(syn) < 30 and (('-' in syn) or (syn.isupper() or any(c.isupper() for c in syn[:3]))):
                dev_codes.append(syn)
    
    return dev_codes


def _empty_molecule_data() -> Dict:
    """Return empty molecule data structure"""
    return {
        'cid': None,
        'cas': None,
        'molecular_formula': None,
        'molecular_weight': None,
        'iupac_name': None,
        'smiles': None,
        'inchi': None,
        'inchi_key': None,
        'dev_codes': [],
        'synonyms': []
    }


# Test
if __name__ == "__main__":
    data = get_molecule_data("Darolutamide")
    print(f"CID: {data['cid']}")
    print(f"CAS: {data['cas']}")
    print(f"Dev Codes: {data['dev_codes'][:10]}")
    print(f"Synonyms: {len(data['synonyms'])}")
