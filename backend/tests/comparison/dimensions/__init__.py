from .text_content import TextContentDimension
from .font_formatting import FontFormattingDimension
from .paragraph_formatting import ParagraphFormattingDimension
from .table_comparison import TableComparisonDimension
from .image_comparison import ImageComparisonDimension
from .document_structure import DocumentStructureDimension
from .paragraph_structure import ParagraphStructureDimension
from .list_numbering import ListNumberingDimension
from .headers_footers import HeadersFootersDimension
from .page_layout import PageLayoutDimension
from .style_system import StyleSystemDimension

ALL_DIMENSIONS = [
    TextContentDimension,
    FontFormattingDimension,
    ParagraphFormattingDimension,
    TableComparisonDimension,
    ImageComparisonDimension,
    DocumentStructureDimension,
    ParagraphStructureDimension,
    ListNumberingDimension,
    HeadersFootersDimension,
    PageLayoutDimension,
    StyleSystemDimension,
]

__all__ = [
    "TextContentDimension",
    "FontFormattingDimension",
    "ParagraphFormattingDimension",
    "TableComparisonDimension",
    "ImageComparisonDimension",
    "DocumentStructureDimension",
    "ParagraphStructureDimension",
    "ListNumberingDimension",
    "HeadersFootersDimension",
    "PageLayoutDimension",
    "StyleSystemDimension",
    "ALL_DIMENSIONS",
]
