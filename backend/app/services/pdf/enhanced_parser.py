"""增强版PDF解析器 - 支持标准模式和Hybrid模式

提供统一的PDF解析接口，支持两种解析模式：
1. 标准模式：使用opendataloader_pdf原生Java解析（快，适合简单PDF）
2. Hybrid模式：使用opendataloader_pdf[hybrid] + Docling后端（慢，适合复杂/嵌套表格PDF）

自动处理模式选择、失败回退、结果统一化。
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.core.config import settings
from app.services.pdf.hybrid_server import hybrid_server_manager


@dataclass
class PDFParseResult:
    """PDF解析结果"""
    success: bool
    json_data: Optional[Dict[str, Any]] = None
    json_path: Optional[Path] = None
    images_dir: Optional[Path] = None
    mode_used: str = "standard"  # "standard" | "hybrid"
    fallback_reason: Optional[str] = None  # 如果使用回退，记录原因
    error_message: Optional[str] = None


class EnhancedPDFParser:
    """增强版PDF解析器

    支持双模式解析，自动失败回退，统一的JSON输出格式。
    """

    def __init__(self, file_path: str, use_hybrid: bool = False):
        """初始化解析器

        Args:
            file_path: PDF文件路径
            use_hybrid: 是否使用hybrid模式（用户选择）
        """
        self.file_path = Path(file_path)
        self.use_hybrid = use_hybrid
        self.result: Optional[PDFParseResult] = None

    def parse(self) -> PDFParseResult:
        """执行PDF解析

        解析策略：
        1. 如果用户选择hybrid且server可用，先尝试hybrid模式
        2. 如果hybrid失败且允许回退，自动切换到标准模式
        3. 如果用户未选择hybrid，直接使用标准模式

        Returns:
            PDFParseResult: 解析结果
        """
        if self.use_hybrid:
            # 用户选择了hybrid模式
            if hybrid_server_manager.is_available():
                # 尝试hybrid模式
                result = self._parse_hybrid()
                if result.success:
                    return result

                # Hybrid失败，检查是否允许回退
                if settings.HYBRID_FALLBACK_ON_FAILURE:
                    print(f"⚠️ Hybrid解析失败，回退到标准模式: {result.error_message}")
                    standard_result = self._parse_standard()
                    if standard_result.success:
                        standard_result.fallback_reason = result.error_message
                        standard_result.mode_used = "standard"
                    return standard_result
                else:
                    return result
            else:
                # Hybrid server不可用
                if settings.HYBRID_FALLBACK_ON_FAILURE:
                    print("⚠️ Hybrid server 不可用，回退到标准模式")
                    standard_result = self._parse_standard()
                    if standard_result.success:
                        standard_result.fallback_reason = "Hybrid server未启动"
                        standard_result.mode_used = "standard"
                    return standard_result
                else:
                    return PDFParseResult(
                        success=False,
                        mode_used="hybrid",
                        error_message="Hybrid server不可用，且未启用自动回退"
                    )
        else:
            # 用户未选择hybrid，直接使用标准模式
            return self._parse_standard()

    def _parse_standard(self) -> PDFParseResult:
        """使用标准模式解析PDF

        Returns:
            PDFParseResult: 解析结果
        """
        try:
            import opendataloader_pdf

            output_dir = self.file_path.parent
            json_path = self.file_path.with_suffix('.json')

            # 如果JSON已存在，直接加载
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                return PDFParseResult(
                    success=True,
                    json_data=json_data,
                    json_path=json_path,
                    images_dir=self._get_images_dir(),
                    mode_used="standard"
                )

            # 调用opendataloader_pdf转换
            opendataloader_pdf.convert(
                input_path=[str(self.file_path)],
                output_dir=str(output_dir),
                format="json",
                quiet=True
            )

            # 加载生成的JSON
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                return PDFParseResult(
                    success=True,
                    json_data=json_data,
                    json_path=json_path,
                    images_dir=self._get_images_dir(),
                    mode_used="standard"
                )
            else:
                return PDFParseResult(
                    success=False,
                    mode_used="standard",
                    error_message="标准模式解析后未生成JSON文件"
                )

        except Exception as e:
            return PDFParseResult(
                success=False,
                mode_used="standard",
                error_message=f"标准模式解析失败: {str(e)}"
            )

    def _parse_hybrid(self) -> PDFParseResult:
        """使用Hybrid模式解析PDF

        Returns:
            PDFParseResult: 解析结果
        """
        try:
            import opendataloader_pdf

            output_dir = self.file_path.parent
            json_path = self.file_path.with_suffix('.json')

            # 如果已有标准模式的JSON，先备份
            if json_path.exists():
                backup_path = json_path.with_suffix('.json.standard')
                shutil.copy2(json_path, backup_path)

            # 调用hybrid模式转换
            opendataloader_pdf.convert(
                input_path=[str(self.file_path)],
                output_dir=str(output_dir),
                format="json",
                hybrid="docling-fast",
                hybrid_mode="full",
                hybrid_url=hybrid_server_manager.server_url,
                quiet=True
            )

            # 加载生成的JSON
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                # 验证JSON结构是否有效
                if self._validate_json_structure(json_data):
                    return PDFParseResult(
                        success=True,
                        json_data=json_data,
                        json_path=json_path,
                        images_dir=self._get_images_dir(),
                        mode_used="hybrid"
                    )
                else:
                    # JSON结构无效，恢复备份
                    self._restore_backup(json_path)
                    return PDFParseResult(
                        success=False,
                        mode_used="hybrid",
                        error_message="Hybrid模式生成的JSON结构无效"
                    )
            else:
                return PDFParseResult(
                    success=False,
                    mode_used="hybrid",
                    error_message="Hybrid模式解析后未生成JSON文件"
                )

        except Exception as e:
            # 恢复备份（如果存在）
            json_path = self.file_path.with_suffix('.json')
            self._restore_backup(json_path)

            return PDFParseResult(
                success=False,
                mode_used="hybrid",
                error_message=f"Hybrid模式解析失败: {str(e)}"
            )

    def _get_images_dir(self) -> Optional[Path]:
        """获取图片目录"""
        images_dir = Path(str(self.file_path.with_suffix('')) + '_images')
        if images_dir.exists():
            return images_dir
        return None

    def _validate_json_structure(self, json_data: Dict[str, Any]) -> bool:
        """验证JSON结构是否有效

        检查必要的字段是否存在。

        Args:
            json_data: 解析后的JSON数据

        Returns:
            bool: 是否有效
        """
        if not isinstance(json_data, dict):
            return False

        # 检查必要字段
        required_fields = ['kids']
        for field in required_fields:
            if field not in json_data:
                return False

        # 检查kids是否为列表
        kids = json_data.get('kids')
        if not isinstance(kids, list):
            return False

        return True

    def _restore_backup(self, json_path: Path):
        """恢复标准模式的JSON备份

        Args:
            json_path: JSON文件路径
        """
        backup_path = json_path.with_suffix('.json.standard')
        if backup_path.exists():
            shutil.copy2(backup_path, json_path)
            backup_path.unlink()


def parse_pdf(file_path: str, use_hybrid: bool = False) -> PDFParseResult:
    """便捷函数：解析PDF文件

    Args:
        file_path: PDF文件路径
        use_hybrid: 是否使用hybrid模式

    Returns:
        PDFParseResult: 解析结果
    """
    parser = EnhancedPDFParser(file_path, use_hybrid=use_hybrid)
    return parser.parse()
