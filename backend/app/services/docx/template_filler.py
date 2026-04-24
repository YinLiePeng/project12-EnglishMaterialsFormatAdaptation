import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any, Optional
from copy import deepcopy

from lxml import etree
from docx import Document
from docx.oxml.ns import qn

from .parser import ContentElement, ElementType


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

NSMAP = {
    "w": W_NS,
    "r": R_NS,
    "rel": REL_NS,
    "ct": CT_NS,
}


def _xpath(element, path):
    return element.xpath(path, namespaces=NSMAP)


def _find_target_cell(doc_xml, row: int, col: int) -> Optional[Any]:
    tables = _xpath(doc_xml, ".//w:tbl")
    if not tables:
        return None
    table = tables[0]
    rows = _xpath(table, "./w:tr")
    if row >= len(rows):
        return None
    target_row = rows[row]
    cells = _xpath(target_row, "./w:tc")
    if col >= len(cells):
        return None
    return cells[col]


def _build_formatted_elements(
    elements: List[ContentElement],
    style_mapping: Dict[str, Dict[str, Any]],
    style_keys: Optional[Dict[int, str]],
    preserve_format: bool,
) -> Document:
    from .generator import DocxGenerator

    gen = DocxGenerator()
    gen.generate_from_elements(
        elements, style_mapping, style_keys, preserve_format=preserve_format
    )
    return gen.doc


def _extract_body_elements_from_doc(doc: Document) -> List[Any]:
    body = doc.element.body
    result = []
    for child in body:
        tag = etree.QName(child.tag).localname if isinstance(child.tag, str) else ""
        if tag in ("p", "tbl"):
            result.append(deepcopy(child))
    return result


def _collect_image_info(doc: Document) -> Dict[str, bytes]:
    images: Dict[str, bytes] = {}
    for rel in doc.part.rels.values():
        if "image" in rel.reltype and hasattr(rel, "target_ref"):
            try:
                part = rel.target_part
                images[rel.rId] = part.blob
            except Exception:
                pass
    return images


def _get_max_rId(rels_xml) -> int:
    max_id = 0
    for rel in _xpath(rels_xml, "//rel:Relationship"):
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            try:
                max_id = max(max_id, int(rid[3:]))
            except ValueError:
                pass
    return max_id


def _get_next_rId(rels_xml) -> str:
    return f"rId{_get_max_rId(rels_xml) + 1}"


def _get_content_types_map(ct_xml) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for default_el in _xpath(ct_xml, "//ct:Default"):
        ext = default_el.get("Extension", "")
        ct = default_el.get("ContentType", "")
        if ext and ct:
            result[ext.lower()] = ct
    return result


def _remap_image_refs(
    elements: List[Any],
    old_to_new_rId: Dict[str, str],
) -> None:
    if not old_to_new_rId:
        return
    for el in elements:
        for blip in el.iter(qn("a:blip")):
            old_rId = blip.get(qn("r:embed"))
            if old_rId and old_rId in old_to_new_rId:
                blip.set(qn("r:embed"), old_to_new_rId[old_rId])
        for pict in el.iter():
            if not isinstance(pict.tag, str):
                continue
            rId = pict.get(qn("r:id"))
            if rId and rId in old_to_new_rId:
                pict.set(qn("r:id"), old_to_new_rId[rId])


def fill_template_zip(
    template_path: str,
    output_path: str,
    elements: List[ContentElement],
    style_mapping: Dict[str, Dict[str, Any]],
    style_keys: Optional[Dict[int, str]] = None,
    preserve_format: bool = False,
    marker_position: Optional[Dict[str, Any]] = None,
) -> None:
    shutil.copy2(template_path, output_path)

    formatted_doc = _build_formatted_elements(
        elements, style_mapping, style_keys, preserve_format
    )
    new_elements = _extract_body_elements_from_doc(formatted_doc)

    if not new_elements:
        return

    image_blobs = _collect_image_info(formatted_doc)

    with zipfile.ZipFile(output_path, "r") as zin:
        file_list = zin.namelist()
        doc_xml_bytes = zin.read("word/document.xml")
        rels_xml_bytes = zin.read("word/_rels/document.xml.rels")
        ct_xml_bytes = zin.read("[Content_Types].xml")
        existing_media = {n for n in file_list if n.startswith("word/media/")}

    doc_xml = etree.fromstring(doc_xml_bytes)
    rels_xml = etree.fromstring(rels_xml_bytes)
    ct_xml = etree.fromstring(ct_xml_bytes)

    old_to_new_rId: Dict[str, str] = {}
    if image_blobs:
        img_exts_in_doc = _get_content_types_map(ct_xml)
        media_idx = 1
        for existing in sorted(existing_media):
            name = Path(existing).stem
            try:
                num = int(name.replace("image", ""))
                media_idx = max(media_idx, num + 1)
            except ValueError:
                pass

        mime_to_ext = {
            "image/png": "png",
            "image/jpeg": "jpeg",
            "image/gif": "gif",
            "image/bmp": "bmp",
            "image/tiff": "tiff",
            "image/x-emf": "emf",
            "image/x-wmf": "wmf",
            "image/emf": "emf",
            "image/wmf": "wmf",
        }
        ext_to_mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "tiff": "image/tiff",
            "emf": "image/x-emf",
            "wmf": "image/x-wmf",
        }

        for old_rId, blob in image_blobs.items():
            from .parser import DocxParser

            ext_guess = "png"
            new_rId = _get_next_rId(rels_xml)
            media_name = f"word/media/image{media_idx}"
            ext_guess = "png"

            image_info = None
            for rel_obj in formatted_doc.part.rels.values():
                if rel_obj.rId == old_rId and hasattr(rel_obj, "target_ref"):
                    try:
                        target = rel_obj.target_ref
                        if "." in target:
                            ext_guess = target.rsplit(".", 1)[-1].lower()
                        part = rel_obj.target_part
                        if hasattr(part, "content_type"):
                            ct_val = part.content_type
                            if ct_val in mime_to_ext:
                                ext_guess = mime_to_ext[ct_val]
                    except Exception:
                        pass
                    break

            media_path = f"word/media/image{media_idx}.{ext_guess}"
            while media_path in existing_media:
                media_idx += 1
                media_path = f"word/media/image{media_idx}.{ext_guess}"

            mime = ext_to_mime.get(ext_guess, "image/png")

            rel_elem = etree.SubElement(rels_xml, "Relationship")
            rel_elem.set("Id", new_rId)
            rel_elem.set(
                "Type",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
            )
            rel_elem.set("Target", f"media/image{media_idx}.{ext_guess}")

            old_to_new_rId[old_rId] = new_rId

            ct_ext = ext_guess
            if ct_ext == "jpeg":
                ct_ext = "jpg"
            if ct_ext not in img_exts_in_doc:
                default_el = etree.SubElement(ct_xml, "Default")
                default_el.set("Extension", ct_ext)
                default_el.set("ContentType", mime)
                img_exts_in_doc[ct_ext] = mime

            existing_media.add(media_path)
            media_idx += 1

    _remap_image_refs(new_elements, old_to_new_rId)

    ref_element = None

    if marker_position and marker_position.get("type") == "table_cell":
        target_row = marker_position.get("row")
        target_col = marker_position.get("col")
        if target_row is not None and target_col is not None:
            cell = _find_target_cell(doc_xml, target_row, target_col)
            if cell is not None:
                existing_ps = _xpath(cell, "./w:p")
                if existing_ps:
                    ref_element = existing_ps[-1]

    if ref_element is None:
        body = doc_xml
        body_ps = _xpath(body, ".//w:body/w:p")
        if body_ps:
            for p in body_ps:
                text = "".join(t.text or "" for t in _xpath(p, ".//w:t"))
                if "{{CONTENT}}" in text or "{{content}}" in text:
                    p.clear()
                    p.tag = qn("w:p")
                    ref_element = p
                    break

        if ref_element is None:
            for alt in ["{内容}", "【内容】"]:
                for p in body_ps:
                    text = "".join(t.text or "" for t in _xpath(p, ".//w:t"))
                    if alt in text:
                        p.clear()
                        p.tag = qn("w:p")
                        ref_element = p
                        break
                if ref_element is not None:
                    break

    if ref_element is None:
        body_children = _xpath(doc_xml, ".//w:body/*")
        sect_prs = _xpath(doc_xml, ".//w:body/w:sectPr")
        if sect_prs:
            ref_element = sect_prs[0]
        elif body_children:
            ref_element = body_children[-1]

    if ref_element is None:
        raise ValueError("无法定位模板中的插入锚点")

    parent = ref_element.getparent()
    insert_after = ref_element
    for elem in new_elements:
        insert_after.addnext(elem)
        insert_after = elem

    doc_xml_bytes_new = etree.tostring(
        doc_xml, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    rels_xml_bytes_new = etree.tostring(
        rels_xml, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    ct_xml_bytes_new = etree.tostring(
        ct_xml, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    changes = {
        "word/document.xml": doc_xml_bytes_new,
        "word/_rels/document.xml.rels": rels_xml_bytes_new,
        "[Content_Types].xml": ct_xml_bytes_new,
    }

    if image_blobs and old_to_new_rId:
        rId_to_media = {}
        for old_rId, new_rId in old_to_new_rId.items():
            for rel_elem in _xpath(rels_xml, "//rel:Relationship"):
                if rel_elem.get("Id") == new_rId:
                    rId_to_media[old_rId] = rel_elem.get("Target")
                    break
        for old_rId, blob in image_blobs.items():
            target = rId_to_media.get(old_rId)
            if target:
                changes[f"word/{target}"] = blob

    _rewrite_zip(output_path, changes)


def _rewrite_zip(zip_path: str, changes: Dict[str, bytes]) -> None:
    with zipfile.ZipFile(zip_path, "r") as zin:
        existing = {}
        for name in zin.namelist():
            if name not in changes:
                existing[name] = zin.read(name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in sorted(existing.keys()):
            zout.writestr(name, existing[name])
        for name, data in changes.items():
            zout.writestr(name, data)
