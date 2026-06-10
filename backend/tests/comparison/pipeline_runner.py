"""PDF→DOCX 管道执行器"""

import asyncio
import sys
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.pdf.parser import PDFParser
from app.services.pdf.enhanced_parser import EnhancedPDFParser
from app.services.processor import DocumentProcessor
from app.services.docx.parser import ContentElement


class PipelineRunner:
    """PDF→DOCX 转换管道执行器"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_single(self, pdf_path: Path) -> Tuple[Path, float]:
        """处理单个PDF文件

        Args:
            pdf_path: PDF文件路径

        Returns:
            (output_path, processing_time): 生成的DOCX路径和处理时间
        """
        start_time = time.time()

        # Step 1: 使用EnhancedPDFParser生成JSON（如果不存在）
        enhanced = await asyncio.to_thread(EnhancedPDFParser, str(pdf_path), False)
        parse_result = await asyncio.to_thread(enhanced.parse)

        if not parse_result.success:
            raise ValueError(f"PDF解析失败: {parse_result.error_message}")

        # Step 2: 使用PDFParser将JSON转为ContentElements
        pdf_parser = await asyncio.to_thread(PDFParser, str(pdf_path))
        pdf_parser.json_data = parse_result.json_data
        pdf_parser.json_path = parse_result.json_path
        pdf_parser.images_dir = parse_result.images_dir
        elements = await asyncio.to_thread(pdf_parser.convert_to_content_elements)

        if not elements:
            raise ValueError(f"PDF解析结果为空: {pdf_path.name}")

        # Step 2: 通过DocumentProcessor处理
        processor = DocumentProcessor()
        result = await processor.process_document(
            input_file_path=str(pdf_path),
            layout_mode="none",
            preset_style="preserve",
            use_llm=False,
            elements=elements,
        )

        processing_time = time.time() - start_time

        if isinstance(result, dict) and "output_path" in result:
            return Path(result["output_path"]), processing_time
        else:
            raise ValueError(f"处理失败: {result}")

    async def run_all(
        self, pdf_files: list, progress_callback=None
    ) -> Dict[str, Tuple[Optional[Path], float, Optional[str]]]:
        """批量处理所有PDF文件

        Args:
            pdf_files: PDF文件路径列表
            progress_callback: 进度回调函数 (index, total, filename, success, time_or_error)

        Returns:
            {filename: (output_path, processing_time, error)}
        """
        results = {}

        for i, pdf_path in enumerate(pdf_files):
            try:
                output_path, proc_time = await self.run_single(pdf_path)
                results[pdf_path.name] = (output_path, proc_time, None)
                if progress_callback:
                    progress_callback(i + 1, len(pdf_files), pdf_path.name, True, proc_time)
            except Exception as e:
                results[pdf_path.name] = (None, 0.0, str(e))
                if progress_callback:
                    progress_callback(i + 1, len(pdf_files), pdf_path.name, False, str(e))

        return results
