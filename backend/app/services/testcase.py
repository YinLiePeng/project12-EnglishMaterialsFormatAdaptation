"""测试用例收集服务"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class TestCaseService:
    """测试用例收集服务"""

    def __init__(self, storage_path: str = "./测试用例/用户反馈"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def submit_testcase(
        self,
        original_file_path: str,
        original_filename: str,
        feedback_description: str,
        problem_types: List[str],
        output_file_path: Optional[str] = None,
        output_filename: Optional[str] = None,
        contact_info: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """提交测试用例

        Args:
            original_file_path: 原始文件路径
            original_filename: 原始文件名
            feedback_description: 反馈描述
            problem_types: 问题类型列表
            output_file_path: 输出文件路径（可选）
            output_filename: 输出文件名（可选）
            contact_info: 联系方式（可选）
            task_id: 原始任务ID（可选）
        """
        # 生成测试用例ID
        testcase_id = f"tc-{uuid.uuid4()}"

        # 创建测试用例目录
        testcase_dir = self.storage_path / testcase_id
        testcase_dir.mkdir(parents=True, exist_ok=True)

        # 复制原始文件
        original_dest = testcase_dir / original_filename
        original_src = Path(original_file_path)
        if original_src.exists():
            original_dest.write_bytes(original_src.read_bytes())

        # 复制输出文件（如果有）
        output_dest = None
        if output_file_path and Path(output_file_path).exists():
            output_filename = output_filename or Path(output_file_path).name
            output_dest = testcase_dir / output_filename
            output_dest.write_bytes(Path(output_file_path).read_bytes())

        # 创建metadata.json
        metadata = {
            "id": testcase_id,
            "original_filename": original_filename,
            "output_filename": output_filename,
            "feedback_description": feedback_description,
            "problem_types": problem_types,
            "contact_info": contact_info,
            "task_id": task_id,
            "created_at": datetime.now().isoformat(),
            "status": "待处理",
        }

        metadata_path = testcase_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return {"testcase_id": testcase_id, "created_at": metadata["created_at"]}

    def get_testcase_list(
        self,
        page: int = 1,
        page_size: int = 20,
        problem_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取测试用例列表"""
        testcases = []

        # 遍历所有测试用例目录
        for testcase_dir in sorted(self.storage_path.iterdir(), reverse=True):
            if not testcase_dir.is_dir():
                continue

            metadata_path = testcase_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                # 过滤条件
                if problem_type and problem_type not in metadata.get(
                    "problem_types", []
                ):
                    continue
                if status and metadata.get("status") != status:
                    continue

                testcases.append(metadata)
            except Exception:
                continue

        # 分页
        total = len(testcases)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = testcases[start:end]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "testcases": paginated,
        }

    def get_testcase_detail(self, testcase_id: str) -> Optional[Dict[str, Any]]:
        """获取测试用例详情"""
        testcase_dir = self.storage_path / testcase_id
        metadata_path = testcase_dir / "metadata.json"

        if not metadata_path.exists():
            return None

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # 添加文件路径信息
        metadata["original_file_path"] = str(
            testcase_dir / metadata.get("original_filename", "")
        )
        if metadata.get("output_filename"):
            metadata["output_file_path"] = str(
                testcase_dir / metadata["output_filename"]
            )

        return metadata

    def get_testcase_file(self, testcase_id: str, file_type: str) -> Optional[Path]:
        """获取测试用例文件路径

        Args:
            testcase_id: 测试用例ID
            file_type: 文件类型，"original" 或 "output"
        """
        testcase_dir = self.storage_path / testcase_id
        metadata = self.get_testcase_detail(testcase_id)

        if not metadata:
            return None

        if file_type == "original":
            filename = metadata.get("original_filename")
        elif file_type == "output":
            filename = metadata.get("output_filename")
        else:
            return None

        if not filename:
            return None

        file_path = testcase_dir / filename
        return file_path if file_path.exists() else None

    def delete_testcase(self, testcase_id: str) -> bool:
        """删除测试用例"""
        testcase_dir = self.storage_path / testcase_id

        if not testcase_dir.exists():
            return False

        # 删除目录及其内容
        import shutil

        shutil.rmtree(testcase_dir)

        return True

    def update_testcase_status(self, testcase_id: str, status: str) -> bool:
        """更新测试用例状态"""
        testcase_dir = self.storage_path / testcase_id
        metadata_path = testcase_dir / "metadata.json"

        if not metadata_path.exists():
            return False

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        metadata["status"] = status
        metadata["updated_at"] = datetime.now().isoformat()

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return True


# 全局测试用例服务实例
testcase_service = TestCaseService()
