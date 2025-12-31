"""Ontology Semantic Index Module.

This module provides semantic enhancement capabilities by parsing OWL/TTL ontology files
and building an in-memory index for fast lookups. Inspired by Vanna's RAG approach,
it implements three-layer semantic enhancement:

1. Term Translation: Chinese labels → column/table names
2. Semantic Understanding: Comments, examples, enum values
3. Relationship Inference: ObjectProperty domain/range → JOIN paths

Usage:
    index = OntologySemanticIndex()
    index.load_from_ttl("/path/to/ontology.ttl")
    index.load_source_mapping("/path/to/mapping.json")

    # Get semantic context for a query
    context = index.build_semantic_context("海螺项目的负责人是谁?")
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TermMapping:
    """Mapping for a canonical term to its variants (aliases, abbreviations, slang)."""

    canonical: str  # Standard term (matches rdfs:label)
    property_name: str = ""  # Mapped property local name (e.g., "pj_leader")
    aliases: List[str] = field(default_factory=list)  # Alternative names
    abbreviations: List[str] = field(default_factory=list)  # Short forms
    slang: List[str] = field(default_factory=list)  # Informal terms/jargon
    context_hints: List[str] = field(default_factory=list)  # Context clues for disambiguation

    def all_variants(self) -> List[str]:
        """Get all variant forms of this term."""
        return self.aliases + self.abbreviations + self.slang


class SemanticDictionary:
    """Semantic dictionary for term normalization and expansion.

    Supports:
    - Aliases: 负责人 → 项目负责人
    - Abbreviations: PM → 项目经理, Q1 → 第一季度
    - Slang/Jargon: 甲方 → 客户, pj → 项目

    Usage:
        dict = SemanticDictionary()
        dict.load_from_file("semantic_dictionary.json")
        canonical = dict.normalize_term("PM")  # → "项目经理"
        expanded = dict.expand_query("PM负责的pj")  # → "项目经理负责的项目"
    """

    def __init__(self):
        # variant → canonical term
        self._variant_to_canonical: Dict[str, str] = {}
        # canonical → TermMapping
        self._canonical_to_mapping: Dict[str, TermMapping] = {}
        # Global abbreviations (not tied to specific ontology terms)
        self._global_abbreviations: Dict[str, str] = {}
        self._loaded = False

    def load_from_file(self, path: str) -> bool:
        """Load dictionary from JSON file.

        Expected format:
        {
            "term_mappings": [
                {
                    "canonical": "项目负责人",
                    "property": "pj_leader",
                    "aliases": ["负责人", "项目经理"],
                    "abbreviations": ["PM", "PL"],
                    "slang": ["头儿"]
                }
            ],
            "global_abbreviations": {
                "Q1": "第一季度",
                "YTD": "年初至今"
            }
        }
        """
        dict_file = Path(path)
        if not dict_file.exists():
            logger.warning(f"Dictionary file not found: {path}")
            return False

        try:
            with open(dict_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load term mappings
            for mapping in data.get("term_mappings", []):
                self.add_term_mapping(
                    canonical=mapping.get("canonical", ""),
                    property_name=mapping.get("property", ""),
                    aliases=mapping.get("aliases", []),
                    abbreviations=mapping.get("abbreviations", []),
                    slang=mapping.get("slang", []),
                    context_hints=mapping.get("context_hints", []),
                )

            # Load global abbreviations
            for abbr, expansion in data.get("global_abbreviations", {}).items():
                self._global_abbreviations[abbr] = expansion

            self._loaded = True
            logger.info(f"Loaded semantic dictionary: {len(self._canonical_to_mapping)} terms, "
                       f"{len(self._global_abbreviations)} global abbreviations")
            return True

        except Exception as e:
            logger.error(f"Failed to load semantic dictionary: {e}")
            return False

    def save_to_file(self, path: str) -> bool:
        """Save current dictionary to JSON file."""
        try:
            data = {
                "term_mappings": [],
                "global_abbreviations": self._global_abbreviations.copy()
            }

            for mapping in self._canonical_to_mapping.values():
                data["term_mappings"].append({
                    "canonical": mapping.canonical,
                    "property": mapping.property_name,
                    "aliases": mapping.aliases,
                    "abbreviations": mapping.abbreviations,
                    "slang": mapping.slang,
                    "context_hints": mapping.context_hints,
                })

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved semantic dictionary to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save semantic dictionary: {e}")
            return False

    def add_term_mapping(
        self,
        canonical: str,
        property_name: str = "",
        aliases: List[str] = None,
        abbreviations: List[str] = None,
        slang: List[str] = None,
        context_hints: List[str] = None,
    ) -> None:
        """Add a term mapping to the dictionary."""
        if not canonical:
            return

        mapping = TermMapping(
            canonical=canonical,
            property_name=property_name,
            aliases=aliases or [],
            abbreviations=abbreviations or [],
            slang=slang or [],
            context_hints=context_hints or [],
        )

        self._canonical_to_mapping[canonical] = mapping

        # Build reverse index
        for variant in mapping.all_variants():
            self._variant_to_canonical[variant.lower()] = canonical

    def add_alias(self, canonical: str, alias: str) -> None:
        """Add an alias for a canonical term."""
        if canonical in self._canonical_to_mapping:
            self._canonical_to_mapping[canonical].aliases.append(alias)
        else:
            self.add_term_mapping(canonical, aliases=[alias])
        self._variant_to_canonical[alias.lower()] = canonical

    def add_abbreviation(self, abbr: str, expansion: str, is_global: bool = False) -> None:
        """Add an abbreviation mapping.

        Args:
            abbr: The abbreviation (e.g., "PM")
            expansion: The expanded form (e.g., "项目经理")
            is_global: If True, adds to global abbreviations (not tied to ontology)
        """
        if is_global:
            self._global_abbreviations[abbr] = expansion
        else:
            if expansion in self._canonical_to_mapping:
                self._canonical_to_mapping[expansion].abbreviations.append(abbr)
            else:
                self.add_term_mapping(expansion, abbreviations=[abbr])
            self._variant_to_canonical[abbr.lower()] = expansion

    def add_slang(self, slang: str, meaning: str) -> None:
        """Add a slang/jargon term."""
        if meaning in self._canonical_to_mapping:
            self._canonical_to_mapping[meaning].slang.append(slang)
        else:
            self.add_term_mapping(meaning, slang=[slang])
        self._variant_to_canonical[slang.lower()] = meaning

    def remove_variant(self, variant: str) -> bool:
        """Remove a variant (alias/abbreviation/slang) from the dictionary."""
        variant_lower = variant.lower()
        if variant_lower not in self._variant_to_canonical:
            return False

        canonical = self._variant_to_canonical.pop(variant_lower)
        if canonical in self._canonical_to_mapping:
            mapping = self._canonical_to_mapping[canonical]
            # Remove from all variant lists
            mapping.aliases = [a for a in mapping.aliases if a.lower() != variant_lower]
            mapping.abbreviations = [a for a in mapping.abbreviations if a.lower() != variant_lower]
            mapping.slang = [s for s in mapping.slang if s.lower() != variant_lower]

        return True

    def normalize_term(self, term: str) -> str:
        """Normalize a term to its canonical form.

        Args:
            term: Input term (may be alias/abbreviation/slang)

        Returns:
            Canonical form if found, otherwise original term
        """
        # Check global abbreviations first
        if term in self._global_abbreviations:
            return self._global_abbreviations[term]

        # Check variant index
        canonical = self._variant_to_canonical.get(term.lower())
        if canonical:
            return canonical

        return term

    def expand_query(self, query: str) -> str:
        """Expand abbreviations and slang in a query to canonical forms.

        Args:
            query: User's query with potential abbreviations/slang

        Returns:
            Query with terms normalized to canonical forms
        """
        result = query

        # Replace global abbreviations (case-sensitive for uppercase abbrs)
        for abbr, expansion in self._global_abbreviations.items():
            if abbr in result:
                result = result.replace(abbr, expansion)

        # Replace variants (case-insensitive matching but preserve original for replacement)
        for variant, canonical in self._variant_to_canonical.items():
            # Find case-insensitive match
            pattern = re.compile(re.escape(variant), re.IGNORECASE)
            result = pattern.sub(canonical, result)

        return result

    def get_canonical_terms(self) -> List[str]:
        """Get all canonical terms in the dictionary."""
        return list(self._canonical_to_mapping.keys())

    def get_mapping(self, canonical: str) -> Optional[TermMapping]:
        """Get the full mapping for a canonical term."""
        return self._canonical_to_mapping.get(canonical)

    def get_stats(self) -> Dict:
        """Get dictionary statistics."""
        total_variants = sum(len(m.all_variants()) for m in self._canonical_to_mapping.values())
        return {
            "loaded": self._loaded,
            "canonical_terms": len(self._canonical_to_mapping),
            "total_variants": total_variants,
            "global_abbreviations": len(self._global_abbreviations),
        }


@dataclass
class PropertyInfo:
    """Information about an ontology property (DataProperty or ObjectProperty)."""

    uri: str  # Full URI, e.g., "http://datahub/cost#pj_leader"
    local_name: str  # Local name, e.g., "pj_leader"
    label: str  # Chinese label, e.g., "项目负责人"
    comment: str  # Business description
    examples: List[str] = field(default_factory=list)
    rules: str = ""
    source_mapping: str = ""
    domain: str = ""  # Domain class URI
    range: str = ""  # Range class/datatype URI
    property_type: str = "DataProperty"  # DataProperty or ObjectProperty
    is_functional: bool = False  # owl:FunctionalProperty

    # Mapped MySQL info (from source_mapping.json)
    table_name: str = ""
    column_name: str = ""

    def get_enum_values(self) -> List[str]:
        """Extract enumeration values from comment if present."""
        if not self.comment:
            return []

        # Pattern: look for enumerated lists in comments
        # Example: "枚举包括\n-现场技术支持\n-远程技术支持"
        enum_patterns = [
            r'枚举[包括有如下：:]*\s*([-\n].+)',
            r'包括[：:]\s*([-\n].+)',
            r'取值[包括有如下：:]*\s*([-\n].+)',
        ]

        for pattern in enum_patterns:
            match = re.search(pattern, self.comment, re.DOTALL)
            if match:
                enum_text = match.group(1)
                # Extract items starting with - or •
                items = re.findall(r'[-•]\s*([^\n-•]+)', enum_text)
                return [item.strip() for item in items if item.strip()]

        return []


@dataclass
class ClassInfo:
    """Information about an ontology class."""

    uri: str  # Full URI
    local_name: str  # Local name, e.g., "project"
    label: str  # Chinese label, e.g., "项目"
    comment: str  # Business description
    parent_class: str = ""  # Parent class URI (rdfs:subClassOf)

    # Mapped MySQL info
    table_name: str = ""

    # Properties belonging to this class
    data_properties: List[str] = field(default_factory=list)
    object_properties: List[str] = field(default_factory=list)


@dataclass
class RelationshipPath:
    """Represents a JOIN path between two classes."""

    from_class: str
    to_class: str
    via_property: str
    join_type: str = "INNER"  # INNER, LEFT, etc.
    from_table: str = ""
    to_table: str = ""
    from_column: str = ""
    to_column: str = ""


class OntologySemanticIndex:
    """Semantic index for OWL/TTL ontology with source mapping.

    This class provides fast lookups for:
    - Chinese term → column/table mapping
    - Property semantic information (comments, examples, enums)
    - Relationship paths for JOIN inference
    """

    # RDF/OWL namespace prefixes
    NAMESPACES = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
    }

    def __init__(self):
        self.classes: Dict[str, ClassInfo] = {}  # URI → ClassInfo
        self.properties: Dict[str, PropertyInfo] = {}  # URI → PropertyInfo

        # Indexes for fast lookup
        self.label_to_property: Dict[str, List[str]] = {}  # Chinese label → property URIs
        self.label_to_class: Dict[str, str] = {}  # Chinese label → class URI
        self.column_to_property: Dict[str, str] = {}  # column_name → property URI
        self.table_to_class: Dict[str, str] = {}  # table_name → class URI

        # Relationship graph for JOIN inference
        self.relationships: Dict[str, List[RelationshipPath]] = {}  # class URI → outgoing relationships

        # Source mapping data
        self.source_mapping: Dict[str, dict] = {}  # table_name → mapping info

        # Semantic dictionary for aliases, abbreviations, slang
        self.dictionary: SemanticDictionary = SemanticDictionary()

        self._loaded = False

    def load_from_ttl(self, ttl_path: str) -> bool:
        """Load ontology from TTL file using rdflib.

        Args:
            ttl_path: Path to the TTL file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal
            from rdflib.namespace import XSD
        except ImportError:
            logger.error("rdflib not installed. Please install it: pip install rdflib")
            return False

        ttl_file = Path(ttl_path)
        if not ttl_file.exists():
            logger.error(f"TTL file not found: {ttl_path}")
            return False

        try:
            g = Graph()
            g.parse(ttl_file, format='turtle')
            logger.info(f"Loaded TTL file with {len(g)} triples")

            # Detect the ontology namespace (usually the base namespace)
            # Look for the most common subject namespace
            namespaces = {}
            for s, p, o in g:
                ns = str(s).rsplit('#', 1)[0] + '#' if '#' in str(s) else str(s).rsplit('/', 1)[0] + '/'
                namespaces[ns] = namespaces.get(ns, 0) + 1

            # Get the ontology namespace (most common non-standard namespace)
            ont_ns = None
            for ns, count in sorted(namespaces.items(), key=lambda x: -x[1]):
                if not any(std in ns for std in ['w3.org', 'xmlns']):
                    ont_ns = ns
                    break

            if ont_ns:
                EX = Namespace(ont_ns)
                logger.info(f"Detected ontology namespace: {ont_ns}")
            else:
                logger.warning("Could not detect ontology namespace")
                return False

            # Parse OWL Classes
            for class_uri in g.subjects(RDF.type, OWL.Class):
                self._parse_class(g, class_uri, EX)

            # Parse DataProperties
            for prop_uri in g.subjects(RDF.type, OWL.DatatypeProperty):
                self._parse_property(g, prop_uri, EX, "DataProperty")

            # Parse ObjectProperties
            for prop_uri in g.subjects(RDF.type, OWL.ObjectProperty):
                self._parse_property(g, prop_uri, EX, "ObjectProperty")

            # Build relationship graph
            self._build_relationship_graph()

            self._loaded = True
            logger.info(f"Indexed {len(self.classes)} classes, {len(self.properties)} properties")
            return True

        except Exception as e:
            logger.error(f"Failed to parse TTL file: {e}")
            return False

    def _parse_class(self, g, class_uri, EX) -> None:
        """Parse an OWL Class from the graph."""
        from rdflib import RDFS

        local_name = self._get_local_name(class_uri)

        # Get label (rdfs:label)
        label = ""
        for obj in g.objects(class_uri, RDFS.label):
            label = str(obj)
            break

        # Get comment (rdfs:comment)
        comment = ""
        for obj in g.objects(class_uri, RDFS.comment):
            comment = str(obj)
            break

        # Get parent class (rdfs:subClassOf)
        parent = ""
        for obj in g.objects(class_uri, RDFS.subClassOf):
            parent = str(obj)
            break

        class_info = ClassInfo(
            uri=str(class_uri),
            local_name=local_name,
            label=label or local_name,
            comment=comment,
            parent_class=parent,
        )

        self.classes[str(class_uri)] = class_info

        # Build label index
        if label:
            self.label_to_class[label] = str(class_uri)
        self.label_to_class[local_name] = str(class_uri)

    def _parse_property(self, g, prop_uri, EX, prop_type: str) -> None:
        """Parse an OWL Property (DataProperty or ObjectProperty) from the graph."""
        from rdflib import RDFS, OWL, Literal

        local_name = self._get_local_name(prop_uri)

        # Get label
        label = ""
        for obj in g.objects(prop_uri, RDFS.label):
            label = str(obj)
            break

        # Get comment
        comment = ""
        for obj in g.objects(prop_uri, RDFS.comment):
            comment = str(obj)
            break

        # Get domain
        domain = ""
        for obj in g.objects(prop_uri, RDFS.domain):
            domain = str(obj)
            break

        # Get range
        range_uri = ""
        for obj in g.objects(prop_uri, RDFS.range):
            range_uri = str(obj)
            break

        # Get custom annotations (ex:examples, ex:rules, ex:source_mapping)
        examples = []
        rules = ""
        source_mapping = ""

        # Find the ontology namespace for custom properties
        ont_ns = str(prop_uri).rsplit('#', 1)[0] + '#' if '#' in str(prop_uri) else str(prop_uri).rsplit('/', 1)[0] + '/'

        for p, o in g.predicate_objects(prop_uri):
            p_str = str(p)
            if 'examples' in p_str:
                examples.append(str(o))
            elif 'rules' in p_str:
                rules = str(o)
            elif 'source_mapping' in p_str:
                source_mapping = str(o)

        # Check if functional property
        is_functional = (prop_uri, None, OWL.FunctionalProperty) in g

        prop_info = PropertyInfo(
            uri=str(prop_uri),
            local_name=local_name,
            label=label or local_name,
            comment=comment,
            examples=examples,
            rules=rules,
            source_mapping=source_mapping,
            domain=domain,
            range=range_uri,
            property_type=prop_type,
            is_functional=is_functional,
        )

        self.properties[str(prop_uri)] = prop_info

        # Build label index
        if label:
            if label not in self.label_to_property:
                self.label_to_property[label] = []
            self.label_to_property[label].append(str(prop_uri))

        # Also index by local name
        if local_name not in self.label_to_property:
            self.label_to_property[local_name] = []
        self.label_to_property[local_name].append(str(prop_uri))

        # Add property to its domain class
        if domain and domain in self.classes:
            if prop_type == "DataProperty":
                self.classes[domain].data_properties.append(str(prop_uri))
            else:
                self.classes[domain].object_properties.append(str(prop_uri))

    def _get_local_name(self, uri) -> str:
        """Extract local name from URI."""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        return uri_str.split('/')[-1]

    def load_source_mapping(self, mapping_path: str) -> bool:
        """Load source mapping from JSON file.

        This connects OWL concepts to MySQL table/column names.

        Args:
            mapping_path: Path to the mapping JSON file

        Returns:
            True if loaded successfully
        """
        mapping_file = Path(mapping_path)
        if not mapping_file.exists():
            logger.warning(f"Source mapping file not found: {mapping_path}")
            return False

        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)

            for table_mapping in mapping_data:
                table_name = table_mapping.get("table_name", "")
                mapped_class = table_mapping.get("mapped_class", "")

                if not table_name:
                    continue

                self.source_mapping[table_name] = table_mapping

                # Link class to table
                if mapped_class:
                    # Find the class by local name
                    class_local = mapped_class.replace("ex:", "")
                    for class_uri, class_info in self.classes.items():
                        if class_info.local_name == class_local:
                            class_info.table_name = table_name
                            self.table_to_class[table_name] = class_uri
                            break

                # Link properties to columns
                for col_mapping in table_mapping.get("columns", []):
                    col_name = col_mapping.get("column_name", "")
                    mapped_prop = col_mapping.get("mapped_property", "")

                    if col_name and mapped_prop:
                        prop_local = mapped_prop.replace("ex:", "")
                        for prop_uri, prop_info in self.properties.items():
                            if prop_info.local_name == prop_local:
                                prop_info.table_name = table_name
                                prop_info.column_name = col_name
                                self.column_to_property[f"{table_name}.{col_name}"] = prop_uri
                                self.column_to_property[col_name] = prop_uri
                                break

            logger.info(f"Loaded source mapping for {len(self.source_mapping)} tables")
            return True

        except Exception as e:
            logger.error(f"Failed to load source mapping: {e}")
            return False

    def load_dictionary(self, dict_path: str) -> bool:
        """Load semantic dictionary for aliases, abbreviations, and slang.

        Args:
            dict_path: Path to the dictionary JSON file

        Returns:
            True if loaded successfully
        """
        return self.dictionary.load_from_file(dict_path)

    def save_dictionary(self, dict_path: str) -> bool:
        """Save current dictionary to file."""
        return self.dictionary.save_to_file(dict_path)

    def add_alias(self, canonical: str, alias: str) -> None:
        """Add an alias mapping (runtime API)."""
        self.dictionary.add_alias(canonical, alias)

    def add_abbreviation(self, abbr: str, expansion: str, is_global: bool = False) -> None:
        """Add an abbreviation mapping (runtime API)."""
        self.dictionary.add_abbreviation(abbr, expansion, is_global)

    def add_slang(self, slang: str, meaning: str) -> None:
        """Add a slang/jargon mapping (runtime API)."""
        self.dictionary.add_slang(slang, meaning)

    def normalize_query(self, query: str) -> str:
        """Normalize a query by expanding abbreviations and slang.

        Args:
            query: User's original query

        Returns:
            Normalized query with canonical terms
        """
        return self.dictionary.expand_query(query)

    def _build_relationship_graph(self) -> None:
        """Build relationship graph from ObjectProperties for JOIN inference."""
        for prop_uri, prop_info in self.properties.items():
            if prop_info.property_type != "ObjectProperty":
                continue

            if not prop_info.domain or not prop_info.range:
                continue

            # Create relationship path
            from_class = prop_info.domain
            to_class = prop_info.range

            # Get table info if available
            from_table = ""
            to_table = ""
            if from_class in self.classes:
                from_table = self.classes[from_class].table_name
            if to_class in self.classes:
                to_table = self.classes[to_class].table_name

            rel_path = RelationshipPath(
                from_class=from_class,
                to_class=to_class,
                via_property=prop_uri,
                from_table=from_table,
                to_table=to_table,
                from_column=prop_info.column_name,
            )

            if from_class not in self.relationships:
                self.relationships[from_class] = []
            self.relationships[from_class].append(rel_path)

    # ==================== Query Methods ====================

    def find_property_by_label(self, chinese_label: str) -> Optional[PropertyInfo]:
        """Find property by Chinese label (exact match).

        First tries to normalize the term using the semantic dictionary,
        then performs exact match against ontology labels.

        Args:
            chinese_label: Chinese label to search for

        Returns:
            PropertyInfo if found, None otherwise
        """
        # First, try to normalize using dictionary (handles aliases, abbrs, slang)
        normalized = self.dictionary.normalize_term(chinese_label)

        # Try normalized term first
        prop_uris = self.label_to_property.get(normalized, [])
        if prop_uris:
            return self.properties.get(prop_uris[0])

        # Fall back to original term if normalization didn't help
        if normalized != chinese_label:
            prop_uris = self.label_to_property.get(chinese_label, [])
            if prop_uris:
                return self.properties.get(prop_uris[0])

        return None

    def search_properties_by_label(self, query: str) -> List[PropertyInfo]:
        """Search properties by partial label match.

        Args:
            query: Search query (partial match)

        Returns:
            List of matching PropertyInfo objects
        """
        results = []
        query_lower = query.lower()

        for label, prop_uris in self.label_to_property.items():
            if query_lower in label.lower() or query in label:
                for uri in prop_uris:
                    if uri in self.properties:
                        results.append(self.properties[uri])

        return results

    def find_class_by_label(self, chinese_label: str) -> Optional[ClassInfo]:
        """Find class by Chinese label."""
        class_uri = self.label_to_class.get(chinese_label)
        if class_uri:
            return self.classes.get(class_uri)
        return None

    def get_join_path(self, from_class: str, to_class: str) -> Optional[RelationshipPath]:
        """Get JOIN path between two classes.

        Args:
            from_class: Source class URI or local name
            to_class: Target class URI or local name

        Returns:
            RelationshipPath if found
        """
        # Normalize to URI
        from_uri = self._normalize_class_uri(from_class)
        to_uri = self._normalize_class_uri(to_class)

        if not from_uri or not to_uri:
            return None

        # Direct relationship
        for rel in self.relationships.get(from_uri, []):
            if rel.to_class == to_uri:
                return rel

        # Reverse relationship
        for rel in self.relationships.get(to_uri, []):
            if rel.to_class == from_uri:
                # Create reverse path
                return RelationshipPath(
                    from_class=from_uri,
                    to_class=to_uri,
                    via_property=rel.via_property,
                    from_table=rel.to_table,
                    to_table=rel.from_table,
                    from_column=rel.from_column,
                )

        return None

    def _normalize_class_uri(self, class_ref: str) -> Optional[str]:
        """Normalize class reference to full URI."""
        if class_ref in self.classes:
            return class_ref

        # Try to find by local name
        for uri, info in self.classes.items():
            if info.local_name == class_ref or info.local_name == class_ref.replace("ex:", ""):
                return uri

        # Try to find by label
        return self.label_to_class.get(class_ref)

    # ==================== Semantic Context Building ====================

    def extract_terms_from_query(self, query: str) -> List[str]:
        """Extract potential entity/property terms from user query.

        Uses simple heuristics to find Chinese terms that might match
        ontology labels.

        Args:
            query: User's natural language query

        Returns:
            List of extracted terms
        """
        terms = []

        # Check against all known labels
        for label in self.label_to_property.keys():
            if label in query and len(label) >= 2:
                terms.append(label)

        for label in self.label_to_class.keys():
            if label in query and len(label) >= 2:
                terms.append(label)

        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)

        return unique_terms

    def build_semantic_context(self, query: str, max_properties: int = 10) -> str:
        """Build semantic context for a query.

        This is the main method for generating semantic enhancement.
        It extracts relevant ontology information based on the query.

        The method:
        1. Normalizes the query using semantic dictionary (expands abbrs, slang)
        2. Extracts terms from the normalized query
        3. Adds term alias/normalization hints from dictionary
        4. Builds context with matched properties and relationships

        Args:
            query: User's natural language query
            max_properties: Maximum number of properties to include

        Returns:
            Formatted semantic context string
        """
        if not self._loaded:
            return ""

        # First normalize the query using dictionary
        normalized_query = self.normalize_query(query)
        if normalized_query != query:
            logger.debug(f"Query normalized: '{query}' → '{normalized_query}'")

        # Extract terms from both original and normalized query
        extracted_terms = self.extract_terms_from_query(normalized_query)
        original_terms = self.extract_terms_from_query(query) if normalized_query != query else []

        # Combine terms (normalized takes priority)
        all_terms = list(dict.fromkeys(extracted_terms + original_terms))

        context_parts = ["语义上下文 (Semantic Context):"]

        # Add term normalization hints from semantic dictionary
        term_hints = self._build_term_normalization_hints(query)
        if term_hints:
            context_parts.append("\n【术语规范化提示】")
            context_parts.extend(term_hints)

        # Collect relevant properties
        relevant_props: List[PropertyInfo] = []
        relevant_classes: Set[str] = set()

        for term in all_terms:
            # Find matching properties
            props = self.search_properties_by_label(term)
            relevant_props.extend(props)

            # Find matching classes
            class_info = self.find_class_by_label(term)
            if class_info:
                relevant_classes.add(class_info.uri)

        # Also search properties from dictionary mappings directly
        dict_props = self._find_properties_from_dictionary(query)
        relevant_props.extend(dict_props)

        # Deduplicate properties
        seen_uris = set()
        unique_props = []
        for prop in relevant_props:
            if prop.uri not in seen_uris:
                seen_uris.add(prop.uri)
                unique_props.append(prop)

        # Limit number of properties
        unique_props = unique_props[:max_properties]

        # Format property information
        if unique_props:
            context_parts.append("\n【相关字段】")
            for prop in unique_props:
                prop_context = self._format_property_context(prop)
                context_parts.append(prop_context)

        # Find and format relationships
        relationships = self._find_relevant_relationships(relevant_classes)
        if relationships:
            context_parts.append("\n【表关联关系】")
            for rel in relationships[:5]:  # Limit to 5 relationships
                rel_context = self._format_relationship_context(rel)
                context_parts.append(rel_context)

        # Only return if we have actual content beyond the header
        if len(context_parts) > 1:
            return "\n".join(context_parts)
        return ""

    def _build_term_normalization_hints(self, query: str) -> List[str]:
        """Build term normalization hints from semantic dictionary.

        This helps LLM understand that abbreviations and aliases should be
        expanded to their canonical forms when generating SQL.

        Args:
            query: User's original query

        Returns:
            List of formatted hint strings
        """
        hints = []

        # Check each term mapping for matches in the query
        for canonical, mapping in self.dictionary._canonical_to_mapping.items():
            # Check if any variant appears in the query
            matched_variant = None
            for variant in mapping.all_variants():
                if variant in query:
                    matched_variant = variant
                    break

            if matched_variant and matched_variant != canonical:
                # Get additional info from the raw dictionary data
                property_name = mapping.property_name

                # Build the hint with property context
                hint = f"  - '{matched_variant}' 是 '{canonical}' 的简称/别名"
                if property_name:
                    # Look up the table.column for this property
                    col_key = property_name
                    for key in self.column_to_property.keys():
                        if key.endswith(f".{property_name}") or key == property_name:
                            hint += f"，对应字段 {key}"
                            break
                    else:
                        hint += f"，对应属性 {property_name}"

                hints.append(hint)

                # Add enum values if available from extended dictionary format
                # (These are stored in the JSON but not in TermMapping by default)
                # We'll check the raw data

        # Also check for custom enum_values and descriptions in dictionary
        hints.extend(self._get_extended_dictionary_hints(query))

        return hints

    def _get_extended_dictionary_hints(self, query: str) -> List[str]:
        """Get extended hints from dictionary entries with enum_values or descriptions.

        The semantic_dictionary.json may contain extended fields like:
        - enum_values: List of valid values for a field
        - description: Usage guidance for the field

        Args:
            query: User's original query

        Returns:
            List of additional hint strings
        """
        hints = []

        # We need to re-read the dictionary file to get extended fields
        # since TermMapping doesn't store them
        try:
            from pathlib import Path
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent.parent.parent.parent.parent
            dict_path = project_root / "assets" / "schema" / "semantic_dictionary.json"

            if dict_path.exists():
                import json
                with open(dict_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for mapping in data.get("term_mappings", []):
                    # Check if this mapping is relevant to the query
                    canonical = mapping.get("canonical", "")
                    aliases = mapping.get("aliases", [])
                    property_name = mapping.get("property", "")
                    enum_values = mapping.get("enum_values", [])
                    description = mapping.get("description", "")

                    # Check if any alias appears in query
                    is_relevant = any(alias in query for alias in aliases) or canonical in query

                    if is_relevant and (enum_values or description):
                        if enum_values:
                            hints.append(f"  - {property_name} 字段的有效值包括: {', '.join(enum_values)}")
                        if description:
                            hints.append(f"  - 提示: {description}")
        except Exception as e:
            logger.debug(f"Failed to load extended dictionary hints: {e}")

        return hints

    def _find_properties_from_dictionary(self, query: str) -> List[PropertyInfo]:
        """Find properties by looking up dictionary mappings.

        This method directly uses the property_name from dictionary entries
        to find properties, bypassing the label-based search.

        Args:
            query: User's query

        Returns:
            List of matched PropertyInfo objects
        """
        props = []

        for canonical, mapping in self.dictionary._canonical_to_mapping.items():
            # Check if any variant appears in query
            is_match = any(v in query for v in mapping.all_variants()) or canonical in query

            if is_match and mapping.property_name:
                # Find the property by column name
                prop_uri = self.column_to_property.get(mapping.property_name)
                if prop_uri and prop_uri in self.properties:
                    props.append(self.properties[prop_uri])
                else:
                    # Try with table prefix
                    for key, uri in self.column_to_property.items():
                        if key.endswith(f".{mapping.property_name}"):
                            if uri in self.properties:
                                props.append(self.properties[uri])
                            break

        return props

    def _format_property_context(self, prop: PropertyInfo) -> str:
        """Format property information for prompt context."""
        parts = []

        # Basic info
        table_col = f"{prop.table_name}.{prop.column_name}" if prop.table_name and prop.column_name else prop.local_name
        parts.append(f"  - {prop.label} → {table_col}")

        # Comment (truncate if too long)
        if prop.comment:
            comment = prop.comment[:200] + "..." if len(prop.comment) > 200 else prop.comment
            # Clean up multiline comments
            comment = comment.replace('\n', ' ').replace('"', '')
            parts.append(f"    含义: {comment}")

        # Enum values
        enum_values = prop.get_enum_values()
        if enum_values:
            parts.append(f"    可选值: {', '.join(enum_values[:5])}")

        # Examples
        if prop.examples:
            example = prop.examples[0][:100] if len(prop.examples[0]) > 100 else prop.examples[0]
            parts.append(f"    示例: {example}")

        return "\n".join(parts)

    def _format_relationship_context(self, rel: RelationshipPath) -> str:
        """Format relationship information for prompt context."""
        prop_info = self.properties.get(rel.via_property)
        prop_label = prop_info.label if prop_info else self._get_local_name(rel.via_property)

        from_class_info = self.classes.get(rel.from_class)
        to_class_info = self.classes.get(rel.to_class)

        from_name = from_class_info.label if from_class_info else self._get_local_name(rel.from_class)
        to_name = to_class_info.label if to_class_info else self._get_local_name(rel.to_class)

        # Table join info
        if rel.from_table and rel.to_table:
            return f"  - {from_name}({rel.from_table}) --[{prop_label}]--> {to_name}({rel.to_table})"
        else:
            return f"  - {from_name} --[{prop_label}]--> {to_name}"

    def _find_relevant_relationships(self, class_uris: Set[str]) -> List[RelationshipPath]:
        """Find relationships involving the given classes."""
        relationships = []

        for class_uri in class_uris:
            # Outgoing relationships
            for rel in self.relationships.get(class_uri, []):
                relationships.append(rel)

            # Incoming relationships
            for from_uri, rels in self.relationships.items():
                for rel in rels:
                    if rel.to_class == class_uri:
                        relationships.append(rel)

        return relationships

    # ==================== Statistics ====================

    def get_stats(self) -> Dict:
        """Get statistics about the loaded ontology."""
        return {
            "loaded": self._loaded,
            "classes": len(self.classes),
            "properties": len(self.properties),
            "data_properties": sum(1 for p in self.properties.values() if p.property_type == "DataProperty"),
            "object_properties": sum(1 for p in self.properties.values() if p.property_type == "ObjectProperty"),
            "source_mapping_tables": len(self.source_mapping),
            "label_index_size": len(self.label_to_property),
        }


# Singleton instance for global access
_global_index: Optional[OntologySemanticIndex] = None


def get_semantic_index() -> OntologySemanticIndex:
    """Get the global semantic index instance."""
    global _global_index
    if _global_index is None:
        _global_index = OntologySemanticIndex()
    return _global_index


def initialize_semantic_index(ttl_path: str, mapping_path: str) -> OntologySemanticIndex:
    """Initialize the global semantic index with TTL and mapping files.

    Args:
        ttl_path: Path to TTL file
        mapping_path: Path to source mapping JSON

    Returns:
        Initialized OntologySemanticIndex
    """
    global _global_index
    _global_index = OntologySemanticIndex()
    _global_index.load_from_ttl(ttl_path)
    _global_index.load_source_mapping(mapping_path)
    return _global_index
